# Infrastructure Configuration Recommendations

## Overview

This document provides comprehensive configuration recommendations for the MCP Demo infrastructure in different environments (development, staging, production).

## Environment-Specific Configurations

### Development Environment

#### Purpose
- Local development and testing
- Fast iteration cycles
- Easy debugging
- Minimal resource usage

#### Configuration

**Logging** (`.env`):
```env
LOG_LEVEL=DEBUG
USE_JSON_LOGS=false
LOG_FILE=logs/mcp-backend-dev.log
ENABLE_CONSOLE_TRACING=true
```

**Caching**:
```env
CACHE_ENABLED=true
CACHE_BACKEND=memory
CACHE_MAX_SIZE=1000
CACHE_DEFAULT_TTL=300  # 5 minutes (shorter for development)
```

**Observability**:
```env
# No external exporters in development
JAEGER_HOST=
OTLP_ENDPOINT=
SENTRY_DSN=

# Optionally enable console tracing for debugging
ENABLE_CONSOLE_TRACING=true
```

**Database**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/mcp_dev
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

#### Docker Compose (development)
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=DEBUG
      - CACHE_BACKEND=memory
      - DATABASE_URL=postgresql://user:password@db:5432/mcp_dev
    volumes:
      - ./app:/app/app  # Mount for hot reload
      - ./logs:/app/logs
    command: uvicorn app.main:app --reload --host 0.0.0.0
  
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mcp_dev
    volumes:
      - dev_db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  dev_db_data:
```

---

### Staging Environment

#### Purpose
- Pre-production testing
- Performance validation
- Integration testing
- Similar to production but isolated

#### Configuration

**Logging** (`.env`):
```env
LOG_LEVEL=INFO
USE_JSON_LOGS=true
LOG_FILE=/var/log/mcp-backend/app.log
ENABLE_CONSOLE_TRACING=false
```

**Caching**:
```env
CACHE_ENABLED=true
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://redis:6379/0
CACHE_MAX_SIZE=10000
CACHE_DEFAULT_TTL=1800  # 30 minutes
```

**Observability**:
```env
# Tracing
JAEGER_HOST=jaeger
JAEGER_PORT=6831

# Error tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

**Database**:
```env
DATABASE_URL=postgresql://user:password@db-staging:5432/mcp_staging
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

#### Docker Compose (staging)
```yaml
version: '3.8'

services:
  app:
    image: mcp-backend:staging
    replicas: 2
    environment:
      - LOG_LEVEL=INFO
      - CACHE_BACKEND=redis
      - JAEGER_HOST=jaeger
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
  
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
  
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: mcp_staging
    volumes:
      - db_data:/var/lib/postgresql/data
  
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'
  
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
  
  jaeger:
    image: jaegertracing/all-in-one:latest
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
    ports:
      - "16686:16686"  # UI
      - "6831:6831/udp"  # Agent

volumes:
  redis_data:
  db_data:
  prometheus_data:
  grafana_data:
```

---

### Production Environment

#### Purpose
- Live user traffic
- Maximum performance and reliability
- Comprehensive monitoring
- High availability

#### Configuration

**Logging** (`.env`):
```env
LOG_LEVEL=INFO
USE_JSON_LOGS=true
LOG_FILE=/var/log/mcp-backend/app.log
ENABLE_CONSOLE_TRACING=false
```

**Caching**:
```env
CACHE_ENABLED=true
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://redis-cluster.prod.internal:6379/0
CACHE_MAX_SIZE=100000
CACHE_DEFAULT_TTL=3600  # 1 hour

# Optional: Separate TTLs for different cache types
CACHE_EMBEDDING_TTL=7200  # 2 hours
CACHE_SEARCH_TTL=3600     # 1 hour
CACHE_RAG_TTL=1800        # 30 minutes
```

**Observability**:
```env
# Logging
LOG_LEVEL=INFO

# Tracing (use OTLP for production)
OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=mcp-backend
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.01  # 1% sampling

# Error tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.01  # 1% sampling
SENTRY_PROFILES_SAMPLE_RATE=0.01
```

**Database**:
```env
DATABASE_URL=postgresql://user:password@db-primary.prod.internal:5432/mcp_production
DATABASE_REPLICA_URL=postgresql://user:password@db-replica.prod.internal:5432/mcp_production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600  # Recycle connections every hour
DB_POOL_PRE_PING=true  # Verify connections before use
```

**Performance Tuning**:
```env
# Worker processes
WORKERS=4  # Number of Uvicorn workers
WORKER_CONNECTIONS=1000

# Timeouts
REQUEST_TIMEOUT=30
KEEPALIVE_TIMEOUT=5

