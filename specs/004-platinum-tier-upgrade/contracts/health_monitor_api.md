# Health Monitor API Contract

**Feature**: 004-platinum-tier-upgrade
**Component**: Health Monitoring & Watchdog Service
**Version**: 1.0.0

## Overview

Defines the internal API contract for system health monitoring, watcher supervision, and alerting for 24/7 Cloud deployment.

**Implementation**: Python service (`src/services/health_monitor.py`)
**Dependencies**: `psutil` (v7.2.2), `systemd-watchdog`

---

## HealthMonitor

### `collect_health_snapshot() -> HealthStatus`

Collects current system health metrics.

**Returns**: `HealthStatus` object

**Behavior**:
1. Checks PID status of all configured watchers
2. Collects resource metrics (CPU, memory, disk)
3. Checks vault sync status
4. Determines overall health status
5. Saves snapshot to `vault/Health/{instance}_{timestamp}.health.json`

**Status Determination**:
```python
if any_watcher_crashed or disk_usage > 90 or memory_usage > 90:
    status = "critical"
elif any_watcher_errors > 10/hour or disk_usage > 80:
    status = "degraded"
else:
    status = "healthy"
```

**Example**:
```python
health_monitor = HealthMonitor(instance="cloud")
health = health_monitor.collect_health_snapshot()

print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_seconds}s")
print(f"Watchers running: {len([w for w in health.watchers.values() if w['status'] == 'running'])}")
```

---

### `check_watcher_health(watcher_name: str) -> WatcherHealth`

Checks health of a specific watcher process.

**Parameters**:
- `watcher_name` (str): Watcher identifier (e.g., `"gmail_watcher"`)

**Returns**: `WatcherHealth` object

**Behavior**:
1. Loads expected PID from watcher registry
2. Checks if process is running (`psutil.pid_exists()`)
3. Collects process metrics (CPU, memory, uptime)
4. Checks error count from logs
5. Returns health status

**Example**:
```python
watcher_health = health_monitor.check_watcher_health("gmail_watcher")
if watcher_health.status != "running":
    print(f"Watcher down! Last seen: {watcher_health.last_check}")
```

---

### `start_watchdog() -> None`

Starts the watchdog background process.

**Behavior**:
1. Loads watcher configuration
2. Starts monitoring loop (every 60 seconds)
3. For each watcher:
   - Check if process is running
   - If crashed: attempt auto-restart
   - If 3+ consecutive failures: send alert
4. Logs all events to `vault/Logs/health.jsonl`

**Systemd Integration**:
```python
# Notifies systemd watchdog every 30s
sd_notify("WATCHDOG=1")
```

**Example**:
```python
health_monitor.start_watchdog()
# Runs indefinitely, monitors watchers every 60s
```

---

### `restart_watcher(watcher_name: str) -> bool`

Attempts to restart a crashed watcher.

**Parameters**:
- `watcher_name` (str): Watcher to restart

**Returns**: `True` if restart successful, `False` otherwise

**Behavior**:
1. Kills existing process (if zombie)
2. Starts new process via systemd (`systemctl restart {watcher}.service`)
3. Waits 5 seconds for startup
4. Checks if process is running
5. Logs restart event

**Retry Logic**:
- Max 3 restart attempts within 10 minutes
- Exponential backoff: 1s, 2s, 4s
- After 3 failures: escalate to alert

**Example**:
```python
success = health_monitor.restart_watcher("gmail_watcher")
if success:
    print("Watcher restarted successfully")
else:
    print("Restart failed, alerting admin")
```

---

### `generate_daily_report() -> HealthReport`

Generates daily health summary report.

**Returns**: `HealthReport` object

**Behavior**:
1. Aggregates health snapshots from past 24 hours
2. Calculates uptime percentage
3. Summarizes watcher events (starts, crashes, restarts)
4. Summarizes vault sync stats
5. Identifies alerts triggered
6. Saves report to `vault/Documents/HEALTH_REPORT_{date}.md`

**Example**:
```python
report = health_monitor.generate_daily_report()
print(f"Uptime: {report.uptime_percent}%")
print(f"Watcher crashes: {report.watcher_crashes}")
print(f"Alerts: {report.alerts_triggered}")
```

---

## AlertManager

### `send_alert(alert_type: str, message: str, severity: str) -> None`

Sends alert notification via configured channels.

**Parameters**:
- `alert_type` (str): Alert category (e.g., `"watcher_crash"`, `"disk_space"`)
- `message` (str): Alert message
- `severity` (str): `"info"`, `"warning"`, `"critical"`

**Behavior**:
1. Checks alert configuration for enabled channels
2. Formats message with timestamp, severity, instance
3. Sends via configured channels:
   - Email (via Gmail API)
   - Webhook (HTTP POST to configured URL)
