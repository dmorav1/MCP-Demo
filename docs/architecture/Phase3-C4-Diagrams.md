# Phase 3: Outbound Adapters - C4 Diagrams

**Document Version:** 1.0  
**Date:** November 6, 2025  
**Notation:** C4 Model (Context, Container, Component, Code)

---

## Level 1: System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                         MCP RAG System                              │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │   Web API    │◄─────────── HTTP Requests ───────┐              │
│  │  (FastAPI)   │                                    │              │
│  └──────┬───────┘                                    │              │
│         │                                            │              │
│         │                                    ┌───────┴────────┐    │
│         │                                    │   Users/MCP    │    │
│         │                                    │    Clients     │    │
│         ▼                                    └────────────────┘    │
│  ┌──────────────┐                                                  │
│  │ Application  │                                                  │
│  │    Layer     │                                                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐         ┌──────────────┐                        │
│  │   Adapter    │────────►│  PostgreSQL  │                        │
│  │    Layer     │         │  + pgvector  │                        │
│  │  (Phase 3)   │         └──────────────┘                        │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         │                 ┌──────────────┐                        │
│         └────────────────►│   OpenAI     │                        │
│                           │     API      │                        │
│                           └──────────────┘                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP RAG System                                  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                      FastAPI Application                        │    │
│  │                                                                 │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │    │
│  │  │   Routers    │──►│ Application  │──►│   Domain     │      │    │
│  │  │ (REST API)   │   │  Use Cases   │   │    Layer     │      │    │
│  │  └──────────────┘   └──────┬───────┘   └──────────────┘      │    │
│  │                             │                                  │    │
│  │                             │                                  │    │
│  │                             ▼                                  │    │
│  │                     ┌───────────────┐                         │    │
│  │                     │    Adapters   │                         │    │
│  │                     │   (Phase 3)   │                         │    │
│  │                     └───────┬───────┘                         │    │
│  │                             │                                  │    │
│  └─────────────────────────────┼──────────────────────────────────┘    │
│                                │                                        │
│                    ┌───────────┴──────────┐                            │
│                    │                      │                            │
│                    ▼                      ▼                            │
│         ┌─────────────────┐    ┌──────────────────┐                   │
│         │   PostgreSQL    │    │   Embedding      │                   │
│         │   Database      │    │   Services       │                   │
│         │                 │    │                  │                   │
│         │ • pgvector ext  │    │ • Local Models   │                   │
│         │ • Conversations │    │ • OpenAI API     │                   │
│         │ • Chunks        │    │ • FastEmbed      │                   │
│         │ • Embeddings    │    │ • LangChain      │                   │
│         └─────────────────┘    └──────────────────┘                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Level 3: Component Diagram - Adapter Layer

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Adapter Layer (Phase 3)                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                    Application Use Cases                        │     │
│  │         (IngestConversationUseCase, SearchUseCase)             │     │
│  └────────────────────┬──────────────────┬────────────────────────┘     │
│                       │                  │                               │
│                       ▼                  ▼                               │
│            ┌──────────────────┐  ┌──────────────────┐                   │
│            │   Repository     │  │   Embedding      │                   │
│            │   Interfaces     │  │   Service        │                   │
│            │   (Domain Ports) │  │   Interface      │                   │
│            └──────────┬───────┘  └────────┬─────────┘                   │
│                       │                    │                             │
│    ┌──────────────────┼────────────────────┼──────────────────┐         │
│    │  Adapter Layer   │                    │                  │         │
│    │                  │                    │                  │         │
│    │  ┌───────────────▼──────────┐  ┌──────▼────────────┐   │         │
│    │  │  Persistence Adapters     │  │  Embedding        │   │         │
│    │  │                           │  │  Adapters         │   │         │
│    │  │  ┌─────────────────────┐ │  │                   │   │         │
│    │  │  │ Conversation        │ │  │  ┌──────────────┐ │   │         │
│    │  │  │ Repository          │ │  │  │ Local        │ │   │         │
│    │  │  └─────────────────────┘ │  │  │ Sentence     │ │   │         │
│    │  │                           │  │  │ Transformer  │ │   │         │
│    │  │  ┌─────────────────────┐ │  │  └──────────────┘ │   │         │
│    │  │  │ Chunk Repository    │ │  │                   │   │         │
│    │  │  └─────────────────────┘ │  │  ┌──────────────┐ │   │         │
│    │  │                           │  │  │ OpenAI       │ │   │         │
│    │  │  ┌─────────────────────┐ │  │  │ Embedding    │ │   │         │
│    │  │  │ Vector Search       │ │  │  └──────────────┘ │   │         │
│    │  │  │ Repository          │ │  │                   │   │         │
│    │  │  └─────────────────────┘ │  │  ┌──────────────┐ │   │         │
│    │  │                           │  │  │ FastEmbed    │ │   │         │
│    │  │  ┌─────────────────────┐ │  │  └──────────────┘ │   │         │
│    │  │  │ Embedding           │ │  │                   │   │         │
│    │  │  │ Repository          │ │  │  ┌──────────────┐ │   │         │
│    │  │  └─────────────────────┘ │  │  │ LangChain    │ │   │         │
│    │  │                           │  │  │ Wrapper      │ │   │         │
│    │  │  ┌─────────────────────┐ │  │  └──────────────┘ │   │         │
│    │  │  │ SQLAlchemy Models   │ │  │         ▲         │   │         │
│    │  │  └─────────────────────┘ │  │         │         │   │         │
│    │  │                           │  │  ┌──────┴───────┐ │   │         │
│    │  │  ┌─────────────────────┐ │  │  │ Embedding    │ │   │         │
│    │  │  │ Unit of Work        │ │  │  │ Factory      │ │   │         │
│    │  │  └─────────────────────┘ │  │  └──────────────┘ │   │         │
│    │  └───────────┬───────────────┘  └─────────┬─────────┘   │         │
│    │              │                            │             │         │
│    └──────────────┼────────────────────────────┼─────────────┘         │
│                   │                            │                       │
│                   ▼                            ▼                       │
│         ┌─────────────────┐          ┌──────────────────┐             │
│         │   PostgreSQL    │          │   ML Libraries   │             │
│         │   + pgvector    │          │   & APIs         │             │
│         └─────────────────┘          └──────────────────┘             │
│                                                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Level 4: Code Diagram - Repository Adapter Pattern

