# Operations Guide - MCP RAG Demo

**Version:** 1.0  
**Date:** November 7, 2025  
**Status:** Complete  
**Related Documents:**
- [Phase 3 Architecture](Phase3-Architecture.md)
- [Configuration Guide](Configuration-Guide.md)
- [Phase 3 Migration Guide](Phase3-Migration-Guide.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Deployment Procedures](#deployment-procedures)
3. [Monitoring and Observability](#monitoring-and-observability)
4. [Health Checks](#health-checks)
5. [Incident Response](#incident-response)
6. [Backup and Recovery](#backup-and-recovery)
7. [Scaling and Performance](#scaling-and-performance)
8. [Maintenance Procedures](#maintenance-procedures)

---

## Overview

This guide provides operational procedures for deploying, monitoring, and maintaining the MCP RAG Demo application in production environments.

### Operational Responsibilities

**DevOps Team:**
- Deploy and configure infrastructure
- Monitor system health and performance
- Respond to incidents and outages
- Perform backups and disaster recovery
- Scale resources based on demand

**Development Team:**
- Provide deployment artifacts
- Support incident investigation
- Implement fixes for production issues
- Optimize application performance

---

## Deployment Procedures

### Prerequisites

Before deployment:
- [ ] Infrastructure provisioned (compute, database, networking)
- [ ] Secrets configured in secret manager
- [ ] Configuration validated
- [ ] Database schema migrated to latest version
- [ ] Health checks tested in staging
- [ ] Rollback plan documented

### Deployment Methods

#### Method 1: Docker Compose (Development/Staging)

**1. Prepare Configuration**
```bash
# Create production .env file
cp .env.example .env.production
nano .env.production

# Verify configuration
python scripts/validate_config.py --env-file=.env.production
```

**2. Build Images**
```bash
# Build application image
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Tag for registry
docker tag mcp-demo:latest registry.example.com/mcp-demo:v1.0.0
docker tag mcp-demo:latest registry.example.com/mcp-demo:latest

# Push to registry
docker push registry.example.com/mcp-demo:v1.0.0
docker push registry.example.com/mcp-demo:latest
```

**3. Deploy**
```bash
# Pull latest images
docker-compose pull

# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose ps
docker-compose logs -f mcp-backend
```

**4. Smoke Test**
```bash
# Health check
curl http://localhost:8000/health

# Test ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d @test-data.json

# Test search
curl "http://localhost:8000/search?q=test&top_k=5"
```

#### Method 2: Kubernetes

**1. Create Namespace**
```bash
kubectl create namespace mcp-prod
kubectl config set-context --current --namespace=mcp-prod
```

**2. Deploy Secrets**
```bash
# Create secrets from files
kubectl create secret generic mcp-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --namespace=mcp-prod

# Verify
kubectl get secrets -n mcp-prod
```

**3. Deploy Database (if not using managed service)**
```bash
# Apply PostgreSQL + pgvector deployment
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-pvc.yaml

# Wait for ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
```

**4. Deploy Application**
```bash
# Apply application deployment
kubectl apply -f k8s/mcp-backend-deployment.yaml
kubectl apply -f k8s/mcp-backend-service.yaml
kubectl apply -f k8s/mcp-backend-ingress.yaml

# Wait for ready
kubectl wait --for=condition=ready pod -l app=mcp-backend --timeout=300s

# Check status
kubectl get pods -l app=mcp-backend
kubectl logs -l app=mcp-backend --tail=100
```

**5. Verify Deployment**
```bash
# Get service endpoint
kubectl get service mcp-backend

# Health check
kubectl port-forward service/mcp-backend 8000:8000 &
curl http://localhost:8000/health
```

#### Method 3: AWS ECS/Fargate

**1. Create Task Definition**
```json
{
  "family": "mcp-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "mcp-backend",
      "image": "registry.example.com/mcp-demo:v1.0.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "USE_NEW_ARCHITECTURE",
          "value": "true"
        },
        {
          "name": "EMBEDDING_PROVIDER",
          "value": "openai"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:mcp/prod/openai-key"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:mcp/prod/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**2. Create Service**
```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster mcp-prod-cluster \
  --service-name mcp-backend \
  --task-definition mcp-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=mcp-backend,containerPort=8000"

# Wait for stable
aws ecs wait services-stable --cluster mcp-prod-cluster --services mcp-backend
```

### Rolling Updates

**Docker Compose:**
```bash
# Pull new version
docker-compose pull

# Rolling update (one container at a time)
docker-compose up -d --no-deps --build mcp-backend

# Verify
docker-compose ps
```

**Kubernetes:**
```bash
# Update image
kubectl set image deployment/mcp-backend mcp-backend=registry.example.com/mcp-demo:v1.0.1

# Watch rollout
kubectl rollout status deployment/mcp-backend

# Rollback if needed
kubectl rollout undo deployment/mcp-backend
```

**ECS:**
```bash
# Update service with new task definition
aws ecs update-service \
  --cluster mcp-prod-cluster \
  --service mcp-backend \
  --task-definition mcp-backend:2 \
  --force-new-deployment

# Monitor
aws ecs wait services-stable --cluster mcp-prod-cluster --services mcp-backend
```

### Blue-Green Deployment

**1. Deploy Green Environment**
```bash
# Deploy new version to green environment
kubectl apply -f k8s/mcp-backend-green-deployment.yaml

# Verify green is healthy
kubectl get pods -l app=mcp-backend,env=green
```

**2. Switch Traffic**
```bash
# Update service selector to point to green
kubectl patch service mcp-backend -p '{"spec":{"selector":{"env":"green"}}}'

# Monitor for errors
kubectl logs -l app=mcp-backend,env=green --tail=100 -f
```

**3. Decommission Blue**
```bash
# After validation period (e.g., 1 hour)
kubectl delete deployment mcp-backend-blue
```

### Canary Deployment

**1. Deploy Canary**
```bash
# Deploy canary with 10% of traffic
kubectl apply -f k8s/mcp-backend-canary-deployment.yaml

# Verify canary is healthy
kubectl get pods -l app=mcp-backend,canary=true
```

**2. Configure Traffic Split**
```yaml
# Using Istio or similar
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: mcp-backend
spec:
  hosts:
  - mcp-backend
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: mcp-backend-canary
        weight: 100
  - route:
    - destination:
        host: mcp-backend-stable
        weight: 90
    - destination:
        host: mcp-backend-canary
        weight: 10
```

**3. Monitor and Promote**
```bash
# Monitor canary metrics for 24 hours
# If successful, promote to 100%
kubectl apply -f k8s/mcp-backend-stable-deployment.yaml

# Decommission old version
kubectl delete deployment mcp-backend-old
```

---

## Monitoring and Observability

### Logging

**Log Aggregation**

All logs are structured JSON for easy parsing:

```json
{
  "timestamp": "2025-11-07T14:30:45.123Z",
  "level": "INFO",
  "logger": "app.application.ingest_conversation",
  "message": "Conversation ingested successfully",
  "conversation_id": "123",
  "chunk_count": 15,
  "duration_ms": 1234,
  "trace_id": "abc-def-ghi"
}
```

**Log Collection:**

**Option 1: ELK Stack**
```bash
# Filebeat configuration
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
  - add_docker_metadata: ~

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "mcp-backend-%{+yyyy.MM.dd}"
```

**Option 2: CloudWatch Logs (AWS)**
```bash
# Already configured in ECS task definition
# View logs:
aws logs tail /ecs/mcp-backend --follow
```

**Option 3: Kubernetes Logs**
```bash
# View logs
kubectl logs -l app=mcp-backend --tail=100 -f

# With stern (multi-pod)
stern mcp-backend
```

**Important Log Queries:**

```bash
# Errors in last hour
grep '"level":"ERROR"' logs.json | jq -r '.message'

# Slow requests (>5s)
jq 'select(.duration_ms > 5000)' logs.json

# Failed embeddings
jq 'select(.message | contains("EmbeddingError"))' logs.json
```

### Metrics

**Application Metrics**

Key metrics to track:

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `http_requests_total` | Counter | Total HTTP requests | N/A |
| `http_request_duration_seconds` | Histogram | Request latency | p95 > 2s |
| `ingest_conversations_total` | Counter | Conversations ingested | N/A |
| `ingest_duration_seconds` | Histogram | Ingestion time | p95 > 5s |
| `search_requests_total` | Counter | Search queries | N/A |
| `search_duration_seconds` | Histogram | Search latency | p95 > 0.5s |
| `embedding_generation_duration_seconds` | Histogram | Embedding time | p95 > 0.5s |
| `embedding_errors_total` | Counter | Embedding failures | > 10/min |
| `database_connections_active` | Gauge | Active DB connections | > 80% of pool |
| `database_query_duration_seconds` | Histogram | DB query time | p95 > 1s |

**Prometheus Configuration**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['mcp-backend:8000']
    metrics_path: '/metrics'
```

**Grafana Dashboard**

Import dashboard from `monitoring/grafana-dashboard.json`:

**Panels:**
1. Request Rate (requests/sec)
2. Request Duration (p50, p95, p99)
3. Error Rate (errors/sec, % of total)
4. Ingestion Throughput (conversations/min)
5. Search Latency (ms, p95)
6. Database Connections (active/total)
7. Embedding Generation Time (ms)
8. CPU and Memory Usage

### Alerting

**Critical Alerts (Page On-Call)**

**1. Service Down**
```yaml
# Prometheus alert rule
- alert: ServiceDown
  expr: up{job="mcp-backend"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "MCP Backend is down"
    description: "Service {{ $labels.instance }} has been down for more than 1 minute"
```

**2. High Error Rate**
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }} errors/sec"
```

**3. Database Unavailable**
```yaml
- alert: DatabaseDown
  expr: database_connections_active == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Database connection lost"
    description: "No active database connections"
```

**Warning Alerts (Notify Team)**

**4. Slow Requests**
```yaml
- alert: SlowRequests
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Requests are slow"
    description: "p95 latency is {{ $value }}s"
```

**5. High Database Connection Usage**
```yaml
- alert: HighDBConnectionUsage
  expr: (database_connections_active / database_connections_total) > 0.8
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Database connection pool nearly exhausted"
    description: "{{ $value | humanizePercentage }} of connections in use"
```

**Alert Destinations:**

**PagerDuty:**
```yaml
# alertmanager.yml
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '<pagerduty-integration-key>'
    description: '{{ .CommonAnnotations.summary }}'
```

**Slack:**
```yaml
- name: 'slack-warnings'
  slack_configs:
  - api_url: '<slack-webhook-url>'
    channel: '#mcp-alerts'
    title: 'Alert: {{ .CommonLabels.alertname }}'
    text: '{{ .CommonAnnotations.description }}'
```

### Distributed Tracing

**OpenTelemetry Integration**

```python
# app/infrastructure/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_tracing():
    """Configure distributed tracing."""
    tracer_provider = TracerProvider()
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(tracer_provider)
```

**Trace Example:**
```
Trace: Ingest Conversation (3.2s)
├── Validate Input (10ms)
├── Chunk Messages (50ms)
├── Generate Embeddings (2.8s)
│   ├── Batch 1: 10 texts (1.4s)
│   └── Batch 2: 5 texts (700ms)
└── Save to Database (340ms)
    ├── Insert Conversation (50ms)
    └── Insert Chunks (290ms)
```

---

## Health Checks

### Health Check Endpoint

**Endpoint:** `GET /health`

**Response (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T14:30:45.123Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "embedding_service": {
      "status": "healthy",
      "provider": "openai",
      "model": "text-embedding-ada-002"
    },
    "di_container": {
      "status": "healthy",
      "architecture": "new"
    }
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-07T14:30:45.123Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "embedding_service": {
      "status": "healthy",
      "provider": "openai",
      "model": "text-embedding-ada-002"
    },
    "di_container": {
      "status": "healthy",
      "architecture": "new"
    }
  }
}
```

### Liveness Probe

**Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Readiness Probe

**Kubernetes:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 3
```

### Startup Probe

**Kubernetes (for slow-starting containers):**
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30  # Allow up to 5 minutes for startup
```

---

## Incident Response

### Incident Severity Levels

**SEV-1 (Critical)**
- Service completely down
- Data loss or corruption
- Security breach
- **Response Time:** Immediate (page on-call)
- **Resolution SLA:** 1 hour

**SEV-2 (High)**
- Degraded service performance
- Feature unavailable
- High error rate (>10%)
- **Response Time:** 15 minutes
- **Resolution SLA:** 4 hours

**SEV-3 (Medium)**
- Minor performance issues
- Non-critical feature impaired
- Elevated error rate (1-10%)
- **Response Time:** 1 hour
- **Resolution SLA:** 1 business day

**SEV-4 (Low)**
- Cosmetic issues
- Documentation errors
- Minor bugs
- **Response Time:** Next business day
- **Resolution SLA:** 1 week

### Incident Response Procedure

**1. Detection and Alerting**
- Alert fired (PagerDuty, Slack, etc.)
- On-call engineer paged
- Incident declared in tracking system

**2. Initial Response (5 minutes)**
```bash
# Acknowledge alert
pagerduty ack <incident-id>

# Check service status
kubectl get pods -l app=mcp-backend
kubectl logs -l app=mcp-backend --tail=100

# Check recent deployments
kubectl rollout history deployment/mcp-backend

# Check metrics
open https://grafana.example.com/dashboard/mcp-backend
```

**3. Assessment (10 minutes)**
- Determine severity level
- Identify affected components
- Estimate user impact
- Escalate if needed

**4. Mitigation (varies)**

**Common Mitigations:**

**Service Down:**
```bash
# Restart pods
kubectl rollout restart deployment/mcp-backend

# Or rollback to previous version
kubectl rollout undo deployment/mcp-backend
```

**Database Issues:**
```bash
# Check database status
kubectl logs -l app=postgres --tail=100

# Check connections
psql -h postgres -U user -d mcp_db -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Restart if needed
kubectl rollout restart deployment/postgres
```

**High Error Rate:**
```bash
# Check recent errors
kubectl logs -l app=mcp-backend | grep ERROR | tail -50

# Scale up if traffic spike
kubectl scale deployment/mcp-backend --replicas=5

# Enable feature flag rollback if new code issue
kubectl set env deployment/mcp-backend USE_NEW_ARCHITECTURE=false
```

**5. Communication**
- Update status page
- Notify stakeholders
- Regular updates every 30 minutes

**6. Resolution**
- Verify fix resolves issue
- Monitor metrics for stability
- Document root cause

**7. Post-Mortem**
- Write incident report within 48 hours
- Identify action items
- Schedule follow-up review

### Runbooks

**Runbook: Database Connection Pool Exhausted**

**Symptoms:**
- `database_connections_active` at maximum
- Slow requests or timeouts
- Errors: "QueuePool limit exceeded"

**Diagnosis:**
```bash
# Check connection pool usage
kubectl logs -l app=mcp-backend | grep "connection pool"

# Check for connection leaks
psql -d mcp_db -c "SELECT state, COUNT(*) FROM pg_stat_activity GROUP BY state;"
```

**Mitigation:**
```bash
# Quick fix: Increase pool size
kubectl set env deployment/mcp-backend DB_POOL_SIZE=20 DB_MAX_OVERFLOW=40

# Restart to apply changes
kubectl rollout restart deployment/mcp-backend
```

**Root Cause Analysis:**
- Check for code that doesn't close sessions
- Review long-running transactions
- Check for increased traffic

**Runbook: OpenAI API Rate Limited**

**Symptoms:**
- Embedding generation errors
- Errors: "Rate limit exceeded"
- `embedding_errors_total` increased

**Diagnosis:**
```bash
# Check OpenAI usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check error logs
kubectl logs -l app=mcp-backend | grep "RateLimitError"
```

**Mitigation:**
```bash
# Short-term: Switch to local provider
kubectl set env deployment/mcp-backend \
  EMBEDDING_PROVIDER=local \
  EMBEDDING_MODEL=all-MiniLM-L6-v2

# Restart
kubectl rollout restart deployment/mcp-backend
```

**Long-term:**
- Request rate limit increase from OpenAI
- Implement caching layer
- Use batch operations more effectively

---

## Backup and Recovery

### Database Backup

**Automated Backups (Recommended)**

**PostgreSQL (pg_dump):**
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="mcp_db"

# Create backup
pg_dump -h postgres -U user -d $DB_NAME | gzip > $BACKUP_DIR/mcp_db_$DATE.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/mcp_db_$DATE.sql.gz s3://mcp-backups/daily/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**CronJob (Kubernetes):**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres -U user -d mcp_db | \
              gzip | \
              aws s3 cp - s3://mcp-backups/daily/mcp_db_$(date +%Y%m%d_%H%M%S).sql.gz
          restartPolicy: OnFailure
```

**AWS RDS Automated Backups:**
```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier mcp-prod-db \
  --backup-retention-period 30 \
  --preferred-backup-window "02:00-03:00"

# Enable PITR
aws rds modify-db-instance \
  --db-instance-identifier mcp-prod-db \
  --enable-point-in-time-recovery
```

### Backup Verification

**Monthly Test Restore:**
```bash
# 1. Download backup
aws s3 cp s3://mcp-backups/daily/mcp_db_latest.sql.gz /tmp/

# 2. Create test database
psql -h test-postgres -U user -c "CREATE DATABASE mcp_db_test;"

# 3. Restore
gunzip < /tmp/mcp_db_latest.sql.gz | psql -h test-postgres -U user -d mcp_db_test

# 4. Verify data
psql -h test-postgres -U user -d mcp_db_test -c "SELECT COUNT(*) FROM conversations;"
psql -h test-postgres -U user -d mcp_db_test -c "SELECT COUNT(*) FROM conversation_chunks;"

# 5. Cleanup
psql -h test-postgres -U user -c "DROP DATABASE mcp_db_test;"
```

### Disaster Recovery

**Recovery Time Objective (RTO):** 4 hours  
**Recovery Point Objective (RPO):** 24 hours (daily backups)

**DR Procedure:**

**1. Declare Disaster**
- Major data center failure
- Catastrophic data loss
- Multi-region outage

**2. Assess Situation**
```bash
# Check primary region
aws ec2 describe-instance-status --region us-east-1

# Check database
aws rds describe-db-instances --region us-east-1
```

**3. Failover to DR Region**
```bash
# Promote read replica to primary (if available)
aws rds promote-read-replica \
  --db-instance-identifier mcp-prod-db-replica-us-west-2

# Or restore from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mcp-prod-db-recovered \
  --db-snapshot-identifier mcp-prod-db-snapshot-latest \
  --availability-zone us-west-2a
```

**4. Update DNS/Load Balancer**
```bash
# Update Route53 to point to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://dns-update.json
```

**5. Verify Services**
```bash
# Check health
curl https://api.mcp.example.com/health

# Test functionality
./scripts/smoke_test.sh
```

**6. Notify Stakeholders**
- Update status page
- Send notification to users
- Communicate recovery timeline

### Point-in-Time Recovery

**Restore to specific time:**
```bash
# AWS RDS PITR
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier mcp-prod-db \
  --target-db-instance-identifier mcp-prod-db-pitr \
  --restore-time "2025-11-07T14:30:00Z"

# Wait for restore
aws rds wait db-instance-available \
  --db-instance-identifier mcp-prod-db-pitr

# Test restored database
psql -h mcp-prod-db-pitr.xxx.rds.amazonaws.com -U user -d mcp_db
```

---

## Scaling and Performance

### Horizontal Scaling

**Scale Application:**

**Kubernetes:**
```bash
# Manual scaling
kubectl scale deployment/mcp-backend --replicas=5

# Auto-scaling
kubectl autoscale deployment/mcp-backend --min=2 --max=10 --cpu-percent=70
```

**ECS:**
```bash
# Update desired count
aws ecs update-service \
  --cluster mcp-prod-cluster \
  --service mcp-backend \
  --desired-count 5
```

### Vertical Scaling

**Increase Resources:**

**Kubernetes:**
```yaml
# Update deployment
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

**Docker Compose:**
```yaml
services:
  mcp-backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Database Scaling

**Read Replicas:**
```bash
# Create read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier mcp-prod-db-replica-1 \
  --source-db-instance-identifier mcp-prod-db \
  --availability-zone us-east-1b
```

**Connection Pooling:**
```python
# Use PgBouncer for connection pooling
# docker-compose.yml
pgbouncer:
  image: pgbouncer/pgbouncer
  environment:
    - DATABASES=mcp_db=host=postgres port=5432 dbname=mcp_db
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
    - DEFAULT_POOL_SIZE=20
```

### Caching

**Redis for Embedding Cache:**
```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data

mcp-backend:
  environment:
    - REDIS_URL=redis://redis:6379/0
    - ENABLE_EMBEDDING_CACHE=true
```

```python
# app/adapters/outbound/embeddings/cached_embedding_service.py
class CachedEmbeddingService:
    def __init__(self, embedding_service, redis_client):
        self.embedding_service = embedding_service
        self.redis = redis_client
    
    async def generate_embedding(self, text: str) -> Embedding:
        # Check cache
        cache_key = f"embedding:{hash(text)}"
        cached = self.redis.get(cache_key)
        if cached:
            return Embedding.from_json(cached)
        
        # Generate and cache
        embedding = await self.embedding_service.generate_embedding(text)
        self.redis.setex(cache_key, 86400, embedding.to_json())  # 24h TTL
        return embedding
```

---

## Maintenance Procedures

### Database Maintenance

**Vacuum and Analyze:**
```bash
# Weekly maintenance
psql -h postgres -U user -d mcp_db -c "VACUUM ANALYZE conversations;"
psql -h postgres -U user -d mcp_db -c "VACUUM ANALYZE conversation_chunks;"
```

**Reindex:**
```bash
# Monthly reindex
psql -h postgres -U user -d mcp_db -c "REINDEX INDEX idx_chunk_embedding;"
```

**Update Statistics:**
```bash
# Update table statistics
psql -h postgres -U user -d mcp_db -c "ANALYZE conversations;"
psql -h postgres -U user -d mcp_db -c "ANALYZE conversation_chunks;"
```

### Certificate Renewal

**TLS Certificates:**
```bash
# Using cert-manager (Kubernetes)
kubectl get certificates -n mcp-prod

# Manual renewal (Let's Encrypt)
certbot renew --nginx

# Update secret
kubectl create secret tls mcp-tls \
  --cert=/etc/letsencrypt/live/api.mcp.example.com/fullchain.pem \
  --key=/etc/letsencrypt/live/api.mcp.example.com/privkey.pem \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Dependency Updates

**Monthly Security Updates:**
```bash
# Update Python dependencies
pip-audit  # Check for vulnerabilities
pip install --upgrade -r requirements.txt

# Rebuild and test
docker-compose build
pytest tests/

# Deploy to staging first
kubectl apply -f k8s/staging/
```

### Log Rotation

**Docker:**
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "10"
  }
}
```

**Systemd (Linux):**
```bash
# /etc/logrotate.d/mcp-backend
/var/log/mcp-backend/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 mcp mcp
    postrotate
        systemctl reload mcp-backend
    endscript
}
```

---

## Additional Resources

- [Monitoring Dashboard](https://grafana.example.com/dashboard/mcp-backend)
- [Alert Manager](https://alertmanager.example.com)
- [Incident Tracking](https://pagerduty.com)
- [Status Page](https://status.mcp.example.com)
- [Runbook Repository](https://github.com/example/mcp-runbooks)

---

**Document Status**: Complete  
**Last Updated**: November 7, 2025  
**Maintained By**: Product Owner Agent & DevOps Team
