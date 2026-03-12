#!/bin/bash

#######################################################################
# Cron Job Setup Script
#######################################################################
#
# Sets up automated cron jobs for AI Employee maintenance tasks
#
# Jobs configured:
# - Daily Odoo database backup (2 AM)
# - Weekly health reports (Monday 8 AM)
# - Monthly budget reports (1st of month, 9 AM)
#
# Usage:
#   sudo ./setup-cron-jobs.sh
#
# Created: 2026-03-12
# Part of: Platinum Tier US5 - Odoo Integration
#######################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Cron jobs to install
CRON_JOBS=(
    # Daily Odoo backup at 2 AM
    "0 2 * * * /opt/ai-employee/deployment/scripts/backup-odoo.sh >> /var/log/odoo-backup.log 2>&1"

    # Weekly health report (Monday 8 AM)
    "0 8 * * 1 cd /opt/ai-employee && /opt/ai-employee/.venv/bin/python3 -c 'from src.services.health_monitor import HealthMonitor; hm = HealthMonitor(\"cloud\"); hm.generate_weekly_report()' >> /var/log/health-report.log 2>&1"

    # Monthly budget/financial report (1st of month, 9 AM)
    "0 9 1 * * cd /opt/ai-employee && /opt/ai-employee/.venv/bin/python3 -m src.scripts.generate_monthly_report >> /var/log/monthly-report.log 2>&1"
)

log_info "Setting up cron jobs for AI Employee..."

# Create log directory
mkdir -p /var/log

# Install cron jobs
log_info "Installing ${#CRON_JOBS[@]} cron jobs..."

for job in "${CRON_JOBS[@]}"; do
    # Check if job already exists
    if crontab -l 2>/dev/null | grep -q "$job"; then
        log_info "Job already exists: ${job:0:50}..."
    else
        # Add job to crontab
        (crontab -l 2>/dev/null; echo "$job") | crontab -
        log_success "Added job: ${job:0:50}..."
    fi
done

# Display current crontab
echo ""
log_info "Current crontab:"
crontab -l

echo ""
log_success "Cron jobs setup complete!"
echo ""
echo "Logs are written to:"
echo "  - /var/log/odoo-backup.log"
echo "  - /var/log/health-report.log"
echo "  - /var/log/monthly-report.log"
echo ""
echo "To view/edit cron jobs:"
echo "  crontab -l  # List jobs"
echo "  crontab -e  # Edit jobs"