# Rate limiting (if using)
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

#### Kubernetes Deployment (production)

**Deployment YAML**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-backend
  namespace: production
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcp-backend
  template:
    metadata:
      labels:
        app: mcp-backend
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: mcp-backend
        image: mcp-backend:1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: CACHE_BACKEND
          value: "redis"
        - name: CACHE_REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: SENTRY_DSN
          valueFrom:
            secretKeyRef:
              name: sentry-credentials
              key: dsn
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-backend
  namespace: production
spec:
  selector:
    app: mcp-backend
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-backend-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-backend
  minReplicas: 4
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 25
        periodSeconds: 60
```

---

## Monitoring Configuration

### Prometheus Configuration

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    environment: 'prod'

scrape_configs:
  - job_name: 'mcp-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets:
          - 'mcp-backend:8000'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+)(?::\d+)?'
        replacement: '${1}'

  - job_name: 'redis'
    static_configs:
      - targets:
          - 'redis-exporter:9121'

  - job_name: 'postgres'
    static_configs:
      - targets:
          - 'postgres-exporter:9187'

# Alert rules
rule_files:
  - '/etc/prometheus/alerts/*.yml'

# Alertmanager
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'
```

### Alert Rules

**alerts/mcp-backend.yml**:
```yaml
groups:
  - name: mcp_backend_alerts
    interval: 30s
    rules:
      # Critical alerts
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
      
      - alert: ServiceDown
        expr: up{job="mcp-backend"} == 0
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "MCP Backend service is down"
          description: "Instance {{ $labels.instance }} is down"
      
      - alert: DatabaseConnectionPoolExhausted
        expr: (db_connections_in_use / db_connections_max) > 0.9
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "Connection pool usage is {{ $value | humanizePercentage }}"
      
      # Warning alerts
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0
        for: 10m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High request latency"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"
      
      - alert: LowCacheHitRate
        expr: |
          rate(cache_hits_total[10m]) 
          / (rate(cache_hits_total[10m]) + rate(cache_misses_total[10m])) 
          < 0.3
        for: 15m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 30%)"
      
      - alert: HighMemoryUsage
        expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.85
        for: 10m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
      
      # Info alerts
      - alert: HighLLMTokenUsage
        expr: rate(llm_tokens_total[1h]) > 100000
        for: 1h
        labels:
          severity: info
          team: backend
        annotations:
          summary: "High LLM token usage"
          description: "Token usage rate: {{ $value }} tokens/hour"
```

### Grafana Dashboards

The repository includes a comprehensive dashboard at `monitoring/grafana/mcp-backend-dashboard.json` with:

1. **Overview Panel**: Request rate, latency, error rate
2. **Performance Panel**: Latency percentiles (P50, P95, P99)
3. **Cache Panel**: Hit rate, miss rate, eviction rate
4. **Database Panel**: Query latency, connection pool usage
5. **LLM Panel**: Token usage, request rate, cost estimation
6. **System Panel**: CPU, memory, disk usage
7. **Business Metrics**: Conversations ingested, searches performed

**Import Instructions**:
1. Open Grafana UI
2. Navigate to Dashboards → Import
3. Upload `monitoring/grafana/mcp-backend-dashboard.json`
4. Select Prometheus data source
5. Click Import

---

## Security Considerations

### Secrets Management

**Development**: Use `.env` file (not committed)
```env
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
SENTRY_DSN=https://...
```

**Staging/Production**: Use secrets management
- Kubernetes Secrets
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

**Example (Kubernetes Secret)**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-backend-secrets
type: Opaque
stringData:
  database-url: postgresql://user:password@db:5432/mcp_prod
  openai-api-key: sk-...
  sentry-dsn: https://...
```

### Network Security

**Development**: Open access
```yaml
# docker-compose.yml
ports:
  - "8000:8000"
  - "5432:5432"
```

**Production**: Restricted access
- Use internal networking
- Firewall rules
- VPC/Security groups
- mTLS for service-to-service communication

### Log Sanitization

Ensure sensitive data is not logged:

**Bad Example**:
```python
logger.info(f"User login: {username}, password: {password}")
```

**Good Example**:
```python
logger.info(f"User login: {username}", extra={"event": "user_login"})
```

---

## Performance Tuning

### Cache Tuning

**Monitor these metrics**:
- Cache hit rate (target: >60%)
- Cache memory usage
- Eviction rate
- Average TTL before expiration

**Tune these settings**:
```env
# Increase cache size if eviction rate is high
CACHE_MAX_SIZE=100000  # Adjust based on memory

# Increase TTL if hit rate is low
CACHE_DEFAULT_TTL=7200  # 2 hours

