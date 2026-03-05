# Platinum Tier Deployment Guide

**Version**: 0.4.0 (Platinum Tier - Phase 1)
**Last Updated**: 2026-03-06
**Status**: Foundational components ready for deployment

## Overview

This guide provides step-by-step instructions for deploying the Platinum Tier foundational components to a Cloud VM and configuring bidirectional vault synchronization between Cloud and Local instances.

### What's Been Built

✅ **VaultSyncService** (T001-T028):
- Git-based bidirectional vault synchronization
- Automatic secret filtering using detect-secrets
- Conflict detection and resolution
- Complete audit logging
- systemd timer integration (5-minute sync interval)

✅ **ClaimManager** (T029-T044):
- Advisory file-based task locks
- Work-zone routing (Cloud vs Local capabilities)
- Task delegation with metadata
- 15-minute TTL with auto-expiry
- systemd timer integration (1-minute expiry check)

### What's NOT Built Yet

⏳ **HealthMonitor** (T050-T078): Watcher supervision, auto-restart, health snapshots
⏳ **Odoo Integration** (T094-T120): MCP server, expense sync, budget tracking
⏳ **Offline Resilience** (T121-T135): Offline queueing, escalation alerts

---

## Prerequisites

### Local Machine (Your Development Machine)

- ✅ Python 3.13+ installed
- ✅ Git repository initialized with remote
- ✅ All dependencies installed (`uv sync`)
- ✅ VaultSyncService and ClaimManager implemented
- ✅ Company_Handbook.md configured with work_zones and routing_rules

### Cloud VM Requirements

- **OS**: Ubuntu 22.04 LTS (or later)
- **CPU**: 2 cores minimum
- **RAM**: 4GB minimum
- **Disk**: 50GB minimum
- **Provider**: DigitalOcean / AWS EC2 / Linode / Any VPS
- **Network**: Static IP address, SSH access

### Git Repository

- GitHub/GitLab/Gitea repository created
- SSH keys configured for passwordless access
- Both Cloud and Local can push/pull

---

## Part 1: Cloud VM Provisioning

### Step 1: Create Cloud VM

**DigitalOcean Example**:
```bash
# Create Droplet via CLI
doctl compute droplet create ai-employee-cloud \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys <your-ssh-key-id>

# Get IP address
doctl compute droplet list
```

**AWS EC2 Example**:
```bash
# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name YourKeyPair \
  --security-groups ai-employee-sg
```

### Step 2: Initial Server Setup

SSH into your Cloud VM:

```bash
ssh root@<cloud-vm-ip>
```

Update system and install dependencies:

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.13+
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

# Install Git and build tools
apt install -y git build-essential libssl-dev libffi-dev

# Install systemd development headers (for health monitoring later)
apt install -y libsystemd-dev pkg-config

# Install detect-secrets dependencies
apt install -y python3-pip
```

### Step 3: Create AI Employee User

```bash
# Create dedicated user
useradd -m -d /opt/ai-employee -U -r -s /bin/bash aiemployee

# Set up sudo access (optional, for debugging)
usermod -aG sudo aiemployee

# Switch to aiemployee user
su - aiemployee
```

### Step 4: Clone Repository

As `aiemployee` user:

```bash
cd /opt/ai-employee

# Clone your repository (use SSH for passwordless access)
git clone git@github.com:YourUsername/Personal-AI-Employee-Hackathon-0.git .

# Or HTTPS with credentials
git clone https://github.com/YourUsername/Personal-AI-Employee-Hackathon-0.git .

# Checkout platinum branch
git checkout 004-platinum-tier-upgrade

# Verify files
ls -la
```

---

## Part 2: Cloud VM Configuration

### Step 1: Install Python Dependencies

```bash
# Install uv (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Install dependencies
cd /opt/ai-employee
uv sync

# Verify installation
uv run python --version
# Should show: Python 3.13+
```

### Step 2: Configure Environment

Create `.env.cloud` file:

```bash
cd /opt/ai-employee
nano .env.cloud
```

Add configuration:

```bash
# Instance Configuration
INSTANCE_NAME=cloud
VAULT_PATH=/opt/ai-employee
VAULT_SYNC_REMOTE=origin

# Development mode (set to false for production)
DEV_MODE=false
DRY_RUN=false

# Claim Management
CLAIM_TTL_MINUTES=15
CLAIM_EXPIRE_INTERVAL_SECONDS=60

# Logging
LOG_LEVEL=INFO

