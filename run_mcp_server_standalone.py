#!/usr/bin/env python3
"""
Standalone script to run the MCP server.
This script imports and runs the MCP server defined in app/mcp_server.py.
"""

import asyncio
import sys
import os

# Add the current directory to Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mcp_server import mcp_app

if __name__ == "__main__":
    try:
        # Run the MCP server using stdio transport
        mcp_app.run()
    except KeyboardInterrupt:
        print("🛑 MCP server shutdown initiated by user")
    except Exception as e:
        print(f"❌ Error running MCP server: {e}")
        sys.exit(1)