4. Logs alert to `vault/Logs/alerts.jsonl`

**Rate Limiting**:
- Max 10 alerts per hour (prevents spam)
- Critical alerts bypass rate limit

**Example**:
```python
alert_manager = AlertManager()
alert_manager.send_alert(
    alert_type="watcher_crash",
    message="Gmail watcher crashed 3 times consecutively",
    severity="critical"
)
```

---

### `check_disk_space() -> DiskStatus`

Monitors disk space and triggers alerts if thresholds exceeded.

**Returns**: `DiskStatus` object

**Behavior**:
1. Checks disk usage (`psutil.disk_usage()`)
2. If >90%: triggers critical alert
3. If >80%: triggers warning alert
4. If >80%: auto-rotates old logs to free space

**Example**:
```python
disk_status = alert_manager.check_disk_space()
if disk_status.usage_percent > 80:
    print(f"Disk usage high: {disk_status.usage_percent}%")
```

---

## Data Structures

### HealthStatus

```python
@dataclass
class HealthStatus:
    health_id: str
    instance: str  # "cloud" or "local"
    timestamp: datetime
    uptime_seconds: int
    status: str  # "healthy", "degraded", "critical", "offline"
    watchers: Dict[str, WatcherHealth]
    resources: ResourceMetrics
    vault_sync: SyncStatus
    alerts: List[str]
```

### WatcherHealth

```python
@dataclass
class WatcherHealth:
    watcher_name: str
    pid: Optional[int]
    status: str  # "running", "stopped", "crashed"
    uptime_seconds: int
    last_check: datetime
    events_processed_today: int
    errors_last_hour: int
    cpu_percent: float
    memory_mb: int
```

### ResourceMetrics

```python
@dataclass
class ResourceMetrics:
    cpu_percent: float
    memory_mb: int
    memory_percent: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: Tuple[float, float, float]
```

### HealthReport

```python
@dataclass
class HealthReport:
    report_id: str
    instance: str
    date: date
    uptime_percent: float
    watcher_crashes: int
    watcher_restarts: int
    vault_syncs_completed: int
    vault_sync_failures: int
    alerts_triggered: int
    critical_alerts: int
    avg_cpu_percent: float
    avg_memory_mb: int
    max_disk_usage_percent: float
```

---

## Configuration

**Watcher Configuration** (`config/watchers.yaml`):
```yaml
watchers:
  gmail_watcher:
    service_name: "gmail-watcher.service"
    expected_uptime_percent: 99.0
    max_restart_attempts: 3
    restart_backoff_seconds: [1, 2, 4]

  filesystem_watcher:
    service_name: "filesystem-watcher.service"
    expected_uptime_percent: 99.5
    max_restart_attempts: 3
    restart_backoff_seconds: [1, 2, 4]

  scheduler:
    service_name: "scheduler.service"
    expected_uptime_percent: 100.0
    max_restart_attempts: 3
    restart_backoff_seconds: [1, 2, 4]
```

**Alert Configuration** (`Company_Handbook.md`):
```yaml
alerts:
  enabled: true
  channels:
    email:
      enabled: true
      recipient: "admin@example.com"
    webhook:
      enabled: true
      url: "https://hooks.slack.com/services/XXX"

  thresholds:
    disk_warning: 80
    disk_critical: 90
    memory_warning: 80
    memory_critical: 90
    watcher_restart_limit: 3
```

**Environment Variables**:
```bash
INSTANCE_NAME=cloud  # or "local"
HEALTH_CHECK_INTERVAL_SECONDS=60
ALERT_EMAIL=admin@example.com
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/XXX
```

---

## Systemd Service Configuration

**Watchdog Service**: `health-monitor.service`

```ini
[Unit]
Description=Health Monitor & Watchdog
After=network.target

[Service]
Type=notify
NotifyAccess=main
WatchdogSec=90s
ExecStart=/usr/bin/python3 -m src.services.health_monitor watchdog
Restart=on-failure
RestartSec=10s
WorkingDirectory=/opt/ai-employee
Environment="INSTANCE_NAME=cloud"
User=aiemployee

[Install]
WantedBy=multi-user.target
```

**Key Config**:
- `Type=notify`: Enables systemd watchdog integration
- `WatchdogSec=90s`: Expects watchdog ping every 90s (2x check interval)
- `Restart=on-failure`: Auto-restart if watchdog crashes

---

## Watchdog Lifecycle

