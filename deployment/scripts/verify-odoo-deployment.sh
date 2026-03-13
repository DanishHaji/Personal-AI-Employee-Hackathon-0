#!/bin/bash

#######################################################################
# Odoo Deployment Verification Script
#######################################################################
#
# Verifies Odoo installation and integration after deployment
#
# Tests:
# - Odoo service is running
# - PostgreSQL database is accessible
# - nginx reverse proxy is configured
# - SSL certificate is valid
# - API endpoints are responding
# - Health monitoring includes Odoo
# - Backup script is configured
#
# Usage:
#   ./verify-odoo-deployment.sh [odoo.domain.com]
#
# Created: 2026-03-12
# Part of: Platinum Tier US5 - Odoo Integration
#######################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN=${1:-""}
PASSED=0
FAILED=0
WARNINGS=0

log_pass() {
    echo -e "${GREEN}✅ PASS${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}❌ FAIL${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO${NC} $1"
}

log_section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Test 1: Odoo systemd service
test_odoo_service() {
    log_section "Test 1: Odoo Service Status"

    if systemctl is-active --quiet odoo.service; then
        log_pass "Odoo service is running"

        # Check service status
        uptime=$(systemctl show odoo.service --property=ActiveEnterTimestamp --value)
        log_info "Service started: $uptime"

        # Check for errors
        errors=$(journalctl -u odoo.service --since "1 hour ago" --priority=err --quiet | wc -l)
        if [ "$errors" -eq 0 ]; then
            log_pass "No errors in last hour"
        else
            log_warn "Found $errors errors in last hour (check: journalctl -u odoo.service)"
        fi
    else
        log_fail "Odoo service is not running"
        log_info "Start with: sudo systemctl start odoo.service"
    fi
}

# Test 2: PostgreSQL database
test_postgresql() {
    log_section "Test 2: PostgreSQL Database"

    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw odoo; then
        log_pass "Odoo database exists"

        # Check database size
        db_size=$(sudo -u postgres psql -d odoo -c "SELECT pg_size_pretty(pg_database_size('odoo'));" -t | xargs)
        log_info "Database size: $db_size"
    else
        log_fail "Odoo database not found"
    fi

    if sudo -u postgres psql -c '\du' | grep -qw odoo; then
        log_pass "Odoo database user exists"
    else
        log_fail "Odoo database user not found"
    fi
}

# Test 3: nginx configuration
test_nginx() {
    log_section "Test 3: nginx Reverse Proxy"

    if [ -f /etc/nginx/sites-enabled/odoo ]; then
        log_pass "nginx configuration exists"

        # Test configuration
        if nginx -t 2>&1 | grep -q "successful"; then
            log_pass "nginx configuration is valid"
        else
            log_fail "nginx configuration has errors"
        fi
    else
        log_fail "nginx configuration not found"
        log_info "Expected: /etc/nginx/sites-enabled/odoo"
    fi

    if systemctl is-active --quiet nginx; then
        log_pass "nginx service is running"
    else
        log_fail "nginx service is not running"
    fi
}

# Test 4: SSL certificate
test_ssl() {
    log_section "Test 4: SSL Certificate"

    if [ -z "$DOMAIN" ]; then
        log_warn "Domain not provided - skipping SSL check"
        log_info "Usage: $0 odoo.example.com"
        return
    fi

    cert_path="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

    if [ -f "$cert_path" ]; then
        log_pass "SSL certificate exists"

        # Check expiry
        expiry=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
        log_info "Certificate expires: $expiry"

        # Check if expiring soon (30 days)
        if openssl x509 -checkend 2592000 -noout -in "$cert_path" > /dev/null; then
            log_pass "Certificate is valid for >30 days"
        else
            log_warn "Certificate expiring within 30 days"
        fi
    else
        log_fail "SSL certificate not found"
        log_info "Setup with: sudo ./setup-ssl.sh $DOMAIN"
    fi
}

# Test 5: Odoo HTTP endpoints
test_odoo_endpoints() {
    log_section "Test 5: Odoo HTTP Endpoints"

    # Test local port
    if curl -s http://127.0.0.1:8069 > /dev/null; then
        log_pass "Odoo listening on port 8069"
    else
        log_fail "Cannot connect to Odoo on port 8069"
    fi

    # Test via nginx (if domain provided)
    if [ -n "$DOMAIN" ]; then
        if curl -s -k "https://$DOMAIN" | grep -q "Odoo"; then
            log_pass "Odoo accessible via https://$DOMAIN"
        else
            log_fail "Cannot access Odoo via https://$DOMAIN"
        fi
    fi
}

