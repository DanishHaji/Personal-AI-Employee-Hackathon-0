# AI Employee Dashboard

**Last Updated**: 2026-03-14 10:00:00 UTC

## System Status

| Component | Status | Last Check |
|-----------|--------|------------|
| Local Instance | 🟢 Healthy | 2026-03-14 10:00:00 |
| Cloud Instance | 🟢 Healthy | 2026-03-14 09:59:45 |
| Vault Sync | 🟢 Synced | 2026-03-14 09:58:30 |
| Health Monitor | 🟢 Running | 2026-03-14 09:59:55 |

## Work Zones

### Local Instance (🏠)

- **Status**: Online
- **Instance ID**: `local`
- **Capabilities**: Approvals, WhatsApp, Banking, Email Send
- **Last Sync**: 2 minutes ago (2026-03-14 09:58:30)
- **Sync Direction**: Bidirectional
- **Queue Items**: 0 pending
- **Uptime**: 24h 15m
- **Resource Usage**:
  - CPU: 15%
  - Memory: 2.1 GB / 8 GB (26%)
  - Disk: 42.5 GB free (85%)

### Cloud Instance (☁️)

- **Status**: Online
- **Instance ID**: `cloud`
- **Capabilities**: Email Triage, Drafts, Document Analysis, Odoo Integration
- **Last Sync**: 1 minute ago (2026-03-14 09:59:00)
- **Sync Direction**: Bidirectional
- **Queue Items**: 0 pending
- **Uptime**: 7d 3h 22m
- **Resource Usage**:
  - CPU: 8%
  - Memory: 1.4 GB / 4 GB (35%)
  - Disk: 28.3 GB free (70%)

## Vault Sync Status

| Metric | Value | Target |
|--------|-------|--------|
| Last Successful Sync | 2 minutes ago | <5 minutes |
| Sync Duration (Latest) | 1.25s | <5s |
| Sync Duration (P95) | 3.2s | <5s |
| Conflicts (Last 24h) | 0 | 0 |
| Failed Syncs (Last 24h) | 0 | 0 |
| Queue Backlog | 0 items | 0 items |

## Recent Activity (Last 24h)

### Email Processing

- **Emails Triaged**: 15
- **Drafts Created**: 8
- **Emails Sent**: 5
- **Average Triage Time**: 12s

### Communication

- **WhatsApp Messages Sent**: 12
- **Social Media Drafts**: 3
- **Calendar Invites**: 2

### Financial

- **Expenses Recorded**: 7
- **Expenses Synced to Odoo**: 7
- **Budget Alerts**: 1 (Software: 85% used)

### Documents

- **Documents Generated**: 3
- **Meeting Notes Created**: 2

### Approvals

- **Items Awaiting Approval**: 2
  - `/Needs_Action/EMAIL_DRAFT_20260314_001.md` (Email to client)
  - `/Needs_Action/DOCUMENT_DRAFT_20260314_003.md` (Proposal)
- **Approvals Processed**: 5
- **Rejections**: 0

## Service Status

### Local Services

| Service | Status | Uptime |
|---------|--------|--------|
| WhatsApp Watcher | 🟢 Running | 24h 15m |
| Filesystem Watcher | 🟢 Running | 24h 15m |
| Health Monitor | 🟢 Running | 24h 15m |

### Cloud Services (systemd)

| Service | Status | Uptime | Last Restart |
|---------|--------|--------|--------------|
| vault-sync | 🟢 Running | 7d 3h 22m | 2026-03-07 06:38:00 |
| health-monitor | 🟢 Running | 7d 3h 22m | 2026-03-07 06:38:00 |
| gmail-watcher | 🟢 Running | 7d 3h 22m | 2026-03-07 06:38:00 |
| filesystem-watcher | 🟢 Running | 7d 3h 22m | 2026-03-07 06:38:00 |

## Alerts (Last 7 days)

