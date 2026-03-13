#!/bin/bash

#######################################################################
# Odoo Installation Script for Cloud VM
#######################################################################
#
# Installs and configures Odoo Community Edition on Ubuntu 22.04
# for Personal AI Employee expense tracking integration
#
# Prerequisites:
#   - Ubuntu 22.04 LTS
#   - Root or sudo access
#   - Internet connectivity
#   - At least 2GB RAM, 20GB disk space
#
# Usage:
#   sudo ./install-odoo.sh
#
# Created: 2026-03-12
# Part of: Platinum Tier US5 - Odoo Integration
#######################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ODOO_VERSION="17.0"
ODOO_USER="odoo"
ODOO_HOME="/opt/odoo"
ODOO_CONFIG="/etc/odoo.conf"
POSTGRES_USER="odoo"
POSTGRES_DB="odoo"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."

    # Update package list
    apt-get update -qq

    # Install required packages
    apt-get install -y \
        git \
        python3-pip \
        python3-dev \
        python3-venv \
        python3-wheel \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libtiff5-dev \
        libjpeg8-dev \
        libopenjp2-7-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev \
        libpq-dev \
        wget \
        node-less \
        npm \
        || { log_error "Failed to install system dependencies"; exit 1; }

    # Install wkhtmltopdf (for PDF reports)
    log_info "Installing wkhtmltopdf..."
    wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    apt-get install -y ./wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    rm wkhtmltox_0.12.6.1-2.jammy_amd64.deb

    log_success "System dependencies installed"
}

install_postgresql() {
    log_info "Installing PostgreSQL..."

    # Install PostgreSQL
    apt-get install -y postgresql postgresql-contrib || {
        log_error "Failed to install PostgreSQL"
        exit 1
    }

    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql

    # Create Odoo PostgreSQL user
    log_info "Creating PostgreSQL user: $POSTGRES_USER"
    sudo -u postgres psql -c "CREATE USER $POSTGRES_USER WITH CREATEDB PASSWORD 'odoo_password';" 2>/dev/null || \
        log_warning "PostgreSQL user $POSTGRES_USER already exists"

    # Create Odoo database
    log_info "Creating PostgreSQL database: $POSTGRES_DB"
    sudo -u postgres createdb -O $POSTGRES_USER $POSTGRES_DB 2>/dev/null || \
        log_warning "PostgreSQL database $POSTGRES_DB already exists"

    log_success "PostgreSQL installed and configured"
}

create_odoo_user() {
    log_info "Creating Odoo system user..."

    if id "$ODOO_USER" &>/dev/null; then
        log_warning "User $ODOO_USER already exists, skipping"
    else
        useradd -r -m -s /bin/bash -d "$ODOO_HOME" "$ODOO_USER"
        log_success "User $ODOO_USER created"
    fi
}

install_odoo() {
    log_info "Cloning Odoo Community Edition v${ODOO_VERSION}..."

    if [ -d "$ODOO_HOME/odoo" ]; then
        log_warning "Odoo already cloned, pulling latest changes"
        cd "$ODOO_HOME/odoo"
        sudo -u "$ODOO_USER" git pull
    else
        # Clone Odoo repository
        sudo -u "$ODOO_USER" git clone --depth 1 --branch "$ODOO_VERSION" \
            https://github.com/odoo/odoo.git "$ODOO_HOME/odoo"
    fi

    log_success "Odoo cloned to $ODOO_HOME/odoo"
}

install_python_dependencies() {
    log_info "Installing Python dependencies..."

    # Create virtual environment
    sudo -u "$ODOO_USER" python3 -m venv "$ODOO_HOME/venv"

    # Install Odoo Python requirements
    sudo -u "$ODOO_USER" "$ODOO_HOME/venv/bin/pip" install --upgrade pip
    sudo -u "$ODOO_USER" "$ODOO_HOME/venv/bin/pip" install wheel
    sudo -u "$ODOO_USER" "$ODOO_HOME/venv/bin/pip" install -r "$ODOO_HOME/odoo/requirements.txt"

    log_success "Python dependencies installed"
}

configure_odoo() {
    log_info "Creating Odoo configuration file..."

    cat > "$ODOO_CONFIG" << EOF
[options]
; Odoo Configuration for AI Employee Integration
; Created: $(date)

; Database settings
admin_passwd = $(openssl rand -base64 32)
db_host = localhost
db_port = 5432
db_user = $POSTGRES_USER
db_password = odoo_password
db_name = $POSTGRES_DB

; Server settings
http_port = 8069
http_interface = 127.0.0.1
workers = 2
max_cron_threads = 1

; Logging
logfile = /var/log/odoo/odoo.log
log_level = info

; Addons
addons_path = $ODOO_HOME/odoo/addons

; Data directory
data_dir = $ODOO_HOME/.local/share/Odoo

; Proxy mode (for nginx)
proxy_mode = True
EOF

    # Set permissions
    chown "$ODOO_USER:$ODOO_USER" "$ODOO_CONFIG"
    chmod 640 "$ODOO_CONFIG"

    # Create log directory
    mkdir -p /var/log/odoo
    chown -R "$ODOO_USER:$ODOO_USER" /var/log/odoo

    log_success "Odoo configuration created at $ODOO_CONFIG"
}

