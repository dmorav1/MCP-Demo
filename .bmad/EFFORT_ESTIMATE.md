# Effort Estimate: AI Knowledge Base Application

## 1. Estimation Methodology
This document breaks down the required work into Epics and Tasks. The effort for each task is estimated using three metrics:
-   **Story Points:** A relative measure of complexity, uncertainty, and effort (using a modified Fibonacci sequence: 1, 2, 3, 5, 8, 13).
-   **Estimated Hours (Range):** A rough time-based estimate to provide a general idea for planning (e.g., 4-6 hours).
-   **Confidence:** A percentage indicating how confident we are in the estimate (e.g., 90%).

---

## 2. High-Level Summary
| Epic / Component | Total Story Points | Total Estimated Hours |
| :--------------- | :----------------- | :-------------------- |
| Backend Service  | `[Sum]`            | `[Sum]`               |
| Frontend Service | `[Sum]`            | `[Sum]`               |
| Database & Infra | `[Sum]`            | `[Sum]`               |
| MCP Server       | `[Sum]`            | `[Sum]`               |
| **Grand Total** | **`[Grand Total]`**| **`[Grand Total]`** |

---

## 3. Detailed Breakdown

### ### Epic 1: Backend Service (`backend-service`)
| ID      | Task / User Story                                          | Story Pts | Hours (Range) | Confidence | Notes                               |
| :------ | :--------------------------------------------------------- | :-------- | :------------ | :--------- | :---------------------------------- |
| BE-01   | Setup FastAPI app with basic routing & config              | 2         | 3-5           | 95%        | Pydantic settings, main.py          |
| BE-02   | Implement `ConversationCRUD` module for database operations| 5         | 8-12          | 90%        | Create, Read, Update, Delete logic  |
| BE-03   | Develop `EmbeddingService` for local & OpenAI providers    | 8         | 12-16         | 85%        | Requires handling external API keys |
| BE-04   | Create `/ingest` endpoint and `ConversationProcessor`      | 5         | 8-12          | 90%        | Includes text chunking logic        |
| BE-05   | Implement `/search` endpoint with pgvector similarity      | 5         | 6-10          | 90%        | L2 distance operator `<->`          |
| BE-06   | Implement Slack ingestion module                           | 8         | 16-24         | 80%        | Depends on Slack SDK complexity     |
| BE-07   | Write unit and integration tests for all endpoints         | 13        | 20-30         | 85%        | Use `httpx` for async testing       |

### ### Epic 2: Frontend Service (`frontend-service`)
| ID      | Task / User Story                                          | Story Pts | Hours (Range) | Confidence | Notes                               |
| :------ | :--------------------------------------------------------- | :-------- | :------------ | :--------- | :---------------------------------- |
| FE-01   | Setup React project with TypeScript & basic layout         | 3         | 4-6           | 95%        | CRA or Vite setup                   |
| FE-02   | Create a component for displaying conversation lists       | 3         | 4-8           | 90%        | Fetches from `/conversations`       |
| FE-03   | Develop the main search/chat interface component           | 8         | 12-16         | 85%        | State management for queries/results|
| FE-04   | Integrate Axios for all backend API communication          | 2         | 3-5           | 95%        | Centralized API service module      |

### ### Epic 3: Database & DevOps/Infrastructure
| ID      | Task / User Story                                          | Story Pts | Hours (Range) | Confidence | Notes                               |
| :------ | :--------------------------------------------------------- | :-------- | :------------ | :--------- | :---------------------------------- |
| DB-01   | Define SQLAlchemy models for `Conversation` & `Chunk`      | 3         | 4-6           | 95%        | `models.py` with vector type        |
| DB-02   | Create `init-db.sql` for `pgvector` extension              | 1         | 1-2           | 100%       |                                     |
| DevOps-01 | Write `docker-compose.yml` for all services              | 5         | 6-10          | 90%        | Includes networking, volumes, health  |
| DevOps-02 | Create Dockerfiles for each service                      | 5         | 8-12          | 90%        | Multi-stage builds for optimization |
| DevOps-03 | Implement structured logging across all services         | 3         | 4-8           | 90%        | Centralized `logging_config.py`     |

### ### Epic 4: MCP Server (`mcp-server`)
| ID      | Task / User Story                                          | Story Pts | Hours (Range) | Confidence | Notes                                   |
| :------ | :--------------------------------------------------------- | :-------- | :------------ | :--------- | :-------------------------------------- |
| MCP-01  | Develop MCP server logic to wrap FastAPI endpoints         | 5         | 8-12          | 85%        | `app/mcp_server.py`                     |
| MCP-02  | Create standalone bootstrap script for MCP server          | 2         | 2-4           | 90%        | `run_mcp_server_standalone.py`          |

---

## 4. Assumptions & Risks
### Assumptions
-   The core logic for `pgvector` similarity search is performant enough for the initial user load.
-   Required API keys (OpenAI, Slack) will be available during development.
-   The frontend design is straightforward and doesn't require complex state management.

### Risks
-   **Slack API Rate Limiting:** The ingestion process might be slower than anticipated due to Slack's API limits, requiring a more complex queuing system (Risk: Medium).
-   **Embedding Model Performance:** The chosen `sentence-transformers` model may not provide the desired search relevance, requiring experimentation with other models (Risk: Low).