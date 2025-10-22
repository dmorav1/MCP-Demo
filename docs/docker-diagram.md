# Docker Compose Architecture Diagram - MCP Demo

## Architecture Overview (Mermaid)

```mermaid
graph TB
    subgraph External["External Layer"]
        User[User/Browser]
        SlackAPI[Slack API]
        LogViewer[Log Viewer]
    end

    subgraph DockerNetwork["Docker Network: mcp-network (bridge)"]
        subgraph Frontend["frontend Container"]
            FrontendApp[React App<br/>Port: 3001→3000]
        end

        subgraph Backend["mcp-backend Container"]
            FastAPI[FastAPI REST API<br/>Port: 8000]
            MCPServer[MCP Server]
            EmbeddingService[Embedding Service<br/>local/OpenAI]
            CRUD[CRUD Operations]
        end

        subgraph Database["postgres Container"]
            PostgreSQL[PostgreSQL + pgvector<br/>Port: 5433→5432]
            VectorStore[Vector Store<br/>L2 Distance Search]
            ConvData[Conversations & Chunks]
        end

        subgraph Slack["slackbot Container"]
            SlackBot[Slack Socket Mode<br/>Port: 3000]
            IngestProcessor[Ingest Processor]
        end

        subgraph Logs["dozzle Container"]
            Dozzle[Log Viewer<br/>Port: 9999→8080]
        end
    end

    subgraph ExternalServices["External Services"]
        OpenAI[OpenAI API<br/>Optional]
        DockerSocket[Docker Socket<br/>Read-Only]
    end

    User -->|HTTP :3001| FrontendApp
    LogViewer -->|HTTP :9999| Dozzle
    SlackAPI <-->|WebSocket| SlackBot

    FrontendApp -->|HTTP :8000<br/>API Calls| FastAPI
    SlackBot -->|HTTP :8000<br/>POST /ingest| FastAPI
    
    FastAPI --> MCPServer
    FastAPI --> EmbeddingService
    FastAPI --> CRUD
    
    CRUD -->|SQL Queries<br/>postgresql+psycopg| PostgreSQL
    SlackBot -->|SQL Queries<br/>Direct Write| PostgreSQL
    
    PostgreSQL --> VectorStore
    PostgreSQL --> ConvData
    
    EmbeddingService -.->|Optional<br/>Embedding API| OpenAI
    Dozzle -->|Read Logs| DockerSocket

    classDef frontend fill:#61dafb,stroke:#333,stroke-width:2px,color:#000
    classDef backend fill:#009688,stroke:#333,stroke-width:2px,color:#fff
    classDef database fill:#336791,stroke:#333,stroke-width:2px,color:#fff
    classDef slack fill:#4A154B,stroke:#333,stroke-width:2px,color:#fff
    classDef logs fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff
    classDef external fill:#ffd93d,stroke:#333,stroke-width:2px,color:#000

    class FrontendApp frontend
    class FastAPI,MCPServer,EmbeddingService,CRUD backend
    class PostgreSQL,VectorStore,ConvData database
    class SlackBot,IngestProcessor slack
    class Dozzle logs
    class User,SlackAPI,LogViewer,OpenAI,DockerSocket external
```

## Service Communication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as MCP Backend
    participant P as Postgres
    participant S as Slack API
    participant SB as Slackbot

    Note over P: 1. Startup & Health Checks
    P->>P: Initialize pgvector
    P->>B: Health check passed
    B->>F: Health check passed
    B->>SB: Health check passed

    Note over U,SB: 2. Slack Ingestion Flow
    S->>SB: WebSocket: New messages
    SB->>B: POST /ingest (chunks + metadata)
    B->>B: Generate embeddings (384d→1536d)
    B->>P: INSERT conversations + chunks
    P-->>B: Success
    B-->>SB: Ingestion complete

    Note over U,P: 3. Search Query Flow
    U->>F: Enter search query
    F->>B: GET /search?q=query&top_k=5
    B->>B: Generate query embedding
    B->>P: SELECT with <-> L2 distance
    P-->>B: Ranked results
    B-->>F: JSON response
    F-->>U: Display results

    Note over U,P: 4. MCP Protocol Flow
    U->>B: MCP tool call (stdio)
    B->>B: Parse MCP request
    B->>B: Proxy to FastAPI endpoint
    B->>P: Execute query
    P-->>B: Results
    B-->>U: MCP response
