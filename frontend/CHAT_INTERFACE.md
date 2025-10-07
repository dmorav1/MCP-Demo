# Chat Interface - Claude Desktop Alternative

## Overview

This web-based chat interface replaces Claude Desktop, providing direct access to your MCP server with LLM-powered responses based on historical Slack conversations.

## Features

- **Real-time Chat**: Ask questions and get instant responses
- **Context-Aware**: Automatically searches historical conversations for relevant context
- **Transparent**: Shows which past conversations informed the response
- **Standalone**: No dependency on Claude Desktop

## Quick Start

### 1. Start All Services

```bash
# Set environment variables
export OPENAI_API_KEY=your-key-here

# Start everything
docker-compose up -d

# Verify services
docker-compose ps
```

### 2. Access the Chat Interface

Open your browser to: **http://localhost:3001**

### 3. Ask Questions

Examples:
- "How do I fix blank text issues?"
- "What are common database connection problems?"
- "Show me solutions for API timeout errors"

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser   │────▶│  Chat API    │────▶│ MCP Backend  │
│  (React)    │◀────│  (FastAPI)   │◀────│ (Search)     │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │   OpenAI     │
                    │     LLM      │
                    └──────────────┘
```

## API Endpoints

### POST /chat/ask
Ask a question with conversation history

```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "content": "How do I fix connection errors?",
    "conversation_history": []
  }'
```

### WebSocket /chat/ws
Real-time streaming chat (for advanced implementations)

### GET /chat/conversations
Browse all stored conversations

## Development

### Run Frontend Locally

```bash
cd frontend
npm install
npm start
```

### Run Backend Locally

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## Troubleshooting

### "OpenAI API key not configured"
- Set `OPENAI_API_KEY` in `.env` file
- Restart services: `docker-compose restart mcp-backend`

### No context found
- Ensure conversations are ingested: `curl http://localhost:8000/conversations`
- Check embedding generation: `docker-compose logs mcp-backend | grep embedding`

### Frontend not loading
- Check frontend logs: `docker-compose logs frontend`
- Verify CORS settings in [`app/main.py`](app/main.py)
- Ensure port 3001 is not in use

## Customization

### Change LLM Model
Edit [`app/mcp_gateway.py`](app/mcp_gateway.py):
```python
model="gpt-4-turbo-preview"  # or "gpt-3.5-turbo" for faster/cheaper
```

### Adjust Context Window
```python
context = await search_mcp_context(query, top_k=10)  # Increase for more context
```

### Modify UI Theme
Edit [`frontend/src/App.css`](frontend/src/App.css) color scheme

## Production Deployment

1. **Build optimized frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Serve with nginx** or deploy to Vercel/Netlify

3. **Configure environment:**
   - Set production `REACT_APP_API_URL`
   - Enable HTTPS for API
   - Set proper CORS origins

4. **Monitor usage:**
   - Track OpenAI API costs
   - Monitor response times
   - Log user interactions

## Comparison with Claude Desktop

| Feature | Claude Desktop | This Solution |
|---------|---------------|---------------|
| Deployment | Desktop app required | Web browser only |
| Customization | Limited | Full control |
| Branding | Claude branding | Your branding |
| Cost | Per-user license | OpenAI API usage |
| Integration | MCP protocol | Direct HTTP/WebSocket |
| Hosting | Local only | Can deploy anywhere |

## Next Steps

- [ ] Add user authentication
- [ ] Implement conversation persistence
- [ ] Add file upload for context
- [ ] Create mobile-responsive design
- [ ] Add analytics dashboard
- [ ] Implement feedback mechanisms