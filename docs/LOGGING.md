# MCP Backend Logging Guide

This guide explains how to view and manage logs in the MCP Backend application, both in development and Docker container environments.

## 🔧 Logging Configuration

The application uses a comprehensive logging system with the following features:

- **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Multiple output destinations**: Console, files, error-specific files
- **Structured formatting**: Timestamps, module names, function names, line numbers
- **Custom log levels**: API_CALL, DATABASE for specialized tracking

### Log Levels

```python
DEBUG    # Detailed information for debugging
INFO     # General information about program execution  
WARNING  # Something unexpected happened, but still working
ERROR    # A serious problem occurred
CRITICAL # Very serious error occurred
```

### Environment Variables

- `LOG_LEVEL`: Set to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (default: `INFO`)

## 📁 Log File Locations

### In Development
- `logs/mcp-backend.log` - All logs
- `logs/errors.log` - Error logs only

### In Docker Container
- `/app/logs/mcp-backend.log` - All logs
- `/app/logs/errors.log` - Error logs only

## 🐳 Viewing Logs in Docker

### Method 1: Using the Docker Logs Helper Script

```bash
./docker-logs.sh
```

This interactive script provides options to:
1. Show live logs (follow)
2. Show recent logs (last 100 lines)
3. Check log files inside container
4. Access container shell
5. Show all running containers

### Method 2: Docker Commands

```bash
# View live logs
docker logs -f <container_name>

# View recent logs
docker logs --tail 100 <container_name>

# View logs with timestamps
docker logs -f --timestamps <container_name>

# Access container shell
docker exec -it <container_name> /bin/bash

# View log files inside container
docker exec <container_name> cat /app/logs/mcp-backend.log
docker exec <container_name> tail -f /app/logs/mcp-backend.log
```

### Method 3: VS Code Docker Extension

1. Open the Docker extension in VS Code
2. Find your running container under "Containers"
3. Right-click → "View Logs"
4. Logs will open in a new terminal with real-time output

## 📊 Log Format Examples

### Console Output
```
2025-01-29 10:30:15 - app.main - INFO - 🚀 Creating database tables...
2025-01-29 10:30:16 - app.services - INFO - 🔧 Initializing EmbeddingService with model: text-embedding-ada-002
2025-01-29 10:30:17 - app.crud - INFO - 💾 Creating new conversation: Sample Conversation
```

### File Output (Detailed)
```
2025-01-29 10:30:15 | app.main | INFO | startup_event:25 | 🌟 Application startup completed
2025-01-29 10:30:16 | app.services | INFO | __init__:18 | 🔧 Initializing EmbeddingService with model: text-embedding-ada-002
2025-01-29 10:30:17 | app.crud | INFO | create_conversation:23 | 💾 Creating new conversation: Sample Conversation
```

## 🎯 Module-Specific Logging

Each module has detailed logging:

### `app.main` (FastAPI endpoints)
- 📍 Route access
- 📥 Request processing
- ✅ Successful responses
- ❌ Error handling

### `app.services` (Business logic)
- 🔧 Service initialization
- 🔄 Embedding generation
- 📝 Conversation processing
- 🎯 Context formatting

### `app.crud` (Database operations)
- 💾 Creating records
- 🔍 Fetching data
- 🗑️ Deleting records
- 🗃️ Search operations

### `app.database` (Database configuration)
- 🔧 Configuration loading
- 🔌 Connection management
- 📊 Settings validation

## 🧪 Testing Logging

Run the logging test script:

```bash
python test_logging.py
```

This will:
1. Test different log levels
2. Check log file creation
3. Test API endpoints (if server is running)

## 🚨 Common Issues

### Logs Not Appearing in Docker

1. **Check container is running**:
   ```bash
   docker ps
   ```

2. **Verify log level**:
   ```bash
   docker exec <container> env | grep LOG_LEVEL
   ```

3. **Check log directory permissions**:
   ```bash
   docker exec <container> ls -la /app/logs/
   ```

### No Log Files Created

1. **Directory permissions**: Ensure the application can write to the log directory
2. **Environment variables**: Check that `LOG_LEVEL` is set correctly
3. **Container filesystem**: Verify the container has writable filesystem

### High Volume of Logs

1. **Adjust log level**: Set `LOG_LEVEL=WARNING` or `LOG_LEVEL=ERROR`
2. **Filter logs**: Use grep to filter specific log messages
   ```bash
   docker logs <container> | grep "ERROR"
   ```

## 📈 Log Monitoring

### Real-time Monitoring
```bash
# Follow all logs
docker logs -f <container>

# Follow only errors
docker logs -f <container> 2>&1 | grep "ERROR\\|CRITICAL"

# Follow API calls
docker logs -f <container> 2>&1 | grep "📍\\|📥\\|🔍"
```

### Log Analysis
```bash
# Count error types
docker logs <container> 2>&1 | grep "ERROR" | cut -d'|' -f3 | sort | uniq -c

# View recent embedding operations
docker logs <container> 2>&1 | grep "🔄.*embedding" | tail -10

# Monitor database operations
docker logs <container> 2>&1 | grep "💾\\|🗑️\\|🔍" | tail -20
```

## 🔧 Customizing Logs

### Change Log Level at Runtime
Set environment variable before starting container:
```bash
export LOG_LEVEL=DEBUG
docker-compose up
```

### Custom Log Formatting
Modify `app/logging_config.py` to change log formats or add new handlers.

### Adding New Log Messages
Use the centralized logger in your modules:
```python
from app.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Your message here")
```

## 📝 Log Message Emoji Guide

- 🚀 Startup/initialization
- ✅ Success operations
- ❌ Errors
- ⚠️ Warnings
- 🔧 Configuration
- 📍 API endpoints
- 📥 Incoming requests
- 🔍 Search operations
- 💾 Database writes
- 🗑️ Delete operations
- 🔄 Processing operations
- 📊 Data/metrics
- 🎯 Business logic
- 🐳 Docker-related
- 🔌 Connections
