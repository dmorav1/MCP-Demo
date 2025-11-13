# DATABASE STRATEGY

**Project:** MCP RAG Demo  
**Version:** 1.0.0  
**Last Updated:** 2025-11-13

## Overview

This document provides comprehensive guidance for DATABASE STRATEGY in the MCP Demo production deployment.


## Production Database Setup

### Amazon RDS PostgreSQL Configuration

**Instance Specifications**:
```terraform
resource "aws_db_instance" "postgres" {
  identifier     = "mcp-demo-prod"
  engine         = "postgres"
  engine_version = "15.4"
  
  # Instance class
  instance_class = "db.r5.large"  # 2 vCPU, 16 GiB RAM
  
  # Storage
  allocated_storage     = 100  # GB
  max_allocated_storage = 1000  # Auto-scaling limit
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn
  
  # High Availability
  multi_az = true
  
  # Networking
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false
  
  # Database
  db_name  = "mcp_db"
  username = "mcp_admin"
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
  port     = 5432
  
  # Backup
  backup_retention_period = 30
  backup_window          = "03:00-04:00"  # UTC
  maintenance_window     = "sun:04:00-sun:05:00"  # UTC
  skip_final_snapshot    = false
  final_snapshot_identifier = "mcp-demo-final-${timestamp()}"
  
  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = true
  performance_insights_retention_period = 7
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  # Parameters
  parameter_group_name = aws_db_parameter_group.postgres15.name
  
  tags = {
    Environment = "production"
    Application = "mcp-demo"
  }
}

# Parameter Group
resource "aws_db_parameter_group" "postgres15" {
  name   = "mcp-demo-postgres15"
  family = "postgres15"
  
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgvector"
  }
  
  parameter {
    name  = "log_statement"
    value = "ddl"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries > 1s
  }
  
  parameter {
    name  = "max_connections"
    value = "200"
  }
}
```

### pgvector Extension

**Installation**:
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Vector Index Configuration**:
```sql
-- Create HNSW index for fast similarity search
CREATE INDEX conversations_embedding_idx ON conversation_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create IVFFlat index (alternative, lower memory)
CREATE INDEX conversations_embedding_ivfflat_idx ON conversation_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Analyze for optimal query planning
ANALYZE conversation_chunks;
```

**Performance Tuning**:
```sql
-- Adjust work_mem for vector operations
ALTER SYSTEM SET work_mem = '256MB';

-- Increase shared_buffers for better caching
ALTER SYSTEM SET shared_buffers = '4GB';

-- Optimize for vector searches
ALTER SYSTEM SET effective_cache_size = '12GB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Database Authentication Security

**AWS IAM Authentication** (Recommended):

AWS RDS supports IAM database authentication, which provides enhanced security by using short-lived authentication tokens instead of static passwords.

**Benefits**:
- No password storage or management required
- Tokens are valid for 15 minutes only
- Integrates with AWS IAM for access control
- Passwords not exposed in environment variables or process lists
- Automatic credential rotation

**Configuration**:
```terraform
resource "aws_db_instance" "postgres" {
  # ... other configuration ...
  
  # Enable IAM database authentication
  iam_database_authentication_enabled = true
}

# Create IAM policy for database access
resource "aws_iam_policy" "rds_iam_auth" {
  name        = "mcp-demo-rds-iam-auth"
  description = "Allow IAM authentication to RDS"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = [
          "arn:aws:rds-db:us-east-1:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_instance.postgres.resource_id}/mcp_admin"
        ]
      }
    ]
  })
}
```

**Application Usage**:
```python
import boto3
import psycopg2

def get_iam_db_connection():
    """Create database connection using IAM authentication"""
    rds_client = boto3.client('rds', region_name='us-east-1')
    
    # Generate authentication token (valid for 15 minutes)
    token = rds_client.generate_db_auth_token(
        DBHostname='mcp-demo-prod.abc123.us-east-1.rds.amazonaws.com',
        Port=5432,
        DBUsername='mcp_admin',
        Region='us-east-1'
    )
    
    # Connect using the token as password
    conn = psycopg2.connect(
        host='mcp-demo-prod.abc123.us-east-1.rds.amazonaws.com',
        port=5432,
        user='mcp_admin',
        password=token,
        database='mcp_db',
        sslmode='require'
    )
    
    return conn
```

**Shell Script Usage**:
```bash
# Generate authentication token
export PGPASSWORD=$(aws rds generate-db-auth-token \
    --hostname mcp-demo-prod.abc123.us-east-1.rds.amazonaws.com \
    --port 5432 \
    --username mcp_admin \
    --region us-east-1)

