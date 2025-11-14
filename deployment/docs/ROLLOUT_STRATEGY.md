# ROLLOUT STRATEGY

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-01

## Overview

This document provides comprehensive guidance for ROLLOUT STRATEGY in the MCP Demo production deployment.


## Deployment Strategies

### 1. Blue-Green Deployment

**Overview**: Maintain two identical production environments (blue and green), switch traffic instantly.

**Advantages**:
- Zero-downtime deployment
- Instant rollback capability
- Full testing in production environment before cutover
- Clear separation between old and new versions

**Implementation**:

```yaml
# Blue deployment (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-backend-blue
  labels:
    app: mcp-backend
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-backend
      version: blue
  template:
    metadata:
      labels:
        app: mcp-backend
        version: blue
    spec:
      containers:
        - name: mcp-backend
          image: mcp-backend:v1.0.0
---
# Green deployment (new version)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-backend-green
  labels:
    app: mcp-backend
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-backend
      version: green
  template:
    metadata:
      labels:
        app: mcp-backend
        version: green
    spec:
      containers:
        - name: mcp-backend
          image: mcp-backend:v1.1.0
---
# Service selector (controls traffic routing)
apiVersion: v1
kind: Service
metadata:
  name: mcp-backend
spec:
  selector:
    app: mcp-backend
    version: blue  # Switch to "green" to cutover
  ports:
    - port: 8000
      targetPort: 8000
```

**Deployment Process**:

1. **Deploy Green** (5 minutes)
   ```bash
   # Deploy new version alongside blue
   kubectl apply -f deployment-green.yaml
   
   # Wait for green to be ready
   kubectl wait --for=condition=ready pod -l version=green --timeout=300s
   ```

2. **Smoke Test Green** (10 minutes)
   ```bash
   # Port-forward to green service
   kubectl port-forward svc/mcp-backend-green 9000:8000
   
   # Run smoke tests
   curl http://localhost:9000/health
   curl -X POST http://localhost:9000/search -d '{"query":"test"}'
   ```

3. **Switch Traffic** (Instant)
   ```bash
   # Update service selector
   kubectl patch service mcp-backend -p '{"spec":{"selector":{"version":"green"}}}'
   
   # Verify traffic is routed to green
   kubectl get endpoints mcp-backend
   ```

4. **Monitor** (30 minutes)
   ```bash
   # Watch metrics
   - Error rate
   - Latency
   - Traffic distribution
   
   # If issues detected, instant rollback
   kubectl patch service mcp-backend -p '{"spec":{"selector":{"version":"blue"}}}'
   ```

5. **Cleanup Old Version** (Next day)
   ```bash
   # After 24 hours of stable operation
   kubectl delete deployment mcp-backend-blue
   
   # Rename green to blue for next deployment
   kubectl label deployment mcp-backend-green version=blue --overwrite
   kubectl label deployment mcp-backend-green version-
   ```

**Cost**: 2x infrastructure during deployment (1-2 hours)

### 2. Canary Deployment

**Overview**: Gradually roll out changes to a small subset of users before full deployment.

**Advantages**:
- Lower risk than big-bang deployment
- Early detection of issues
- Controlled blast radius
- Real user feedback

**Canary Stages**:
1. 5% traffic → Canary
2. 25% traffic → Canary
3. 50% traffic → Canary
4. 100% traffic → Canary (promote)

**Istio Implementation**:

```yaml
# Virtual Service for traffic splitting
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
            host: mcp-backend
            subset: canary
    - route:
        - destination:
            host: mcp-backend
            subset: stable
          weight: 95
        - destination:
            host: mcp-backend
            subset: canary
          weight: 5
---
# Destination Rule
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: mcp-backend
spec:
  host: mcp-backend
  subsets:
    - name: stable
      labels:
        version: stable
    - name: canary
      labels:
        version: canary
```

**Automated Canary Progression** (Flagger):

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: mcp-backend
  namespace: mcp-demo
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-backend
  service:
    port: 8000
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 5
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
      - name: request-duration
        thresholdRange:
          max: 500
        interval: 1m
  webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://mcp-backend:8000/health"
```

**Manual Canary Process**:

```bash
# Stage 1: Deploy canary (5% traffic)
kubectl apply -f deployment-canary.yaml
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"stable"},"weight":95},{"destination":{"host":"mcp-backend","subset":"canary"},"weight":5}]}]}}'

