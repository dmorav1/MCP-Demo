# Security Architecture

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-13

## Executive Summary

This document outlines the comprehensive security architecture for the MCP RAG Demo production deployment, covering network security, authentication, authorization, secrets management, and compliance.

## Security Principles

- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimal permissions for all components
- **Zero Trust**: No implicit trust, verify everything
- **Encryption Everywhere**: Data at rest and in transit
- **Security by Default**: Secure configurations out of the box

## Table of Contents

1. [Network Security](#network-security)
2. [Identity and Access Management](#identity-and-access-management)
3. [Secrets Management](#secrets-management)
4. [API Security](#api-security)
5. [Data Protection](#data-protection)
6. [Container Security](#container-security)
7. [Compliance](#compliance)

---

## Network Security

### VPC Architecture

**Security Zones**:
1. **Public Subnets**: Load balancers, NAT gateways only
2. **Private Subnets**: Application workloads (EKS nodes)
3. **Database Subnets**: Data layer, no internet access

**Network Segmentation**:
```
Internet
    ↓ (HTTPS only)
AWS WAF → CloudFront → ALB
    ↓ (Port 8000)
EKS Nodes (Private)
    ↓ (PostgreSQL 5432, Redis 6379)
RDS/ElastiCache (Database Subnet)
```

### Security Groups

**Layered Security Model**:

1. **ALB Security Group**
   - Inbound: 443 (HTTPS), 80 (HTTP redirect) from 0.0.0.0/0
   - Outbound: 8000 to EKS node security group

2. **EKS Node Security Group**
   - Inbound: 8000 from ALB, all ports from self
   - Outbound: 5432 to database SG, 6379 to cache SG, 443 to internet

3. **Database Security Group**
   - Inbound: 5432 from EKS node SG only
   - Outbound: None

### Network Policies (Kubernetes)

**Default Deny Policy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: mcp-demo
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

**Allow Backend Traffic**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend
  namespace: mcp-demo
spec:
  podSelector:
    matchLabels:
      app: mcp-backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: istio-system
          podSelector:
            matchLabels:
              app: istio-ingressgateway
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    - ports:
        - protocol: TCP
          port: 443  # External API calls (OpenAI, etc.)
```

### SSL/TLS Configuration

**Certificate Management**:
- **Production**: AWS Certificate Manager (ACM)
- **Staging**: Let's Encrypt
- **Development**: Self-signed certificates

**TLS Settings**:
- Minimum version: TLS 1.2
- Preferred version: TLS 1.3
- Cipher suites: Strong ciphers only (AES-GCM, ChaCha20)
- HSTS enabled: `max-age=31536000; includeSubDomains`

**Service Mesh mTLS**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: mcp-demo
spec:
  mtls:
    mode: STRICT
```

### AWS WAF Rules

**Protection Rules**:
1. **Rate Limiting**: 2000 requests per 5 minutes per IP
2. **Geo-blocking**: Block high-risk countries (configurable)
3. **SQL Injection**: AWS Managed SQL injection rule group
4. **XSS Protection**: AWS Managed XSS rule group
5. **Bot Control**: AWS Managed Bot Control rule group
6. **IP Reputation**: Block known malicious IPs

**Custom Rules**:
```json
{
  "Name": "RateLimitRule",
  "Priority": 1,
  "Action": {
    "Block": {}
  },
  "Statement": {
    "RateBasedStatement": {
      "Limit": 2000,
      "AggregateKeyType": "IP"
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "RateLimitRule"
  }
}
```

---

## Identity and Access Management

### AWS IAM

**Principle of Least Privilege**:

1. **EKS Node Role**
   - EC2 Container Registry (read-only)
   - CloudWatch Logs (write-only)
   - AWS Secrets Manager (read specific secrets)
   - S3 backups bucket (read/write)

2. **RDS Role**
   - Enhanced monitoring
   - CloudWatch logs export

3. **Application Service Account (IRSA)**
   - Secrets Manager access for specific secrets
   - S3 access for backups
   - CloudWatch metrics/logs

**IAM Policy Example**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:mcp-demo/prod/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::mcp-demo-prod-backups/*"
    }
  ]
}
```

### Kubernetes RBAC

**Service Account for Backend**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-backend
  namespace: mcp-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/mcp-backend-role
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mcp-backend-role
  namespace: mcp-demo
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mcp-backend-binding
  namespace: mcp-demo
subjects:
  - kind: ServiceAccount
    name: mcp-backend
    namespace: mcp-demo
roleRef:
  kind: Role
  name: mcp-backend-role
  apiGroup: rbac.authorization.k8s.io
```

### API Authentication & Authorization

**Authentication Methods**:

1. **API Keys** (Primary)
   - Format: `Bearer <api-key>`
   - Stored in AWS Secrets Manager
   - Rotated every 90 days
   - Rate-limited per key

2. **OAuth 2.0** (Future)
   - Client credentials flow
   - JWT tokens with 1-hour expiration
   - Refresh tokens for long-lived sessions

3. **Service-to-Service**
   - mTLS with Istio
   - Service account tokens
   - JWT validation

**Authorization**:
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    api_key = credentials.credentials
    if not await validate_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/conversations/ingest")
async def ingest(api_key: str = Depends(verify_api_key)):
    # Authorized request
    pass
```

---

## Secrets Management

### AWS Secrets Manager

**Secret Organization**:
```
/mcp-demo/prod/
  ├── database/url
  ├── database/password
  ├── redis/url
  ├── api-keys/openai
  ├── api-keys/anthropic
  └── application/jwt-secret
```

**Rotation Policy**:
- Database passwords: 90 days
- API keys: 90 days (manual coordination with provider)
- JWT secrets: 180 days
- Service account tokens: Auto-rotated by Kubernetes

**Access Pattern**:
```python
import boto3
from functools import lru_cache

@lru_cache(maxsize=128)
def get_secret(secret_name: str) -> str:
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Usage
DATABASE_URL = get_secret('/mcp-demo/prod/database/url')
```

**Kubernetes Integration**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: mcp-demo
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
    - secretKey: url
      remoteRef:
        key: /mcp-demo/prod/database/url
```

### Environment-Specific Secrets

| Environment | Secret Scope | Rotation Frequency |
|-------------|--------------|-------------------|
| Development | Local only | Never (test values) |
| Staging | Separate AWS account | 90 days |
| Production | Separate AWS account | 90 days (automated) |

---

## API Security

### Rate Limiting

**Implementation Layers**:

1. **AWS WAF**: 2000 req/5min per IP
2. **ALB**: Connection limiting
3. **Istio**: Rate limiting per user/API key
4. **Application**: Fine-grained limits

**Application-Level Rate Limiting**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/rag/ask")
@limiter.limit("100/minute")
async def ask_question(request: Request):
    # Limited endpoint
    pass
```

**Rate Limits by Tier**:
| Tier | Requests/Minute | Requests/Hour |
|------|----------------|---------------|
| Free | 10 | 100 |
| Basic | 100 | 1,000 |
| Pro | 1,000 | 10,000 |
| Enterprise | Unlimited | Unlimited |

### Input Validation

**Validation Strategy**:
```python
from pydantic import BaseModel, Field, validator

class IngestRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=100000)
    
    @validator('content')
    def sanitize_content(cls, v):
        # Remove potential XSS vectors
        return sanitize_html(v)
```

**SQL Injection Prevention**:
- Use SQLAlchemy ORM (parameterized queries)
- Never concatenate user input into SQL
- Database user has minimal permissions

**CORS Configuration**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mcp-demo.example.com",
        "https://staging.mcp-demo.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

---

## Data Protection

### Encryption at Rest

**Database Encryption**:
- RDS encryption enabled with AWS KMS
- EBS volumes encrypted (EKS nodes)
- S3 buckets encrypted (SSE-S3 or SSE-KMS)

**Encryption Keys**:
- Customer-managed KMS keys
- Key rotation: Automatic (yearly)
- Key policy: Least privilege access

### Encryption in Transit

**All traffic encrypted**:
- Internet → ALB: TLS 1.3
- ALB → EKS: TLS 1.2+
- Pod ↔ Pod: mTLS via Istio
- EKS → RDS: TLS 1.2
- EKS → Redis: TLS 1.2

### Data Anonymization

**PII Handling**:
```python
def anonymize_pii(text: str) -> str:
    # Replace email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                  '[EMAIL]', text)
    # Replace phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    # Replace SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    return text
```

**Data Retention**:
- Conversation data: 90 days (configurable)
- Logs: 30 days
- Backups: 30 days
- Audit logs: 1 year

---

## Container Security

### Image Security

**Base Images**:
- Use official Python slim images
- Regular security scanning
- No root user in containers

**Dockerfile Best Practices**:
```dockerfile
FROM python:3.11-slim AS base

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy only requirements first (cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser app /app

USER appuser
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Image Scanning**:
- Trivy scan in CI pipeline
- Block deployment if critical vulnerabilities found
- Scan on push to ECR

### Pod Security

**Pod Security Standards**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Security Context**:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

---

## Compliance

### Standards & Frameworks

**Target Compliance**:
- SOC 2 Type II (future)
- GDPR (data protection)
- CCPA (California privacy)
- HIPAA (if handling health data)

### Audit Logging

**CloudTrail Logging**:
- All API calls logged
- Multi-region trail
- Log file validation enabled
- Stored in S3 with replication

**Application Audit Logs**:
```python
import structlog

audit_logger = structlog.get_logger("audit")

@app.post("/conversations/ingest")
async def ingest(request: Request, api_key: str = Depends(verify_api_key)):
    audit_logger.info(
        "conversation_ingested",
        user_id=get_user_from_api_key(api_key),
        ip_address=request.client.host,
        conversation_id=conversation_id,
        action="ingest",
        result="success"
    )
```

### Security Monitoring

**AWS GuardDuty**:
- Enabled in all regions
- Threat detection for:
  - Unusual API calls
  - Compromised instances
  - Reconnaissance activity

**AWS Security Hub**:
- Centralized security findings
- CIS AWS Foundations Benchmark
- PCI DSS compliance checks

---

## Security Incident Response

### Incident Response Plan

**Phases**:
1. **Detection**: Automated alerts + monitoring
2. **Containment**: Isolate affected components
3. **Eradication**: Remove threat
4. **Recovery**: Restore services
5. **Post-Incident**: Review and improve

**Runbook Location**: `/deployment/docs/runbooks/security-incident-response.md`

### Security Contacts

- Security Team: security@example.com
- On-Call Engineer: Pager Duty integration
- AWS Support: Enterprise support plan

---

## Security Checklist

Production deployment security checklist:

- [ ] VPC with private subnets configured
- [ ] Security groups follow least privilege
- [ ] Network policies implemented
- [ ] TLS 1.2+ enforced everywhere
- [ ] AWS WAF rules enabled
- [ ] Secrets in AWS Secrets Manager
- [ ] IAM roles follow least privilege
- [ ] RBAC configured in Kubernetes
- [ ] API authentication enabled
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] Database encryption enabled
- [ ] S3 bucket encryption enabled
- [ ] Container images scanned
- [ ] Pod security standards enforced
- [ ] Audit logging enabled
- [ ] GuardDuty enabled
- [ ] Security Hub enabled
- [ ] Incident response plan documented

---

**Document Version**: 1.0  
**Author**: Architect Agent  
**Review Status**: Pending approval  
**Last Updated**: 2025-11-13
