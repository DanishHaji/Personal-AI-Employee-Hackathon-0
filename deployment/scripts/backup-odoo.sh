#!/bin/bash

#######################################################################
# Odoo Database Backup Script
#######################################################################
#
# Creates daily backup of Odoo database
# Keeps last 30 days of backups
#
# Usage:
#   ./backup-odoo.sh
#
# Cron: 0 2 * * * /opt/ai-employee/deployment/scripts/backup-odoo.sh
#
# Created: 2026-03-12
# Part of: Platinum Tier US5 - Odoo Integration
#######################################################################

set -euo pipefail

# Configuration
BACKUP_DIR="/opt/backups/odoo"
DB_NAME="odoo"
DB_USER="odoo"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/odoo_backup_$TIMESTAMP.sql.gz"

echo "Starting Odoo database backup..."
echo "Database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"

# Create backup
if sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_success "Backup created successfully ($SIZE)"
else
    log_error "Backup failed"
    exit 1
fi

# Remove old backups
echo "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "odoo_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -5

# Backup filestore (Odoo attachments)
FILESTORE_DIR="/opt/odoo/.local/share/Odoo/filestore/$DB_NAME"
if [ -d "$FILESTORE_DIR" ]; then
    FILESTORE_BACKUP="$BACKUP_DIR/odoo_filestore_$TIMESTAMP.tar.gz"
    echo ""
    echo "Backing up filestore..."
    tar -czf "$FILESTORE_BACKUP" -C "$(dirname "$FILESTORE_DIR")" "$(basename "$FILESTORE_DIR")"
    SIZE=$(du -h "$FILESTORE_BACKUP" | cut -f1)
    log_success "Filestore backup created ($SIZE)"
fi

echo ""
log_success "Backup completed successfully!"