```
┌──────────────────────────────────────────────────────────────────────┐
│                   Repository Adapter Pattern                          │
│                                                                       │
│  Domain Layer (app/domain/)                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  <<interface>>                                               │    │
│  │  IConversationRepository                                     │    │
│  │  ┌────────────────────────────────────────────────────┐     │    │
│  │  │ + save(conversation: Conversation): Conversation   │     │    │
│  │  │ + get_by_id(id: ConversationId): Conversation     │     │    │
│  │  │ + get_all(skip: int, limit: int): List[...]       │     │    │
│  │  │ + delete(id: ConversationId): bool                │     │    │
│  │  │ + exists(id: ConversationId): bool                │     │    │
│  │  │ + count(): int                                     │     │    │
│  │  └────────────────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              ▲                                        │
│                              │ implements                            │
│                              │                                        │
│  Adapter Layer (app/adapters/outbound/persistence/)                  │
│  ┌──────────────────────────┴──────────────────────────────────┐    │
│  │  SQLAlchemyConversationRepository                            │    │
│  │  ┌────────────────────────────────────────────────────┐     │    │
│  │  │ - session: AsyncSession                            │     │    │
│  │  │ + save(conversation: Conversation): Conversation   │     │    │
│  │  │ + get_by_id(id: ConversationId): Conversation     │     │    │
│  │  │ + get_all(skip: int, limit: int): List[...]       │     │    │
│  │  │ + delete(id: ConversationId): bool                │     │    │
│  │  │ + exists(id: ConversationId): bool                │     │    │
│  │  │ + count(): int                                     │     │    │
│  │  └────────────────────────────────────────────────────┘     │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                           │ uses                                     │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────┐    │
│  │  ConversationModel (SQLAlchemy)                              │    │
│  │  ┌────────────────────────────────────────────────────┐     │    │
│  │  │ + id: int                                          │     │    │
│  │  │ + scenario_title: str                              │     │    │
│  │  │ + original_title: str                              │     │    │
│  │  │ + url: str                                         │     │    │
│  │  │ + created_at: datetime                             │     │    │
│  │  │ + chunks: relationship                             │     │    │
│  │  │ + to_domain(): Conversation                        │     │    │
│  │  │ + from_domain(conv: Conversation): Model           │     │    │
│  │  └────────────────────────────────────────────────────┘     │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram: Ingest Conversation Flow

```
User           API          UseCase         Repository      Database      Embedding
  │             │              │                │              │           Service
  │─POST─────► │              │                │              │              │
  │  /ingest   │              │                │              │              │
  │            │              │                │              │              │
  │            │──execute──► │                │              │              │
  │            │   (request)  │                │              │              │
  │            │              │                │              │              │
  │            │              │─save(conv)───► │              │              │
  │            │              │                │              │              │
  │            │              │                │──INSERT────► │              │
  │            │              │                │              │              │
  │            │              │                │◄─result───── │              │
  │            │              │◄─conversation─ │              │              │
  │            │              │                │              │              │
  │            │              │─generate_batch────────────────────────────► │
  │            │              │   (chunks)     │              │              │
  │            │              │                │              │              │
  │            │              │◄─embeddings────────────────────────────────  │
  │            │              │                │              │              │
  │            │              │─save_chunks──► │              │              │
  │            │              │  (with embed)  │              │              │
  │            │              │                │              │              │
  │            │              │                │─BULK INSERT─►│              │
  │            │              │                │              │              │
  │            │              │                │◄─result───── │              │
  │            │              │◄─saved chunks─ │              │              │
  │            │              │                │              │              │
  │            │              │─COMMIT────────►│              │              │
  │            │              │                │──COMMIT────► │              │
  │            │              │                │              │              │
  │            │◄─response─── │                │              │              │
  │◄─200 OK──  │              │                │              │              │
  │            │              │                │              │              │
