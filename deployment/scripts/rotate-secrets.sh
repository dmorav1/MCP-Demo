#!/bin/bash
# rotate-secrets.sh - Rotate secrets in AWS Secrets Manager

set -e

SECRET_NAME="${1}"
if [ -z "$SECRET_NAME" ]; then
    echo "Usage: $0 <secret-name>"
    echo "Example: $0 /mcp-demo/prod/database/password"
    exit 1
fi

echo "Rotating secret: $SECRET_NAME"

# Generate new strong password
NEW_SECRET=$(openssl rand -base64 32)

# Get current version
CURRENT_VERSION=$(aws secretsmanager describe-secret \
  --secret-id "$SECRET_NAME" \
  --query 'VersionIdsToStages' \
  --output json)

echo "Current version: $CURRENT_VERSION"

# Update secret with new value
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_NAME" \
  --secret-string "$NEW_SECRET"

# Verify the secret was updated successfully
RETRIEVED_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --query 'SecretString' \
  --output text)

if [ "$RETRIEVED_SECRET" != "$NEW_SECRET" ]; then
    echo "❌ Secret verification failed: retrieved value does not match new value"
    exit 2
fi
echo "✅ Secret rotated successfully"
echo ""
echo "Next steps:"
echo "1. Wait 5-10 minutes for External Secrets Operator to sync"
echo "2. Verify pods are picking up new secret:"
echo "   kubectl rollout restart deployment/mcp-backend -n mcp-demo"
echo "3. Monitor application logs for any authentication errors"
echo "4. If issues occur, you can rollback using previous version"
