# Database Backup Procedures

This document outlines the backup and recovery procedures for the Unified Trading Intelligence Platform database.

## Table of Contents

1. [Overview](#overview)
2. [Backup Strategy](#backup-strategy)
3. [Automated Backups](#automated-backups)
4. [Manual Backups](#manual-backups)
5. [Backup Verification](#backup-verification)
6. [Restore Procedures](#restore-procedures)
7. [Disaster Recovery](#disaster-recovery)
8. [Backup Retention Policy](#backup-retention-policy)

---

## Overview

The platform uses PostgreSQL (Supabase) for data persistence. Regular backups are critical for:
- Data protection against accidental deletion
- Recovery from system failures
- Compliance requirements
- Migration and testing

### Backup Types

1. **Full Backups**: Complete database dump
2. **Incremental Backups**: Changes since last backup (via WAL)
3. **Point-in-Time Recovery (PITR)**: Restore to specific timestamp

---

## Backup Strategy

### Production Environment

- **Frequency**: Daily full backups + continuous WAL archiving
- **Retention**: 30 days for daily backups, 7 days for WAL
- **Storage**: Supabase automatic backups + external S3 bucket
- **Verification**: Weekly restore tests

### Staging Environment

- **Frequency**: Weekly full backups
- **Retention**: 14 days
- **Storage**: Supabase automatic backups

### Development Environment

- **Frequency**: Manual backups before major changes
- **Retention**: 7 days
- **Storage**: Local filesystem

---

## Automated Backups

### Supabase Automatic Backups

Supabase provides automatic daily backups for all projects:

**Features**:
- Daily full backups
- 7-day retention (free tier)
- 30-day retention (pro tier)
- Point-in-time recovery (pro tier)
- One-click restore from dashboard

**Access Backups**:
1. Go to Supabase dashboard
2. Select your project
3. Navigate to "Database" → "Backups"
4. View available backups and restore points

### Custom Automated Backups

For additional protection, set up automated backups to external storage:

#### Using pg_dump with Cron (Linux/Mac)

```bash
# Create backup script
cat > /usr/local/bin/backup-trading-db.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/var/backups/trading-platform"
DATABASE_URL="your-database-url"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup: $BACKUP_FILE"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    echo "Backup created successfully: $BACKUP_FILE"
    echo "Size: $(du -h $BACKUP_FILE | cut -f1)"
else
    echo "Error: Backup failed"
    exit 1
fi

# Remove old backups
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "Old backups removed (older than $RETENTION_DAYS days)"

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_FILE" s3://your-bucket/backups/

echo "Backup completed successfully"
EOF

# Make script executable
chmod +x /usr/local/bin/backup-trading-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
# 0 2 * * * /usr/local/bin/backup-trading-db.sh >> /var/log/trading-db-backup.log 2>&1
```

#### Using Task Scheduler (Windows)

```powershell
# Create backup script
$backupScript = @'
$BackupDir = "C:\Backups\trading-platform"
$DatabaseUrl = $env:DATABASE_URL
$RetentionDays = 30
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "$BackupDir\backup_$Date.sql.gz"

# Create backup directory
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

# Create backup
Write-Host "Creating backup: $BackupFile"
pg_dump $DatabaseUrl | gzip > $BackupFile

# Verify backup
if (Test-Path $BackupFile) {
    $size = (Get-Item $BackupFile).Length / 1MB
    Write-Host "Backup created successfully: $BackupFile"
    Write-Host "Size: $([math]::Round($size, 2)) MB"
} else {
    Write-Host "Error: Backup failed"
    exit 1
}

# Remove old backups
Get-ChildItem -Path $BackupDir -Filter "backup_*.sql.gz" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
    Remove-Item -Force

Write-Host "Backup completed successfully"
'@

# Save script
$backupScript | Out-File -FilePath "C:\Scripts\backup-trading-db.ps1"

# Create scheduled task (daily at 2 AM)
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Scripts\backup-trading-db.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
Register-ScheduledTask -TaskName "TradingPlatformBackup" -Action $action -Trigger $trigger -Principal $principal
```

---

## Manual Backups

### Full Database Backup

```bash
# Using pg_dump
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz

# Custom format (faster restore, parallel)
pg_dump -Fc $DATABASE_URL > backup_$(date +%Y%m%d).dump
```

### Backup Specific Tables

```bash
# Backup single table
pg_dump -t users $DATABASE_URL > users_backup.sql

# Backup multiple tables
pg_dump -t users -t trades -t positions $DATABASE_URL > critical_tables_backup.sql
```

### Backup Schema Only

```bash
# Schema without data
pg_dump --schema-only $DATABASE_URL > schema_backup.sql

# Data without schema
pg_dump --data-only $DATABASE_URL > data_backup.sql
```

### Export to CSV

```bash
# Export table to CSV
psql $DATABASE_URL -c "\COPY users TO 'users.csv' CSV HEADER"
psql $DATABASE_URL -c "\COPY trades TO 'trades.csv' CSV HEADER"
```

---

## Backup Verification

### Verify Backup Integrity

```bash
# Check if backup file is valid
gunzip -t backup.sql.gz

# Check backup size
ls -lh backup.sql.gz

# Verify backup can be read
gunzip -c backup.sql.gz | head -n 100
```

### Test Restore (Recommended Weekly)

```bash
# Create test database
createdb test_restore

# Restore backup
gunzip -c backup.sql.gz | psql test_restore

# Verify data
psql test_restore -c "SELECT COUNT(*) FROM users;"
psql test_restore -c "SELECT COUNT(*) FROM trades;"

# Cleanup
dropdb test_restore
```

---

## Restore Procedures

### Full Database Restore

```bash
# From SQL file
psql $DATABASE_URL < backup.sql

# From compressed file
gunzip -c backup.sql.gz | psql $DATABASE_URL

# From custom format
pg_restore -d $DATABASE_URL backup.dump

# Parallel restore (faster)
pg_restore -j 4 -d $DATABASE_URL backup.dump
```

### Restore Specific Tables

```bash
# Restore single table
pg_restore -t users -d $DATABASE_URL backup.dump

# Restore multiple tables
pg_restore -t users -t trades -d $DATABASE_URL backup.dump
```

### Point-in-Time Recovery (Supabase Pro)

1. Go to Supabase dashboard
2. Navigate to "Database" → "Backups"
3. Select "Point-in-Time Recovery"
4. Choose timestamp
5. Click "Restore"

### Restore from CSV

```bash
# Import CSV to table
psql $DATABASE_URL -c "\COPY users FROM 'users.csv' CSV HEADER"
```

---

## Disaster Recovery

### Recovery Time Objective (RTO)

- **Target**: < 1 hour for production
- **Target**: < 4 hours for staging

### Recovery Point Objective (RPO)

- **Target**: < 24 hours (daily backups)
- **With PITR**: < 5 minutes

### Disaster Recovery Steps

1. **Assess the Situation**
   - Identify the issue (data loss, corruption, deletion)
   - Determine the scope (full database, specific tables, specific records)
   - Identify the last known good state

2. **Notify Stakeholders**
   - Alert team members
   - Communicate expected downtime
   - Document the incident

3. **Stop Application**
   - Put application in maintenance mode
   - Stop all write operations
   - Prevent further data loss

4. **Restore from Backup**
   - Choose appropriate backup (most recent or specific point-in-time)
   - Restore to staging first (if possible)
   - Verify restored data
   - Restore to production

5. **Verify Restoration**
   - Check table counts
   - Verify critical data
   - Run smoke tests
   - Check data integrity

6. **Resume Operations**
   - Remove maintenance mode
   - Monitor application
   - Verify normal operations

7. **Post-Incident Review**
   - Document what happened
   - Identify root cause
   - Implement preventive measures
   - Update procedures

### Emergency Contacts

- **Database Admin**: [Contact Info]
- **DevOps Lead**: [Contact Info]
- **Supabase Support**: support@supabase.io

---

## Backup Retention Policy

### Production

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| Full Backup | Daily | 30 days | Supabase + S3 |
| WAL Archives | Continuous | 7 days | Supabase |
| Weekly Backup | Weekly | 90 days | S3 |
| Monthly Backup | Monthly | 1 year | S3 Glacier |

### Staging

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| Full Backup | Weekly | 14 days | Supabase |

### Development

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| Manual Backup | As needed | 7 days | Local |

---

## Backup Monitoring

### Automated Monitoring

Set up alerts for:
- Backup failures
- Backup size anomalies
- Missing backups
- Restore test failures

### Backup Health Checks

```bash
# Check last backup time
aws s3 ls s3://your-bucket/backups/ --recursive | tail -1

# Verify backup size
aws s3 ls s3://your-bucket/backups/ --recursive | awk '{print $3, $4}' | sort -n

# Test restore (weekly)
./test-restore.sh
```

---

## Best Practices

1. **Test Restores Regularly**: Verify backups work before you need them
2. **Multiple Backup Locations**: Store backups in different locations
3. **Encrypt Backups**: Protect sensitive data in backups
4. **Document Procedures**: Keep this document up to date
5. **Automate Everything**: Reduce human error
6. **Monitor Backup Health**: Set up alerts for failures
7. **Version Control Schema**: Track schema changes in Git
8. **Backup Before Changes**: Always backup before major changes

---

## Backup Scripts

### Complete Backup Script

```bash
#!/bin/bash
# Complete backup script with verification and upload

set -e

# Configuration
BACKUP_DIR="/var/backups/trading-platform"
DATABASE_URL="$DATABASE_URL"
S3_BUCKET="your-backup-bucket"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"
LOG_FILE="/var/log/trading-db-backup.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Start backup
log "Starting backup..."

# Create backup
if pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"; then
    log "Backup created: $BACKUP_FILE"
    log "Size: $(du -h $BACKUP_FILE | cut -f1)"
else
    log "ERROR: Backup failed"
    exit 1
fi

# Verify backup
if gunzip -t "$BACKUP_FILE"; then
    log "Backup verification successful"
else
    log "ERROR: Backup verification failed"
    exit 1
fi

# Upload to S3
if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/"; then
    log "Backup uploaded to S3"
else
    log "WARNING: S3 upload failed"
fi

# Remove old local backups
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
log "Old backups removed (older than $RETENTION_DAYS days)"

# Remove old S3 backups
aws s3 ls "s3://$S3_BUCKET/backups/" | while read -r line; do
    createDate=$(echo $line | awk '{print $1" "$2}')
    createDate=$(date -d "$createDate" +%s)
    olderThan=$(date -d "$RETENTION_DAYS days ago" +%s)
    if [[ $createDate -lt $olderThan ]]; then
        fileName=$(echo $line | awk '{print $4}')
        if [[ $fileName != "" ]]; then
            aws s3 rm "s3://$S3_BUCKET/backups/$fileName"
            log "Removed old S3 backup: $fileName"
        fi
    fi
done

log "Backup completed successfully"
```

---

## Troubleshooting

### Backup Fails

```bash
# Check disk space
df -h

# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check permissions
ls -la /var/backups/trading-platform/

# Check logs
tail -f /var/log/trading-db-backup.log
```

### Restore Fails

```bash
# Check backup integrity
gunzip -t backup.sql.gz

# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check for conflicts
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"

# Drop and recreate database (CAUTION!)
dropdb trading_db
createdb trading_db
```

### Slow Restore

```bash
# Use parallel restore
pg_restore -j 4 -d $DATABASE_URL backup.dump

# Disable triggers during restore
pg_restore --disable-triggers -d $DATABASE_URL backup.dump

# Restore schema first, then data
pg_restore --schema-only -d $DATABASE_URL backup.dump
pg_restore --data-only -d $DATABASE_URL backup.dump
```

---

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Supabase Backup Guide](https://supabase.com/docs/guides/platform/backups)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_restore Documentation](https://www.postgresql.org/docs/current/app-pgrestore.html)

---

**Last Updated**: 2024
**Maintained By**: Platform Team
**Review Schedule**: Quarterly
