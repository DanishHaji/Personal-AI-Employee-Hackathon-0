# Quickstart Guide: Platinum Tier - Always-On Cloud + Local Executive

**Feature**: 004-platinum-tier-upgrade
**Prerequisites**: Gold Tier (003-gold-tier-upgrade) fully implemented and tested

## Overview

This guide provides step-by-step instructions for implementing and testing Platinum Tier features. Implementation follows a phased approach prioritizing foundational capabilities first.

---

## Phase 1: Vault Synchronization (P2 - Foundation)

**Goal**: Enable Git-based vault sync with secret filtering

**Why First**: Vault sync is the communication backbone between Cloud and Local zones. Without it, distributed operation is impossible.

### Implementation Steps

1. **Setup Git Repository**
   ```bash
   cd vault/
   git init
   git add .
   git commit -m "Initial vault commit (Gold Tier)"
   git remote add origin <your-git-repo-url>
   git push -u origin main
   ```

2. **Install Secret Detection**
   ```bash
   pip install detect-secrets pre-commit

   # Create .pre-commit-config.yaml
   cat > .pre-commit-config.yaml <<EOF
   repos:
     - repo: https://github.com/Yelp/detect-secrets
       rev: v1.5.0
       hooks:
         - id: detect-secrets
           args: ['--baseline', '.secrets.baseline']
   EOF

   pre-commit install
   ```

3. **Configure Secret Filters**
   ```bash
   # Add to .gitignore
   cat >> vault/.gitignore <<EOF
   # Platinum Tier - Secret Filtering
   .env
   .env.*
   *_credentials.json
   whatsapp_session/
   banking/
   *.pem
   *.key
   oauth_tokens_sensitive.json
   .odoo_token
   EOF
   ```

4. **Implement VaultSyncService**
   - Create: `src/services/vault_sync_service.py`
   - Implement methods from contract: `sync()`, `filter_secrets()`, `resolve_conflict()`
   - Add logging to `vault/Logs/sync.jsonl`

5. **Test Vault Sync**
   ```bash
   # Test sync locally
   python -m src.services.vault_sync_service sync --direction bidirectional

   # Verify secrets filtered
   cat vault/Logs/sync.jsonl | grep "secrets_filtered"
   ```

### Acceptance Test

```python
def test_vault_sync_filters_secrets():
    # Create .env file
    with open("vault/.env", "w") as f:
        f.write("SECRET_KEY=abc123")

    # Attempt sync
    sync_service = VaultSyncService(vault_path="vault/")
    result = sync_service.sync(direction="push")

    # Verify .env was filtered
    assert ".env" in result.secrets_blocked
    assert result.secrets_filtered == 1

    # Verify .env not in remote
    # (manual verification on remote Git repo)
```

**Success Criteria**: Vault syncs bidirectionally in <30s, zero secrets reach remote

---

## Phase 2: Work-Zone Specialization (P1 - Core Feature)

**Goal**: Implement Cloud-Local routing and claim management

### Implementation Steps

1. **Configure Work Zones**
   ```yaml
   # Add to vault/Company_Handbook.md
   work_zones:
     cloud:
       enabled: true
       capabilities:
         - email_triage
         - draft_responses
         - schedule_monitoring
       restrictions:
         - no_whatsapp_access
         - no_banking_credentials

     local:
       enabled: true
       capabilities:
         - approve_cloud_drafts
         - whatsapp_send
         - banking_transactions
       exclusive_secrets:
         - whatsapp_session
         - banking_credentials

   routing_rules:
     - pattern: "EMAIL_*"
       action: "reply_draft"
       zone: "cloud"
       requires_approval: true

     - pattern: "WHATSAPP_*"
       action: "send_message"
       zone: "local"
       requires_approval: false
   ```

2. **Create Vault Folders**
   ```bash
   mkdir -p vault/Cloud_Drafts
   mkdir -p vault/Needs_Local
   mkdir -p vault/Claims
   mkdir -p vault/Health
   ```

3. **Implement ClaimManager**
   - Create: `src/services/claim_manager.py`
   - Implement from contract: `claim_task()`, `release_claim()`, `check_claim()`, `route_task()`, `delegate_to_local()`

4. **Update Executor**
   - Modify `src/services/executor_service.py` to check claims before processing
   - Add zone-based routing logic
   - Implement delegation for local-only tasks

