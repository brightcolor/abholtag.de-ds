#!/bin/bash
# PostgreSQL database backup
set -e

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${DB_NAME:-abfuhrkalender}"
DB_USER="${DB_USER:-abfuhr}"
DB_HOST="${DB_HOST:-db}"

mkdir -p "$BACKUP_DIR"

echo "=== Database Backup ==="
echo "Database: $DB_NAME"
echo "Timestamp: $TIMESTAMP"

# Dump database
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom \
  --compress=9 \
  --file="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"

# Generate SHA256 checksum
sha256sum "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump" > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump.sha256"

echo "Backup created: ${DB_NAME}_${TIMESTAMP}.dump"
echo "Checksum: ${DB_NAME}_${TIMESTAMP}.dump.sha256"

# Clean up backups older than 90 days
find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -mtime +90 -delete
find "$BACKUP_DIR" -name "${DB_NAME}_*.dump.sha256" -mtime +90 -delete

echo "=== Backup Complete ==="