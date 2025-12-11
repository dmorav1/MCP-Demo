# CI/CD Pipeline Status

## Current Status

[![CI Pipeline](https://github.com/dmorav1/MCP-Demo/actions/workflows/ci.yml/badge.svg)](https://github.com/dmorav1/MCP-Demo/actions/workflows/ci.yml)
[![CD Deploy](https://github.com/dmorav1/MCP-Demo/actions/workflows/cd-deploy.yml/badge.svg)](https://github.com/dmorav1/MCP-Demo/actions/workflows/cd-deploy.yml)

## Quick Links

- [View CI Pipeline Runs](https://github.com/dmorav1/MCP-Demo/actions/workflows/ci.yml)
- [View CD Deployments](https://github.com/dmorav1/MCP-Demo/actions/workflows/cd-deploy.yml)
- [Trigger Rollback](https://github.com/dmorav1/MCP-Demo/actions/workflows/rollback.yml)

## Pipeline Health

Last Updated: Check GitHub Actions for real-time status

### Environments

| Environment | Status | Last Deployed | Version |
|-------------|--------|---------------|---------|
| Development | ![Status](https://img.shields.io/badge/status-active-green) | Auto on main | latest |
| Staging | ![Status](https://img.shields.io/badge/status-active-green) | Manual | TBD |
| Production | ![Status](https://img.shields.io/badge/status-active-green) | Manual | TBD |

## Metrics

### Recent Deployments

Check [GitHub Actions](https://github.com/dmorav1/MCP-Demo/actions) for deployment history.

### Test Coverage

Target: 80%+  
Current: Check [Codecov](https://codecov.io) (if configured)

### Security

- CodeQL: Enabled
- Trivy: Enabled
- Vulnerability Threshold: HIGH/CRITICAL blocking

## Documentation

- [CI/CD Pipeline Guide](../deployment/docs/CICD_PIPELINE.md)
- [Deployment Runbook](../deployment/docs/DEPLOYMENT_RUNBOOK.md)
- [Implementation Summary](../CICD_IMPLEMENTATION_SUMMARY.md)

## Support

For pipeline issues:
1. Check [Troubleshooting Guide](../deployment/docs/CICD_PIPELINE.md#troubleshooting)
2. Review workflow logs in GitHub Actions
3. Contact DevOps team

---

**Last Updated**: 2025-11-14
