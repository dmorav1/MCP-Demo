# Known Issues and Limitations

**Document Version:** 1.0  
**Date:** November 12, 2025  
**Author:** Tester Agent  
**Related:** API_VALIDATION_REPORT.md

---

## Summary

This document lists all known issues, limitations, and areas for improvement discovered during comprehensive API validation testing. Issues are prioritized by severity and impact.

---

## Critical Issues

**None identified** ✅

---

## High Severity Issues

**None identified** ✅

---

## Medium Severity Issues

### Issue #1: Unhandled ValueError in Empty Messages Validation

**Status:** 🐛 Confirmed Bug  
**Severity:** Medium  
**Component:** API Layer - Conversation Ingest Endpoint  
**Discovered:** API Validation Testing (test_ingest_empty_messages)

**Description:**  
When a POST request to `/conversations/ingest` contains an empty messages array, the DTO validation raises a `ValueError` that is not caught by the API error handlers, resulting in a 500 Internal Server Error instead of a proper 400/422 validation error.

**Steps to Reproduce:**
```bash
curl -X POST http://localhost:8000/conversations/ingest \
  -H "Content-Type: application/json" \
  -d '{"messages": []}'
```

**Expected Behavior:**
- HTTP 400 Bad Request or 422 Unprocessable Entity
- Clear error message: "messages cannot be empty"
- Proper error response format

**Actual Behavior:**
- HTTP 500 Internal Server Error
- Generic error message
- ValueError in logs: "messages cannot be empty"

**Impact:**
- Poor user experience
- Unclear error messages
- Makes debugging harder for API consumers

**Root Cause:**
- DTO validation in `IngestConversationRequest.__post_init__` raises `ValueError`
- No error handler middleware catches `ValueError` from DTO validation
- Error propagates to FastAPI's default error handler

**Recommended Fix:**
```python
# In app/adapters/inbound/api/error_handlers.py

@app.exception_handler(ValueError)
async def validation_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": "validation_error"}
    )
```

**Test Coverage:**
- Test: `tests/test_api_comprehensive.py::TestInvalidInputs::test_ingest_empty_messages`
- Status: XFAIL (expected failure documenting the bug)

**Estimated Effort:** 2-4 hours

---

### Issue #2: Unhandled ValueError in Empty Query Validation

**Status:** 🐛 Confirmed Bug  
**Severity:** Medium  
**Component:** API Layer - Search Endpoint  
**Discovered:** API Validation Testing (test_search_empty_query)

**Description:**  
When a POST request to `/search` contains an empty query string, the DTO validation raises a `ValueError` that is not caught by the API error handlers, resulting in a 500 Internal Server Error instead of a proper 400/422 validation error.

**Steps to Reproduce:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "", "top_k": 5}'
```

**Expected Behavior:**
- HTTP 400 Bad Request or 422 Unprocessable Entity
- Clear error message: "query cannot be empty"
- Proper error response format

**Actual Behavior:**
- HTTP 500 Internal Server Error
- Generic error message
- ValueError in logs: "query cannot be empty"

**Impact:**
- Poor user experience
- Unclear error messages
- Makes debugging harder for API consumers

**Root Cause:**
- DTO validation in `SearchConversationRequest.__post_init__` raises `ValueError`
- No error handler middleware catches `ValueError` from DTO validation
- Error propagates to FastAPI's default error handler

**Recommended Fix:**
Same as Issue #1 - add ValueError handler middleware

**Test Coverage:**
- Test: `tests/test_api_comprehensive.py::TestInvalidInputs::test_search_empty_query`
- Status: XFAIL (expected failure documenting the bug)

**Estimated Effort:** 2-4 hours (can be fixed together with Issue #1)

---

## Low Severity Issues

### Issue #3: RAG MCP Tool Not Implemented

**Status:** 📋 Planned Feature  
**Severity:** Low  
**Component:** MCP Server  
**Discovered:** MCP Server Testing

**Description:**  
The MCP server does not have an `ask_question` tool for RAG functionality, even though the RAG API endpoint exists and works correctly.

**Impact:**
- Claude Desktop users cannot use RAG functionality via MCP protocol
- Must use REST API instead
- Limits MCP integration capabilities

**Recommended Implementation:**
```python
@mcp_app.tool()
async def ask_question(context: Context, query: str, top_k: int = 5, conversation_id: str = None) -> dict:
    """
    Ask a question using RAG (Retrieval-Augmented Generation).
    """
    await context.info(f"❓ [MCP] Asking question: '{query}'")
    
    rag_service = container.resolve(RAGService)
    result = await rag_service.ask(query, top_k, conversation_id)
    
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result["confidence"],
        "metadata": result["metadata"]
    }
