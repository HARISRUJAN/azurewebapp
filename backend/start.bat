@echo off
REM Start script for backend (Windows)

echo Starting AI Governance Platform Backend...
echo Make sure Qdrant is running on http://localhost:6333
echo.

REM Use custom server script to ensure ProactorEventLoop is used
python run_server.py