```

## Container Dependencies

```mermaid
graph TD
    A[postgres] -->|healthcheck| B[mcp-backend]
    B -->|healthcheck| C[frontend]
    B -->|healthcheck| D[slackbot]
    E[dozzle] -.->|independent| F[All Containers]

    style A fill:#336791,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#009688,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#61dafb,stroke:#333,stroke-width:2px,color:#000
    style D fill:#4A154B,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#ff6b6b,stroke:#333,stroke-width:2px,color:#fff
```

## Detailed Service Communication

### 1. **postgres** → Base de Datos
- **Imagen**: `pgvector/pgvector:pg15`
- **Puerto**: `5433:5432` (host:container)
- **Función**: Almacenamiento de vectores y datos conversacionales
- **Comunicación**:
  - Recibe conexiones de: `mcp-backend`, `slackbot`
  - Protocolo: PostgreSQL (`postgresql+psycopg://`)

### 2. **mcp-backend** → API Principal
- **Build**: Dockerfile local
- **Puerto**: `8000:8000`
- **Función**: 
  - API REST para operaciones CRUD
  - Servidor MCP (Model Context Protocol)
  - Generación de embeddings (local o OpenAI)
  - Búsqueda semántica con pgvector
- **Comunicación**:
  - **← frontend**: Recibe peticiones HTTP en puerto 8000
  - **← slackbot**: Recibe peticiones HTTP en puerto 8000
  - **→ postgres**: Conecta a postgres:5432 para queries SQL
  - **→ OpenAI API**: (Opcional) Para embeddings si está configurado
- **Dependencias**: Espera a que postgres esté healthy

### 3. **frontend** → Interfaz de Usuario
- **Build**: ./frontend/Dockerfile
- **Puerto**: `3001:3000` (host:container)
- **Función**: Interfaz React para interactuar con el sistema
- **Comunicación**:
  - **← Usuario**: Recibe peticiones del navegador en localhost:3001
  - **→ mcp-backend**: Hace llamadas HTTP a http://localhost:8000
- **Dependencias**: Espera a que mcp-backend esté healthy

### 4. **slackbot** → Integración Slack
- **Build**: ./slack/Dockerfile
- **Puerto**: `3000:3000`
- **Función**: 
  - Recibe mensajes de Slack vía Socket Mode
  - Procesa e ingesta conversaciones
  - Envía respuestas usando embeddings
- **Comunicación**:
  - **← Slack API**: Conexión WebSocket bidireccional
  - **→ mcp-backend**: Llama al endpoint de ingesta http://mcp-backend:8000
  - **→ postgres**: (Directa) Puede escribir datos directamente
  - **→ OpenAI API**: (Opcional) Para embeddings
- **Dependencias**: Espera a que mcp-backend esté healthy

### 5. **dozzle** → Monitoreo de Logs
- **Imagen**: `amir20/dozzle:latest`
- **Puerto**: `9999:8080`
- **Función**: Visualización de logs de todos los contenedores
- **Comunicación**:
  - **← Usuario**: Acceso web en localhost:9999
  - **→ Docker Socket**: Lee logs de /var/run/docker.sock (read-only)

## Main Data Flows

