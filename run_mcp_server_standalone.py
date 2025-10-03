#!/usr/bin/env python3
"""
Standalone script to run the MCP server with stdio transport support.
This script imports and runs the MCP server defined in app/mcp_server.py.
"""

import asyncio
import sys
import os

# Add the current directory to Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mcp_server import mcp_app

if __name__ == "__main__":
    print("🚀 Starting MCP server with stdio transport")
    try:
        # Run the MCP server using stdio transport (FastMCP default)
        mcp_app.run()
    except KeyboardInterrupt:
        print("🛑 MCP server shutdown initiated by user")
    except Exception as e:
        print(f"❌ Error running MCP server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)