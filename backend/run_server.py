"""
Custom server startup script that ensures WindowsProactorEventLoopPolicy is used.
This fixes the issue where uvicorn creates a SelectorEventLoop instead of ProactorEventLoop.
"""
import sys
import asyncio
import os

# CRITICAL: Set event loop policy BEFORE any other imports
# This must be done before uvicorn or any async code runs
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print(f"[OK] Set event loop policy to: {type(asyncio.get_event_loop_policy()).__name__}")

# Now import uvicorn and app
import uvicorn
from app.main import app

async def serve():
    """Async function to serve the uvicorn server"""
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        loop="asyncio",  # Use asyncio loop
    )
    server = uvicorn.Server(config)
    await server.serve()

def run_server():
    """Run uvicorn server with ProactorEventLoop"""
    # Verify policy is set
    if sys.platform.startswith("win"):
        policy = asyncio.get_event_loop_policy()
        if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
            print(f"[WARNING] Event loop policy is {type(policy).__name__}, not WindowsProactorEventLoopPolicy!")
        else:
            print(f"[OK] Event loop policy verified: {type(policy).__name__}")
    
    # Use asyncio.run() which will respect the event loop policy we set
    # This ensures ProactorEventLoop is used instead of SelectorEventLoop
    print("[INFO] Starting uvicorn server with ProactorEventLoop support...")
    asyncio.run(serve())

if __name__ == "__main__":
    run_server()

