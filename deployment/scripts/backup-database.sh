#!/bin/bash
# backup-database.sh - Create manual database backup

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="mcp-demo-manual-${TIMESTAMP}"
INSTANCE_ID="${DB_INSTANCE_ID:-mcp-demo-prod}"

echo "Creating database snapshot..."
echo "Instance: $INSTANCE_ID"
echo "Snapshot: $SNAPSHOT_NAME"

aws rds create-db-snapshot \
  --db-instance-identifier "$INSTANCE_ID" \
  --db-snapshot-identifier "$SNAPSHOT_NAME" \
  --tags Key=Type,Value=Manual Key=Date,Value="$TIMESTAMP"

echo "Waiting for snapshot to complete..."
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier "$SNAPSHOT_NAME"

echo "✅ Snapshot created successfully: $SNAPSHOT_NAME"

# Optional: Export to S3
if [ "${EXPORT_TO_S3:-false}" = "true" ]; then
    echo "Exporting snapshot to S3..."
    # Fetch AWS account ID dynamically if not set
    if [ -z "${AWS_ACCOUNT_ID}" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        echo "Fetched AWS Account ID: ${AWS_ACCOUNT_ID}"
    fi
    
    aws rds start-export-task \
      --export-task-identifier "${SNAPSHOT_NAME}-export" \
      --source-arn "arn:aws:rds:${AWS_REGION:-us-east-1}:${AWS_ACCOUNT_ID}:snapshot:${SNAPSHOT_NAME}" \
      --s3-bucket-name "${S3_BACKUP_BUCKET:-mcp-demo-backups}" \
      --s3-prefix "manual-backups/${TIMESTAMP}/" \
      --iam-role-arn "${EXPORT_ROLE_ARN}" \
      --kms-key-id "${KMS_KEY_ID}"
    echo "✅ Export initiated"
fi
