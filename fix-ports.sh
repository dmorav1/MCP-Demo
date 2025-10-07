#!/bin/bash
// filepath: fix-ports.sh

echo "🔧 Checking and fixing port conflicts..."

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    
    if [ -n "$pid" ]; then
        echo "⚠️  Port $port is in use by PID $pid"
        read -p "Kill process on port $port? (y/n): " answer
        
        if [ "$answer" = "y" ]; then
            kill -9 $pid
            echo "✅ Killed process on port $port"
        else
            echo "⏭️  Skipping port $port"
        fi
    else
        echo "✅ Port $port is available"
    fi
}

# Check critical ports
kill_port 5433  # PostgreSQL
kill_port 8000  # FastAPI Backend
kill_port 3001  # Frontend

echo ""
echo "✅ Port check complete"