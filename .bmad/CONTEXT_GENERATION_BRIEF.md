# BRIEF: Application Context Generation

## 1. Your Role
Act as a **Senior Software Architect**. Your task is to perform a comprehensive analysis of this entire application codebase.

## 2. Your Mission
Your primary mission is to understand the complete context of this application by reading all the files and code within this workspace. After your analysis, you must synthesize this information into a new, detailed technical documentation file.

## 3. The Deliverable
You will create a new file named **`TECHNICAL_CONTEXT.md`** in the .bmad/ directory. This file must be well-structured and contain the following sections:

-   **`## 1. High-Level Application Purpose`**
    -   Describe what this application does from a user's perspective. What problem does it solve?

-   **`## 2. Technology Stack`**
    -   List the key languages, frameworks, libraries, and databases used in each service (frontend, backend, mcp-server, db).

-   **`## 3. Service Breakdown & Responsibilities`**
    -   For each container (`frontend-service`, `backend-service`, `db-service`, `mcp-server`), detail its specific role and primary responsibilities within the application.

-   **`## 4. Core Data Flow`**
    -   Explain the end-to-end data flow. Start from how data is ingested from Slack, how it's processed and stored by the backend and database, and finally, how a user's query from the frontend retrieves a solution.

-   **`## 5. Local Setup and Execution`**
    -   Based on the `docker-compose.yml`, `.env` files, and any other configuration, provide a clear, step-by-step guide on how a new developer would set up and run this project locally.

-   **`## 6. Key Files and Entrypoints`**
    -   Identify and list the most important files or entry points for each service (e.g., `app.py`, `server.js`, `main.py`).

## 4. Instructions
-   Begin by confirming you have read these instructions.
-   Perform the analysis.
-   Create the `TECHNICAL_CONTEXT.md` file with the content you've generated.
-   Notify me upon completion.