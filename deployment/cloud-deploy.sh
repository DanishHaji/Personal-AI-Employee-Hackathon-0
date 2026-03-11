#!/bin/bash

#######################################################################
# AI Employee - Cloud VM Deployment Script
#######################################################################
#
# Automated deployment for Platinum Tier Cloud instance
#
# Prerequisites:
#   - Fresh Ubuntu 22.04 VM
#   - Root or sudo access
#   - Internet connectivity
#
# Usage:
#   sudo ./cloud-deploy.sh
#
# Created: 2026-03-10
# Part of: Platinum Tier US3 - Cloud Deployment
#######################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/ai-employee"
SERVICE_USER="aiemployee"
SERVICE_GROUP="aiemployee"
PYTHON_VERSION="3.13"
REPO_URL="https://github.com/DanishHaji/Personal-AI-Employee-Hackathon-0.git"
BRANCH="004-platinum-tier-upgrade"

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

create_user() {
    log_info "Creating service user: $SERVICE_USER"

    if id "$SERVICE_USER" &>/dev/null; then
        log_warning "User $SERVICE_USER already exists, skipping"
    else
        useradd -r -m -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
        log_success "User $SERVICE_USER created"
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."

    # Update package list
    apt-get update -qq

    # Install required packages
    apt-get install -y \
        software-properties-common \
        build-essential \
        git \
        curl \
        wget \
        pkg-config \
        libsystemd-dev \
        python3-systemd \
        || { log_error "Failed to install system dependencies"; exit 1; }

    log_success "System dependencies installed"
}

install_python() {
    log_info "Installing Python ${PYTHON_VERSION}..."

    # Check if Python 3.13+ already installed
    if command -v python3.13 &>/dev/null; then
        log_success "Python 3.13 already installed"
        return
    fi

    # Add deadsnakes PPA for Python 3.13
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq

    # Install Python 3.13
    apt-get install -y \
        python3.13 \
        python3.13-dev \
        python3.13-venv \
        python3.13-distutils \
        || { log_error "Failed to install Python 3.13"; exit 1; }

    # Make python3 point to python3.13
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1

    log_success "Python ${PYTHON_VERSION} installed"
}

install_uv() {
    log_info "Installing uv package manager..."

    if command -v uv &>/dev/null; then
        log_success "uv already installed"
        return
    fi

    # Install uv as aiemployee user
    su - "$SERVICE_USER" -c "curl -LsSf https://astral.sh/uv/install.sh | sh"

    # Add uv to PATH for aiemployee user
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$INSTALL_DIR/.bashrc"

    log_success "uv package manager installed"
}

clone_repository() {
    log_info "Cloning AI Employee repository..."

    if [ -d "$INSTALL_DIR/.git" ]; then
        log_warning "Repository already exists, pulling latest changes"
        su - "$SERVICE_USER" -c "cd $INSTALL_DIR && git pull origin $BRANCH"
    else
        # Clone as aiemployee user
        su - "$SERVICE_USER" -c "git clone --branch $BRANCH $REPO_URL $INSTALL_DIR"
    fi

    log_success "Repository cloned/updated"
}

install_python_dependencies() {
    log_info "Installing Python dependencies with uv..."

    # Run uv sync as aiemployee user
    su - "$SERVICE_USER" -c "cd $INSTALL_DIR && /home/$SERVICE_USER/.cargo/bin/uv sync"

    log_success "Python dependencies installed"
}

