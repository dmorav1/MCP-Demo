# CONFIGURATION MANAGEMENT

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-13

## Overview

This document provides comprehensive guidance for CONFIGURATION MANAGEMENT in the MCP Demo production deployment.


## Environment Configuration Strategy

### Configuration Hierarchy

```
Base Configuration (config/base.yaml)
    ↓
Environment Overrides (config/{dev,staging,prod}.yaml)
    ↓
Secret Injection (AWS Secrets Manager)
    ↓
Runtime Environment Variables
```

### Configuration Files

**Base Configuration** (`config/base.yaml`):
```yaml
app:
  name: mcp-demo
  log_level: INFO
  use_json_logs: true

database:
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600

cache:
  enabled: true
  default_ttl: 3600
  max_size: 1000

llm:
  provider: openai
  model: gpt-3.5-turbo
  temperature: 0.7
  max_tokens: 1000
```

**Production Overrides** (`config/prod.yaml`):
```yaml
app:
  log_level: WARNING
  
database:
  pool_size: 20
  max_overflow: 40

cache:
  enabled: true
  backend: redis
  default_ttl: 7200
```

### Environment-Specific ConfigMaps

**Development**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-backend-config
  namespace: mcp-demo-dev
data:
  environment: development
  log_level: DEBUG
  database_pool_size: "5"
  cache_enabled: "false"
```

**Staging**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-backend-config
  namespace: mcp-demo-staging
data:
  environment: staging
  log_level: INFO
  database_pool_size: "10"
  cache_enabled: "true"
  cache_backend: redis
```

**Production**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-backend-config
  namespace: mcp-demo
data:
  environment: production
  log_level: WARNING
  database_pool_size: "20"
  cache_enabled: "true"
  cache_backend: redis
  cache_default_ttl: "7200"
```

## Secret Management

### AWS Secrets Manager

**Secret Structure**:
```
/mcp-demo/
  ├── dev/
  │   ├── database/url
  │   ├── api-keys/openai
  │   └── jwt-secret
  ├── staging/
  │   ├── database/url
  │   ├── api-keys/openai
  │   └── jwt-secret
  └── prod/
      ├── database/url
      ├── database/readonly-url
      ├── redis/url
      ├── api-keys/openai
      ├── api-keys/anthropic
      └── jwt-secret
```

**External Secrets Operator**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: mcp-demo
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mcp-backend-secrets
  namespace: mcp-demo
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: mcp-backend-secrets
    creationPolicy: Owner
  data:
    - secretKey: database-url
      remoteRef:
        key: /mcp-demo/prod/database/url
    - secretKey: redis-url
      remoteRef:
        key: /mcp-demo/prod/redis/url
    - secretKey: openai-api-key
      remoteRef:
        key: /mcp-demo/prod/api-keys/openai
```

### Secret Rotation

**Rotation Schedule**:
- Database passwords: Every 90 days
- API keys: Every 90 days (coordinate with provider)
- JWT secrets: Every 180 days
- Service account tokens: Auto-rotated by Kubernetes

**Rotation Process**:
1. Generate new secret
2. Store in AWS Secrets Manager with new version
3. Update application to use new secret
4. Wait 24 hours (grace period)
5. Revoke old secret

**Automated Rotation Script**:
```python
import boto3
from datetime import datetime, timedelta

def rotate_database_password():
    secrets_client = boto3.client('secretsmanager')
    rds_client = boto3.client('rds')
    
    # Generate new password
    new_password = secrets_client.get_random_password(
        PasswordLength=32,
        ExcludeCharacters='/@"\''
    )['RandomPassword']
    
    # Update RDS password
    rds_client.modify_db_instance(
        DBInstanceIdentifier='mcp-demo-prod',
        MasterUserPassword=new_password,
        ApplyImmediately=False  # Apply during maintenance window
    )
    
    # Update secret
    secrets_client.update_secret(
        SecretId='/mcp-demo/prod/database/password',
        SecretString=new_password
    )
    
    print(f"Password rotated successfully at {datetime.now()}")
```

## Feature Flags

### LaunchDarkly Integration

**Feature Flag Examples**:
```python
from ldclient import Context, LDClient

ld_client = LDClient(sdk_key=os.getenv('LAUNCHDARKLY_SDK_KEY'))

def is_feature_enabled(feature_key: str, user_id: str) -> bool:
    context = Context.builder(user_id).build()
    return ld_client.variation(feature_key, context, False)

# Usage
@app.post("/rag/ask")
async def ask_question(request: RAGRequest, user_id: str = Depends(get_user_id)):
    # Check if new RAG algorithm is enabled
    if is_feature_enabled("new-rag-algorithm", user_id):
        return await new_rag_service.ask(request)
    else:
        return await old_rag_service.ask(request)
```

