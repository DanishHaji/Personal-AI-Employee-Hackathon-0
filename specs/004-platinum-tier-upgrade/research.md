---
id: 004-research
title: Platinum Tier Technical Research
feature: 004-platinum-tier-upgrade
stage: research
date: 2026-03-04
status: completed
---

# Platinum Tier Technical Research

This document captures technical research and decision rationale for the Platinum Tier upgrade implementation.

## 1. Vault Sync Technology

### Decision: Git (with Secret Filtering)

**Rationale:**
- **Version Control Integration**: Git provides built-in version history, which aligns with the project's existing workflow and allows for precise tracking of vault changes over time.
- **Secret Filtering**: Git pre-commit hooks with tools like `detect-secrets` or `gitleaks` provide robust secret detection before commits, addressing the critical security requirement.
- **Proven at Scale**: While Git struggles with large binary files, Obsidian vaults are primarily Markdown text files with YAML frontmatter, where Git excels.
- **Conflict Resolution**: Git's merge capabilities are mature and well-understood, with clear conflict markers and resolution workflows.
- **Cloud VM Integration**: Git requires minimal setup on Ubuntu 22.04 (`apt install git`) and integrates seamlessly with systemd-based automation.

**Alternatives Considered:**

1. **Syncthing**
   - **Pros**: Real-time peer-to-peer sync, excellent for binary files, no waiting for sync operations
   - **Cons**:
     - Significant data loss and file corruption reported with multi-device setups (4+ clients)
     - Conflict resolution is less mature than Git's
     - Requires all devices online simultaneously for sync
     - Secret filtering requires custom integration
     - No built-in version history
   - **Source**: Users reported "disastrous" results with "significant data loss or file corruption more than half the time" in star formations

**Performance Considerations (10GB Vault):**
- Git handles text-heavy repositories well even at 10GB+
- Use `.gitattributes` to exclude large binary files (attachments, images) from sync if needed
- Implement shallow clones on Cloud VM to reduce initial clone time
- Use Git LFS (Large File Storage) for any binary assets if necessary

**Implementation Recommendations:**

1. **Secret Filtering Setup**
   - Use `detect-secrets` (Yelp) with pre-commit framework
   - Configure `.pre-commit-config.yaml` at repository root
   - Add patterns for: API keys, tokens, passwords, private keys
   - Block commits containing secrets automatically

2. **Git Configuration**
   ```bash
   # On Cloud VM
   git config --global user.name "AI Employee Cloud"
   git config --global user.email "cloud@aiemployee.local"
   git config --global pull.rebase true  # Avoid merge commits
   git config --global core.autocrlf false  # Preserve line endings
   ```

3. **Automation Strategy**
   - Use systemd timer for periodic pull/push (every 5-15 minutes)
   - Implement file watcher (inotify) for immediate push on local changes
   - Auto-commit with structured messages: `[cloud] <timestamp> - <files changed>`

4. **Conflict Prevention**
   - Use work-zone routing (see Section 4) to minimize simultaneous edits
   - Implement advisory locking via claim files before major operations
   - Auto-pull before any write operations from Cloud VM