### Active Alerts

- ⚠️ **Budget Warning** - Software budget at 85% (Used: $425 of $500) - 2026-03-14 09:30:00

### Resolved Alerts (Last 7 days)

- 🟢 **Sync Delay** - Vault sync delayed by 8 minutes (resolved) - 2026-03-12 14:22:00
- 🟢 **Service Restart** - gmail-watcher restarted automatically (resolved) - 2026-03-10 03:15:00

## Performance Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Email Triage Time (avg) | 12s | <30s | 🟢 |
| Draft Generation Time (avg) | 45s | <60s | 🟢 |
| Sync Duration (p95) | 3.2s | <5s | 🟢 |
| Queue Processing Time (avg) | 38s | <60s | 🟢 |
| Approval Turnaround (avg) | 2.1h | <4h | 🟢 |
| Odoo Sync Time (avg) | 6s | <10s | 🟢 |

## Network Status

- **Connectivity**: 🟢 Online
- **Last Network Test**: 2026-03-14 09:59:50
- **Latency to Cloud**: 45ms
- **Git Remote Reachable**: Yes
- **Odoo Server Reachable**: Yes

## Security

- **Secret Scan Status**: 🟢 Passed (last scan: 2026-03-14 09:00:00)
- **Secrets Blocked (Last 7 days)**: 0
- **Failed Login Attempts**: 0
- **API Key Rotations Due**: None

## Capacity & Trends

### Vault Size

- **Total Size**: 1.2 GB
- **Growth Rate**: +15 MB/day
- **Estimated Days Until 80% Full**: >300 days

### Log Files

- **Total Log Size**: 245 MB
- **Oldest Log**: 2025-12-15 (90 days ago)
- **Auto-Cleanup**: Enabled (>90 days)

### Queue Trends

- **Max Queue Depth (7 days)**: 3 items
- **Average Queue Processing Time**: 38s
- **Queue Abandonment Rate**: 0%

## Quick Actions

### Manual Sync

```bash
# Local → Cloud
python -c "from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/path/to/vault', 'local').sync('push')"

# Cloud → Local
python -c "from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/path/to/vault', 'local').sync('pull')"

# Bidirectional
python -c "from src.services.vault_sync_service import VaultSyncService; \
  VaultSyncService('/path/to/vault', 'local').sync('bidirectional')"
```

### Process Queue

```bash
python -c "from src.services.vault_sync_service import VaultSyncService; \
  sync = VaultSyncService('/path/to/vault', 'local'); \
  results = sync.process_sync_queue(); \
  print(f'Synced: {results[\"synced\"]}, Failed: {results[\"failed\"]}')"
```

### Health Check

```bash
python -c "from src.services.health_monitor import HealthMonitor; \
  hm = HealthMonitor('/path/to/vault'); \
  hm.run_health_check()"
```

### View Logs

```bash
# Recent sync events
tail -10 vault/Logs/sync.jsonl | jq

# Recent health checks
tail -10 vault/Logs/health.jsonl | jq

# Active alerts
cat vault/Logs/alerts.jsonl | jq 'select(.resolved == false)'
```

## System Information

- **Version**: 0.4.0 (Platinum Tier)
- **Deployment**: Dual Work Zone (Cloud + Local)
- **Vault Path (Local)**: `/Users/you/vault`
- **Vault Path (Cloud)**: `/opt/ai-employee/vault`
- **Git Remote**: `git@github.com:your-username/personal-ai-employee-vault.git`
- **Odoo Instance**: `https://odoo.yourdomain.com`
- **Python Version**: 3.13+
- **Timezone**: America/Los_Angeles

---

**Monitoring Guide**: See `/docs/monitoring.md` for detailed monitoring instructions.
**Troubleshooting**: See `/docs/troubleshooting-platinum.md` for common issues and solutions.
**Deployment Guide**: See `/deployment/README.md` for setup instructions.
