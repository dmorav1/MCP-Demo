#!/bin/bash

# Development startup script with support for different modes

# Default if no argument is provided
MODE=${1:-all}

setup_env() {
    echo "--- Running Environment Setup ---" >> setup.log
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found. Copying from .env.example..." >> setup.log
        cp .env.example .env
    fi

    if [ ! -d ".venv" ]; then
        echo "🐍 Creating Python virtual environment..." >> setup.log
        uv venv --python 3.11 .venv >> setup.log
    fi

    echo "📦 Syncing dependencies..." >> setup.log
    uv pip install -q -r requirements.txt
}

start_db() {
    echo "--- Starting Database ---" >> setup.log
    docker-compose up -d postgres >> setup.log
    echo "⏳ Waiting for PostgreSQL to be ready..." >> setup.log

    # Retry loop for checking DB connection
    for i in {1..5}; do
        docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Database is ready!" >> setup.log
            return 0
        fi
        echo "DB not ready, waiting... ($i/5)" >> setup.log
        sleep 3
    done

    echo "❌ Database connection failed after several attempts." >> setup.log
    return 1
}

run_server() {
    echo "--- Starting Application Servers ---" >> server.log
    
    # Get port from environment or use default
    PORT=${UVICORN_PORT:-8000}
    
    # Check if database is running
    echo "🔍 Checking database connection..." >> server.log
    docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Database is not running. Starting database first..." >> server.log
        start_db
        if [ $? -ne 0 ]; then
            echo "❌ Failed to start database. Exiting." >> server.log
            exit 1
        fi
    else
        echo "✅ Database connection verified" >> server.log
    fi

    echo "📖 API Docs: http://localhost:${PORT}/docs" >> server.log
    echo "🏥 Health Check: http://localhost:${PORT}/health" >> server.log
    echo "🔧 MCP server: available via stdio transport" >> server.log
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Start FastAPI server in background
    echo "🚀 Starting FastAPI server..." >> server.log
    UVICORN_PORT=${PORT} python -m app.main &
    FASTAPI_PID=$!
    
    # Wait a moment for FastAPI to start
    sleep 2
    
    # Start MCP server
    echo "🚀 Starting MCP server..." >> server.log
    FASTAPI_BASE_URL="http://localhost:${PORT}" python run_mcp_server_standalone.py &
    MCP_PID=$!
    
    # Function to cleanup both processes on exit
    cleanup() {
        echo "🛑 Shutting down servers..."
        if [ ! -z "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID 2>/dev/null
        fi
        if [ ! -z "$MCP_PID" ]; then
            kill $MCP_PID 2>/dev/null
        fi
        echo "👋 All servers stopped" 
        exit 0
    }
    
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM >> server.log

    echo "✅ Both servers are running!" >> server.log
    echo "   - FastAPI server PID: $FASTAPI_PID" >> server.log
    echo "   - MCP server PID: $MCP_PID" >> server.log
    echo "⚠️  Press Ctrl+C to stop both servers" >> server.log

    # Wait for processes to finish
    wait
}

run_mcp_server() {

    CURRENT_DIR=$(pwd)
    cd $CURRENT_DIR

    if [ ! -d ".venv" ]; then
        uv venv --python 3.11 .venv
    fi

    uv pip install -q -r $CURRENT_DIR/requirements.txt

    PORT=${UVICORN_PORT:-8000}
    
    # Activate virtual environment
    source .venv/bin/activate

    FASTAPI_BASE_URL="http://localhost:${PORT}" python $CURRENT_DIR/run_mcp_server_standalone.py &
    MCP_PID=$!
    
    # Function to cleanup both processes on exit
    cleanup() {
        if [ ! -z "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID 2>/dev/null
        fi
        if [ ! -z "$MCP_PID" ]; then
            kill $MCP_PID 2>/dev/null
        fi
        exit 0
    }
    
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM

}

run_inspector() {
    echo "--- Starting MCP Inspector ---" >> inspector.log
    echo "Ensure your database is running first by calling './start-dev.sh setup'" >> inspector.log
    echo "🔧 Connecting MCP Inspector to standalone MCP server..." >> inspector.log

    # Check if database is running first
    echo "🔍 Checking database connection..." >> inspector.log
    docker-compose exec postgres psql -U mcp_user -d mcp_db -c "SELECT 1;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ Database is not running. Please run './start-dev.sh setup' first." >> inspector.log
        exit 1
    else
        echo "✅ Database connection verified" >> inspector.log
    fi
    
    # Check if FastAPI server is running
    echo "🔍 Checking if FastAPI server is running..." >> inspector.log
    PORT=${UVICORN_PORT:-8000}
    curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ FastAPI server is not running. Starting it..." >> inspector.log
        # Activate virtual environment and start FastAPI in background
        source .venv/bin/activate
        UVICORN_PORT=${PORT} python -m app.main &
        FASTAPI_PID=$!
        echo "⏳ Waiting for FastAPI server to start..." >> inspector.log
        sleep 3
        
        # Verify it started
        curl -s "http://localhost:${PORT}/health" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "❌ Failed to start FastAPI server." >> inspector.log
            exit 1
        fi
        echo "✅ FastAPI server started (PID: $FASTAPI_PID)" >> inspector.log
    else
        echo "✅ FastAPI server is already running" >> inspector.log
    fi
    
    # Activate virtual environment and run with MCP inspector
    source .venv/bin/activate

    echo "🚀 Starting MCP Inspector..." >> inspector.log

    # Use the standalone MCP server runner
    FASTAPI_BASE_URL="http://localhost:${PORT}" npx @modelcontextprotocol/inspector uv run run_mcp_server_standalone.py

    echo "" >> inspector.log
    echo "🎉 MCP Inspector should now be running!" >> inspector.log
    echo "📝 Look for the URL and auth token in the output above" >> inspector.log
    echo "🌐 The inspector will automatically open in your browser" >> inspector.log
    echo "⚠️  Keep this terminal open to maintain the connection" >> inspector.log
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
elif [ "$MODE" == "mcp_run" ]; then
    run_mcp_server
else
    echo "Unknown mode: $MODE"
    echo "Usage: ./start-dev.sh [setup|run|inspect|all]"
    echo ""
    echo "Modes:"
    echo "  setup   - Set up environment and start database only"
    echo "  run     - Start both FastAPI and MCP servers concurrently"
    echo "  inspect - Start MCP Inspector (requires database and FastAPI server)"
    echo "  all     - Set up environment, start database, and run both servers"
    echo ""
    echo "💡 Tip: Use 'inspect' mode to debug and test your MCP server with a web UI"
    exit 1
fi