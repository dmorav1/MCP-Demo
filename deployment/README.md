# MCP Demo Production Deployment

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2025-11-13

## Overview

This directory contains comprehensive production deployment architecture, infrastructure as code, and operational documentation for the MCP RAG Demo project.

## Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Terraform v1.6+
- kubectl v1.28+
- AWS CLI v2
- Docker

### Deploy to Production

```bash
# 1. Clone repository
git clone https://github.com/org/mcp-demo
cd mcp-demo/deployment

# 2. Configure AWS credentials
aws configure

# 3. Initialize Terraform
cd terraform
terraform init

# 4. Plan infrastructure
terraform plan -var-file=environments/prod.tfvars

# 5. Apply infrastructure
terraform apply -var-file=environments/prod.tfvars

# 6. Deploy application
cd ../kubernetes
kubectl apply -k overlays/prod/

# 7. Verify deployment
kubectl get pods -n mcp-demo
kubectl get svc -n mcp-demo
```

## Directory Structure

```
deployment/
├── README.md                          # This file
├── docs/                             # Comprehensive documentation
│   ├── DEPLOYMENT_ARCHITECTURE.md    # Overall architecture design
│   ├── SECURITY_ARCHITECTURE.md      # Security controls and policies
│   ├── MONITORING_ALERTING.md        # Observability strategy
│   ├── COST_OPTIMIZATION.md          # Cost management strategies
│   ├── ROLLOUT_STRATEGY.md           # Deployment procedures
│   ├── CONFIGURATION_MANAGEMENT.md   # Config and secrets management
│   └── DATABASE_STRATEGY.md          # Database setup and operations
├── terraform/                        # Infrastructure as Code
│   ├── main.tf                       # Main Terraform configuration
│   ├── variables.tf                  # Variable definitions
│   ├── outputs.tf                    # Output definitions
│   ├── modules/                      # Reusable Terraform modules
│   │   ├── vpc/                      # VPC networking
│   │   ├── eks/                      # EKS cluster
│   │   ├── rds/                      # PostgreSQL database
│   │   ├── elasticache/              # Redis cache
│   │   ├── s3/                       # S3 buckets
│   │   ├── secrets/                  # Secrets Manager
│   │   └── monitoring/               # CloudWatch, alerts
│   └── environments/                 # Environment-specific configs
│       ├── dev.tfvars
│       ├── staging.tfvars
│       └── prod.tfvars
├── kubernetes/                       # Kubernetes manifests
│   ├── base/                         # Base manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   ├── pdb.yaml
│   │   └── configmap.yaml
│   └── overlays/                     # Environment-specific overlays
│       ├── dev/
│       ├── staging/
│       └── prod/
├── scripts/                          # Operational scripts
│   ├── backup-database.sh
│   ├── restore-database.sh
│   ├── rotate-secrets.sh
│   ├── dr-test.sh
│   └── smoke-tests.sh
└── configs/                          # Configuration files
    ├── prometheus/
    ├── grafana/
    └── istio/
```

## Documentation Index

### Architecture & Design

1. **[Deployment Architecture](docs/DEPLOYMENT_ARCHITECTURE.md)**
   - Multi-environment strategy (dev, staging, prod)
   - Container orchestration with Amazon EKS
   - Scaling strategies (horizontal and vertical)
   - High availability setup (99.95% SLA)
   - Disaster recovery procedures (RTO < 1hr, RPO < 15min)

2. **[Security Architecture](docs/SECURITY_ARCHITECTURE.md)**
   - Network security (VPC, security groups, network policies)
   - SSL/TLS certificate management
   - Authentication and authorization strategy
   - API rate limiting and DDoS protection with AWS WAF
   - Secrets management with AWS Secrets Manager
   - Compliance and audit logging

3. **[Database Strategy](docs/DATABASE_STRATEGY.md)**
   - Amazon RDS PostgreSQL with pgvector
   - Multi-AZ deployment for high availability
   - Read replicas for scaling
   - Backup and restore procedures
   - Database migration strategy with Alembic
   - Performance tuning and monitoring

### Operations