# Connect using the token
psql -h mcp-demo-prod.abc123.us-east-1.rds.amazonaws.com \
     -U mcp_admin \
     -d mcp_db

# Clear the token immediately after use
unset PGPASSWORD
```

**Alternative: .pgpass File**:

For environments where IAM authentication is not available, use a `.pgpass` file for secure password storage:

```bash
# Create .pgpass file with restricted permissions
cat > ~/.pgpass << EOF
hostname:5432:database:username:password
EOF

# Set proper permissions (required by PostgreSQL)
chmod 0600 ~/.pgpass

# PostgreSQL will automatically use credentials from .pgpass
psql -h hostname -U username -d database
```

**Security Best Practices**:
1. Always prefer IAM authentication over static passwords
2. Never pass passwords via command-line arguments (visible in process lists)
3. Avoid using `PGPASSWORD` environment variable except for IAM tokens
4. If using `.pgpass`, ensure file permissions are set to 0600
5. Use SSL/TLS for all database connections
6. Rotate credentials regularly (IAM tokens auto-expire in 15 minutes)

### Read Replicas

**Configuration**:
```terraform
resource "aws_db_instance" "read_replica" {
  identifier     = "mcp-demo-prod-replica-1"
  replicate_source_db = aws_db_instance.postgres.identifier
  
  instance_class = "db.r5.large"
  
  # Can be in different AZ for regional disaster recovery
  availability_zone = "us-east-1b"
  
  # Read replicas can have different configurations
  backup_retention_period = 7  # Shorter retention for replicas
  
  # Monitoring
  performance_insights_enabled = true
  monitoring_interval = 60
  
  tags = {
    Environment = "production"
    Application = "mcp-demo"
    Role        = "read-replica"
  }
}
```

**Application Configuration** (Read/Write Split):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Primary database (read-write)
primary_engine = create_engine(
    os.getenv('DATABASE_URL'),
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_pre_ping=True,
)

# Read replica (read-only)
replica_engine = create_engine(
    os.getenv('DATABASE_REPLICA_URL'),
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_pre_ping=True,
)

# Session factories
PrimarySession = sessionmaker(bind=primary_engine)
ReplicaSession = sessionmaker(bind=replica_engine)

# Usage
def write_operation():
    with PrimarySession() as session:
        # Write operation
        session.add(new_conversation)
        session.commit()

def read_operation():
    with ReplicaSession() as session:
        # Read operation
        return session.query(Conversation).all()
```

## Database Migration Strategy

### Migration Tools

**Alembic Configuration**:
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()
```

### Migration Best Practices

**1. Backward Compatible Migrations**:
```python
# Good: Add column with default value (backward compatible)
def upgrade():
    op.add_column('conversations',
        sa.Column('new_field', sa.String(255), nullable=True, server_default=''))

def downgrade():
    op.drop_column('conversations', 'new_field')

# Bad: Drop column immediately (NOT backward compatible)
# This breaks old code that references the column
def upgrade():
    op.drop_column('conversations', 'old_field')  # DON'T DO THIS
```

**2. Multi-Phase Migrations**:
```python
# Phase 1: Add new column (keep old column)
def upgrade_phase1():
    op.add_column('conversations',
        sa.Column('user_id_new', sa.Integer(), nullable=True))

# Phase 2: Backfill data
def upgrade_phase2():
    op.execute("""
        UPDATE conversations 
        SET user_id_new = user_id
        WHERE user_id_new IS NULL
    """)

# Phase 3: Make column non-nullable
def upgrade_phase3():
    op.alter_column('conversations', 'user_id_new', nullable=False)

# Phase 4: Drop old column (after code deployment)
def upgrade_phase4():
    op.drop_column('conversations', 'user_id')
    op.alter_column('conversations', 'user_id_new', new_column_name='user_id')
```

**3. Large Data Migrations**:
```python
def upgrade():
    # Use batches for large tables
    connection = op.get_bind()
    
    batch_size = 10000
    offset = 0
    
    while True:
        result = connection.execute(f"""
            UPDATE conversations
            SET processed = TRUE
            WHERE id IN (
                SELECT id FROM conversations
                WHERE processed IS NULL
                LIMIT {batch_size}
            )
        """)
        
        if result.rowcount == 0:
            break
        
        offset += batch_size
        print(f"Processed {offset} rows")
```

### Migration Process

**Pre-Deployment**:
```bash
# 1. Generate migration
alembic revision --autogenerate -m "Add new_field to conversations"

