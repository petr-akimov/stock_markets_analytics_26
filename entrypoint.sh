#!/bin/sh
set -e

echo "Starting FastAPI backend on port 8000..."
uvicorn src.app.api:app --host 127.0.0.1 --port 8000 &

echo "Starting Nginx frontend on port 8080..."
exec nginx -g "daemon off;"