# Troubleshooting Guide - Platinum Tier

Common issues and solutions for Platinum Tier dual work zone deployment.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Vault Sync Issues](#vault-sync-issues)
3. [Cloud Instance Problems](#cloud-instance-problems)
4. [Local Instance Problems](#local-instance-problems)
5. [Odoo Integration Issues](#odoo-integration-issues)
6. [Email & Notification Issues](#email--notification-issues)
7. [Performance Problems](#performance-problems)
8. [Secret Detection Failures](#secret-detection-failures)

## Quick Diagnostics

### Check Overall System Health

```bash
# Local instance
cat vault/Dashboard.md

# Cloud instance (SSH)
ssh cloud-vm "cat /opt/ai-employee/vault/Dashboard.md"
```

### View Recent Logs

```bash
# Sync log (last 10 events)
tail -10 vault/Logs/sync.jsonl | jq

# Health log
tail -10 vault/Logs/health.jsonl | jq

# Alerts
tail -10 vault/Logs/alerts.jsonl | jq
```

### Check Service Status (Cloud)

```bash
ssh cloud-vm "sudo systemctl status vault-sync health-monitor gmail-watcher filesystem-watcher"
```

## Vault Sync Issues

### Problem: "Git push rejected - secrets detected"

**Symptoms**:
```
ERROR: Potential secrets about to be committed to git repo!
Secret Type: Secret Keyword
Location: file.py:42
```

**Cause**: detect-secrets found potential secrets in staged files

**Solution**:
```bash
# Option 1: If it's a false positive, add pragma
# In the file at the reported line:
secret_value = "test_key_123"  # pragma: allowlist secret

# Option 2: Add file to .gitignore if it shouldn't be tracked
echo "path/to/sensitive/file" >> .gitignore
git rm --cached path/to/sensitive/file

# Option 3: Remove the secret and use environment variable
# Replace hardcoded secret with: os.getenv("SECRET_NAME")
```

### Problem: "Sync fails with 'conflict detected'"

**Symptoms**:
```
SyncResult(status='conflict', conflicts_detected=2)
```

**Cause**: Both Cloud and Local modified the same file

**Solution**:
```bash
# View conflicts
cat vault/Logs/sync_conflicts.jsonl | tail -5 | jq

# Manual resolution
cd vault
git status  # Shows conflicted files

# Edit conflicted files, remove conflict markers
# <<<<<<< HEAD
# =======
# >>>>>>> remote

# Mark as resolved
git add conflicted_file.md
git commit -m "Resolve sync conflict"

# Resume sync
python -c "from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/path/to/vault', 'local').sync('bidirectional')"
```

### Problem: "Offline for >1 hour, changes not syncing"

**Symptoms**:
- Sync queue growing: `ls vault/Sync_Queue/ | wc -l` shows many files
- Last sync timestamp old in Dashboard.md

**Cause**: Network connectivity issues or Git authentication failure

**Solution**:
```bash
# Check network connectivity
ping -c 3 8.8.8.8

# Test Git SSH
ssh -T git@github.com

# Process queue manually
python -c "from src.services.vault_sync_service import VaultSyncService; \
  sync = VaultSyncService('/path/to/vault', 'local'); \
  results = sync.process_sync_queue(); \
  print(f'Synced: {results[\"synced\"]}, Failed: {results[\"failed\"]}')"

# Check for errors
tail -20 vault/Logs/sync.jsonl | jq 'select(.status == "error")'
```

### Problem: "Queue items stuck in 'failed' status"

**Symptoms**:
```bash
cat vault/Sync_Queue/QUEUE_*.json | jq '.status' | grep failed
```

**Cause**: Persistent sync error (bad credentials, network, etc.)

**Solution**:
```bash
# View failed item details
cat vault/Sync_Queue/QUEUE_*.json | jq 'select(.status == "failed")'

# Check last error
cat vault/Sync_Queue/QUEUE_*.json | jq '.last_error'

# Fix underlying issue (credentials, network, etc.)

# Reset failed items to pending (will retry)
for file in vault/Sync_Queue/QUEUE_*.json; do
  jq '.status = "pending" | .retry_count = 0' "$file" > "$file.tmp"
  mv "$file.tmp" "$file"
done

# Process queue
python -c "from src.services.vault_sync_service import VaultSyncService; \
  sync = VaultSyncService('/path/to/vault', 'local'); \
  sync.process_sync_queue()"
```

## Cloud Instance Problems

### Problem: "Cloud services not starting on boot"

**Symptoms**:
```bash
ssh cloud-vm "sudo systemctl status vault-sync"
# Shows: inactive (dead)
```

**Cause**: Services not enabled or configuration error

**Solution**:
```bash
ssh cloud-vm << 'EOF'
# Enable services
sudo systemctl enable vault-sync health-monitor gmail-watcher filesystem-watcher

# Start services
sudo systemctl start vault-sync health-monitor gmail-watcher filesystem-watcher

# Check status
sudo systemctl status vault-sync health-monitor gmail-watcher filesystem-watcher

# View logs if failing
sudo journalctl -u vault-sync -n 50
EOF
```

### Problem: "Cloud can't access Gmail"

**Symptoms**:
```
GmailAuthenticationError: OAuth credentials not found
```

**Cause**: OAuth credentials not copied to Cloud VM

**Solution**:
```bash
# Copy credentials from Local to Cloud (one-time)
scp ~/.credentials/gmail-oauth.json cloud-vm:/opt/ai-employee/.credentials/

# Set proper permissions
ssh cloud-vm "chmod 600 /opt/ai-employee/.credentials/gmail-oauth.json"

# Verify .env.cloud has correct path
ssh cloud-vm "grep GMAIL_CREDENTIALS /opt/ai-employee/.env.cloud"

# Should show: GMAIL_CREDENTIALS_PATH=/opt/ai-employee/.credentials/gmail-oauth.json

# Restart gmail-watcher
ssh cloud-vm "sudo systemctl restart gmail-watcher"
```

### Problem: "Cloud drafts not appearing in Local vault"

**Symptoms**:
- Cloud creates drafts in `/Cloud_Drafts/`
- Drafts not syncing to Local

**Cause**: Vault sync not running or Git push failing

**Solution**:
```bash
# Check Cloud sync status
ssh cloud-vm "sudo journalctl -u vault-sync -n 20"

# Manually trigger sync from Cloud
ssh cloud-vm "cd /opt/ai-employee && \
  python -c 'from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService(\"/opt/ai-employee/vault\", \"cloud\").sync(\"push\")'"

# Check for Git errors
ssh cloud-vm "cd /opt/ai-employee/vault && git status"

# Pull on Local
cd vault && git pull origin main
```

## Local Instance Problems

### Problem: "WhatsApp watcher failing"

**Symptoms**:
```
WhatsAppSessionError: Session not found
```

**Cause**: WhatsApp session expired or not initialized

**Solution**:
```bash
# Re-initialize WhatsApp session
python scripts/setup_whatsapp.py

# Scan QR code with phone
# Session saved to ~/.whatsapp-session/

# Restart watcher
pkill -f whatsapp_watcher
python src/watchers/whatsapp_watcher.py &
```

### Problem: "Local not receiving email alerts"

**Symptoms**:
- Cloud offline >24 hours
- No email received

**Cause**: Email configuration incorrect or missing

**Solution**:
```bash
# Check email configuration in .env
grep EMAIL .env

# Test email sending
python -c "from src.services.health_monitor import AlertManager; \
  am = AlertManager('/path/to/vault', email_enabled=True); \
  am.send_alert('test', 'critical', 'Test email alert', {})"

# Check alerts log
tail vault/Logs/alerts.jsonl | jq

# For Gmail with 2FA, use App Password:
# 1. Google Account → Security → App Passwords
# 2. Generate password for "Mail"
# 3. Use in EMAIL_PASSWORD (not your regular password)
```

## Odoo Integration Issues

### Problem: "Odoo expenses not syncing"

**Symptoms**:
```bash
tail vault/Logs/odoo_sync.jsonl | jq 'select(.status == "failed")'
```

**Cause**: API authentication error or network issue

**Solution**:
```bash
# Test Odoo connection
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://odoo.yourdomain.com/api/health

# Check credentials in .env.cloud
ssh cloud-vm "grep ODOO /opt/ai-employee/.env.cloud"

# Verify API key in Odoo:
# Settings → Users → Administrator → API Keys

# Test sync manually
ssh cloud-vm "cd /opt/ai-employee && \
  python -c 'from src.services.expense_service import ExpenseService; \
  es = ExpenseService(\"/opt/ai-employee/vault\", \
    odoo_url=\"https://odoo.yourdomain.com\", \
    odoo_api_key=\"YOUR_KEY\", odoo_database=\"odoo\"); \
  print(es.get_budget_status_from_odoo(\"2026-03\"))'"
```

### Problem: "Odoo service not starting"

**Symptoms**:
```bash
ssh cloud-vm "sudo systemctl status odoo"
# Shows: failed
```

**Cause**: PostgreSQL not running or configuration error

**Solution**:
```bash
ssh cloud-vm << 'EOF'
# Check PostgreSQL
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql

# Check Odoo configuration
sudo cat /etc/odoo.conf | grep -E "db_host|db_port|db_user|db_password"

# Check Odoo logs
sudo tail -50 /var/log/odoo/odoo.log

# Restart Odoo
sudo systemctl restart odoo

# Check port
sudo netstat -tlnp | grep 8069
EOF
```

### Problem: "Budget warnings not creating alerts"

**Symptoms**:
- Budget exceeds 80% but no alert in `/Needs_Action/`

**Cause**: Budget monitoring not running or Odoo connection failed

**Solution**:
```bash
# Manually check budget warnings
ssh cloud-vm "cd /opt/ai-employee && \
  python -c 'from src.services.expense_service import ExpenseService; \
  es = ExpenseService(\"/opt/ai-employee/vault\", \
    odoo_url=\"https://odoo.yourdomain.com\", \
    odoo_api_key=\"YOUR_KEY\", odoo_database=\"odoo\"); \
  warnings = es.check_budget_warnings(\"2026-03\"); \
  print(f\"Warnings: {len(warnings)}\"); \
  for w in warnings: print(w)'"

# Check alerts directory
ls vault/Needs_Action/BUDGET_ALERT_*

# Verify scheduler is running monthly report task
ssh cloud-vm "sudo systemctl status scheduler"
```

## Email & Notification Issues

### Problem: "Emails sent but not in Sent folder"

**Symptoms**:
- Confirmation in logs: "Email sent successfully"
- Not appearing in Gmail Sent folder

**Cause**: Gmail API sent vs IMAP sent folder sync

**Solution**:
```bash
# This is expected behavior - Gmail API sends don't always appear in IMAP Sent

# Verify in audit log
cat vault/Logs/audit.jsonl | jq 'select(.action_type == "email_send")'

# Check Gmail web interface - should be in Sent there

# If needed, manually sync:
# Gmail Settings → Labels → Sent → "Show in IMAP"
```

### Problem: "Gmail rate limit exceeded"

**Symptoms**:
```
GmailAPIError: 429 - Rate limit exceeded
```

**Cause**: Too many API calls in short period

**Solution**:
```bash
# Check watcher configuration
cat config/watchers.yaml | grep -A 5 gmail

# Increase check interval (default: 120s)
# Edit config/watchers.yaml:
gmail_watcher:
  check_interval: 300  # 5 minutes instead of 2

# Restart watcher
ssh cloud-vm "sudo systemctl restart gmail-watcher"

# Monitor API usage
cat vault/Logs/gmail.jsonl | jq '.api_calls' | tail -20
```

## Performance Problems

### Problem: "Sync taking >30 seconds"

**Symptoms**:
```bash
cat vault/Logs/sync.jsonl | jq '.duration_ms' | tail -20
# Shows: >30000 (30+ seconds)
```

**Cause**: Large files, slow network, or many files changed

**Solution**:
```bash
# Check vault size
du -sh vault/

# Find large files
find vault/ -type f -size +10M -exec ls -lh {} \;

# Move large files to separate tracked location
# Don't sync receipts/attachments if very large

# Check network speed
ssh cloud-vm "speedtest-cli"

# Compress Git repository
cd vault
git gc --aggressive --prune=now

# Check Git pack file size
du -sh .git/objects/pack/
```

### Problem: "High CPU usage on Cloud VM"

**Symptoms**:
```bash
ssh cloud-vm "top"
# Python processes using >50% CPU
```

**Cause**: Watchers checking too frequently or processing large data

**Solution**:
```bash
# Check watcher intervals
ssh cloud-vm "cat /opt/ai-employee/config/watchers.yaml"

# Increase intervals
# Edit and restart services

# Check for stuck processes
ssh cloud-vm "ps aux | grep python | grep -v grep"

# Kill and restart if stuck
ssh cloud-vm "sudo systemctl restart gmail-watcher filesystem-watcher"

# Monitor resource usage
ssh cloud-vm "htop"
```

## Secret Detection Failures

### Problem: "Valid code flagged as secret"

**Symptoms**:
```
Secret Type: Secret Keyword
Location: tests/test_auth.py:15
```

**Cause**: Test data or example code contains secret-like patterns

**Solution**:
```python
# Add pragma comment to line:
test_api_key = "sk-test-123456"  # pragma: allowlist secret

# Or add to .secrets.baseline
detect-secrets scan --update .secrets.baseline

# Commit updated baseline
git add .secrets.baseline
git commit -m "Update secrets baseline"
```

### Problem: "Pre-commit hook not running"

**Symptoms**:
- Secrets committed without detection
- No "Detect secrets..." message during commit

**Cause**: Hook not installed or not executable

**Solution**:
```bash
# Re-install pre-commit hooks
pre-commit install

# Test hook
pre-commit run detect-secrets --all-files

# Check hook is executable
ls -la .git/hooks/pre-commit

# Make executable if needed
chmod +x .git/hooks/pre-commit
```

## Getting Help

If you've tried the above solutions and still have issues:

1. **Run validation script**:
   ```bash
   ./deployment/scripts/validate-secrets.sh
   ./deployment/scripts/verify-odoo-deployment.sh odoo.yourdomain.com
   ```

2. **Collect diagnostic information**:
   ```bash
   # System info
   python --version
   git --version
   uv --version

   # Service status
   sudo systemctl status vault-sync health-monitor gmail-watcher

   # Recent logs (last 50 lines each)
   tail -50 vault/Logs/sync.jsonl
   tail -50 vault/Logs/health.jsonl
   tail -50 vault/Logs/alerts.jsonl

   # Queue status
   ls -la vault/Sync_Queue/
   ```

3. **Check GitHub Issues**: https://github.com/your-username/personal-ai-employee/issues

4. **Review Documentation**:
   - `/docs/monitoring.md` - Monitoring and metrics
   - `/deployment/README.md` - Deployment guide
   - `/specs/004-platinum-tier-upgrade/spec.md` - Architecture spec

---

**Last Updated**: 2026-03-14 | **Version**: 0.4.0 (Platinum Tier)
