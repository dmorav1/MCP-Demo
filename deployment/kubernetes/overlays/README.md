# Kubernetes Environment Overlays

Environment-specific configurations using Kustomize overlays for dev, staging, and production.

## Quick Start

Deploy to each environment:

```bash
# Development
kubectl apply -k deployment/kubernetes/overlays/dev/

# Staging
kubectl apply -k deployment/kubernetes/overlays/staging/

# Production (after configuring secrets)
kubectl apply -k deployment/kubernetes/overlays/production/
```

## Environment Configurations

### Development
- 1 replica, minimal resources
- Debug logging
- Local secrets (literals)

### Staging
- 2 replicas, medium resources
- Info logging
- External secret management

### Production
- 3-10 replicas (HPA)
- High resources, warning logging
- External secrets, network policies, PDB

## Secret Management

**Development**: Use literal secrets in kustomization.yaml
**Staging/Production**: Use AWS Secrets Manager or HashiCorp Vault

Example with AWS Secrets Manager:
```bash
kubectl create secret generic db-credentials -n production \
  --from-literal=password=$(aws secretsmanager get-secret-value --secret-id mcp-demo/db --query SecretString --output text)
```

## Validation

```bash
# Validate configuration
kubectl kustomize deployment/kubernetes/overlays/production/ | kubectl apply --dry-run=client -f -
```

See full documentation in deployment/docs/CICD_PIPELINE.md
