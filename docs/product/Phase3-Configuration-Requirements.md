# Phase 3: Configuration Requirements

**Document Version:** 1.0  
**Date:** November 6, 2025  
**Author:** Product Owner Agent  
**Status:** Configuration Specification  

---

## Purpose

This document specifies all configuration requirements for Phase 3 (Outbound Adapters Implementation), including environment variables, configuration files, secrets management, and environment-specific settings.

## Configuration Strategy

### Configuration Principles

1. **12-Factor App**: Follow 12-factor app configuration principles
2. **Environment Variables**: Primary configuration mechanism
3. **No Secrets in Code**: All secrets externalized
4. **Fail Fast**: Invalid configuration causes startup failure

### Configuration Loading Priority

1. Environment Variables (highest priority)
2. .env.{ENVIRONMENT} file (environment-specific)
3. .env file (general defaults)
4. Code defaults (lowest priority)

---

## Required Environment Variables

### Database Configuration

**DATABASE_URL** (Required)
- Type: String (connection string)
- Format: postgresql+psycopg://user:password@host:port/database
- Example: postgresql+psycopg://user:password@localhost:5433/mcpdemo
- Description: PostgreSQL database connection string

**DATABASE_POOL_SIZE** (Optional)
- Type: Integer
- Default: 10
- Range: 1-100
- Recommended: Dev=5, Staging=10, Prod=20

**DATABASE_POOL_MAX_OVERFLOW** (Optional)
- Type: Integer
- Default: 20
- Recommended: 50-100% of pool_size

**DATABASE_ECHO** (Optional)
- Type: Boolean
- Default: false
- Recommended: Dev=true, Prod=false

### Embedding Configuration

**EMBEDDING_PROVIDER** (Optional)
- Type: String (enum)
- Default: local
- Values: local, openai, fastembed, langchain
- Recommended: Dev=local, Prod=openai (based on budget)

**EMBEDDING_MODEL** (Optional)
- Type: String
- Default: Depends on provider
- Examples:
  - Local: all-MiniLM-L6-v2
  - OpenAI: text-embedding-ada-002
  - FastEmbed: BAAI/bge-small-en-v1.5

**EMBEDDING_DIMENSION** (Optional)
- Type: Integer
- Default: 1536
- Values: 384, 768, 1536
- Note: Must match database vector column dimension

**OPENAI_API_KEY** (Conditional)
- Type: String (secret)
- Required: Only if EMBEDDING_PROVIDER=openai
- Format: Starts with "sk-"
- Security: Store in environment or secrets manager, rotate quarterly

### Logging Configuration

**LOG_LEVEL** (Optional)
- Type: String (enum)
- Default: INFO
- Values: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Recommended: Dev=DEBUG, Staging=INFO, Prod=WARNING

**LOG_FORMAT** (Optional)
- Type: String (enum)
- Default: json
- Values: json, text
- Recommended: Dev=text, Prod=json

**LOG_FILE** (Optional)
- Type: String (file path)
- Default: None (stdout only)
- Example: /var/log/mcp-demo/app.log

### Performance Configuration

**CHUNK_MAX_SIZE** (Optional)
- Type: Integer
- Default: 1000
- Range: 100-5000
- Description: Maximum characters per conversation chunk

**SEARCH_TOP_K_MAX** (Optional)
- Type: Integer
- Default: 100
- Range: 1-1000
- Description: Maximum allowed top_k in search queries

**SEARCH_TIMEOUT_SECONDS** (Optional)
- Type: Integer
- Default: 5
- Range: 1-30

**EMBEDDING_BATCH_SIZE** (Optional)
- Type: Integer
- Default: 32
- Range: 1-100

### Feature Flags

**ENABLE_SLACK_INGEST** (Optional)
- Type: Boolean
- Default: true
- Values: true, false

**ENABLE_MCP_SERVER** (Optional)
- Type: Boolean
- Default: true

