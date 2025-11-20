#!/bin/bash
# Start script for backend

echo "Starting AI Governance Platform Backend..."
echo "Make sure Qdrant is running on http://localhost:6333"
echo ""

uvicorn app.main:app --reload --port 8000