### Acceptance Test

```python
def test_cloud_drafts_email_local_approves():
    # Setup: Cloud instance processes email
    claim_manager_cloud = ClaimManager(instance="cloud")

    # Cloud claims and drafts response
    claim = claim_manager_cloud.claim_task(
        task_id="EMAIL_TEST_001",
        zone="cloud"
    )

    # Cloud creates draft
    draft_path = "vault/Cloud_Drafts/DRAFT_EMAIL_TEST_001.md"
    # ... create draft file ...

    # Sync vault (Git push/pull simulation)
    sync_service.sync(direction="bidirectional")

    # Local instance comes online
    claim_manager_local = ClaimManager(instance="local")

    # Local detects draft, moves to Pending_Approval
    # ... move file logic ...

    # Human approves
    # ... approval logic ...

    # Local executes send
    assert os.path.exists("vault/Done/EMAIL_TEST_001.md")
```

**Success Criteria**: Cloud drafts responses, Local approves and executes, no zone violations

---

## Phase 3: Cloud Deployment & Health Monitoring (P3)

**Goal**: Deploy to Cloud VM with 24/7 operation and health monitoring

### Implementation Steps

1. **Provision Cloud VM**
   ```bash
   # DigitalOcean/AWS/Linode
   # Ubuntu 22.04, 2 CPU, 4GB RAM, 50GB disk

   # SSH into VM
   ssh root@your-vm-ip
   ```

2. **Install Dependencies**
   ```bash
   # Update system
   apt update && apt upgrade -y

   # Install Python 3.12+
   apt install python3.12 python3.12-venv python3-pip git -y

   # Install systemd development headers
   apt install libsystemd-dev -y

   # Clone repository
   cd /opt
   git clone <your-repo-url> ai-employee
   cd ai-employee

   # Setup Python environment
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install psutil systemd-watchdog
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env.cloud
   nano .env.cloud
   # Set:
   # INSTANCE_NAME=cloud
   # VAULT_PATH=/opt/ai-employee/vault
   # (do NOT add WhatsApp/banking credentials - cloud restrictions)
   ```

4. **Create Systemd Services**

   **Health Monitor** (`/etc/systemd/system/health-monitor.service`):
   ```ini
   [Unit]
   Description=AI Employee Health Monitor
   After=network.target

   [Service]
   Type=notify
   NotifyAccess=main
   WatchdogSec=90s
   ExecStart=/opt/ai-employee/venv/bin/python -m src.services.health_monitor watchdog
   Restart=on-failure
   RestartSec=10s
   WorkingDirectory=/opt/ai-employee
   EnvironmentFile=/opt/ai-employee/.env.cloud
   User=aiemployee

   [Install]
   WantedBy=multi-user.target
   ```

   **Gmail Watcher** (`/etc/systemd/system/gmail-watcher.service`):
   ```ini
   [Unit]
   Description=AI Employee Gmail Watcher
   After=network.target

   [Service]
   Type=simple
   ExecStart=/opt/ai-employee/venv/bin/python -m src.watchers.gmail_watcher
   Restart=on-failure
   RestartSec=5s
   WorkingDirectory=/opt/ai-employee
   EnvironmentFile=/opt/ai-employee/.env.cloud
   User=aiemployee

   [Install]
   WantedBy=multi-user.target
   ```

   **Vault Sync Timer** (`/etc/systemd/system/vault-sync.timer`):
   ```ini
   [Unit]
   Description=Vault Sync Timer (every 5 minutes)

   [Timer]
   OnBootSec=1min
   OnUnitActiveSec=5min
   AccuracySec=10s

   [Install]
   WantedBy=timers.target
   ```

5. **Start Services**
   ```bash
   # Create user
   useradd -m -d /opt/ai-employee -U -r -s /bin/bash aiemployee
   chown -R aiemployee:aiemployee /opt/ai-employee

   # Enable and start services
   systemctl daemon-reload
   systemctl enable health-monitor.service gmail-watcher.service vault-sync.timer
   systemctl start health-monitor.service gmail-watcher.service vault-sync.timer

   # Check status
   systemctl status health-monitor.service
   systemctl status gmail-watcher.service
   ```

