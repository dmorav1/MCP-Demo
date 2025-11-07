# Known Issues - Integration Tests

This document tracks known issues discovered during integration test development.

## Test Implementation Issues

### 1. Repository API Mismatches (Fixed Required)

**Issue**: Integration tests use incorrect method names for repositories.

**Actual Repository APIs:**
- `SqlAlchemyChunkRepository`:
  - `save_chunks(chunks)` - batch save, not `save(chunk)`
  - `get_by_conversation(conversation_id)` - not `get_by_conversation_id`
  - No `count_by_conversation()` or `delete()` methods
  
- `SqlAlchemyVectorSearchRepository`:
  - `similarity_search(embedding, limit)` - not `search_similar`
  - `similarity_search_with_threshold(embedding, limit, threshold)`

**Resolution**: Tests need to be updated to use correct method names.

### 2. Value Object Constraints

**Issue**: `ChunkText` has max length of 10,000 characters (business rule).

**Location**: `app/domain/value_objects.py:42`

**Impact**: Test `test_edge_case_very_long_chunk_text` fails with 50,000 character text.

**Resolution**: Either:
1. Test with text < 10,000 characters
2. Test that validation error is raised for text > 10,000 characters
3. Question if 10,000 character limit is appropriate

### 3. Missing Repository Methods

**Issue**: Some repository operations assumed in tests don't exist:
- `ChunkRepository.delete(chunk_id)` - not implemented
- `ChunkRepository.count_by_conversation(conversation_id)` - not implemented

**Resolution**: Either:
1. Implement missing methods in repositories
2. Remove tests for non-existent functionality
3. Use alternative approaches (e.g., use `get_by_conversation` and count results)

## Architecture Observations

### Repository Design Patterns

**Observation**: Different repositories have inconsistent APIs:
- `ConversationRepository` has `save()`, `delete()`, `exists()`, `count()`
- `ChunkRepository` has `save_chunks()` (batch only), no delete, no count by conversation
- `VectorSearchRepository` is read-only (search methods only)

**Recommendation**: Consider standardizing repository interfaces for consistency.

### Value Object Immutability

**Issue Fixed**: Value objects are frozen dataclasses (immutable).

**Impact**: Tests that try to mutate value objects (e.g., `conversation.metadata.title = "new"`) fail with `FrozenInstanceError`.

**Resolution**: Create new value object instances instead of mutating existing ones.

## Test Coverage Gaps (To Address)

1. **Transaction Handling**: Need more tests for:
   - Concurrent modifications
   - Isolation levels
   - Deadlock scenarios

2. **Error Handling**: Need tests for:
   - Database connection failures
   - Timeout scenarios
   - Invalid SQL injection attempts

3. **Performance**: Need benchmarks for:
   - Large batch operations (1000+ records)
   - Vector search with 10,000+ vectors
   - Connection pool under load

## Recommendations

### Short Term
1. Fix method name mismatches in integration tests
2. Adjust edge case tests to respect business rules
3. Document actual repository APIs in README

### Medium Term
1. Implement missing repository methods if needed
2. Add more comprehensive error handling tests
3. Add performance benchmarks with realistic data volumes

### Long Term
1. Consider standardizing repository interfaces
2. Review business rules (e.g., chunk length limits)
3. Add integration tests for all embedding service providers (OpenAI, FastEmbed)

## Test Status Summary

| Test Suite | Total Tests | Passing | Failing | Notes |
|------------|-------------|---------|---------|-------|
| Conversation Repository | 14 | 14 | 0 | ✅ All passing |
| Chunk Repository | 9 | 0 | 9 | ❌ API mismatches |
| Vector Search | 8 | 0 | 8 | ❌ API mismatches |
| Local Embedding | 15 | Not tested | Not tested | ⏳ Requires model download |
| E2E Ingestion | 6 | Not tested | Not tested | ⏳ Depends on embeddings |
| E2E Search | 7 | Not tested | Not tested | ⏳ Depends on embeddings |

**Total**: 59 tests created, 14 passing, 17 failing, 28 not yet tested

## Next Steps

1. Update chunk and vector search integration tests to use correct APIs
2. Test embedding service integration (requires model download)
3. Test e2e workflows (requires working database + embedding tests)
4. Generate coverage report
5. Create performance benchmark document