configure_environment() {
    log_info "Creating Cloud environment configuration..."

    ENV_FILE="$INSTALL_DIR/.env.cloud"

    if [ -f "$ENV_FILE" ]; then
        log_warning ".env.cloud already exists, backing up to .env.cloud.backup"
        cp "$ENV_FILE" "$ENV_FILE.backup"
    fi

    # Create .env.cloud template (user must fill in actual values)
    cat > "$ENV_FILE" << 'EOF'
# AI Employee Cloud Instance Configuration
# IMPORTANT: Fill in actual values before starting services

# Instance Configuration
INSTANCE=cloud
VAULT_PATH=/opt/ai-employee

# Gmail API (required for email monitoring)
GMAIL_CREDENTIALS_PATH=/opt/ai-employee/.credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=/opt/ai-employee/.credentials/gmail_token.json

# Claude API (required for AI processing)
ANTHROPIC_API_KEY=your_api_key_here

# GitHub (for vault sync)
# Generate SSH key and add to GitHub:
#   ssh-keygen -t ed25519 -C "cloud@ai-employee" -f ~/.ssh/id_ed25519
#   cat ~/.ssh/id_ed25519.pub  # Add this to GitHub
GIT_SSH_KEY=/home/aiemployee/.ssh/id_ed25519

# Monitoring
HEALTH_CHECK_INTERVAL=60
WATCHDOG_TIMEOUT=120

# Alerts (optional)
ALERT_EMAIL=
ALERT_WEBHOOK_URL=

# CRITICAL: DO NOT add these secrets to Cloud instance
# These stay on Local instance only:
#   - WhatsApp session files
#   - Banking credentials
#   - Odoo admin credentials
#   - Payment API keys
EOF

    chown "$SERVICE_USER:$SERVICE_GROUP" "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    log_success "Environment configuration created at $ENV_FILE"
    log_warning "IMPORTANT: Edit $ENV_FILE with actual credentials before starting services"
}

setup_git_ssh() {
    log_info "Setting up Git SSH for vault sync..."

    SSH_DIR="/home/$SERVICE_USER/.ssh"

    if [ ! -d "$SSH_DIR" ]; then
        su - "$SERVICE_USER" -c "mkdir -p $SSH_DIR && chmod 700 $SSH_DIR"
    fi

    if [ ! -f "$SSH_DIR/id_ed25519" ]; then
        log_info "Generating SSH key for Git..."
        su - "$SERVICE_USER" -c "ssh-keygen -t ed25519 -C 'cloud@ai-employee' -f $SSH_DIR/id_ed25519 -N ''"

        log_success "SSH key generated"
        log_warning "Add this public key to GitHub:"
        echo ""
        cat "$SSH_DIR/id_ed25519.pub"
        echo ""
        read -p "Press Enter after adding SSH key to GitHub..."
    else
        log_success "SSH key already exists"
    fi

    # Configure Git
    su - "$SERVICE_USER" -c "git config --global user.name 'AI Employee Cloud'"
    su - "$SERVICE_USER" -c "git config --global user.email 'cloud@ai-employee'"

    log_success "Git configured"
}

create_vault_directories() {
    log_info "Creating Platinum Tier vault directories..."

    DIRECTORIES=(
        "$INSTALL_DIR/Cloud_Drafts"
        "$INSTALL_DIR/Needs_Local"
        "$INSTALL_DIR/Claims"
        "$INSTALL_DIR/Health"
        "$INSTALL_DIR/Logs"
        "$INSTALL_DIR/Cloud_Dropzone"
    )

    for dir in "${DIRECTORIES[@]}"; do
        if [ ! -d "$dir" ]; then
            su - "$SERVICE_USER" -c "mkdir -p $dir"
        fi
    done

    log_success "Vault directories created"
}

install_systemd_services() {
    log_info "Installing systemd service files..."

    SERVICES=(
        "vault-sync.service"
        "vault-sync.timer"
        "claim-expiry.service"
        "claim-expiry.timer"
        "health-monitor.service"
        "gmail-watcher.service"
        "filesystem-watcher.service"
    )

    for service in "${SERVICES[@]}"; do
        log_info "Installing $service..."

        # Copy service file
        cp "$INSTALL_DIR/deployment/systemd/$service" "/etc/systemd/system/$service"

        # Update Python path in service file (use absolute path from venv)
        PYTHON_PATH="$INSTALL_DIR/.venv/bin/python3"
        sed -i "s|/usr/bin/python3|$PYTHON_PATH|g" "/etc/systemd/system/$service"

        # Update vault path in service file
        sed -i "s|/opt/ai-employee|$INSTALL_DIR|g" "/etc/systemd/system/$service"

        log_success "$service installed"
    done

    # Reload systemd
    systemctl daemon-reload

    log_success "systemd services installed"
}

