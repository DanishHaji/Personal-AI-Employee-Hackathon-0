# Monitoring Guide - Platinum Tier

Comprehensive monitoring for dual work zone deployment (Cloud + Local instances).

## Table of Contents

1. [Dashboard Overview](#dashboard-overview)
2. [Health Monitoring](#health-monitoring)
3. [Sync Status](#sync-status)
4. [Alert Management](#alert-management)
5. [Resource Usage](#resource-usage)
6. [Service Status](#service-status)
7. [Log Analysis](#log-analysis)
8. [Performance Metrics](#performance-metrics)
9. [Troubleshooting](#troubleshooting)

## Dashboard Overview

The main dashboard (`vault/Dashboard.md`) provides real-time visibility into system health.

### Dashboard Location

```bash
# Local instance
cat vault/Dashboard.md

# Cloud instance (SSH)
ssh cloud-vm "cat /opt/ai-employee/vault/Dashboard.md"
```

### Dashboard Structure

```markdown
# AI Employee Dashboard

**Last Updated**: 2026-03-14 09:45:23 UTC

## System Status

| Component | Status | Last Check |
|-----------|--------|------------|
| Local Instance | 🟢 Healthy | 2026-03-14 09:45:20 |
| Cloud Instance | 🟢 Healthy | 2026-03-14 09:45:15 |
| Vault Sync | 🟢 Synced | 2026-03-14 09:44:30 |
| Health Monitor | 🟢 Running | 2026-03-14 09:45:00 |

## Work Zones

### Local Instance (🏠)
- **Status**: Online
- **Capabilities**: Approvals, WhatsApp, Banking, Email Send
- **Last Sync**: 2 minutes ago
- **Queue Items**: 0 pending

### Cloud Instance (☁️)
- **Status**: Online
- **Capabilities**: Email Triage, Drafts, Odoo Integration
- **Last Sync**: 3 minutes ago
- **Queue Items**: 0 pending

## Recent Activity (Last 24h)

- Emails Triaged: 15
- Drafts Created: 8
- Approvals Processed: 5
- WhatsApp Messages Sent: 12
- Expenses Synced to Odoo: 7
- Documents Generated: 3

## Alerts (Last 7 days)

- 🟢 No critical alerts
- ⚠️ 2 warnings (budget threshold)
```

### Status Indicators

- 🟢 **Healthy**: All systems operational
- 🟡 **Warning**: Non-critical issue detected
- 🔴 **Critical**: Immediate attention required
- ⚫ **Offline**: Instance not responding

## Health Monitoring

### Health Check System

The Health Monitor (`src/services/health_monitor.py`) performs automated checks every 5 minutes:

```python
# Checks performed:
- Instance connectivity (ping test)
- Vault sync status (last sync time)
- Service status (systemd units)
- Disk space (>10% free required)
- Queue health (items not stuck)
- Log file growth (detect issues)
```

### Health Log Format

Location: `vault/Logs/health.jsonl`

```jsonl
{
  "timestamp": "2026-03-14T09:45:00Z",
  "instance": "cloud",
  "check_type": "system_health",
  "status": "healthy",
  "checks": {
    "disk_space": {"status": "ok", "free_gb": 42.5, "percent_free": 85},
    "memory": {"status": "ok", "free_gb": 2.1, "percent_free": 52},
    "cpu": {"status": "ok", "load_avg": 0.35, "percent_used": 15},
    "services": {
      "vault-sync": "running",
      "health-monitor": "running",
      "gmail-watcher": "running"
    }
  },
  "duration_ms": 234
}
```

### Viewing Health Status

```bash
# Last 10 health checks
tail -10 vault/Logs/health.jsonl | jq

# Check specific instance
cat vault/Logs/health.jsonl | jq 'select(.instance == "cloud")' | tail -5

# Find unhealthy checks
cat vault/Logs/health.jsonl | jq 'select(.status != "healthy")'

# Check disk space trends
cat vault/Logs/health.jsonl | jq '.checks.disk_space.free_gb' | tail -20
```

### Health Alerts

Alerts are triggered when:

| Condition | Severity | Action |
|-----------|----------|--------|
| Instance offline >1 hour | Warning | Log to alerts.jsonl |
| Instance offline >24 hours | Critical | Email + Slack notification |
| Disk space <10% | Critical | Email notification |
| Queue items stuck >1 hour | Warning | Retry automatically |
| Service crashed | Critical | Attempt auto-restart |
| Sync failing >5 attempts | Critical | Email notification |

## Sync Status

### Sync Monitoring

Vault sync logs track all synchronization events.

**Location**: `vault/Logs/sync.jsonl`

```jsonl
{
  "timestamp": "2026-03-14T09:44:30Z",
  "instance": "local",
  "direction": "bidirectional",
  "status": "success",
  "files_synced": 3,
  "conflicts_detected": 0,
  "duration_ms": 1250,
  "network_available": true,
  "queue_processed": 0,
  "git_hash_before": "a1b2c3d",
  "git_hash_after": "e4f5g6h"
}
```

### Sync Status Commands

```bash
# Last sync time and status
tail -1 vault/Logs/sync.jsonl | jq '{timestamp, status, duration_ms}'

# Sync success rate (last 24 hours)
cat vault/Logs/sync.jsonl | \
  jq -r 'select(.timestamp > "'$(date -u -d '24 hours ago' --iso-8601=seconds)'") | .status' | \
  sort | uniq -c

# Average sync duration
cat vault/Logs/sync.jsonl | jq '.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'

# Failed syncs with errors
cat vault/Logs/sync.jsonl | jq 'select(.status == "failed")'

# Conflicts detected
cat vault/Logs/sync.jsonl | jq 'select(.conflicts_detected > 0)'
```

### Sync Queue Status

Monitor pending sync items when offline.

```bash
# Queue item count
ls vault/Sync_Queue/ | wc -l

# Queue item details
cat vault/Sync_Queue/QUEUE_*.json | jq

# Items by status
cat vault/Sync_Queue/QUEUE_*.json | jq '.status' | sort | uniq -c

# Failed items
cat vault/Sync_Queue/QUEUE_*.json | jq 'select(.status == "failed")'

# Items by priority
cat vault/Sync_Queue/QUEUE_*.json | jq '.priority' | sort -rn
```

### Sync Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Sync duration | <5 seconds (p95) | >30 seconds |
| Sync frequency | Every 5 minutes | >15 minutes gap |
| Conflict rate | <1% of syncs | >5% of syncs |
| Queue processing | <60 seconds | >5 minutes |
| Network detection | <5 seconds | >30 seconds |

## Alert Management

### Alert Log Format

**Location**: `vault/Logs/alerts.jsonl`

```jsonl
{
  "alert_id": "ALERT_20260314_094500_001",
  "timestamp": "2026-03-14T09:45:00Z",
  "alert_type": "budget_warning",
  "severity": "warning",
  "instance": "cloud",
  "message": "Software budget at 85% (Used: $425 of $500)",
  "details": {
    "category": "software",
    "budget": 500.00,
    "spent": 425.00,
    "percent": 0.85
  },
  "notification_sent": true,
  "notification_channels": ["vault"],
  "resolved": false,
  "resolved_at": null
}
```

### Viewing Alerts

```bash
# All unresolved alerts
cat vault/Logs/alerts.jsonl | jq 'select(.resolved == false)'

# Critical alerts (last 7 days)
cat vault/Logs/alerts.jsonl | \
  jq 'select(.severity == "critical" and .timestamp > "'$(date -u -d '7 days ago' --iso-8601=seconds)'")'

# Alerts by type
cat vault/Logs/alerts.jsonl | jq '.alert_type' | sort | uniq -c

# Email notification status
cat vault/Logs/alerts.jsonl | jq 'select(.notification_sent == false)'
```

### Alert Severity Levels

| Severity | Description | Response Time | Notification |
|----------|-------------|---------------|--------------|
| **info** | Informational only | No action required | Vault log only |
| **warning** | Non-critical issue | Review within 24h | Vault log + Dashboard |
| **critical** | Requires immediate attention | Review within 1h | Email + Vault + Dashboard |
| **emergency** | System failure | Immediate action | Email + SMS + Vault |

### Alert Categories

- **budget_warning**: Budget threshold exceeded (80%, 100%)
- **instance_offline**: Instance not responding >24 hours
- **sync_failure**: Vault sync failing repeatedly
- **service_crash**: systemd service stopped unexpectedly
- **disk_space_low**: Disk space below 10%
- **queue_stuck**: Queue items failing repeatedly
- **secrets_detected**: Secrets blocked from Git commit
- **conflict_detected**: Manual intervention needed for vault conflict

## Resource Usage

### Local Instance Monitoring

```bash
# CPU and memory usage
top -bn1 | grep "python"

# Disk space
df -h vault/

# Network bandwidth (if monitoring enabled)
iftop -i eth0

# Process count
ps aux | grep "ai-employee" | wc -l
```

### Cloud Instance Monitoring

```bash
# SSH into Cloud VM
ssh cloud-vm

# Check resource usage
htop

# Disk usage by directory
du -sh /opt/ai-employee/*

# Service resource consumption
systemctl status vault-sync --no-pager
systemctl status health-monitor --no-pager
systemctl status gmail-watcher --no-pager

# Memory usage
free -h

# Disk I/O
iostat -x 1 5
```

### Resource Thresholds

| Resource | Warning | Critical | Action |
|----------|---------|----------|--------|
| **CPU** | >70% sustained | >90% sustained | Investigate process load |
| **Memory** | >80% used | >95% used | Check for memory leaks |
| **Disk** | <20% free | <10% free | Clean up logs/files |
| **Network** | >80% bandwidth | >95% bandwidth | Check for sync issues |

### Resource Optimization

**Reduce CPU usage:**
```bash
# Increase watcher check intervals
# Edit config/watchers.yaml:
gmail_watcher:
  check_interval: 300  # 5 minutes (default: 120s)

filesystem_watcher:
  check_interval: 60   # 1 minute (default: 30s)
```

**Reduce disk usage:**
```bash
# Compress Git repository
cd vault
git gc --aggressive --prune=now

# Remove old log files (>90 days)
find vault/Logs -name "*.jsonl" -mtime +90 -delete

# Archive old queue items
find vault/Sync_Queue -name "QUEUE_*.json" -mtime +7 -delete
```

**Reduce memory usage:**
```bash
# Restart services to clear memory
ssh cloud-vm "sudo systemctl restart vault-sync health-monitor gmail-watcher"
```

## Service Status

### Local Instance Services

Services run as user processes (not systemd on Local).

```bash
# Check if watchers running
ps aux | grep "watcher"

# Start watchers manually
python src/watchers/whatsapp_watcher.py &
python src/watchers/filesystem_watcher.py &

# Kill watchers
pkill -f whatsapp_watcher
pkill -f filesystem_watcher
```

### Cloud Instance Services

Services managed by systemd.

```bash
# Check all AI Employee services
ssh cloud-vm "sudo systemctl status vault-sync health-monitor gmail-watcher filesystem-watcher"

# Individual service status
ssh cloud-vm "sudo systemctl status vault-sync"

# View service logs
ssh cloud-vm "sudo journalctl -u vault-sync -n 50 --no-pager"

# Restart service
ssh cloud-vm "sudo systemctl restart vault-sync"

# Enable service to start on boot
ssh cloud-vm "sudo systemctl enable vault-sync"

# Check service startup time
ssh cloud-vm "systemd-analyze blame | grep ai-employee"
```

### Service Health Checks

Each service reports health independently:

```jsonl
{
  "timestamp": "2026-03-14T09:45:00Z",
  "service": "vault-sync",
  "status": "running",
  "uptime_seconds": 86400,
  "last_action": "sync_completed",
  "last_action_time": "2026-03-14T09:44:30Z",
  "errors_last_hour": 0,
  "restarts_last_day": 0
}
```

## Log Analysis

### Log File Locations

| Log File | Purpose | Retention |
|----------|---------|-----------|
| `vault/Logs/audit.jsonl` | All actions and decisions | 90 days |
| `vault/Logs/sync.jsonl` | Vault sync events | 30 days |
| `vault/Logs/health.jsonl` | Health checks | 14 days |
| `vault/Logs/alerts.jsonl` | System alerts | 30 days |
| `vault/Logs/gmail.jsonl` | Email processing | 30 days |
| `vault/Logs/odoo_sync.jsonl` | Odoo integration | 30 days |

### Common Log Queries

**Find errors in last 24 hours:**
```bash
find vault/Logs -name "*.jsonl" -mtime -1 -exec \
  jq 'select(.status == "error" or .severity == "error")' {} \;
```

**Track action by user/agent:**
```bash
cat vault/Logs/audit.jsonl | jq 'select(.performed_by == "cloud_agent")'
```

**Performance analysis:**
```bash
# Sync durations over time
cat vault/Logs/sync.jsonl | jq '[.timestamp, .duration_ms]' | \
  awk '{print $1, $2}' | \
  gnuplot -e "set terminal dumb; plot '-' using 2 with lines"
```

**Email processing volume:**
```bash
cat vault/Logs/gmail.jsonl | \
  jq -r '.timestamp[0:10]' | \
  sort | uniq -c
```

### Log Rotation

Logs are automatically rotated to prevent disk space issues:

```bash
# Manual log cleanup (keeps last 30 days)
find vault/Logs -name "*.jsonl" -mtime +30 -delete

# Archive old logs
find vault/Logs -name "*.jsonl" -mtime +7 -exec gzip {} \;
```

## Performance Metrics

### Key Performance Indicators (KPIs)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Email triage time | <30 seconds | 12 seconds | 🟢 |
| Draft generation time | <60 seconds | 45 seconds | 🟢 |
| Sync duration (p95) | <5 seconds | 3.2 seconds | 🟢 |
| Queue processing time | <60 seconds | 38 seconds | 🟢 |
| Approval turnaround | <4 hours | 2.1 hours | 🟢 |
| Odoo sync time | <10 seconds | 6 seconds | 🟢 |

### Performance Monitoring Commands

**Email Processing:**
```bash
# Average email triage time
cat vault/Logs/gmail.jsonl | \
  jq '.processing_time_ms' | \
  awk '{sum+=$1; n++} END {print sum/n}'
```

**Sync Performance:**
```bash
# P95 sync duration
cat vault/Logs/sync.jsonl | \
  jq '.duration_ms' | \
  sort -n | \
  awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'
```

**Queue Processing:**
```bash
# Average queue processing time
cat vault/Logs/sync.jsonl | \
  jq 'select(.queue_processed > 0) | .duration_ms' | \
  awk '{sum+=$1; n++} END {print sum/n}'
```

### Performance Bottlenecks

**Identify slow operations:**
```bash
# Find slowest syncs
cat vault/Logs/sync.jsonl | jq 'select(.duration_ms > 5000)'

# Find large file transfers
cat vault/Logs/sync.jsonl | jq 'select(.files_synced > 10)'

# Find operations with conflicts
cat vault/Logs/sync.jsonl | jq 'select(.conflicts_detected > 0)'
```

**Network latency:**
```bash
# Measure Git push/pull latency
ssh cloud-vm "cd /opt/ai-employee/vault && \
  time git pull origin main && \
  time git push origin main"
```

## Troubleshooting

### Quick Diagnostic Script

```bash
#!/bin/bash
# Run comprehensive diagnostics

echo "=== System Status ==="
cat vault/Dashboard.md

echo -e "\n=== Recent Health Checks ==="
tail -5 vault/Logs/health.jsonl | jq

echo -e "\n=== Recent Sync Events ==="
tail -5 vault/Logs/sync.jsonl | jq

echo -e "\n=== Unresolved Alerts ==="
cat vault/Logs/alerts.jsonl | jq 'select(.resolved == false)'

echo -e "\n=== Queue Status ==="
ls vault/Sync_Queue/ | wc -l
echo "pending queue items"

echo -e "\n=== Cloud Service Status ==="
ssh cloud-vm "sudo systemctl status vault-sync health-monitor gmail-watcher --no-pager"

echo -e "\n=== Resource Usage ==="
df -h vault/
free -h
```

### Common Issues

**Issue: Dashboard not updating**
```bash
# Check if health monitor running
ps aux | grep health_monitor

# Manually trigger health check
python -c "from src.services.health_monitor import HealthMonitor; \
  hm = HealthMonitor('/path/to/vault'); \
  hm.run_health_check()"
```

**Issue: Sync metrics missing**
```bash
# Check sync log exists and is writable
ls -la vault/Logs/sync.jsonl

# Check recent sync events
tail vault/Logs/sync.jsonl
```

**Issue: Alerts not appearing in Dashboard**
```bash
# Check if AlertManager logging
tail vault/Logs/alerts.jsonl

# Verify Dashboard.md is writable
ls -la vault/Dashboard.md
```

### Monitoring Best Practices

1. **Regular Dashboard Checks**: Review dashboard at least once daily
2. **Alert Response**: Respond to critical alerts within 1 hour
3. **Log Review**: Weekly review of error patterns in logs
4. **Performance Tracking**: Monitor sync duration trends weekly
5. **Resource Planning**: Check disk space trends monthly
6. **Service Health**: Verify all services running after system restarts
7. **Network Monitoring**: Track offline incidents and patterns
8. **Queue Hygiene**: Clean up old queue items weekly

### Automated Monitoring Setup

**Cron job for daily health report:**
```bash
# Add to crontab: 0 9 * * * /path/to/daily-health-report.sh
#!/bin/bash
{
  echo "Daily Health Report - $(date)"
  echo "========================"
  cat vault/Dashboard.md
  echo -e "\n=== Unresolved Alerts ==="
  cat vault/Logs/alerts.jsonl | jq 'select(.resolved == false)'
  echo -e "\n=== Failed Syncs (Last 24h) ==="
  cat vault/Logs/sync.jsonl | \
    jq 'select(.status == "failed" and .timestamp > "'$(date -u -d '24 hours ago' --iso-8601=seconds)'")'
} | mail -s "AI Employee Health Report" user@example.com
```

## Dashboard Update API

The system automatically updates `vault/Dashboard.md` every 5 minutes. To manually trigger an update:

```python
from src.services.health_monitor import HealthMonitor

hm = HealthMonitor("/path/to/vault")
hm.update_dashboard()
```

Dashboard structure is defined in `src/services/health_monitor.py:update_dashboard()` method.

---

**Last Updated**: 2026-03-14 | **Version**: 0.4.0 (Platinum Tier)

For troubleshooting specific issues, see: `/docs/troubleshooting-platinum.md`