### Flow 1: Slack Ingestion
```mermaid
flowchart LR
    A[Slack API] -->|WebSocket| B[slackbot]
    B -->|HTTP POST /ingest| C[mcp-backend]
    C --> D[ConversationProcessor]
    D --> E[EmbeddingService]
    E -->|SQL INSERT<br/>with vectors| F[(postgres)]
    F --> G[conversations table]
    F --> H[conversation_chunks table]

    style A fill:#4A154B,color:#fff
    style B fill:#4A154B,color:#fff
    style C fill:#009688,color:#fff
    style F fill:#336791,color:#fff
```

### Flow 2: Semantic Search
```mermaid
flowchart LR
    A[User] -->|Search Query| B[Frontend]
    B -->|GET /search?q=query| C[mcp-backend]
    C --> D[Generate Query<br/>Embedding]
    D -->|SQL: SELECT with<br/><-> L2 distance| E[(postgres)]
    E --> F[pgvector Search]
    F -->|Ranked Results| C
    C -->|JSON Response| B
    B -->|Display Results| A

    style A fill:#ffd93d,color:#000
    style B fill:#61dafb,color:#000
    style C fill:#009688,color:#fff
    style E fill:#336791,color:#fff
```

### Flow 3: MCP Operations
```mermaid
flowchart LR
    A[MCP Client<br/>Claude Desktop] -->|MCP Protocol<br/>stdio| B[mcp_server.py]
    B -->|HTTP Proxy| C[FastAPI Endpoints]
    C -->|SQL Queries| D[(postgres)]
    D -->|Results| C
    C -->|Response| B
    B -->|MCP Response| A

    style A fill:#ffd93d,color:#000
    style B fill:#009688,color:#fff
    style C fill:#009688,color:#fff
    style D fill:#336791,color:#fff
```

## Key Environment Variables

| Variable | postgres | mcp-backend | frontend | slackbot | dozzle |
|----------|----------|-------------|----------|----------|--------|
| DATABASE_URL | ❌ | ✅ | ❌ | ✅ | ❌ |
| OPENAI_API_KEY | ❌ | ✅ | ❌ | ✅ | ❌ |
| SLACK_BOT_TOKEN | ❌ | ✅ | ❌ | ✅ | ❌ |
| SLACK_APP_TOKEN | ❌ | ❌ | ❌ | ✅ | ❌ |
| FASTAPI_BASE_URL | ❌ | ✅ | ❌ | ✅ | ❌ |
| REACT_APP_API_URL | ❌ | ❌ | ✅ | ❌ | ❌ |

## Health Checks and Dependencies

```mermaid
graph TD
    P[postgres<br/>Health check every 30s<br/>pg_isready] 
    B[mcp-backend<br/>Health check every 30s<br/>curl /health]
    F[frontend<br/>Health check every 30s<br/>curl localhost:3000]
    S[slackbot<br/>No health check]
    D[dozzle<br/>Independent startup]

    P -->|depends_on:<br/>service_healthy| B
    B -->|depends_on:<br/>service_healthy| F
    B -->|depends_on:<br/>service_healthy| S

    style P fill:#336791,color:#fff
    style B fill:#009688,color:#fff
    style F fill:#61dafb,color:#000
    style S fill:#4A154B,color:#fff
    style D fill:#ff6b6b,color:#fff
```

## Network and Volumes

- **Network**: `mcp-network` (bridge) - All services share this network
- **Volumes**:
  - `postgres_data`: PostgreSQL database persistence
  - Bind mounts: For development (hot reload in frontend and backend)

## Exposed Ports to Host

| Service | Host Port | Container Port | Purpose |
|----------|-------------|------------------|-----------|
| postgres | 5433 | 5432 | PostgreSQL Database |
| mcp-backend | 8000 | 8000 | FastAPI REST API |
| mcp-server | 8001 | 8001 | MCP Server (SSE) |
| frontend | 3001 | 3000 | React Web Interface |
| slackbot | 3000 | 3000 | Slack Webhook (if applicable) |
| dozzle | 9999 | 8080 | Log Viewer |

## Important Notes

