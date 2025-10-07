#!/bin/bash
// filepath: fix-docker-daemon.sh

echo "🔧 Checking Docker daemon..."

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker daemon is not running"
    echo ""
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "📱 macOS detected"
        echo "   Opening Docker Desktop..."
        open -a Docker
        echo "   Waiting for Docker to start..."
        
        for i in {1..30}; do
            if docker info >/dev/null 2>&1; then
                echo "✅ Docker is now running"
                exit 0
            fi
            sleep 2
            echo -n "."
        done
        
        echo ""
        echo "❌ Docker failed to start. Please start Docker Desktop manually."
        exit 1
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🐧 Linux detected"
        echo "   Starting Docker service..."
        sudo systemctl start docker
        
        if docker info >/dev/null 2>&1; then
            echo "✅ Docker is now running"
        else
            echo "❌ Failed to start Docker. Try: sudo systemctl status docker"
            exit 1
        fi
    else
        echo "❓ Unknown OS. Please start Docker manually."
        exit 1
    fi
else
    echo "✅ Docker daemon is running"
fi