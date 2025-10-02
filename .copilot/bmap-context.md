# BMAP Method Context for AI Assistants

## Business Layer

**Primary Use Cases:**
- Customer support teams searching historical conversations for solutions
- Product managers analyzing feature discussions from Slack channels  
- Documentation teams extracting knowledge from informal conversations
- Training AI agents with context from past team interactions

**Key Metrics:**
- Search relevance accuracy (similarity scores)
- Ingestion throughput (conversations/minute)
- Query response time (<200ms target)
- Context recall for AI agent responses

## Mapping Layer

**User Journeys:**
1. **Support Agent**: Query issue → Search similar conversations → Find resolution pattern
2. **Product Manager**: Analyze feature feedback → Search related discussions → Extract insights
3. **AI Agent**: Receive user question → Search context → Provide informed response

**Data Dependencies:**
- Slack workspace access (Socket Mode API)
- OpenAI/Local embedding models for semantic search
- PostgreSQL with pgvector for similarity queries

## Architecture Layer

**System Boundaries:**
- **Ingestion**: Slack → FastAPI (`/ingest`) → PostgreSQL
- **Search**: Query → Embedding → Vector Search → Ranked Results
- **Integration**: MCP Protocol → External AI Agents

**Critical Design Decisions:**
- Vector dimension standardization (1536d) for embedding compatibility
- Chunking strategy balancing context preservation vs. search granularity
- Dual embedding support (local vs. cloud) for deployment flexibility

## Process Layer

**Development Workflow:**
```bash
# Feature development cycle
./start-dev.sh setup     # Environment + DB
# Code changes with GitHub Copilot assistance
pytest tests/           # Validation
./start-dev.sh inspect  # MCP integration testing
```

**Operational Processes:**
- Continuous Slack ingestion via background worker
- Vector index maintenance for search performance
- Embedding model updates and migration procedures

## AI Assistant Prompts

**For GitHub Copilot Chat:**
- "Given this BMAP context, suggest improvements to search relevance"
- "How can I optimize the ingestion process for high-volume Slack channels?"
- "What monitoring should I add to track the key business metrics?"