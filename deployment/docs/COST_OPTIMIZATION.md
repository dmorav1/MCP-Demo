# COST OPTIMIZATION

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-13

## Overview

This document provides comprehensive guidance for COST OPTIMIZATION in the MCP Demo production deployment.


## Cost Analysis

### Current Infrastructure Costs (Estimated)

**Production Environment** (Monthly):

| Component | Resource | Quantity | Unit Cost | Monthly Cost |
|-----------|----------|----------|-----------|--------------|
| **EKS** | Control Plane | 1 | $73 | $73 |
| **EC2** | m5.xlarge nodes | 3-10 | $0.192/hr | $414-$1,382 |
| **RDS** | db.r5.large Multi-AZ | 1 | $0.48/hr | $346 |
| **ElastiCache** | cache.r5.large | 3 nodes | $0.252/hr | $544 |
| **ALB** | Application Load Balancer | 1 | $22.50 + LCU | $30-$50 |
| **NAT Gateway** | 3 AZs | 3 | $32.40/mo | $97 |
| **S3** | Backups/Logs | - | $0.023/GB | $50-$100 |
| **CloudWatch** | Logs/Metrics | - | Variable | $50-$100 |
| **Data Transfer** | Outbound | - | $0.09/GB | $100-$200 |
| **Total** | - | - | - | **$1,704-$2,892** |

**Staging Environment** (30% of production): **$500-$900/month**  
**Development** (local): **$0/month**

### Cost Optimization Strategies

#### 1. Right-Sizing Resources

**EC2 Instances**:
- Start with t3.large for dev/staging (burst capacity)
- Use Compute Optimizer recommendations
- Review CPU/Memory utilization weekly
- Consider Graviton2 instances (ARM) for 20% cost savings

**Database**:
- Start smaller: db.t3.large → upgrade to db.r5.large if needed
- Monitor IOPS usage
- Use Aurora Serverless v2 for variable workloads

**Example Savings**: 30-40% on compute costs

#### 2. Reserved Instances & Savings Plans

**Commitment Strategy**:
- 1-year Compute Savings Plan: 17% discount
- 3-year Compute Savings Plan: 42% discount
- Target: 70% of baseline capacity on reservations

**ROI Calculation**:
```
Baseline: 3 m5.xlarge × $0.192/hr × 730 hrs = $421/mo
1-year savings: $421 × 17% = $71/mo = $856/year
3-year savings: $421 × 42% = $177/mo = $2,124/year
```

**Recommendation**: Start with 1-year plans, move to 3-year after 6 months

#### 3. Spot Instances

**Use Cases**:
- Non-critical workloads
- Batch processing
- Development/test environments

**Implementation**:
```yaml
# EKS Node Group with Spot
nodeGroups:
  - name: spot-workers
    instancesDistribution:
      instanceTypes: ["m5.large", "m5.xlarge", "m5a.large"]
      onDemandBaseCapacity: 1
      onDemandPercentageAboveBaseCapacity: 0
      spotAllocationStrategy: capacity-optimized
```

**Expected Savings**: 50-70% on compute costs for spot-eligible workloads

#### 4. Auto-Scaling Optimization

**Aggressive Scale-Down**:
```yaml
scaleDown:
  stabilizationWindowSeconds: 180  # Reduced from 300
  policies:
    - type: Percent
      value: 25  # Increased from 10%
      periodSeconds: 60
```

**Schedule-Based Scaling** (non-prod environments):
```bash
# Scale down dev/staging during off-hours
kubectl scale deployment mcp-backend --replicas=1 -n staging
# Automate with CronJob
```

**Savings**: 40-60% on non-prod environments

#### 5. Data Transfer Optimization

**Strategies**:
- Use VPC endpoints for AWS services (avoid NAT Gateway charges)
- Enable S3 Transfer Acceleration only when needed
- Use CloudFront for static assets (cheaper egress)
- Compress responses (gzip)

**VPC Endpoint Configuration**:
```terraform
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.s3"
  route_table_ids = aws_route_table.private[*].id
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.us-east-1.ecr.api"
  vpc_endpoint_type   = "Interface"
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
}
```

**Savings**: $50-$100/month on data transfer

#### 6. Storage Optimization