# 2. Review migration file
cat alembic/versions/abc123_add_new_field.py

# 3. Test on dev database
alembic upgrade head

# 4. Test rollback
alembic downgrade -1
alembic upgrade head

# 5. Commit migration files
git add alembic/versions/abc123_add_new_field.py
git commit -m "Add migration for new_field"
```

**Production Deployment**:
```bash
# 1. Backup database
aws rds create-db-snapshot \
  --db-instance-identifier mcp-demo-prod \
  --db-snapshot-identifier pre-migration-$(date +%Y%m%d-%H%M%S)

# 2. Run migration (in maintenance window if needed)
kubectl exec -it $(kubectl get pod -l app=mcp-backend -o name | head -1) -- \
  python -m alembic upgrade head

# 3. Verify migration
kubectl exec -it $(kubectl get pod -l app=mcp-backend -o name | head -1) -- \
  python -c "from app.models import *; print('Migration successful')"

# 4. Deploy application (if needed)
kubectl set image deployment/mcp-backend mcp-backend=mcp-backend:v1.1.0

# 5. Monitor for errors
kubectl logs -f deployment/mcp-backend
```

## Backup and Restore Procedures

### Automated Backups

**RDS Automated Backups**:
- Daily full snapshots (03:00-04:00 UTC)
- Transaction logs for point-in-time recovery
- Retention: 30 days
- Cross-region replication to us-west-2

**Manual Backup Script**:
```bash
#!/bin/bash
# backup-database.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="mcp-demo-manual-${TIMESTAMP}"

echo "Creating manual snapshot: ${SNAPSHOT_NAME}"

aws rds create-db-snapshot \
  --db-instance-identifier mcp-demo-prod \
  --db-snapshot-identifier "${SNAPSHOT_NAME}" \
  --tags Key=Type,Value=Manual Key=Date,Value="${TIMESTAMP}"

echo "Waiting for snapshot to complete..."
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier "${SNAPSHOT_NAME}"

echo "Snapshot created successfully"

# Optional: Export to S3 for long-term archival
aws rds start-export-task \
  --export-task-identifier "${SNAPSHOT_NAME}-export" \
  --source-arn "arn:aws:rds:us-east-1:ACCOUNT_ID:snapshot:${SNAPSHOT_NAME}" \
  --s3-bucket-name mcp-demo-backups \
  --s3-prefix "manual-backups/${TIMESTAMP}/" \
  --iam-role-arn "arn:aws:iam::ACCOUNT_ID:role/rds-export-role" \
  --kms-key-id "arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID"

echo "Export initiated"
```

### Restore Procedures

**Point-in-Time Recovery**:
```bash
#!/bin/bash
# restore-pitr.sh

TARGET_TIME="2025-11-13T10:30:00Z"
NEW_INSTANCE="mcp-demo-restored-$(date +%Y%m%d-%H%M%S)"

echo "Restoring to point in time: ${TARGET_TIME}"

aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier mcp-demo-prod \
  --target-db-instance-identifier "${NEW_INSTANCE}" \
  --restore-time "${TARGET_TIME}" \
  --db-subnet-group-name mcp-demo-subnet-group \
  --vpc-security-group-ids sg-xxxxx \
  --no-publicly-accessible \
  --multi-az

echo "Waiting for restore to complete..."
aws rds wait db-instance-available \
  --db-instance-identifier "${NEW_INSTANCE}"

# Get endpoint
ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "${NEW_INSTANCE}" \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "Restore complete. New endpoint: ${ENDPOINT}"
echo "Update application configuration to use new endpoint"
```

**Snapshot Restore**:
```bash
#!/bin/bash
# restore-snapshot.sh

SNAPSHOT_ID="mcp-demo-manual-20251113_120000"
NEW_INSTANCE="mcp-demo-restored-from-snapshot"

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier "${NEW_INSTANCE}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --db-instance-class db.r5.large \
  --db-subnet-group-name mcp-demo-subnet-group \
  --vpc-security-group-ids sg-xxxxx \
  --multi-az \
  --publicly-accessible false

echo "Restore initiated"
```

### Disaster Recovery Testing

**Monthly DR Test**:
```bash
#!/bin/bash
# dr-test.sh

set -e

echo "=== Disaster Recovery Test ==="
echo "Date: $(date)"

# 1. Restore latest snapshot to test instance
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier mcp-demo-prod \
  --query 'DBSnapshots | sort_by(@, &SnapshotCreateTime)[-1].DBSnapshotIdentifier' \
  --output text)