1. **Internal Communication**: Services use service names (e.g., `postgres:5432`, `mcp-backend:8000`) within the Docker network.

2. **External Communication**: The host accesses via `localhost` with mapped ports (e.g., `localhost:8000`, `localhost:3001`).

3. **Startup Order**: 
   1. postgres → waits for health check
   2. mcp-backend → waits for postgres healthy
   3. frontend, slackbot, and mcp-server → wait for mcp-backend healthy
   4. dozzle → starts independently

4. **Configuration Redundancy**: Both `mcp-backend` and `slackbot` have direct access to postgres and can generate embeddings.

5. **MCP Server Access**: 
   - **Local stdio mode**: Use `run_mcp_server_standalone.py` directly for Claude Desktop
   - **Network SSE mode**: Docker container exposes port 8001 for remote MCP clients
   - Connect external MCP clients to: `http://localhost:8001/sse`

## Connecting External MCP Clients

### Option 1: Local stdio (Claude Desktop)
```json
{
  "mcpServers": {
    "mcp-demo": {
      "command": "python",
      "args": ["/path/to/MCP-Demo/run_mcp_server_standalone.py"],
      "env": {
        "FASTAPI_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Option 2: Docker SSE (Network Access)
```json
{
  "mcpServers": {
    "mcp-demo": {
      "url": "http://localhost:8001/sse",
      "transport": "sse"
    }
  }
}
```

### Testing MCP Server
```bash
# Check if MCP server is running
curl http://localhost:8001/health

# Test SSE connection
curl -N http://localhost:8001/sse
```

## Architecture Diagram (Complete View)

```mermaid
graph TB
    subgraph External["🌐 External Access"]
        U[👤 User Browser<br/>localhost:3001]
        SA[💬 Slack API<br/>WebSocket]
        LV[📊 Log Viewer<br/>localhost:9999]
    end

    subgraph Network["🐳 Docker Network: mcp-network"]
        subgraph FE["📱 Frontend Container"]
            F[React App<br/>:3001→:3000<br/>REACT_APP_API_URL]
        end

        subgraph BE["🔧 Backend Container"]
            B[FastAPI<br/>:8000<br/>REST API]
            E[Embedding Service<br/>384d→1536d]
        end

        subgraph MCP["🔌 MCP Server Container"]
            M[MCP Server<br/>:8001<br/>SSE Transport]
        end

        subgraph DB["💾 Database Container"]
            P[(PostgreSQL<br/>pgvector<br/>:5433→:5432)]
            V[Vector Index<br/>IVFFlat L2]
        end

        subgraph SB["🤖 Slackbot Container"]
            S[Socket Mode<br/>:3000<br/>Ingest Processor]
        end

        subgraph LOG["📋 Logs Container"]
            D[Dozzle<br/>:9999→:8080]
        end
    end

    subgraph APIs["☁️ External APIs"]
        O[OpenAI API<br/>text-embedding-ada-002]
        DS[Docker Socket<br/>/var/run/docker.sock]
    end

    U -->|HTTP| F
    U -->|SSE :8001| M
    LV -->|HTTP| D
    SA <-->|WS| S

    F -->|HTTP :8000| B
    S -->|POST /ingest| B
    M -->|HTTP Proxy| B
    B --> E
    
    B -->|SQL| P
    S -->|SQL| P
    P --> V

    E -.->|Optional| O
    D -->|RO| DS

    style F fill:#61dafb,stroke:#333,stroke-width:3px,color:#000
    style B fill:#009688,stroke:#333,stroke-width:3px,color:#fff
    style M fill:#8e44ad,stroke:#333,stroke-width:3px,color:#fff
    style P fill:#336791,stroke:#333,stroke-width:3px,color:#fff
    style S fill:#4A154B,stroke:#333,stroke-width:3px,color:#fff
    style D fill:#ff6b6b,stroke:#333,stroke-width:3px,color:#fff
```