# Gmail Integration (Cloud has access to Gmail)
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=/opt/ai-employee/credentials.json
GMAIL_TOKEN_PATH=/opt/ai-employee/token.json

# WhatsApp Integration (Cloud does NOT have access - local only)
WHATSAPP_ENABLED=false

# Rate Limiting
RATE_LIMIT_STATE_FILE=/opt/ai-employee/Logs/rate_limit_state.json
```

**IMPORTANT**: Do NOT copy the following to cloud:
- WhatsApp session files
- Banking credentials
- OAuth tokens for sensitive services
- `.env` file from local (contains local secrets)

### Step 3: Configure Git for Vault Sync

```bash
# Configure Git user
git config --global user.name "AI Employee Cloud"
git config --global user.email "cloud@ai-employee.local"

# Set up SSH key for GitHub (passwordless push/pull)
ssh-keygen -t ed25519 -C "cloud@ai-employee.local" -f ~/.ssh/id_ed25519 -N ""

# Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy output and add to GitHub: Settings > SSH Keys > New SSH key
```

Test Git access:

```bash
ssh -T git@github.com
# Should see: Hi YourUsername! You've successfully authenticated
```

### Step 4: Initialize Vault Folders

Ensure Platinum Tier folders exist:

```bash
cd /opt/ai-employee

# Verify Platinum folders
ls -la Cloud_Drafts/ Needs_Local/ Claims/ Health/

# If missing, create them
mkdir -p Cloud_Drafts Needs_Local Claims Health

# Set permissions
chown -R aiemployee:aiemployee /opt/ai-employee
```

---

## Part 3: Deploy Systemd Services

### Step 1: Install Vault Sync Service

As `root`:

```bash
# Copy service files
cp /opt/ai-employee/deployment/systemd/vault-sync.service /etc/systemd/system/
cp /opt/ai-employee/deployment/systemd/vault-sync.timer /etc/systemd/system/

# Edit service file to use correct paths
nano /etc/systemd/system/vault-sync.service
```

Ensure paths are correct:
```ini
ExecStart=/opt/ai-employee/.venv/bin/python -m src.services.vault_sync_service sync --direction bidirectional --vault-path /opt/ai-employee --instance cloud
WorkingDirectory=/opt/ai-employee
EnvironmentFile=/opt/ai-employee/.env.cloud
User=aiemployee
```

### Step 2: Install Claim Expiry Service

```bash
# Copy service files
cp /opt/ai-employee/deployment/systemd/claim-expiry.service /etc/systemd/system/
cp /opt/ai-employee/deployment/systemd/claim-expiry.timer /etc/systemd/system/

# Edit service file
nano /etc/systemd/system/claim-expiry.service
```

Ensure paths are correct:
```ini
ExecStart=/opt/ai-employee/.venv/bin/python -m src.services.claim_manager expire --vault-path /opt/ai-employee --zone cloud
WorkingDirectory=/opt/ai-employee
EnvironmentFile=/opt/ai-employee/.env.cloud
User=aiemployee
```

### Step 3: Enable and Start Services

```bash
# Reload systemd
systemctl daemon-reload

# Enable services (start on boot)
systemctl enable vault-sync.timer
systemctl enable claim-expiry.timer

# Start timers
systemctl start vault-sync.timer
systemctl start claim-expiry.timer

# Check status
systemctl status vault-sync.timer
systemctl status claim-expiry.timer
```

### Step 4: Verify Services

```bash
# Check vault-sync timer
systemctl list-timers | grep vault-sync
# Should show: Next trigger in ~5 minutes

# Check claim-expiry timer
systemctl list-timers | grep claim-expiry
# Should show: Next trigger in ~1 minute

# Trigger manual sync to test
systemctl start vault-sync.service

# Check logs
journalctl -u vault-sync.service -n 50 --no-pager
```

---

## Part 4: Local Machine Configuration

### Step 1: Update Local Environment

Edit `.env` on your local machine:

```bash
# Instance Configuration
INSTANCE_NAME=local
VAULT_PATH=/path/to/your/local/vault
VAULT_SYNC_REMOTE=origin

# Local has access to ALL capabilities
GMAIL_ENABLED=true
WHATSAPP_ENABLED=true
```

### Step 2: Test Local Sync

```bash
# On local machine
cd /path/to/your/ai-employee

# Test sync
uv run python -m src.services.vault_sync_service sync --direction pull --instance local