echo "Restoring from snapshot: ${LATEST_SNAPSHOT}"

TEST_INSTANCE="mcp-demo-dr-test-$(date +%Y%m%d)"

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier "${TEST_INSTANCE}" \
  --db-snapshot-identifier "${LATEST_SNAPSHOT}" \
  --db-instance-class db.t3.medium \
  --db-subnet-group-name mcp-demo-subnet-group

# 2. Wait for availability
aws rds wait db-instance-available --db-instance-identifier "${TEST_INSTANCE}"

# 3. Test connectivity and data integrity
TEST_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "${TEST_INSTANCE}" \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Use AWS IAM authentication for secure database access
export PGPASSWORD=$(aws rds generate-db-auth-token \
    --hostname "${TEST_ENDPOINT}" \
    --port 5432 \
    --username mcp_admin \
    --region us-east-1)

psql -h "${TEST_ENDPOINT}" -U mcp_admin -d mcp_db -c "
SELECT 'DR Test Successful' AS status,
       count(*) AS conversation_count,
       max(created_at) AS latest_conversation
FROM conversations;
"

unset PGPASSWORD

# 4. Cleanup
echo "Cleaning up test instance"
aws rds delete-db-instance \
  --db-instance-identifier "${TEST_INSTANCE}" \
  --skip-final-snapshot

echo "=== DR Test Complete ==="
```

## Database Monitoring

### Key Metrics

**Performance Metrics**:
- Connection count
- CPU utilization
- Free memory
- Disk I/O
- Read/write latency
- Replication lag (for Multi-AZ)

**Query Metrics**:
- Slow queries (> 1s)
- Query execution time (p50, p95, p99)
- Queries per second
- Cache hit ratio

**Resource Metrics**:
- Storage used
- Storage IOPS
- Network throughput

### Prometheus Queries

```promql
# Connection pool exhaustion
(pg_stat_database_numbackends / pg_settings_max_connections) > 0.8

# High replication lag
pg_stat_replication_replay_lag > 100

# Slow queries
rate(pg_stat_statements_mean_time[5m]) > 1000

# Cache hit ratio
(pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)) < 0.9
```

### Alerting Rules

```yaml
- alert: DatabaseConnectionsHigh
  expr: |
    (pg_stat_database_numbackends / pg_settings_max_connections) > 0.8
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Database connection pool is 80% full"

- alert: DatabaseReplicationLag
  expr: pg_stat_replication_replay_lag > 100
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Database replication lag is high"

- alert: DatabaseSlowQueries
  expr: rate(pg_stat_statements_mean_time[5m]) > 1000
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Database has slow queries"
```

### Query Optimization

**pg_stat_statements**:
```sql
-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Find frequently executed queries
SELECT 
    query,
    calls,
    total_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

**EXPLAIN ANALYZE**:
```sql
-- Analyze query performance
EXPLAIN ANALYZE
SELECT *
FROM conversation_chunks
WHERE embedding <-> '[0.1, 0.2, ...]'::vector < 0.5
ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
LIMIT 10;
```

## Database Maintenance

### Routine Maintenance Tasks

**Daily**:
- Monitor connection count
- Check slow query log
- Verify backups completed

**Weekly**:
- Review query performance
- Check index usage
- Monitor table bloat
- Review disk space

**Monthly**:
- Test backup restore
- Review and optimize indexes
- Update statistics
- Review parameter settings

**Quarterly**:
- Major version upgrade planning
- Capacity planning
- Security audit

### Vacuum and Analyze

**Auto-vacuum Configuration**:
```sql
-- Check autovacuum settings
SHOW autovacuum;
SHOW autovacuum_naptime;
SHOW autovacuum_vacuum_threshold;

-- Tune for high-write workloads
ALTER SYSTEM SET autovacuum_naptime = '30s';
ALTER SYSTEM SET autovacuum_vacuum_threshold = 1000;
ALTER SYSTEM SET autovacuum_analyze_threshold = 500;

SELECT pg_reload_conf();
```

**Manual Vacuum**:
```sql
-- Full vacuum (requires lock, use during maintenance window)
VACUUM FULL ANALYZE conversations;

-- Regular vacuum (no lock, can run anytime)
VACUUM ANALYZE conversation_chunks;

-- Check last vacuum time
SELECT 
    schemaname,
    relname,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
ORDER BY last_autovacuum ASC;
```

---

**Document Version**: 1.0  
**Author**: Architect Agent  
**Last Updated**: 2025-11-13
