"""
Hybrid crawler API endpoints for query-seeded and domain-seeded crawling.
Protected endpoints requiring admin authentication.
"""
import logging
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.orm import Session
from app.core.security import get_current_active_admin
from app.models.database import get_db, User
from app.services.hybrid_crawler import hybrid_crawler
from app.services.ingestion_service import ingestion_service
from app.models.schemas import DocumentIngest
from app.core.scheduler import get_scheduler
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response schemas
class QueryCrawlRequest(BaseModel):
    """Request schema for query-seeded crawl."""
    query: str = Field(..., description="Natural language search query (e.g., 'EU AI Act high-risk obligations')")
    max_depth: int = Field(default=2, ge=0, le=5, description="Maximum crawl depth (0-5)")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of seed URLs from search API (1-50)")
    # Future extensions: allowed_domains, tags, excluded_paths, etc.
    # allowed_domains: Optional[List[str]] = None
    # tags: Optional[List[str]] = None
    # excluded_paths: Optional[List[str]] = None


class DomainCrawlRequest(BaseModel):
    """Request schema for domain-seeded crawl."""
    start_url: HttpUrl = Field(..., description="Starting URL/domain to crawl (e.g., 'https://digital-strategy.ec.europa.eu/')")
    max_depth: int = Field(default=3, ge=0, le=5, description="Maximum crawl depth (0-5)")
    max_pages: int = Field(default=200, ge=1, le=1000, description="Maximum number of pages to crawl (1-1000)")
    # Future extensions: allowed_paths, excluded_paths, tags, etc.
    # allowed_paths: Optional[List[str]] = None
    # excluded_paths: Optional[List[str]] = None
    # tags: Optional[List[str]] = None


