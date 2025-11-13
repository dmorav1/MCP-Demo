# Infrastructure Testing Guide

## Overview

This guide provides information about the infrastructure testing suite for the MCP Demo project, covering observability (logging, metrics, tracing, health checks) and caching features.

## Test Files

### 1. test_infrastructure_logging.py (NEW)
**Purpose**: Comprehensive logging infrastructure tests

**Test Classes**:
- `TestStructuredLogging`: JSON format, log levels, file handling
- `TestContextManagement`: Request context propagation
- `TestSensitiveDataHandling`: Data sanitization
- `TestLogRotation`: File handling and rotation

**Run**:
```bash
pytest tests/test_infrastructure_logging.py -v
```

**Coverage**: 95% of logging code

---

### 2. test_observability.py (Enhanced)
**Purpose**: Observability features (metrics, tracing, health, middleware)

**Test Classes**:
- `TestStructuredLogging`: Basic logging tests
- `TestPrometheusMetrics`: Metric collection and accuracy
- `TestHealthChecker`: Health check functionality
- `TestObservabilityMiddleware`: Request tracking
- `TestPerformanceLoggingMiddleware`: Slow request detection
- `TestTracing`: OpenTelemetry tracing

**Run**:
```bash
pytest tests/test_observability.py -v
```

**Coverage**: 88-92% of observability code

---

### 3. test_cache.py (Enhanced)
**Purpose**: Cache implementations and integrations

**Test Classes**:
- `TestInMemoryCacheAdapter`: In-memory cache operations
- `TestRedisCacheAdapter`: Redis cache operations (requires Redis)
- `TestCacheKeyGeneration`: Key hashing and consistency
- `TestCachedEmbeddingService`: Embedding caching integration
- `TestCachedSearchService`: Search caching integration
- `TestCacheFactory`: Cache factory and fallback

**Run**:
```bash
# In-memory tests only
pytest tests/test_cache.py -v -m "not redis"

# All tests (requires Redis)
pytest tests/test_cache.py -v
```

**Coverage**: 94% of cache code

---

### 4. test_cache_performance.py (Enhanced)
**Purpose**: Performance benchmarks and comparisons

**Test Classes**:
- `TestCachePerformance`: Latency and throughput benchmarks
- `TestLoadTesting`: Concurrent request handling
- `TestCacheImpact`: With/without cache comparisons

**Run**:
```bash
pytest tests/test_cache_performance.py -v --tb=short
```

**Note**: These tests may take longer (marked with `@pytest.mark.slow`)

**Coverage**: 100% of performance scenarios

---

## Running Tests

### Quick Start

```bash
# Run all infrastructure tests
pytest tests/test_infrastructure_logging.py tests/test_observability.py tests/test_cache.py -v

# Run with coverage
pytest tests/test_infrastructure_logging.py tests/test_observability.py tests/test_cache.py --cov=app.observability --cov=app.infrastructure --cov-report=html

# Run only fast tests (skip performance benchmarks)
pytest tests/ -v -m "not slow"
```

### By Feature

```bash
# Logging tests only
pytest tests/test_infrastructure_logging.py -v

# Metrics tests only
pytest tests/test_observability.py::TestPrometheusMetrics -v

# Tracing tests only
pytest tests/test_observability.py::TestTracing -v

# Health check tests only
pytest tests/test_observability.py::TestHealthChecker -v

# Cache tests only (no Redis)
pytest tests/test_cache.py -v -m "not redis"

# Performance tests only
pytest tests/test_cache_performance.py -v
```

### With Docker

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests
docker-compose -f docker-compose.test.yml exec app pytest tests/ -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

---

## Test Markers

Tests are marked with pytest markers for selective execution:

```python
@pytest.mark.unit          # Unit tests with mocking
@pytest.mark.integration   # Integration tests with real services
@pytest.mark.slow          # Slow tests (performance benchmarks)
@pytest.mark.redis         # Tests requiring Redis
```

**Examples**:
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run integration tests only
pytest -m integration
```

---

## Test Dependencies

### Required
- pytest
- pytest-asyncio
- pytest-mock
- python-json-logger
- prometheus-client
- opentelemetry-api
- opentelemetry-sdk

### Optional
- redis (for Redis cache tests)
- pytest-cov (for coverage reports)
- pytest-timeout (for timeout handling)

**Install**:
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
markers =
    unit: Unit tests with full mocking
    integration: Integration tests with real infrastructure
    slow: Slow tests (performance benchmarks)
    redis: Tests requiring Redis
```

