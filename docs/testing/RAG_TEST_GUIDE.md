# RAG Service Test Guide

## Overview

This guide explains how to run and interpret the comprehensive test suite for the RAG (Retrieval-Augmented Generation) service.

## Test Suite Structure

The RAG test suite consists of 111+ tests organized into 7 categories:

### 1. Unit Tests (`tests/test_rag_service.py`) - 41 tests
Core functionality tests with full mocking:
- Service initialization
- Query sanitization and validation
- Context formatting and management
- Token counting and truncation
- Citation extraction
- Confidence scoring
- Conversation memory
- Error handling
- LLM provider selection

### 2. Integration Tests (`tests/test_rag_integration.py`) - 10 tests
End-to-end pipeline tests:
- Complete RAG pipeline (query → embedding → retrieval → generation → response)
- Multi-turn conversations with memory
- Different LLM providers (OpenAI, Anthropic, local)
- Streaming response generation
- Retrieval quality validation
- Source citation accuracy

### 3. Quality Evaluation (`tests/test_rag_quality.py`) - 8 tests
RAG quality metrics and evaluation:
- Answer relevance scoring
- Answer faithfulness to context
- Context relevance measurement
- Hallucination detection
- Citation accuracy validation
- Overall quality score calculation

**Evaluation Dataset**: `tests/evaluation/rag_eval_dataset.json`
- 10 test cases with ground truth Q&A pairs
- Categories: factual questions, opinion synthesis, comparative analysis, edge cases

### 4. Performance Tests (`tests/test_rag_performance.py`) - 6 tests
Performance benchmarks and stress tests:
- Response latency measurement
- Concurrent request handling
- Token usage tracking
- Caching effectiveness
- High-volume query load testing

### 5. Prompt Engineering (`tests/test_rag_prompts.py`) - 5 tests
Prompt optimization tests:
- Prompt template variations
- A/B testing of prompts
- Few-shot learning examples
- System prompt effectiveness
- Context length optimization

### 6. Edge Cases (`tests/test_rag_edge_cases.py`) - 8 tests
Edge case handling:
- Queries with no relevant context
- Ambiguous and vague queries
- Very long queries (>1000 chars)
- Special characters and Unicode
- Multilingual queries
- Boundary conditions

### 7. Safety & Quality (`tests/test_rag_safety.py`) - 6 tests
Safety guardrails and quality checks:
- Content filtering
- Out-of-domain query handling
- Confidence threshold validation
- User-friendly error messages
- Input validation
- Security best practices

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure pytest and asyncio support are installed
pip install pytest pytest-asyncio
```

### Run All RAG Tests

```bash
# Run all RAG-related tests
pytest tests/test_rag*.py -v

# Run with coverage
pytest tests/test_rag*.py --cov=app.application.rag_service --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/test_rag_service.py -v

# Integration tests
pytest tests/test_rag_integration.py -v -m integration

# Quality evaluation
pytest tests/test_rag_quality.py -v

# Performance tests (may take longer)
pytest tests/test_rag_performance.py -v -m performance

# Edge cases
pytest tests/test_rag_edge_cases.py -v

# Safety tests
pytest tests/test_rag_safety.py -v
```

### Run by Test Markers

```bash
# Unit tests only
pytest -m unit tests/test_rag*.py

# Integration tests only
pytest -m integration tests/test_rag*.py

# Performance tests only (slow)
pytest -m performance tests/test_rag*.py

# Skip slow tests
pytest -m "not slow" tests/test_rag*.py
```

### Run Specific Tests

```bash
# Run specific test class
pytest tests/test_rag_service.py::TestQuerySanitization -v