class CrawlJobResponse(BaseModel):
    """Response schema for crawl job submission."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (e.g., 'queued', 'running', 'completed')")
    mode: str = Field(..., description="Crawl mode ('query' or 'domain')")
    message: Optional[str] = Field(None, description="Additional information about the job")


# In-memory job tracking (for production, use Redis or database)
_job_status: dict = {}


async def _process_query_crawl_job(
    job_id: str,
    query: str,
    max_depth: int,
    top_k: int,
    triggered_by: str
):
    """
    Background job to process query-seeded crawl and ingest results.
    
    This function is called by the scheduler to run the crawl job asynchronously.
    """
    db: Session = None
    try:
        from app.models.database import SessionLocal
        db = SessionLocal()
        
        _job_status[job_id] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
        logger.info(f"Job {job_id}: Starting query-seeded crawl for query='{query}' (triggered by {triggered_by})")
        
        # Run the query-seeded crawl
        results = await hybrid_crawler.crawl_query_seeded(
            query=query,
            top_k=top_k,
            max_depth=max_depth,
            max_pages=30  # Use default from config
        )
        
        if not results:
            _job_status[job_id] = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "pages_crawled": 0,
                "error": "No pages crawled"
            }
            logger.warning(f"Job {job_id}: No pages crawled for query '{query}'")
            return
        
        # Aggregate content from all pages
        markdown_parts = []
        titles = []
        for result in results:
            page_markdown = result.get("markdown", "").strip()
            if page_markdown:
                markdown_parts.append(page_markdown)
                page_title = result.get("metadata", {}).get("title", "")
                if page_title:
                    titles.append(page_title)
        
        if not markdown_parts:
            _job_status[job_id] = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "pages_crawled": len(results),
                "error": "No content extracted"
            }
            logger.warning(f"Job {job_id}: No content extracted from {len(results)} pages")
            return
        
        # Combine content
        combined_content = "\n\n---\n\n".join(markdown_parts)
        title = titles[0] if titles else f"Query: {query}"
        
        # Get metadata from first result
        first_result = results[0]
        metadata = first_result.get("metadata", {}).copy()
        metadata["pages_crawled"] = len(results)
        metadata["source_query"] = query
        metadata["triggered_by"] = triggered_by
        metadata["job_id"] = job_id
        metadata["crawled_at"] = datetime.utcnow().isoformat()
        
        # Ingest into vector DB
        document_data = DocumentIngest(
            title=title,
            source=f"Query: {query}",
            url=results[0].get("url", ""),
            content=combined_content,
            metadata=metadata
        )
        
        db_document = ingestion_service.ingest_document(
            db=db,
            document_data=document_data,
            origin_id=None  # No origin for query-seeded crawls
        )
        
        _job_status[job_id] = {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "pages_crawled": len(results),
            "document_id": db_document.id,
            "content_length": len(combined_content)
        }
        
        logger.info(f"Job {job_id}: Successfully completed query-seeded crawl. Document ID: {db_document.id}, {len(results)} pages")
        
    except Exception as e:
        error_msg = str(e)
        _job_status[job_id] = {
            "status": "failed",
            "failed_at": datetime.utcnow().isoformat(),
            "error": error_msg
        }
        logger.exception(f"Job {job_id}: Error processing query-seeded crawl: {error_msg}")
    finally:
        if db:
            db.close()


async def _process_domain_crawl_job(
    job_id: str,
    start_url: str,
    max_depth: int,
    max_pages: int,
    triggered_by: str
):
    """
    Background job to process domain-seeded crawl and ingest results.
    
    This function is called by the scheduler to run the crawl job asynchronously.
    """
    db: Session = None
    try:
        from app.models.database import SessionLocal
        db = SessionLocal()
        
        _job_status[job_id] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
        logger.info(f"Job {job_id}: Starting domain-seeded crawl for URL='{start_url}' (triggered by {triggered_by})")
        
        # Run the domain-seeded crawl
        results = await hybrid_crawler.crawl_domain_seeded(
            base_url=start_url,
            max_depth=max_depth,
            max_pages=max_pages
        )
        
        if not results:
            _job_status[job_id] = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "pages_crawled": 0,
                "error": "No pages crawled"
            }
            logger.warning(f"Job {job_id}: No pages crawled for URL '{start_url}'")
            return
        
        # Aggregate content from all pages
        markdown_parts = []
        titles = []
        for result in results:
            page_markdown = result.get("markdown", "").strip()
            if page_markdown:
                markdown_parts.append(page_markdown)
                page_title = result.get("metadata", {}).get("title", "")
                if page_title:
                    titles.append(page_title)
        
        if not markdown_parts:
            _job_status[job_id] = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "pages_crawled": len(results),
                "error": "No content extracted"
            }
            logger.warning(f"Job {job_id}: No content extracted from {len(results)} pages")
            return
        
        # Combine content
        combined_content = "\n\n---\n\n".join(markdown_parts)
        title = titles[0] if titles else start_url.split('/')[-1] or start_url
        
        # Get metadata from first result
        first_result = results[0]
        metadata = first_result.get("metadata", {}).copy()
        metadata["pages_crawled"] = len(results)
        metadata["root_domain"] = metadata.get("root_domain", start_url)
        metadata["triggered_by"] = triggered_by
        metadata["job_id"] = job_id
        metadata["crawled_at"] = datetime.utcnow().isoformat()
        
        # Ingest into vector DB
        document_data = DocumentIngest(
            title=title,
            source=metadata.get("root_domain", start_url),
            url=start_url,
            content=combined_content,
            metadata=metadata
        )
        
        db_document = ingestion_service.ingest_document(
            db=db,
            document_data=document_data,
            origin_id=None  # No origin for domain-seeded crawls
        )
        
        _job_status[job_id] = {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "pages_crawled": len(results),
            "document_id": db_document.id,
            "content_length": len(combined_content)
        }
        
        logger.info(f"Job {job_id}: Successfully completed domain-seeded crawl. Document ID: {db_document.id}, {len(results)} pages")
        
    except Exception as e:
        error_msg = str(e)
        _job_status[job_id] = {
            "status": "failed",
            "failed_at": datetime.utcnow().isoformat(),
            "error": error_msg
        }
        logger.exception(f"Job {job_id}: Error processing domain-seeded crawl: {error_msg}")
    finally:
        if db:
            db.close()


def enqueue_crawl_job(
    mode: str,
    params: dict,
    triggered_by: str
) -> str:
    """
    Enqueue a crawl job to run asynchronously.
    
    Args:
        mode: Crawl mode ('query' or 'domain')
        params: Parameters for the crawl job
        triggered_by: Username of the admin who triggered the crawl
        
    Returns:
        job_id: Unique identifier for the job
        
    This function uses the existing APScheduler to run crawl jobs in the background.
    The job will be executed asynchronously and results will be ingested into Qdrant.
    
    Future extensions:
    - Add job priority
    - Add job scheduling (run at specific time)
    - Add job dependencies
    - Store job status in database instead of in-memory
    """
    scheduler = get_scheduler()
    
    if not scheduler.running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not running. Please restart the server."
        )
    
    # Generate unique job ID
    job_id = f"crawl_{mode}_{uuid.uuid4().hex[:8]}"
    
    # Create job function based on mode
    if mode == "query":
        job_func = _process_query_crawl_job
        job_args = [
            job_id,
            params["query"],
            params.get("max_depth", 2),
            params.get("top_k", 10),
            triggered_by
        ]
    elif mode == "domain":
        job_func = _process_domain_crawl_job
        job_args = [
            job_id,
            str(params["start_url"]),  # Convert HttpUrl to string
            params.get("max_depth", 3),
            params.get("max_pages", 200),
            triggered_by
        ]
    else:
        raise ValueError(f"Invalid crawl mode: {mode}. Must be 'query' or 'domain'")
    
    # Initialize job status
    _job_status[job_id] = {
        "status": "queued",
        "queued_at": datetime.utcnow().isoformat(),
        "mode": mode,
        "triggered_by": triggered_by
    }
    
    # Schedule the job to run immediately
    # Use APScheduler's date trigger with current time for immediate execution
    try:
        from apscheduler.triggers.date import DateTrigger
        scheduler.add_job(
            job_func,
            trigger=DateTrigger(run_date=datetime.utcnow()),
            args=job_args,
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Enqueued {mode} crawl job {job_id} triggered by {triggered_by}")
    except Exception as e:
        logger.error(f"Failed to enqueue crawl job {job_id}: {e}")
        del _job_status[job_id]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue crawl job: {str(e)}"
        )
    
    return job_id


@router.post("/crawl/query", response_model=CrawlJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_query_crawl(
    request: QueryCrawlRequest,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Start a query-seeded crawl job.
    
    This endpoint initiates a crawl job that:
    1. Uses a search API (Perplexity/Google) to find seed URLs based on the query
    2. Crawls those URLs with shallow depth for freshness
    3. Ingests the crawled content into the vector database
    
    **Admin Panel Usage:**
    ```javascript
    const response = await fetch('/api/crawl/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        query: 'EU AI Act high-risk obligations',
        max_depth: 2,
        top_k: 10
      })
    });
    const { job_id, status } = await response.json();
    ```
    
    **Future Extensions:**
    - Add `allowed_domains` to restrict crawling to specific domains
    - Add `tags` to categorize crawled content
    - Add `excluded_paths` to skip certain URL patterns
    - Add `priority` to control job execution order
    
    Returns:
        Job ID and status for tracking the crawl progress
    """
    try:
        job_id = enqueue_crawl_job(
            mode="query",
            params={
                "query": request.query,
                "max_depth": request.max_depth,
                "top_k": request.top_k
            },
            triggered_by=current_user.username
        )
        
        return CrawlJobResponse(
            job_id=job_id,
            status="queued",
            mode="query",
            message=f"Query-seeded crawl job queued for query: '{request.query}'"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting query crawl: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start crawl job: {str(e)}"
        )