```

---

## Sequence Diagram: Vector Search Flow

```
User           API          UseCase        Repository    VectorSearch    Database
  │             │              │                │         Repository        │
  │─POST─────► │              │                │              │            │
  │  /search   │              │                │              │            │
  │            │              │                │              │            │
  │            │──execute──► │                │              │            │
  │            │   (query)    │                │              │            │
  │            │              │                │              │            │
  │            │              │─generate──────►│              │            │
  │            │              │  embedding     │              │            │
  │            │              │  (query text)  │              │            │
  │            │              │                │              │            │
  │            │              │◄─embedding──── │              │            │
  │            │              │                │              │            │
  │            │              │─similarity_search────────────►│            │
  │            │              │  (embedding, k)               │            │
  │            │              │                               │            │
  │            │              │                               │─SELECT────►│
  │            │              │                               │  (vector)  │
  │            │              │                               │  ORDER BY  │
  │            │              │                               │  distance  │
  │            │              │                               │            │
  │            │              │                               │◄─results───│
  │            │              │◄─chunks + scores──────────────│            │
  │            │              │                               │            │
  │            │              │─rank & filter───────────────► │            │
  │            │              │                               │            │
  │            │◄─response─── │                               │            │
  │◄─200 OK──  │              │                               │            │
  │  (results) │              │                               │            │
```

---

## Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Production Environment                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │                    Application Server                     │      │
│  │                                                            │      │
│  │  ┌─────────────────────────────────────────────────┐     │      │
│  │  │  FastAPI App (Docker Container)                 │     │      │
│  │  │                                                  │     │      │
│  │  │  • Application Layer                            │     │      │
│  │  │  • Domain Layer                                 │     │      │
│  │  │  • Adapter Layer                                │     │      │
│  │  │                                                  │     │      │
│  │  │  Embedding Models (volume mounted):             │     │      │
│  │  │  • all-MiniLM-L6-v2 (384d)                      │     │      │
│  │  └─────────────────────────────────────────────────┘     │      │
│  │                          │                                │      │
│  └──────────────────────────┼────────────────────────────────┘      │
│                             │                                        │
│           ┌─────────────────┼─────────────────┐                     │
│           │                 │                 │                     │
│           ▼                 ▼                 ▼                     │
│  ┌─────────────────┐  ┌──────────┐  ┌──────────────┐              │
│  │   PostgreSQL    │  │  OpenAI  │  │    Redis     │              │
│  │   + pgvector    │  │   API    │  │   (Cache)    │              │
│  │                 │  │          │  │              │              │
│  │  (Managed RDS)  │  │ (External)│  │  (Optional)  │              │
│  └─────────────────┘  └──────────┘  └──────────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Dependency Flow Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                     Dependency Direction                        │
│                 (Following Hexagonal Architecture)              │
│                                                                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Presentation Layer                     │       │
│  │              (FastAPI Routes)                       │       │
│  └─────────────────────┬───────────────────────────────┘       │
│                        │                                        │
│                        │ depends on                             │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────┐       │
│  │             Application Layer                       │       │
│  │             (Use Cases)                             │       │
│  └─────────────────────┬───────────────────────────────┘       │
│                        │                                        │
│                        │ depends on                             │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Domain Layer                           │       │
│  │      (Entities, Value Objects, Interfaces)          │       │
│  └─────────────────────▲───────────────────────────────┘       │
│                        │                                        │
│                        │ implements                             │
│                        │                                        │
│  ┌─────────────────────┴───────────────────────────────┐       │
│  │             Adapter Layer                           │       │
│  │      (Repository & Service Implementations)         │       │
│  └─────────────────────┬───────────────────────────────┘       │
│                        │                                        │
│                        │ uses                                   │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────┐       │
│  │          External Systems                           │       │
│  │     (Database, APIs, Libraries)                     │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  Key Principle: Dependencies point INWARD                      │
│  • Adapters depend on Domain                                   │
│  • Domain never depends on Adapters                            │
│  • External systems are implementation details                 │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

**End of C4 Diagrams**

