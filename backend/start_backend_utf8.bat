@echo off
REM Start backend with UTF-8 encoding to fix Crawl4AI Windows console issues
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set NO_COLOR=1
set TERM=dumb

cd /d %~dp0
REM Use custom server script to ensure ProactorEventLoop is used
..\aigov_env\Scripts\python.exe run_server.py

