# Production Deployment Architecture

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-13

## Executive Summary

This deployment architecture provides enterprise-grade production infrastructure for the MCP RAG Demo project with 99.95% availability SLA.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Amazon EKS (Kubernetes 1.28+) |
| Database | RDS PostgreSQL + pgvector (Multi-AZ) |
| Cache | ElastiCache Redis (Cluster mode) |
| IaC | Terraform |
| CI/CD | GitHub Actions + ArgoCD |
| Monitoring | Prometheus + Grafana + Jaeger |
| Service Mesh | Istio |

### Target SLAs

- Availability: 99.95% (4.38 hours downtime/year)
- RTO: < 1 hour
- RPO: < 15 minutes
- Latency (p95): < 500ms
