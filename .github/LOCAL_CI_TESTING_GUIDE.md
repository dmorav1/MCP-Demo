# Local CI Testing Guide

How to test GitHub Actions CI workflow locally before pushing to avoid wasting CI minutes and waiting for failures.

---

## Quick Start (Recommended)

### Option 1: Find Hanging Test (FASTEST - 2-5 minutes)

Quickly identify which test is causing the timeout:

```bash
./.github/find-hanging-test.sh
```

**What it does**:
- Runs tests with 30-second timeout (vs 5 minutes in CI)
- Stops at first failure (`-x` flag)
- Shows exactly which test is hanging
- Completes in 2-5 minutes

**When to use**: When CI is timing out and you need to find the culprit fast

---

### Option 2: Full CI Simulation (10-15 minutes)

Run the exact same command as GitHub Actions:

```bash
./.github/test-ci-locally.sh
```

**What it does**:
- Mimics GitHub Actions CI workflow exactly
- Uses same Python version, environment variables, and flags
- 15-minute job timeout (same as CI)
- Shows coverage report
- Provides detailed summary

**When to use**: Before pushing to verify everything works

---

## Manual Testing Methods

### Method 1: Quick Test (No Database)

Just run unit tests that don't need database:

```bash
source .venv/bin/activate

# Install test deps
pip install pytest pytest-timeout pytest-asyncio>=0.21.0

# Run fast tests only
pytest -x --timeout=30 -v tests/ -m "not slow and not integration and not database"
```

---

### Method 2: With Local PostgreSQL

If you have PostgreSQL running locally:

```bash
# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
export OPENAI_API_KEY="sk-test-key"
export ANTHROPIC_API_KEY="test-key"

# Run tests (exact CI command)
pytest tests/ \
  -v \
  --tb=short \
  -m "not slow and not integration" \
  --timeout=300 \
  --cov=app \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-report=html
```

---

### Method 3: With Docker PostgreSQL

Start PostgreSQL in Docker (matches CI environment):

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name test-postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=test_db \
  pgvector/pgvector:pg16

# Wait for it to be ready
sleep 5

# Run tests
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
pytest tests/ -v -m "not slow and not integration" --timeout=300

# Cleanup
docker stop test-postgres
docker rm test-postgres
```

---

## Diagnosing Timeout Issues

### Step 1: Identify the Hanging Test

Run with verbose output and short timeout:

```bash
pytest -x -v --timeout=30 -m "not slow and not integration" tests/ 2>&1 | tee output.log
```

Look for the last test that started running before the timeout.

---

### Step 2: Run Just That Test

Once you find the suspect test:

```bash
# Run specific test file
pytest tests/test_suspect.py -v --timeout=30

# Run specific test function
pytest tests/test_suspect.py::test_function_name -v --timeout=10

# Run with maximum verbosity
pytest tests/test_suspect.py::test_function_name -vv -s --timeout=10
```

---

### Step 3: Common Hanging Causes

Check for these issues in the hanging test:

#### 1. Real API Calls
```python
# BAD: Real API call
def test_something():
    client = OpenAI(api_key=settings.openai_api_key)  # ❌ Real API call!
    result = client.embeddings.create(...)

# GOOD: Mocked
def test_something(mocker):
    mock_client = mocker.patch('openai.OpenAI')
    mock_client.return_value.embeddings.create.return_value = {...}
```

#### 2. Model Downloads
```python
# BAD: Downloads model
@pytest.fixture
def embedding_service():
    return LocalEmbeddingService(model_name="all-MiniLM-L6-v2")  # ❌ Downloads 400MB!

# GOOD: Mocked or skipped
@pytest.mark.integration
@pytest.mark.slow
def test_with_real_model():
    # Only runs with RUN_INTEGRATION_TESTS=1
    pass
```

#### 3. Infinite Loops
```python
# BAD: Infinite loop
def test_something():
    while True:  # ❌ Never exits!
        if some_condition:
            break
    # If some_condition never true, hangs forever

# GOOD: With timeout or max iterations
def test_something():
    max_iterations = 100
    for i in range(max_iterations):
        if some_condition:
            break
```

#### 4. Blocking Operations
```python
# BAD: Waiting indefinitely
def test_something():
    result = queue.get()  # ❌ Blocks forever if queue empty!

