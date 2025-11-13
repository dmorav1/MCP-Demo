# Observability Quick Reference

## 🚀 Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 2. Start all services including monitoring
docker-compose up -d

# 3. Access services
# - API: http://localhost:8000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3030 (admin/admin)
# - Jaeger: http://localhost:16686
```

## 📊 Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /health` | Enhanced health check | `curl localhost:8000/health` |
| `GET /metrics` | Prometheus metrics | `curl localhost:8000/metrics` |
| `GET /docs` | API documentation | Open in browser |

## 📈 Key Metrics

### HTTP Metrics
```promql
# Request rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m])
```

### Business Metrics
```promql
# Conversations ingested per hour
rate(conversations_ingested_total[1h])

# Searches per hour
rate(searches_performed_total[1h])

# RAG queries per hour
rate(rag_queries_total[1h])
```

### Database Metrics
```promql
# DB query latency
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Query count by operation
rate(db_queries_total[5m])
```

### Cache Metrics
```promql
# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

## 🔧 Environment Variables

### Logging
```bash
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
USE_JSON_LOGS=true              # Enable JSON logging
LOG_FILE=logs/mcp-backend.log   # Log file path
```

### Tracing
```bash
JAEGER_HOST=localhost           # Jaeger agent host
JAEGER_PORT=6831                # Jaeger agent port
OTLP_ENDPOINT=                  # OTLP endpoint (optional)
ENABLE_CONSOLE_TRACING=false    # Debug tracing
```

### Error Tracking
```bash
SENTRY_DSN=                     # Sentry DSN
SENTRY_ENVIRONMENT=production   # Environment name
SENTRY_TRACES_SAMPLE_RATE=0.1  # Trace sampling (0.0-1.0)
```

### Performance
```bash
SLOW_REQUEST_THRESHOLD=1.0      # Seconds for slow request warning
```

## 🎯 Common Tasks

### View Logs
```bash
# Container logs
docker logs mcp-backend

# File logs
tail -f logs/mcp-backend.log

# JSON logs
tail -f logs/mcp-backend.log | jq '.'
```

### Query Metrics
```bash
# Get all metrics
curl localhost:8000/metrics

# Specific metric
curl localhost:8000/metrics | grep http_requests_total
```

### View Traces
1. Open http://localhost:16686
2. Select service: `mcp-backend`
3. Click "Find Traces"
4. Click on a trace to view details

### Import Grafana Dashboard
1. Open http://localhost:3030
2. Login (admin/admin)
3. Go to Dashboards → Import
4. Upload `monitoring/grafana/mcp-backend-dashboard.json`
5. Select Prometheus data source

## 🚨 Alerts

Default alerts configured in `monitoring/prometheus-alerts.yml`:

- **High Error Rate**: >0.1 errors/sec for 5min
- **Very High Error Rate**: >1.0 errors/sec for 2min (critical)
- **High Latency**: p95 >2s for 5min
- **Slow DB Queries**: p95 >1s for 5min
- **Service Down**: No heartbeat for 1min (critical)
- **Low Cache Hit Rate**: <50% for 10min
- **High LLM Latency**: p95 >30s for 5min
- **High Embedding Latency**: p95 >5s for 5min

## 📊 Dashboard Panels

The Grafana dashboard includes:

1. **Request Rate** - HTTP requests over time
2. **Request Latency (p95)** - 95th percentile latency
3. **Error Rate** - Errors over time
4. **Active Requests** - Requests in progress
5. **DB Query Latency** - Database performance
6. **Embedding Generation Time** - Embedding latency
7. **Cache Hit Rate** - Cache effectiveness
8. **LLM Token Usage** - Token consumption
9. **Business Metrics** - Ingestions, searches, RAG queries

## 🔍 Troubleshooting

### Metrics not showing up
```bash
# Check Prometheus targets
curl localhost:9090/api/v1/targets

# Check metrics endpoint
curl localhost:8000/metrics

# Check container logs
docker logs prometheus
docker logs mcp-backend
```

### Traces not appearing
```bash
# Check Jaeger is running
docker ps | grep jaeger

# Check environment variables
docker exec mcp-backend env | grep JAEGER

# Check application logs
docker logs mcp-backend | grep -i trace
```

### High memory usage
```bash
# Check Prometheus retention
# Edit monitoring/prometheus.yml:
# --storage.tsdb.retention.time=7d

# Restart Prometheus
docker-compose restart prometheus
```

## 🎓 Best Practices

1. **Use structured logging** - Makes parsing easier
2. **Add request IDs** - Track requests across services
3. **Sample traces** - Don't trace everything in production
4. **Set alert thresholds** - Based on your SLOs
5. **Monitor business metrics** - Not just technical metrics
6. **Regular dashboard reviews** - Tune and improve
7. **Test alerts** - Ensure they fire correctly

## 📚 Resources

- **Full Setup Guide**: `docs/MONITORING_SETUP.md`
- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **Jaeger Docs**: https://www.jaegertracing.io/docs/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/

## 🆘 Support

For issues:
1. Check this reference
2. Check `docs/MONITORING_SETUP.md`
3. Review container logs
4. Check GitHub issues

---

**Quick Links**:
- Health: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3030
- Jaeger: http://localhost:16686
- API Docs: http://localhost:8000/docs
