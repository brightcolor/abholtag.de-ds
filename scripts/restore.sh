#!/bin/bash
# Restore PostgreSQL database from a backup
set -e

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.dump>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

DB_NAME="${DB_NAME:-abfuhrkalender}"
DB_USER="${DB_USER:-abfuhr}"
DB_HOST="${DB_HOST:-db}"

echo "=== Database Restore ==="
echo "Backup file: $BACKUP_FILE"
echo "Target database: $DB_NAME"

# Verify checksum if available
if [ -f "${BACKUP_FILE}.sha256" ]; then
    echo "Verifying checksum..."
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

# Drop and recreate database
echo "Dropping existing connections..."
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
"

echo "Restoring from backup..."
pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  "$BACKUP_FILE"

echo "=== Restore Complete ==="