# Check sync log
cat Logs/sync.jsonl | tail -1 | jq
```

### Step 3: Test Claim Management

```bash
# Test claim from local
uv run python -m src.services.claim_manager claim \
  --task-id TEST_CLAIM_001 \
  --zone local \
  --action-type test

# Check claim file
ls -la Claims/
cat Claims/TEST_CLAIM_001.claim.md

# Release claim
uv run python -m src.services.claim_manager release \
  --claim-id CLAIM_<timestamp>_TEST_CLAIM_001 \
  --zone local
```

---

## Part 5: Testing & Validation

### Test 1: Bidirectional Vault Sync

**On Local Machine**:

```bash
# Create test file
echo "Test from Local" > test-local.md

# Stage and sync
git add test-local.md
uv run python -m src.services.vault_sync_service sync --direction push --instance local

# Check sync log
cat Logs/sync.jsonl | tail -1 | jq
```

**On Cloud VM**:

```bash
# Wait 5 minutes for auto-sync, or trigger manually
systemctl start vault-sync.service

# Check if file received
ls -la test-local.md
cat test-local.md
# Should show: "Test from Local"
```

**On Cloud VM**:

```bash
# Create test file
echo "Test from Cloud" > test-cloud.md

# Sync
uv run python -m src.services.vault_sync_service sync --direction push --instance cloud
```

**On Local Machine**:

```bash
# Pull changes
uv run python -m src.services.vault_sync_service sync --direction pull --instance local

# Check if file received
cat test-cloud.md
# Should show: "Test from Cloud"
```

✅ **Success**: Bidirectional sync working!

### Test 2: Secret Filtering

**On Local Machine**:

```bash
# Create test secret file
echo "SECRET_KEY=abc123" > .env.test

# Try to sync
git add .env.test
uv run python -m src.services.vault_sync_service sync --direction push --instance local

# Check sync log
cat Logs/sync.jsonl | tail -1 | jq .secrets_blocked
# Should show: [".env.test"]
```

✅ **Success**: Secrets blocked from syncing!

### Test 3: Work-Zone Routing

**On Cloud VM**:

```bash
# Test routing
uv run python -m src.services.claim_manager route \
  --task-id EMAIL_TEST_001 \
  --action-type reply_draft

# Should show: "Task should be routed to: cloud"

uv run python -m src.services.claim_manager route \
  --task-id WHATSAPP_TEST_001 \
  --action-type send_message

# Should show: "Task should be routed to: local"
```

✅ **Success**: Routing rules working correctly!

### Test 4: Claim Expiry

**On Cloud VM**:

```bash
# Create test claim
uv run python -m src.services.claim_manager claim \
  --task-id EXPIRY_TEST \
  --zone cloud \
  --action-type test

# Wait 16 minutes (TTL is 15 minutes)
sleep 960

# Trigger expiry check (or wait for timer)
systemctl start claim-expiry.service

# Check logs
journalctl -u claim-expiry.service -n 20 --no-pager
# Should show: "Expired 1 stale claims"

# Verify claim file deleted
ls Claims/EXPIRY_TEST.claim.md
# Should show: No such file or directory
```

✅ **Success**: Claim expiry working!

---

## Part 6: Monitoring & Debugging

### Check Service Status

```bash
# On Cloud VM
systemctl status vault-sync.timer
systemctl status claim-expiry.timer

# List all timers
systemctl list-timers
```

### View Logs

```bash
# Vault sync logs
journalctl -u vault-sync.service -f

# Claim expiry logs
journalctl -u claim-expiry.service -f

# All AI Employee services
journalctl -u 'vault-sync*' -u 'claim-expiry*' -f
```

### Check Sync Activity

```bash
# View sync log
tail -f /opt/ai-employee/Logs/sync.jsonl | jq

# Count syncs
cat /opt/ai-employee/Logs/sync.jsonl | wc -l

# View recent syncs
cat /opt/ai-employee/Logs/sync.jsonl | tail -5 | jq
```

### Check Claims

```bash
# List active claims
ls -la /opt/ai-employee/Claims/

# View claim log
tail -f /opt/ai-employee/Logs/claims.jsonl | jq
```

### Check Git Status

```bash
cd /opt/ai-employee

# Check uncommitted changes
git status

# Check recent commits
git log --oneline -10

# Check remote sync status
git fetch
git status
```

---

## Part 7: Troubleshooting

### Issue: Vault Sync Fails with "Remote not found"

**Symptom**:
```
Error: Git pull failed: fatal: ambiguous argument 'HEAD..origin/004-platinum-tier-upgrade'
```

**Solution**:
```bash
# Fetch remote branches first
cd /opt/ai-employee
git fetch origin