6. **Implement HealthMonitor**
   - Create: `src/services/health_monitor.py`
   - Implement from contract: `collect_health_snapshot()`, `check_watcher_health()`, `start_watchdog()`, `restart_watcher()`

### Acceptance Test

```bash
# Test watcher auto-restart
sudo systemctl stop gmail-watcher.service
sleep 90  # Wait for watchdog to detect crash
systemctl status gmail-watcher.service
# Should show: Active (running) - restarted by watchdog

# Check health snapshot
cat vault/Health/cloud_*.health.json | tail -1 | jq
# Should show all watchers running

# Verify 24/7 operation
uptime
# Should show days/weeks of uptime
```

**Success Criteria**: 99% uptime over 7 days, watchdog auto-restarts crashed watchers, health snapshots every 5 minutes

---

## Phase 4: Odoo Integration (P5)

**Goal**: Cloud-hosted Odoo accounting with expense sync

### Implementation Steps

1. **Install Odoo Community**
   ```bash
   # On Cloud VM
   sudo apt install postgresql-14
   sudo useradd -m -d /opt/odoo -U -r -s /bin/bash odoo

   sudo su - odoo
   git clone https://github.com/odoo/odoo.git --depth 1 --branch 18.0
   cd odoo
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Odoo**
   ```bash
   sudo nano /etc/odoo.conf
   # Set database, admin password, etc.

   # Start Odoo
   sudo systemctl enable odoo.service
   sudo systemctl start odoo.service
   ```

3. **Setup HTTPS (Let's Encrypt)**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   sudo certbot --nginx -d odoo.cloud.example.com
   ```

4. **Implement Odoo MCP Server**
   - Create: `mcp-servers/odoo/server.py`
   - Implement tools from contract: `odoo_create_expense`, `odoo_get_budget_status`, `odoo_generate_financial_report`
   - Configure category mapping

5. **Test Expense Sync**
   ```python
   # Create expense in AI Employee
   expense_service.create_expense(
       amount=100.00,
       category="software",
       vendor="Test Vendor"
   )

   # Sync to Odoo
   odoo_mcp.sync_all_expenses(since_date="2026-03-04")

   # Verify in Odoo
   # Open https://odoo.cloud.example.com
   # Check Accounting > Journal Entries
   ```

### Acceptance Test

```python
def test_odoo_expense_sync():
    # Create expense
    expense_id = create_test_expense(amount=50.00, category="software")

    # Sync to Odoo
    result = odoo_mcp.create_expense(
        expense_id=expense_id,
        amount=50.00,
        category="software",
        vendor="Test Vendor",
        date="2026-03-04"
    )

    # Verify success
    assert result["success"] == True
    assert "odoo_entry_id" in result

    # Verify in Odoo (API query)
    odoo_entry = odoo_api.search_read(
        model="account.move.line",
        domain=[["ref", "=", expense_id]]
    )
    assert len(odoo_entry) == 1
    assert odoo_entry[0]["debit"] == 50.00
```

**Success Criteria**: 100% of expenses sync to Odoo within 2 minutes, monthly reports generated automatically

---

## Phase 5: Offline Resilience (P4)

**Goal**: Cloud and Local operate independently when disconnected

### Implementation Steps

1. **Implement Offline Queueing**
   - Modify VaultSyncService to queue changes during outage
   - Create `/vault/Sync_Queue/` for pending changes

2. **Test Network Failure**
   ```bash
   # On Cloud VM, simulate network outage
   sudo iptables -A OUTPUT -p tcp --dport 443 -j DROP

   # Verify Cloud continues operating (creates drafts locally)
   # Wait 5 minutes
   # Restore network
   sudo iptables -D OUTPUT -p tcp --dport 443 -j DROP

   # Verify sync resumes automatically
   cat vault/Logs/sync.jsonl | tail -5
   ```

3. **Implement Escalation Alerts**
   - If Local offline >24 hours, Cloud sends summary email
   - Configure alert thresholds in Company_Handbook

### Acceptance Test

```python
def test_offline_resilience():
    # Disconnect network (mock)
    sync_service.set_network_available(False)

    # Cloud creates 10 drafts while offline
    for i in range(10):
        create_cloud_draft(f"DRAFT_{i}")

    # Verify drafts queued locally
    queue_files = os.listdir("vault/Sync_Queue/")
    assert len(queue_files) >= 10

    # Reconnect network
    sync_service.set_network_available(True)

    # Trigger sync
    result = sync_service.sync(direction="push")

    # Verify all drafts synced
    assert result.status == "success"
    assert result.files_changed >= 10
```

