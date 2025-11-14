#!/bin/bash
# restore-database.sh - Restore database from snapshot or point-in-time

set -e

RESTORE_TYPE="${1:-snapshot}"  # snapshot or pitr
INSTANCE_ID="${DB_INSTANCE_ID}"
NEW_INSTANCE="${NEW_INSTANCE_ID:-mcp-demo-restored-$(date +%Y%m%d-%H%M%S)}"

if [ -z "$INSTANCE_ID" ]; then
    echo "ERROR: DB_INSTANCE_ID environment variable must be set to the source instance ID."
    echo "Usage: DB_INSTANCE_ID=<source-instance-id> $0 {snapshot|pitr} <args>"
    exit 1
fi
if [ "$RESTORE_TYPE" = "snapshot" ]; then
    SNAPSHOT_ID="${2}"
    if [ -z "$SNAPSHOT_ID" ]; then
        echo "Usage: $0 snapshot <snapshot-id>"
        echo "Available snapshots:"
        aws rds describe-db-snapshots \
          --db-instance-identifier "$INSTANCE_ID" \
          --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]' \
          --output table
        exit 1
    fi
    
    echo "Restoring from snapshot: $SNAPSHOT_ID"
    aws rds restore-db-instance-from-db-snapshot \
      --db-instance-identifier "$NEW_INSTANCE" \
      --db-snapshot-identifier "$SNAPSHOT_ID" \
      --db-instance-class db.r5.large \
      --vpc-security-group-ids "${SECURITY_GROUP_ID}" \
      --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
      --multi-az \
      --publicly-accessible false

elif [ "$RESTORE_TYPE" = "pitr" ]; then
    TARGET_TIME="${2}"
    if [ -z "$TARGET_TIME" ]; then
        echo "Usage: $0 pitr <target-time>"
        echo "Example: $0 pitr 2025-11-13T10:30:00Z"
        exit 1
    fi
    
    echo "Restoring to point in time: $TARGET_TIME"
    aws rds restore-db-instance-to-point-in-time \
      --source-db-instance-identifier "$INSTANCE_ID" \
      --target-db-instance-identifier "$NEW_INSTANCE" \
      --restore-time "$TARGET_TIME" \
      --vpc-security-group-ids "${SECURITY_GROUP_ID}" \
      --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
      --multi-az \
      --publicly-accessible false
else
    echo "Invalid restore type: $RESTORE_TYPE"
    echo "Usage: $0 {snapshot|pitr} <args>"
    exit 1
fi

echo "Waiting for restore to complete..."
aws rds wait db-instance-available --db-instance-identifier "$NEW_INSTANCE"

ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "$NEW_INSTANCE" \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "✅ Restore complete!"
echo "New instance: $NEW_INSTANCE"
echo "Endpoint: $ENDPOINT"
echo ""
echo "Next steps:"
echo "1. Test the restored instance"
echo "2. Update application configuration if needed"
echo "3. Consider promoting to production if replacing failed instance"