```

**Test Coverage:**
- Test: `tests/test_mcp_server.py::TestMCPToolInvocations::test_ask_question_tool`
- Status: SKIPPED (feature not yet implemented)

**Estimated Effort:** 4-6 hours

---

## Limitations

### Limitation #1: Pagination Tests Require Database

**Component:** Test Infrastructure  
**Description:**  
Pagination tests for the `/conversations` list endpoint are skipped because they require a real database with test data. Current test infrastructure uses mocked dependencies.

**Workaround:**
- Use integration tests with real database
- Set up test database fixtures
- Create sample data generators

**Impact:** Low - pagination functionality works but lacks automated testing

**Test Coverage:**
- Test: `tests/test_api_comprehensive.py::TestPagination::test_conversations_list_pagination`
- Status: SKIPPED

---

### Limitation #2: Performance Tests Use Mocked Dependencies

**Component:** Performance Testing  
**Description:**  
Current performance tests use mocked dependencies (no real database, no real LLM API calls), so they measure API layer performance only, not real-world end-to-end performance.

**Impact:**
- Performance metrics are not representative of production
- Cannot identify database bottlenecks
- Cannot measure real LLM API latency

**Recommendation:**
- Create separate performance test suite
- Use real infrastructure (database, embedding models)
- Measure P50, P95, P99 latencies
- Test with realistic data volumes

**Estimated Effort:** 8-12 hours

---

### Limitation #3: No Authentication/Authorization Tests

**Component:** Security Testing  
**Status:** Feature not implemented  
**Description:**  
Authentication and authorization are not yet implemented in the API, so there are no tests for these security features.

**Impact:** None currently (feature doesn't exist yet)

**When Implemented, Should Test:**
- Token validation
- Token expiration
- Invalid token handling
- Authorization rules
- Role-based access control
- API key management

**Estimated Effort:** 6-8 hours (after feature implementation)

---

### Limitation #4: No Rate Limiting Tests

**Component:** Security Testing  
**Status:** Feature not implemented  
**Description:**  
Rate limiting is not yet implemented in the API, so there are no tests for rate limiting functionality.

**Impact:** None currently (feature doesn't exist yet)

**When Implemented, Should Test:**
- Request rate limits per endpoint
- Rate limit headers (X-RateLimit-*)
- Rate limit exceeded responses (429 status)
- Per-user/per-API-key rate limits
- Rate limit reset behavior

**Estimated Effort:** 4-6 hours (after feature implementation)

---

### Limitation #5: No OpenAPI Schema Validation

**Component:** Contract Testing  
**Description:**  
While the API has response schema validation tests, there's no automated validation against an OpenAPI specification document.

**Impact:** Medium - manual schema validation required

**Recommendation:**
- Generate OpenAPI schema from FastAPI
- Add schema validation to CI/CD
- Validate request/response against schema
- Check for breaking changes

**Estimated Effort:** 4-6 hours

---

### Limitation #6: No Real MCP Client Integration Tests

**Component:** MCP Server Testing  
**Description:**  
MCP server tests use mocked dependencies and don't test with a real MCP client (Claude Desktop).

**Impact:**
- Cannot test actual MCP protocol wire format
- Cannot test Claude Desktop integration
- Cannot test MCP transport layer (stdio/SSE)

**Recommendation:**
- Add integration tests with MCP test client
- Test stdio and SSE transport modes
- Test with Claude Desktop configuration
- Verify tool invocations from actual client

**Estimated Effort:** 6-10 hours

---

## Technical Debt

### Debt #1: Pydantic Config Deprecation Warnings

**Severity:** Low  
**Component:** Multiple (models, schemas)  
**Description:**  
Tests show warnings about deprecated class-based `config` in Pydantic models:
```
PydanticDeprecatedSince20: Support for class-based `config` is deprecated, 
use ConfigDict instead.
```

**Impact:**
- No functional impact currently
- Will break in Pydantic V3.0
- Makes test output noisy

**Recommended Fix:**
```python
# Old style (deprecated)
class MyModel(BaseModel):
    class Config:
        from_attributes = True

# New style (recommended)
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**Estimated Effort:** 2-3 hours (find and replace across codebase)

---

## Areas for Improvement

### Improvement #1: Add Response Caching Tests

**Priority:** Medium  
**Description:**  
While the application has response caching implemented, there are no automated tests to verify:
- Cache hit/miss behavior
- Cache TTL expiration
- Cache invalidation
- Cache key generation

**Estimated Effort:** 3-4 hours

---

### Improvement #2: Add Logging Tests

**Priority:** Low  
**Description:**  
No tests verify that appropriate logs are generated for:
- Successful operations
- Errors and exceptions
- Performance metrics
- Security events

**Estimated Effort:** 3-4 hours

---

### Improvement #3: Add Health Check Tests

**Priority:** Medium  
**Description:**  
While `/rag/health` exists, there are no comprehensive health check tests for:
- Database connectivity
- Embedding service availability
- LLM service availability
- Dependency service status

**Estimated Effort:** 2-3 hours

---

## Workarounds

### For Issue #1 and #2 (Empty Input Validation)

**Temporary Workaround:**  
API consumers should validate inputs client-side before sending requests:

```python
# Client-side validation
if not messages or len(messages) == 0:
    raise ValueError("Messages cannot be empty")

if not query or query.strip() == "":
    raise ValueError("Query cannot be empty")
```

**Note:** This is not a substitute for fixing the server-side issue.

---

## Testing TODO List

### Short Term (Next Sprint)
- [ ] Fix Issue #1 (empty messages validation)
- [ ] Fix Issue #2 (empty query validation)
- [ ] Implement Issue #3 (RAG MCP tool)
- [ ] Add health check comprehensive tests
- [ ] Fix Pydantic deprecation warnings

### Medium Term (Next 2-3 Sprints)
- [ ] Add database integration tests with fixtures
- [ ] Add OpenAPI schema validation
- [ ] Add response caching tests
- [ ] Add logging tests
- [ ] Set up real MCP client integration tests

### Long Term (Future)
- [ ] Add load/stress testing infrastructure
- [ ] Add authentication/authorization tests (when implemented)
- [ ] Add rate limiting tests (when implemented)
- [ ] Add monitoring and alerting tests
- [ ] Add chaos engineering tests

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-12 | Tester Agent | Initial document after API validation |

---

## Related Documents

- [API_VALIDATION_REPORT.md](API_VALIDATION_REPORT.md) - Comprehensive test results
- [RAG_TEST_GUIDE.md](RAG_TEST_GUIDE.md) - RAG service testing guide
- [TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md) - Overall test suite summary

---

**Document Status:** Current  
**Next Review:** After bug fixes and feature implementations  
**Owner:** Tester Agent / QA Team
