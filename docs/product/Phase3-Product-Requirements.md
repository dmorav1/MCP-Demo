# Phase 3: Outbound Adapters - Product Requirements Document

**Document Version:** 1.0  
**Date:** November 6, 2025  
**Author:** Product Owner Agent  
**Status:** Requirements Specification  
**Related Documents:**
- Architecture-Migration-PRD.md
- Phase3-Outbound-Adapters-Design.md
- AGENT_TASK_PLAN.md

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Product Vision](#product-vision)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [API Contract Compatibility](#api-contract-compatibility)
6. [Performance Requirements](#performance-requirements)
7. [Data Consistency Requirements](#data-consistency-requirements)
8. [Embedding Provider Selection Criteria](#embedding-provider-selection-criteria)
9. [Error Handling and Retry Policies](#error-handling-and-retry-policies)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Configuration Management](#configuration-management)
12. [Acceptance Criteria](#acceptance-criteria)
13. [Success Metrics](#success-metrics)

---

## Executive Summary

Phase 3 implements the outbound adapter layer for the MCP RAG Demo hexagonal architecture migration. This phase translates domain port interfaces into concrete implementations that connect to external systems (PostgreSQL + pgvector, embedding services) while maintaining full backward compatibility with existing API contracts.

### Key Objectives

1. **Zero Feature Regression**: All existing functionality must work identically after migration
2. **Backward Compatibility**: Existing API contracts (schemas.py, dto.py) must remain unchanged
3. **Performance Parity**: Performance must match or exceed current implementation
4. **Provider Flexibility**: Support multiple embedding providers with runtime configuration
5. **Production Ready**: Implement comprehensive error handling, logging, and monitoring

### Stakeholders

- **End Users**: Slack bot users, API consumers, MCP clients
- **Development Team**: Backend developers implementing adapters
- **Operations Team**: DevOps managing deployment and monitoring
- **Business Stakeholders**: Product management tracking migration progress

---

## Product Vision

Transform the MCP RAG system into a maintainable, testable, and extensible architecture while preserving all existing functionality and user experience. The adapter layer serves as a clean separation between business logic and infrastructure, enabling future enhancements without core changes.

### User Stories

#### US-001: Conversation Ingestion (Critical)
**As a** Slack bot user  
**I want** to ingest conversation messages into the system  
**So that** they can be searched and used for context-augmented answers

**Acceptance Criteria:**
- Messages are chunked intelligently (by speaker change or size limit)
- Embeddings are generated for all chunks
- Data is persisted to PostgreSQL with pgvector
- Ingestion completes within acceptable time limits
- Errors are handled gracefully with clear messages

#### US-002: Semantic Search (Critical)
**As a** MCP client or API consumer  
**I want** to search conversations using natural language queries  
**So that** I can find relevant conversation context

**Acceptance Criteria:**
- Queries are embedded using the same model as ingestion
- Vector similarity search returns top-k results
- Results are ranked by relevance score
- Search completes within latency requirements
- Handles empty results gracefully

#### US-003: Conversation Management (High)
**As an** API consumer  
**I want** to list, retrieve, and delete conversations  
**So that** I can manage stored conversation data

**Acceptance Criteria:**
- Can paginate through conversations
- Can retrieve individual conversations with chunks
- Can delete conversations with cascade to chunks
- Operations are atomic (transaction-safe)
- Response format matches existing API contracts

#### US-004: Embedding Provider Selection (High)
**As a** system operator  
**I want** to configure which embedding provider to use  
**So that** I can optimize for cost, latency, or quality

**Acceptance Criteria:**
- Support local (sentence-transformers) embeddings
- Support OpenAI embeddings
- Support FastEmbed embeddings
- Support LangChain wrapper for future extensibility
- Configuration via environment variables
- Graceful fallback if provider unavailable

#### US-005: System Health and Monitoring (Medium)
**As a** DevOps engineer  
**I want** comprehensive logging and metrics  
**So that** I can monitor system health and debug issues

**Acceptance Criteria:**
- Structured logging at appropriate levels
- Metrics for ingestion throughput, search latency, errors
- Database connection pool monitoring
- Embedding provider health checks
- Request tracing for debugging

---

## Functional Requirements

### FR-001: Conversation Repository

**Description**: Implement persistent storage for conversation entities

**Requirements:**
- Save new conversations with auto-generated IDs
- Retrieve conversations by ID
- List conversations with pagination (skip/limit)
- Delete conversations (cascade to chunks)
- Check conversation existence
- Count total conversations

**Current Behavior (Legacy)**: Implemented in `crud.py` using SQLAlchemy models
**Target Behavior**: Same functionality via `IConversationRepository` interface

### FR-002: Chunk Repository

**Description**: Implement persistent storage for conversation chunks

**Requirements:**
- Batch save multiple chunks
- Retrieve chunks by conversation ID (ordered by order_index)
- Retrieve individual chunks by ID
- Update chunk embeddings
- Find chunks without embeddings

**Current Behavior (Legacy)**: Implemented in `crud.py` with SQLAlchemy
**Target Behavior**: Same functionality via `IChunkRepository` interface

### FR-003: Vector Search Repository

**Description**: Implement pgvector similarity search

**Requirements:**
- Perform L2 distance-based similarity search
- Support top-k results
- Support relevance threshold filtering
- Return chunks with relevance scores
- Use IVFFlat index for performance

**Current Behavior (Legacy)**: Implemented in `crud.py` using raw SQL with pgvector
**Target Behavior**: Same functionality via `IVectorSearchRepository` interface

### FR-004: Embedding Service

**Description**: Implement embedding generation with multiple providers

**Requirements:**
- **Local Provider**: sentence-transformers (all-MiniLM-L6-v2, 384-d → padded to 1536-d)
- **OpenAI Provider**: text-embedding-ada-002 (1536-d native)
- **FastEmbed Provider**: Alternative local model
- **LangChain Wrapper**: For future LangChain integration
- Batch embedding generation
- Dimension normalization (resize to 1536-d)
- Error handling with fallback to zero vectors

**Current Behavior (Legacy)**: Implemented in `services.py` with local/OpenAI support
**Target Behavior**: Same functionality via `IEmbeddingService` protocol

---

## Performance Requirements

### Baseline Metrics (Legacy Implementation)

From analysis of `crud.py` and `services.py`:

| Operation | Current Performance | Target Performance |
|-----------|-------------------|-------------------|
| Ingest single conversation (10 messages) | ~2-3 seconds | ≤ 3 seconds |
| Ingest batch (100 messages) | ~15-20 seconds | ≤ 20 seconds |
| Search query (top-10) | ~100-200 ms | ≤ 200 ms |
| List conversations (page of 50) | ~50-100 ms | ≤ 100 ms |
| Get single conversation | ~20-50 ms | ≤ 50 ms |
| Delete conversation | ~100-200 ms | ≤ 200 ms |

### Performance Requirements by Feature

#### PR-001: Ingestion Throughput

**Requirement**: Process conversations efficiently without degradation

**Metrics:**
- **Target**: ≥ 5 conversations/second (single worker)
- **Measurement**: Time from API request to database commit
- **Acceptance**: 95th percentile ≤ target

#### PR-002: Search Latency

**Requirement**: Return search results quickly for responsive user experience

**Metrics:**
- **Target**: ≤ 200 ms for top-10 results (p95)
- **Target**: ≤ 500 ms for top-100 results (p95)
- **Measurement**: End-to-end search time (query → response)
- **Acceptance**: 99th percentile ≤ 2x target

#### PR-003: Concurrent User Support

**Requirement**: Support multiple simultaneous users without contention

**Metrics:**
- **Target**: ≥ 10 concurrent API requests
- **Target**: ≥ 5 concurrent ingestion operations
- **Measurement**: Request success rate under load
- **Acceptance**: < 1% error rate, < 5% latency increase

---

## Data Consistency Requirements

### DC-001: Atomic Operations

**Requirement**: Conversation and chunk creation must be atomic

**Scenario**: Ingest conversation with 10 chunks
- **Success**: All 10 chunks saved, conversation committed
- **Failure**: Zero chunks saved, conversation rolled back
- **Never**: Partial save (e.g., 7 of 10 chunks)

**Implementation**: Unit of Work pattern with transaction management

### DC-002: Referential Integrity

**Requirement**: Maintain foreign key relationships

**Rules:**
- Chunks always belong to exactly one conversation
- Cannot create chunk without conversation
- Deleting conversation deletes all chunks (CASCADE)
- Orphan chunks not permitted

**Implementation**: Database foreign key constraints + domain validation

### DC-003: Embedding Consistency

**Requirement**: Embeddings match their text content

**Rules:**
- Embedding generated from current chunk text
- Embedding dimension always 1536
- Embedding provider consistent within conversation
- Re-embedding regenerates for current text

**Implementation**: Embedding generation service + validation

---

## Embedding Provider Selection Criteria

### Provider Comparison Matrix

| Criteria | Local (sentence-transformers) | OpenAI (ada-002) | FastEmbed |
|----------|------------------------------|------------------|-----------|
| **Cost per 1M tokens** | $0 (hardware) | ~$0.10 | $0 (hardware) |
| **Latency (single)** | ~50ms | ~100ms | ~40ms |
| **Latency (batch 32)** | ~20ms/text | ~100ms/text | ~15ms/text |
| **Quality (MTEB)** | 0.58 (good) | 0.61 (excellent) | 0.59 (good) |
| **Dimension** | 384 (padded to 1536) | 1536 (native) | 384 (padded) |
| **Offline capable** | ✅ Yes | ❌ No | ✅ Yes |
| **Rate limits** | None | 3000 RPM | None |

### Selection Guidelines

#### Use Local (sentence-transformers) when:
- ✅ Cost is primary concern
- ✅ Offline operation required
- ✅ Data privacy is critical
- ✅ High throughput needed (no rate limits)
- ⚠️ Sufficient CPU/memory available

**Recommendation**: Default for development and cost-sensitive production

#### Use OpenAI (ada-002) when:
- ✅ Best quality required
- ✅ Budget allows ($0.10 per 1M tokens)
- ✅ Consistent with other OpenAI services
- ⚠️ Internet connectivity reliable
- ⚠️ Rate limits acceptable (3000 RPM)

**Recommendation**: Production use cases prioritizing quality

#### Use FastEmbed when:
- ✅ Fastest local inference needed
- ✅ Lightweight deployment required
- ✅ Minimal dependencies desired
- ⚠️ CPU-only environment

**Recommendation**: Resource-constrained deployments

---

## Error Handling and Retry Policies

### Error Classification

#### Transient Errors (Retry)
- Network timeouts
- Database connection failures
- OpenAI rate limit exceeded (429)
- OpenAI service unavailable (503)
- PostgreSQL deadlock detected

**Strategy**: Exponential backoff retry (3 attempts)

#### Permanent Errors (Fail Fast)
- Invalid API key
- Database schema mismatch
- Domain validation failure
- Out of memory error
- Unsupported model name

**Strategy**: Log error, return meaningful message, no retry

### Retry Policy Specification

#### RP-001: Database Connection Retry

**Scope**: SQLAlchemy connection errors

**Policy:**
- Max attempts: 3
- Base delay: 1 second
- Backoff multiplier: 2x (1s, 2s, 4s)
- Max delay: 10 seconds
- Jitter: ±20%

#### RP-002: OpenAI API Retry

**Scope**: OpenAI embedding generation

**Policy:**
- Max attempts: 3
- Rate limit (429): Wait 60 seconds, retry
- Server error (5xx): Exponential backoff (2s, 4s, 8s)
- Timeout: 30 seconds per request
- Fallback: Local model after 3 failures

---

## Monitoring and Observability

### Logging Requirements

#### LOG-001: Structured Logging

**Format**: JSON-structured logs with consistent schema

**Required Fields:**
- `timestamp`: ISO 8601 format
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `logger`: Module name
- `message`: Human-readable description
- `context`: Operation-specific metadata

#### LOG-002: Operation Logging

**Ingest Operation Example:**
```json
{
  "timestamp": "2025-11-06T19:00:00Z",
  "level": "INFO",
  "logger": "app.application.ingest_conversation",
  "message": "Conversation ingestion completed",
  "context": {
    "conversation_id": "12345",
    "chunks_created": 10,
    "duration_ms": 2347,
    "embedding_provider": "local"
  }
}
```

### Metrics Requirements

#### MET-001: Ingestion Metrics

**Metrics to Track:**
- `ingest_requests_total`: Counter (status: success/failure)
- `ingest_duration_seconds`: Histogram
- `chunks_created_total`: Counter
- `embeddings_generated_total`: Counter (provider)
- `ingestion_errors_total`: Counter (error_type)

#### MET-002: Search Metrics

**Metrics to Track:**
- `search_requests_total`: Counter (status: success/failure)
- `search_duration_seconds`: Histogram
- `search_results_count`: Histogram
- `embedding_generation_duration_seconds`: Histogram
- `vector_search_duration_seconds`: Histogram

### Health Checks

#### HC-001: Liveness Probe

**Endpoint**: `GET /health/live`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T19:00:00Z"
}
```

#### HC-002: Readiness Probe

**Endpoint**: `GET /health/ready`

**Checks:**
- Database connection available
- Embedding provider available
- Disk space available
- Memory usage acceptable

---

## Configuration Management

### Required Configuration Variables

**Database Configuration:**
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:port/db
DATABASE_POOL_SIZE=10
DATABASE_POOL_MAX_OVERFLOW=20
```

**Embedding Configuration:**
```bash
EMBEDDING_PROVIDER=local  # local, openai, fastembed, langchain
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-xxx  # Required if EMBEDDING_PROVIDER=openai
```

**Logging Configuration:**
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration by Environment

#### Development Environment
```bash
DATABASE_URL=postgresql+psycopg://user:password@127.0.0.1:5433/mcpdemo
EMBEDDING_PROVIDER=local
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

#### Production Environment
```bash
DATABASE_URL=postgresql+psycopg://user:pass@prod-db.aws.com:5432/mcpdemo
DATABASE_POOL_SIZE=20
EMBEDDING_PROVIDER=openai
LOG_LEVEL=WARNING
LOG_FORMAT=json
ENABLE_METRICS=true
```

---

## Acceptance Criteria

### AC-001: Functional Parity

**Criterion**: All legacy features work identically with new adapters

**Validation:**
- [ ] Ingest 100 conversations: Same chunks created
- [ ] Search 50 queries: Same results returned
- [ ] List conversations: Same pagination behavior
- [ ] Get conversation: Same data structure
- [ ] Delete conversation: Same cascade behavior

**Pass Condition**: 100% feature parity

### AC-002: API Contract Compatibility

**Criterion**: All API endpoints work with existing clients

**Validation:**
- [ ] Pydantic schemas unchanged
- [ ] Application DTOs unchanged
- [ ] API request/response formats unchanged
- [ ] Error response formats unchanged
- [ ] HTTP status codes unchanged

**Pass Condition**: All contract tests pass

### AC-003: Performance Requirements

**Criterion**: Performance meets or exceeds targets

**Validation:**
- [ ] Ingest throughput ≥ 5 conversations/second
- [ ] Search latency ≤ 200ms (p95)
- [ ] Concurrent users ≥ 10 (no errors)
- [ ] Database queries optimized (< 100ms)

**Pass Condition**: All performance targets met

### AC-004: Code Quality

**Criterion**: Code follows architecture and quality standards

**Validation:**
- [ ] Hexagonal architecture principles followed
- [ ] No domain → adapter dependencies
- [ ] Test coverage ≥ 80%
- [ ] No critical linting errors
- [ ] All functions documented

**Pass Condition**: Architect approval + metrics pass

### AC-005: Error Handling

**Criterion**: Errors handled gracefully with clear messages

**Validation:**
- [ ] Database connection failure → Retry + fallback
- [ ] OpenAI rate limit → Retry + fallback to local
- [ ] Invalid input → Clear validation error
- [ ] Transaction failure → Rollback + error log
- [ ] Timeout → Cancel + error response

**Pass Condition**: All error scenarios handled

---

## Success Metrics

### User-Facing Metrics

**M-001: Zero Downtime Migration**
- **Target**: 100% uptime during Phase 3 deployment
- **Success**: No user-impacting outages

**M-002: No User-Reported Issues**
- **Target**: Zero bug reports related to Phase 3 migration
- **Success**: No regression bugs in 2 weeks post-deployment

**M-003: Performance Improvement**
- **Target**: ≥ 0% (no degradation), ideal ≥ 10% improvement
- **Success**: No user complaints about slowness

### Development Metrics

**M-004: Code Coverage**
- **Target**: ≥ 80% code coverage for adapter layer
- **Success**: Coverage badge green

**M-005: Architecture Compliance**
- **Target**: 100% adherence to hexagonal architecture
- **Success**: Architect approval

### Operational Metrics

**M-006: Deployment Success Rate**
- **Target**: 100% successful deployments
- **Success**: No rollbacks required

**M-007: Error Rate**
- **Target**: < 0.1% request error rate
- **Success**: Error rate below threshold for 1 week

---

## Glossary

**Adapter**: Infrastructure implementation of a domain port interface  
**Hexagonal Architecture**: Architecture pattern separating core logic from infrastructure  
**Port**: Domain interface defining operations without implementation details  
**DTO**: Data Transfer Object - data structure for layer communication  
**Entity**: Domain object with identity and lifecycle  
**Repository**: Abstraction for data persistence  
**Embedding**: Vector representation of text (1536 dimensions)  
**pgvector**: PostgreSQL extension for vector similarity search  

---

**Document Status**: ✅ Ready for Implementation  
**Next Steps**: Architect review → Developer implementation → Tester validation