**Success Criteria**: Zero data loss during 24-hour outage, automatic sync on reconnect

---

## Complete End-to-End Test Scenario

**Scenario**: Email arrives while Local offline → Cloud drafts → Local approves → send

### Steps

1. **Setup**: Local machine is off, Cloud VM running 24/7

2. **Event**: Email arrives at 10:00 AM
   ```
   From: client@example.com
   Subject: Meeting Request
   Body: Can we meet next week?
   ```

3. **Cloud Processing**:
   - Gmail watcher detects email (within 1 minute)
   - Creates EMAIL entity in `/Needs_Action/`
   - ClaimManager routes to cloud zone (email triage)
   - Cloud claims task
   - Drafts response in `/Cloud_Drafts/DRAFT_EMAIL_xxx.md`
   - Syncs vault to Git (every 5 minutes)

4. **Local Comes Online** (6 hours later, 4:00 PM):
   - VaultSyncService pulls latest changes
   - Detects new draft in `/Cloud_Drafts/`
   - Moves draft to `/Pending_Approval/`
   - Notifies user (Dashboard update)

5. **User Approval** (4:05 PM):
   - Reviews draft in Obsidian
   - Moves to `/Approved/`

6. **Local Execution**:
   - Executor detects approved draft
   - Claims task (local zone)
   - Sends email via Gmail API (using local credentials)
   - Moves to `/Done/`
   - Syncs vault

7. **Verification**:
   - Client receives email at 4:06 PM
   - Audit log shows complete flow
   - Health report shows Cloud uptime: 100%, Local: came online at 4:00 PM

### Expected Metrics

- **Email Triage Latency**: <1 minute (Cloud detection)
- **Draft Creation**: ~30 seconds (Cloud processing)
- **Sync to Git**: <5 minutes (next timer trigger)
- **Local Approval Time**: ~5 minutes (human review)
- **Email Send**: <10 seconds (after approval)
- **Total Time**: 6 hours 6 minutes (mostly Local offline time)

**Without Platinum Tier**: Email would wait 6+ hours until Local comes online (no 24/7 operation)

---

## Troubleshooting

### Issue: Secrets Leaked to Cloud

**Symptom**: `.env` file appears in remote Git repo

**Solution**:
```bash
# Remove from Git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch vault/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all

# Rotate leaked secrets immediately
```

### Issue: Vault Sync Conflicts

**Symptom**: `SyncConflict` entries in `sync_conflicts.jsonl`

**Solution**:
```bash
# List conflicts
cat vault/Logs/sync_conflicts.jsonl | jq '.[] | select(.resolved == false)'

# Resolve manually
python -m src.services.vault_sync_service resolve --conflict-id CONFLICT_xxx --strategy keep_local
```

### Issue: Watchdog Not Restarting Watchers

**Symptom**: Watcher crashed but not restarted

**Check**:
```bash
# Check watchdog logs
journalctl -u health-monitor.service -n 50

# Check systemd watchdog status
systemctl show health-monitor.service | grep Watchdog

# Manually restart
systemctl restart health-monitor.service
```

---

## Next Steps

After completing Quickstart:

1. **Run `/sp.tasks`**: Generate detailed implementation tasks
2. **Implement in order**: P2 (Vault Sync) → P1 (Work-Zone) → P3 (Cloud Deploy) → P5 (Odoo) → P4 (Offline)
3. **Test each phase**: Use acceptance tests before moving to next phase
4. **Monitor health**: Check `vault/Health/` snapshots daily during rollout
5. **Production Deployment**: Start with non-critical emails for first week

---

**Implementation Time Estimate**:
- Phase 1 (Vault Sync): 8-10 hours
- Phase 2 (Work-Zone): 12-15 hours
- Phase 3 (Cloud Deploy): 10-12 hours
- Phase 4 (Odoo): 8-10 hours
- Phase 5 (Offline): 6-8 hours
- **Total**: 44-55 hours (within 60-hour Platinum Tier scope)

---

*Quickstart complete. Ready for `/sp.tasks` to generate detailed implementation tasks.*