4. **[Monitoring & Alerting](docs/MONITORING_ALERTING.md)**
   - Prometheus + Grafana stack
   - Jaeger for distributed tracing
   - Alerting rules and severity levels
   - SLO/SLI definitions (99.95% availability, p95 < 500ms)
   - On-call rotation and escalation
   - Incident response procedures

5. **[Rollout Strategy](docs/ROLLOUT_STRATEGY.md)**
   - Blue-green deployment
   - Canary releases with Istio/Flagger
   - Rolling updates
   - Rollback procedures
   - CI/CD pipeline with GitHub Actions + ArgoCD
   - Gradual migration from legacy systems

6. **[Configuration Management](docs/CONFIGURATION_MANAGEMENT.md)**
   - Environment-specific configurations
   - Secret management with AWS Secrets Manager
   - Feature flags with LaunchDarkly
   - Configuration validation
   - Kustomize overlays

7. **[Cost Optimization](docs/COST_OPTIMIZATION.md)**
   - Cost analysis and budgeting
   - Reserved instances and savings plans
   - Spot instances for non-critical workloads
   - Auto-scaling optimization
   - Cost monitoring and anomaly detection
   - Expected savings: 30-40%

## Technology Stack

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Cloud Provider** | AWS | Infrastructure hosting |
| **IaC** | Terraform | Infrastructure provisioning |
| **Orchestration** | Amazon EKS (Kubernetes 1.28+) | Container orchestration |
| **Service Mesh** | Istio | Traffic management, security, observability |
| **Container Registry** | Amazon ECR | Docker image storage |
| **CI/CD** | GitHub Actions + ArgoCD | Continuous deployment |

### Data Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Database** | Amazon RDS PostgreSQL 15 | Primary data store |
| **Vector Extension** | pgvector | Embedding storage and search |
| **Cache** | Amazon ElastiCache (Redis) | Response caching |
| **Object Storage** | Amazon S3 | Backups, logs, archives |

### Observability

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Metrics** | Prometheus | Time-series metrics |
| **Visualization** | Grafana | Dashboards |
| **Tracing** | Jaeger + OpenTelemetry | Distributed tracing |
| **Logging** | Loki / CloudWatch | Log aggregation |
| **Alerting** | Alertmanager + PagerDuty | Alert management |

### Security

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **WAF** | AWS WAF | DDoS protection, rate limiting |
| **Secrets** | AWS Secrets Manager | Secret storage and rotation |
| **TLS** | AWS Certificate Manager | SSL/TLS certificates |
| **Network** | VPC, Security Groups | Network isolation |
| **IAM** | AWS IAM | Access control |

## Deployment Environments

### Development

- **Infrastructure**: Docker Compose (local)
- **Purpose**: Local development and testing
- **Data**: Synthetic/test data
- **Cost**: $0/month

### Staging

- **Infrastructure**: EKS (scaled down)
  - 2× t3.large nodes
  - RDS db.t3.medium (single-AZ)
  - ElastiCache cache.t3.micro
- **Purpose**: Integration testing, QA
- **Data**: Anonymized production data
- **Cost**: ~$500-900/month

### Production

- **Infrastructure**: EKS (full scale)
  - 3-10× m5.xlarge nodes
  - RDS db.r5.large (Multi-AZ)
  - ElastiCache cache.r5.large (cluster)
- **Purpose**: Live service
- **SLA**: 99.95% availability
- **Cost**: ~$1,700-2,900/month

## Key Metrics & SLAs

### Service Level Objectives

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Availability** | 99.95% | 4.38 hours downtime/year |
| **Latency (p95)** | < 500ms | API response time |
| **Latency (p99)** | < 1s | API response time |
| **Error Rate** | < 0.1% | Failed requests |
| **RTO** | < 1 hour | Recovery time |
| **RPO** | < 15 minutes | Data loss window |

### Capacity

| Metric | Initial | Target Year 1 |
|--------|---------|---------------|
| **Concurrent Users** | 10,000 | 100,000 |
| **Requests/Second** | 1,000 | 10,000 |
| **Database Size** | 100 GB | 1 TB |
| **Vector Embeddings** | 1M | 10M |

## Getting Started

### 1. Infrastructure Setup

```bash
# Navigate to Terraform directory
cd terraform

# Copy example environment file
cp environments/prod.tfvars.example environments/prod.tfvars

# Edit with your values
vi environments/prod.tfvars

# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan -var-file=environments/prod.tfvars

# Apply infrastructure
terraform apply -var-file=environments/prod.tfvars
```

