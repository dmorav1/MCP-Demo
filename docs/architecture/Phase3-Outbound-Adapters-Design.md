# Phase 3: Outbound Adapters Architecture Design

**Document Version:** 1.0  
**Date:** November 6, 2025  
**Author:** Architect Agent  
**Status:** Design Specification  
**Related Documents:**
- Architecture-Migration-PRD.md
- PHASE_IMPLEMENTATION_REVIEW.md
- AGENT_TASK_PLAN.md

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Adapter Layer Design](#adapter-layer-design)
4. [Repository Adapters](#repository-adapters)
5. [Embedding Service Adapters](#embedding-service-adapters)
6. [Vector Search Adapter](#vector-search-adapter)
7. [Dependency Injection Configuration](#dependency-injection-configuration)
8. [Configuration Strategy](#configuration-strategy)
9. [Error Handling & Logging](#error-handling--logging)
10. [Transaction Management](#transaction-management)
11. [Performance Optimization](#performance-optimization)
12. [Architecture Decision Records](#architecture-decision-records)
13. [Implementation Guidelines](#implementation-guidelines)

---

## Executive Summary

This document defines the architecture for Phase 3 of the Hexagonal Architecture Migration: **Outbound Adapters Implementation**. The adapter layer implements domain port interfaces, connecting the application core to external systems (database, embedding services) while maintaining strict adherence to hexagonal architecture principles.

### Key Principles

1. **Dependency Inversion**: Adapters depend on domain interfaces, never the reverse
2. **Single Responsibility**: Each adapter has one clear purpose
3. **Configuration-Driven**: Adapter selection via environment configuration
4. **Testability**: All adapters support dependency injection and mocking
5. **Performance**: Optimized for production workloads with connection pooling and batch operations

### Deliverables

- SQLAlchemy repository adapters for PostgreSQL + pgvector
- Multiple embedding service adapters (Local, OpenAI, FastEmbed, LangChain)
- Optimized vector search adapter
- DI container configuration
- Comprehensive error handling and logging
- Transaction management strategy

---

## Architecture Overview

### Hexagonal Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│                  (FastAPI Routes, MCP Server)                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Application Layer                          │
│              (Use Cases: Ingest, Search, RAG)                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Domain Layer                            │
│    (Entities, Value Objects, Port Interfaces, Services)      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Adapter Layer (Phase 3)                     │
│                                                              │
│  ┌────────────────────┐    ┌──────────────────────┐        │
│  │  Repository         │    │  Embedding Service   │        │
│  │  Adapters          │    │  Adapters            │        │
│  │                    │    │                      │        │
│  │ • Conversation     │    │ • Local (sentence-   │        │
│  │ • Chunk            │    │   transformers)      │        │
│  │ • VectorSearch     │    │ • OpenAI             │        │
│  │ • Embedding        │    │ • FastEmbed          │        │
│  └────────────────────┘    │ • LangChain Wrapper  │        │
│                            └──────────────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   External Systems                           │
│         (PostgreSQL + pgvector, OpenAI API)                  │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
app/
├── domain/                       # Phase 1 (COMPLETE)
│   ├── entities.py
│   ├── value_objects.py
│   ├── repositories.py          # Port interfaces
│   └── services.py
│
├── application/                  # Phase 2 (COMPLETE)
│   ├── ingest_conversation.py
│   ├── search_conversations.py
│   ├── rag_service.py
│   └── dto.py
│
├── adapters/                     # Phase 3 (NEW)
│   ├── __init__.py
│   ├── outbound/
│   │   ├── __init__.py
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── sqlalchemy_models.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── chunk_repository.py
│   │   │   ├── vector_search_repository.py
│   │   │   ├── embedding_repository.py
│   │   │   └── unit_of_work.py
│   │   │
│   │   └── embedding/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── local_sentence_transformer.py
│   │       ├── openai_embedding.py
│   │       ├── fastembed_embedding.py
│   │       ├── langchain_wrapper.py
│   │       └── factory.py
│   │
│   └── config/
│       └── adapter_config.py
│
└── infrastructure/               # Phase 1 (EXISTING)
    ├── config.py
    └── container.py             # Will be extended
```

---

## Adapter Layer Design

### Core Design Principles

#### 1. Port-Adapter Pattern

Every adapter implements a domain-defined port interface:

```python
# Domain defines the contract (Port)
class IConversationRepository(ABC):
    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        pass

# Adapter implements the contract
class SQLAlchemyConversationRepository(IConversationRepository):
    async def save(self, conversation: Conversation) -> Conversation:
        # SQLAlchemy-specific implementation
        pass
```

**Key Point**: The domain layer never imports from the adapter layer.

#### 2. Separation of Concerns

- **Persistence Adapters**: Handle database operations (CRUD, transactions)
- **Embedding Adapters**: Handle vector generation (local or API-based)
- **Each adapter is independent**: Can be replaced without affecting others

#### 3. Configuration-Driven Selection

Adapters are selected at runtime based on environment configuration:

```yaml
# .env
EMBEDDING_PROVIDER=local  # or openai, fastembed, langchain
EMBEDDING_MODEL=all-MiniLM-L6-v2
DATABASE_URL=postgresql+psycopg://...
```

---

## Repository Adapters

### Overview

Repository adapters implement domain repository interfaces using SQLAlchemy ORM with PostgreSQL + pgvector.

### Design Goals

1. **Domain Entity Mapping**: Convert between domain entities and SQLAlchemy models
2. **Transaction Safety**: Ensure ACID properties
3. **Performance**: Optimize queries, use bulk operations
4. **Error Translation**: Convert SQLAlchemy exceptions to domain exceptions

### SQLAlchemy Models

**Location**: `app/adapters/outbound/persistence/sqlalchemy_models.py`

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class ConversationModel(Base):
    """
    SQLAlchemy model for conversation persistence.
    
    Design Notes:
    - Separate from domain entities to maintain clean boundaries
    - Optimized for database operations
    - Includes database-specific indexes and constraints
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_title = Column(Text, nullable=True)
    original_title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship with cascade delete
    chunks = relationship(
        "ConversationChunkModel",
        back_populates="conversation",
        order_by="ConversationChunkModel.order_index",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    def to_domain(self) -> Conversation:
        """Convert SQLAlchemy model to domain entity."""
        # Mapping logic here
        pass
    
    @staticmethod
    def from_domain(conversation: Conversation) -> 'ConversationModel':
        """Convert domain entity to SQLAlchemy model."""
        # Mapping logic here
        pass


class ConversationChunkModel(Base):
    """
    SQLAlchemy model for conversation chunk persistence.
    
    Design Notes:
    - Stores embeddings as pgvector type
    - Indexed for fast vector similarity search
    - Foreign key with CASCADE delete
    """
    __tablename__ = "conversation_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, 
        ForeignKey("conversations.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    order_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # Configurable dimension
    author_name = Column(Text, nullable=True)
    author_type = Column(String(16), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    
    conversation = relationship("ConversationModel", back_populates="chunks")
    
    __table_args__ = (
        # Vector similarity search index (IVFFlat for performance)
        Index(
            'ix_conversation_chunks_embedding',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_ops={'embedding': 'vector_l2_ops'},
            postgresql_with={'lists': 100}  # Tune based on dataset size
        ),
        # Unique constraint on conversation + order
        Index(
            'ix_conversation_chunks_conversation_order', 
            'conversation_id', 
            'order_index', 
            unique=True
        ),
    )
    
    def to_domain(self) -> ConversationChunk:
        """Convert SQLAlchemy model to domain entity."""
        pass
    
    @staticmethod
    def from_domain(chunk: ConversationChunk) -> 'ConversationChunkModel':
        """Convert domain entity to SQLAlchemy model."""
        pass
```

### Conversation Repository Adapter

**Location**: `app/adapters/outbound/persistence/conversation_repository.py`

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import logging

from app.domain.repositories import IConversationRepository, RepositoryError
from app.domain.entities import Conversation
from app.domain.value_objects import ConversationId
from .sqlalchemy_models import ConversationModel, ConversationChunkModel

logger = logging.getLogger(__name__)


class SQLAlchemyConversationRepository(IConversationRepository):
    """
    SQLAlchemy implementation of conversation repository.
    
    Design Decisions:
    - Uses AsyncSession for non-blocking I/O
    - Eager loads chunks to minimize N+1 queries
    - Translates SQLAlchemy exceptions to domain exceptions
    - Maps between domain entities and persistence models
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session (injected by DI container)
        """
        self.session = session
        logger.debug("SQLAlchemyConversationRepository initialized")
    
    async def save(self, conversation: Conversation) -> Conversation:
        """
        Persist a conversation and return it with assigned ID.
        
        Implementation Notes:
        - Converts domain entity to SQLAlchemy model
        - Handles new conversations (INSERT) and updates (UPDATE)
        - Flushes to get DB-assigned ID
        - Converts back to domain entity
        
        Args:
            conversation: The conversation to save
            
        Returns:
            The saved conversation with ID assigned
            
        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Convert domain entity to persistence model
            conv_model = ConversationModel.from_domain(conversation)
            
            # Add to session
            self.session.add(conv_model)
            
            # Flush to get ID without committing transaction
            await self.session.flush()
            await self.session.refresh(conv_model)
            
            # Convert back to domain entity
            saved_conversation = conv_model.to_domain()
            
            logger.info(f"Saved conversation with ID: {conv_model.id}")
            return saved_conversation
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")
            raise RepositoryError(f"Save operation failed: {str(e)}") from e
    
    async def get_by_id(self, conversation_id: ConversationId) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID with eager loading of chunks.
        
        Implementation Notes:
        - Uses selectinload to avoid N+1 query problem
        - Returns None if not found (not an error)
        - Maps to domain entity
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            The conversation if found, None otherwise
        """
        try:
            # Build query with eager loading
            stmt = (
                select(ConversationModel)
                .options(selectinload(ConversationModel.chunks))
                .where(ConversationModel.id == conversation_id.value)
            )
            
            result = await self.session.execute(stmt)
            conv_model = result.scalar_one_or_none()
            
            if conv_model is None:
                logger.debug(f"Conversation {conversation_id.value} not found")
                return None
            
            # Convert to domain entity
            conversation = conv_model.to_domain()
            logger.debug(f"Retrieved conversation {conversation_id.value}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id.value}: {str(e)}")
            raise RepositoryError(f"Get operation failed: {str(e)}") from e
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Retrieve conversations with pagination.
        
        Implementation Notes:
        - Orders by created_at DESC (newest first)
        - Uses offset/limit for pagination
        - Eager loads chunks
        
        Args:
            skip: Number of conversations to skip
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversations ordered by creation date (newest first)
        """
        try:
            stmt = (
                select(ConversationModel)
                .options(selectinload(ConversationModel.chunks))
                .order_by(ConversationModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            conv_models = result.scalars().all()
            
            conversations = [model.to_domain() for model in conv_models]
            logger.debug(f"Retrieved {len(conversations)} conversations (skip={skip}, limit={limit})")
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get all conversations: {str(e)}")
            raise RepositoryError(f"Get all operation failed: {str(e)}") from e
    
    async def delete(self, conversation_id: ConversationId) -> bool:
        """
        Delete a conversation and all its chunks (cascade).
        
        Implementation Notes:
        - Uses cascade delete (configured in FK)
        - Returns False if conversation doesn't exist
        - Logs deletion for audit trail
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If deletion fails
        """
        try:
            # Find conversation
            stmt = select(ConversationModel).where(
                ConversationModel.id == conversation_id.value
            )
            result = await self.session.execute(stmt)
            conv_model = result.scalar_one_or_none()
            
            if conv_model is None:
                logger.debug(f"Conversation {conversation_id.value} not found for deletion")
                return False
            
            # Delete (cascades to chunks automatically)
            await self.session.delete(conv_model)
            await self.session.flush()
            
            logger.info(f"Deleted conversation {conversation_id.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id.value}: {str(e)}")
            raise RepositoryError(f"Delete operation failed: {str(e)}") from e
    
    async def exists(self, conversation_id: ConversationId) -> bool:
        """
        Check if a conversation exists (optimized query).
        
        Implementation Notes:
        - Uses COUNT instead of loading full object
        - More efficient for existence checks
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if conversation exists, False otherwise
        """
        try:
            stmt = select(func.count()).select_from(ConversationModel).where(
                ConversationModel.id == conversation_id.value
            )
            result = await self.session.execute(stmt)
            count = result.scalar()
            
            exists = count > 0
            logger.debug(f"Conversation {conversation_id.value} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check existence of conversation {conversation_id.value}: {str(e)}")
            raise RepositoryError(f"Exists check failed: {str(e)}") from e
    
    async def count(self) -> int:
        """
        Get total number of conversations.
        
        Returns:
            Total conversation count
        """
        try:
            stmt = select(func.count()).select_from(ConversationModel)
            result = await self.session.execute(stmt)
            count = result.scalar()
            
            logger.debug(f"Total conversations: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count conversations: {str(e)}")
            raise RepositoryError(f"Count operation failed: {str(e)}") from e
```

### Chunk Repository Adapter

**Location**: `app/adapters/outbound/persistence/chunk_repository.py`

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from app.domain.repositories import IChunkRepository, RepositoryError
from app.domain.entities import ConversationChunk
from app.domain.value_objects import ConversationId, ChunkId, Embedding
from .sqlalchemy_models import ConversationChunkModel

logger = logging.getLogger(__name__)


class SQLAlchemyChunkRepository(IChunkRepository):
    """
    SQLAlchemy implementation of chunk repository.
    
    Design Decisions:
    - Optimized for batch operations (bulk inserts)
    - Supports efficient embedding updates
    - Filters chunks without embeddings for processing
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("SQLAlchemyChunkRepository initialized")
    
    async def save_chunks(self, chunks: List[ConversationChunk]) -> List[ConversationChunk]:
        """
        Save multiple chunks in a batch operation.
        
        Implementation Notes:
        - Uses bulk save for efficiency
        - Returns chunks with assigned IDs
        - Maintains order
        
        Args:
            chunks: List of chunks to save
            
        Returns:
            Saved chunks with IDs assigned
            
        Raises:
            RepositoryError: If batch save fails
        """
        try:
            if not chunks:
                return []
            
            # Convert to models
            chunk_models = [ConversationChunkModel.from_domain(chunk) for chunk in chunks]
            
            # Bulk add
            self.session.add_all(chunk_models)
            await self.session.flush()
            
            # Refresh to get IDs
            for model in chunk_models:
                await self.session.refresh(model)
            
            # Convert back to domain
            saved_chunks = [model.to_domain() for model in chunk_models]
            
            logger.info(f"Saved {len(saved_chunks)} chunks in batch")
            return saved_chunks
            
        except Exception as e:
            logger.error(f"Failed to save chunks batch: {str(e)}")
            raise RepositoryError(f"Batch save failed: {str(e)}") from e
    
    async def get_by_conversation(self, conversation_id: ConversationId) -> List[ConversationChunk]:
        """
        Get all chunks for a conversation, ordered by index.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            List of chunks ordered by order_index
        """
        try:
            stmt = (
                select(ConversationChunkModel)
                .where(ConversationChunkModel.conversation_id == conversation_id.value)
                .order_by(ConversationChunkModel.order_index)
            )
            
            result = await self.session.execute(stmt)
            chunk_models = result.scalars().all()
            
            chunks = [model.to_domain() for model in chunk_models]
            logger.debug(f"Retrieved {len(chunks)} chunks for conversation {conversation_id.value}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for conversation {conversation_id.value}: {str(e)}")
            raise RepositoryError(f"Get chunks failed: {str(e)}") from e
    
    async def get_by_id(self, chunk_id: ChunkId) -> Optional[ConversationChunk]:
        """
        Retrieve a chunk by ID.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The chunk if found, None otherwise
        """
        try:
            stmt = select(ConversationChunkModel).where(
                ConversationChunkModel.id == chunk_id.value
            )
            
            result = await self.session.execute(stmt)
            chunk_model = result.scalar_one_or_none()
            
            if chunk_model is None:
                return None
            
            return chunk_model.to_domain()
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id.value}: {str(e)}")
            raise RepositoryError(f"Get chunk failed: {str(e)}") from e
    
    async def update_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Update the embedding for a specific chunk.
        
        Implementation Notes:
        - Efficient single-field update
        - Validates embedding dimension
        
        Args:
            chunk_id: The chunk identifier
            embedding: The new embedding
            
        Returns:
            True if updated successfully, False if chunk not found
            
        Raises:
            RepositoryError: If update fails
        """
        try:
            stmt = select(ConversationChunkModel).where(
                ConversationChunkModel.id == chunk_id.value
            )
            result = await self.session.execute(stmt)
            chunk_model = result.scalar_one_or_none()
            
            if chunk_model is None:
                return False
            
            # Update embedding
            chunk_model.embedding = embedding.vector
            await self.session.flush()
            
            logger.debug(f"Updated embedding for chunk {chunk_id.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update embedding for chunk {chunk_id.value}: {str(e)}")
            raise RepositoryError(f"Update embedding failed: {str(e)}") from e
    
    async def get_chunks_without_embeddings(self) -> List[ConversationChunk]:
        """
        Get all chunks that don't have embeddings yet.
        
        Implementation Notes:
        - Useful for batch embedding generation
        - Filters on NULL embedding column
        
        Returns:
            List of chunks without embeddings
        """
        try:
            stmt = select(ConversationChunkModel).where(
                ConversationChunkModel.embedding.is_(None)
            )
            
            result = await self.session.execute(stmt)
            chunk_models = result.scalars().all()
            
            chunks = [model.to_domain() for model in chunk_models]
            logger.debug(f"Found {len(chunks)} chunks without embeddings")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks without embeddings: {str(e)}")
            raise RepositoryError(f"Get chunks without embeddings failed: {str(e)}") from e
```


### Vector Search Repository Adapter

**Location**: `app/adapters/outbound/persistence/vector_search_repository.py`

```python
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
import logging

from app.domain.repositories import IVectorSearchRepository, RepositoryError
from app.domain.entities import ConversationChunk
from app.domain.value_objects import Embedding, RelevanceScore
from .sqlalchemy_models import ConversationChunkModel

logger = logging.getLogger(__name__)


class PgVectorSearchRepository(IVectorSearchRepository):
    """
    pgvector-based implementation of vector similarity search.
    
    Design Decisions:
    - Uses L2 distance operator (<->) for similarity
    - Leverages IVFFlat index for performance
    - Converts distance to similarity score (0.0-1.0 range)
    - Supports threshold-based filtering
    
    Performance Notes:
    - IVFFlat index provides approximate nearest neighbor search
    - Trade-off between accuracy and speed (configurable via 'lists' parameter)
    - For datasets < 1M vectors, IVFFlat with lists=100 is optimal
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("PgVectorSearchRepository initialized")
    
    async def similarity_search(
        self, 
        query_embedding: Embedding, 
        top_k: int = 10
    ) -> List[Tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search using L2 distance.
        
        Implementation Notes:
        - Uses pgvector's <-> operator (L2 distance)
        - Lower distance = higher similarity
        - Converts distance to relevance score: similarity = 1.0 / (1.0 + distance)
        - Orders by distance ASC (closest first)
        - Limits to top_k results
        
        Performance:
        - Leverages IVFFlat index for ~10x speedup vs sequential scan
        - Query time: O(sqrt(n)) with index vs O(n) without
        
        Args:
            query_embedding: The query vector
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples ordered by relevance
            
        Raises:
            RepositoryError: If search fails
        """
        try:
            # Convert embedding to pgvector format
            embedding_str = f"[{','.join(str(x) for x in query_embedding.vector)}]"
            
            # Build query with vector similarity
            # Note: <-> is L2 distance operator
            query = text("""
                SELECT id, conversation_id, order_index, chunk_text, 
                       embedding, author_name, author_type, timestamp,
                       (embedding <-> :query_embedding) AS distance
                FROM conversation_chunks
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT :top_k
            """)
            
            result = await self.session.execute(
                query,
                {"query_embedding": embedding_str, "top_k": top_k}
            )
            
            rows = result.fetchall()
            
            # Convert results to domain entities
            results = []
            for row in rows:
                # Reconstruct chunk model
                chunk_model = ConversationChunkModel(
                    id=row.id,
                    conversation_id=row.conversation_id,
                    order_index=row.order_index,
                    chunk_text=row.chunk_text,
                    embedding=row.embedding,
                    author_name=row.author_name,
                    author_type=row.author_type,
                    timestamp=row.timestamp
                )
                
                chunk = chunk_model.to_domain()
                
                # Convert distance to relevance score
                # Formula: similarity = 1.0 / (1.0 + distance)
                # This normalizes to 0.0-1.0 range where 1.0 is perfect match
                distance = float(row.distance)
                relevance = RelevanceScore(1.0 / (1.0 + distance))
                
                results.append((chunk, relevance))
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise RepositoryError(f"Vector search operation failed: {str(e)}") from e
    
    async def similarity_search_with_threshold(
        self, 
        query_embedding: Embedding, 
        threshold: float = 0.7,
        top_k: int = 10
    ) -> List[Tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search with relevance threshold.
        
        Implementation Notes:
        - First retrieves top_k results
        - Then filters by threshold
        - More efficient than database-level filtering for small result sets
        
        Alternative Implementation:
        - For large datasets, could push threshold to database query
        - Would require converting threshold to distance: distance = (1.0 / threshold) - 1.0
        
        Args:
            query_embedding: The query vector
            threshold: Minimum relevance score (0.0 to 1.0)
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples above threshold
            
        Raises:
            RepositoryError: If search fails
        """
        try:
            # Get all top_k results
            all_results = await self.similarity_search(query_embedding, top_k)
            
            # Filter by threshold
            filtered_results = [
                (chunk, score) for chunk, score in all_results
                if score.value >= threshold
            ]
            
            logger.info(
                f"Threshold search returned {len(filtered_results)} results "
                f"(filtered from {len(all_results)})"
            )
            return filtered_results
            
        except Exception as e:
            logger.error(f"Threshold vector search failed: {str(e)}")
            raise RepositoryError(f"Threshold search operation failed: {str(e)}") from e
```

### Embedding Repository Adapter

**Location**: `app/adapters/outbound/persistence/embedding_repository.py`

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.domain.repositories import IEmbeddingRepository, RepositoryError
from app.domain.value_objects import ChunkId, Embedding
from .sqlalchemy_models import ConversationChunkModel

logger = logging.getLogger(__name__)


class SQLAlchemyEmbeddingRepository(IEmbeddingRepository):
    """
    SQLAlchemy implementation for embedding storage.
    
    Design Note:
    - This is a specialized view of chunk repository focused on embeddings
    - Could be combined with ChunkRepository, but separated for SRP
    - Useful for background embedding generation jobs
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("SQLAlchemyEmbeddingRepository initialized")
    
    async def store_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Store an embedding for a chunk.
        
        Implementation Notes:
        - Same as chunk_repository.update_embedding()
        - Separated for interface segregation
        
        Args:
            chunk_id: The chunk identifier
            embedding: The embedding vector
            
        Returns:
            True if stored successfully
            
        Raises:
            RepositoryError: If storage fails
        """
        try:
            stmt = select(ConversationChunkModel).where(
                ConversationChunkModel.id == chunk_id.value
            )
            result = await self.session.execute(stmt)
            chunk_model = result.scalar_one_or_none()
            
            if chunk_model is None:
                logger.warning(f"Chunk {chunk_id.value} not found for embedding storage")
                return False
            
            chunk_model.embedding = embedding.vector
            await self.session.flush()
            
            logger.debug(f"Stored embedding for chunk {chunk_id.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding for chunk {chunk_id.value}: {str(e)}")
            raise RepositoryError(f"Store embedding failed: {str(e)}") from e
    
    async def get_embedding(self, chunk_id: ChunkId) -> Optional[Embedding]:
        """
        Retrieve an embedding for a chunk.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The embedding if found, None otherwise
        """
        try:
            stmt = select(ConversationChunkModel.embedding).where(
                ConversationChunkModel.id == chunk_id.value
            )
            result = await self.session.execute(stmt)
            embedding_vector = result.scalar_one_or_none()
            
            if embedding_vector is None:
                return None
            
            return Embedding(vector=embedding_vector)
            
        except Exception as e:
            logger.error(f"Failed to get embedding for chunk {chunk_id.value}: {str(e)}")
            raise RepositoryError(f"Get embedding failed: {str(e)}") from e
    
    async def has_embedding(self, chunk_id: ChunkId) -> bool:
        """
        Check if a chunk has an embedding (efficient query).
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            True if chunk has embedding, False otherwise
        """
        try:
            stmt = select(ConversationChunkModel.embedding).where(
                ConversationChunkModel.id == chunk_id.value
            )
            result = await self.session.execute(stmt)
            embedding_vector = result.scalar_one_or_none()
            
            return embedding_vector is not None
            
        except Exception as e:
            logger.error(f"Failed to check embedding for chunk {chunk_id.value}: {str(e)}")
            raise RepositoryError(f"Has embedding check failed: {str(e)}") from e
    
    async def get_chunks_needing_embeddings(self) -> List[ChunkId]:
        """
        Get chunk IDs that need embeddings generated.
        
        Returns:
            List of chunk IDs without embeddings
        """
        try:
            stmt = select(ConversationChunkModel.id).where(
                ConversationChunkModel.embedding.is_(None)
            )
            
            result = await self.session.execute(stmt)
            chunk_ids = result.scalars().all()
            
            chunk_id_objects = [ChunkId(value=id_val) for id_val in chunk_ids]
            logger.debug(f"Found {len(chunk_id_objects)} chunks needing embeddings")
            return chunk_id_objects
            
        except Exception as e:
            logger.error(f"Failed to get chunks needing embeddings: {str(e)}")
            raise RepositoryError(f"Get chunks needing embeddings failed: {str(e)}") from e
```

---

## Embedding Service Adapters

### Overview

Multiple embedding service adapters support different embedding providers:

1. **Local (SentenceTransformers)**: Free, runs on-premise, good quality
2. **OpenAI**: Paid API, high quality, requires API key
3. **FastEmbed**: Alternative local option, lighter weight
4. **LangChain Wrapper**: Future extensibility for LangChain ecosystem

All adapters implement the `IEmbeddingService` protocol.

### Base Adapter Interface

**Location**: `app/adapters/outbound/embedding/base.py`

```python
from abc import ABC, abstractmethod
from typing import List
import logging

from app.domain.value_objects import Embedding
from app.domain.repositories import EmbeddingError

logger = logging.getLogger(__name__)


class BaseEmbeddingAdapter(ABC):
    """
    Abstract base class for embedding adapters.
    
    Design Pattern: Template Method
    - Provides common error handling and logging
    - Subclasses implement provider-specific logic
    """
    
    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension
        logger.info(f"Initializing {self.__class__.__name__} with model {model_name}")
    
    @abstractmethod
    async def _generate_embedding_impl(self, text: str) -> List[float]:
        """Provider-specific implementation."""
        pass
    
    @abstractmethod
    async def _generate_embeddings_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """Provider-specific batch implementation."""
        pass
    
    async def generate_embedding(self, text: str) -> Embedding:
        """
        Generate an embedding for text content.
        
        Template method with error handling and validation.
        """
        try:
            if not text or not text.strip():
                raise EmbeddingError("Cannot generate embedding for empty text")
            
            # Call provider-specific implementation
            vector = await self._generate_embedding_impl(text)
            
            # Validate dimension
            if len(vector) != self.dimension:
                raise EmbeddingError(
                    f"Expected embedding dimension {self.dimension}, got {len(vector)}"
                )
            
            embedding = Embedding(vector=vector)
            logger.debug(f"Generated embedding for text (length: {len(text)})")
            return embedding
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
        """
        Generate embeddings for multiple texts in batch.
        
        Template method with error handling and validation.
        """
        try:
            if not texts:
                return []
            
            # Filter empty texts
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                raise EmbeddingError("No valid texts to embed")
            
            # Call provider-specific implementation
            vectors = await self._generate_embeddings_batch_impl(valid_texts)
            
            # Validate dimensions
            for i, vector in enumerate(vectors):
                if len(vector) != self.dimension:
                    raise EmbeddingError(
                        f"Embedding {i}: expected dimension {self.dimension}, got {len(vector)}"
                    )
            
            embeddings = [Embedding(vector=v) for v in vectors]
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}") from e
```

### Local SentenceTransformer Adapter

**Location**: `app/adapters/outbound/embedding/local_sentence_transformer.py`

```python
from typing import List
import asyncio
from sentence_transformers import SentenceTransformer
import logging

from .base import BaseEmbeddingAdapter
from app.domain.repositories import EmbeddingError

logger = logging.getLogger(__name__)


class LocalSentenceTransformerAdapter(BaseEmbeddingAdapter):
    """
    Local embedding adapter using SentenceTransformers library.
    
    Model: all-MiniLM-L6-v2 (default)
    - Dimension: 384
    - Speed: ~1000 sentences/sec on CPU
    - Quality: Good for most use cases
    - Cost: Free (runs locally)
    
    Design Decisions:
    - Loads model once in __init__ (singleton pattern recommended)
    - Uses asyncio.to_thread() for non-blocking execution
    - Supports batch encoding for efficiency
    
    Performance Notes:
    - Batch processing is ~10x faster than sequential
    - Optimal batch size: 32-64 texts
    - Memory usage: ~500MB for model + embeddings
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    DEFAULT_DIMENSION = 384
    
    def __init__(
        self, 
        model_name: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION,
        device: str = "cpu"
    ):
        """
        Initialize local embedding model.
        
        Args:
            model_name: HuggingFace model identifier
            dimension: Expected embedding dimension
            device: 'cpu' or 'cuda' for GPU acceleration
        """
        super().__init__(model_name, dimension)
        self.device = device
        
        # Load model (heavy operation, done once)
        try:
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Loaded SentenceTransformer model {model_name} on {device}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise EmbeddingError(f"Model initialization failed: {str(e)}") from e
    
    async def _generate_embedding_impl(self, text: str) -> List[float]:
        """
        Generate embedding using SentenceTransformers.
        
        Implementation Notes:
        - Runs in thread pool to avoid blocking async loop
        - model.encode() is CPU-bound operation
        """
        def _encode():
            # model.encode returns numpy array
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        
        # Run in thread pool to avoid blocking
        vector = await asyncio.to_thread(_encode)
        return vector
    
    async def _generate_embeddings_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings in batch for efficiency.
        
        Implementation Notes:
        - Much faster than sequential encoding
        - model.encode handles batching internally
        - Batch size controlled by model (usually 32)
        """
        def _encode_batch():
            # model.encode returns numpy array of shape (n_texts, dimension)
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Convert to list of lists
            return [emb.tolist() for emb in embeddings]
        
        # Run in thread pool
        vectors = await asyncio.to_thread(_encode_batch)
        return vectors


# Alternative: Use sentence-transformers with ONNX for faster inference
class LocalSentenceTransformerONNXAdapter(BaseEmbeddingAdapter):
    """
    ONNX-optimized version for production deployments.
    
    Benefits:
    - 2-3x faster inference
    - Lower memory usage
    - Requires ONNX Runtime
    
    Trade-offs:
    - More complex setup
    - Limited model support
    """
    # Implementation similar to above but with ONNX runtime
    pass
```

### OpenAI Embedding Adapter

**Location**: `app/adapters/outbound/embedding/openai_embedding.py`

```python
from typing import List
import asyncio
from openai import AsyncOpenAI
import logging

from .base import BaseEmbeddingAdapter
from app.domain.repositories import EmbeddingError

logger = logging.getLogger(__name__)


class OpenAIEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    OpenAI embedding adapter using text-embedding-ada-002.
    
    Model: text-embedding-ada-002
    - Dimension: 1536
    - Speed: ~100-500 embeddings/sec (API-dependent)
    - Quality: Excellent
    - Cost: $0.0001 per 1K tokens
    
    Design Decisions:
    - Uses async OpenAI client
    - Implements exponential backoff for rate limits
    - Supports batch requests (max 2048 texts per batch)
    
    Rate Limits:
    - Free tier: 3 requests/min
    - Paid tier: 3000 requests/min
    
    Security:
    - API key from environment variable
    - Never log API keys
    """
    
    DEFAULT_MODEL = "text-embedding-ada-002"
    DEFAULT_DIMENSION = 1536
    MAX_BATCH_SIZE = 2048  # OpenAI limit
    
    def __init__(
        self,
        api_key: str,
        model_name: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model_name: OpenAI model identifier
            dimension: Expected embedding dimension
        """
        super().__init__(model_name, dimension)
        
        if not api_key:
            raise EmbeddingError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI embedding adapter with model {model_name}")
    
    async def _generate_embedding_impl(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI API.
        
        Implementation Notes:
        - Single text request
        - Handles rate limiting with retry
        - Validates response format
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text,
                encoding_format="float"
            )
            
            # Extract embedding from response
            if not response.data or len(response.data) == 0:
                raise EmbeddingError("OpenAI returned empty response")
            
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding request failed: {str(e)}")
            raise EmbeddingError(f"OpenAI API error: {str(e)}") from e
    
    async def _generate_embeddings_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings in batch using OpenAI API.
        
        Implementation Notes:
        - OpenAI supports up to 2048 texts per request
        - Splits large batches automatically
        - Maintains order of results
        """
        try:
            # Split into chunks if exceeds max batch size
            all_embeddings = []
            
            for i in range(0, len(texts), self.MAX_BATCH_SIZE):
                batch = texts[i:i + self.MAX_BATCH_SIZE]
                
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                    encoding_format="float"
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding request failed: {str(e)}")
            raise EmbeddingError(f"OpenAI batch API error: {str(e)}") from e
```

### FastEmbed Adapter

**Location**: `app/adapters/outbound/embedding/fastembed_embedding.py`

```python
from typing import List
import asyncio
import logging

# Note: FastEmbed is a lightweight alternative to SentenceTransformers
# Install: pip install fastembed
try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    TextEmbedding = None

from .base import BaseEmbeddingAdapter
from app.domain.repositories import EmbeddingError

logger = logging.getLogger(__name__)


class FastEmbedAdapter(BaseEmbeddingAdapter):
    """
    FastEmbed adapter for lightweight, fast embeddings.
    
    Model: BAAI/bge-small-en-v1.5 (default)
    - Dimension: 384
    - Speed: ~2000 sentences/sec on CPU (2x faster than SentenceTransformers)
    - Quality: Comparable to SentenceTransformers
    - Cost: Free (runs locally)
    
    Benefits:
    - Smaller model size
    - Faster inference
    - Lower memory footprint
    
    Trade-offs:
    - Fewer model options
    - Less mature library
    """
    
    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    DEFAULT_DIMENSION = 384
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION
    ):
        """Initialize FastEmbed model."""
        if not FASTEMBED_AVAILABLE:
            raise EmbeddingError(
                "FastEmbed is not installed. Install with: pip install fastembed"
            )
        
        super().__init__(model_name, dimension)
        
        try:
            self.model = TextEmbedding(model_name)
            logger.info(f"Loaded FastEmbed model {model_name}")
        except Exception as e:
            logger.error(f"Failed to load FastEmbed model: {str(e)}")
            raise EmbeddingError(f"FastEmbed initialization failed: {str(e)}") from e
    
    async def _generate_embedding_impl(self, text: str) -> List[float]:
        """Generate embedding using FastEmbed."""
        def _encode():
            # FastEmbed returns generator, convert to list
            embeddings = list(self.model.embed([text]))
            return embeddings[0].tolist()
        
        vector = await asyncio.to_thread(_encode)
        return vector
    
    async def _generate_embeddings_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch using FastEmbed."""
        def _encode_batch():
            # FastEmbed returns generator
            embeddings = list(self.model.embed(texts))
            return [emb.tolist() for emb in embeddings]
        
        vectors = await asyncio.to_thread(_encode_batch)
        return vectors
```

### LangChain Wrapper Adapter

**Location**: `app/adapters/outbound/embedding/langchain_wrapper.py`

```python
from typing import List
import logging

try:
    from langchain.embeddings.base import Embeddings as LangChainEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    LangChainEmbeddings = None

from .base import BaseEmbeddingAdapter
from app.domain.repositories import EmbeddingError

logger = logging.getLogger(__name__)


class LangChainEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    Wrapper for LangChain embedding providers.
    
    Purpose:
    - Future extensibility for LangChain ecosystem
    - Access to LangChain's diverse embedding providers
    - Integration with LangChain RAG components
    
    Supported Providers (via LangChain):
    - OpenAI
    - Cohere
    - HuggingFace
    - Anthropic
    - And many more...
    
    Design Decision:
    - Wraps any LangChain embedding provider
    - Adapts LangChain interface to our domain interface
    """
    
    def __init__(
        self,
        langchain_embeddings: LangChainEmbeddings,
        dimension: int
    ):
        """
        Initialize with LangChain embedding provider.
        
        Args:
            langchain_embeddings: Any LangChain Embeddings instance
            dimension: Expected embedding dimension
        """
        if not LANGCHAIN_AVAILABLE:
            raise EmbeddingError(
                "LangChain is not installed. Install with: pip install langchain"
            )
        
        model_name = langchain_embeddings.__class__.__name__
        super().__init__(model_name, dimension)
        self.embeddings = langchain_embeddings
    
    async def _generate_embedding_impl(self, text: str) -> List[float]:
        """Generate embedding via LangChain provider."""
        try:
            # LangChain's embed_query is async-compatible
            vector = await self.embeddings.aembed_query(text)
            return vector
        except Exception as e:
            logger.error(f"LangChain embedding failed: {str(e)}")
            raise EmbeddingError(f"LangChain error: {str(e)}") from e
    
    async def _generate_embeddings_batch_impl(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch via LangChain provider."""
        try:
            # LangChain's embed_documents handles batching
            vectors = await self.embeddings.aembed_documents(texts)
            return vectors
        except Exception as e:
            logger.error(f"LangChain batch embedding failed: {str(e)}")
            raise EmbeddingError(f"LangChain batch error: {str(e)}") from e
```

### Embedding Adapter Factory

**Location**: `app/adapters/outbound/embedding/factory.py`

```python
from typing import Optional
import logging

from app.domain.repositories import IEmbeddingService, EmbeddingError
from app.infrastructure.config import get_embedding_config
from .local_sentence_transformer import LocalSentenceTransformerAdapter
from .openai_embedding import OpenAIEmbeddingAdapter
from .fastembed_embedding import FastEmbedAdapter

logger = logging.getLogger(__name__)


class EmbeddingAdapterFactory:
    """
    Factory for creating embedding adapters based on configuration.
    
    Design Pattern: Factory Method
    - Centralizes adapter creation logic
    - Handles configuration validation
    - Provides sensible defaults
    
    Usage:
        factory = EmbeddingAdapterFactory()
        embedding_service = factory.create_from_config()
    """
    
    @staticmethod
    def create_from_config() -> IEmbeddingService:
        """
        Create embedding adapter from application configuration.
        
        Configuration (from environment):
        - EMBEDDING_PROVIDER: 'local', 'openai', 'fastembed', 'langchain'
        - EMBEDDING_MODEL: Model identifier
        - EMBEDDING_DIMENSION: Expected dimension
        - OPENAI_API_KEY: Required for OpenAI provider
        
        Returns:
            Configured embedding service adapter
            
        Raises:
            EmbeddingError: If configuration is invalid
        """
        config = get_embedding_config()
        
        provider = config.provider.lower()
        model = config.model
        dimension = config.dimension
        
        logger.info(f"Creating embedding adapter: provider={provider}, model={model}")
        
        if provider == "local":
            return LocalSentenceTransformerAdapter(
                model_name=model,
                dimension=dimension
            )
        
        elif provider == "openai":
            api_key = config.api_key
            if not api_key:
                raise EmbeddingError(
                    "OPENAI_API_KEY environment variable is required for OpenAI provider"
                )
            return OpenAIEmbeddingAdapter(
                api_key=api_key,
                model_name=model,
                dimension=dimension
            )
        
        elif provider == "fastembed":
            return FastEmbedAdapter(
                model_name=model,
                dimension=dimension
            )
        
        elif provider == "langchain":
            raise EmbeddingError(
                "LangChain provider requires custom initialization. "
                "Use EmbeddingAdapterFactory.create_langchain() instead."
            )
        
        else:
            raise EmbeddingError(
                f"Unknown embedding provider: {provider}. "
                f"Supported providers: local, openai, fastembed, langchain"
            )
    
    @staticmethod
    def create_langchain(
        langchain_embeddings: 'LangChainEmbeddings',
        dimension: int
    ) -> IEmbeddingService:
        """
        Create LangChain wrapper adapter.
        
        Args:
            langchain_embeddings: Pre-configured LangChain embeddings instance
            dimension: Expected embedding dimension
            
        Returns:
            LangChain embedding adapter
        """
        from .langchain_wrapper import LangChainEmbeddingAdapter
        return LangChainEmbeddingAdapter(langchain_embeddings, dimension)
    
    @staticmethod
    def create_custom(
        provider: str,
        model: str,
        dimension: int,
        **kwargs
    ) -> IEmbeddingService:
        """
        Create embedding adapter with custom parameters.
        
        Args:
            provider: Provider name
            model: Model identifier
            dimension: Embedding dimension
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Configured embedding adapter
        """
        if provider == "local":
            return LocalSentenceTransformerAdapter(
                model_name=model,
                dimension=dimension,
                device=kwargs.get("device", "cpu")
            )
        
        elif provider == "openai":
            return OpenAIEmbeddingAdapter(
                api_key=kwargs.get("api_key"),
                model_name=model,
                dimension=dimension
            )
        
        elif provider == "fastembed":
            return FastEmbedAdapter(
                model_name=model,
                dimension=dimension
            )
        
        else:
            raise EmbeddingError(f"Unsupported provider: {provider}")
```


---

## Dependency Injection Configuration

### DI Container Extension

**Location**: `app/infrastructure/container.py` (extend existing)

```python
# Extension to existing container.py

class AdapterServiceProvider(ServiceProvider):
    """
    Service provider for outbound adapters.
    
    Registers all adapter implementations with the DI container.
    """
    
    def configure_services(self, container: Container) -> None:
        """Configure adapter services."""
        from app.adapters.outbound.persistence import (
            SQLAlchemyConversationRepository,
            SQLAlchemyChunkRepository,
            PgVectorSearchRepository,
            SQLAlchemyEmbeddingRepository
        )
        from app.adapters.outbound.embedding import EmbeddingAdapterFactory
        from app.domain.repositories import (
            IConversationRepository,
            IChunkRepository,
            IVectorSearchRepository,
            IEmbeddingRepository,
            IEmbeddingService
        )
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Database session factory
        container.register_scoped(
            AsyncSession,
            factory=lambda: get_async_session()  # From database module
        )
        
        # Repository adapters (scoped to request/transaction)
        container.register_scoped(
            IConversationRepository,
            implementation=SQLAlchemyConversationRepository
        )
        
        container.register_scoped(
            IChunkRepository,
            implementation=SQLAlchemyChunkRepository
        )
        
        container.register_scoped(
            IVectorSearchRepository,
            implementation=PgVectorSearchRepository
        )
        
        container.register_scoped(
            IEmbeddingRepository,
            implementation=SQLAlchemyEmbeddingRepository
        )
        
        # Embedding service (singleton - expensive to create)
        container.register_singleton(
            IEmbeddingService,
            factory=EmbeddingAdapterFactory.create_from_config
        )


def configure_production_container() -> Container:
    """
    Configure container for production use.
    
    Returns:
        Fully configured container with all services
    """
    providers = [
        CoreServiceProvider(),
        ApplicationServiceProvider(),
        AdapterServiceProvider()  # New
    ]
    
    return configure_container(providers)
```

### Database Session Management

**Location**: `app/adapters/outbound/persistence/__init__.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging

from app.infrastructure.config import get_database_config

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine (created once)
_engine = None
_session_factory = None


def get_async_engine():
    """Get or create async database engine."""
    global _engine
    
    if _engine is None:
        config = get_database_config()
        
        _engine = create_async_engine(
            config.url,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            future=True  # SQLAlchemy 2.0 style
        )
        
        logger.info(f"Created async database engine: pool_size={config.pool_size}")
    
    return _engine


def get_session_factory():
    """Get or create async session factory."""
    global _session_factory
    
    if _session_factory is None:
        engine = get_async_engine()
        
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
            autoflush=False,
            autocommit=False
        )
        
        logger.info("Created async session factory")
    
    return _session_factory


async def get_async_session() -> AsyncSession:
    """
    Get a new async database session.
    
    Usage in FastAPI:
        @app.post("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_async_session)):
            # Use session
            pass
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_database():
    """Initialize database schema (for development/testing)."""
    engine = get_async_engine()
    
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from .sqlalchemy_models import ConversationModel, ConversationChunkModel
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database schema initialized")


async def close_database():
    """Close database connections (for graceful shutdown)."""
    global _engine
    
    if _engine:
        await _engine.dispose()
        logger.info("Database connections closed")
```

---

## Configuration Strategy

### Environment-Based Configuration

**Configuration File**: `.env`

```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/dbname
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Embedding Service Configuration
EMBEDDING_PROVIDER=local  # Options: local, openai, fastembed, langchain
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Provider-specific model name
EMBEDDING_DIMENSION=384  # Must match model output
EMBEDDING_BATCH_SIZE=32

# OpenAI Configuration (if using OpenAI provider)
OPENAI_API_KEY=sk-...

# Search Configuration
SEARCH_DEFAULT_TOP_K=10
SEARCH_MAX_TOP_K=50
SEARCH_RELEVANCE_THRESHOLD=0.7

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Configuration Models

**Location**: `app/adapters/config/adapter_config.py`

```python
from pydantic import BaseModel, Field
from typing import Literal


class AdapterConfig(BaseModel):
    """
    Configuration for adapter layer.
    
    Extends infrastructure config with adapter-specific settings.
    """
    
    # Database Adapters
    database_connection_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_timeout: int = Field(default=30)
    database_pool_recycle: int = Field(default=3600)  # Recycle connections after 1 hour
    
    # Vector Search Optimization
    vector_index_type: Literal["ivfflat", "hnsw"] = Field(default="ivfflat")
    vector_index_lists: int = Field(default=100)  # For IVFFlat
    vector_index_m: int = Field(default=16)  # For HNSW
    vector_index_ef_construction: int = Field(default=64)  # For HNSW
    
    # Embedding Service
    embedding_timeout_seconds: int = Field(default=30)
    embedding_max_retries: int = Field(default=3)
    embedding_retry_backoff_ms: int = Field(default=1000)
    
    # Performance Tuning
    enable_query_logging: bool = Field(default=False)
    enable_slow_query_logging: bool = Field(default=True)
    slow_query_threshold_ms: float = Field(default=1000.0)
    
    # Caching (for future implementation)
    enable_embedding_cache: bool = Field(default=False)
    embedding_cache_ttl_seconds: int = Field(default=3600)


def get_adapter_config() -> AdapterConfig:
    """Get adapter configuration from environment."""
    return AdapterConfig()
```

### Configuration Validation

```python
# Location: app/adapters/config/validation.py

from app.infrastructure.config import get_embedding_config
from app.adapters.config.adapter_config import get_adapter_config
from app.domain.repositories import EmbeddingError
import logging

logger = logging.getLogger(__name__)


def validate_adapter_configuration():
    """
    Validate adapter configuration at startup.
    
    Checks:
    - Database URL is valid
    - Embedding provider is configured correctly
    - Required environment variables are set
    - Model dimensions match configuration
    
    Raises:
        EmbeddingError: If configuration is invalid
    """
    embedding_config = get_embedding_config()
    adapter_config = get_adapter_config()
    
    # Validate embedding provider
    if embedding_config.provider == "openai" and not embedding_config.api_key:
        raise EmbeddingError("OPENAI_API_KEY is required when using OpenAI provider")
    
    # Validate dimensions match model
    if embedding_config.provider == "local":
        # all-MiniLM-L6-v2 outputs 384 dimensions
        if embedding_config.model == "all-MiniLM-L6-v2" and embedding_config.dimension != 384:
            logger.warning(
                f"Model all-MiniLM-L6-v2 outputs 384 dimensions, "
                f"but configured dimension is {embedding_config.dimension}"
            )
    
    elif embedding_config.provider == "openai":
        # text-embedding-ada-002 outputs 1536 dimensions
        if embedding_config.model == "text-embedding-ada-002" and embedding_config.dimension != 1536:
            logger.warning(
                f"Model text-embedding-ada-002 outputs 1536 dimensions, "
                f"but configured dimension is {embedding_config.dimension}"
            )
    
    logger.info("Adapter configuration validated successfully")
```

---

## Error Handling & Logging

### Error Translation Strategy

```python
# Location: app/adapters/outbound/error_handling.py

from functools import wraps
import logging
from typing import Callable, Any
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.domain.repositories import RepositoryError, EmbeddingError

logger = logging.getLogger(__name__)


def translate_database_errors(func: Callable) -> Callable:
    """
    Decorator to translate SQLAlchemy exceptions to domain exceptions.
    
    Design Pattern: Exception Translation
    - Prevents infrastructure exceptions from leaking to domain
    - Provides consistent error handling across adapters
    - Maintains abstraction boundaries
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}")
            raise RepositoryError(f"Data integrity violation: {str(e)}") from e
        except OperationalError as e:
            logger.error(f"Database operational error: {str(e)}")
            raise RepositoryError(f"Database operation failed: {str(e)}") from e
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}") from e
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {str(e)}")
            raise RepositoryError(f"Unexpected error: {str(e)}") from e
    
    return wrapper


def translate_embedding_errors(func: Callable) -> Callable:
    """
    Decorator to translate embedding service exceptions to domain exceptions.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except EmbeddingError:
            # Already a domain exception, re-raise
            raise
        except Exception as e:
            logger.exception(f"Embedding service error in {func.__name__}: {str(e)}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}") from e
    
    return wrapper
```

### Structured Logging

```python
# Location: app/adapters/outbound/logging_utils.py

import logging
import time
from contextvars import ContextVar
from typing import Optional
from functools import wraps

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredLogger:
    """
    Structured logging for adapters.
    
    Provides consistent logging format with:
    - Request ID for tracing
    - Performance metrics
    - Error details
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_repository_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None
    ):
        """Log repository operation with structured data."""
        request_id = request_id_var.get()
        
        log_data = {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "error": str(error) if error else None
        }
        
        if error:
            self.logger.error(f"Repository operation failed", extra=log_data)
        elif duration_ms and duration_ms > 1000:
            self.logger.warning(f"Slow repository operation", extra=log_data)
        else:
            self.logger.debug(f"Repository operation completed", extra=log_data)
    
    def log_embedding_operation(
        self,
        operation: str,
        text_count: int,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None
    ):
        """Log embedding operation with structured data."""
        request_id = request_id_var.get()
        
        log_data = {
            "operation": operation,
            "text_count": text_count,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "error": str(error) if error else None
        }
        
        if error:
            self.logger.error(f"Embedding operation failed", extra=log_data)
        elif duration_ms:
            avg_time = duration_ms / text_count if text_count > 0 else 0
            log_data["avg_time_per_text_ms"] = avg_time
            self.logger.info(f"Embedding operation completed", extra=log_data)


def log_performance(operation_name: str):
    """
    Decorator to log operation performance.
    
    Usage:
        @log_performance("save_conversation")
        async def save(self, conversation):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(func.__module__)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                if duration_ms > 1000:
                    logger.warning(
                        f"{operation_name} took {duration_ms:.2f}ms",
                        extra={"operation": operation_name, "duration_ms": duration_ms}
                    )
                else:
                    logger.debug(
                        f"{operation_name} completed in {duration_ms:.2f}ms",
                        extra={"operation": operation_name, "duration_ms": duration_ms}
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation_name} failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={"operation": operation_name, "duration_ms": duration_ms, "error": str(e)}
                )
                raise
        
        return wrapper
    return decorator
```

---

## Transaction Management

### Unit of Work Pattern

**Location**: `app/adapters/outbound/persistence/unit_of_work.py`

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.domain.repositories import RepositoryError

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.
    
    Design Pattern: Unit of Work
    - Coordinates multiple repository operations in a transaction
    - Ensures atomicity (all-or-nothing)
    - Simplifies transaction management
    
    Usage:
        async with UnitOfWork(session) as uow:
            await uow.conversations.save(conversation)
            await uow.chunks.save_chunks(chunks)
            await uow.commit()
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._committed = False
        self._rolled_back = False
    
    async def __aenter__(self):
        """Begin transaction."""
        logger.debug("Beginning transaction")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End transaction with automatic rollback on error."""
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
            logger.error(f"Transaction rolled back due to error: {exc_val}")
            return False  # Re-raise exception
        
        # No exception, commit if not already committed/rolled back
        if not self._committed and not self._rolled_back:
            await self.commit()
        
        return True
    
    async def commit(self):
        """Commit transaction."""
        if self._committed or self._rolled_back:
            raise RepositoryError("Transaction already finalized")
        
        try:
            await self.session.commit()
            self._committed = True
            logger.debug("Transaction committed successfully")
        except Exception as e:
            await self.rollback()
            logger.error(f"Commit failed, transaction rolled back: {str(e)}")
            raise RepositoryError(f"Transaction commit failed: {str(e)}") from e
    
    async def rollback(self):
        """Rollback transaction."""
        if self._rolled_back:
            return  # Already rolled back
        
        try:
            await self.session.rollback()
            self._rolled_back = True
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            raise RepositoryError(f"Transaction rollback failed: {str(e)}") from e
    
    async def flush(self):
        """Flush changes without committing."""
        try:
            await self.session.flush()
            logger.debug("Session flushed")
        except Exception as e:
            logger.error(f"Flush failed: {str(e)}")
            raise RepositoryError(f"Session flush failed: {str(e)}") from e
```

### Transaction Management in Use Cases

```python
# Example: Ingest conversation with transaction

class IngestConversationUseCase:
    async def execute(self, request: IngestConversationRequest) -> IngestConversationResponse:
        async with UnitOfWork(self.session) as uow:
            try:
                # Step 1: Save conversation
                conversation = await self.conversation_repo.save(conversation)
                
                # Step 2: Generate embeddings
                chunks_with_embeddings = await self._generate_embeddings(chunks)
                
                # Step 3: Save chunks
                saved_chunks = await self.chunk_repo.save_chunks(chunks_with_embeddings)
                
                # Step 4: Commit transaction
                await uow.commit()
                
                return self._build_response(conversation, saved_chunks)
                
            except Exception as e:
                # Automatic rollback via context manager
                logger.error(f"Ingestion failed: {str(e)}")
                raise
```

---

## Performance Optimization

### Connection Pooling

```python
# Configured in engine creation (app/adapters/outbound/persistence/__init__.py)

engine = create_async_engine(
    database_url,
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections on demand
    pool_timeout=30,  # Seconds to wait for connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connection health before use
    echo=False  # Disable SQL logging in production
)
```

### Batch Operations

**Bulk Insert Optimization**:

```python
# In chunk repository

async def save_chunks(self, chunks: List[ConversationChunk]) -> List[ConversationChunk]:
    """
    Optimized bulk insert.
    
    Performance Comparison:
    - Sequential inserts: ~100 chunks/sec
    - Bulk insert: ~5000 chunks/sec (50x faster)
    """
    if not chunks:
        return []
    
    # Convert to models
    chunk_models = [ConversationChunkModel.from_domain(chunk) for chunk in chunks]
    
    # Bulk add (single transaction)
    self.session.add_all(chunk_models)
    await self.session.flush()
    
    # Bulk refresh (efficient ID retrieval)
    for model in chunk_models:
        await self.session.refresh(model, attribute_names=['id'])
    
    return [model.to_domain() for model in chunk_models]
```

**Batch Embedding Generation**:

```python
# In embedding service

async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
    """
    Batch embedding generation for efficiency.
    
    Performance Comparison:
    - Sequential: ~10 embeddings/sec
    - Batch (size=32): ~200 embeddings/sec (20x faster)
    """
    # Process in optimal batches
    OPTIMAL_BATCH_SIZE = 32
    all_embeddings = []
    
    for i in range(0, len(texts), OPTIMAL_BATCH_SIZE):
        batch = texts[i:i + OPTIMAL_BATCH_SIZE]
        batch_embeddings = await self._generate_batch(batch)
        all_embeddings.extend(batch_embeddings)
    
    return all_embeddings
```

### Query Optimization

**Eager Loading to Prevent N+1 Queries**:

```python
# In conversation repository

async def get_by_id(self, conversation_id: ConversationId) -> Optional[Conversation]:
    """
    Eager load chunks to prevent N+1 query problem.
    
    Without eager loading:
    - 1 query for conversation
    - N queries for chunks (one per chunk)
    
    With eager loading:
    - 1 query for conversation
    - 1 query for all chunks (JOIN)
    """
    stmt = (
        select(ConversationModel)
        .options(selectinload(ConversationModel.chunks))  # Eager load
        .where(ConversationModel.id == conversation_id.value)
    )
    
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**Index Optimization**:

```sql
-- Vector similarity index (in SQLAlchemy model)
CREATE INDEX CONCURRENTLY ix_conversation_chunks_embedding
ON conversation_chunks
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- Benefits:
-- - 10-100x faster vector search
-- - Approximate nearest neighbor (99%+ recall)
-- - Optimal for 10K-1M vectors

-- Composite index for conversation chunks
CREATE INDEX ix_conversation_chunks_conversation_order
ON conversation_chunks (conversation_id, order_index);

-- Benefits:
-- - Fast chunk retrieval by conversation
-- - Efficient ordering
-- - Supports unique constraint
```

### Caching Strategy (Future Enhancement)

```python
# Conceptual design for Phase 4

class CachedEmbeddingService:
    """
    Decorator for embedding service with caching.
    
    Benefits:
    - Avoid regenerating embeddings for identical text
    - Reduce API costs (for OpenAI)
    - Faster response times
    
    Implementation:
    - Redis for distributed caching
    - TTL: 1 hour (configurable)
    - Cache key: hash(text + model_name)
    """
    
    def __init__(self, embedding_service: IEmbeddingService, cache: Cache):
        self.service = embedding_service
        self.cache = cache
    
    async def generate_embedding(self, text: str) -> Embedding:
        # Check cache
        cache_key = self._generate_cache_key(text)
        cached = await self.cache.get(cache_key)
        
        if cached:
            return Embedding(vector=cached)
        
        # Generate and cache
        embedding = await self.service.generate_embedding(text)
        await self.cache.set(cache_key, embedding.vector, ttl=3600)
        
        return embedding
```


---

## Architecture Decision Records

### ADR-001: SQLAlchemy with Async Support

**Status**: Accepted

**Context**:
We need an ORM that supports async operations for non-blocking I/O with PostgreSQL.

**Decision**:
Use SQLAlchemy 2.0+ with async extensions (`asyncpg` driver).

**Consequences**:
- ✅ Native async/await support
- ✅ Mature ORM with extensive documentation
- ✅ Type hints and IDE support
- ✅ Compatible with FastAPI's async paradigm
- ⚠️ Requires careful session management
- ⚠️ Learning curve for async patterns

**Alternatives Considered**:
- `asyncpg` directly: More performant but no ORM features
- `tortoise-orm`: Simpler but less mature
- `sqlmodel`: Cleaner API but limited async support at time of decision

---

### ADR-002: pgvector for Vector Similarity Search

**Status**: Accepted

**Context**:
We need efficient vector similarity search for RAG system.

**Decision**:
Use pgvector extension with IVFFlat indexing for approximate nearest neighbor search.

**Consequences**:
- ✅ Native PostgreSQL integration (no separate vector database)
- ✅ 10-100x faster search with IVFFlat index
- ✅ Simplified deployment (single database)
- ✅ ACID transactions for vector + metadata
- ⚠️ Approximate search (99%+ recall)
- ⚠️ PostgreSQL extension requirement

**Alternatives Considered**:
- `Pinecone`: Managed service but external dependency and cost
- `Weaviate`: Feature-rich but adds deployment complexity
- `Milvus`: Specialized vector DB but operational overhead
- `FAISS`: Fast but in-memory only, no persistence

**Performance Notes**:
- IVFFlat optimal for 10K-1M vectors
- For larger datasets (>1M), consider HNSW index
- Lists parameter tuned to dataset size (sqrt(n) recommended)

---

### ADR-003: Multiple Embedding Provider Support

**Status**: Accepted

**Context**:
Different use cases require different embedding providers (cost, quality, latency).

**Decision**:
Implement adapter pattern with factory for multiple embedding providers:
- Local (SentenceTransformers): Free, good quality, self-hosted
- OpenAI: High quality, paid, API-based
- FastEmbed: Lightweight alternative, free
- LangChain: Future extensibility

**Consequences**:
- ✅ Flexibility to choose provider based on requirements
- ✅ Easy to add new providers
- ✅ Can switch providers without code changes (configuration)
- ✅ Cost optimization (use local for development, OpenAI for production)
- ⚠️ Increased complexity (multiple implementations)
- ⚠️ Different embedding dimensions require database migration

**Implementation Notes**:
- Factory pattern for provider selection
- Configuration-driven selection
- Consistent interface (IEmbeddingService protocol)

---

### ADR-004: Unit of Work Pattern for Transaction Management

**Status**: Accepted

**Context**:
Need to coordinate multiple repository operations in atomic transactions.

**Decision**:
Implement Unit of Work pattern with context manager for transaction lifecycle.

**Consequences**:
- ✅ Explicit transaction boundaries
- ✅ Automatic rollback on error
- ✅ Coordinates multiple repositories
- ✅ Prevents partial updates
- ⚠️ Additional abstraction layer
- ⚠️ Requires discipline to use correctly

**Usage Pattern**:
```python
async with UnitOfWork(session) as uow:
    await repo1.save(entity1)
    await repo2.save(entity2)
    await uow.commit()  # Both succeed or both fail
```

---

### ADR-005: Separation of Embedding Repository

**Status**: Accepted

**Context**:
Embedding operations could be part of ChunkRepository but have distinct concerns.

**Decision**:
Create separate IEmbeddingRepository interface for embedding-specific operations.

**Consequences**:
- ✅ Interface Segregation Principle (ISP)
- ✅ Clear separation of concerns
- ✅ Easier to implement background embedding jobs
- ✅ Can optimize separately from chunk operations
- ⚠️ Slight duplication with ChunkRepository
- ⚠️ More interfaces to implement

**Rationale**:
- Embeddings can be generated asynchronously
- Different access patterns (batch processing vs CRUD)
- Allows for future caching strategies

---

### ADR-006: Domain Entity Mapping Strategy

**Status**: Accepted

**Context**:
Need to convert between domain entities and SQLAlchemy models.

**Decision**:
Implement bidirectional mapping methods on SQLAlchemy models:
- `model.to_domain()`: Model → Domain Entity
- `Model.from_domain(entity)`: Domain Entity → Model

**Consequences**:
- ✅ Clear mapping responsibilities
- ✅ Centralized conversion logic
- ✅ Type-safe conversions
- ⚠️ Couples model to domain (but acceptable in adapter layer)
- ⚠️ Requires maintaining two object representations

**Alternatives Considered**:
- Separate mapper classes: More SOLID but adds complexity
- Domain entities as SQLAlchemy models: Violates hexagonal architecture
- Repository handles mapping: Scatters mapping logic

---

### ADR-007: L2 Distance for Vector Similarity

**Status**: Accepted

**Context**:
pgvector supports multiple distance metrics (L2, cosine, inner product).

**Decision**:
Use L2 distance (`<->` operator) as primary similarity metric.

**Consequences**:
- ✅ Fast with IVFFlat index
- ✅ Intuitive interpretation (distance = dissimilarity)
- ✅ Compatible with most embedding models
- ⚠️ Requires normalized embeddings for best results
- ⚠️ Different from cosine similarity (but highly correlated)

**Conversion to Similarity Score**:
```python
# L2 distance → relevance score (0.0-1.0)
relevance = 1.0 / (1.0 + distance)
```

**Alternatives**:
- Cosine distance: Requires normalization, similar results
- Inner product: Fast but less intuitive

---

### ADR-008: Async Session Scoping

**Status**: Accepted

**Context**:
Database sessions need proper lifecycle management in async context.

**Decision**:
Use scoped sessions tied to request lifecycle (FastAPI dependency injection).

**Consequences**:
- ✅ One session per request
- ✅ Automatic cleanup
- ✅ No session leaks
- ✅ Works well with FastAPI
- ⚠️ Requires explicit dependency injection
- ⚠️ Testing requires session fixtures

**Implementation**:
```python
async def get_session():
    async with session_factory() as session:
        yield session

@app.post("/endpoint")
async def endpoint(session: AsyncSession = Depends(get_session)):
    # Use session
    pass
```

---

### ADR-009: Error Translation at Adapter Boundary

**Status**: Accepted

**Context**:
SQLAlchemy and external service errors should not leak to domain layer.

**Decision**:
Translate all infrastructure exceptions to domain exceptions at adapter boundary.

**Consequences**:
- ✅ Maintains abstraction boundaries
- ✅ Domain layer has no infrastructure dependencies
- ✅ Consistent error handling
- ✅ Enables infrastructure replacement
- ⚠️ May lose some error detail
- ⚠️ Requires comprehensive exception handling

**Exception Hierarchy**:
```
DomainError
├── RepositoryError
│   ├── EntityNotFoundError
│   ├── DuplicateEntityError
│   └── DatabaseConnectionError
└── EmbeddingError
    ├── ModelLoadError
    ├── APIError
    └── DimensionMismatchError
```

---

## Implementation Guidelines

### Phase 3 Implementation Order

**Week 1: Foundation**
1. Create adapter directory structure
2. Implement SQLAlchemy models with mapping methods
3. Setup async session management
4. Implement ConversationRepository adapter
5. Write unit tests for conversation repository

**Week 2: Core Repositories**
6. Implement ChunkRepository adapter
7. Implement VectorSearchRepository adapter
8. Implement EmbeddingRepository adapter
9. Write integration tests for repositories
10. Implement Unit of Work pattern

**Week 3: Embedding Services**
11. Implement base embedding adapter
12. Implement LocalSentenceTransformer adapter
13. Implement OpenAI adapter
14. Implement FastEmbed adapter
15. Implement embedding adapter factory

**Week 4: Integration & Optimization**
16. Integrate adapters with DI container
17. Update application use cases to use adapters
18. Implement error handling and logging
19. Performance testing and optimization
20. Documentation and code review

### Testing Strategy

**Unit Tests**:
- Mock database sessions
- Test domain entity ↔ model mapping
- Test error translation
- Test business logic in adapters

```python
# Example unit test
@pytest.mark.asyncio
async def test_conversation_repository_save():
    # Arrange
    mock_session = Mock(AsyncSession)
    repository = SQLAlchemyConversationRepository(mock_session)
    conversation = create_test_conversation()
    
    # Act
    saved = await repository.save(conversation)
    
    # Assert
    assert saved.id is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
```

**Integration Tests**:
- Use test database (Docker container)
- Test actual database operations
- Test transaction management
- Test vector search functionality

```python
# Example integration test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_search_integration(test_db_session):
    # Arrange
    repo = PgVectorSearchRepository(test_db_session)
    await seed_test_data(test_db_session)
    
    # Act
    query_embedding = create_test_embedding()
    results = await repo.similarity_search(query_embedding, top_k=5)
    
    # Assert
    assert len(results) <= 5
    assert all(isinstance(r[0], ConversationChunk) for r in results)
    assert all(isinstance(r[1], RelevanceScore) for r in results)
```

**Performance Tests**:
- Benchmark embedding generation (sequential vs batch)
- Benchmark vector search (with/without index)
- Test connection pool under load
- Monitor memory usage

### Code Quality Standards

**Type Hints**:
```python
async def save(self, conversation: Conversation) -> Conversation:
    """All public methods must have type hints."""
    pass
```

**Docstrings**:
```python
async def similarity_search(
    self, 
    query_embedding: Embedding, 
    top_k: int = 10
) -> List[Tuple[ConversationChunk, RelevanceScore]]:
    """
    Brief description.
    
    Longer description with implementation notes.
    
    Args:
        query_embedding: Description
        top_k: Description
        
    Returns:
        Description
        
    Raises:
        RepositoryError: When
    """
    pass
```

**Logging**:
```python
logger.debug("Detailed information for debugging")
logger.info("Important business events")
logger.warning("Degraded performance or recoverable errors")
logger.error("Operation failures", exc_info=True)
```

**Error Handling**:
```python
try:
    result = await dangerous_operation()
except SpecificError as e:
    logger.error(f"Specific error: {str(e)}")
    raise DomainError(f"Friendly message: {str(e)}") from e
except Exception as e:
    logger.exception("Unexpected error")
    raise RepositoryError(f"Operation failed: {str(e)}") from e
```

### Migration from Legacy Code

**Step 1: Identify Dependencies**
- Current code in `app/crud.py`, `app/services.py`
- Map functions to domain operations
- Identify use cases

**Step 2: Create Adapters**
- Implement adapter interfaces
- Test adapters independently
- Ensure feature parity

**Step 3: Update Use Cases**
- Replace direct database calls with repository calls
- Replace direct embedding calls with service calls
- Add transaction management

**Step 4: Update DI Container**
- Register adapters
- Configure dependencies
- Test end-to-end

**Step 5: Deprecate Legacy Code**
- Mark old functions as deprecated
- Add warnings
- Update documentation

**Step 6: Remove Legacy Code**
- Delete deprecated functions
- Update tests
- Final verification

### Success Criteria

**Functional Requirements**:
- ✅ All repository interfaces implemented
- ✅ Multiple embedding providers working
- ✅ Vector search returns accurate results
- ✅ Transactions maintain data integrity
- ✅ Error handling prevents data corruption

**Non-Functional Requirements**:
- ✅ Test coverage > 80%
- ✅ All tests passing
- ✅ Vector search < 100ms for 10K chunks
- ✅ Embedding generation < 1s per text (local)
- ✅ Batch operations > 100 items/sec
- ✅ Zero infrastructure dependencies in domain layer

**Quality Requirements**:
- ✅ Code follows SOLID principles
- ✅ No circular dependencies
- ✅ All public APIs documented
- ✅ Logging at appropriate levels
- ✅ Exceptions properly translated
- ✅ Performance benchmarks documented

---

## Appendix A: Directory Structure (Complete)

```
app/
├── domain/                          # Phase 1 ✅
│   ├── __init__.py
│   ├── entities.py
│   ├── value_objects.py
│   ├── repositories.py             # Port interfaces
│   └── services.py
│
├── application/                     # Phase 2 ✅
│   ├── __init__.py
│   ├── dto.py
│   ├── ingest_conversation.py
│   ├── search_conversations.py
│   └── rag_service.py
│
├── adapters/                        # Phase 3 (NEW) 🎯
│   ├── __init__.py
│   │
│   ├── outbound/
│   │   ├── __init__.py
│   │   │
│   │   ├── persistence/
│   │   │   ├── __init__.py          # Session management
│   │   │   ├── sqlalchemy_models.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── chunk_repository.py
│   │   │   ├── vector_search_repository.py
│   │   │   ├── embedding_repository.py
│   │   │   └── unit_of_work.py
│   │   │
│   │   ├── embedding/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── local_sentence_transformer.py
│   │   │   ├── openai_embedding.py
│   │   │   ├── fastembed_embedding.py
│   │   │   ├── langchain_wrapper.py
│   │   │   └── factory.py
│   │   │
│   │   ├── error_handling.py
│   │   └── logging_utils.py
│   │
│   └── config/
│       ├── __init__.py
│       ├── adapter_config.py
│       └── validation.py
│
├── infrastructure/                  # Phase 1 (EXISTING)
│   ├── __init__.py
│   ├── config.py
│   └── container.py                # Extended for Phase 3
│
├── routers/                         # Presentation layer
│   ├── conversations.py
│   └── ingest.py
│
├── models.py                        # Legacy (to be deprecated)
├── crud.py                          # Legacy (to be deprecated)
├── services.py                      # Legacy (to be deprecated)
└── main.py
```

---

## Appendix B: Configuration Examples

### Development Configuration

```bash
# .env.development

# Database (local PostgreSQL with pgvector)
DATABASE_URL=postgresql+psycopg://dev_user:dev_pass@localhost:5432/mcp_dev
DATABASE_ECHO=true
DATABASE_POOL_SIZE=5

# Embedding (local for development)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=16

# Search
SEARCH_DEFAULT_TOP_K=10
SEARCH_RELEVANCE_THRESHOLD=0.7

# Logging
LOG_LEVEL=DEBUG
ENABLE_QUERY_LOGGING=true
```

### Production Configuration

```bash
# .env.production

# Database (managed PostgreSQL)
DATABASE_URL=postgresql+psycopg://prod_user:${DB_PASSWORD}@db.example.com:5432/mcp_prod
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Embedding (OpenAI for quality)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=64
OPENAI_API_KEY=${OPENAI_API_KEY}

# Search
SEARCH_DEFAULT_TOP_K=10
SEARCH_MAX_TOP_K=50
SEARCH_RELEVANCE_THRESHOLD=0.75

# Performance
ENABLE_EMBEDDING_CACHE=true
EMBEDDING_CACHE_TTL_SECONDS=3600

# Logging
LOG_LEVEL=INFO
ENABLE_SLOW_QUERY_LOGGING=true
SLOW_QUERY_THRESHOLD_MS=500.0
```

### Testing Configuration

```bash
# .env.test

# Database (ephemeral test database)
DATABASE_URL=postgresql+psycopg://test:test@localhost:5432/mcp_test
DATABASE_ECHO=false
DATABASE_POOL_SIZE=2

# Embedding (fast local model)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Logging
LOG_LEVEL=WARNING
```

---

## Appendix C: Performance Benchmarks

### Expected Performance Metrics

| Operation | Metric | Target | Notes |
|-----------|--------|--------|-------|
| Save Conversation | Latency | < 50ms | Single conversation with metadata |
| Save Chunks (batch) | Throughput | > 100 chunks/sec | Batch size 32 |
| Vector Search | Latency | < 100ms | 10K chunks, top_k=10 |
| Vector Search | Latency | < 500ms | 100K chunks, top_k=10 |
| Embedding (local) | Throughput | > 50 texts/sec | Batch size 32 |
| Embedding (OpenAI) | Throughput | > 100 texts/sec | Batch size 64, API-dependent |
| Full Ingestion | End-to-end | < 2s | 10 messages, embedding + storage |

### Scalability Targets

| Dataset Size | Vector Search | Notes |
|--------------|--------------|-------|
| 1K chunks | < 10ms | Sequential scan acceptable |
| 10K chunks | < 50ms | IVFFlat index recommended |
| 100K chunks | < 200ms | IVFFlat optimized |
| 1M chunks | < 500ms | Consider HNSW index |

---

## Appendix D: Migration Checklist

### Pre-Implementation

- [ ] Review domain and application layers
- [ ] Understand existing database schema
- [ ] Set up development environment
- [ ] Create test database with pgvector
- [ ] Install dependencies (SQLAlchemy, sentence-transformers, etc.)

### Implementation Phase

- [ ] Create adapter directory structure
- [ ] Implement SQLAlchemy models
- [ ] Implement repository adapters
- [ ] Implement embedding adapters
- [ ] Implement error handling
- [ ] Implement logging utilities
- [ ] Configure DI container
- [ ] Write unit tests (>80% coverage)
- [ ] Write integration tests
- [ ] Update use cases to use adapters

### Testing Phase

- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Performance testing
- [ ] Load testing
- [ ] Security review
- [ ] Code review

### Deployment Phase

- [ ] Update deployment scripts
- [ ] Configure production environment
- [ ] Database migration (if needed)
- [ ] Deploy to staging
- [ ] Smoke tests in staging
- [ ] Deploy to production
- [ ] Monitor performance metrics
- [ ] Document lessons learned

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-06 | Architect Agent | Initial design specification |

---

## References

1. Hexagonal Architecture: https://alistair.cockburn.us/hexagonal-architecture/
2. SQLAlchemy 2.0 Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
3. pgvector Documentation: https://github.com/pgvector/pgvector
4. SentenceTransformers: https://www.sbert.net/
5. OpenAI Embeddings API: https://platform.openai.com/docs/guides/embeddings
6. Clean Architecture (Robert C. Martin)
7. Domain-Driven Design (Eric Evans)

---

**End of Document**

