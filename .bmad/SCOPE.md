Current:
- Connecting to claude desktop using connectors.
- Ingesting slack channel and saving it to vector database (PG Vector). [Not ingesting threads, just plain messages]
- Naive RAG.
- Local environment using OpenAI API for embeddings.
- Reading slack channel every 2 minutes.
- Slack free tier level.
- No authentication for MCP connection.
- Api keys configured through .env file.
- Custom WebUI to interact with the MCP to replace Claude desktop in the future.

Next steps:
- Deploy LLM in Bedrock (on-premise) - Spike + implementation.
- Integrate On-premise LLM to the current flow.
- Add basic authentication to MCP server.
- Improve or change the WebUI.