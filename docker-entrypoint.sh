#!/bin/bash

# Docker entrypoint script to support multiple modes
# Usage: docker run image [fastapi|mcp]

MODE=${1:-fastapi}

case "$MODE" in
    "fastapi")
        echo "🚀 Starting FastAPI server..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
        ;;
    "mcp")
        echo "🔧 Starting MCP server..."
        # Set default FastAPI base URL if not provided
        export FASTAPI_BASE_URL=${FASTAPI_BASE_URL:-http://host.docker.internal:8000}
        echo "Using FastAPI base URL: $FASTAPI_BASE_URL"
        exec python run_mcp_server_standalone.py
        ;;
    *)
        echo "❌ Unknown mode: $MODE"
        echo "Available modes: fastapi, mcp"
        exit 1
        ;;
esac