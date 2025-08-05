#!/bin/bash

# Development startup script with support for different modes

# Default t    # Activate virtual environment and run with MCP inspector
    source .venv/bin/activate
    
    echo "🚀 Starting MCP Inspector..."
    
    # Use a simple Python script without -m flag to avoid argument parsing issues
    npx @modelcontextprotocol/inspector python3 run_mcp_server.py if no argument is provided
MODE=${1:-all}

setup_env() {
    echo "--- Running Environment Setup ---"
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found. Copying from .env.example..."
        cp .env.example .env
    fi

    if [ ! -d ".venv" ]; then
        echo "🐍 Creating Python virtual environment..."
        uv venv --python 3.11 .venv
    fi

    echo "📦 Syncing dependencies..."
    uv pip install -r requirements.txt
}

start_db() {
    echo "--- Starting Database ---"
    docker-compose up -d postgres
    echo "⏳ Waiting for PostgreSQL to be ready..."
    
    # Retry loop for checking DB connection
    for i in {1..5}; do
        docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Database is ready!"
            return 0
        fi
        echo "DB not ready, waiting... ($i/5)"
        sleep 3
    done

    echo "❌ Database connection failed after several attempts."
    return 1
}

run_server() {
    echo "--- Starting Application Server ---"
    
    # Get port from environment or use default
    PORT=${UVICORN_PORT:-8000}
    
    # Check if database is running
    echo "🔍 Checking database connection..."
    docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Database is not running. Starting database first..."
        start_db
        if [ $? -ne 0 ]; then
            echo "❌ Failed to start database. Exiting."
            exit 1
        fi
    else
        echo "✅ Database connection verified"
    fi
    
    echo "📖 API Docs: http://localhost:${PORT}/docs"
    echo "🏥 Health Check: http://localhost:${PORT}/health"
    echo "🔧 MCP stdio transport: available for MCP inspector"
    
    # Activate virtual environment and run the application
    source .venv/bin/activate
    UVICORN_PORT=${PORT} python -m app.main
}

run_inspector() {
    echo "--- Starting MCP Inspector ---"
    echo "Ensure your database is running first by calling './start-dev.sh setup'"
    echo "🔧 Connecting MCP Inspector to stdio transport..."
    
    # Check if database is running first
    echo "🔍 Checking database connection..."
    docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Database is not running. Please run './start-dev.sh setup' first."
        exit 1
    else
        echo "✅ Database connection verified"
    fi
    
    # Activate virtual environment and run with MCP inspector
    source .venv/bin/activate
    
    echo " Starting MCP Inspector..."
    
    # Try using python3 directly instead of full path, and pass -m and app.main as separate arguments
    npx @modelcontextprotocol/inspector python3 -m app.main
    
    echo ""
    echo "🎉 MCP Inspector should now be running!"
    echo "📝 Look for the URL and auth token in the output above"
    echo "🌐 The inspector will automatically open in your browser"
    echo "⚠️  Keep this terminal open to maintain the connection"
}


# Main logic to select mode
if [ "$MODE" == "setup" ]; then
    setup_env
    start_db
elif [ "$MODE" == "run" ]; then
    run_server
elif [ "$MODE" == "inspect" ]; then
    run_inspector
elif [ "$MODE" == "all" ]; then
    setup_env
    start_db && run_server
else
    echo "Unknown mode: $MODE"
    echo "Usage: ./start-dev.sh [setup|run|inspect|all]"
    echo ""
    echo "Modes:"
    echo "  setup   - Set up environment and start database only"
    echo "  run     - Start the application server (FastAPI + MCP on stdio)"
    echo "  inspect - Start MCP Inspector (requires database to be running)"
    echo "  all     - Set up environment, start database, and run server"
    echo ""
    echo "💡 Tip: Use 'inspect' mode to debug and test your MCP server with a web UI"
    exit 1
fi