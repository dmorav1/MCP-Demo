# Monitoring and Observability Setup Guide

This guide explains how to set up comprehensive monitoring and observability for the MCP Backend service.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Configuration](#configuration)
4. [Prometheus Setup](#prometheus-setup)
5. [Grafana Setup](#grafana-setup)
6. [Jaeger Tracing](#jaeger-tracing)
7. [Sentry Error Tracking](#sentry-error-tracking)
8. [Monitoring Best Practices](#monitoring-best-practices)

## Overview

The MCP Backend implements comprehensive observability with:

- **Structured JSON Logging** - Contextual logs with request tracking
- **Prometheus Metrics** - Performance and business metrics
- **OpenTelemetry Tracing** - Distributed tracing across services
- **Sentry Error Tracking** - Exception monitoring and alerting
- **Enhanced Health Checks** - Detailed component status

## Features

### Structured Logging

- JSON format for easy parsing and analysis
- Contextual information (request ID, user ID)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Performance metrics in logs
- Automatic request/response logging

### Prometheus Metrics

#### HTTP Metrics
- `http_requests_total` - Total requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Active requests gauge

#### Error Metrics
- `errors_total` - Total errors by type and endpoint

#### Database Metrics
- `db_queries_total` - Total database queries by operation
- `db_query_duration_seconds` - Query latency histogram

#### Embedding Metrics
- `embedding_generations_total` - Total embedding generations
- `embedding_generation_duration_seconds` - Generation latency

#### Cache Metrics
- `cache_hits_total` - Cache hits by type
- `cache_misses_total` - Cache misses by type

#### LLM Metrics (RAG)
- `llm_requests_total` - LLM requests by provider and model
- `llm_tokens_total` - Token usage by type (prompt/completion)
- `llm_request_duration_seconds` - LLM request latency

#### Business Metrics
- `conversations_ingested_total` - Conversations ingested
- `searches_performed_total` - Searches performed
- `rag_queries_total` - RAG queries

### Distributed Tracing

- Request tracing across all layers (API → Use Case → Adapter)
- Span attributes for debugging
- Integration with Jaeger or any OTLP-compatible backend
- Automatic FastAPI and SQLAlchemy instrumentation

### Error Tracking

- Automatic exception capture
- Full stack traces with context
- User tracking (when available)
- Breadcrumbs for debugging

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
USE_JSON_LOGS=true               # Enable JSON logging
LOG_FILE=logs/mcp-backend.log    # Log file path

# Tracing
JAEGER_HOST=localhost            # Jaeger agent host
JAEGER_PORT=6831                 # Jaeger agent port
OTLP_ENDPOINT=                   # OTLP endpoint (optional)
ENABLE_CONSOLE_TRACING=false     # Debug tracing to console

# Error Tracking
SENTRY_DSN=                      # Sentry DSN
SENTRY_ENVIRONMENT=development   # Environment name
SENTRY_TRACES_SAMPLE_RATE=0.1   # Trace sampling rate
SENTRY_PROFILES_SAMPLE_RATE=0.1 # Profile sampling rate

# Performance
SLOW_REQUEST_THRESHOLD=1.0       # Seconds for slow request warning
```

### Docker Compose Integration

Add to `docker-compose.yml`:

```yaml
services:
  mcp-backend:
    environment:
      - LOG_LEVEL=INFO
      - USE_JSON_LOGS=true
      - JAEGER_HOST=jaeger
      - SENTRY_DSN=${SENTRY_DSN}
      - SENTRY_ENVIRONMENT=production

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus-alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - mcp-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - mcp-network

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "6831:6831/udp"  # Jaeger agent
      - "14268:14268"  # Jaeger collector
    networks:
      - mcp-network

volumes:
  prometheus_data:
  grafana_data:
```

## Prometheus Setup

### 1. Create Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - 'alerts.yml'

scrape_configs:
  - job_name: 'mcp-backend'
    static_configs:
      - targets: ['mcp-backend:8000']
    metrics_path: '/metrics'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### 2. Start Prometheus

```bash
docker-compose up -d prometheus
```

### 3. Access Prometheus UI

Open http://localhost:9090

### 4. Query Examples

```promql
# Request rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m])

# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

## Grafana Setup

### 1. Start Grafana

```bash
docker-compose up -d grafana
```

### 2. Access Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. Change password when prompted

### 3. Add Prometheus Data Source

1. Go to Configuration → Data Sources
2. Click "Add data source"
3. Select "Prometheus"
4. Set URL to `http://prometheus:9090`
5. Click "Save & Test"

### 4. Import Dashboard

1. Go to Dashboards → Import
2. Upload `monitoring/grafana/mcp-backend-dashboard.json`
3. Select Prometheus data source
4. Click "Import"

### 5. Create Custom Dashboards

Use the provided template as a starting point and customize:

- Add panels for specific endpoints
- Create alerting rules
- Set up notification channels
- Add business-specific metrics

## Jaeger Tracing

### 1. Start Jaeger

```bash
docker-compose up -d jaeger
```

### 2. Access Jaeger UI

Open http://localhost:16686

### 3. View Traces

1. Select service: `mcp-backend`
2. Select operation or use search
3. Click "Find Traces"
4. Click on a trace to view details

### 4. Trace Analysis

Look for:
- **Long spans** - Performance bottlenecks
- **Error spans** - Failed operations
- **Span attributes** - Debugging context
- **Service dependencies** - Architecture visualization

## Sentry Error Tracking

### 1. Create Sentry Project

1. Sign up at https://sentry.io
2. Create a new project (Python/FastAPI)
3. Copy the DSN

### 2. Configure Sentry

Add to `.env`:

```bash
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 3. View Errors

1. Go to Sentry dashboard
2. View error reports with:
   - Full stack traces
   - Request context
   - User information
   - Breadcrumbs
   - Environment details

### 4. Set Up Alerts

1. Go to Alerts → Create Alert
2. Configure conditions (e.g., error rate threshold)
3. Add notification channels (email, Slack, PagerDuty)
4. Save alert rule

## Monitoring Best Practices

### 1. The Four Golden Signals

Monitor these key metrics:

- **Latency** - Request duration
- **Traffic** - Request rate
- **Errors** - Error rate
- **Saturation** - Resource utilization

### 2. Alert Fatigue Prevention

- Set appropriate thresholds
- Use multi-level severity (info, warning, critical)
- Implement alert grouping
- Add actionable descriptions
- Regular alert review and tuning

### 3. Dashboard Organization

- **Overview Dashboard** - High-level metrics
- **Service Dashboards** - Detailed per-service metrics
- **Business Dashboards** - Business KPIs
- **Debug Dashboards** - Troubleshooting views

### 4. Log Management

- Use structured logging for easy parsing
- Include correlation IDs for request tracking
- Set appropriate log levels per environment
- Implement log rotation and archiving
- Use log aggregation tools (ELK, Loki)

### 5. Trace Sampling

- Use sampling to reduce overhead
- Sample 100% of errors
- Increase sampling for important endpoints
- Adjust based on traffic volume

### 6. Performance Impact

Observability features are designed to have minimal impact:

- Metrics: ~1-2ms per request
- Tracing: ~2-5ms per request (with sampling)
- Logging: ~0.5-1ms per log entry
- Total overhead: <1% in production

### 7. Security Considerations

- Don't log sensitive data (passwords, tokens, PII)
- Sanitize logs before external export
- Use secure connections for metrics export
- Implement access controls for dashboards
- Rotate credentials regularly

## Troubleshooting

### Metrics Not Showing Up

1. Check Prometheus is scraping: http://localhost:9090/targets
2. Verify metrics endpoint: http://localhost:8000/metrics
3. Check network connectivity between services
4. Review Prometheus logs: `docker logs prometheus`

### Traces Not Appearing in Jaeger

1. Verify Jaeger is running: `docker ps | grep jaeger`
2. Check JAEGER_HOST environment variable
3. Review application logs for tracing errors
4. Verify network connectivity to Jaeger agent

### Sentry Errors Not Captured

1. Verify SENTRY_DSN is set correctly
2. Check Sentry project is active
3. Review application logs for Sentry errors
4. Test with manual error: `sentry_sdk.capture_exception(Exception("Test"))`

### High Memory Usage

1. Reduce trace sampling rate
2. Adjust Prometheus retention period
3. Implement log rotation
4. Review metric cardinality (label combinations)

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Sentry Documentation](https://docs.sentry.io/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## Support

For issues or questions:
1. Check application logs
2. Review this documentation
3. Check service-specific documentation
4. Open an issue in the repository