```
┌─────────────────────────────────────────────────┐
│ 1. start_watchdog() called on boot             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. Every 60s: collect_health_snapshot()        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. For each watcher: check_watcher_health()    │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   Watcher OK      Watcher crashed
        │                 │
        │                 ▼
        │          ┌──────────────┐
        │          │ 4. restart_  │
        │          │ watcher()    │
        │          └──────┬───────┘
        │                 │
        │        ┌────────┴────────┐
        │        │                 │
        │        ▼                 ▼
        │   Restart OK      3rd failure
        │        │                 │
        │        │                 ▼
        │        │          ┌──────────────┐
        │        │          │ 5. send_     │
        │        │          │ alert()      │
        │        │          └──────────────┘
        │        │
        └────────┴──────────┐
                            │
                            ▼
                  ┌──────────────────┐
                  │ 6. Notify systemd│
                  │ (watchdog ping)  │
                  └────────┬─────────┘
                           │
                           ▼
                  Loop back to step 2
```

---

## Error Scenarios

### Watcher Crash (Auto-Recovery)

**Scenario**: Gmail watcher crashes due to API rate limit

**Flow**:
```
1. check_watcher_health("gmail_watcher") detects PID missing
2. restart_watcher("gmail_watcher") called
3. systemctl restart gmail-watcher.service
4. Wait 5s, verify process running
5. Log: "Watcher restarted successfully"
6. Continue monitoring
```

### Repeated Crashes (Escalation)

**Scenario**: Gmail watcher crashes 3 times in 10 minutes

**Flow**:
```
1. Crash #1: Auto-restart (1s delay)
2. Crash #2: Auto-restart (2s delay)
3. Crash #3: Auto-restart (4s delay)
4. Crash #3 detected again within 10min window
5. stop_auto_restart("gmail_watcher")
6. send_alert(
     type="watcher_crash",
     message="Gmail watcher failed 3 times, manual intervention needed",
     severity="critical"
   )
7. Email sent to admin
```

### Disk Space Critical

**Scenario**: Disk usage hits 92%

**Flow**:
```
1. check_disk_space() detects 92% usage
2. Triggers critical alert
3. rotate_old_logs() called automatically
4. Deletes logs older than 30 days
5. Frees ~2GB space
6. Disk usage drops to 84%
7. Alert cleared
```

---

## Testing

### Unit Tests

```python
def test_health_snapshot():
    health = health_monitor.collect_health_snapshot()
    assert health.instance in ["cloud", "local"]
    assert health.status in ["healthy", "degraded", "critical", "offline"]

def test_watcher_health_check():
    watcher = health_monitor.check_watcher_health("gmail_watcher")
    assert watcher.watcher_name == "gmail_watcher"
    assert watcher.status in ["running", "stopped", "crashed"]

def test_restart_watcher_success(mock_systemctl):
    success = health_monitor.restart_watcher("gmail_watcher")
    assert success == True
    mock_systemctl.assert_called_with("restart", "gmail-watcher.service")

def test_alert_sent(mock_email):
    alert_manager.send_alert(
        alert_type="test",
        message="Test alert",
        severity="warning"
    )
    mock_email.assert_called_once()
```

### Integration Tests

- Real systemd service monitoring
- Watcher restart via systemctl
- Disk space check with actual filesystem
- Alert email delivery

---

## Performance

**Health Snapshot Collection**: 50-100ms
**Watcher Health Check**: 10-20ms per watcher
**Watchdog Loop (3 watchers)**: 150-200ms total
**Overhead**: <1% CPU, <50MB memory

---

## Monitoring Dashboard

**Daily Report Format** (`vault/Documents/HEALTH_REPORT_2026-03-04.md`):

```markdown
# Health Report: Cloud Instance - March 4, 2026

## Summary

- **Uptime**: 99.87%
- **Status**: Healthy
- **Alerts**: 2 warnings, 0 critical

## Watchers

| Watcher | Uptime | Crashes | Restarts | Events Processed |
|---------|--------|---------|----------|------------------|
| gmail_watcher | 99.95% | 0 | 0 | 1,247 |
| filesystem_watcher | 100% | 0 | 0 | 342 |
| scheduler | 100% | 0 | 0 | 24 |

## Resources

- **CPU**: Avg 12.3%, Max 45.2%
- **Memory**: Avg 487MB, Max 612MB
- **Disk**: Max usage 78.2%, Free 11.2GB

## Vault Sync

- **Syncs completed**: 287
- **Syncs failed**: 1 (network timeout, auto-recovered)
- **Average sync time**: 1.8s

## Alerts

1. [15:30] WARNING: Disk usage 81% (cleared after log rotation)
2. [22:15] WARNING: Gmail API rate limit (watcher backed off, recovered)

## Recommendations

- Disk usage trending up, consider cleanup or expansion
- Gmail API usage high, review polling interval
```

---

*Contract complete. Ready for implementation in `/sp.tasks`.*
