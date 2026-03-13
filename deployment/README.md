# Deployment Guide - Personal AI Employee (Platinum Tier)

Complete deployment instructions for Cloud + Local dual work zone architecture with Odoo accounting integration.

## Quick Start

```bash
# Local instance (5 minutes)
git clone https://github.com/your-username/personal-ai-employee.git
cd personal-ai-employee
cp .env.example .env
# Edit .env with your credentials
uv sync
python src/main.py

# Cloud instance (30 minutes)
ssh root@your-cloud-vm
./deployment/cloud-deploy.sh
```

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local Instance Setup](#local-instance-setup)
4. [Cloud VM Setup](#cloud-vm-setup)
5. [Odoo Installation](#odoo-installation-optional)
6. [Vault Synchronization](#vault-synchronization)
7. [Health Monitoring](#health-monitoring)
8. [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud VM (24/7)                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Gmail Watcher    │  │ FileSystem       │                │
│  │ (Triage)         │  │ Watcher          │                │
│  └──────────────────┘  └──────────────────┘                │
│            │                     │                           │
│            v                     v                           │
│  ┌─────────────────────────────────────┐                   │
│  │ Cloud Drafts/ (Email replies,       │                   │
│  │  social posts, documents)           │                   │
│  └─────────────────────────────────────┘                   │
│            │                                                 │
│            │ Git Push (drafts only)                         │
│            v                                                 │
│  ┌─────────────────────────────────────┐                   │
│  │ Odoo Accounting (Optional)          │                   │
│  │  - Budget tracking                  │                   │
│  │  - Financial reports                │                   │
│  └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                        ║
                        ║ Git Sync (bidirectional)
                        ║
┌─────────────────────────────────────────────────────────────┐
│                    Local Machine                             │
│  ┌─────────────────────────────────────┐                   │
│  │ Approved/ Rejected/ (Your review)   │                   │
│  │  - Approve Cloud drafts             │                   │
│  │  - Execute sensitive actions        │                   │
│  └─────────────────────────────────────┘                   │
│            │                                                 │
│            v                                                 │
│  ┌─────────────────────────────────────┐                   │
│  │ Secrets (Local Only, Never Synced)  │                   │
│  │  - WhatsApp sessions                │                   │
│  │  - Banking credentials              │                   │
│  │  - Sensitive OAuth tokens           │                   │
│  └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Local Instance Requirements

- **OS**: macOS, Linux, or Windows WSL2
- **Python**: 3.12+ (3.13+ recommended)
- **Git**: 2.30+
- **uv**: 0.1.0+ (Python package manager)
- **Storage**: 5GB minimum for vault
- **Memory**: 2GB RAM minimum

### Cloud VM Requirements

- **OS**: Ubuntu 22.04 LTS
- **CPU**: 2 vCPUs minimum
- **RAM**: 4GB minimum (8GB recommended with Odoo)
- **Storage**: 40GB minimum (80GB recommended with Odoo)
- **Network**: Public IP, ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

**Recommended Cloud Providers**:
- DigitalOcean: $24/month (4GB RAM, 2 vCPUs, 80GB SSD)
- AWS EC2: t3.medium ($30/month)
- Linode: Shared CPU 4GB ($24/month)
- Hetzner: CX21 (€5.83/month, great value)

## Local Instance Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-username/personal-ai-employee.git
cd personal-ai-employee
```

### 2. Install Dependencies

**Using uv (recommended)**:
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

**Using pip**:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Instance Configuration
INSTANCE=local
TIER=platinum
VAULT_PATH=/Users/you/Documents/vault  # Absolute path to your vault

# Gmail Configuration (required)
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=/Users/you/.credentials/gmail-oauth.json
GMAIL_READONLY=false  # Local can send emails

# WhatsApp Configuration (Local only)
WHATSAPP_ENABLED=true
WHATSAPP_SESSION_PATH=/Users/you/.whatsapp-session

# Vault Sync
GIT_REMOTE=origin
GIT_BRANCH=main
SYNC_INTERVAL_MINUTES=15  # How often to sync with Cloud

# Email Alerts (optional but recommended)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_ALERT_RECIPIENT=alerts@example.com

# Health Monitoring
HEALTH_CHECK_INTERVAL=60  # seconds
```

### 4. Setup Gmail OAuth

```bash
# Run Gmail setup script
python scripts/setup_gmail.py

# Follow OAuth flow in browser
# Credentials saved to ~/.credentials/gmail-oauth.json
```

**Important**: Use an App Password if using Gmail with 2FA:
1. Go to Google Account → Security → App Passwords
2. Generate password for "Mail"
3. Use app password in `EMAIL_PASSWORD`

### 5. Initialize Vault

```bash
# Create vault directory
mkdir -p ~/Documents/vault
cd ~/Documents/vault

# Initialize as Git repository
git init
git remote add origin https://github.com/your-username/vault.git

# Create initial structure
mkdir -p {Needs_Action,Needs_Local,Cloud_Drafts,Approved,Rejected,Logs,Contacts,Documents,Expenses,Receipts,Budgets,Sync_Queue}

# Initial commit
git add .
git commit -m "Initial vault structure"
git push -u origin main
```

### 6. Start Local Instance

```bash
# Start all services
python src/main.py

# Or start individual services
python src/scheduler.py &  # Background scheduler
python src/watchers/filesystem_watcher.py &  # Filesystem watcher
python src/services/health_monitor.py &  # Health monitoring
```

## Cloud VM Setup

### 1. Provision Cloud VM

**DigitalOcean Example**:
```bash
# Create Droplet via UI or CLI
doctl compute droplet create ai-employee-cloud \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region sfo3 \
  --ssh-keys your-ssh-key-id \
  --enable-monitoring \
  --enable-ipv6

# Get IP address
doctl compute droplet list
```

**AWS EC2 Example**:
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --subnet-id subnet-xxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ai-employee-cloud}]'
```

### 2. Initial Server Setup

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt-get update && apt-get upgrade -y

# Install basic tools
apt-get install -y git curl wget build-essential

# Create deploy user (optional but recommended)
adduser deploy
usermod -aG sudo deploy
su - deploy
```

### 3. Run Automated Deployment

```bash
# Clone repository
git clone https://github.com/your-username/personal-ai-employee.git /opt/ai-employee
cd /opt/ai-employee

# Make deployment script executable
chmod +x deployment/cloud-deploy.sh

# Run deployment (installs Python, dependencies, systemd services)
sudo ./deployment/cloud-deploy.sh
```

The script will:
- ✅ Install Python 3.13 and uv
- ✅ Clone vault repository
- ✅ Install system dependencies
- ✅ Create `.env.cloud` template
- ✅ Setup systemd services (vault-sync, health-monitor, watchers)
- ✅ Configure log rotation
- ✅ Setup SSH keys for Git

### 4. Configure Cloud Environment

Edit `/opt/ai-employee/.env.cloud`:

```bash
# Instance Configuration
INSTANCE=cloud
TIER=platinum
VAULT_PATH=/opt/ai-employee/vault

# Gmail Configuration
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=/opt/ai-employee/.credentials/gmail-oauth.json
GMAIL_READONLY=true  # Cloud only reads/triages, doesn't send

# WhatsApp Configuration (DISABLED on cloud)
WHATSAPP_ENABLED=false  # Never enable on cloud!

# Vault Sync
GIT_REMOTE=origin
GIT_BRANCH=main
SYNC_INTERVAL_MINUTES=5  # More frequent sync on cloud

# Email Alerts
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=cloud-alerts@example.com
EMAIL_PASSWORD=your-app-password
EMAIL_ALERT_RECIPIENT=your-email@example.com

# Odoo Integration (if using)
ODOO_URL=https://odoo.yourdomain.com
ODOO_DATABASE=odoo
ODOO_API_KEY=your_odoo_api_key
```

### 5. Setup Git SSH Keys

```bash
# Generate SSH key for Cloud instance
ssh-keygen -t ed25519 -C "ai-employee-cloud" -f ~/.ssh/ai_employee_cloud

# Add to GitHub/GitLab
cat ~/.ssh/ai_employee_cloud.pub
# Copy and add to GitHub: Settings → SSH Keys

# Configure Git
git config --global user.name "AI Employee Cloud"
git config --global user.email "cloud@ai-employee.local"

# Test SSH connection
ssh -T git@github.com
```

### 6. Start Cloud Services

```bash
# Enable and start services
sudo systemctl enable vault-sync.service
sudo systemctl enable health-monitor.service
sudo systemctl enable gmail-watcher.service
sudo systemctl enable filesystem-watcher.service

sudo systemctl start vault-sync.service
sudo systemctl start health-monitor.service
sudo systemctl start gmail-watcher.service
sudo systemctl start filesystem-watcher.service

# Check status
sudo systemctl status vault-sync health-monitor gmail-watcher filesystem-watcher

# View logs
sudo journalctl -u vault-sync -f
sudo journalctl -u gmail-watcher -f
```

## Odoo Installation (Optional)

Professional accounting integration with Odoo Community Edition.

### 1. Install Odoo

```bash
cd /opt/ai-employee/deployment
sudo ./install-odoo.sh
```

This installs:
- PostgreSQL database
- Odoo Community Edition v17.0
- nginx reverse proxy
- Python dependencies

**Time**: ~15-20 minutes

### 2. Setup SSL Certificate

```bash
# Replace with your domain
sudo ./setup-ssl.sh odoo.yourdomain.com
```

**Prerequisites**:
- Domain pointing to your server IP
- Ports 80 and 443 open in firewall

### 3. Configure Odoo

1. Access Odoo: `https://odoo.yourdomain.com`
2. Create database: `odoo`
3. Set admin password (save this!)
4. Install **Accounting** module
5. Configure chart of accounts (see `/mcp-servers/odoo/config.json` for mappings)
6. Generate API key:
   - Settings → Users → Administrator
   - API Keys → Generate New Key
   - Copy for `.env.cloud`

### 4. Setup Automated Backups

```bash
sudo ./deployment/scripts/setup-cron-jobs.sh
```

Configures:
- Daily Odoo database backups (2 AM)
- Weekly health reports (Monday 8 AM)
- Monthly financial reports (1st of month, 9 AM)

### 5. Verify Installation

```bash
sudo ./deployment/scripts/verify-odoo-deployment.sh odoo.yourdomain.com
```

Runs 8 verification tests:
- Odoo service status
- PostgreSQL database
- nginx configuration
- SSL certificate
- HTTP endpoints
- Backup configuration
- Health monitoring
- Configuration files

**Expected**: All tests pass ✅

## Vault Synchronization

### Sync Strategy

- **Cloud → Local**: Drafts, triage results, monitoring data
- **Local → Cloud**: Approvals, rejections, offline work
- **Bidirectional**: Logs, contacts, documents (non-sensitive)
- **Local-Only**: Secrets, WhatsApp sessions, banking credentials

### Git Hooks

Pre-commit hook (`{vault}/.git/hooks/pre-commit`) runs:
1. **detect-secrets**: Scan for accidental secret commits
2. **Secret filtering**: Remove sensitive files from staging
3. **Work zone validation**: Ensure Cloud doesn't commit secrets

### Manual Sync

```bash
# Force immediate sync (Local)
python -c "from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/path/to/vault', 'local').sync('bidirectional')"

# Force immediate sync (Cloud)
ssh cloud-vm "cd /opt/ai-employee && \
  python -c \"from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/opt/ai-employee/vault', 'cloud').sync('bidirectional')\""
```

### Offline Resilience

**Automatic queue-based sync**:
- Changes commit locally when offline
- Queue items saved to `/Sync_Queue/`
- Auto-retry on network restore
- Zero data loss guaranteed

**Check queue status**:
```bash
ls -la vault/Sync_Queue/
# QUEUE_*.json files = pending sync
```

**Process queue manually**:
```bash
python -c "from src.services.vault_sync_service import VaultSyncService; \
  sync = VaultSyncService('/path/to/vault', 'local'); \
  print(sync.process_sync_queue())"
```

## Health Monitoring

### Check System Health

**Cloud**:
```bash
ssh cloud-vm
sudo journalctl -u health-monitor -n 50

# View health snapshot
python -c "from src.services.health_monitor import HealthMonitor; \
  hm = HealthMonitor('/opt/ai-employee/vault', 'cloud'); \
  snapshot = hm.collect_health_snapshot(); \
  print(f'Status: {snapshot.status}'); \
  print(f'Alerts: {snapshot.alerts}')"
```

**Local**:
```bash
# Check if Cloud is online
cat vault/Logs/sync.jsonl | grep "cloud" | tail -5

# Check health status
python -c "from src.services.health_monitor import HealthMonitor; \
  hm = HealthMonitor('/path/to/vault', 'local'); \
  hm.check_offline_escalation()"
```

### Email Alerts

**Configure SMTP** (`.env` or `.env.cloud`):
```bash
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=alerts@example.com
EMAIL_PASSWORD=app-specific-password
EMAIL_ALERT_RECIPIENT=you@example.com
```

**Alert Triggers**:
- ⚠️ Other instance offline >24 hours
- ⚠️ Disk space <5GB
- ⚠️ Service crash/restart
- ⚠️ Sync failure rate >20%

### Dashboard

View real-time status in `/vault/Dashboard.md`:
- Cloud/Local instance status
- Last sync time
- Pending queue items
- Health metrics
- Recent alerts

## Troubleshooting

### Common Issues

#### 1. Git Sync Fails with "permission denied"

**Cause**: SSH key not configured
**Fix**:
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add to GitHub
cat ~/.ssh/id_ed25519.pub  # Copy and add to GitHub

# Test connection
ssh -T git@github.com
```

#### 2. Secrets Blocked During Push

**Cause**: detect-secrets found potential secrets
**Fix**:
```bash
# View detected secrets
detect-secrets scan

# If false positive, add pragma to line:
# secret_value = "test"  # pragma: allowlist secret

# Re-run commit
git add .
git commit -m "your message"
```

#### 3. Cloud Can't Access Gmail

**Cause**: OAuth credentials not copied to Cloud
**Fix**:
```bash
# Copy from Local to Cloud (one-time)
scp ~/.credentials/gmail-oauth.json cloud-vm:/opt/ai-employee/.credentials/

# Set read-only on Cloud (.env.cloud)
GMAIL_READONLY=true
```

#### 4. Odoo Sync Failing

**Cause**: API key or URL incorrect
**Fix**:
```bash
# Test Odoo connection
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://odoo.yourdomain.com/api/health

# Check logs
tail -f vault/Logs/odoo_sync.jsonl

# Verify configuration
grep ODOO /opt/ai-employee/.env.cloud
```

#### 5. Health Monitor Not Alerting

**Cause**: Email configuration missing/incorrect
**Fix**:
```bash
# Test email configuration
python -c "from src.services.health_monitor import AlertManager; \
  am = AlertManager('/path/to/vault', email_enabled=True); \
  am.send_alert('test', 'info', 'Test alert', {})"

# Check logs
cat vault/Logs/alerts.jsonl | tail -10
```

#### 6. Services Not Starting on Boot

**Cause**: systemd services not enabled
**Fix**:
```bash
# Enable all services
sudo systemctl enable vault-sync health-monitor gmail-watcher filesystem-watcher

# Check which services are enabled
systemctl list-unit-files | grep ai-employee

# View service logs
sudo journalctl -u vault-sync -e
```

### Log Locations

- **Cloud Logs**: `/var/log/syslog`, `sudo journalctl -u <service>`
- **Application Logs**: `/vault/Logs/*.jsonl`
- **Odoo Logs**: `/var/log/odoo/odoo.log`
- **nginx Logs**: `/var/log/nginx/odoo-*.log`

### Performance Checks

```bash
# Check sync performance
cat vault/Logs/sync.jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# Should be <30s for 95% of syncs

# Check resource usage (Cloud)
ssh cloud-vm "htop"
# CPU: Should be <50% average
# RAM: Should be <80% of available
# Disk: Should have >10GB free
```

### Getting Help

1. **Check Documentation**: `/docs/troubleshooting-platinum.md`
2. **Review Logs**: `/vault/Logs/*.jsonl`
3. **Health Status**: `/vault/Dashboard.md`
4. **Run Verification**: `./deployment/scripts/verify-odoo-deployment.sh`
5. **GitHub Issues**: https://github.com/your-username/personal-ai-employee/issues

## Security Checklist

Before going to production:

- [ ] `.env` and `.env.cloud` not committed to Git
- [ ] SSH keys configured with passphrase
- [ ] Cloud VM firewall configured (ports 22, 80, 443 only)
- [ ] Gmail OAuth credentials secured (not world-readable)
- [ ] WhatsApp sessions never on Cloud VM
- [ ] Odoo admin password saved in password manager
- [ ] Email alerts configured and tested
- [ ] Backup cron jobs verified
- [ ] SSL certificates valid and auto-renewing
- [ ] detect-secrets pre-commit hook working

## Next Steps

1. **Test End-to-End**: Send test email, verify Cloud drafts, approve on Local
2. **Configure Trust Rules**: Add trusted contacts/patterns in `Company_Handbook.md`
3. **Setup Odoo Budgets**: Configure monthly budgets in Odoo
4. **Schedule Tasks**: Add weekly/monthly reports in `Company_Handbook.md`
5. **Monitor Performance**: Check `/vault/Dashboard.md` daily for first week

---

**Deployment Support**: See `/docs/troubleshooting-platinum.md` or create issue on GitHub

**Last Updated**: 2026-03-14 | **Version**: 0.4.0 (Platinum Tier)