# GOOD: With timeout
def test_something():
    result = queue.get(timeout=1.0)
```

---

## Using `act` (GitHub Actions Runner)

Install `act` to run GitHub Actions workflows locally:

### Installation

```bash
# macOS
brew install act

# Linux
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

### Usage

```bash
# Run the CI workflow
act pull_request

# Run specific job
act -j backend-test

# Use specific runner image
act -P ubuntu-latest=catthehacker/ubuntu:act-latest

# Dry run (show what would run)
act -n
```

**Note**: `act` requires Docker to be running.

---

## Comparing Local vs CI Results

### Check Differences

If tests pass locally but fail in CI (or vice versa):

#### 1. Python Version
```bash
# Local
python3 --version

# CI uses (check .github/workflows/ci.yml)
PYTHON_VERSION: '3.11'
```

#### 2. Environment Variables
```bash
# CI sets these:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db
OPENAI_API_KEY=sk-test-key (or from secrets)
ANTHROPIC_API_KEY=test-key (or from secrets)
```

#### 3. PostgreSQL Version
```bash
# CI uses (check .github/workflows/ci.yml)
image: pgvector/pgvector:pg16

# Check your local version
psql --version
```

#### 4. Dependencies
```bash
# CI installs fresh each time
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio>=0.21.0 pytest-timeout

# Your local might have different versions
pip freeze | grep pytest
```

---

## Workflow Validation (Syntax Only)

### Using `actionlint`

Install and run actionlint to check workflow syntax:

```bash
# Install
brew install actionlint  # macOS
# OR
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Run
actionlint .github/workflows/ci.yml

# Check all workflows
actionlint .github/workflows/*.yml
```

### Using Python YAML Validator

```bash
python3 -c "
import yaml
import sys

try:
    with open('.github/workflows/ci.yml', 'r') as f:
        workflow = yaml.safe_load(f)
    print('✅ Valid YAML syntax')
    print(f'Jobs: {list(workflow.get(\"jobs\", {}).keys())}')
except Exception as e:
    print(f'❌ Invalid YAML: {e}')
    sys.exit(1)
"
```

---

## Troubleshooting

### Tests Pass Locally But Timeout in CI

**Possible causes**:
1. CI has slower network (model downloads take longer)
2. CI has less CPU/RAM (tests run slower)
3. Different Python version
4. CI runs more tests in parallel

**Solution**:
- Use `--timeout=300` locally (same as CI)
- Check which tests are marked `slow` or `integration`
- Ensure mocks are used for external services

### Tests Fail Locally But Pass in CI

**Possible causes**:
1. Wrong Python version locally
2. Missing environment variables
3. PostgreSQL not running or wrong version
4. Stale dependencies in local venv

**Solution**:
- Recreate venv with Python 3.11
- Set all environment variables
- Use Docker PostgreSQL (pg16)
- `pip install -r requirements.txt --force-reinstall`

### Permission Denied on Scripts

```bash
chmod +x .github/*.sh
```

---

## Quick Reference

### Essential Commands

```bash
# Quick diagnostic (2-5 min)
./.github/find-hanging-test.sh

# Full CI simulation (10-15 min)
./.github/test-ci-locally.sh

# Just run tests (minimal)
pytest tests/ -m "not slow and not integration" --timeout=30

# Run specific test
pytest tests/test_file.py::test_function -v

# Check workflow syntax
actionlint .github/workflows/ci.yml

# Validate YAML
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

### Environment Setup

```bash
# Create venv with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio>=0.21.0 pytest-timeout

# Set env vars
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
export OPENAI_API_KEY="sk-test-key"
export ANTHROPIC_API_KEY="test-key"
```

---

## Summary

**Recommended Workflow**:

1. **Before pushing**: Run `./.github/find-hanging-test.sh` (quick check)
2. **If tests pass**: Run `./.github/test-ci-locally.sh` (full simulation)
3. **If tests hang**: Identify the test and fix it
4. **Then push**: CI should now pass

**Time Investment**:
- Quick check: 2-5 minutes
- Full simulation: 10-15 minutes
- **vs waiting for CI**: 15-30 minutes per failed run

**Cost Savings**:
- Avoid wasting GitHub Actions minutes
- Faster iteration cycle
- Catch issues before CI

---

**Last Updated**: 2025-11-28
