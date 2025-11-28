# Testing and Coverage Notes

## Local Testing Environment

⚠️ **Note**: Local testing may fail due to Python version compatibility issues.

- **CI Environment**: Python 3.11 (as configured in `.github/workflows/ci.yml`)
- **Local Environment**: May use Python 3.14+ which has compatibility issues with dependencies like `torch==2.2.2`

## Coverage Validation Status

### Current Status
- **Coverage Threshold**: 80% (currently in **advisory mode**)
- **Enforcement**: Will show warnings but not block builds
- **Timeline**: Will be enforced after initial pipeline stabilization

### Running Tests Locally

If you have Python 3.11 installed:

```bash
# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-timeout

# Run tests with coverage
pytest tests/ -v --tb=short -m "not slow" \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-report=html
```

### Viewing Coverage Results

After running tests:
- **Terminal**: Coverage summary shown in output
- **HTML Report**: Open `htmlcov/index.html` in browser
- **XML Report**: `coverage.xml` for CI integration

## CI/CD Pipeline Testing

The CI pipeline will:
1. ✅ Run all backend tests with PostgreSQL service
2. ✅ Run all frontend tests
3. ✅ Calculate coverage and show warnings if below 80%
4. ✅ Continue execution (advisory mode)
5. ✅ Upload coverage reports to Codecov

## Next Steps

- [ ] Run CI pipeline to get actual coverage baseline
- [ ] Review coverage reports from first successful run
- [ ] Create issues for areas needing test coverage
- [ ] Plan to enforce 80% threshold after coverage improves

## Manual Coverage Validation

Since local testing is blocked by Python version:

**Option 1**: Use GitHub Actions
- Push changes to a branch
- CI will run automatically
- Check Actions tab for coverage results

**Option 2**: Use Docker
```bash
# Build and run tests in Docker (matches CI environment)
docker build -f Dockerfile -t mcp-test --target builder .
docker run --rm mcp-test pytest tests/ --cov=app --cov-report=term
```

**Option 3**: Install Python 3.11
```bash
# Using pyenv
pyenv install 3.11.9
pyenv local 3.11.9
python -m venv .venv
source .venv/bin/activate
```

## Coverage Advisory Mode

The coverage check has been modified to be **non-blocking** initially:

```yaml
- name: Check coverage threshold
  run: |
    # ... coverage calculation ...
    if [ $coverage_int -lt 80 ]; then
      echo "::warning::Coverage ${coverage_int}% is below 80% threshold"
      echo "ℹ️  Currently in advisory mode - not blocking the build"
    fi
  continue-on-error: true
```

This allows the pipeline to:
- ✅ Run successfully even with low coverage
- ✅ Provide visibility into current coverage levels
- ✅ Avoid blocking urgent fixes
- ✅ Set expectations for future enforcement

---

**Last Updated**: 2025-11-28
