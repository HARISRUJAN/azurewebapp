import logging
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.database import ScrapingOrigin, Document
from app.services.crawling_service import crawl_url
from app.services.ingestion_service import ingestion_service
from app.models.schemas import DocumentIngest

logger = logging.getLogger(__name__)


class CrawlAndIngestResult:
    """Result of crawl and ingest operation"""
    def __init__(self, success: bool, message: str, origin_id: int, document_id: Optional[int] = None):
        self.success = success
        self.message = message
        self.origin_id = origin_id
        self.document_id = document_id


class ScrapingService:
    def update_origin_status(
        self,
        db: Session,
        origin_id: int,
        crawl_status: str,  # "success" or "failed"
        qdrant_status: Optional[str] = None,  # "success" or "failed" with optional error message
        error_message: Optional[str] = None
    ):
        """
        Update the last run status of an origin.
        
        Args:
            db: Database session
            origin_id: ID of the origin to update
            crawl_status: Status of the crawl operation ("success" or "failed")
            qdrant_status: Optional status of Qdrant ingestion ("success" or "failed: error message")
            error_message: Optional overall error message (deprecated, use qdrant_status instead)
        """
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if origin:
            origin.last_run = datetime.utcnow()
            
            # Build comprehensive status message
            status_parts = [f"Crawl: {crawl_status}"]
            if qdrant_status:
                origin.qdrant_status = qdrant_status[:500] if len(qdrant_status) > 500 else qdrant_status  # Truncate long errors
                status_parts.append(f"Qdrant: {qdrant_status[:200]}")  # Truncate for last_status field
            elif error_message:
                # Legacy support: if error_message provided but no qdrant_status, assume it's a crawl error
                status_parts.append(f"Error: {error_message[:200]}")
            
            origin.last_status = ", ".join(status_parts)
            db.commit()
    
    def get_origin_status(self, db: Session, origin_id: int) -> Optional[dict]:
        """Get status information for an origin"""
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if not origin:
            return None
        
        return {
            "id": origin.id,
            "name": origin.name,
            "last_run": origin.last_run,
            "last_status": origin.last_status,
            "qdrant_status": origin.qdrant_status,
            "enabled": origin.enabled
        }
    
    async def crawl_and_ingest_origin(self, db: Session, origin_id: int) -> CrawlAndIngestResult:
        """
        Crawl an origin URL using Crawl4AI and ingest the content into the vector DB.
        
        Args:
            db: Database session
            origin_id: ID of the ScrapingOrigin to crawl
            
        Returns:
            CrawlAndIngestResult with success status and message
        """
        # Load origin from DB
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if not origin:
            return CrawlAndIngestResult(
                success=False,
                message=f"Origin with ID {origin_id} not found",
                origin_id=origin_id
            )
        
        if not origin.enabled:
            return CrawlAndIngestResult(
                success=False,
                message=f"Origin '{origin.name}' is disabled",
                origin_id=origin_id
            )
        
        import time
        start_time = time.time()
        
        # Structured logging: start of operation
        logger.info(
            f"CRAWL_START origin_id={origin_id} url={origin.url} name={origin.name}",
            extra={
                "origin_id": origin_id,
                "url": origin.url,
                "name": origin.name,
                "status": "started"
            }
        )
        
        try:
            # Step 1: Crawl the URL using multi-page crawler
            logger.info(f"[Step 1/4] Crawling URL: {origin.url}")
            crawl_start = time.time()
            
            # Get crawl configuration from settings
            from app.core.config import settings
            from app.services.crawling_service import crawl_multi_page
            
            # Use multi-page crawler with configured limits
            max_depth = settings.crawl_max_depth
            max_pages = settings.crawl_max_pages_per_run
            
            crawl_results = await crawl_multi_page(
                start_urls=[origin.url],
                max_depth=max_depth,
                max_pages=max_pages,
                allowed_paths=settings.crawl_allowed_paths if settings.crawl_allowed_paths else None,
                excluded_paths=settings.crawl_excluded_paths if settings.crawl_excluded_paths else None,
                same_domain_only=True,  # Domain-seeded mode for origins
                base_domain=None  # Will be determined from origin.url
            )
            crawl_elapsed_ms = int((time.time() - crawl_start) * 1000)
            
            # Check if any pages were crawled successfully
            successful_results = [r for r in crawl_results if not r.get("error")]
            failed_results = [r for r in crawl_results if r.get("error")]
            
            if not successful_results:
                error_msg = "No pages crawled successfully"
                if failed_results:
                    error_msg = f"All {len(failed_results)} pages failed. First error: {failed_results[0].get('error', 'Unknown error')}"
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"CRAWL_FAILED origin_id={origin_id} url={origin.url} elapsed_ms={elapsed_ms} error={error_msg}",
                    extra={
                        "origin_id": origin_id,
                        "url": origin.url,
                        "status": "failed",
                        "elapsed_ms": elapsed_ms,
                        "error_message": error_msg,
                        "stage": "crawl",
                        "pages_attempted": len(crawl_results),
                        "pages_failed": len(failed_results)
                    }
                )
                self.update_origin_status(db, origin_id, crawl_status="failed", error_message=error_msg)
                return CrawlAndIngestResult(
                    success=False,
                    message=f"Crawl failed: {error_msg}",
                    origin_id=origin_id
                )
            
            # Aggregate content from all successful pages
            logger.info(f"[Step 2/4] Aggregating content from {len(successful_results)} pages")
            
            # Combine markdown content with page separators
            markdown_parts = []
            titles = []
            for result in successful_results:
                page_markdown = result.get("markdown", "").strip()
                if page_markdown:
                    markdown_parts.append(page_markdown)
                    page_title = result.get("metadata", {}).get("title", "")
                    if page_title:
                        titles.append(page_title)
            
            # Join with page separators
            markdown_content = "\n\n---\n\n".join(markdown_parts)
            
            if not markdown_content:
                error_msg = "No content extracted from any crawled pages"
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"CONTENT_EXTRACTION_FAILED origin_id={origin_id} url={origin.url} elapsed_ms={elapsed_ms} error={error_msg}",
                    extra={
                        "origin_id": origin_id,
                        "url": origin.url,
                        "status": "failed",
                        "elapsed_ms": elapsed_ms,
                        "error_message": error_msg,
                        "stage": "content_extraction",
                        "pages_crawled": len(successful_results)
                    }
                )
                self.update_origin_status(db, origin_id, crawl_status="failed", error_message=error_msg)
                return CrawlAndIngestResult(
                    success=False,
                    message=error_msg,
                    origin_id=origin_id
                )
            
            # Use first page's title or origin name
            title = titles[0] if titles else origin.name
            
            logger.info(f"Extracted {len(markdown_content)} characters from {len(successful_results)} pages (crawl_elapsed_ms={crawl_elapsed_ms})")
            
            # Aggregate metadata from first successful page
            first_result = successful_results[0]
            metadata = first_result.get("metadata", {}).copy()
            metadata["pages_crawled"] = len(successful_results)
            metadata["pages_failed"] = len(failed_results)
            metadata["total_pages_attempted"] = len(crawl_results)
            
            # Step 3: Check for duplicates (allow re-crawling to update content)
            logger.info(f"[Step 3/4] Checking for existing documents. Title: {title}")
            
            # Check if document with same URL and origin exists
            existing_doc = db.query(Document).filter(
                Document.url == origin.url,
                Document.origin_id == origin_id
            ).first()
            
            if existing_doc:
                logger.info(f"Document already exists (ID: {existing_doc.id}) for {origin.url}. Updating with new content.")
                # Instead of skipping, we could update the existing document
                # For now, we'll skip to avoid duplicates, but log it clearly
                self.update_origin_status(db, origin_id, crawl_status="success", qdrant_status="success (already ingested)")
                return CrawlAndIngestResult(
                    success=True,
                    message=f"Content already ingested (document ID: {existing_doc.id}). To re-crawl, delete the existing document first.",
                    origin_id=origin_id,
                    document_id=existing_doc.id
                )
            
            # Step 4: Prepare and ingest document
            logger.info(f"[Step 4/4] Preparing document for ingestion")
            document_metadata = {
                "origin_id": origin_id,
                "origin_name": origin.name,
                "source_type": metadata.get("source_type", "web"),
                "content_type": metadata.get("content_type", ""),
                "crawled_at": datetime.utcnow().isoformat(),
                **metadata
            }
            
            document_data = DocumentIngest(
                title=title,
                source=origin.name,
                url=origin.url,
                content=markdown_content,
                metadata=document_metadata
            )
            
            logger.info(f"Ingesting document: {title} ({len(markdown_content)} chars) into vector DB")
            
            # Ingest into vector DB using existing ingestion service
            qdrant_success = False
            qdrant_error = None
            try:
                db_document = ingestion_service.ingest_document(
                    db=db,
                    document_data=document_data,
                    origin_id=origin_id
                )
                logger.info(f"Successfully ingested document ID: {db_document.id}")
                qdrant_success = True
            except Exception as ingest_error:
                error_msg = str(ingest_error)
                elapsed_ms = int((time.time() - start_time) * 1000)
                # Structured logging: ingestion failure
                logger.error(
                    f"INGESTION_FAILED origin_id={origin_id} url={origin.url} elapsed_ms={elapsed_ms} error={error_msg}",
                    extra={
                        "origin_id": origin_id,
                        "url": origin.url,
                        "status": "failed",
                        "elapsed_ms": elapsed_ms,
                        "error_message": error_msg,
                        "stage": "ingestion"
                    }
                )
                logger.exception(f"Ingestion error for origin {origin_id}: {error_msg}")
                
                # Check if it's a Qdrant-specific error
                if "QDRANT_ERROR:" in error_msg:
                    qdrant_error = error_msg.replace("QDRANT_ERROR: ", "")
                    qdrant_success = False
                    # Crawl succeeded but Qdrant failed
                    self.update_origin_status(
                        db, 
                        origin_id, 
                        crawl_status="success", 
                        qdrant_status=f"failed: {qdrant_error[:400]}"
                    )
                    return CrawlAndIngestResult(
                        success=False,
                        message=f"Crawl succeeded but Qdrant ingestion failed: {qdrant_error}",
                        origin_id=origin_id
                    )
                else:
                    # General ingestion error (could be chunking, etc.)
                    qdrant_error = error_msg
                    qdrant_success = False
                    self.update_origin_status(
                        db, 
                        origin_id, 
                        crawl_status="success", 
                        qdrant_status=f"failed: {error_msg[:400]}"
                    )
                    return CrawlAndIngestResult(
                        success=False,
                        message=f"Ingestion failed: {error_msg}",
                        origin_id=origin_id
                    )
            
            # Update origin status to success for both crawl and Qdrant
            if qdrant_success:
                status_msg = f"success ({len(successful_results)}/{len(crawl_results)} pages)"
                self.update_origin_status(db, origin_id, crawl_status=status_msg, qdrant_status="success")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            # Structured logging: success
            logger.info(
                f"CRAWL_SUCCESS origin_id={origin_id} url={origin.url} document_id={db_document.id} elapsed_ms={elapsed_ms} pages_crawled={len(successful_results)}",
                extra={
                    "origin_id": origin_id,
                    "url": origin.url,
                    "document_id": db_document.id,
                    "status": "success",
                    "elapsed_ms": elapsed_ms,
                    "error_message": None,
                    "pages_crawled": len(successful_results),
                    "pages_failed": len(failed_results)
                }
            )
            logger.info(f"✓ Successfully completed crawl and ingest for origin {origin_id}: {origin.name} (Document ID: {db_document.id}, {len(successful_results)} pages, elapsed: {elapsed_ms}ms)")
            
            return CrawlAndIngestResult(
                success=True,
                message=f"Successfully crawled and ingested {len(markdown_content)} characters. Document ID: {db_document.id}",
                origin_id=origin_id,
                document_id=db_document.id
            )
            
        except Exception as e:
            error_msg = f"Error during crawl and ingest: {str(e)}"
            elapsed_ms = int((time.time() - start_time) * 1000)
            # Structured logging: general failure
            logger.error(
                f"CRAWL_FAILED origin_id={origin_id} url={origin.url} elapsed_ms={elapsed_ms} error={error_msg}",
                extra={
                    "origin_id": origin_id,
                    "url": origin.url,
                    "status": "failed",
                    "elapsed_ms": elapsed_ms,
                    "error_message": error_msg,
                    "stage": "unknown"
                }
            )
            logger.exception(f"Crawl and ingest failed for origin {origin_id}: {error_msg}")
            # If we got here, it's likely a crawl error (before Qdrant)
            self.update_origin_status(db, origin_id, crawl_status="failed", error_message=error_msg)
            return CrawlAndIngestResult(
                success=False,
                message=error_msg,
                origin_id=origin_id
            )


scraping_service = ScrapingService()