# Use different TTLs for different data types
CACHE_EMBEDDING_TTL=14400  # 4 hours (stable data)
CACHE_SEARCH_TTL=3600      # 1 hour (moderate churn)
CACHE_RAG_TTL=1800         # 30 minutes (high churn)
```

### Database Tuning

**Connection Pool**:
```env
# Base formula: pool_size = (available_cpu_cores * 2) + disk_spindles
# For 4 cores, 1 SSD: (4 * 2) + 1 = 9, round to 10
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20  # 2x pool size for burst traffic
```

**PostgreSQL Settings** (`postgresql.conf`):
```
# Memory
shared_buffers = 4GB  # 25% of RAM
effective_cache_size = 12GB  # 75% of RAM
work_mem = 64MB  # Per operation
maintenance_work_mem = 512MB

# Connections
max_connections = 200

# Query optimization
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### Worker Configuration

**Calculate Workers**:
```
workers = (2 * cpu_cores) + 1

Examples:
- 2 cores: 5 workers
- 4 cores: 9 workers
- 8 cores: 17 workers
```

**Set in Uvicorn**:
```bash
uvicorn app.main:app \
  --workers 9 \
  --host 0.0.0.0 \
  --port 8000 \
  --loop uvloop \
  --http httptools
```

---

## Backup and Recovery

### Database Backups

**Development**: Manual backups
```bash
pg_dump -h localhost -U user mcp_dev > backup.sql
```

**Production**: Automated backups
```bash
# Daily full backup
0 2 * * * pg_dump -h db-primary -U user mcp_prod | gzip > /backups/mcp_prod_$(date +\%Y\%m\%d).sql.gz

# Hourly incremental using WAL archiving
archive_command = 'cp %p /backups/wal_archive/%f'
```

### Cache Persistence

**Redis RDB**: Periodic snapshots
```
# redis.conf
save 900 1      # After 900 sec if at least 1 key changed
save 300 10     # After 300 sec if at least 10 keys changed
save 60 10000   # After 60 sec if at least 10000 keys changed
```

**Redis AOF**: Append-only file
```
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
```

---

## Troubleshooting Guide

### High Latency

**Check**:
```bash
# 1. Cache hit rate
curl http://localhost:8000/metrics | grep cache_hits

# 2. Database slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# 3. Resource usage
docker stats
kubectl top pods
```

**Solutions**:
- Increase cache size/TTL
- Add database indexes
- Scale horizontally (more replicas)

### Memory Issues

**Check**:
```bash
# Memory usage
docker stats
kubectl top pods

# Cache memory
redis-cli INFO MEMORY
```

**Solutions**:
- Reduce cache size
- Enable Redis LRU eviction
- Increase pod memory limits
- Check for memory leaks

### Cache Not Working

**Check**:
```bash
# Redis connection
redis-cli PING

# Cache metrics
curl http://localhost:8000/metrics | grep cache
```

**Solutions**:
- Verify CACHE_ENABLED=true
- Check Redis connectivity
- Verify cache keys are being set
- Check cache TTL settings

---

## Migration Path

### From No Cache to Cache

1. **Enable in-memory cache first** (low risk)
```env
CACHE_ENABLED=true
CACHE_BACKEND=memory
```

2. **Monitor hit rates and performance**

3. **Deploy Redis** when ready
```env
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://redis:6379/0
```

4. **Gradually increase cache size**

### From Minimal to Full Observability

1. **Start with logging**
```env
LOG_LEVEL=INFO
USE_JSON_LOGS=true
```

2. **Add metrics** (Prometheus)
```env
# Metrics enabled by default at /metrics
```

3. **Add tracing** (low sampling)
```env
JAEGER_HOST=jaeger
OTEL_TRACES_SAMPLER_ARG=0.01  # 1%
```

4. **Increase sampling** as comfortable

5. **Add error tracking**
```env
SENTRY_DSN=https://...
```

---

## Conclusion

Follow these recommendations for a robust, scalable, and observable MCP Demo infrastructure:

- ✅ Start with development config for local work
- ✅ Use staging config for pre-production testing
- ✅ Deploy production config with high availability
- ✅ Monitor key metrics and set up alerts
- ✅ Tune performance based on actual usage
- ✅ Regular backups and disaster recovery planning

For questions or issues, refer to:
- [Infrastructure Test Validation Report](./INFRASTRUCTURE_TEST_VALIDATION.md)
- [Performance Comparison Report](./INFRASTRUCTURE_PERFORMANCE_REPORT.md)
- [Implementation Documentation](./OBSERVABILITY_IMPLEMENTATION.md)

---

*Document Version: 1.0*  
*Last Updated: 2025-11-13*