create_systemd_service() {
    log_info "Creating systemd service..."

    cat > /etc/systemd/system/odoo.service << EOF
[Unit]
Description=Odoo Community Edition
Documentation=https://www.odoo.com/documentation
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$ODOO_USER
Group=$ODOO_USER
ExecStart=$ODOO_HOME/venv/bin/python3 $ODOO_HOME/odoo/odoo-bin -c $ODOO_CONFIG
WorkingDirectory=$ODOO_HOME
StandardOutput=journal
StandardError=journal
SyslogIdentifier=odoo

# Restart policy
Restart=on-failure
RestartSec=10s

# Resource limits
CPUQuota=50%
MemoryMax=2G

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable and start Odoo
    systemctl enable odoo.service

    log_success "Odoo systemd service created"
}

configure_nginx() {
    log_info "Installing and configuring nginx..."

    # Install nginx
    apt-get install -y nginx

    # Create nginx configuration
    cat > /etc/nginx/sites-available/odoo << 'EOF'
upstream odoo {
    server 127.0.0.1:8069;
}

upstream odoo-chat {
    server 127.0.0.1:8072;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name odoo.example.com;  # CHANGE THIS

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name odoo.example.com;  # CHANGE THIS

    # SSL certificates (will be created by Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/odoo.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/odoo.example.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/odoo-access.log;
    error_log /var/log/nginx/odoo-error.log;

    # Proxy settings
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    # Proxy headers
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    # File upload size
    client_max_body_size 100M;

    # Odoo web requests
    location / {
        proxy_redirect off;
        proxy_pass http://odoo;
    }

    # Odoo web polls
    location /longpolling {
        proxy_pass http://odoo-chat;
    }

    # Static files
    location ~* /web/static/ {
        proxy_cache_valid 200 90m;
        proxy_buffering on;
        expires 864000;
        proxy_pass http://odoo;
    }

    # Gzip compression
    gzip on;
    gzip_types text/css text/scss text/plain text/xml application/xml application/json application/javascript;
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/odoo

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Test nginx configuration
    nginx -t

    # Reload nginx
    systemctl reload nginx

    log_success "Nginx configured for Odoo"
}

print_next_steps() {
    echo ""
    echo "=========================================="
    echo "Odoo Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Update nginx configuration with your domain:"
    echo "   sudo nano /etc/nginx/sites-available/odoo"
    echo "   # Replace 'odoo.example.com' with your domain"
    echo ""
    echo "2. Setup SSL with Let's Encrypt:"
    echo "   sudo ./setup-ssl.sh odoo.example.com"
    echo ""
    echo "3. Start Odoo service:"
    echo "   sudo systemctl start odoo.service"
    echo ""
    echo "4. Check Odoo status:"
    echo "   sudo systemctl status odoo.service"
    echo "   sudo journalctl -u odoo.service -f"
    echo ""
    echo "5. Access Odoo:"
    echo "   https://odoo.example.com"
    echo ""
    echo "6. Initial setup:"
    echo "   - Create database: odoo"
    echo "   - Set admin password"
    echo "   - Install accounting module"
    echo "   - Generate API key for AI Employee"
    echo ""
    echo "7. Configure AI Employee .env.cloud:"
    echo "   ODOO_URL=https://odoo.example.com"
    echo "   ODOO_DATABASE=odoo"
    echo "   ODOO_USERNAME=admin"
    echo "   ODOO_API_KEY=<your-api-key>"
    echo ""
    echo "Admin password saved in: $ODOO_CONFIG"
    echo "View with: sudo grep admin_passwd $ODOO_CONFIG"
    echo ""
    echo "=========================================="
}

main() {
    echo ""
    echo "=========================================="
    echo "Odoo Installation for AI Employee"
    echo "Platinum Tier US5 - Odoo Integration"
    echo "=========================================="
    echo ""

    log_info "Starting installation..."
    echo ""

    # Step 1: Check root
    check_root

    # Step 2: Install dependencies
    install_dependencies

    # Step 3: Install PostgreSQL
    install_postgresql

    # Step 4: Create Odoo user
    create_odoo_user

    # Step 5: Install Odoo
    install_odoo

    # Step 6: Install Python dependencies
    install_python_dependencies

    # Step 7: Configure Odoo
    configure_odoo

    # Step 8: Create systemd service
    create_systemd_service

    # Step 9: Configure nginx
    configure_nginx

    # Print next steps
    print_next_steps

    log_success "Installation script completed successfully!"
}

# Run main
main
