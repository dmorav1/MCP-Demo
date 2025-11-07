# Integration Test Suite

This directory contains comprehensive integration tests for the MCP Demo project that validate adapters work correctly with real infrastructure.

## Test Organization

```
tests/integration/
├── conftest.py              # Shared fixtures (PostgreSQL container, repositories, test data)
├── database/                # Database adapter integration tests
│   ├── test_conversation_repository_integration.py
│   ├── test_chunk_repository_integration.py
│   └── test_vector_search_integration.py
├── embedding/               # Embedding service integration tests
│   └── test_local_embedding_integration.py
├── e2e/                     # End-to-end workflow tests
│   ├── test_ingestion_workflow.py
│   └── test_search_workflow.py
└── README.md               # This file
```

## Prerequisites

### Required Dependencies

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov testcontainers
```

### Docker Requirement

Integration tests use **testcontainers-python** which requires Docker to be running:
- Install Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Ensure Docker daemon is running: `docker ps`
- Grant permissions for testcontainers to create containers

### Hardware Requirements

- **Memory**: At least 4GB available RAM (testcontainers + embedding models)
- **Disk**: At least 2GB free space for Docker images and models
- **CPU**: Multi-core recommended for faster test execution

## Running Tests

### Run All Integration Tests

```bash
# Run all integration tests (requires Docker)
pytest tests/integration/ -v -m integration

# Run with output capture disabled (see print statements)
pytest tests/integration/ -v -m integration -s
```

### Run Specific Test Categories

```bash
# Database adapter tests only
pytest tests/integration/database/ -v -m integration

# Embedding service tests only
pytest tests/integration/embedding/ -v -m integration

# End-to-end workflow tests only
pytest tests/integration/e2e/ -v -m integration

# Performance tests only
pytest tests/integration/ -v -m "integration and slow and performance"
```

### Run Individual Test Files

```bash
# Test conversation repository
pytest tests/integration/database/test_conversation_repository_integration.py -v

# Test vector search
pytest tests/integration/database/test_vector_search_integration.py -v

# Test ingestion workflow
pytest tests/integration/e2e/test_ingestion_workflow.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
pytest tests/integration/database/test_conversation_repository_integration.py::TestConversationRepositoryIntegration -v

# Run specific test method
pytest tests/integration/database/test_conversation_repository_integration.py::TestConversationRepositoryIntegration::test_save_and_retrieve_conversation -v
```

### Skip Slow Tests

```bash
# Run integration tests but skip slow ones
pytest tests/integration/ -v -m "integration and not slow"
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.integration` - Integration tests requiring real infrastructure
- `@pytest.mark.slow` - Tests that take >5 seconds (model loading, large datasets)
- `@pytest.mark.e2e` - End-to-end workflow tests
- `@pytest.mark.performance` - Performance and load tests

Example usage:
```bash
# Run only fast integration tests
pytest -v -m "integration and not slow"

# Run only e2e tests
pytest -v -m "integration and e2e"
```

## Test Coverage

Generate test coverage report:

```bash
# Run with coverage
pytest tests/integration/ -v -m integration --cov=app --cov-report=html

