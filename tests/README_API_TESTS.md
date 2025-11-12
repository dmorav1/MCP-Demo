# API Validation Test Suite

Comprehensive automated tests for the MCP Demo hexagonal architecture API implementation.

## Quick Start

```bash
# Run all API validation tests
pytest tests/test_api_comprehensive.py tests/test_mcp_server.py -v

# Run specific test category
pytest tests/test_api_comprehensive.py::TestSecurity -v

# Run with coverage
pytest tests/test_api_comprehensive.py tests/test_mcp_server.py --cov=app --cov-report=html
```

## Test Files

### test_api_comprehensive.py (697 lines, 34 tests)
Comprehensive API functional, integration, and security tests.

**Categories:**
- Conversation Endpoints (3 tests)
- Search Endpoints (4 tests)
- RAG Endpoints (3 tests)
- Invalid Inputs (7 tests)
- Integration Workflows (3 tests)
- Contract Validation (3 tests)
- Performance (3 tests)
- Security (4 tests)
- Compatibility (2 tests)
- Pagination (1 test - skipped)

### test_mcp_server.py (420 lines, 17 tests)
MCP protocol server validation tests.

**Categories:**
- Tool Invocations (3 tests)
- Protocol Compliance (5 tests)
- Error Handling (3 tests)
- Integration (3 tests)
- Data Transformation (2 tests)

## Test Results

**Total:** 51 tests  
**Passed:** 46 (90%)  
**Skipped:** 3  
**Expected Failures (xfail):** 2  
**Execution Time:** ~6.5 seconds

## Known Issues

1. **test_ingest_empty_messages** (XFAIL) - Bug: Empty messages ValueError not handled properly
2. **test_search_empty_query** (XFAIL) - Bug: Empty query ValueError not handled properly
3. **test_ask_question_tool** (SKIPPED) - Feature: RAG MCP tool not yet implemented

## Documentation

See `docs/testing/` for detailed reports:
- **API_VALIDATION_REPORT.md** - Comprehensive test results
- **KNOWN_ISSUES.md** - Bug tracking and limitations
- **TEST_EXECUTION_SUMMARY.md** - Execution details and metrics

## Test Strategy

All tests use **mocked dependencies** for:
- Fast execution (< 7 seconds)
- No external dependencies (database, APIs)
- Reliable, repeatable results
- CI/CD friendly

## Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

## Contributing

When adding new tests:
1. Follow existing test patterns
2. Use mocked dependencies
3. Add test to appropriate category
4. Update test counts in documentation
5. Run full suite before committing

---

**Status:** ✅ COMPLETE  
**Last Updated:** November 12, 2025  
**Maintained By:** Tester Agent
