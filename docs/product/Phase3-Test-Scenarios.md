# Phase 3: Test Scenarios Document

**Document Version:** 1.0  
**Date:** November 6, 2025  
**Author:** Product Owner Agent  
**Status:** Test Specification  
**Related Documents:**
- Phase3-Product-Requirements.md
- Phase3-Acceptance-Criteria.md

---

## Purpose

This document defines comprehensive test scenarios for validating Phase 3 (Outbound Adapters Implementation). Each scenario includes preconditions, test steps, expected outcomes, and validation criteria to ensure complete functionality and backward compatibility.

---

## Table of Contents

1. [Functional Test Scenarios](#functional-test-scenarios)
2. [Integration Test Scenarios](#integration-test-scenarios)
3. [Performance Test Scenarios](#performance-test-scenarios)
4. [Error Handling Test Scenarios](#error-handling-test-scenarios)
5. [Configuration Test Scenarios](#configuration-test-scenarios)
6. [Backward Compatibility Test Scenarios](#backward-compatibility-test-scenarios)
7. [End-to-End Workflows](#end-to-end-workflows)

---

## Functional Test Scenarios

### TS-FUNC-001: Ingest Single Conversation

**Priority**: Critical  
**Type**: Functional  
**Component**: Conversation Repository, Chunk Repository, Embedding Service

**Preconditions:**
- Database is running and accessible
- Embedding provider is configured (local)
- No existing conversations in database

**Test Data:**
```json
{
  "scenario_title": "Customer Support Chat",
  "original_title": "Ticket #12345",
  "url": "https://example.com/ticket/12345",
  "messages": [
    {
      "text": "Hello, I need help with my account",
      "author_name": "John Doe",
      "author_type": "human",
      "timestamp": "2025-11-06T10:00:00Z"
    },
    {
      "text": "Hi John! I'd be happy to help. What seems to be the issue?",
      "author_name": "Support Agent",
      "author_type": "assistant",
      "timestamp": "2025-11-06T10:01:00Z"
    },
    {
      "text": "I can't log in to my account",
      "author_name": "John Doe",
      "author_type": "human",
      "timestamp": "2025-11-06T10:02:00Z"
    }
  ]
}
```

**Test Steps:**
1. POST /ingest with test data
2. Wait for response (should be < 3 seconds)
3. Extract conversation_id from response
4. GET /conversations/{conversation_id}
5. Verify conversation details
6. Query database directly to verify chunks and embeddings

**Expected Outcomes:**
- HTTP 200 response from /ingest
- Response includes conversation_id and chunks_created count
- chunks_created equals 2 or 3 (depending on chunking logic)
- GET /conversations/{id} returns conversation with all fields
- All chunks have embeddings (1536 dimensions)
- Chunks ordered by order_index (0, 1, 2, ...)
- Author information preserved in chunks
- Timestamps preserved correctly

**Validation Criteria:**
- [ ] Conversation persisted to database
- [ ] Correct number of chunks created
- [ ] All chunks have embeddings
- [ ] Embeddings are 1536-dimensional
- [ ] Response time < 3 seconds
- [ ] No errors logged

---

### TS-FUNC-002: Search Conversations by Query

**Priority**: Critical  
**Type**: Functional  
**Component**: Vector Search Repository, Embedding Service

**Preconditions:**
- At least 10 conversations ingested
- All conversations have embeddings
- Database contains diverse conversation content

**Test Data:**
- Query 1: "account login problem"
- Query 2: "password reset"
- Query 3: "billing inquiry"
- top_k: 5

**Test Steps:**
1. GET /search?q=account+login+problem&top_k=5
2. Record response time
3. Validate response structure
4. Verify result relevance
5. Repeat with different queries

**Expected Outcomes:**
- HTTP 200 response
- Response time < 200ms (p95)
- Results array contains 0-5 results
- Results ordered by relevance_score (descending)
- Each result includes:
  - chunk_id, conversation_id
  - chunk_text, scenario_title
  - author_name, author_type
  - relevance_score (0.0-1.0)
- Most relevant result mentions "account" or "login"

**Validation Criteria:**
- [ ] Response structure correct
- [ ] Results ranked by relevance
- [ ] Relevance scores in valid range
- [ ] Top results semantically relevant to query
- [ ] Response time meets target
- [ ] Empty results handled gracefully

---

### TS-FUNC-003: List Conversations with Pagination

**Priority**: High  
**Type**: Functional  
**Component**: Conversation Repository

**Preconditions:**
- Database contains 100 conversations
- Conversations have varied created_at timestamps

**Test Data:**
- Page 1: skip=0, limit=20
- Page 2: skip=20, limit=20
- Page 3: skip=40, limit=20
- Last page: skip=80, limit=20

**Test Steps:**
1. GET /conversations?skip=0&limit=20
2. Record conversation IDs and created_at timestamps
3. GET /conversations?skip=20&limit=20
4. Verify no duplicate IDs across pages
5. Verify ordering (newest first)
6. GET /conversations?skip=1000&limit=20 (beyond end)

**Expected Outcomes:**
- Each page returns up to 20 conversations
- No duplicates across pages
- Conversations ordered by created_at descending
- Each conversation includes:
  - id, scenario_title, created_at
  - chunks array (may be empty)
- Beyond-end query returns empty array (not error)
- Response time < 100ms per page

**Validation Criteria:**
- [ ] Pagination works correctly
- [ ] No duplicate results
- [ ] Correct ordering maintained
- [ ] Edge cases handled (skip > count)
- [ ] Response time acceptable
- [ ] All fields present

---

### TS-FUNC-004: Delete Conversation with Cascade

**Priority**: High  
**Type**: Functional  
**Component**: Conversation Repository, Chunk Repository

**Preconditions:**
- Conversation exists with ID=123
- Conversation has 5 chunks
- Chunks have embeddings

**Test Steps:**
1. GET /conversations/123 (verify exists)
2. Count chunks in database for conversation_id=123
3. DELETE /conversations/123
4. GET /conversations/123 (should be 404)
5. Query database for chunks with conversation_id=123
6. Attempt DELETE /conversations/123 again

**Expected Outcomes:**
- First GET returns 200 with conversation data
- DELETE returns 200 with success message
- Second GET returns 404 (not found)
- No chunks remain with conversation_id=123
- Second DELETE returns 404 or False (not found)
- No orphan data in database

**Validation Criteria:**
- [ ] Conversation deleted successfully
- [ ] All associated chunks deleted (cascade)
- [ ] No orphan chunks remain
- [ ] Subsequent retrieval returns 404
- [ ] Idempotent delete handled correctly
- [ ] Foreign key constraints maintained

---

### TS-FUNC-005: Retrieve Single Conversation

**Priority**: High  
**Type**: Functional  
**Component**: Conversation Repository, Chunk Repository

**Preconditions:**
- Conversation exists with ID=456
- Conversation has 8 chunks with embeddings

**Test Steps:**
1. GET /conversations/456
2. Validate response structure
3. Count chunks in response
4. Verify chunk ordering
5. GET /conversations/999999 (non-existent)

**Expected Outcomes:**
- Existing conversation returns 200
- Response includes all conversation fields
- Chunks array contains 8 elements
- Chunks ordered by order_index (0-7)
- Each chunk includes all metadata
- Embeddings excluded from response (too large)
- Non-existent conversation returns 404
- Response time < 50ms

**Validation Criteria:**
- [ ] Correct conversation returned
- [ ] All chunks included and ordered
- [ ] Metadata complete
- [ ] Embeddings not in response
- [ ] 404 for non-existent conversation
- [ ] Response time acceptable

---

## Integration Test Scenarios

### TS-INT-001: Full Ingestion Pipeline

**Priority**: Critical  
**Type**: Integration  
**Components**: All adapters (end-to-end)

**Preconditions:**
- Clean database
- All services running

**Test Steps:**
1. Ingest conversation via API
2. Verify conversation saved to database
3. Verify chunks created
4. Verify embeddings generated
5. Verify embeddings stored in database
6. Verify vector index includes new embeddings
7. Search for content from ingested conversation
8. Verify search returns the conversation

**Expected Outcomes:**
- Complete pipeline executes successfully
- Data flows from API → Use Case → Adapters → Database
- Embedding generation completes
- Vector search finds ingested content
- No errors at any step
- All transactions committed

**Validation Criteria:**
- [ ] End-to-end flow works
- [ ] All adapters invoked correctly
- [ ] Data persisted completely
- [ ] Searchable immediately after ingestion
- [ ] No errors or warnings
- [ ] Performance acceptable

---

### TS-INT-002: Multi-Provider Embedding Generation

**Priority**: High  
**Type**: Integration  
**Component**: Embedding Service Adapters

**Preconditions:**
- Local model installed
- OpenAI API key configured (if available)
- FastEmbed installed

**Test Steps:**
1. Configure EMBEDDING_PROVIDER=local
2. Generate embedding for "test text"
3. Verify 1536-dimensional vector returned
4. Switch to EMBEDDING_PROVIDER=openai (if key available)
5. Generate embedding for same text
6. Verify 1536-dimensional vector returned
7. Switch to EMBEDDING_PROVIDER=fastembed
8. Generate embedding for same text

**Expected Outcomes:**
- All providers generate embeddings
- All embeddings are 1536-dimensional
- Local provider uses sentence-transformers
- OpenAI provider uses ada-002 API
- FastEmbed provider uses fastembed library
- Each provider returns different vectors (provider-specific)
- Configuration switch works without restart

**Validation Criteria:**
- [ ] All providers functional
- [ ] Correct dimension for all
- [ ] Provider selection via config works
- [ ] No errors with any provider
- [ ] Performance within expected range

---

### TS-INT-003: Database Transaction Rollback

**Priority**: High  
**Type**: Integration  
**Component**: Unit of Work, Repository Adapters

**Preconditions:**
- Database supports transactions
- Test database isolated

**Test Steps:**
1. Start ingestion process
2. Inject failure after conversation save, before chunk save
3. Verify transaction rolled back
4. Query database for conversation (should not exist)
5. Verify no partial data saved

**Expected Outcomes:**
- Transaction rollback triggered on error
- No conversation in database
- No chunks in database
- Database in consistent state
- Error logged with details
- User receives error response

**Validation Criteria:**
- [ ] Transaction rollback works
- [ ] No partial data persisted
- [ ] Database consistency maintained
- [ ] Error handling correct
- [ ] Logs indicate rollback

---

### TS-INT-004: Connection Pool Management

**Priority**: Medium  
**Type**: Integration  
**Component**: Database Connection Pool

**Preconditions:**
- Connection pool configured (max 20)
- Load testing tools available

**Test Steps:**
1. Monitor connection pool (start: 0 active)
2. Execute 5 concurrent requests
3. Verify connections acquired and released
4. Execute 30 concurrent requests (> pool size)
5. Verify pool overflow handling
6. Wait for requests to complete
7. Verify all connections released
8. Check for connection leaks

**Expected Outcomes:**
- Connections acquired on demand
- Connections reused across requests
- Pool size respected (max 20)
- Overflow handled gracefully (queueing)
- All connections released after use
- No connection leaks
- No connection exhaustion errors

**Validation Criteria:**
- [ ] Pool management works correctly
- [ ] No connection leaks
- [ ] Overflow handled
- [ ] Performance stable under load
- [ ] Metrics show pool usage

---

## Performance Test Scenarios

### TS-PERF-001: Ingestion Throughput

**Priority**: High  
**Type**: Performance  
**Target**: ≥ 5 conversations/second

**Preconditions:**
- Clean database
- Local embedding provider (fastest)
- No rate limits

**Test Setup:**
- 100 conversations, 10 messages each
- Sequential ingestion
- Measure total time and per-conversation time

**Test Steps:**
1. Record start time
2. Ingest 100 conversations sequentially
3. Record end time
4. Calculate throughput (conversations/second)
5. Calculate average time per conversation

**Expected Outcomes:**
- Total time ≤ 20 seconds (100 / 5 = 20s)
- Throughput ≥ 5 conversations/second
- Average time per conversation ≤ 200ms
- No errors during ingestion
- Memory usage stable (no leaks)

**Validation Criteria:**
- [ ] Throughput meets target (≥ 5 conv/s)
- [ ] Performance consistent across all conversations
- [ ] No degradation over time
- [ ] Resource usage acceptable

---

### TS-PERF-002: Search Latency

**Priority**: Critical  
**Type**: Performance  
**Target**: ≤ 200ms (p95)

**Preconditions:**
- Database contains 10,000 chunks with embeddings
- Vector index created and warmed up

**Test Setup:**
- 100 search queries
- Measure latency for each
- Calculate percentiles (p50, p95, p99)

**Test Steps:**
1. Execute 100 search queries (top_k=10)
2. Record latency for each
3. Calculate p50, p95, p99 latencies
4. Identify slowest queries
5. Analyze query plans (EXPLAIN)

**Expected Outcomes:**
- p50 latency ≤ 100ms
- p95 latency ≤ 200ms
- p99 latency ≤ 500ms
- All queries use vector index
- No table scans
- Consistent performance across queries

**Validation Criteria:**
- [ ] p95 latency meets target (≤ 200ms)
- [ ] No outliers (> 1 second)
- [ ] Index used effectively
- [ ] Performance stable

---

### TS-PERF-003: Concurrent Load

**Priority**: High  
**Type**: Performance  
**Target**: 10 concurrent users, < 1% error rate

**Preconditions:**
- System running in production-like environment
- Load testing tool configured (e.g., Locust)

**Test Setup:**
- 10 concurrent users
- Mix: 20% ingest, 80% search
- Duration: 10 minutes
- Ramp-up: 1 minute

**Test Steps:**
1. Start load test with 10 virtual users
2. Monitor error rate, response times, resource usage
3. Verify no errors occur
4. Verify response times within targets
5. Check database connection pool usage
6. Monitor CPU and memory usage

**Expected Outcomes:**
- Error rate < 1%
- Ingest p95 latency ≤ 3 seconds
- Search p95 latency ≤ 200ms
- No connection pool exhaustion
- CPU usage < 80%
- Memory usage < 80%
- No crashes or restarts

**Validation Criteria:**
- [ ] Error rate below 1%
- [ ] Response times within targets
- [ ] Resource utilization acceptable
- [ ] System stability maintained
- [ ] No degradation over time

---

### TS-PERF-004: Large Conversation Handling

**Priority**: Medium  
**Type**: Performance  
**Scenario**: Handle conversations with 100+ messages

**Preconditions:**
- Database running
- Embedding provider available

**Test Data:**
- Conversation with 150 messages
- Average message length: 100 words
- Expected chunks: ~30-50

**Test Steps:**
1. Ingest large conversation
2. Measure ingestion time
3. Verify all chunks created
4. Verify all embeddings generated
5. Search for content from conversation
6. Retrieve conversation with all chunks

**Expected Outcomes:**
- Ingestion completes successfully
- Ingestion time ≤ 30 seconds
- All chunks created with embeddings
- Search finds relevant chunks
- Retrieval returns all chunks
- No memory issues
- No timeout errors

**Validation Criteria:**
- [ ] Large conversations handled
- [ ] Performance acceptable
- [ ] No errors or timeouts
- [ ] All data persisted correctly
- [ ] Searchable after ingestion

---

## Error Handling Test Scenarios

### TS-ERR-001: Database Connection Failure

**Priority**: Critical  
**Type**: Error Handling  
**Component**: Connection Retry Logic

**Preconditions:**
- Application running
- Database accessible

**Test Steps:**
1. Stop database service
2. Attempt to ingest conversation
3. Observe retry behavior
4. Check error logs
5. Restart database
6. Verify automatic recovery
7. Retry failed operation

**Expected Outcomes:**
- Connection failure detected
- Retry attempted 3 times with exponential backoff
- User receives error response after retries exhausted
- Error logged with details (connection refused)
- After database restart, next request succeeds
- No data corruption

**Validation Criteria:**
- [ ] Retry logic executes
- [ ] Exponential backoff observed
- [ ] Clear error message to user
- [ ] Error logged appropriately
- [ ] Automatic recovery works
- [ ] No data corruption

---

### TS-ERR-002: OpenAI Rate Limit

**Priority**: High  
**Type**: Error Handling  
**Component**: Embedding Service

**Preconditions:**
- EMBEDDING_PROVIDER=openai
- OpenAI API key configured

**Test Steps:**
1. Configure very low rate limit (testing)
2. Ingest multiple conversations rapidly
3. Trigger rate limit error (429)
4. Observe retry and fallback behavior
5. Verify fallback to local provider
6. Check error logs

**Expected Outcomes:**
- Rate limit error (429) detected
- Retry after 60 seconds attempted
- After retries exhausted, falls back to local provider
- Ingestion continues with local embeddings
- User notified of degraded service
- Warning logged about fallback

**Validation Criteria:**
- [ ] Rate limit error detected
- [ ] Retry with wait executed
- [ ] Fallback to local provider works
- [ ] Ingestion still succeeds
- [ ] Appropriate warnings logged
- [ ] User informed of fallback

---

### TS-ERR-003: Invalid Input Validation

**Priority**: High  
**Type**: Error Handling  
**Component**: Input Validation

**Test Data:**
- Empty messages array
- Messages with no text
- Negative top_k value
- Query exceeding max length
- Invalid embedding provider name

**Test Steps:**
1. POST /ingest with empty messages
2. POST /ingest with message missing text field
3. GET /search?q=test&top_k=-5
4. GET /search?q=[10,000 character string]
5. Configure EMBEDDING_PROVIDER=invalid

**Expected Outcomes:**
- HTTP 400 (Bad Request) for all invalid inputs
- Clear error messages indicating issue
- Validation errors include field name
- No exceptions thrown
- No partial processing
- Validation occurs at API layer

**Validation Criteria:**
- [ ] Invalid inputs rejected
- [ ] Appropriate status codes (400)
- [ ] Clear error messages
- [ ] No crashes or exceptions
- [ ] Validation comprehensive

---

### TS-ERR-004: Transaction Rollback on Failure

**Priority**: Critical  
**Type**: Error Handling  
**Component**: Unit of Work

**Preconditions:**
- Database supports transactions

**Test Steps:**
1. Start ingestion
2. Inject failure after conversation save
3. Verify rollback occurs
4. Check database state (should be unchanged)
5. Retry with valid data
6. Verify success

**Expected Outcomes:**
- Transaction starts
- Error occurs mid-transaction
- Rollback executed automatically
- No partial data in database
- Database consistent
- Error logged with transaction details
- Retry succeeds

**Validation Criteria:**
- [ ] Rollback executes on error
- [ ] No partial data persisted
- [ ] Database consistency maintained
- [ ] Error details logged
- [ ] Retry successful

---

## Configuration Test Scenarios

### TS-CFG-001: Environment Configuration Loading

**Priority**: High  
**Type**: Configuration  
**Component**: Configuration Management

**Test Environments:**
- Development
- Staging
- Production

**Test Steps:**
1. Deploy to development with .env.development
2. Verify DATABASE_URL points to local database
3. Verify EMBEDDING_PROVIDER=local
4. Deploy to staging with .env.staging
5. Verify DATABASE_URL points to staging database
6. Verify EMBEDDING_PROVIDER=openai
7. Deploy to production with .env.production
8. Verify all production settings

**Expected Outcomes:**
- Each environment loads correct configuration
- Development uses local database and embeddings
- Staging uses staging database and OpenAI
- Production uses production database and settings
- No cross-environment configuration leakage
- Secrets loaded from secure storage (staging/prod)

**Validation Criteria:**
- [ ] Environment-specific configs load correctly
- [ ] No config leakage between environments
- [ ] Secrets management works
- [ ] Validation passes for each environment
- [ ] Application starts successfully

---

### TS-CFG-002: Configuration Validation

**Priority**: High  
**Type**: Configuration  
**Component**: Startup Validation

**Test Cases:**
- Missing DATABASE_URL
- Invalid EMBEDDING_PROVIDER
- Missing OPENAI_API_KEY when provider=openai
- Invalid DATABASE_POOL_SIZE (negative)
- Missing required variables

**Test Steps:**
1. Remove DATABASE_URL from environment
2. Start application
3. Verify startup fails with clear error
4. Restore DATABASE_URL, set EMBEDDING_PROVIDER=invalid
5. Start application
6. Verify validation error

**Expected Outcomes:**
- Startup fails if required config missing
- Clear error message indicates which config is invalid
- Error message suggests fix
- Application does not start in invalid state
- Logs show validation error

**Validation Criteria:**
- [ ] Invalid config detected at startup
- [ ] Clear error messages
- [ ] Application fails fast
- [ ] No partial startup state
- [ ] Validation comprehensive

---

## Backward Compatibility Test Scenarios

### TS-COMPAT-001: API Contract Compatibility

**Priority**: Critical  
**Type**: Backward Compatibility  
**Component**: API Endpoints

**Preconditions:**
- Legacy API tests available
- Test data from legacy system

**Test Steps:**
1. Run all legacy API tests against new implementation
2. Compare request/response formats
3. Verify status codes unchanged
4. Verify error response formats unchanged
5. Test with legacy client code

**Expected Outcomes:**
- All legacy API tests pass
- Request formats identical
- Response formats identical
- Status codes unchanged
- Error responses compatible
- Legacy clients work without changes

**Validation Criteria:**
- [ ] 100% legacy test pass rate
- [ ] No breaking API changes
- [ ] Response schemas identical
- [ ] Error formats unchanged
- [ ] Legacy clients compatible

---

### TS-COMPAT-002: Data Model Compatibility

**Priority**: Critical  
**Type**: Backward Compatibility  
**Component**: Database Schema

**Preconditions:**
- Database contains legacy data

**Test Steps:**
1. Query legacy conversations
2. Verify all fields readable
3. Query legacy chunks
4. Verify all embeddings readable
5. Perform search on legacy data
6. Ingest new conversation
7. Verify old and new data coexist

**Expected Outcomes:**
- All legacy data readable
- Legacy embeddings compatible
- Legacy conversations searchable
- New data uses same schema
- No migration required
- Mixed old/new data works together

**Validation Criteria:**
- [ ] Legacy data readable
- [ ] Legacy embeddings work
- [ ] Search includes old and new data
- [ ] No data migration needed
- [ ] Schema fully compatible

---

## End-to-End Workflows

### TS-E2E-001: Complete RAG Workflow

**Priority**: Critical  
**Type**: End-to-End  
**Scenario**: Ingest → Search → Retrieve → Answer

**Test Steps:**
1. **Ingest Phase**
   - Ingest 5 conversations about different topics
   - Verify all conversations ingested successfully
   
2. **Search Phase**
   - Search for "password reset"
   - Verify relevant conversations returned
   - Record top result conversation_id
   
3. **Retrieve Phase**
   - GET /conversations/{conversation_id}
   - Verify full conversation retrieved
   
4. **Answer Phase** (Future: MCP Server)
   - Use retrieved context for RAG
   - Verify context relevant to query

**Expected Outcomes:**
- Complete workflow executes successfully
- Each phase builds on previous
- Data flows correctly through pipeline
- Relevant context retrieved
- No errors at any stage

**Validation Criteria:**
- [ ] All phases complete successfully
- [ ] Data flows correctly
- [ ] Results relevant and accurate
- [ ] Performance acceptable end-to-end
- [ ] User experience smooth

---

### TS-E2E-002: Multi-User Concurrent Workflow

**Priority**: High  
**Type**: End-to-End  
**Scenario**: Multiple users ingesting and searching simultaneously

**Test Steps:**
1. User A ingests conversation A
2. User B ingests conversation B (simultaneously)
3. User C searches for content from A (simultaneously)
4. User D searches for content from B (simultaneously)
5. Verify all operations succeed
6. Verify no data corruption
7. Verify searches return correct results

**Expected Outcomes:**
- All operations complete successfully
- No database deadlocks
- No connection pool exhaustion
- Searches return correct user-specific results
- Data integrity maintained
- Performance acceptable under load

**Validation Criteria:**
- [ ] Concurrent operations successful
- [ ] No errors or conflicts
- [ ] Data integrity maintained
- [ ] Performance stable
- [ ] Results isolated correctly

---

## Test Execution Summary

### Test Coverage Summary

| Category | Scenarios | Priority Critical | Priority High | Priority Medium |
|----------|-----------|-------------------|---------------|-----------------|
| Functional | 5 | 2 | 3 | 0 |
| Integration | 4 | 1 | 3 | 0 |
| Performance | 4 | 1 | 2 | 1 |
| Error Handling | 4 | 2 | 2 | 0 |
| Configuration | 2 | 0 | 2 | 0 |
| Backward Compatibility | 2 | 2 | 0 | 0 |
| End-to-End | 2 | 1 | 1 | 0 |
| **Total** | **23** | **9** | **13** | **1** |

### Execution Order

**Phase 1: Core Functionality (Critical)**
1. TS-FUNC-001: Ingest Single Conversation
2. TS-FUNC-002: Search Conversations
3. TS-INT-001: Full Ingestion Pipeline
4. TS-ERR-001: Database Connection Failure
5. TS-COMPAT-001: API Contract Compatibility
6. TS-COMPAT-002: Data Model Compatibility

**Phase 2: Extended Functionality (High Priority)**
7. TS-FUNC-003: List Conversations
8. TS-FUNC-004: Delete Conversation
9. TS-INT-002: Multi-Provider Embeddings
10. TS-INT-003: Transaction Rollback
11. TS-PERF-002: Search Latency
12. TS-ERR-002: OpenAI Rate Limit
13. TS-CFG-001: Environment Configuration

**Phase 3: Performance and Stability**
14. TS-PERF-001: Ingestion Throughput
15. TS-PERF-003: Concurrent Load
16. TS-INT-004: Connection Pool Management
17. TS-E2E-002: Multi-User Concurrent Workflow

**Phase 4: Edge Cases and Validation**
18-23: Remaining scenarios

---

**Document Status**: ✅ Ready for Testing  
**Next Steps**: Execute test scenarios → Record results → Update acceptance criteria