**S3 Lifecycle Policies**:
```json
{
  "Rules": [
    {
      "Id": "TransitionOldBackups",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

**EBS Optimization**:
- Use gp3 instead of gp2 (20% cheaper)
- Delete orphaned volumes
- Take snapshots, delete old volumes

**Savings**: 30-50% on storage costs

#### 7. Database Optimization

**Strategies**:
- Use read replicas for read-heavy workloads
- Enable query caching
- Optimize indexes
- Archive old data to S3

**RDS Cost Optimization**:
- Consider Aurora Serverless v2 (pay per ACU)
- Stop non-prod databases during off-hours
- Use cross-region replicas only if needed

**Example**:
```bash
# Stop staging database nightly
aws rds stop-db-instance --db-instance-identifier mcp-demo-staging

# Start in morning
aws rds start-db-instance --db-instance-identifier mcp-demo-staging
```

**Savings**: 60-70% on non-prod database costs

#### 8. Monitoring Cost Management

**CloudWatch Optimization**:
- Reduce log retention (30 days vs 90 days)
- Filter logs before ingestion
- Use metric filters sparingly
- Consider Prometheus + Loki (self-hosted)

**Cost Comparison**:
```
CloudWatch Logs: $0.50/GB ingested + $0.03/GB stored
Loki (self-hosted): EC2 costs only (~$100/mo)
Savings: 50-70% for high log volumes
```

### Cost Monitoring

#### AWS Cost Explorer

**Budget Alerts**:
```json
{
  "BudgetName": "mcp-demo-monthly",
  "BudgetLimit": {
    "Amount": "3000",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["Project$mcp-demo"]
  },
  "NotificationsWithSubscribers": [
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]
}
```

#### Cost Allocation Tags

**Required Tags**:
```
Project: mcp-demo
Environment: prod/staging/dev
Team: platform
CostCenter: engineering
ManagedBy: terraform
```

#### Cost Dashboards

**Grafana Dashboard Metrics**:
- Daily cost by service
- Cost per request
- Cost trend (week-over-week)
- Cost anomalies

**Prometheus Query Example**:
```promql
# Cost per request
aws_billing_estimated_charges / 
rate(http_requests_total[1d])
```

### Cost Optimization Roadmap

**Month 1-2** (Quick Wins):
- [ ] Right-size EC2 instances
- [ ] Enable S3 lifecycle policies
- [ ] Stop non-prod resources off-hours
- [ ] Delete unused resources
- **Target Savings**: 20%

**Month 3-4** (Medium Term):
- [ ] Purchase 1-year Savings Plans
- [ ] Implement spot instances for dev/staging
- [ ] Add VPC endpoints
- [ ] Optimize database tier
- **Target Savings**: 30%

**Month 5-6** (Long Term):
- [ ] Move to 3-year Savings Plans
- [ ] Implement multi-region for disaster recovery (evaluate cost)
- [ ] Optimize data transfer patterns
- [ ] Consider Graviton instances
- **Target Savings**: 40%

### Cost vs Performance Trade-offs

| Optimization | Cost Savings | Performance Impact | Recommendation |
|--------------|--------------|-------------------|----------------|
| Smaller instances | High | Moderate | Start small, scale up |
| Spot instances | Very High | Low (with handling) | Use for non-critical |
| Reduce NAT Gateways | Medium | None | Use VPC endpoints |
| Lower RDS tier | High | High | Monitor carefully |
| Reduce retention | Low | None | Archive to S3 |
| Self-hosted monitoring | Medium | Medium | Consider at scale |

### Cost Anomaly Detection

**Automated Alerts**:
```yaml
# CloudWatch Alarm for cost spikes
AnomalyDetection:
  - ServiceName: Amazon EC2
    Threshold: 150%  # Alert if 50% above normal
  - ServiceName: Amazon RDS
    Threshold: 150%
  - ServiceName: Data Transfer
    Threshold: 200%  # More variance expected
```

### Cost Reporting

**Weekly Report**:
- Total spend vs budget
- Top 5 cost drivers
- Week-over-week change
- Optimization opportunities

**Monthly Review**:
- Cost trends
- Savings achieved
- Optimization backlog
- Budget forecast

**Stakeholders**:
- Engineering team: Weekly Slack summary
- Finance: Monthly detailed report
- Executive: Quarterly business review

---

**Document Version**: 1.0  
**Author**: Architect Agent  
**Last Updated**: 2025-11-13