**Feature Flag Strategy**:
| Flag | Type | Purpose | Rollout |
|------|------|---------|---------|
| `new-rag-algorithm` | Release | New RAG implementation | Gradual 10% → 100% |
| `cache-embeddings` | Ops | Enable embedding cache | On/off toggle |
| `enhanced-logging` | Ops | Detailed debug logs | On for specific users |
| `streaming-responses` | Release | Streaming RAG responses | Beta users first |

### Configuration Management Tools

**Kustomize Overlays**:
```
deployment/kubernetes/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   └── prod/
│       ├── kustomization.yaml
│       └── patches/
```

**Kustomization Example** (`overlays/prod/kustomization.yaml`):
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: mcp-demo

bases:
  - ../../base

namePrefix: prod-

commonLabels:
  environment: production
  managed-by: kustomize

replicas:
  - name: mcp-backend
    count: 3

images:
  - name: mcp-backend
    newName: 123456789012.dkr.ecr.us-east-1.amazonaws.com/mcp-backend
    newTag: v1.0.0

configMapGenerator:
  - name: mcp-backend-config
    behavior: merge
    literals:
      - LOG_LEVEL=WARNING
      - DATABASE_POOL_SIZE=20
      - CACHE_ENABLED=true

patchesStrategicMerge:
  - patches/increase-resources.yaml
  - patches/add-istio.yaml
```

## Configuration Validation

### Pre-Deployment Validation

**Schema Validation**:
```python
from pydantic import BaseSettings, Field, validator

class AppConfig(BaseSettings):
    environment: str = Field(..., regex="^(dev|staging|prod)$")
    log_level: str = Field(..., regex="^(DEBUG|INFO|WARNING|ERROR)$")
    database_url: str = Field(..., min_length=10)
    database_pool_size: int = Field(10, ge=1, le=100)
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith('postgresql://'):
            raise ValueError('Database URL must use postgresql:// scheme')
        return v
    
    class Config:
        env_file = '.env'
        case_sensitive = False

# Load and validate
try:
    config = AppConfig()
except ValidationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

**Pre-Deployment Checks**:
```bash
#!/bin/bash
# validate-config.sh

set -e

echo "Validating configuration..."

# Check required secrets exist
aws secretsmanager describe-secret --secret-id /mcp-demo/prod/database/url || exit 1
aws secretsmanager describe-secret --secret-id /mcp-demo/prod/api-keys/openai || exit 1

# Validate Kubernetes manifests
kubectl apply --dry-run=client -f deployment/kubernetes/overlays/prod/

# Validate Terraform
cd deployment/terraform
terraform validate

# Validate Kustomize
kustomize build deployment/kubernetes/overlays/prod/ | kubectl apply --dry-run=server -f -

echo "Configuration validation passed!"
```

## Configuration Documentation

### Configuration Reference

**Application Configuration**:
```markdown
# Configuration Reference

## Environment Variables

### Required
- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql://user:pass@host:port/db`
  - Example: `postgresql://mcp_user:password@db.example.com:5432/mcp_db`

- `OPENAI_API_KEY`: OpenAI API key
  - Format: `sk-...`
  - Source: https://platform.openai.com/api-keys

### Optional
- `LOG_LEVEL`: Logging level (default: INFO)
  - Values: DEBUG, INFO, WARNING, ERROR, CRITICAL

- `CACHE_ENABLED`: Enable response caching (default: true)
  - Values: true, false

- `CACHE_BACKEND`: Cache backend (default: memory)
  - Values: memory, redis

- `DATABASE_POOL_SIZE`: Connection pool size (default: 10)
  - Range: 1-100
```

### Change Management

**Configuration Change Process**:
1. Create PR with configuration changes
2. Review by platform team
3. Test in development environment
4. Deploy to staging
5. Validate in staging
6. Deploy to production
7. Monitor for 24 hours

**High-Risk Changes** (require additional approval):
- Database connection strings
- API keys
- Authentication settings
- Rate limiting thresholds

---

**Document Version**: 1.0  
**Author**: Architect Agent  
**Last Updated**: 2025-11-13
