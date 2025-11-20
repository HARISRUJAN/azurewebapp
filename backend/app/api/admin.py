from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db, ScrapingOrigin
from app.models.schemas import (
    ScrapingOriginCreate,
    ScrapingOriginUpdate,
    ScrapingOriginResponse,
    SystemHealth,
    OriginStatus,
    QdrantHealth,
    QdrantCollectionsHealth
)
from app.core.security import get_current_active_admin

router = APIRouter()


@router.get("/origins", response_model=List[ScrapingOriginResponse])
async def list_origins(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """List all scraping origins"""
    origins = db.query(ScrapingOrigin).all()
    return origins


@router.post("/origins", response_model=ScrapingOriginResponse, status_code=status.HTTP_201_CREATED)
async def create_origin(
    origin: ScrapingOriginCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Create a new scraping origin"""
    db_origin = ScrapingOrigin(**origin.dict())
    db.add(db_origin)
    db.commit()
    db.refresh(db_origin)
    
    # Schedule the new origin if enabled
    from app.core.scheduler import schedule_origin
    schedule_origin(db_origin)
    
    return db_origin


@router.put("/origins/{origin_id}", response_model=ScrapingOriginResponse)
async def update_origin(
    origin_id: int,
    origin_update: ScrapingOriginUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Update a scraping origin"""
    db_origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not db_origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    update_data = origin_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_origin, field, value)
    
    db.commit()
    db.refresh(db_origin)
    
    # Reschedule the origin with updated settings
    from app.core.scheduler import schedule_origin
    schedule_origin(db_origin)
    
    return db_origin


@router.delete("/origins/{origin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_origin(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Delete a scraping origin"""
    db_origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not db_origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    # Unschedule the origin before deleting
    from app.core.scheduler import unschedule_origin
    unschedule_origin(origin_id)
    
    db.delete(db_origin)
    db.commit()
    return None


@router.get("/origins/{origin_id}/status", response_model=dict)
async def get_origin_status(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Get status information for a specific origin"""
    from app.services.scraping_service import scraping_service
    status_info = scraping_service.get_origin_status(db, origin_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    return status_info


@router.post("/origins/{origin_id}/crawl")
async def trigger_crawl(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Manually trigger crawl and ingestion for a specific origin.
    Admin-only endpoint.
    
    Rate limited: Max 5 requests per minute per admin user.
    
    Returns detailed information about the crawl and ingestion process.
    """
    # Simple rate limiting: 5 requests per minute per user
    # V1 implementation: in-memory tracking (use Redis for production)
    import time
    from collections import defaultdict
    
    # In-memory rate limit tracking (simple V1 implementation)
    if not hasattr(trigger_crawl, '_rate_limit_tracker'):
        trigger_crawl._rate_limit_tracker = defaultdict(list)
    
    user_tracker = trigger_crawl._rate_limit_tracker[current_user.username]
    now = time.time()
    
    # Remove requests older than 1 minute
    user_tracker[:] = [req_time for req_time in user_tracker if now - req_time < 60]
    
    # Check if limit exceeded (5 requests per minute)
    if len(user_tracker) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: Maximum 5 crawl requests per minute. Please wait before trying again."
        )
    
    # Record this request
    user_tracker.append(now)
    
    from app.services.scraping_service import scraping_service
    
    # Reload origin to get current info
    origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    # Trigger crawl and ingest
    result = await scraping_service.crawl_and_ingest_origin(db, origin_id)
    
    # Reload origin to get updated status
    db.refresh(origin)
    
    response = {
        "success": result.success,
        "message": result.message,
        "origin_id": origin_id,
        "origin_name": origin.name,
        "origin_url": origin.url,
        "document_id": result.document_id,
        "last_run": origin.last_run.isoformat() if origin.last_run else None,
        "last_status": origin.last_status,
        "qdrant_status": origin.qdrant_status
    }
    
    # Add additional details if successful
    if result.success:
        response["status"] = "completed"
        if result.document_id:
            # Get document info
            from app.models.database import Document
            doc = db.query(Document).filter(Document.id == result.document_id).first()
            if doc:
                from app.models.database import Chunk
                chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
                response["document_info"] = {
                    "document_id": doc.id,
                    "title": doc.title,
                    "chunks_count": chunk_count,
                    "content_length": len(doc.content) if doc.content else 0
                }
    else:
        response["status"] = "failed"
    
    return response


@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Get system health status including Qdrant connection"""
    from app.services.vector_service import vector_service
    from app.core.config import settings
    
    origins = db.query(ScrapingOrigin).all()
    origin_statuses = [
        OriginStatus(
            origin_id=origin.id,
            origin_name=origin.name,
            last_run=origin.last_run,
            last_status=origin.last_status,
            qdrant_status=origin.qdrant_status,
            enabled=origin.enabled
        )
        for origin in origins
    ]
    
    # Check Qdrant health for both collections
    
    qdrant_collections_health = None
    qdrant_health = None  # Keep legacy for backward compatibility
    
    try:
        # Initialize vector service if not already initialized
        if not vector_service._initialized:
            vector_service._init_client()
        
        # Check legacy collection (if exists)
        legacy_collection_health = None
        try:
            legacy_info = vector_service.client.get_collection(vector_service.collection_name)
            legacy_count = vector_service.client.count(vector_service.collection_name).count
            legacy_collection_health = QdrantHealth(
                connected=True,
                url=settings.qdrant_url,
                collection_name=vector_service.collection_name,
                collection_exists=True,
                points_count=legacy_count,
                vector_size=legacy_info.config.params.vectors.size if hasattr(legacy_info.config.params.vectors, 'size') else None
            )
            # Also set legacy qdrant_health for backward compatibility
            qdrant_health = legacy_collection_health
        except Exception as legacy_error:
            # Legacy collection doesn't exist or error - that's okay
            legacy_collection_health = QdrantHealth(
                connected=True,
                url=settings.qdrant_url,
                collection_name=vector_service.collection_name,
                collection_exists=False,
                points_count=0
            )
        
        # Check semantic collection
        semantic_collection_health = None
        try:
            semantic_info = vector_service.client.get_collection(vector_service.semantic_collection_name)
            semantic_count = vector_service.client.count(vector_service.semantic_collection_name).count
            semantic_collection_health = QdrantHealth(
                connected=True,
                url=settings.qdrant_url,
                collection_name=vector_service.semantic_collection_name,
                collection_exists=True,
                points_count=semantic_count,
                vector_size=semantic_info.config.params.vectors.size if hasattr(semantic_info.config.params.vectors, 'size') else None
            )
        except Exception as semantic_error:
            semantic_collection_health = QdrantHealth(
                connected=True,
                url=settings.qdrant_url,
                collection_name=vector_service.semantic_collection_name,
                collection_exists=False,
                points_count=0,
                error=str(semantic_error)
            )
        
        qdrant_collections_health = QdrantCollectionsHealth(
            connected=True,
            url=settings.qdrant_url,
            legacy_collection=legacy_collection_health,
            semantic_collection=semantic_collection_health
        )
        
    except Exception as e:
        error_type = type(e).__name__
        error_str = str(e) if str(e) else repr(e)
        qdrant_collections_health = QdrantCollectionsHealth(
            connected=False,
            url=settings.qdrant_url,
            error=f"{error_type}: {error_str}"
        )
        qdrant_health = QdrantHealth(
            connected=False,
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            collection_exists=False,
            error=f"{error_type}: {error_str}"
        )
    
    return SystemHealth(
        status="healthy",
        origins=origin_statuses,
        qdrant=qdrant_health,  # Legacy support
        qdrant_collections=qdrant_collections_health  # New: both collections
    )

