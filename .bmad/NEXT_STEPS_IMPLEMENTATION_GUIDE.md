# Next Steps Implementation Guide

## Executive Summary

This document provides a comprehensive roadmap for implementing the **"Next steps"** outlined in the [SCOPE.md](./SCOPE.md) file. These enhancements will transform the current proof-of-concept into a production-ready, secure, and fully on-premise AI-powered knowledge base system.

### Current State (Baseline)
✅ MCP server connecting to Claude Desktop  
✅ Slack channel ingestion to PostgreSQL + pgvector  
✅ Naive RAG implementation  
✅ Local embeddings using OpenAI API  
✅ Custom WebUI (React frontend)  
✅ 2-minute polling cycle for Slack  
✅ Unauthenticated MCP connections  

### Target State (After Implementation)
🎯 On-premise LLM deployed on AWS Bedrock  
🎯 Zero external API dependencies (OpenAI replaced)  
🎯 Authenticated and secure MCP server  
🎯 Enhanced, production-ready WebUI  
🎯 Full observability and monitoring  

---

## Table of Contents

1. [Next Step 1: Deploy LLM in Bedrock (On-Premise)](#next-step-1-deploy-llm-in-bedrock-on-premise)
2. [Next Step 2: Integrate On-Premise LLM to Current Flow](#next-step-2-integrate-on-premise-llm-to-current-flow)
3. [Next Step 3: Add Basic Authentication to MCP Server](#next-step-3-add-basic-authentication-to-mcp-server)
4. [Next Step 4: Improve or Change the WebUI](#next-step-4-improve-or-change-the-webui)
5. [Implementation Sequence & Dependencies](#implementation-sequence--dependencies)
6. [Risk Assessment & Mitigation](#risk-assessment--mitigation)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Plan](#rollback-plan)

---

## Next Step 1: Deploy LLM in Bedrock (On-Premise)

### 🎯 Objective
Deploy a Large Language Model on AWS Bedrock to replace external OpenAI dependencies, enabling full on-premise control over embeddings and text generation.

### 📋 Prerequisites
- AWS account with Bedrock access enabled
- IAM roles/policies for Bedrock API access
- Understanding of Bedrock model provisioning
- Budget approval for Bedrock usage (provisioned throughput vs. on-demand)

### 🏗️ Architecture Changes

#### Current Architecture
```
Slack Messages → FastAPI (/ingest) → OpenAI Embeddings API → PostgreSQL
                                   ↓
User Query → FastAPI (/search) → OpenAI Embeddings API → pgvector similarity
```

#### Target Architecture
```
Slack Messages → FastAPI (/ingest) → AWS Bedrock Embeddings → PostgreSQL
                                   ↓
User Query → FastAPI (/search) → AWS Bedrock Embeddings → pgvector similarity
                                   ↓
Chat/Answer → AWS Bedrock LLM (Titan, Claude, etc.)
```

### 📝 Implementation Tasks

#### Task 1.1: AWS Bedrock Setup (Spike Phase)
**Effort:** 2-3 days | **Confidence:** 70% (dependent on AWS account setup)

1. **Enable Bedrock in AWS Console:**
   - Navigate to AWS Bedrock service
   - Request model access for desired models:
     - **Embeddings:** Amazon Titan Embeddings G1 - Text
     - **Text Generation:** Amazon Titan Text Premier, Claude 3 (Anthropic), or Llama 3
   - Note: Model access can take 24-48 hours for approval

2. **IAM Configuration:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": [
           "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
           "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*"
         ]
       }
     ]
   }
   ```

3. **Test Bedrock Connectivity:**
   ```python
   # test_bedrock.py
   import boto3
   import json
   
   bedrock_runtime = boto3.client(
       service_name='bedrock-runtime',
       region_name='us-east-1'
   )
   
   # Test embedding
   body = json.dumps({
       "inputText": "Hello world"
   })
   
   response = bedrock_runtime.invoke_model(
       modelId='amazon.titan-embed-text-v1',
       body=body
   )
   
   embedding = json.loads(response['body'].read())
   print(f"Embedding dimension: {len(embedding['embedding'])}")
   ```

4. **Cost Analysis:**
   - Document costs for:
     - Embedding generation (per 1k tokens)
     - LLM inference (per 1k input/output tokens)
     - Provisioned throughput vs. on-demand pricing
   - Compare with current OpenAI costs

**Deliverables:**
- [ ] AWS Bedrock account configured
- [ ] IAM roles and policies created
- [ ] Model access granted for selected models
- [ ] Cost comparison report (Bedrock vs. OpenAI)
- [ ] Spike report documenting findings and recommendations

#### Task 1.2: Create Bedrock Integration Module
**Effort:** 3-4 days | **Confidence:** 85%

1. **Create `app/providers/bedrock.py`:**
   ```python
   """
   AWS Bedrock provider for embeddings and text generation.
   """
   import boto3
   import json
   from typing import List, Optional
   from app.logging_config import get_logger
   from app.config import settings
   
   logger = get_logger(__name__)
   
   class BedrockProvider:
       """AWS Bedrock client for embeddings and LLM inference."""
       
       def __init__(
           self,
           region_name: str = "us-east-1",
           embedding_model_id: str = "amazon.titan-embed-text-v1",
           llm_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
       ):
           self.bedrock_runtime = boto3.client(
               service_name='bedrock-runtime',
               region_name=region_name
           )
           self.embedding_model_id = embedding_model_id
           self.llm_model_id = llm_model_id
           logger.info(f"🔧 Initialized Bedrock provider: {region_name}")
       
       async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
           """Generate embeddings for a list of texts."""
           embeddings = []
           
           for text in texts:
               body = json.dumps({"inputText": text})
               
               response = self.bedrock_runtime.invoke_model(
                   modelId=self.embedding_model_id,
                   body=body
               )
               
               result = json.loads(response['body'].read())
               embeddings.append(result['embedding'])
               
           logger.info(f"✅ Generated {len(embeddings)} embeddings via Bedrock")
           return embeddings
       
       async def generate_text(
           self,
           prompt: str,
           max_tokens: int = 2000,
           temperature: float = 0.7
       ) -> str:
           """Generate text using Bedrock LLM."""
           body = json.dumps({
               "anthropic_version": "bedrock-2023-05-31",
               "max_tokens": max_tokens,
               "temperature": temperature,
               "messages": [
                   {
                       "role": "user",
                       "content": prompt
                   }
               ]
           })
           
           response = self.bedrock_runtime.invoke_model(
               modelId=self.llm_model_id,
               body=body
           )
           
           result = json.loads(response['body'].read())
           return result['content'][0]['text']
   ```

2. **Update `app/config.py`:**
   ```python
   class AppSettings(BaseSettings):
       # ... existing settings ...
       
       # Bedrock Configuration
       aws_region: str = "us-east-1"
       bedrock_embedding_model: str = "amazon.titan-embed-text-v1"
       bedrock_llm_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
       
       # Provider selection
       embedding_provider: str = "local"  # Options: local, openai, bedrock
       llm_provider: str = "bedrock"  # Options: openai, bedrock
   ```

3. **Update `app/services.py` to support Bedrock:**
   ```python
   class EmbeddingService:
       def __init__(self):
           self.provider = settings.embedding_provider
           
           if self.provider == "bedrock":
               from app.providers.bedrock import BedrockProvider
               self.bedrock = BedrockProvider()
           # ... existing openai and local setup ...
       
       async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
           if self.provider == "bedrock":
               return await self.bedrock.generate_embeddings(texts)
           # ... existing logic ...
   ```

**Deliverables:**
- [ ] `app/providers/bedrock.py` created and tested
- [ ] Configuration updated to support Bedrock
- [ ] Unit tests for Bedrock integration
- [ ] Documentation for Bedrock setup

#### Task 1.3: Vector Dimension Migration
**Effort:** 2-3 days | **Confidence:** 90%

**⚠️ Important:** Amazon Titan Embeddings produce **1024-dimensional** vectors, not 1536. This requires a database migration.

1. **Create Alembic migration:**
   ```bash
   alembic revision -m "change_embedding_dimension_to_1024"
   ```

2. **Migration script:**
   ```python
   # alembic/versions/xxx_change_embedding_dimension_to_1024.py
   def upgrade():
       # Drop existing index
       op.execute("DROP INDEX IF EXISTS conversation_chunks_embedding_idx")
       
       # Alter column type
       op.execute("""
           ALTER TABLE conversation_chunks 
           ALTER COLUMN embedding TYPE vector(1024)
       """)
       
       # Recreate index
       op.execute("""
           CREATE INDEX conversation_chunks_embedding_idx 
           ON conversation_chunks 
           USING ivfflat (embedding vector_l2_ops) 
           WITH (lists = 100)
       """)
   
   def downgrade():
       # Rollback logic
       pass
   ```

3. **Update configuration:**
   ```python
   # .env
   EMBEDDING_DIMENSION=1024
   EMBEDDING_PROVIDER=bedrock
   ```

**Deliverables:**
- [ ] Database migration created and tested
- [ ] Existing embeddings regenerated with Bedrock (or data purged)
- [ ] Migration documentation

---

## Next Step 2: Integrate On-Premise LLM to Current Flow

### 🎯 Objective
Replace OpenAI's GPT models with AWS Bedrock LLMs for chat/answer generation, ensuring RAG pipeline uses the on-premise model.

### 📋 Prerequisites
- Step 1 completed (Bedrock deployed and accessible)
- Chat endpoint exists (`/chat/ask` via `app/mcp_gateway.py`)

### 🏗️ Architecture Changes

#### Current Flow
```
User Query → /chat/ask → OpenAI GPT-4 → Response
              ↓
         Vector Search (context retrieval)
```

#### Target Flow
```
User Query → /chat/ask → AWS Bedrock LLM → Response
              ↓
         Vector Search (Bedrock embeddings for context)
```

### 📝 Implementation Tasks

#### Task 2.1: Create LLM Service Layer
**Effort:** 2-3 days | **Confidence:** 90%

1. **Create `app/services/llm_service.py`:**
   ```python
   """
   LLM service for chat/answer generation.
   Supports multiple providers: OpenAI, Bedrock.
   """
   from typing import List, Dict, Optional
   from app.logging_config import get_logger
   from app.config import settings
   
   logger = get_logger(__name__)
   
   class LLMService:
       """Unified interface for LLM inference."""
       
       def __init__(self):
           self.provider = settings.llm_provider
           
           if self.provider == "bedrock":
               from app.providers.bedrock import BedrockProvider
               self.bedrock = BedrockProvider()
           elif self.provider == "openai":
               from openai import AsyncOpenAI
               self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
       
       async def generate_answer(
           self,
           query: str,
           context_chunks: List[Dict],
           conversation_history: Optional[List[Dict]] = None
       ) -> str:
           """
           Generate an answer using retrieved context and conversation history.
           """
           # Build RAG prompt
           context_text = "\n\n".join([
               f"[Source: {chunk['scenario_title']}]\n{chunk['chunk_text']}"
               for chunk in context_chunks
           ])
           
           system_prompt = f"""You are a technical support assistant. 
Use the following conversation history to answer the user's question:

{context_text}

Provide accurate, helpful answers based on the context above."""
           
           if self.provider == "bedrock":
               full_prompt = f"{system_prompt}\n\nUser: {query}\n\nAssistant:"
               return await self.bedrock.generate_text(
                   prompt=full_prompt,
                   max_tokens=2000,
                   temperature=0.7
               )
           
           elif self.provider == "openai":
               messages = [{"role": "system", "content": system_prompt}]
               
               if conversation_history:
                   messages.extend(conversation_history)
               
               messages.append({"role": "user", "content": query})
               
               response = await self.openai_client.chat.completions.create(
                   model="gpt-4",
                   messages=messages
               )
               return response.choices[0].message.content
   ```

2. **Update `app/mcp_gateway.py` (or create if missing):**
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from sqlalchemy.orm import Session
   from app.database import get_db
   from app import crud, schemas
   from app.services.llm_service import LLMService
   
   router = APIRouter(prefix="/chat")
   llm_service = LLMService()
   
   @router.post("/ask", response_model=schemas.ChatResponse)
   async def ask_question(
       request: schemas.ChatRequest,
       db: Session = Depends(get_db)
   ):
       """
       Answer a question using RAG with on-premise LLM.
       """
       # 1. Retrieve relevant context
       search_results = await crud.search_conversations(
           db, 
           query=request.content, 
           top_k=5
       )
       
       # 2. Generate answer using LLM
       answer = await llm_service.generate_answer(
           query=request.content,
           context_chunks=[r.model_dump() for r in search_results],
           conversation_history=request.conversation_history
       )
       
       return schemas.ChatResponse(
           answer=answer,
           context_used=search_results
       )
   ```

3. **Add schemas in `app/schemas.py`:**
   ```python
   class ChatRequest(BaseModel):
       content: str
       conversation_history: Optional[List[Dict[str, str]]] = None
   
   class ChatResponse(BaseModel):
       answer: str
       context_used: List[SearchResult]
   ```

**Deliverables:**
- [ ] `LLMService` created with multi-provider support
- [ ] `/chat/ask` endpoint updated to use Bedrock
- [ ] Unit tests for LLM service
- [ ] Integration tests for RAG pipeline

#### Task 2.2: Update MCP Server for Chat
**Effort:** 1-2 days | **Confidence:** 95%

1. **Add chat tool to `app/mcp_server.py`:**
   ```python
   @mcp_app.tool()
   async def ask_question(
       context: Context,
       query: str,
       conversation_history: Optional[List[Dict]] = None
   ) -> dict:
       """
       Ask a question and get an AI-generated answer using RAG.
       """
       await context.info(f"❓ [MCP] Asking question: '{query}'")
       
       async with httpx.AsyncClient() as client:
           response = await client.post(
               f"{FASTAPI_BASE_URL}/chat/ask",
               json={"content": query, "conversation_history": conversation_history}
           )
           response.raise_for_status()
           return response.json()
   ```

**Deliverables:**
- [ ] MCP chat tool implemented
- [ ] Claude Desktop integration tested
- [ ] Documentation updated

---

## Next Step 3: Add Basic Authentication to MCP Server

### 🎯 Objective
Implement authentication for the MCP server to prevent unauthorized access, supporting both API key-based and JWT token authentication.

### 📋 Prerequisites
- Understanding of FastAPI security middleware
- Decision on authentication strategy (API keys, JWT, OAuth2)

### 🏗️ Security Architecture

#### Recommended Approach: API Key + Optional JWT

```
Client (Claude Desktop) → [API Key Header] → MCP Server → FastAPI Backend
                              ↓ (validates)
                         auth_middleware.py
```

### 📝 Implementation Tasks

#### Task 3.1: Implement API Key Authentication
**Effort:** 2-3 days | **Confidence:** 90%

1. **Create `app/middleware/auth.py`:**
   ```python
   """
   Authentication middleware for MCP server and FastAPI.
   """
   from fastapi import Security, HTTPException, status
   from fastapi.security import APIKeyHeader
   from typing import Optional
   from app.config import settings
   from app.logging_config import get_logger
   
   logger = get_logger(__name__)
   
   API_KEY_NAME = "X-MCP-API-Key"
   api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
   
   async def verify_api_key(api_key: Optional[str] = Security(api_key_header)):
       """
       Verify the API key from request headers.
       """
       if not settings.require_authentication:
           return True  # Auth disabled for development
       
       if api_key is None:
           logger.warning("⚠️ Missing API key in request")
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Missing API key"
           )
       
       # Validate against configured keys (stored in .env or secrets manager)
       valid_keys = settings.mcp_api_keys.split(",")
       
       if api_key not in valid_keys:
           logger.warning(f"❌ Invalid API key attempt: {api_key[:8]}...")
           raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail="Invalid API key"
           )
       
       logger.info(f"✅ Valid API key authenticated")
       return True
   ```

2. **Update `app/config.py`:**
   ```python
   class AppSettings(BaseSettings):
       # ... existing settings ...
       
       # Authentication
       require_authentication: bool = True
       mcp_api_keys: str = ""  # Comma-separated API keys
       jwt_secret_key: Optional[str] = None
       jwt_algorithm: str = "HS256"
       jwt_expiration_minutes: int = 60
   ```

3. **Protect MCP endpoints in `app/main.py`:**
   ```python
   from app.middleware.auth import verify_api_key
   
   @app.get("/search", dependencies=[Depends(verify_api_key)])
   async def search_conversations(...):
       # ... existing code ...
   
   @app.post("/ingest", dependencies=[Depends(verify_api_key)])
   async def ingest_conversation(...):
       # ... existing code ...
   ```

4. **Update Claude Desktop configuration:**
   ```json
   {
     "mcpServers": {
       "mcp-conversational-data": {
         "command": "docker",
         "args": [
           "exec",
           "mcp-server",
           "python",
           "-m",
           "app.mcp_server"
         ],
         "env": {
           "FASTAPI_BASE_URL": "http://localhost:8000",
           "MCP_API_KEY": "your-secure-api-key-here"
         }
       }
     }
   }
   ```

5. **Generate secure API keys:**
   ```python
   # scripts/generate_api_key.py
   import secrets
   
   def generate_api_key(length: int = 32) -> str:
       """Generate a cryptographically secure API key."""
       return secrets.token_urlsafe(length)
   
   if __name__ == "__main__":
       print(f"Generated API Key: {generate_api_key()}")
   ```

**Deliverables:**
- [ ] API key authentication middleware implemented
- [ ] Configuration for enabling/disabling auth
- [ ] API key generation script
- [ ] Documentation for key management
- [ ] Tests for authentication flows

#### Task 3.2: Add JWT Token Authentication (Optional)
**Effort:** 3-4 days | **Confidence:** 85%

1. **Create `app/routers/auth.py`:**
   ```python
   """
   Authentication endpoints for JWT token generation.
   """
   from fastapi import APIRouter, Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
   from datetime import datetime, timedelta
   import jwt
   from app.config import settings
   from app.logging_config import get_logger
   
   logger = get_logger(__name__)
   router = APIRouter(prefix="/auth", tags=["authentication"])
   
   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
   
   @router.post("/token")
   async def login(form_data: OAuth2PasswordRequestForm = Depends()):
       """
       Generate JWT token for authenticated users.
       """
       # Validate credentials (implement user database check)
       if not validate_user(form_data.username, form_data.password):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Incorrect username or password"
           )
       
       # Generate token
       token_data = {
           "sub": form_data.username,
           "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
       }
       
       token = jwt.encode(
           token_data,
           settings.jwt_secret_key,
           algorithm=settings.jwt_algorithm
       )
       
       return {"access_token": token, "token_type": "bearer"}
   
   async def get_current_user(token: str = Depends(oauth2_scheme)):
       """Validate JWT token and extract user."""
       try:
           payload = jwt.decode(
               token,
               settings.jwt_secret_key,
               algorithms=[settings.jwt_algorithm]
           )
           username: str = payload.get("sub")
           if username is None:
               raise HTTPException(status_code=401, detail="Invalid token")
           return username
       except jwt.ExpiredSignatureError:
           raise HTTPException(status_code=401, detail="Token expired")
       except jwt.JWTError:
           raise HTTPException(status_code=401, detail="Invalid token")
   ```

**Deliverables:**
- [ ] JWT token generation endpoint
- [ ] Token validation middleware
- [ ] User database (optional, can use static config initially)
- [ ] Documentation for JWT workflow

#### Task 3.3: Security Hardening
**Effort:** 2 days | **Confidence:** 95%

1. **Add rate limiting:**
   ```python
   # app/middleware/rate_limit.py
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/ingest")
   @limiter.limit("10/minute")
   async def ingest_conversation(...):
       # ... existing code ...
   ```

2. **Add HTTPS/TLS configuration:**
   - Update docker-compose to use SSL certificates
   - Configure nginx as reverse proxy with SSL termination

3. **Implement request logging:**
   ```python
   # Log all authenticated requests
   logger.info(f"🔐 Request: {request.method} {request.url} - User: {current_user}")
   ```

**Deliverables:**
- [ ] Rate limiting implemented
- [ ] HTTPS/TLS configuration guide
- [ ] Security audit log
- [ ] Penetration testing report

---

## Next Step 4: Improve or Change the WebUI

### 🎯 Objective
Enhance the React frontend to provide a production-ready, user-friendly interface with better UX, error handling, and features.

### 📋 Current State Assessment

**Existing Frontend (frontend/src/App.tsx):**
- ✅ Basic chat interface
- ✅ Context display (collapsible)
- ✅ Message history
- ⚠️ Limited error handling
- ⚠️ No loading states for slow operations
- ⚠️ No conversation persistence
- ⚠️ No user authentication UI
- ⚠️ Basic styling

### 🏗️ Proposed Improvements

#### UI/UX Enhancements
1. **Material-UI or Tailwind CSS integration** for professional styling
2. **Real-time status indicators** (typing, searching, processing)
3. **Multi-conversation management** (save, load, delete conversations)
4. **Advanced search filters** (date range, author, relevance threshold)
5. **Export functionality** (conversation history to PDF/JSON)
6. **Dark mode toggle**

#### Technical Improvements
1. **State management** (Redux Toolkit or Zustand)
2. **React Query** for data fetching and caching
3. **Error boundaries** and fallback UI
4. **Progressive Web App (PWA)** support
5. **WebSocket support** for real-time updates

### 📝 Implementation Tasks

#### Task 4.1: Design System & Component Library
**Effort:** 3-4 days | **Confidence:** 90%

1. **Install Material-UI:**
   ```bash
   cd frontend
   npm install @mui/material @mui/icons-material @emotion/react @emotion/styled
   ```

2. **Create theme configuration:**
   ```typescript
   // src/theme.ts
   import { createTheme } from '@mui/material/styles';
   
   export const lightTheme = createTheme({
     palette: {
       mode: 'light',
       primary: {
         main: '#1976d2',
       },
       secondary: {
         main: '#dc004e',
       },
     },
   });
   
   export const darkTheme = createTheme({
     palette: {
       mode: 'dark',
       primary: {
         main: '#90caf9',
       },
       secondary: {
         main: '#f48fb1',
       },
     },
   });
   ```

3. **Create reusable components:**
   ```
   src/components/
   ├── Layout/
   │   ├── Header.tsx
   │   ├── Sidebar.tsx
   │   └── Footer.tsx
   ├── Chat/
   │   ├── MessageList.tsx
   │   ├── MessageBubble.tsx
   │   ├── InputBox.tsx
   │   └── TypingIndicator.tsx
   ├── Search/
   │   ├── SearchBar.tsx
   │   ├── SearchFilters.tsx
   │   └── SearchResults.tsx
   └── Common/
       ├── LoadingSpinner.tsx
       ├── ErrorBoundary.tsx
       └── ToastNotification.tsx
   ```

**Deliverables:**
- [ ] Material-UI integrated
- [ ] Theme system (light/dark mode)
- [ ] Component library documented in Storybook
- [ ] Design tokens (colors, spacing, typography)

#### Task 4.2: State Management & Data Fetching
**Effort:** 3-4 days | **Confidence:** 85%

1. **Install Redux Toolkit and React Query:**
   ```bash
   npm install @reduxjs/toolkit react-redux @tanstack/react-query
   ```

2. **Create Redux store:**
   ```typescript
   // src/store/index.ts
   import { configureStore } from '@reduxjs/toolkit';
   import chatReducer from './chatSlice';
   import authReducer from './authSlice';
   
   export const store = configureStore({
     reducer: {
       chat: chatReducer,
       auth: authReducer,
     },
   });
   
   export type RootState = ReturnType<typeof store.getState>;
   export type AppDispatch = typeof store.dispatch;
   ```

3. **Create chat slice:**
   ```typescript
   // src/store/chatSlice.ts
   import { createSlice, PayloadAction } from '@reduxjs/toolkit';
   
   interface ChatState {
     conversations: Conversation[];
     activeConversationId: string | null;
     messages: Message[];
   }
   
   const initialState: ChatState = {
     conversations: [],
     activeConversationId: null,
     messages: [],
   };
   
   export const chatSlice = createSlice({
     name: 'chat',
     initialState,
     reducers: {
       addMessage: (state, action: PayloadAction<Message>) => {
         state.messages.push(action.payload);
       },
       // ... other reducers
     },
   });
   ```

4. **Create API query hooks:**
   ```typescript
   // src/hooks/useChat.ts
   import { useMutation, useQuery } from '@tanstack/react-query';
   import { apiClient } from '../api/client';
   
   export const useSearchConversations = (query: string, topK: number) => {
     return useQuery({
       queryKey: ['search', query, topK],
       queryFn: () => apiClient.search(query, topK),
       enabled: query.length > 0,
     });
   };
   
   export const useSendMessage = () => {
     return useMutation({
       mutationFn: (message: ChatRequest) => apiClient.askQuestion(message),
       onSuccess: (data) => {
         // Update cache or state
       },
     });
   };
   ```

**Deliverables:**
- [ ] Redux store configured
- [ ] React Query integrated
- [ ] Custom hooks for API interactions
- [ ] Optimistic updates for better UX

#### Task 4.3: Advanced Features
**Effort:** 5-7 days | **Confidence:** 75%

1. **Multi-conversation management:**
   ```typescript
   // src/components/Sidebar/ConversationList.tsx
   const ConversationList = () => {
     const { conversations, loading } = useConversations();
     
     return (
       <List>
         {conversations.map((conv) => (
           <ListItem key={conv.id}>
             <ListItemText 
               primary={conv.title}
               secondary={conv.lastMessage}
             />
             <IconButton onClick={() => deleteConversation(conv.id)}>
               <DeleteIcon />
             </IconButton>
           </ListItem>
         ))}
       </List>
     );
   };
   ```

2. **Advanced search with filters:**
   ```typescript
   interface SearchFilters {
     dateRange?: { start: Date; end: Date };
     authors?: string[];
     minRelevance?: number;
   }
   
   const SearchPage = () => {
     const [filters, setFilters] = useState<SearchFilters>({});
     
     return (
       <>
         <SearchFilterPanel filters={filters} onChange={setFilters} />
         <SearchResults query={query} filters={filters} />
       </>
     );
   };
   ```

3. **Export functionality:**
   ```typescript
   // src/utils/export.ts
   export const exportToPDF = async (conversation: Conversation) => {
     const { jsPDF } = await import('jspdf');
     const doc = new jsPDF();
     
     doc.text(conversation.title, 10, 10);
     conversation.messages.forEach((msg, idx) => {
       doc.text(`${msg.role}: ${msg.content}`, 10, 20 + idx * 10);
     });
     
     doc.save(`conversation-${conversation.id}.pdf`);
   };
   ```

4. **Authentication UI:**
   ```typescript
   // src/components/Auth/LoginForm.tsx
   const LoginForm = () => {
     const { mutate: login, isLoading } = useLogin();
     
     const handleSubmit = (e: React.FormEvent) => {
       e.preventDefault();
       login({ username, password });
     };
     
     return (
       <form onSubmit={handleSubmit}>
         <TextField label="Username" value={username} onChange={...} />
         <TextField label="Password" type="password" value={password} onChange={...} />
         <Button type="submit" disabled={isLoading}>Login</Button>
       </form>
     );
   };
   ```

**Deliverables:**
- [ ] Conversation management UI
- [ ] Advanced search filters
- [ ] Export to PDF/JSON
- [ ] Authentication UI
- [ ] User settings panel

#### Task 4.4: Error Handling & Monitoring
**Effort:** 2-3 days | **Confidence:** 90%

1. **Error boundary:**
   ```typescript
   // src/components/ErrorBoundary.tsx
   class ErrorBoundary extends React.Component<Props, State> {
     componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
       // Log to monitoring service (e.g., Sentry)
       console.error('Error:', error, errorInfo);
     }
     
     render() {
       if (this.state.hasError) {
         return <ErrorFallback />;
       }
       return this.props.children;
     }
   }
   ```

2. **Toast notifications:**
   ```typescript
   // src/components/ToastProvider.tsx
   import { Snackbar, Alert } from '@mui/material';
   
   export const useToast = () => {
     const showSuccess = (message: string) => {
       // Display success toast
     };
     
     const showError = (message: string) => {
       // Display error toast
     };
     
     return { showSuccess, showError };
   };
   ```

3. **Monitoring integration:**
   ```typescript
   // src/monitoring/sentry.ts
   import * as Sentry from "@sentry/react";
   
   Sentry.init({
     dsn: process.env.REACT_APP_SENTRY_DSN,
     environment: process.env.NODE_ENV,
   });
   ```

**Deliverables:**
- [ ] Error boundary implemented
- [ ] Toast notification system
- [ ] Monitoring/logging integration
- [ ] User-friendly error messages

---

## Implementation Sequence & Dependencies

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Set up Bedrock and core infrastructure

```mermaid
graph LR
    A[Task 1.1: Bedrock Setup] --> B[Task 1.2: Bedrock Integration]
    B --> C[Task 1.3: Vector Migration]
    C --> D[Task 2.1: LLM Service]
```

**Dependencies:**
- AWS account access
- Bedrock model approval
- Database migration approval

**Risks:**
- Bedrock model access delays
- Vector dimension migration complexity

### Phase 2: Integration (Weeks 3-4)
**Goal:** Integrate Bedrock into existing flow

```mermaid
graph LR
    A[Task 2.1: LLM Service] --> B[Task 2.2: MCP Chat]
    B --> C[End-to-end testing]
```

**Dependencies:**
- Phase 1 completed
- Test data available

**Risks:**
- Performance degradation
- Cost overruns

### Phase 3: Security (Weeks 5-6)
**Goal:** Implement authentication and security hardening

```mermaid
graph LR
    A[Task 3.1: API Key Auth] --> B[Task 3.2: JWT Auth]
    B --> C[Task 3.3: Security Hardening]
```

**Dependencies:**
- Security policy approval
- Key management strategy

**Risks:**
- Breaking existing integrations
- Complexity in key rotation

### Phase 4: Frontend Enhancement (Weeks 7-9)
**Goal:** Deliver production-ready WebUI

```mermaid
graph LR
    A[Task 4.1: Design System] --> B[Task 4.2: State Management]
    B --> C[Task 4.3: Advanced Features]
    C --> D[Task 4.4: Error Handling]
```

**Dependencies:**
- Design approval
- API authentication complete

**Risks:**
- Scope creep
- Performance issues with large datasets

### Parallel Tracks
- **Weeks 1-4:** Backend team works on Bedrock integration
- **Weeks 3-6:** Security team works on authentication
- **Weeks 5-9:** Frontend team works on UI enhancements

---

## Risk Assessment & Mitigation

### High-Risk Items

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Bedrock model access delay | Medium | High | Start approval process immediately; have fallback to OpenAI |
| Vector dimension migration data loss | Low | Critical | Full database backup; test migration on staging |
| Authentication breaks existing clients | Medium | High | Feature flag for auth; gradual rollout |
| Frontend performance degradation | Medium | Medium | Implement virtualization for large lists; optimize queries |
| Cost overrun with Bedrock | Medium | Medium | Set up billing alerts; implement usage monitoring |

### Medium-Risk Items

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Bedrock API rate limiting | Medium | Medium | Implement request queuing; cache embeddings |
| JWT token management complexity | Low | Medium | Use established libraries; clear documentation |
| Browser compatibility issues | Low | Low | Use Babel/polyfills; test on major browsers |

---

## Testing Strategy

### Unit Testing
```bash
# Backend
pytest tests/ --cov=app --cov-report=html

# Frontend
npm test -- --coverage
```

### Integration Testing
```python
# tests/test_bedrock_integration.py
async def test_bedrock_embedding_generation():
    """Test Bedrock embedding generation end-to-end."""
    service = EmbeddingService()
    embeddings = await service.generate_embeddings(["test text"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 1024  # Bedrock dimension

async def test_bedrock_rag_pipeline():
    """Test full RAG pipeline with Bedrock."""
    # Ingest test data
    # Perform search
    # Generate answer
    # Validate response
```

### Load Testing
```bash
# Use Locust for load testing
locust -f tests/locustfile.py --host=http://localhost:8000
```

### Security Testing
- **OWASP ZAP** for vulnerability scanning
- **Penetration testing** by security team
- **API key rotation testing**

---

## Rollback Plan

### Bedrock Integration Rollback
```yaml
# .env rollback configuration
EMBEDDING_PROVIDER=openai  # Revert to OpenAI
LLM_PROVIDER=openai
```

**Steps:**
1. Update `.env` to use OpenAI
2. Restart services: `docker-compose restart`
3. No database changes needed if using 1536-d vectors

### Authentication Rollback
```yaml
# .env
REQUIRE_AUTHENTICATION=false
```

**Steps:**
1. Disable authentication via config
2. Remove API key headers from clients
3. Redeploy without auth middleware

### Frontend Rollback
```bash
# Revert to previous version
git checkout tags/v1.0.0 frontend/
docker-compose build frontend
docker-compose up -d frontend
```

---

## Success Criteria

### Next Step 1 (Bedrock Deployment)
✅ Bedrock models accessible via API  
✅ Cost analysis completed and approved  
✅ Spike report delivered  
✅ Integration tests passing  

### Next Step 2 (LLM Integration)
✅ RAG pipeline using Bedrock  
✅ Chat endpoint functional  
✅ Performance meets SLA (<2s response time)  
✅ Zero OpenAI API calls  

### Next Step 3 (Authentication)
✅ API key authentication enforced  
✅ No unauthorized access in logs  
✅ Key rotation process documented  
✅ Security audit passed  

### Next Step 4 (WebUI)
✅ User satisfaction survey >4/5  
✅ Page load time <1s  
✅ Zero critical bugs in production  
✅ Accessibility score >90 (Lighthouse)  

---

## Appendix

### A. Configuration Reference

#### Complete `.env` Example
```bash
# Database
DATABASE_URL=postgresql+psycopg://mcp_user:mcp_password@postgres:5432/mcp_db

# AWS Bedrock
AWS_REGION=us-east-1
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1
BEDROCK_LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0

# Provider Selection
EMBEDDING_PROVIDER=bedrock
LLM_PROVIDER=bedrock
EMBEDDING_DIMENSION=1024

# Authentication
REQUIRE_AUTHENTICATION=true
MCP_API_KEYS=key1_abc123,key2_def456
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_EXPIRATION_MINUTES=60

# Slack (Optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_CHANNEL=technical-support

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

### B. Useful Commands

```bash
# Generate API key
python scripts/generate_api_key.py

# Test Bedrock connectivity
python scripts/test_bedrock.py

# Run database migration
alembic upgrade head

# Regenerate all embeddings
python scripts/regenerate_embeddings.py --provider bedrock

# Backup database
docker exec mcp-postgres pg_dump -U mcp_user mcp_db > backup.sql

# Monitor API usage
docker-compose logs -f --tail=100 mcp-backend
```

### C. Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Material-UI Documentation](https://mui.com/)
- [React Query](https://tanstack.com/query/latest)

---

## Conclusion

This implementation guide provides a comprehensive roadmap for achieving all four "Next steps" outlined in the SCOPE.md. The estimated total effort is **10-12 weeks** with a team of 3-4 engineers (1 backend, 1 security, 1-2 frontend).

**Key Success Factors:**
1. **Incremental delivery** - Each phase delivers value independently
2. **Risk mitigation** - Rollback plans for each component
3. **Parallel execution** - Frontend and backend work can proceed simultaneously after Phase 1
4. **Testing emphasis** - Comprehensive testing at each phase prevents regressions

**Next Immediate Actions:**
1. [ ] Kick-off meeting to align team on priorities
2. [ ] AWS Bedrock account setup and model access request
3. [ ] Sprint planning for Phase 1 (Weeks 1-2)
4. [ ] Set up project tracking (Jira/GitHub Projects)

For questions or clarifications, please refer to the existing documentation in `.bmad/TECHNICAL_CONTEXT.md` and `.github/copilot-instructions.md`.