# Wait 15 minutes, monitor metrics
# If OK, proceed to 25%
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"stable"},"weight":75},{"destination":{"host":"mcp-backend","subset":"canary"},"weight":25}]}]}}'

# Wait 15 minutes, monitor metrics
# If OK, proceed to 50%
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"stable"},"weight":50},{"destination":{"host":"mcp-backend","subset":"canary"},"weight":50}]}]}}'

# Wait 30 minutes, monitor metrics
# If OK, promote to 100%
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"canary"},"weight":100}]}]}}'

# Cleanup
kubectl label deployment mcp-backend-canary version=stable --overwrite
kubectl delete deployment mcp-backend-old
```

**Rollback** (at any stage):
```bash
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"stable"},"weight":100}]}]}}'
kubectl delete deployment mcp-backend-canary
```

### 3. Rolling Update

**Overview**: Gradually replace pods with new version (default Kubernetes strategy).

**Configuration**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-backend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 1 pod above desired count
      maxUnavailable: 0  # Always maintain full capacity
  template:
    # ... pod spec
```

**Process**:
1. Create 1 new pod (total: 4 pods)
2. Wait for readiness
3. Terminate 1 old pod (total: 3 pods)
4. Repeat until all pods updated

**Advantages**:
- Simple, built-in to Kubernetes
- No additional infrastructure
- Gradual rollout

**Disadvantages**:
- Mixed versions running simultaneously
- Slower rollback
- Can't easily test before switching traffic

**Use Case**: Low-risk updates, backward-compatible changes

### 4. Recreate Deployment

**Overview**: Terminate all old pods before creating new ones.

**Configuration**:
```yaml
strategy:
  type: Recreate
```

**Use Case**:
- Database migrations requiring downtime
- Non-backward-compatible changes
- Resource-constrained environments

**Downtime**: Yes (brief, seconds to minutes)

## Rollback Procedures

### Automatic Rollback

**Readiness Probe Failure**:
- Kubernetes won't route traffic to failed pods
- Deployment will pause if maxUnavailable reached
- Manual intervention required to rollback

**Flagger Canary Failure**:
- Automatic rollback if metrics threshold breached
- Alerts sent to on-call engineer

### Manual Rollback

**Kubernetes Rollout Commands**:

```bash
# View deployment history
kubectl rollout history deployment/mcp-backend

# Rollback to previous version
kubectl rollout undo deployment/mcp-backend

# Rollback to specific revision
kubectl rollout undo deployment/mcp-backend --to-revision=3

# Check rollback status
kubectl rollout status deployment/mcp-backend
```

**Blue-Green Rollback**:
```bash
# Instant: switch service selector back to blue
kubectl patch service mcp-backend -p '{"spec":{"selector":{"version":"blue"}}}'
```

**Canary Rollback**:
```bash
# Route all traffic back to stable
kubectl patch virtualservice mcp-backend --type merge -p '{"spec":{"http":[{"route":[{"destination":{"host":"mcp-backend","subset":"stable"},"weight":100}]}]}}'

# Delete canary deployment
kubectl delete deployment mcp-backend-canary
```

### Database Rollback

**Migration Rollback Strategy**:

```python
# migrations/v1_1_0_add_column.py
def upgrade():
    """Add new column"""
    op.add_column('conversations', 
        sa.Column('new_field', sa.String(255), nullable=True))

def downgrade():
    """Rollback: remove column"""
    op.drop_column('conversations', 'new_field')
```

**Process**:
```bash
# Before deploying new version
# 1. Run forward migration
alembic upgrade head

# 2. Deploy application (backward compatible)
kubectl apply -f deployment-v1.1.0.yaml

# If rollback needed:
# 3. Rollback application
kubectl rollout undo deployment/mcp-backend

# 4. Rollback database (if necessary)
alembic downgrade -1
```

**Migration Best Practices**:
- Make migrations backward compatible when possible
- Deploy in phases: Add column → Deploy code → Remove old code
- Never drop columns immediately
- Use feature flags for schema-dependent features

## Gradual Migration from Legacy

### Migration Strategy

**Phase 1: Shadow Mode** (Week 1-2)
- Deploy new architecture alongside legacy
- Mirror 10% of traffic to new system
- No user-visible changes
- Compare results for validation

**Phase 2: Canary Users** (Week 3)
- Route 5% of users to new system
- Monitor error rates and performance
- Gather user feedback