# Run specific test function
pytest tests/test_rag_service.py::TestQuerySanitization::test_sanitize_valid_query -v
```

## Test Configuration

### Pytest Markers

The test suite uses these pytest markers (configured in `pytest.ini`):

- `@pytest.mark.unit` - Fast unit tests with full mocking
- `@pytest.mark.integration` - Integration tests with real infrastructure
- `@pytest.mark.performance` - Performance and load tests
- `@pytest.mark.slow` - Tests that may take several seconds
- `@pytest.mark.asyncio` - Async tests (automatically configured)

### Environment Variables

Tests use mocked configurations by default. No API keys required.

For integration tests with real LLM providers (optional):
```bash
export OPENAI_API_KEY=your-key-here
export ANTHROPIC_API_KEY=your-key-here
```

## Understanding Test Results

### Success Criteria

All tests should pass without external API dependencies:
- ✅ Total tests: 111+
- ✅ Coverage target: >80% for rag_service.py
- ✅ No flaky tests
- ✅ Fast execution (<30 seconds for unit tests)

### Common Test Failures

**1. Import Errors**
```
ModuleNotFoundError: No module named 'langchain_openai'
```
**Solution**: Install missing dependencies
```bash
pip install langchain-openai langchain-anthropic langchain-community
```

**2. Async Test Failures**
```
RuntimeError: Event loop is closed
```
**Solution**: Ensure `pytest-asyncio` is installed and `asyncio_mode = auto` is in `pytest.ini`

**3. Mock-Related Failures**
```
AttributeError: Mock object has no attribute 'value'
```
**Solution**: Check that domain objects are properly mocked with required attributes

## Test Data

### Evaluation Dataset

Location: `tests/evaluation/rag_eval_dataset.json`

Structure:
```json
{
  "test_cases": [
    {
      "id": "tc001",
      "query": "What is Python?",
      "context": ["...", "..."],
      "ground_truth_answer": "...",
      "expected_citations": [1, 2],
      "relevance_score": 1.0,
      "category": "factual_question"
    }
  ]
}
```

Categories:
- `factual_question` - Direct factual queries
- `opinion_synthesis` - Queries requiring synthesis
- `comparative_analysis` - Comparison questions
- `out_of_context` - Queries with no relevant context
- `partial_context` - Queries with incomplete information

## Continuous Integration

### GitHub Actions (Recommended)

```yaml
name: RAG Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/test_rag*.py -v --cov=app.application.rag_service
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/test_rag*.py -x
```

## Troubleshooting

### Slow Tests

If tests are running slowly:
```bash
# Skip slow tests during development
pytest -m "not slow" tests/test_rag*.py

# Run only fast unit tests
pytest -m unit tests/test_rag*.py
```

### Debugging Failures

```bash
# Run with verbose output
pytest tests/test_rag_service.py -vv

# Show print statements
pytest tests/test_rag_service.py -s

# Drop into debugger on failure
pytest tests/test_rag_service.py --pdb

# Show local variables on failure
pytest tests/test_rag_service.py -l
```

### Test Coverage

```bash
# Generate coverage report
pytest tests/test_rag*.py --cov=app.application.rag_service --cov-report=html

# View report
open htmlcov/index.html
```

## Best Practices

1. **Run tests frequently** - Run unit tests before every commit
2. **Use markers** - Tag tests appropriately for selective execution
3. **Mock external dependencies** - Avoid real API calls in tests
4. **Keep tests fast** - Unit tests should complete in seconds
5. **Test edge cases** - Cover boundary conditions and error scenarios
6. **Maintain test data** - Keep evaluation dataset up-to-date
7. **Review coverage** - Aim for >80% code coverage

## Next Steps

- Review [RAG Quality Report](./RAG_QUALITY_REPORT.md) for quality metrics
- Check [RAG Performance Report](./RAG_PERFORMANCE_REPORT.md) for benchmarks
- See [Prompt Optimization](./PROMPT_OPTIMIZATION.md) for prompt recommendations
- Read [RAG Limitations](./RAG_LIMITATIONS.md) for known issues

## Support

For questions or issues with the test suite:
1. Check test output and error messages
2. Review this guide and related documentation
3. Examine test code for examples
4. Consult the RAG service implementation
