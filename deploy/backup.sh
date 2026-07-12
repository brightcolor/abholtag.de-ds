#!/bin/sh
# Backup-Skript (§38): PostgreSQL-Dump + Media (Original-PDFs, Uploads) + .env
# Aufruf z. B. täglich per Cron; BACKUP_DIR extern sichern (z. B. restic/borg).
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Datenbank (aus dem Compose-Setup)
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-abfuhrkalender}" \
  "${POSTGRES_DB:-abfuhrkalender}" | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"

# Media: archivierte Quelldokumente und Community-Uploads (Bind Mount)
tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" docker-data/media

# Konfiguration
cp .env "$BACKUP_DIR/env-$STAMP"

# Aufbewahrung: 30 Tage
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup abgeschlossen: $BACKUP_DIR ($STAMP)"