### 2. Configure Secrets

```bash
# Create database secret
aws secretsmanager create-secret \
  --name /mcp-demo/prod/database/url \
  --secret-string "postgresql://user:pass@host:5432/db"

# Create API keys
aws secretsmanager create-secret \
  --name /mcp-demo/prod/api-keys/openai \
  --secret-string "sk-..."

# Create JWT secret
aws secretsmanager create-secret \
  --name /mcp-demo/prod/jwt-secret \
  --secret-string "$(openssl rand -base64 32)"
```

### 3. Deploy Application

```bash
# Configure kubectl
aws eks update-kubeconfig --name mcp-demo-prod --region us-east-1

# Deploy using Kustomize
kubectl apply -k kubernetes/overlays/prod/

# Verify deployment
kubectl get pods -n mcp-demo
kubectl get svc -n mcp-demo

# Check logs
kubectl logs -f deployment/mcp-backend -n mcp-demo
```

### 4. Setup Monitoring

```bash
# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace observability \
  --create-namespace

# Install Jaeger
helm install jaeger jaegertracing/jaeger \
  --namespace observability

# Install Istio
istioctl install --set profile=production -y

# Enable Istio injection
kubectl label namespace mcp-demo istio-injection=enabled
```

### 5. Run Smoke Tests

```bash
# Execute smoke tests
./scripts/smoke-tests.sh https://api.mcp-demo.example.com

# Expected output:
# ✓ Health check passed
# ✓ Search endpoint working
# ✓ RAG endpoint working
# All tests passed!
```

## Operational Procedures

### Daily Operations

- Monitor dashboards (Grafana)
- Review alerts (no action needed if green)
- Check application logs for errors
- Verify backup completion

### Weekly Operations

- Review cost dashboard
- Analyze slow query logs
- Review security scan results
- Update dependencies if needed

### Monthly Operations

- DR test (restore from backup)
- Review and optimize resources
- Security audit
- Capacity planning review

### Quarterly Operations

- Major version upgrades
- Architecture review
- Cost optimization review
- Disaster recovery drill

## Runbooks

Operational runbooks are located in `docs/runbooks/`:

- `01-high-latency.md` - Investigate high API latency
- `02-high-error-rate.md` - Handle error rate spikes
- `03-database-issues.md` - Database troubleshooting
- `04-pod-crash-loop.md` - Fix crashing pods
- `05-disk-space-low.md` - Manage disk space
- `06-cache-issues.md` - Redis troubleshooting
- `07-security-incident.md` - Security incident response

## Support & Contacts

### Team Contacts

- **Platform Team**: platform@example.com
- **Security Team**: security@example.com
- **On-Call Engineer**: Via PagerDuty

### Escalation

1. **L1**: On-call engineer (< 5 min response)
2. **L2**: Senior engineer (15 min response)
3. **L3**: Engineering manager (30 min response)
4. **L4**: CTO (critical incidents only)

### External Support

- **AWS Support**: Enterprise plan (< 15 min response for critical)
- **Third-party Tools**: See vendor documentation

## Contributing

### Making Changes

1. Create feature branch
2. Make changes
3. Test in development
4. Deploy to staging
5. Get approval
6. Deploy to production

### Infrastructure Changes

All infrastructure changes must go through Terraform:

```bash
# Make changes to .tf files
vi terraform/modules/eks/main.tf

# Plan changes
terraform plan -var-file=environments/prod.tfvars

# Get approval from team

# Apply changes
terraform apply -var-file=environments/prod.tfvars
```

### Documentation Updates

Keep documentation up to date:
- Update README when adding new components
- Update runbooks with new procedures
- Update architecture diagrams for significant changes

## License

Proprietary - Internal Use Only

## Changelog

### v1.0.0 (2025-11-13)
- Initial production deployment architecture
- Complete documentation set
- Terraform modules for AWS infrastructure
- Kubernetes manifests for application deployment
- Monitoring and alerting setup
- Security architecture implementation

---

**For detailed information on each component, see the documentation in the `docs/` directory.**

**Questions?** Contact the platform team at platform@example.com