**ENABLE_METRICS** (Optional)
- Type: Boolean
- Default: false
- Recommended: Prod=true

**ENABLE_TRACING** (Optional)
- Type: Boolean
- Default: false
- Note: Placeholder for Phase 6

---

## Configuration Files

### .env.development

```bash
# Development Environment
DATABASE_URL=postgresql+psycopg://user:password@127.0.0.1:5433/mcpdemo
DATABASE_POOL_SIZE=5
DATABASE_ECHO=true

EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536

LOG_LEVEL=DEBUG
LOG_FORMAT=text

ENABLE_SLACK_INGEST=false
ENABLE_MCP_SERVER=true
ENABLE_METRICS=false
```

### .env.staging

```bash
# Staging Environment
DATABASE_URL=postgresql+psycopg://user:${DB_PASSWORD}@staging-db.amazonaws.com:5432/mcpdemo
DATABASE_POOL_SIZE=10
DATABASE_ECHO=false

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_API_KEY=${STAGING_OPENAI_API_KEY}

LOG_LEVEL=INFO
LOG_FORMAT=json

ENABLE_SLACK_INGEST=true
ENABLE_MCP_SERVER=true
ENABLE_METRICS=true
```

### .env.production

```bash
# Production Environment
DATABASE_URL=postgresql+psycopg://user:${DB_PASSWORD}@prod-db.amazonaws.com:5432/mcpdemo
DATABASE_POOL_SIZE=20
DATABASE_ECHO=false

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_API_KEY=${PROD_OPENAI_API_KEY}

LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=/var/log/mcp-demo/app.log

ENABLE_SLACK_INGEST=true
ENABLE_MCP_SERVER=true
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### .env.example (Template)

```bash
# Configuration Template
# Copy to .env and customize

# Database
DATABASE_URL=postgresql+psycopg://user:password@host:port/database
DATABASE_POOL_SIZE=10

# Embeddings
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=1536
#OPENAI_API_KEY=sk-...

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Features
ENABLE_SLACK_INGEST=true
ENABLE_MCP_SERVER=true
ENABLE_METRICS=false
```

---

## Environment-Specific Configurations

### Development
- Local PostgreSQL (Docker)
- Local embeddings (free)
- Debug logging
- Metrics disabled

### Staging
- AWS RDS PostgreSQL
- OpenAI embeddings (test key)
- Info logging
- Metrics enabled

### Production
- AWS RDS Multi-AZ
- OpenAI embeddings (prod key)
- Warning logging only
- All monitoring enabled

---

## Secrets Management

### Development
- Storage: .env file (gitignored)
- Security: File permissions (chmod 600)

### Staging/Production
- Storage: AWS Secrets Manager
- Access: IAM roles
- Rotation: Quarterly (automated)

---

## Configuration Validation

### Validation at Startup

Requirements:
- All required variables present
- Valid values (type, range, format)
- Dependencies satisfied
- Database connection successful

Failure Behavior:
- Log all validation errors
- Exit with non-zero code
- Do NOT start with invalid config

---

## Configuration Checklist

### Development Setup
- [ ] Copy .env.example to .env
- [ ] Set DATABASE_URL for local Docker
- [ ] Set EMBEDDING_PROVIDER=local
- [ ] Set LOG_LEVEL=DEBUG
- [ ] Test application starts

### Staging Setup
- [ ] Create .env.staging
- [ ] Store secrets in AWS Secrets Manager
- [ ] Test database connectivity
- [ ] Test OpenAI API key
- [ ] Deploy and verify

### Production Setup
- [ ] Create .env.production
- [ ] Store all secrets in AWS Secrets Manager
- [ ] Configure IAM roles
- [ ] Enable all monitoring
- [ ] Set LOG_LEVEL=WARNING
- [ ] Test connectivity
- [ ] Perform dry-run
- [ ] Deploy to production
- [ ] Verify health checks

---

**Document Status**: Ready for Implementation