# View HTML report
open htmlcov/index.html
```

Target coverage: **>90%** for adapter modules.

## Test Fixtures

### Key Fixtures (from conftest.py)

- **postgres_container**: PostgreSQL testcontainer with pgvector (session-scoped)
- **postgres_url**: Connection URL for test database
- **engine**: SQLAlchemy engine connected to testcontainer
- **db_session**: Clean database session per test (transaction rollback isolation)
- **conversation_repository**: Repository instance for testing
- **chunk_repository**: Chunk repository instance
- **embedding_repository**: Embedding repository instance
- **vector_search_repository**: Vector search repository instance
- **sample_conversation**: Test conversation with 3 chunks
- **sample_conversation_with_embeddings**: Conversation with embedding vectors
- **realistic_conversation**: Realistic customer support conversation
- **edge_case_conversations**: Edge cases (empty, long text, special characters)
- **many_conversations**: 100 conversations for load testing

### Fixture Scopes

- **session**: Shared across all tests (PostgreSQL container, engine)
- **function**: New instance per test (db_session, repositories)

This ensures test isolation while maximizing performance.

## Test Data

Tests use realistic data scenarios:

1. **Simple Test Data**: Basic conversations for unit-style integration tests
2. **Realistic Conversations**: Customer support scenarios from sample-data.json
3. **Edge Cases**:
   - Empty conversations (no chunks)
   - Very long text (50,000+ characters)
   - Special characters and emojis
   - Unicode text (Chinese, Arabic)
4. **Performance Data**: Bulk data for load testing

## Performance Benchmarks

Expected performance on standard hardware (4-core CPU, 8GB RAM):

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| Single conversation save | <0.1s | Without embeddings |
| Conversation with embeddings | 1-3s | Includes embedding generation |
| Vector search (100 vectors) | <0.1s | Using pgvector |
| Vector search (1000 vectors) | <0.5s | Using pgvector |
| Batch embed (20 texts) | <5s | Using local model |
| Full ingestion workflow | <10s | 10 messages with embeddings |

## Troubleshooting

### Docker Issues

**Problem**: `docker.errors.DockerException: Error while fetching server API version`

**Solution**: 
- Ensure Docker daemon is running: `docker ps`
- Restart Docker Desktop/Engine
- Check Docker permissions

### Slow Tests

**Problem**: Tests take too long

**Solution**:
- Skip slow tests: `pytest -m "integration and not slow"`
- Run specific test files instead of entire suite
- Use faster CPU device for embeddings (default: CPU)

### Memory Issues

**Problem**: Out of memory errors

**Solution**:
- Close other applications
- Increase Docker memory limit (Docker Desktop settings)
- Run fewer tests in parallel
- Skip performance tests with large datasets

### Testcontainer Cleanup

**Problem**: Orphaned containers after test failures

**Solution**:
```bash
# List all containers
docker ps -a

# Remove testcontainers
docker rm -f $(docker ps -a -q --filter "label=org.testcontainers=true")
```

### Model Download Issues

**Problem**: First test run downloads large models

**Solution**:
- Be patient on first run (downloads ~100MB for all-MiniLM-L6-v2)
- Models are cached in `~/.cache/torch/sentence_transformers/`
- Subsequent runs use cached models

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov testcontainers
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m integration --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Running Locally Before Push

```bash
# Quick validation (fast tests only)
pytest tests/integration/ -v -m "integration and not slow"

# Full validation (all tests)
pytest tests/integration/ -v -m integration

# With coverage
pytest tests/integration/ -v -m integration --cov=app --cov-report=term-missing
```

## Test Development Guidelines

### Adding New Integration Tests

1. **Choose appropriate directory**: database/, embedding/, or e2e/
2. **Mark tests appropriately**: `@pytest.mark.integration`, `@pytest.mark.slow`
3. **Use existing fixtures**: Leverage conftest.py fixtures
4. **Test real behavior**: Use real PostgreSQL, real models (not mocks)
5. **Include edge cases**: Empty data, large data, special characters
6. **Add performance tests**: For critical paths
7. **Document expectations**: Use docstrings and comments

### Test Naming Convention

- File: `test_<component>_integration.py`
- Class: `Test<Component>Integration`
- Method: `test_<behavior>_<scenario>`

Examples:
- `test_conversation_repository_integration.py`
- `TestConversationRepositoryIntegration`
- `test_save_and_retrieve_conversation`

### Assertions

Be specific and comprehensive:
```python
# Good
assert result.id is not None
assert result.id.value > 0
assert len(result.chunks) == 3

# Bad
assert result  # Too vague
```

## Known Issues

None at this time. If you encounter issues, please document them here or create a GitHub issue.

## Contributing

When adding new features:
1. Add corresponding integration tests
2. Ensure tests pass locally
3. Update this README if needed
4. Aim for >90% coverage of new code

## Contact

For questions about integration tests, contact the development team or refer to:
- Main README: `/README.md`
- Test documentation: `/docs/testing.md`