@router.post("/crawl/domain", response_model=CrawlJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_domain_crawl(
    request: DomainCrawlRequest,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Start a domain-seeded crawl job.
    
    This endpoint initiates a crawl job that:
    1. Starts from a base URL/domain
    2. Crawls internal links more deeply with strict limits
    3. Only follows same-domain links
    4. Ingests the crawled content into the vector database
    
    **Admin Panel Usage:**
    ```javascript
    const response = await fetch('/api/crawl/domain', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        start_url: 'https://digital-strategy.ec.europa.eu/',
        max_depth: 3,
        max_pages: 200
      })
    });
    const { job_id, status } = await response.json();
    ```
    
    **Future Extensions:**
    - Add `allowed_paths` to restrict crawling to specific URL patterns
    - Add `excluded_paths` to skip certain URL patterns
    - Add `tags` to categorize crawled content
    - Add `priority` to control job execution order
    
    Returns:
        Job ID and status for tracking the crawl progress
    """
    try:
        job_id = enqueue_crawl_job(
            mode="domain",
            params={
                "start_url": request.start_url,
                "max_depth": request.max_depth,
                "max_pages": request.max_pages
            },
            triggered_by=current_user.username
        )
        
        return CrawlJobResponse(
            job_id=job_id,
            status="queued",
            mode="domain",
            message=f"Domain-seeded crawl job queued for URL: '{request.start_url}'"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting domain crawl: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start crawl job: {str(e)}"
        )


@router.get("/crawl/job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_admin)
):
    """
    Get the status of a crawl job.
    
    Returns current status, progress, and results if available.
    """
    if job_id not in _job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return _job_status[job_id]
