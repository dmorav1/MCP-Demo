# CI/CD Pipeline Documentation

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-14

## Overview

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the MCP RAG Demo project. The pipeline is implemented using GitHub Actions and provides automated testing, building, security scanning, and deployment capabilities.

## Table of Contents

1. [Pipeline Architecture](#pipeline-architecture)
2. [CI Pipeline](#ci-pipeline)
3. [CD Pipeline](#cd-pipeline)
4. [Docker Images](#docker-images)
5. [Database Migrations](#database-migrations)
6. [Environment Management](#environment-management)
7. [Quality Gates](#quality-gates)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)

---

## Pipeline Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Push / PR                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CI Pipeline                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Unit Tests   │  │  Frontend    │  │ Code Quality │      │
│  │  - Backend   │  │    Tests     │  │   - Black    │      │
│  │  - Coverage  │  │              │  │   - Flake8   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Security   │  │    Docker    │  │   Quality    │      │
│  │   - CodeQL   │  │    Build     │  │    Gates     │      │
│  │   - Trivy    │  │   - Scan     │  │   - 80% Cov  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │ (on success)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CD Pipeline                               │
│                                                               │
│  ┌──────────────┐       ┌──────────────┐                    │
│  │   Build &    │       │   Deploy     │                    │
│  │   Push       │──────▶│     Dev      │                    │
│  │   Images     │       │  (automatic) │                    │
│  └──────────────┘       └──────────────┘                    │
│                                │                             │
│                         (manual approval)                    │
│                                │                             │
│                                ▼                             │
│                       ┌──────────────┐                       │
│                       │   Deploy     │                       │
│                       │   Staging    │                       │
│                       │  (approval)  │                       │
│                       └──────────────┘                       │
│                                │                             │
│                         (manual approval)                    │
│                                │                             │
│                                ▼                             │
│                       ┌──────────────┐                       │
│                       │   Deploy     │                       │
│                       │  Production  │                       │
│                       │  (approval)  │                       │
│                       └──────────────┘                       │
│                                                               │
│  Rollback Available at Each Stage                            │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Components

- **CI Pipeline** (`ci.yml`): Automated testing, code quality, and security scanning
- **CD Pipeline** (`cd-deploy.yml`): Build, push, and deploy to environments
- **Quality Gates**: Enforce standards before deployment
- **Rollback Scripts**: Automated and manual rollback capabilities

---

## CI Pipeline

### Trigger Conditions

The CI pipeline runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual workflow dispatch

### Jobs

#### 1. Backend Tests

**Purpose**: Run unit and integration tests for the Python backend

**Steps**:
1. Set up Python 3.11 environment
2. Start PostgreSQL service (pgvector)
3. Install dependencies from `requirements.txt`
4. Run pytest with coverage
5. Upload coverage to Codecov
6. Verify 80% coverage threshold

**Requirements**:
- PostgreSQL with pgvector extension
- OpenAI API key (or test key)
- Python dependencies

**Coverage Threshold**: 80% (enforced)

#### 2. Frontend Tests

**Purpose**: Run tests for the React frontend

**Steps**:
1. Set up Node.js 18 environment
2. Install dependencies with npm
3. Run tests with coverage
4. Upload coverage to Codecov

#### 3. Code Quality

**Purpose**: Ensure code follows style guidelines

**Tools**:
- **Black**: Code formatting (Python)
- **isort**: Import sorting (Python)
- **Flake8**: Linting (Python)
- **npm build**: Frontend build check

**Note**: Code quality issues are non-blocking but reported

#### 4. Security Scan

**Purpose**: Identify security vulnerabilities in code

**Tools**:
- **CodeQL**: Static analysis for Python and JavaScript
- Results uploaded to GitHub Security tab

**Languages**: Python, JavaScript

#### 5. Docker Build & Scan

**Purpose**: Build Docker images and scan for vulnerabilities

**Steps**:
1. Build Docker images for backend and frontend
2. Run Trivy vulnerability scanner
3. Upload SARIF results to GitHub Security
4. Fail on HIGH/CRITICAL vulnerabilities (non-blocking)

**Images**: 
- `mcp-backend`
- `mcp-frontend`

---

## CD Pipeline

### Trigger Conditions

The CD pipeline runs:
- Automatically after successful CI pipeline (for dev)
- Manually via workflow dispatch (for staging/production)

### Deployment Environments

#### Development

- **Trigger**: Automatic on main branch
- **Approval**: None required
- **URL**: `https://dev.mcp-demo.example.com`
- **Purpose**: Latest changes for internal testing

#### Staging

- **Trigger**: Manual workflow dispatch
- **Approval**: Required
- **URL**: `https://staging.mcp-demo.example.com`
- **Purpose**: Pre-production validation

#### Production

- **Trigger**: Manual workflow dispatch
- **Approval**: Required
- **URL**: `https://mcp-demo.example.com`
- **Purpose**: Live production environment
- **Strategy**: Blue-Green deployment

### Deployment Steps

1. **Build & Push Images**
   - Build optimized Docker images
   - Tag with SHA and semantic version
   - Push to GitHub Container Registry

2. **Database Migrations**
   - Create database backup
   - Run Alembic migrations
   - Verify migration success
   - Rollback on failure

3. **Deploy Application**
   - Update Kubernetes deployments
   - Apply new image tags
   - Wait for rollout completion

4. **Smoke Tests**
   - Health check endpoint
   - Basic API functionality
   - Database connectivity

5. **Monitoring**
   - Check error rates
   - Monitor latency
   - Verify traffic distribution

6. **Notifications**
   - Slack webhook (if configured)
   - Email notifications (if configured)

---

## Docker Images

### Backend Image (Optimized)

**File**: `Dockerfile.optimized`

**Features**:
- Multi-stage build (builder + runtime)
- Virtual environment for dependencies
- Non-root user for security
- Minimal runtime dependencies
- Health check included

**Build Arguments**:
- `SLIM_EMBEDDINGS`: Use lightweight FastEmbed (default: 1)

**Size Optimization**:
- Builder stage: ~2GB
- Runtime stage: ~500MB (with slim embeddings)

### Frontend Image (Optimized)

**File**: `frontend/Dockerfile.optimized`

**Features**:
- Multi-stage build (builder + nginx)
- Production build with optimizations
- nginx for serving static files
- SPA routing support
- Gzip compression enabled
- Health check included

**Stages**:
- `builder`: Build React application
- `production`: nginx serving built files
- `development`: Development server (optional)

**Size Optimization**:
- Builder stage: ~800MB
- Production stage: ~50MB (nginx + static files)

### Image Tagging Strategy

```
ghcr.io/org/repo-backend:main-abc123def
ghcr.io/org/repo-backend:v1.0.0
ghcr.io/org/repo-backend:latest
```

**Tags**:
- `{branch}-{sha}`: Unique identifier for each commit
- `v{version}`: Semantic version tag
- `latest`: Latest version on main branch

### Image Scanning

**Tool**: Trivy

**Scan Levels**:
- All vulnerabilities (informational)
- HIGH/CRITICAL (blocking in production)

**Results**: Uploaded to GitHub Security tab

---

## Database Migrations

### Migration Script

**Location**: `deployment/scripts/migrations/run-migrations.sh`

**Features**:
- Automatic backup before migration
- Migration execution with Alembic
- Verification of migration success
- Automatic rollback on failure
- Detailed logging

### Usage

```bash
# Run migrations with backup (default)
./deployment/scripts/migrations/run-migrations.sh

# Run without backup (not recommended)
BACKUP_ENABLED=false ./deployment/scripts/migrations/run-migrations.sh

# Specify custom namespace
NAMESPACE=production ./deployment/scripts/migrations/run-migrations.sh
```

### Environment Variables

- `NAMESPACE`: Kubernetes namespace (default: `default`)
- `DEPLOYMENT_NAME`: Deployment name (default: `mcp-backend`)
- `MIGRATION_TIMEOUT`: Timeout in seconds (default: `300`)
- `BACKUP_ENABLED`: Enable backup (default: `true`)

### Migration Process

1. **Create Backup**
   - Connect to database
   - Run `pg_dump` to create backup
   - Store backup file information

2. **Run Migrations**
   - Execute `alembic upgrade head`
   - Capture output and errors
   - Return status code

3. **Verify Migrations**
   - Check current version with `alembic current`
   - Test database connection
   - Run health check

4. **Rollback on Failure**
   - Restore from backup (preferred)
   - OR use `alembic downgrade` (fallback)
   - Verify rollback success

### Rollback Capability

Two rollback methods:

1. **Backup Restore** (Preferred)
   - Fast restoration to pre-migration state
   - Uses `pg_restore`
   - Preserves data integrity

2. **Alembic Downgrade** (Fallback)
   - Uses migration scripts in reverse
   - Requires downgrade scripts
   - May not be available for all migrations

---

## Environment Management

### Environment-Specific Configurations

Configurations are managed through:
1. **Kubernetes ConfigMaps**: Non-sensitive configuration
2. **Kubernetes Secrets**: Sensitive data (API keys, passwords)
3. **Environment Variables**: Runtime configuration

### Configuration Files

**Development**:
```yaml
# config/dev.yaml
environment: development
log_level: DEBUG
database:
  host: postgres-dev
  port: 5432
api_keys:
  openai: ${OPENAI_API_KEY}
```

**Staging**:
```yaml
# config/staging.yaml
environment: staging
log_level: INFO
database:
  host: postgres-staging
  port: 5432
api_keys:
  openai: ${OPENAI_API_KEY}
```

**Production**:
```yaml
# config/production.yaml
environment: production
log_level: WARNING
database:
  host: postgres-prod
  port: 5432
api_keys:
  openai: ${OPENAI_API_KEY}
```

### Secret Management

**GitHub Secrets** (for CI/CD):
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `DATABASE_PASSWORD`: Database password
- `SLACK_WEBHOOK_URL`: Slack notification webhook
- `AWS_ACCESS_KEY_ID`: AWS credentials (if using AWS)
- `AWS_SECRET_ACCESS_KEY`: AWS credentials

**Kubernetes Secrets** (for runtime):
```bash
# Create secret from file
kubectl create secret generic db-credentials \
  --from-literal=username=postgres \
  --from-literal=password=<password> \
  --from-literal=host=postgres.default.svc.cluster.local \
  --from-literal=database=mcp_db

# Create secret for API keys
kubectl create secret generic api-keys \
  --from-literal=openai=<openai-key> \
  --from-literal=anthropic=<anthropic-key>
```

### Configuration Validation

Configuration validation happens in the pipeline:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    environment: str
    database_url: str
    openai_api_key: str
    
    class Config:
        env_file = ".env"
        
    def validate(self):
        """Validate configuration at startup"""
        assert self.database_url, "Database URL required"
        assert self.openai_api_key, "OpenAI API key required"
```

---

## Quality Gates

### Pre-Deployment Checks

All checks must pass before deployment:

#### 1. Test Coverage (Enforced)

- **Minimum**: 80% code coverage
- **Scope**: Backend Python code
- **Tool**: pytest-cov
- **Action**: Block deployment if below threshold

#### 2. Code Quality (Informational)

- **Tools**: Black, Flake8, isort
- **Action**: Report issues but don't block
- **Goal**: Maintain code quality standards

#### 3. Security Scan (Required)

- **Tool**: CodeQL
- **Scope**: Python and JavaScript code
- **Action**: Block on HIGH/CRITICAL findings

#### 4. Vulnerability Scan (Monitored)

- **Tool**: Trivy
- **Scope**: Docker images
- **Action**: Report vulnerabilities, block CRITICAL in production

#### 5. Smoke Tests (Required)

- **Health Check**: `/health` endpoint must return 200
- **Database**: Connection must succeed
- **API**: Basic API calls must work

#### 6. Integration Tests (Staging/Production)

- **Scope**: End-to-end workflows
- **Examples**: 
  - Ingest conversation
  - Search conversations
  - Ask RAG question
- **Action**: Block deployment on failure

### Quality Gate Flow

```
┌─────────────────┐
│  Code Changes   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Unit Tests    │──┐
│   (80% cov)     │  │
└────────┬────────┘  │
         │           │
         ▼           │
┌─────────────────┐  │
│  Code Quality   │  │ All gates
│  (Black, etc)   │  │ must pass
└────────┬────────┘  │
         │           │
         ▼           │
┌─────────────────┐  │
│Security Scan    │  │
│  (CodeQL)       │  │
└────────┬────────┘  │
         │           │
         ▼           │
┌─────────────────┐  │
│ Image Scan      │──┘
│  (Trivy)        │
└────────┬────────┘
         │
         ▼
    ✓ Deploy
```

---

## Rollback Procedures

### Rollback Script

**Location**: `deployment/scripts/rollback.sh`

**Features**:
- Automated rollback on deployment failure
- Manual rollback capability
- Interactive mode for operators
- Health verification after rollback
- Notification on rollback completion

### Automatic Rollback

Automatic rollback triggers:
1. Deployment timeout (5 minutes)
2. Health check failure
3. High error rate after deployment
4. Pod crash loops

### Manual Rollback

#### Quick Rollback (Previous Version)

```bash
# Rollback to previous version
./deployment/scripts/rollback.sh -n production -d mcp-backend

# Interactive mode
./deployment/scripts/rollback.sh -i
```

#### Rollback to Specific Version

```bash
# List available revisions
kubectl rollout history deployment/mcp-backend -n production

# Rollback to specific revision
./deployment/scripts/rollback.sh -n production -d mcp-backend -r 5
```

### Rollback Process

1. **Show Current Status**
   - Display current revision
   - Show current image
   - List pod status

2. **Show History**
   - Display all available revisions
   - Show revision details

3. **Perform Rollback**
   - Execute kubectl rollout undo
   - Wait for completion (timeout: 5 minutes)

4. **Verify Rollback**
   - Check pod health
   - Run health checks
   - Verify application metrics

5. **Notify**
   - Send Slack notification
   - Send email notification

### Rollback Verification

After rollback, verify:
- ✓ All pods are ready
- ✓ Health checks pass
- ✓ Error rate is normal
- ✓ Latency is acceptable
- ✓ No crash loops

### Database Rollback

For database migrations:
1. Restore from pre-migration backup
2. OR use Alembic downgrade (if available)

**Note**: Database rollback may result in data loss for writes after migration.

---

## Troubleshooting

### Common Issues

#### 1. Test Failures in CI

**Symptom**: Tests fail in CI but pass locally

**Solutions**:
- Check service dependencies (PostgreSQL)
- Verify environment variables are set
- Check API key configuration
- Review test logs for specific errors

#### 2. Coverage Below Threshold

**Symptom**: Coverage check fails with <80%

**Solutions**:
- Add tests for new code
- Review coverage report: `htmlcov/index.html`
- Identify untested code paths
- Add unit tests for critical functions

#### 3. Docker Build Failures

**Symptom**: Docker build fails in CI

**Solutions**:
- Test build locally: `docker build -t test .`
- Check Dockerfile syntax
- Verify base images are accessible
- Check disk space on runner

#### 4. Deployment Timeouts

**Symptom**: Deployment exceeds timeout

**Solutions**:
- Check pod events: `kubectl describe pod <pod-name>`
- Review pod logs: `kubectl logs <pod-name>`
- Verify resource limits are adequate
- Check image pull status

#### 5. Migration Failures

**Symptom**: Database migration fails

**Solutions**:
- Review migration logs
- Check database connectivity
- Verify migration scripts
- Test migrations locally
- Restore from backup if needed

### Debug Commands

```bash
# Check pipeline status
gh workflow view ci.yml

# View workflow run logs
gh run view <run-id> --log

# Check deployment status
kubectl get deployment mcp-backend -n production

# View pod logs
kubectl logs -f deployment/mcp-backend -n production

# Check pod events
kubectl describe pod <pod-name> -n production

# View recent rollout history
kubectl rollout history deployment/mcp-backend -n production

# Check service health
curl https://mcp-demo.example.com/health
```

### Support

For issues not covered here:
1. Check GitHub Actions logs
2. Review application logs in Kubernetes
3. Contact DevOps team
4. Create GitHub issue with details

---

## Appendix

### Pipeline Files

- `.github/workflows/ci.yml`: CI pipeline
- `.github/workflows/cd-deploy.yml`: CD pipeline
- `Dockerfile.optimized`: Backend production image
- `frontend/Dockerfile.optimized`: Frontend production image
- `deployment/scripts/migrations/run-migrations.sh`: Migration script
- `deployment/scripts/rollback.sh`: Rollback script

### Required Secrets

GitHub repository secrets that must be configured:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DATABASE_PASSWORD`
- `SLACK_WEBHOOK_URL` (optional)

### Monitoring & Alerts

Monitor pipeline health:
- CI/CD success rate
- Deployment frequency
- Mean time to recovery (MTTR)
- Test coverage trends
- Security vulnerability trends

### Best Practices

1. **Always run CI before merging PR**
2. **Deploy to staging before production**
3. **Monitor deployments for 30 minutes**
4. **Keep rollback capability ready**
5. **Test rollback procedures regularly**
6. **Maintain >80% test coverage**
7. **Fix security vulnerabilities promptly**
8. **Document configuration changes**

---

**Last Updated**: 2025-11-14  
**Version**: 1.0.0  
**Maintained By**: DevOps Team