# Test 6: Backup configuration
test_backups() {
    log_section "Test 6: Backup Configuration"

    backup_script="/opt/ai-employee/deployment/scripts/backup-odoo.sh"

    if [ -f "$backup_script" ]; then
        log_pass "Backup script exists"

        if [ -x "$backup_script" ]; then
            log_pass "Backup script is executable"
        else
            log_warn "Backup script is not executable (run: chmod +x $backup_script)"
        fi
    else
        log_fail "Backup script not found"
    fi

    # Check cron job
    if crontab -l 2>/dev/null | grep -q "backup-odoo.sh"; then
        log_pass "Backup cron job configured"

        schedule=$(crontab -l 2>/dev/null | grep "backup-odoo.sh" | cut -d' ' -f1-5)
        log_info "Backup schedule: $schedule"
    else
        log_warn "Backup cron job not configured"
        log_info "Setup with: sudo deployment/scripts/setup-cron-jobs.sh"
    fi

    # Check backup directory
    if [ -d "/opt/backups/odoo" ]; then
        log_pass "Backup directory exists"

        backup_count=$(find /opt/backups/odoo -name "odoo_backup_*.sql.gz" -type f | wc -l)
        if [ "$backup_count" -gt 0 ]; then
            log_info "Found $backup_count backup(s)"

            # Show latest backup
            latest=$(ls -t /opt/backups/odoo/odoo_backup_*.sql.gz 2>/dev/null | head -1)
            if [ -n "$latest" ]; then
                size=$(du -h "$latest" | cut -f1)
                log_info "Latest backup: $(basename "$latest") ($size)"
            fi
        else
            log_warn "No backups found (run backup script to create first backup)"
        fi
    else
        log_warn "Backup directory not found (will be created on first backup)"
    fi
}

# Test 7: Health monitoring
test_health_monitoring() {
    log_section "Test 7: Health Monitoring Integration"

    health_monitor="/opt/ai-employee/src/services/health_monitor.py"

    if [ -f "$health_monitor" ]; then
        log_pass "Health monitor exists"

        # Check if Odoo is in watcher configuration
        if grep -q '"odoo"' "$health_monitor"; then
            log_pass "Odoo included in health monitoring"
        else
            log_warn "Odoo not found in health monitor watchers"
        fi
    else
        log_fail "Health monitor not found"
    fi
}

# Test 8: Odoo configuration
test_odoo_config() {
    log_section "Test 8: Odoo Configuration"

    config_file="/etc/odoo.conf"

    if [ -f "$config_file" ]; then
        log_pass "Odoo configuration file exists"

        # Check key settings
        if grep -q "db_name = odoo" "$config_file"; then
            log_pass "Database name configured"
        else
            log_warn "Database name not configured"
        fi

        if grep -q "proxy_mode = True" "$config_file"; then
            log_pass "Proxy mode enabled"
        else
            log_warn "Proxy mode not enabled"
        fi

        # Check log file
        log_file=$(grep "logfile =" "$config_file" | cut -d= -f2 | xargs)
        if [ -f "$log_file" ]; then
            log_pass "Log file exists: $log_file"

            # Check for recent activity
            if [ -n "$(tail -5 "$log_file" 2>/dev/null)" ]; then
                log_info "Recent log activity detected"
            else
                log_warn "No recent log activity"
            fi
        else
            log_warn "Log file not found: $log_file"
        fi
    else
        log_fail "Odoo configuration file not found"
    fi
}

# Main execution

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Odoo Deployment Verification Script                      ║"
echo "║  Platinum Tier US5 - Odoo Integration                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ -n "$DOMAIN" ]; then
    log_info "Testing domain: $DOMAIN"
else
    log_warn "No domain provided - some tests will be skipped"
    log_info "Usage: $0 odoo.example.com"
fi

echo ""

# Run all tests
test_odoo_service
test_postgresql
test_nginx
test_ssl
test_odoo_endpoints
test_backups
test_health_monitoring
test_odoo_config

# Summary
echo ""
log_section "Test Summary"
echo ""
echo "  Passed:   $PASSED"
echo "  Failed:   $FAILED"
echo "  Warnings: $WARNINGS"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Odoo deployment is verified and healthy."
    echo ""
    echo "Next steps:"
    echo "  1. Access Odoo: https://$DOMAIN (if domain provided)"
    echo "  2. Complete Odoo setup (create admin user, install Accounting module)"
    echo "  3. Generate API key for AI Employee integration"
    echo "  4. Update .env.cloud with Odoo credentials"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "Please review the failures above and fix before proceeding."
    echo ""
    echo "Common fixes:"
    echo "  - Start services: sudo systemctl start odoo nginx"
    echo "  - Check logs: sudo journalctl -u odoo -f"
    echo "  - Verify configuration: sudo nano /etc/odoo.conf"
    echo ""
    exit 1
fi