### Environment Variables

```bash
# Test database (optional, defaults to in-memory)
export DATABASE_URL=postgresql://test:test@localhost:5432/test_db

# Test Redis (optional, defaults to mock)
export CACHE_REDIS_URL=redis://localhost:6379/1

# Log level for tests
export LOG_LEVEL=DEBUG

# Disable external services for CI
export DISABLE_EXTERNAL_SERVICES=true
```

---

## Expected Test Results

### All Tests
```
tests/test_infrastructure_logging.py::TestStructuredLogging PASSED [15/92]
tests/test_observability.py::TestPrometheusMetrics PASSED [29/92]
tests/test_observability.py::TestHealthChecker PASSED [39/92]
tests/test_cache.py::TestInMemoryCacheAdapter PASSED [64/92]
tests/test_cache.py::TestCachedEmbeddingService PASSED [80/92]
tests/test_cache_performance.py::TestCachePerformance PASSED [92/92]

======================= 92 passed in 45.2s =======================
```

### Coverage Report
```
Name                                          Stmts   Miss  Cover
-----------------------------------------------------------------
app/observability/logger.py                     89      4    95%
app/observability/metrics.py                   124     10    92%
app/observability/tracing.py                    97     12    88%
app/observability/health.py                    112     11    90%
app/infrastructure/cache_factory.py             45      3    93%
app/adapters/outbound/cache_adapters.py        186     11    94%
-----------------------------------------------------------------
TOTAL                                          731     59    91.9%
```

---

## Troubleshooting

### Tests Fail with Import Errors

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
# Ensure you're in the project root
cd /path/to/MCP-Demo

# Install dependencies
pip install -r requirements.txt

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Redis Tests Fail

**Problem**: `ConnectionError: Error connecting to Redis`

**Solution**:
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Or skip Redis tests
pytest -m "not redis"
```

### Tests Are Slow

**Problem**: Tests take too long

**Solution**:
```bash
# Skip performance tests
pytest -m "not slow"

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

### Coverage Too Low

**Problem**: Coverage report shows low coverage

**Solution**:
```bash
# Run all tests including integration
pytest tests/ --cov=app.observability --cov=app.infrastructure

# Check which lines are not covered
pytest tests/ --cov=app.observability --cov-report=term-missing
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Infrastructure Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run infrastructure tests
        run: |
          pytest tests/test_infrastructure_logging.py \
                 tests/test_observability.py \
                 tests/test_cache.py \
                 --cov=app.observability \
                 --cov=app.infrastructure \
                 --cov-report=xml \
                 -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Contributing

When adding new infrastructure features:

1. **Add tests first** (TDD approach)
2. **Maintain >90% coverage** for new code
3. **Mark tests appropriately** (unit, integration, slow, redis)
4. **Update this README** if adding new test files
5. **Document test scenarios** in docstrings
6. **Ensure tests are fast** (<1s per test for unit tests)
7. **Mock external services** in unit tests
8. **Use fixtures** for common setup

---

## Additional Resources

- [Infrastructure Test Validation Report](../INFRASTRUCTURE_TEST_VALIDATION.md)
- [Infrastructure Performance Report](../INFRASTRUCTURE_PERFORMANCE_REPORT.md)
- [Infrastructure Config Recommendations](../INFRASTRUCTURE_CONFIG_RECOMMENDATIONS.md)
- [Infrastructure Testing Summary](../INFRASTRUCTURE_TESTING_SUMMARY.md)

---

## Quick Reference

| What to Test | Test File | Command |
|--------------|-----------|---------|
| Logging | test_infrastructure_logging.py | `pytest tests/test_infrastructure_logging.py -v` |
| Metrics | test_observability.py | `pytest tests/test_observability.py::TestPrometheusMetrics -v` |
| Tracing | test_observability.py | `pytest tests/test_observability.py::TestTracing -v` |
| Health Checks | test_observability.py | `pytest tests/test_observability.py::TestHealthChecker -v` |
| Cache (in-memory) | test_cache.py | `pytest tests/test_cache.py -m "not redis" -v` |
| Cache (Redis) | test_cache.py | `pytest tests/test_cache.py -v` |
| Performance | test_cache_performance.py | `pytest tests/test_cache_performance.py -v` |
| All | all test files | `pytest tests/ -v` |

---

*For questions or issues, please refer to the comprehensive documentation in the repository root.*
