#!/bin/bash

# Docker Container Logging Helper Script
# This script helps you view and manage logs in your Docker container

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 MCP Backend Docker Logging Helper${NC}"
echo "======================================"

# Function to show container logs
show_logs() {
    echo -e "${GREEN}📋 Showing container logs...${NC}"
    echo "Use Ctrl+C to stop following logs"
    echo ""
    
    # Try to find the container by name pattern
    CONTAINER_ID=$(docker ps --filter "name=mcp" --format "{{.ID}}" | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        CONTAINER_ID=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
    fi
    
    if [ -z "$CONTAINER_ID" ]; then
        echo -e "${RED}❌ Could not find MCP backend container${NC}"
        echo "Available containers:"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
        return 1
    fi
    
    echo -e "${BLUE}📦 Container ID: $CONTAINER_ID${NC}"
    echo ""
    
    # Follow logs with timestamps
    docker logs -f --timestamps $CONTAINER_ID
}

# Function to show recent logs
show_recent_logs() {
    echo -e "${GREEN}📋 Showing recent container logs (last 100 lines)...${NC}"
    
    CONTAINER_ID=$(docker ps --filter "name=mcp" --format "{{.ID}}" | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        CONTAINER_ID=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
    fi
    
    if [ -z "$CONTAINER_ID" ]; then
        echo -e "${RED}❌ Could not find MCP backend container${NC}"
        return 1
    fi
    
    docker logs --tail 100 --timestamps $CONTAINER_ID
}

# Function to show log files inside container
show_log_files() {
    echo -e "${GREEN}📁 Checking log files inside container...${NC}"
    
    CONTAINER_ID=$(docker ps --filter "name=mcp" --format "{{.ID}}" | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        CONTAINER_ID=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
    fi
    
    if [ -z "$CONTAINER_ID" ]; then
        echo -e "${RED}❌ Could not find MCP backend container${NC}"
        return 1
    fi
    
    echo "Checking for log files in /app/logs..."
    docker exec $CONTAINER_ID ls -la /app/logs/ 2>/dev/null || echo "No /app/logs directory found"
    
    echo ""
    echo "Checking for log files in /logs..."
    docker exec $CONTAINER_ID ls -la /logs/ 2>/dev/null || echo "No /logs directory found"
}

# Function to access container shell
access_shell() {
    echo -e "${GREEN}🐚 Accessing container shell...${NC}"
    
    CONTAINER_ID=$(docker ps --filter "name=mcp" --format "{{.ID}}" | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        CONTAINER_ID=$(docker ps --filter "name=backend" --format "{{.ID}}" | head -1)
    fi
    
    if [ -z "$CONTAINER_ID" ]; then
        echo -e "${RED}❌ Could not find MCP backend container${NC}"
        return 1
    fi
    
    echo "Type 'exit' to leave the container shell"
    docker exec -it $CONTAINER_ID /bin/bash
}

# Main menu
echo "What would you like to do?"
echo "1) Show live logs (follow)"
echo "2) Show recent logs (last 100 lines)"
echo "3) Check log files inside container"
echo "4) Access container shell"
echo "5) Show all running containers"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        show_logs
        ;;
    2)
        show_recent_logs
        ;;
    3)
        show_log_files
        ;;
    4)
        access_shell
        ;;
    5)
        echo -e "${BLUE}🐳 Running containers:${NC}"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        ;;
    *)
        echo -e "${YELLOW}⚠️ Invalid choice. Please run the script again.${NC}"
        ;;
esac
