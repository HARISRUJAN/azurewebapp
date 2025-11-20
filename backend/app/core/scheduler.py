"""
Background scheduler for periodic crawling of enabled origins.
Uses APScheduler to schedule crawl jobs based on origin frequency_hours.
"""
import logging
import asyncio
from typing import Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, ScrapingOrigin
from app.services.scraping_service import scraping_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None
job_ids: Dict[int, str] = {}  # Map origin_id to job_id


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


async def crawl_origin_job(origin_id: int):
    """
    Background job to crawl and ingest an origin.
    This is called by the scheduler.
    
    Enhanced error handling ensures one failing origin does not crash the scheduler.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Scheduled crawl job started for origin {origin_id}")
        result = await scraping_service.crawl_and_ingest_origin(db, origin_id)
        if result.success:
            logger.info(f"Scheduled crawl completed successfully for origin {origin_id}")
        else:
            logger.warning(f"Scheduled crawl failed for origin {origin_id}: {result.message}")
            # Status is already updated by scraping_service, but ensure it's committed
            try:
                db.commit()
            except Exception:
                pass
    except Exception as e:
        # Catch all exceptions to prevent one failing origin from crashing the scheduler
        error_msg = f"Unexpected error in scheduled crawl job for origin {origin_id}: {str(e)}"
        logger.exception(error_msg)
        
        # Try to update origin status even on unexpected errors
        try:
            from app.models.database import ScrapingOrigin
            from datetime import datetime
            origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
            if origin:
                origin.last_run = datetime.utcnow()
                origin.last_status = f"failed: {error_msg[:200]}"  # Truncate long errors
                db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update origin status after error: {update_error}")
            db.rollback()
    finally:
        db.close()


def schedule_origin(origin: ScrapingOrigin):
    """
    Schedule a crawl job for an origin based on its frequency_hours.
    If a job already exists for this origin, it will be rescheduled.
    """
    global job_ids
    scheduler = get_scheduler()
    
    # Ensure scheduler is running
    if not scheduler.running:
        logger.warning("Scheduler is not running, cannot schedule origin. Will be scheduled on next startup.")
        return
    
    # Remove existing job if any
    if origin.id in job_ids:
        try:
            scheduler.remove_job(job_ids[origin.id])
            logger.info(f"Removed existing job for origin {origin.id}")
        except Exception as e:
            logger.warning(f"Error removing existing job for origin {origin.id}: {str(e)}")
    
    # Only schedule if enabled
    if not origin.enabled:
        logger.info(f"Origin {origin.id} is disabled, not scheduling")
        return
    
    # Schedule new job
    try:
        job_id = f"crawl_origin_{origin.id}"
        trigger = IntervalTrigger(hours=origin.frequency_hours)
        
        scheduler.add_job(
            crawl_origin_job,
            trigger=trigger,
            args=[origin.id],
            id=job_id,
            replace_existing=True
        )
        
        job_ids[origin.id] = job_id
        logger.info(f"Scheduled crawl job for origin {origin.id} ({origin.name}) every {origin.frequency_hours} hours")
    except Exception as e:
        logger.exception(f"Error scheduling job for origin {origin.id}: {str(e)}")


def unschedule_origin(origin_id: int):
    """Remove scheduled job for an origin"""
    global job_ids
    scheduler = get_scheduler()
    
    if origin_id in job_ids:
        try:
            scheduler.remove_job(job_ids[origin_id])
            del job_ids[origin_id]
            logger.info(f"Unscheduled crawl job for origin {origin_id}")
        except Exception as e:
            logger.warning(f"Error unscheduling job for origin {origin_id}: {str(e)}")


def initialize_scheduler():
    """
    Initialize the scheduler and load all enabled origins.
    Call this on application startup.
    """
    scheduler = get_scheduler()
    
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    # Load all enabled origins and schedule them
    db: Session = SessionLocal()
    try:
        origins = db.query(ScrapingOrigin).filter(ScrapingOrigin.enabled == True).all()
        logger.info(f"Initializing scheduler with {len(origins)} enabled origins")
        
        for origin in origins:
            schedule_origin(origin)
        
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.exception(f"Error initializing scheduler: {str(e)}")
    finally:
        db.close()


def shutdown_scheduler():
    """Shutdown the scheduler gracefully. Call this on application shutdown."""
    scheduler = get_scheduler()
    
    if scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.exception(f"Error shutting down scheduler: {str(e)}")

