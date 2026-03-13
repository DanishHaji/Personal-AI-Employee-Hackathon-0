#!/bin/bash

#######################################################################
# Let's Encrypt SSL Setup Script
#######################################################################
#
# Sets up free SSL certificate using Let's Encrypt/Certbot
# for Odoo HTTPS access
#
# Usage:
#   sudo ./setup-ssl.sh odoo.example.com
#
# Prerequisites:
#   - Domain name pointing to this server's IP
#   - Port 80 and 443 open in firewall
#
# Created: 2026-03-12
# Part of: Platinum Tier US5 - Odoo Integration
#######################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -eq 0 ]; then
    log_error "Domain name required"
    echo "Usage: sudo ./setup-ssl.sh odoo.example.com"
    exit 1
fi

DOMAIN=$1

# Check root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Setting up Let's Encrypt SSL for: $DOMAIN"

# Install certbot
log_info "Installing certbot..."
apt-get update -qq
apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
log_info "Obtaining SSL certificate..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" --redirect

# Test auto-renewal
log_info "Testing certificate auto-renewal..."
certbot renew --dry-run

log_success "SSL certificate installed successfully!"
echo ""
echo "Certificate location: /etc/letsencrypt/live/$DOMAIN/"
echo "Auto-renewal configured via systemd timer"
echo ""
echo "Test your site: https://$DOMAIN"
echo ""