enable_services() {
    log_info "Enabling systemd services..."

    TIMERS=(
        "vault-sync.timer"
        "claim-expiry.timer"
    )

    SERVICES=(
        "health-monitor.service"
        "gmail-watcher.service"
        "filesystem-watcher.service"
    )

    # Enable and start timers
    for timer in "${TIMERS[@]}"; do
        systemctl enable "$timer"
        log_success "$timer enabled"
    done

    # Enable services (don't start yet - user needs to configure .env.cloud first)
    for service in "${SERVICES[@]}"; do
        systemctl enable "$service"
        log_success "$service enabled (not started - configure .env.cloud first)"
    done

    log_success "Services enabled"
}

run_health_check() {
    log_info "Running deployment health check..."

    # Check if services are installed
    SERVICES=(
        "vault-sync.timer"
        "claim-expiry.timer"
        "health-monitor.service"
        "gmail-watcher.service"
        "filesystem-watcher.service"
    )

    ALL_OK=true

    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "$service"; then
            log_success "$service installed"
        else
            log_error "$service NOT installed"
            ALL_OK=false
        fi
    done

    # Check if directories exist
    DIRECTORIES=(
        "$INSTALL_DIR/Cloud_Drafts"
        "$INSTALL_DIR/Needs_Local"
        "$INSTALL_DIR/Claims"
        "$INSTALL_DIR/Health"
        "$INSTALL_DIR/Logs"
    )

    for dir in "${DIRECTORIES[@]}"; do
        if [ -d "$dir" ]; then
            log_success "$dir exists"
        else
            log_error "$dir NOT found"
            ALL_OK=false
        fi
    done

    # Check if .env.cloud exists
    if [ -f "$INSTALL_DIR/.env.cloud" ]; then
        log_success ".env.cloud exists"
    else
        log_error ".env.cloud NOT found"
        ALL_OK=false
    fi

    if [ "$ALL_OK" = true ]; then
        log_success "Health check PASSED"
    else
        log_error "Health check FAILED - review errors above"
        return 1
    fi
}

print_next_steps() {
    echo ""
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Configure credentials in .env.cloud:"
    echo "   sudo nano $INSTALL_DIR/.env.cloud"
    echo ""
    echo "2. Add Gmail credentials:"
    echo "   - Upload gmail_credentials.json to $INSTALL_DIR/.credentials/"
    echo ""
    echo "3. Start services:"
    echo "   sudo systemctl start vault-sync.timer"
    echo "   sudo systemctl start claim-expiry.timer"
    echo "   sudo systemctl start health-monitor.service"
    echo "   sudo systemctl start gmail-watcher.service"
    echo "   sudo systemctl start filesystem-watcher.service"
    echo ""
    echo "4. Check service status:"
    echo "   sudo systemctl status health-monitor.service"
    echo "   sudo journalctl -u health-monitor.service -f"
    echo ""
    echo "5. Monitor health snapshots:"
    echo "   ls -lh $INSTALL_DIR/Health/"
    echo ""
    echo "6. View logs:"
    echo "   cat $INSTALL_DIR/Logs/health.jsonl"
    echo "   cat $INSTALL_DIR/Logs/sync.jsonl"
    echo ""
    echo "=========================================="
}

main() {
    echo ""
    echo "=========================================="
    echo "AI Employee Cloud Deployment"
    echo "Platinum Tier - US3"
    echo "=========================================="
    echo ""

    log_info "Starting deployment..."
    echo ""

    # Step 1: Check root
    check_root

    # Step 2: Create user
    create_user

    # Step 3: Install dependencies
    install_dependencies
    install_python
    install_uv

    # Step 4: Clone repository
    clone_repository

    # Step 5: Install Python dependencies
    install_python_dependencies

    # Step 6: Configure environment
    configure_environment
    setup_git_ssh
    create_vault_directories

    # Step 7: Install systemd services
    install_systemd_services
    enable_services

    # Step 8: Health check
    run_health_check

    # Print next steps
    print_next_steps

    log_success "Deployment script completed successfully!"
}

# Run main
main
