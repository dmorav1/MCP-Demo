#!/bin/bash

# Development startup script with support for different modes

# Default to 'all' if no argument is provided
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
    echo "📖 API Docs: http://localhost:8000/docs"
    echo "🏥 Health Check: http://localhost:8000/health"
    echo "🔧 MCP stdio transport: available for MCP inspector"
    uv run python -m app.main
}

run_inspector() {
    echo "--- Starting MCP Inspector ---"
    echo "Ensure your database is running first by calling './start-dev.sh setup'"
    echo "🔧 Connecting MCP Inspector to stdio transport..."
    # NEW - Tell the inspector to run the app as a module
    npx @modelcontextprotocol/inspector uv run python -m app.main
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
    exit 1
fi