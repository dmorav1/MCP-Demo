# Deployment Runbook

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-14

## Quick Reference

### Emergency Contacts

- **DevOps Lead**: devops-lead@example.com
- **Backend Team**: backend-team@example.com
- **Database Admin**: dba@example.com
- **On-Call**: oncall@example.com

### Key URLs

- **Production**: https://mcp-demo.example.com
- **Staging**: https://staging.mcp-demo.example.com
- **Development**: https://dev.mcp-demo.example.com
- **GitHub Actions**: https://github.com/org/mcp-demo/actions
- **Monitoring**: https://grafana.mcp-demo.example.com

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Rollback Procedures](#rollback-procedures)
4. [Troubleshooting](#troubleshooting)
5. [Post-Deployment Verification](#post-deployment-verification)

---

## Pre-Deployment Checklist

### Before Any Deployment

- [ ] All CI checks passing on main branch
- [ ] Code review approved by at least 2 reviewers
- [ ] Release notes prepared
- [ ] Database migrations reviewed (if any)
- [ ] Backup verified and accessible
- [ ] Rollback plan documented
- [ ] Team notified of deployment window
- [ ] On-call engineer identified

### Environment-Specific

#### Development
- [ ] No additional requirements

#### Staging
- [ ] Staging environment health verified
- [ ] Test data refreshed (if needed)
- [ ] Integration test suite passing

#### Production
- [ ] Change window approved
- [ ] Customer notification sent (if downtime expected)
- [ ] Backup completed and verified
- [ ] Monitoring dashboards accessible
- [ ] Incident response team on standby
- [ ] Communication channel open (Slack)

---

## Deployment Procedures

### 1. Development Deployment

**Trigger**: Automatic on push to main

**No manual steps required** - deployment happens automatically after CI passes.

**Verification**:
```bash
# Check deployment status
curl https://dev.mcp-demo.example.com/health

# Check version
curl https://dev.mcp-demo.example.com/version
```

### 2. Staging Deployment

**Duration**: ~15 minutes  
**Downtime**: None (rolling update)

#### Step 1: Trigger Deployment

1. Go to GitHub Actions
2. Select "CD Pipeline - Deploy" workflow
3. Click "Run workflow"
4. Select:
   - Branch: `main`
   - Environment: `staging`
   - Skip tests: `false`
5. Click "Run workflow"

#### Step 2: Monitor Deployment

```bash
# Watch deployment progress
kubectl get deployment mcp-backend -n staging -w

# Check pod status
kubectl get pods -n staging -l app=mcp-backend

# View logs
kubectl logs -f deployment/mcp-backend -n staging
```

#### Step 3: Run Integration Tests

```bash
# Run automated integration tests
npm run test:integration -- --env staging

# Or manually test key features
curl -X POST https://staging.mcp-demo.example.com/ingest \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "test-123", "content": "test message"}'

curl -X POST https://staging.mcp-demo.example.com/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

#### Step 4: Verify Success

- [ ] All pods running and ready
- [ ] Health checks passing
- [ ] Integration tests passed
- [ ] No error spikes in logs
- [ ] Response times normal

### 3. Production Deployment

**Duration**: ~30 minutes  
**Downtime**: None (blue-green deployment)  
**Best Time**: During low-traffic hours (e.g., 2-4 AM EST)

#### Step 1: Pre-Deployment

```bash
# Create production backup
./deployment/scripts/backup.sh -e production

# Verify backup
aws s3 ls s3://mcp-demo-backups/production/

# Check current health
curl https://mcp-demo.example.com/health

# Note current metrics (for comparison)
# - Request rate
# - Error rate
# - Latency (p50, p95, p99)
```

#### Step 2: Communication

```bash
# Post in team Slack channel
"🚀 Starting production deployment
Version: v1.2.3
Expected duration: 30 minutes
Monitoring: [grafana-link]"
```

#### Step 3: Database Migration (if needed)

```bash
# Connect to production cluster
kubectl config use-context production

# Run migration script
./deployment/scripts/migrations/run-migrations.sh
NAMESPACE=production \
DEPLOYMENT_NAME=mcp-backend \
BACKUP_ENABLED=true \
./deployment/scripts/migrations/run-migrations.sh

# Verify migration
kubectl exec -n production deployment/mcp-backend -- \
  python -m alembic current
```

#### Step 4: Trigger Deployment

1. Go to GitHub Actions
2. Select "CD Pipeline - Deploy" workflow
3. Click "Run workflow"
4. Select:
   - Branch: `main`
   - Environment: `production`
   - Skip tests: `false`
5. Click "Run workflow"
6. **Wait for approval** from deployment approver

#### Step 5: Approve Deployment

Deployment approvers review:
- [ ] All CI checks passed
- [ ] Staging validation successful
- [ ] Database migration completed (if applicable)
- [ ] Team ready to monitor
- [ ] Rollback plan ready

**Action**: Click "Approve" in GitHub Actions

#### Step 6: Monitor Blue-Green Cutover

```bash
# Watch blue (old) deployment
kubectl get deployment mcp-backend-blue -n production -w

# Watch green (new) deployment
kubectl get deployment mcp-backend-green -n production -w

# After green is healthy, traffic switches
# Monitor logs for errors
kubectl logs -f deployment/mcp-backend-green -n production

# Check metrics in Grafana
# - Error rate should remain stable
# - Latency should be similar
# - No spike in 5xx errors
```

#### Step 7: Smoke Tests

```bash
# Health check
curl https://mcp-demo.example.com/health

# Version check
curl https://mcp-demo.example.com/version

# Test key endpoints
curl -X POST https://mcp-demo.example.com/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"query": "test", "limit": 5}'

# Test RAG endpoint
curl -X POST https://mcp-demo.example.com/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"question": "What is MCP?", "conversation_id": "test-123"}'
```

#### Step 8: Monitor for 30 Minutes

Watch these metrics in Grafana:
- **Error Rate**: Should be < 0.1%
- **Response Time**: p95 < 500ms
- **Request Rate**: Should match expected traffic
- **Database Connections**: Should be stable
- **Memory Usage**: Should be within normal range
- **CPU Usage**: Should be < 70%

Check logs for:
- [ ] No ERROR level logs
- [ ] No database connection errors
- [ ] No timeout errors
- [ ] No unexpected exceptions

#### Step 9: Post-Deployment

```bash
# Post success message
"✅ Production deployment complete
Version: v1.2.3
Status: All systems normal
Rollback available for next 24h"

# Update release notes
# Tag release in GitHub
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# Schedule cleanup of old blue deployment (after 24h)
kubectl scale deployment mcp-backend-blue -n production --replicas=0
```

---

## Rollback Procedures

### When to Rollback

Immediate rollback if:
- Error rate > 1%
- Response time > 2x normal
- Critical functionality broken
- Database issues
- Security vulnerability discovered

### Quick Rollback

```bash
# Switch traffic back to blue (old) deployment
kubectl patch service mcp-backend -n production \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# Verify rollback
curl https://mcp-demo.example.com/health
curl https://mcp-demo.example.com/version

# Or use rollback script
./deployment/scripts/rollback.sh \
  -n production \
  -d mcp-backend
```

### Database Rollback

```bash
# Restore from pre-migration backup
BACKUP_FILE="backup-mcp_db-20251114-020000.sql"

kubectl exec -n production deployment/mcp-backend -- \
  pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c /tmp/$BACKUP_FILE

# Or use Alembic downgrade
kubectl exec -n production deployment/mcp-backend -- \
  python -m alembic downgrade -1
```

### Post-Rollback

1. Verify system health
2. Notify team of rollback
3. Create incident post-mortem
4. Fix issues before next deployment attempt

---

## Troubleshooting

### Issue: Pods Not Starting

**Symptoms**: Pods in CrashLoopBackOff or Pending state

**Check**:
```bash
# Get pod status
kubectl get pods -n production -l app=mcp-backend

# Describe pod for events
kubectl describe pod <pod-name> -n production

# Check logs
kubectl logs <pod-name> -n production --previous
```

**Common Causes**:
- Image pull failures → Check image tag and registry access
- Configuration errors → Check ConfigMap and Secrets
- Resource limits → Increase CPU/memory limits
- Database connection → Verify database credentials

### Issue: High Error Rate

**Symptoms**: Error rate spikes after deployment

**Check**:
```bash
# View recent logs
kubectl logs -n production deployment/mcp-backend --tail=100

# Check error distribution
kubectl logs -n production deployment/mcp-backend | grep ERROR

# Query metrics
# Check Grafana dashboard for error patterns
```

**Actions**:
- If > 1% error rate: Consider rollback
- If specific endpoint: Disable endpoint or rollback
- If database related: Check connection pool and queries

### Issue: Slow Response Times

**Symptoms**: Latency increase after deployment

**Check**:
```bash
# Check resource usage
kubectl top pods -n production -l app=mcp-backend

# Check database queries
# Use pg_stat_statements to find slow queries

# Check external dependencies
# Verify OpenAI API, Anthropic API response times
```

**Actions**:
- If CPU high: Scale up replicas
- If memory high: Increase memory limit
- If database slow: Check query performance
- If external API slow: Add timeout or retry logic

### Issue: Database Migration Failed

**Symptoms**: Migration script exits with error

**Check**:
```bash
# View migration logs
kubectl logs <migration-job> -n production

# Check current version
kubectl exec deployment/mcp-backend -n production -- \
  python -m alembic current

# Check database connectivity
kubectl exec deployment/mcp-backend -n production -- \
  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1;"
```

**Actions**:
1. Review migration script for errors
2. Check database permissions
3. Verify backup was created
4. Rollback using backup if needed
5. Fix migration script and retry

---

## Post-Deployment Verification

### Automated Checks

```bash
# Run full smoke test suite
./deployment/scripts/smoke-tests.sh production

# Run integration tests against production
npm run test:integration -- --env production
```

### Manual Verification

#### Backend Health
- [ ] `/health` endpoint returns 200
- [ ] `/metrics` endpoint accessible
- [ ] Database connectivity verified
- [ ] Redis cache responding

#### API Functionality
- [ ] Ingest conversation works
- [ ] Search conversations works
- [ ] RAG question answering works
- [ ] MCP protocol endpoints work

#### Frontend
- [ ] Homepage loads
- [ ] Login/authentication works
- [ ] Chat interface functional
- [ ] Search interface functional

#### Monitoring
- [ ] Grafana dashboards showing data
- [ ] Prometheus metrics being collected
- [ ] Logs appearing in Loki
- [ ] Traces visible in Jaeger
- [ ] Alerts configured and working

### Success Criteria

Deployment is considered successful when:
- ✓ All pods running and ready
- ✓ Health checks passing
- ✓ Error rate < 0.1%
- ✓ Response time p95 < 500ms
- ✓ No ERROR logs
- ✓ Smoke tests passing
- ✓ Monitoring dashboards showing normal metrics
- ✓ No customer complaints for 30 minutes

---

## Appendix

### Useful Commands

```bash
# Check deployment status
kubectl get deployment mcp-backend -n production

# Scale deployment
kubectl scale deployment mcp-backend -n production --replicas=5

# Update image
kubectl set image deployment/mcp-backend mcp-backend=new-image:tag -n production

# View rollout history
kubectl rollout history deployment/mcp-backend -n production

# Pause rollout
kubectl rollout pause deployment/mcp-backend -n production

# Resume rollout
kubectl rollout resume deployment/mcp-backend -n production

# Check service endpoints
kubectl get endpoints mcp-backend -n production

# Port forward for debugging
kubectl port-forward deployment/mcp-backend 8000:8000 -n production
```

### Monitoring Queries

**Prometheus**:
```promql
# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Response time p95
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Pod restarts
sum(rate(kube_pod_container_status_restarts_total{namespace="production"}[15m]))
```

### Decision Matrix

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | > 1% | Immediate rollback |
| Error Rate | 0.5-1% | Monitor closely, prepare rollback |
| Error Rate | < 0.5% | Normal operation |
| Response Time | > 2x baseline | Consider rollback |
| Response Time | > 1.5x baseline | Monitor, check for issues |
| Pod Restarts | > 3 in 5 min | Investigate, consider rollback |
| Database CPU | > 90% | Alert DBA, may need to scale |
| Memory Usage | > 90% | Scale up or rollback |

---

**Document Maintainer**: DevOps Team  
**Last Review**: 2025-11-14  
**Next Review**: 2025-12-14
