#!/usr/bin/env python3
"""
Simple script to run the MCP server without using -m flag
"""
import sys
import os
import asyncio

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Import everything we need from app.main
    from app.main import mcp_app, fastapi_app, logger
    import uvicorn
    
    # Define the same main function as in app.main
    async def main():
        # Configure Uvicorn task
        # Get port from environment or use default
        port = int(os.getenv("UVICORN_PORT", "8000"))
        
        uvicorn_config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=port
        )
        uvicorn_server = uvicorn.Server(uvicorn_config)

        # Configure MCP stdio task
        mcp_stdio_task = mcp_app.run_stdio_async()

        logger.info("🚀 Starting concurrent servers...")
        logger.info(f"   - HTTP API running on http://0.0.0.0:{port} (logs in fastapi_server.log)")
        logger.info("   - MCP server running on stdio")

        # Run both tasks
        await asyncio.gather(
            uvicorn_server.serve(),
            mcp_stdio_task
        )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Shutdown logic from old lifespan
        logger.info("🛑 Application shutdown initiated by user.")
        logger.info("🛑 Application shutdown: Lifespan manager is cleaning up.")
        logger.info("🛑 Application shutdown initiated")
        logger.info("👋 MCP Backend API stopped")