**Phase 3: Incremental Rollout** (Week 4-5)
- 10% → 25% → 50% → 75% → 100%
- Each stage: 2-3 days + monitoring
- Pause/rollback if issues detected

**Phase 4: Legacy Deprecation** (Week 6)
- Route 100% traffic to new system
- Keep legacy running (read-only) for 1 week
- Final data sync
- Decommission legacy

**Phase 5: Cleanup** (Week 7)
- Remove legacy infrastructure
- Archive data
- Update documentation

### Traffic Splitting

**Route 53 Weighted Routing**:
```json
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.mcp-demo.example.com",
        "Type": "A",
        "SetIdentifier": "legacy",
        "Weight": 90,
        "AliasTarget": {
          "HostedZoneId": "Z123",
          "DNSName": "legacy-alb.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.mcp-demo.example.com",
        "Type": "A",
        "SetIdentifier": "new",
        "Weight": 10,
        "AliasTarget": {
          "HostedZoneId": "Z456",
          "DNSName": "new-alb.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}
```

### Data Migration

**Dual-Write Strategy**:

```python
async def create_conversation(conversation: ConversationCreate):
    # Write to both old and new datastores
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(legacy_db.insert(conversation))
        task2 = tg.create_task(new_db.insert(conversation))
    
    # Use new DB as source of truth
    return task2.result()
```

**Data Sync Job**:
```python
# Background job to sync historical data
async def sync_historical_data():
    cursor = None
    while True:
        # Fetch batch from legacy DB
        conversations = await legacy_db.fetch_batch(cursor, limit=1000)
        if not conversations:
            break
        
        # Transform and insert into new DB
        for conv in conversations:
            new_conv = transform_conversation(conv)
            await new_db.upsert(new_conv)
        
        cursor = conversations[-1].id
        await asyncio.sleep(1)  # Rate limiting
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.ref_name }}
        run: |
          docker build -t $ECR_REGISTRY/mcp-backend:$IMAGE_TAG .
          docker push $ECR_REGISTRY/mcp-backend:$IMAGE_TAG
      
      - name: Security scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/mcp-backend:${{ github.ref_name }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
  
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/mcp-backend \
            mcp-backend=$ECR_REGISTRY/mcp-backend:$IMAGE_TAG \
            -n staging
          
          kubectl rollout status deployment/mcp-backend -n staging --timeout=5m
      
      - name: Run smoke tests
        run: |
          ./scripts/smoke-tests.sh https://staging.mcp-demo.example.com
  
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Update ArgoCD application
        run: |
          argocd app set mcp-backend \
            --parameter image.tag=$IMAGE_TAG
          
          argocd app sync mcp-backend --prune
      
      - name: Monitor deployment
        run: |
          # Wait and monitor
          sleep 300
          
          # Check error rate
          ERROR_RATE=$(curl -s http://prometheus:9090/api/v1/query \
            --data-urlencode 'query=rate(http_requests_errors_total[5m])/rate(http_requests_total[5m])' \
            | jq -r '.data.result[0].value[1]')
          
          if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
            echo "High error rate detected: $ERROR_RATE"
            kubectl rollout undo deployment/mcp-backend -n production
            exit 1
          fi
      
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment to production: ${{ github.ref_name }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### ArgoCD GitOps

**Application Manifest**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: mcp-backend
  namespace: argocd
spec:
  project: default
  
  source:
    repoURL: https://github.com/org/mcp-demo
    targetRevision: main
    path: deployment/kubernetes/overlays/prod
    
  destination:
    server: https://kubernetes.default.svc
    namespace: mcp-demo
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  
  healthChecks:
    - kind: Deployment
      name: mcp-backend
```

## Deployment Checklist

Pre-deployment:
- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Security scan passed
- [ ] Database migrations tested
- [ ] Runbook updated
- [ ] Rollback plan documented
- [ ] Stakeholders notified
- [ ] Monitoring dashboards ready

During deployment:
- [ ] Deployment started
- [ ] Health checks passing
- [ ] Metrics monitored (error rate, latency)
- [ ] Logs reviewed
- [ ] User feedback monitored
- [ ] Status page updated

Post-deployment:
- [ ] Smoke tests executed
- [ ] Error rate normal
- [ ] Latency within SLO
- [ ] All features working
- [ ] Documentation updated
- [ ] Post-mortem (if issues occurred)
- [ ] Cleanup old resources

---

**Document Version**: 1.0  
**Author**: Architect Agent  
**Last Updated**: 2025-11-13
