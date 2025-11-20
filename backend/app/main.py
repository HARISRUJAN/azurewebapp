import sys
import asyncio

# Fix Windows asyncio event loop policy for subprocess support
# This must be done BEFORE importing FastAPI or any async code
# WindowsProactorEventLoopPolicy is required for subprocess support on Windows
# Needed so Playwright can spawn Chromium as a subprocess
if sys.platform.startswith("win"):
    # Set Windows event loop policy to support subprocess operations
    # ProactorEventLoopPolicy supports subprocess operations (required for Playwright)
    # This fixes NotImplementedError in asyncio subprocess transport
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import init_db
from app.core.scheduler import initialize_scheduler, shutdown_scheduler

# Initialize database
init_db()

app = FastAPI(
    title="AI Governance Literacy Platform API",
    description="API for AI Governance Literacy Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from app.api import auth, content, search, admin, crawl

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on application startup"""
    # Verify event loop policy and type are correct on Windows
    if sys.platform.startswith("win"):
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        current_policy = asyncio.get_event_loop_policy()
        current_loop = asyncio.get_running_loop()
        
        loop_type = type(current_loop).__name__
        policy_type = type(current_policy).__name__
        
        # Check if we have the correct loop type
        is_proactor = isinstance(current_loop, asyncio.ProactorEventLoop)
        is_correct_policy = isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy)
        
        if not is_proactor:
            # This is the critical issue - we have SelectorEventLoop instead of ProactorEventLoop
            logger.error(
                f"CRITICAL: Event loop is {loop_type}, not ProactorEventLoop! "
                f"Policy is {policy_type}. "
                f"This will cause NotImplementedError with Playwright subprocess operations. "
                f"Please start the server using 'python run_server.py' instead of 'uvicorn app.main:app'."
            )
        elif not is_correct_policy:
            logger.warning(
                f"Event loop policy is {policy_type} at startup, "
                f"but WindowsProactorEventLoopPolicy is required for Playwright. "
                f"Current loop: {loop_type}. "
                f"This may cause NotImplementedError when using Playwright."
            )
        else:
            logger.info(
                f"Event loop verified: {loop_type} with policy {policy_type}. "
                f"Playwright subprocess operations should work correctly."
            )
    
    initialize_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler gracefully on application shutdown"""
    shutdown_scheduler()


@app.get("/")
async def root():
    return {"message": "AI Governance Literacy Platform API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

