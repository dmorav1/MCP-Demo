# MCP Server Migration: From FastMCP to Standard MCP

This document explains the specific changes made to migrate from the `fastmcp` approach to the standard MCP server implementation.

## The Problem

During Docker implementation, we discovered that the MCP package installed via pip (`mcp==1.1.1`) doesn't include the `fastmcp` module that was being imported:

```python
# This import failed:
from mcp.server.fastmcp import FastMCP, Context
```

**Error:** `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`

## Investigation Process

### Step 1: Explore Available MCP Modules
```bash
# Check what's actually available in the MCP package
docker run --rm --entrypoint python mcp-demo-mcp-backend:latest -c "import mcp; print(dir(mcp))"

# Result: No 'fastmcp' found, but 'server' and 'stdio_server' were available
```

### Step 2: Examine MCP Server Structure
```bash
# Check server module contents
docker run --rm --entrypoint python mcp-demo-mcp-backend:latest -c "import mcp.server; print(dir(mcp.server))"

# Found: Server, stdio_server, etc.
```

### Step 3: Check Documentation
- The official MCP specification uses the standard server interface
- `fastmcp` appears to be a convenience wrapper that may not be available in all versions

## Migration Strategy

### Before: FastMCP Approach
```python
from mcp.server.fastmcp import FastMCP, Context

# Initialize app
mcp_app = FastMCP(name="mcp-demo")

# Define tools with decorators
@mcp_app.tool()
async def search_conversations(query: str, top_k: int = 5) -> dict:
    """Search for conversations."""
    # Implementation
    return {"results": [...]}

# Run the app
if __name__ == "__main__":
    mcp_app.run()
```

### After: Standard MCP Server
```python
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

# Initialize server
server = Server("mcp-demo")

# Define tool list
@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="search_conversations",
            description="Search for conversations using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        )
    ]

# Handle tool calls
@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name == "search_conversations":
        result = await search_conversations(**arguments)
        return [TextContent(type="text", text=f"Results: {result}")]

# Main function
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Differences Explained

### 1. Tool Registration

**FastMCP (Before):**
```python
@mcp_app.tool()
async def search_conversations(query: str, top_k: int = 5) -> dict:
    # Function signature defines the tool schema automatically
    pass
```

**Standard MCP (After):**
```python
# Explicit tool definition
@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [Tool(name="search_conversations", inputSchema={...})]

# Separate tool execution
@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    # Route to appropriate function based on name
    pass
```

**Why this change:**
- **Explicit Control**: More control over tool schemas
- **Flexibility**: Can modify schemas without changing function signatures
- **Standard Compliance**: Uses official MCP protocol

### 2. Response Format

**FastMCP (Before):**
```python
async def search_conversations(query: str) -> dict:
    return {"results": [...], "count": 5}  # Return any JSON-serializable object
```

**Standard MCP (After):**
```python
async def search_conversations(query: str) -> List[TextContent]:
    result = {"results": [...], "count": 5}
    return [TextContent(type="text", text=f"Results: {result}")]  # Must return TextContent
```

**Why this change:**
- **Protocol Compliance**: MCP protocol expects TextContent responses
- **Consistency**: All tools return the same response type
- **Future-Proof**: Supports rich content types (text, images, etc.)

### 3. Server Initialization

**FastMCP (Before):**
```python
mcp_app = FastMCP(name="mcp-demo")
# ... define tools ...
mcp_app.run()  # Simple one-line startup
```

**Standard MCP (After):**
```python
server = Server("mcp-demo")
# ... define handlers ...

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

asyncio.run(main())  # Explicit async handling
```

**Why this change:**
- **Transport Control**: Explicit control over stdio transport
- **Async Proper**: Proper async/await handling
- **Flexibility**: Can easily switch to other transports (HTTP, WebSocket)

### 4. Error Handling

**FastMCP (Before):**
```python
@mcp_app.tool()
async def search_conversations(query: str) -> dict:
    try:
        # ... implementation ...
        return result
    except Exception as e:
        return {"error": str(e)}  # Return error in response
```

**Standard MCP (After):**
```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        if name == "search_conversations":
            return await search_conversations(**arguments)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]  # Error as TextContent
```

**Why this change:**
- **Centralized Handling**: All errors handled in one place
- **Consistent Format**: All errors return as TextContent
- **Better Debugging**: Can add logging and monitoring

## Benefits of the Migration

### 1. **Compatibility**
- Works with standard MCP package installations
- No dependency on potentially unstable wrapper libraries
- Compatible with official MCP tools and clients

### 2. **Control**
- Explicit tool schema definition
- Fine-grained control over tool behavior
- Better error handling and logging

### 3. **Maintainability**
- Follows official MCP patterns
- Easier to understand and modify
- Better alignment with MCP documentation

### 4. **Future-Proof**
- Uses stable, official APIs
- Easy to extend with new MCP features
- Supports rich content types

## Lessons Learned

### 1. **Verify Package Contents**
Always check what's actually available in installed packages:
```bash
python -c "import package; print(dir(package))"
```

### 2. **Use Official APIs**
Prefer official, documented APIs over convenience wrappers that may not be universally available.

### 3. **Check Multiple Sources**
- Package documentation
- Official specifications
- Community examples
- Source code

### 4. **Plan for Migration**
When using newer or convenience APIs, have a fallback plan for standard implementations.

## Testing the Migration

### Before Migration
```bash
# This would fail:
python app/mcp_server.py
# ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

### After Migration
```bash
# This works:
python run_mcp_server_standalone.py
# 🔧 Starting MCP server...

# Can receive and respond to MCP protocol messages
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | python run_mcp_server_standalone.py
```

## Conclusion

The migration from FastMCP to standard MCP server was necessary for:
- **Compatibility** with standard MCP package installations
- **Reliability** using official, stable APIs
- **Docker support** ensuring the service works in containerized environments

While it required more verbose code, the standard approach provides better control, reliability, and future compatibility.