# Verify branch exists
git branch -r | grep 004-platinum-tier-upgrade

# If branch doesn't exist on remote, push it
git push -u origin 004-platinum-tier-upgrade
```

### Issue: Secret Detected in Commit

**Symptom**:
```
Detect secrets........Failed
ERROR: Potential secrets about to be committed
```

**Solution**:
```bash
# Check which file has secrets
git status

# Remove sensitive files
git reset HEAD <file-with-secret>

# Add to .gitignore
echo "<file-pattern>" >> .gitignore

# Try commit again
git commit
```

### Issue: Claim Files Not Expiring

**Symptom**: Claim files persist beyond 15 minutes

**Solution**:
```bash
# Check timer status
systemctl status claim-expiry.timer

# Check if timer is running
systemctl list-timers | grep claim-expiry

# Manually trigger expiry
systemctl start claim-expiry.service

# Check logs
journalctl -u claim-expiry.service -n 50
```

### Issue: Git Merge Conflicts

**Symptom**: Sync fails with conflict status

**Solution**:
```bash
# On instance with conflict
cd /opt/ai-employee

# Check conflicted files
git status

# Resolve conflict manually
nano <conflicted-file>

# Or use ClaimManager's conflict resolution
uv run python -m src.services.vault_sync_service resolve \
  --conflict-id <conflict-id> \
  --strategy keep_local
```

---

## Part 8: Next Steps

### Immediate Next Steps

1. **Monitor for 24 Hours**:
   - Check sync logs every few hours
   - Verify no errors in journalctl
   - Confirm claims expire correctly

2. **Test Edge Cases**:
   - Disconnect Cloud VM network, verify offline resilience (future feature)
   - Create conflicting edits on both instances
   - Test secret filtering with real secrets

3. **Performance Baseline**:
   - Measure sync duration with 10, 50, 100 files
   - Check claim creation/expiry timing
   - Monitor disk usage

### Before Continuing Implementation

✅ **Validate Current Work**:
- [ ] Cloud VM syncing every 5 minutes reliably
- [ ] Claims expiring after 15 minutes
- [ ] No secrets leaking to Git remote
- [ ] Routing rules working correctly
- [ ] Both instances can push/pull

✅ **Document Observations**:
- Average sync duration: ___ seconds
- Claims created per day: ___
- Sync failures (if any): ___
- Performance issues: ___

### Future Phases

Once foundational components are validated:

**Phase 5: Health Monitoring** (T050-T078)
- HealthMonitor service
- Watcher supervision with auto-restart
- Health snapshots every 5 minutes
- Critical alert emails

**Phase 6: Odoo Integration** (T094-T120)
- Odoo Community installation
- MCP server for expense sync
- Budget tracking and alerts
- Monthly financial reports

**Phase 7: Offline Resilience** (T121-T135)
- Offline queueing
- Escalation alerts after 24 hours
- Graceful degradation

---

## Security Checklist

Before deploying to production:

- [ ] SSH key authentication only (disable password auth)
- [ ] Firewall configured (allow SSH, deny all else)
- [ ] Secrets in `.env.cloud` file (not in Git)
- [ ] `.gitignore` includes all secret patterns
- [ ] Pre-commit hook installed and working
- [ ] Vault path has correct permissions (aiemployee:aiemployee)
- [ ] systemd services run as aiemployee user (not root)
- [ ] Git remote uses SSH (not HTTPS with password)
- [ ] Cloud VM has no WhatsApp or banking credentials
- [ ] Regular backups of Cloud VM configured

---

## Support

**Documentation**:
- Specification: `specs/004-platinum-tier-upgrade/spec.md`
- Implementation Plan: `specs/004-platinum-tier-upgrade/plan.md`
- Tasks: `specs/004-platinum-tier-upgrade/tasks.md`
- API Contracts: `specs/004-platinum-tier-upgrade/contracts/`

**Logs**:
- Sync events: `Logs/sync.jsonl`
- Sync conflicts: `Logs/sync_conflicts.jsonl`
- Claim events: `Logs/claims.jsonl`
- System logs: `journalctl -u vault-sync.service`

**GitHub Issues**:
- Repository: https://github.com/DanishHaji/Personal-AI-Employee-Hackathon-0
- Branch: 004-platinum-tier-upgrade

---

**Deployment Guide Version**: 1.0.0
**Last Updated**: 2026-03-06
**Status**: Ready for Phase 1 deployment testing