**Sources:**
- [Syncthing vs Git discussion on Syncthing Forum](https://forum.syncthing.net/t/should-i-switch-over-from-git-to-syncthing/25569)
- [Obsidian Syncthing sync problems](https://forum.syncthing.net/t/yet-another-obsidian-user-with-sync-problems/21233)
- [Obsidian sync comparison guide](https://seansusmilch.github.io/posts/obsidian-syncthing-private-sync-guide/)
- [detect-secrets by Yelp](https://github.com/Yelp/detect-secrets)
- [GitGuardian Shield pre-commit setup](https://blog.gitguardian.com/setting-up-a-pre-commit-git-hook-with-gitguardian-shield-to-scan-for-secrets/)

---

## 2. Cloud Deployment: Python on Ubuntu 22.04

### Decision: systemd Service with WatchdogSec

**Rationale:**
- **Native Integration**: systemd is the default init system on Ubuntu 22.04, requiring no additional process managers
- **Robust Auto-Restart**: Built-in `Restart=on-failure` and `WatchdogSec` provide application-level health monitoring
- **Resource Management**: systemd allows setting memory limits, CPU quotas, and I/O constraints
- **Logging**: Automatic integration with journald for centralized log management
- **Standard Practice**: systemd services are the 2026 best practice for production Python deployments on Ubuntu

**Alternatives Considered:**

1. **Supervisor**
   - **Pros**: Simple configuration, web UI for monitoring
   - **Cons**: Additional dependency, less integrated with system, redundant with systemd capabilities

2. **Docker/Containers**
   - **Pros**: Isolation, portability
   - **Cons**: Overkill for single-application deployment, adds complexity, resource overhead

**Implementation Recommendations:**

### Service Configuration Template

Create `/etc/systemd/system/ai-employee-cloud.service`:

```ini
[Unit]
Description=AI Employee Cloud Instance
After=network-online.target
Wants=network-online.target
Documentation=https://github.com/yourusername/ai-employee

[Service]
Type=notify
User=aiemployee
Group=aiemployee
WorkingDirectory=/home/aiemployee/ai-employee
Environment="PYTHONUNBUFFERED=1"
Environment="AI_EMPLOYEE_MODE=cloud"
EnvironmentFile=/home/aiemployee/ai-employee/.env

# Main process
ExecStart=/home/aiemployee/ai-employee/.venv/bin/python -m src.main

# Auto-restart configuration
Restart=on-failure
RestartSec=10
StartLimitInterval=5min
StartLimitBurst=4

# Watchdog configuration (app must ping systemd every 30s)
WatchdogSec=60
NotifyAccess=main

# Resource limits
MemoryMax=2G
CPUQuota=200%
TasksMax=100

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-employee-cloud

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/aiemployee/ai-employee/vault /home/aiemployee/ai-employee/logs

[Install]
WantedBy=multi-user.target
```

### Watchdog Integration in Python

Use `systemd-watchdog` library for health pings:

```python
# src/cloud/watchdog.py
from systemd import watchdog
import threading
import time

class SystemdWatchdog:
    def __init__(self, interval_sec: int = 30):
        self.interval = interval_sec
        self.enabled = watchdog.enabled()
        self._running = False
        self._thread = None

    def start(self):
        if not self.enabled:
            return

        self._running = True
        self._thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._thread.start()
        watchdog.ready()  # Signal systemd that we're ready

    def _watchdog_loop(self):
        while self._running:
            watchdog.notify()  # Ping systemd
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
```

### Log Rotation Strategy

systemd/journald handles rotation automatically, but for application logs:

Create `/etc/logrotate.d/ai-employee`:

```
/home/aiemployee/ai-employee/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 aiemployee aiemployee
    sharedscripts
    postrotate
        systemctl reload ai-employee-cloud
    endscript
}
```

### Deployment Commands

```bash
# Install service
sudo cp ai-employee-cloud.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-employee-cloud.service
sudo systemctl start ai-employee-cloud.service

# Monitor status
sudo systemctl status ai-employee-cloud.service
sudo journalctl -u ai-employee-cloud.service -f

# View logs
sudo journalctl -u ai-employee-cloud.service --since today
sudo journalctl -u ai-employee-cloud.service -n 100 --no-pager
```

**Sources:**
- [Systemd: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/systemd-complete-guide)
- [How to run Python script as a service on Ubuntu 22](https://alfredobarron.medium.com/how-to-run-python-script-as-a-service-on-ubuntu-22-613c4e825b6b)
- [Autostart python scripts on boot with systemd](https://blog.merzlabs.com/posts/python-autostart-systemd/)
- [How to Automatically Restart a Linux Service](https://gcore.com/learning/how-to-automatically-restart-a-linux-service)
- [systemd-watchdog PyPI](https://pypi.org/project/systemd-watchdog/)

---

## 3. Odoo Community Integration

### Decision: JSON-RPC via MCP Server (Transition to JSON-2 API)

**Rationale:**
- **Future-Proof**: XML-RPC and legacy JSON-RPC endpoints are deprecated and will be removed in Odoo 20 (Fall 2026). The External JSON-2 API is the replacement.
- **Modern Architecture**: JSON-RPC is REST-like, uses JSON (easier parsing), and is recommended for Odoo v14+
- **MCP Pattern**: Building an MCP (Model Context Protocol) server provides a clean abstraction layer between AI Employee and Odoo
- **Authentication**: JSON-2 API uses API keys (Bearer token) instead of login/password, which is more secure

**Alternatives Considered:**

1. **XML-RPC**
   - **Pros**: Legacy stability, well-documented
   - **Cons**: **DEPRECATED** - will be removed in Odoo 20 (Fall 2026), XML is verbose, slower parsing

2. **Direct REST via Add-ons**
   - **Pros**: RESTful interface
   - **Cons**: Requires installing Odoo add-ons, not part of Community Edition core

**Implementation Recommendations:**

### MCP Server Architecture

```
AI Employee (Local/Cloud)
    ↓
MCP Client (stdio/SSE transport)
    ↓
MCP Server: Odoo Connector
    ↓
Odoo JSON-2 API (https://odoo.example.com)
    ↓
Expense Tracking Module
```

### MCP Server Structure

Create `src/mcp_servers/odoo_server.py`:

```python
from mcp.server import MCPServer, Tool
import httpx
import json
from typing import Dict, List, Any

class OdooMCPServer(MCPServer):
    def __init__(self, odoo_url: str, api_key: str, database: str):
        super().__init__(name="odoo-connector")
        self.odoo_url = odoo_url.rstrip('/')
        self.api_key = api_key
        self.database = database
        self.session = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )

    async def _call_odoo(self, model: str, method: str, args: List, kwargs: Dict = None):
        """Call Odoo JSON-2 API"""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": [
                    self.database,
                    model,
                    method,
                    args,
                    kwargs or {}
                ]
            },
            "id": 1
        }

        response = await self.session.post(
            f"{self.odoo_url}/jsonrpc",
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(f"Odoo API error: {result['error']}")

        return result.get("result")

    @Tool(description="Create expense in Odoo")
    async def create_expense(
        self,
        employee_id: int,
        product_id: int,
        unit_amount: float,
        description: str,
        date: str
    ) -> Dict[str, Any]:
        """Create an expense record in Odoo hr.expense module"""
        expense_id = await self._call_odoo(
            model="hr.expense",
            method="create",
            args=[{
                "employee_id": employee_id,
                "product_id": product_id,
                "unit_amount": unit_amount,
                "name": description,
                "date": date
            }]
        )
        return {"expense_id": expense_id, "status": "created"}

    @Tool(description="List expenses from Odoo")
    async def list_expenses(
        self,
        employee_id: int = None,
        state: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List expenses with optional filters"""
        domain = []
        if employee_id:
            domain.append(("employee_id", "=", employee_id))
        if state:
            domain.append(("state", "=", state))

        expense_ids = await self._call_odoo(
            model="hr.expense",
            method="search",
            args=[domain],
            kwargs={"limit": limit}
        )

        expenses = await self._call_odoo(
            model="hr.expense",
            method="read",
            args=[expense_ids],
            kwargs={"fields": ["employee_id", "product_id", "unit_amount", "name", "date", "state"]}
        )

        return expenses
```

### Authentication Configuration

In `.env`:

```bash
# Odoo Configuration
ODOO_URL=https://your-odoo.example.com
ODOO_DATABASE=your_database
ODOO_API_KEY=your_api_key_here  # Generate in Odoo user preferences

# MCP Server
MCP_ODOO_ENABLED=true
```

### Expense Tracking Integration

The Odoo `hr.expense` module provides:
- Expense creation and tracking
- Multi-currency support
- Receipt attachment
- Approval workflows
- Accounting integration

**Key Models:**
- `hr.expense` - Individual expense records
- `hr.expense.sheet` - Expense reports (grouping multiple expenses)
- `product.product` - Expense categories/products

### Backup Strategy

1. **Automated Backups**
   ```bash
   # Daily backup via cron
   0 2 * * * /usr/bin/python3 /home/aiemployee/ai-employee/scripts/backup_odoo.py
   ```

2. **Backup Script** (using Odoo API):
   - Export expense data as JSON
   - Store in vault under `backups/odoo/YYYY-MM-DD/`
   - Keep 30 days of backups
   - Encrypt sensitive data

3. **Restoration Process**
   - Re-import via JSON-2 API
   - Verify data integrity
   - Document in ADR

**Sources:**
- [Odoo 19.0 External JSON-2 API Documentation](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
- [Odoo API Integration Guide (In-Depth)](https://www.getknit.dev/blog/odoo-api-integration-guide-in-depth)
- [Odoo API & Integrations: The Definitive Guide](https://theledgerlabs.com/odoo-api-integration-guide/)
- [Odoo 18.0 Web Services Documentation](https://www.odoo.com/documentation/18.0/developer/howtos/web_services.html)

---

## 4. Work-Zone Routing: Cloud-Local Delegation

### Decision: File-Based Claim Pattern with Advisory Locks

**Rationale:**
- **Simplicity**: File-based claims work seamlessly with existing file-based architecture (Markdown + YAML)
- **Git-Compatible**: Claim files are versioned and synced automatically
- **Conflict Detection**: Git's merge conflict detection provides built-in simultaneous claim detection
- **No Database**: Aligns with constitutional requirement for file-based architecture
- **Debuggable**: Claim status is human-readable in plain text files

**Alternatives Considered:**

1. **Redis/Distributed Lock Manager**
   - **Pros**: Atomic operations, TTL expiration
   - **Cons**: Requires external service, violates file-based architecture, adds network dependency

2. **Database-Based Locking**
   - **Pros**: ACID guarantees
   - **Cons**: Violates constitution (no database), requires additional infrastructure

**Design Pattern:**

### Claim File Structure

Location: `vault/claims/<task-type>/<task-id>.claim.md`

Example: `vault/claims/email-response/MSG-123.claim.md`

```yaml
---
id: claim-001
task_id: MSG-123
task_type: email-response
claimed_by: cloud  # or "local"
claimed_at: 2026-03-04T10:30:00Z
expires_at: 2026-03-04T11:30:00Z  # 1 hour TTL
status: active  # active, completed, expired, released
priority: high
metadata:
  subject: "Re: Project Update"
  estimated_duration: 30
---

# Task Claim: MSG-123

## Task Details
- Type: Email Response
- Priority: High
- Estimated Duration: 30 minutes

## Claimed By
- Agent: Cloud Instance
- Timestamp: 2026-03-04 10:30:00 UTC

## Notes
User requested autonomous response to project update inquiry.
```

### Claim Lifecycle

```python
# src/routing/claim_manager.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal
import yaml

AgentType = Literal["cloud", "local"]
ClaimStatus = Literal["active", "completed", "expired", "released"]

@dataclass
class TaskClaim:
    id: str
    task_id: str
    task_type: str
    claimed_by: AgentType
    claimed_at: datetime
    expires_at: datetime
    status: ClaimStatus
    priority: str
    metadata: dict

class ClaimManager:
    def __init__(self, vault_path: Path):
        self.claims_dir = vault_path / "claims"
        self.claims_dir.mkdir(parents=True, exist_ok=True)

    def try_claim(
        self,
        task_id: str,
        task_type: str,
        agent: AgentType,
        ttl_minutes: int = 60,
        priority: str = "medium",
        metadata: dict = None
    ) -> Optional[TaskClaim]:
        """
        Attempt to claim a task. Returns TaskClaim if successful, None if already claimed.

        Uses optimistic locking with Git conflict detection:
        1. Pull latest claims
        2. Check if claim exists
        3. Create claim file
        4. Commit and push
        5. If push fails (conflict), pull and retry
        """
        claim_path = self._get_claim_path(task_type, task_id)

        # Check existing claim
        if claim_path.exists():
            existing = self._load_claim(claim_path)
            if existing.status == "active" and existing.expires_at > datetime.utcnow():
                return None  # Already claimed and not expired

        # Create new claim
        claim = TaskClaim(
            id=f"claim-{task_id}",
            task_id=task_id,
            task_type=task_type,
            claimed_by=agent,
            claimed_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
            status="active",
            priority=priority,
            metadata=metadata or {}
        )

        # Write claim file
        self._write_claim(claim_path, claim)

        # Commit to Git (will detect conflicts if simultaneous claim)
        try:
            self._git_commit_and_push(claim_path, f"Claim task {task_id} by {agent}")
            return claim
        except GitConflictError:
            # Another agent claimed simultaneously
            return None

    def release_claim(self, task_id: str, task_type: str):
        """Release a claim (mark as completed or released)"""
        claim_path = self._get_claim_path(task_type, task_id)
        if claim_path.exists():
            claim = self._load_claim(claim_path)
            claim.status = "completed"
            self._write_claim(claim_path, claim)
            self._git_commit_and_push(claim_path, f"Release claim {task_id}")

    def is_claimed(self, task_id: str, task_type: str) -> bool:
        """Check if task is currently claimed by any agent"""
        claim_path = self._get_claim_path(task_type, task_id)
        if not claim_path.exists():
            return False

        claim = self._load_claim(claim_path)
        return claim.status == "active" and claim.expires_at > datetime.utcnow()

    def cleanup_expired(self):
        """Mark expired claims as expired (run periodically)"""
        for claim_file in self.claims_dir.rglob("*.claim.md"):
            claim = self._load_claim(claim_file)
            if claim.status == "active" and claim.expires_at < datetime.utcnow():
                claim.status = "expired"
                self._write_claim(claim_file, claim)
```

### Conflict Resolution Strategy

1. **Simultaneous Claims** (Both agents claim same task):
   - Git push from second agent will fail with conflict
   - Second agent detects conflict and abandons claim
   - First agent proceeds with task
   - **Winner**: First to successfully push to Git

2. **Expired Claims**:
   - Background task runs every 5 minutes to mark expired claims
   - Expired claims can be re-claimed by either agent

3. **Stale Claims** (Agent crashes mid-task):
   - TTL expiration handles this automatically
   - Configurable TTL based on task type (email: 30m, research: 2h, etc.)

4. **Split-Brain** (Git connectivity issues):
   - Local agent continues working on local tasks
   - Cloud agent works only on cloud-assigned tasks
   - When connectivity restored, Git merge resolves conflicts
   - Manual intervention for data conflicts (rare)

### Routing Rules

Encode in `vault/config/routing-rules.md`:

```yaml
---
version: 1
updated: 2026-03-04
---

# Work-Zone Routing Rules

## Cloud Agent Responsibilities
- Email responses (autonomous)
- Calendar management
- Expense tracking (Odoo integration)
- Proactive insights
- Background research

## Local Agent Responsibilities
- File processing (local attachments)
- Sensitive document handling
- Interactive sessions
- Development tasks

## Claiming Protocol
1. Agent checks routing rules for task type
2. If task type matches zone → attempt claim
3. If claim successful → execute task
4. If claim fails → skip (other agent handling)
5. If task outside zone → skip

## TTL by Task Type
- email-response: 30 minutes
- calendar-event: 15 minutes
- expense-entry: 10 minutes
- research-task: 120 minutes
- file-processing: 60 minutes
```

**Sources:**
- [How to Build Conflict Resolution (OneUpTime, January 2026)](https://oneuptime.com/blog/post/2026-01-30-conflict-resolution/view)
- [Consistency Patterns in Distributed Systems](https://www.designgurus.io/blog/consistency-patterns-distributed-systems)
- [Concurrency and Automatic Conflict Resolution](https://dev.to/frosnerd/concurrency-and-automatic-conflict-resolution-4i9o)

---

## 5. Health Monitoring: Python Libraries

### Decision: psutil + systemd-watchdog + Custom Alert System

**Rationale:**
- **psutil**: Industry-standard library for process monitoring (v7.2.2, released Jan 2026), cross-platform, mature
- **systemd-watchdog**: Native integration with systemd's watchdog mechanism, lightweight
- **Custom Alerts**: Build on top of psutil for application-specific health metrics
- **No External Dependencies**: Avoid heavy monitoring stacks (Prometheus, Grafana) for single-application deployment

**Alternatives Considered:**

1. **Supervisor with superlance**
   - **Pros**: Built-in monitoring, crash reports
   - **Cons**: Redundant with systemd, additional dependency

2. **Full Monitoring Stack (Prometheus + Alertmanager)**
   - **Pros**: Industry standard, powerful querying
   - **Cons**: Massive overkill for single application, resource intensive

**Implementation Recommendations:**

### Health Monitoring Architecture

```
Application Process
    ↓
psutil (process metrics)
    ↓
HealthMonitor (custom)
    ↓
systemd-watchdog (heartbeat) + AlertManager (notifications)
```

### Health Monitor Implementation

```python
# src/monitoring/health_monitor.py
import psutil
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from systemd import watchdog
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthMetrics:
    timestamp: datetime
    status: HealthStatus
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    open_files: int
    threads: int
    uptime_seconds: float
    errors_last_hour: int

class HealthMonitor:
    def __init__(
        self,
        check_interval: int = 30,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        disk_threshold: float = 90.0
    ):
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

        self.process = psutil.Process()
        self.start_time = datetime.utcnow()
        self.error_count = 0
        self.last_error_reset = datetime.utcnow()

        self.logger = logging.getLogger(__name__)

    def get_metrics(self) -> HealthMetrics:
        """Collect current health metrics"""
        try:
            cpu_percent = self.process.cpu_percent(interval=1.0)
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()

            # Disk usage for working directory
            disk = psutil.disk_usage(self.process.cwd())
            disk_usage_percent = disk.percent

            # Process info
            open_files = len(self.process.open_files())
            threads = self.process.num_threads()
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

            # Reset error count hourly
            if datetime.utcnow() - self.last_error_reset > timedelta(hours=1):
                self.error_count = 0
                self.last_error_reset = datetime.utcnow()

            # Determine health status
            status = self._calculate_status(
                cpu_percent, memory_percent, disk_usage_percent
            )

            return HealthMetrics(
                timestamp=datetime.utcnow(),
                status=status,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                open_files=open_files,
                threads=threads,
                uptime_seconds=uptime,
                errors_last_hour=self.error_count
            )
        except Exception as e:
            self.logger.error(f"Failed to collect health metrics: {e}")
            self.error_count += 1
            return None

    def _calculate_status(
        self,
        cpu: float,
        memory: float,
        disk: float
    ) -> HealthStatus:
        """Calculate overall health status based on thresholds"""
        if (cpu > self.cpu_threshold or
            memory > self.memory_threshold or
            disk > self.disk_threshold):
            return HealthStatus.UNHEALTHY

        if (cpu > self.cpu_threshold * 0.8 or
            memory > self.memory_threshold * 0.8 or
            disk > self.disk_threshold * 0.8):
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def check_health(self) -> bool:
        """
        Perform health check and return True if healthy.
        Used by watchdog to determine if process should be restarted.
        """
        metrics = self.get_metrics()
        if not metrics:
            return False

        if metrics.status == HealthStatus.UNHEALTHY:
            self.logger.error(f"Unhealthy status: {metrics}")
            return False

        if metrics.status == HealthStatus.DEGRADED:
            self.logger.warning(f"Degraded status: {metrics}")

        # Ping systemd watchdog
        if watchdog.enabled():
            watchdog.notify()

        return True

    def log_metrics(self, metrics: HealthMetrics):
        """Log metrics to structured log file"""
        log_entry = {
            "timestamp": metrics.timestamp.isoformat(),
            "status": metrics.status.value,
            "cpu_percent": metrics.cpu_percent,
            "memory_mb": metrics.memory_mb,
            "memory_percent": metrics.memory_percent,
            "disk_usage_percent": metrics.disk_usage_percent,
            "open_files": metrics.open_files,
            "threads": metrics.threads,
            "uptime_seconds": metrics.uptime_seconds,
            "errors_last_hour": metrics.errors_last_hour
        }

        # Write to metrics log (parsed by analytics)
        with open("/var/log/ai-employee/metrics.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
```

### Alert Manager

```python
# src/monitoring/alert_manager.py
import smtplib
import requests
from email.message import EmailMessage
from typing import List, Dict

class AlertManager:
    def __init__(self, config: dict):
        self.email_enabled = config.get("email_enabled", False)
        self.email_to = config.get("email_to", [])
        self.webhook_enabled = config.get("webhook_enabled", False)
        self.webhook_url = config.get("webhook_url")
        self.smtp_config = config.get("smtp", {})

    def send_alert(
        self,
        severity: str,  # "warning", "error", "critical"
        title: str,
        message: str,
        metrics: Dict = None
    ):
        """Send alert via configured channels"""
        alert_data = {
            "severity": severity,
            "title": title,
            "message": message,
            "metrics": metrics or {},
            "timestamp": datetime.utcnow().isoformat(),
            "host": os.uname().nodename
        }

        if self.email_enabled:
            self._send_email_alert(alert_data)

        if self.webhook_enabled:
            self._send_webhook_alert(alert_data)

    def _send_email_alert(self, alert_data: Dict):
        """Send email alert"""
        msg = EmailMessage()
        msg["Subject"] = f"[{alert_data['severity'].upper()}] {alert_data['title']}"
        msg["From"] = self.smtp_config["from"]
        msg["To"] = ", ".join(self.email_to)

        body = f"""
AI Employee Health Alert

Severity: {alert_data['severity']}
Host: {alert_data['host']}
Time: {alert_data['timestamp']}

{alert_data['message']}

Metrics:
{json.dumps(alert_data['metrics'], indent=2)}
        """
        msg.set_content(body)

        with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as smtp:
            if self.smtp_config.get("use_tls"):
                smtp.starttls()
            if self.smtp_config.get("username"):
                smtp.login(self.smtp_config["username"], self.smtp_config["password"])
            smtp.send_message(msg)

    def _send_webhook_alert(self, alert_data: Dict):
        """Send webhook alert (e.g., to Slack, Discord, custom endpoint)"""
        try:
            response = requests.post(
                self.webhook_url,
                json=alert_data,
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to send webhook alert: {e}")
```

### Integration with Main Application

```python
# src/main.py
import asyncio
from monitoring.health_monitor import HealthMonitor
from monitoring.alert_manager import AlertManager

async def main():
    # Initialize monitoring
    health_monitor = HealthMonitor(
        check_interval=30,
        cpu_threshold=80.0,
        memory_threshold=80.0,
        disk_threshold=90.0
    )

    alert_manager = AlertManager({
        "email_enabled": True,
        "email_to": ["admin@example.com"],
        "webhook_enabled": True,
        "webhook_url": os.getenv("ALERT_WEBHOOK_URL"),
        "smtp": {
            "host": os.getenv("SMTP_HOST"),
            "port": int(os.getenv("SMTP_PORT", 587)),
            "use_tls": True,
            "username": os.getenv("SMTP_USERNAME"),
            "password": os.getenv("SMTP_PASSWORD"),
            "from": "ai-employee@example.com"
        }
    })

    # Start health monitoring loop
    async def monitor_loop():
        while True:
            metrics = health_monitor.get_metrics()
            if metrics:
                health_monitor.log_metrics(metrics)

                if metrics.status == HealthStatus.UNHEALTHY:
                    alert_manager.send_alert(
                        severity="critical",
                        title="AI Employee Unhealthy",
                        message=f"Application is unhealthy. CPU: {metrics.cpu_percent}%, Memory: {metrics.memory_percent}%",
                        metrics=vars(metrics)
                    )
                elif metrics.status == HealthStatus.DEGRADED:
                    alert_manager.send_alert(
                        severity="warning",
                        title="AI Employee Degraded",
                        message=f"Application performance degraded. CPU: {metrics.cpu_percent}%, Memory: {metrics.memory_percent}%",
                        metrics=vars(metrics)
                    )

            await asyncio.sleep(health_monitor.check_interval)

    # Run monitoring in background
    asyncio.create_task(monitor_loop())

    # Main application logic
    # ...
```

### Auto-Restart Pattern

systemd handles auto-restart automatically with the service configuration from Section 2. The health monitor complements this by:

1. **Proactive Detection**: Detects degraded state before failure
2. **Alerting**: Notifies administrators of issues
3. **Metrics**: Provides data for post-mortem analysis
4. **Graceful Shutdown**: Can trigger graceful shutdown if unhealthy (systemd will restart)

```python
# In main application loop
if not health_monitor.check_health():
    logger.error("Health check failed. Initiating graceful shutdown.")
    await cleanup()
    sys.exit(1)  # systemd will auto-restart
```

**Sources:**
- [psutil 7.2.3 Documentation](https://psutil.readthedocs.io/)
- [psutil on PyPI (v7.2.2, Jan 2026)](https://pypi.org/project/psutil/)
- [systemd-watchdog PyPI](https://pypi.org/project/systemd-watchdog/)
- [How to create watchdog for systemd service](https://sleeplessbeastie.eu/2022/08/15/how-to-create-watchdog-for-systemd-service/)
- [Using watchdog and sd-notify functionality for systemd in Python 3](https://blog.stigok.com/2020/01/26/sd-notify-systemd-watchdog-python-3.html)

---

## Summary of Decisions

| Area | Decision | Key Rationale |
|------|----------|--------------|
| **Vault Sync** | Git with secret filtering | Version control, mature conflict resolution, pre-commit secret detection |
| **Cloud Deployment** | systemd with WatchdogSec | Native Ubuntu integration, robust auto-restart, resource management |
| **Odoo Integration** | JSON-2 API via MCP Server | Future-proof (XML-RPC deprecated 2026), modern architecture, secure API keys |
| **Work-Zone Routing** | File-based claim pattern | Git-compatible, no database, simple conflict detection, debuggable |
| **Health Monitoring** | psutil + systemd-watchdog | Industry standard, lightweight, systemd integration, custom alerting |

## Next Steps

1. Create ADR for each significant decision (vault sync, Odoo integration, work-zone routing)
2. Implement proof-of-concept for claim manager
3. Set up systemd service configuration and test auto-restart
4. Build Odoo MCP server with expense tracking tools
5. Configure Git pre-commit hooks with detect-secrets
6. Implement health monitoring and alert system

## References

All source links are embedded inline in each section above. Key resources:

- Odoo 19.0 External API Documentation
- systemd Best Practices Guide 2026
- psutil Official Documentation (v7.2.3)
- Git Pre-commit Hooks for Secret Detection
- Distributed Systems Conflict Resolution Patterns

---

*Document created: 2026-03-04*
*Last updated: 2026-03-04*
*Status: Completed*
