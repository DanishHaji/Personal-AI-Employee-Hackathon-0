---
name: dashboard-updater
description: Update Dashboard.md with current system state and recent activity
---

# Dashboard Updater Skill

This skill updates the Dashboard.md file in the Obsidian vault with current system state, including:
- Pending actions count (items in /Needs_Action/)
- Pending approvals count (items in /Pending_Approval/)
- System health status based on watcher heartbeats
- Recent activity (last 5 actions from audit logs)
- Watcher status (Gmail Watcher, File System Watcher, Orchestrator)

## Usage

```
Use dashboard-updater skill to refresh Dashboard.md
```

Or with specific vault path:

```
Update dashboard at /path/to/vault
```

## Implementation

When invoked, this skill should:

1. **Read vault path** from context or environment variable VAULT_PATH
2. **Count pending items**:
   - Count .md files in /Needs_Action/ folder
   - Count .md files in /Pending_Approval/ folder
3. **Read heartbeat status**:
   - Read /Logs/heartbeat.json
   - Determine each watcher's status based on timestamp freshness:
     - ✅ Running: heartbeat within last 5 minutes
     - ⚠️ Stale: heartbeat 5-15 minutes old
     - ❌ Stopped: heartbeat 15+ minutes old or missing
4. **Calculate system health**:
   - ✅ Healthy: All watchers running
   - ⚠️ Degraded: Some watchers stale/stopped
   - ❌ Down: All watchers stopped
5. **Read recent activity**:
   - Read today's audit log: /Logs/YYYY-MM-DD.json
   - Filter for user-visible actions: email_detected, file_dropped, plan_created, task_completed
   - Take the 5 most recent entries
   - Format as: `[HH:MM] action: description → target_path`
   - **Note**: This automatically includes both Email and FileDrop entities from their respective watchers
6. **Check for high pending count** (T055 - Edge Case):
   - If pending_actions >= 100:
     - Set system_health to DEGRADED (if not already worse)
     - Add warning section to dashboard
     - Include recommended actions
7. **Generate Dashboard.md**:
   - Use the DashboardSummary model to generate markdown
   - Include high count warning if applicable
   - Write to vault root: /Dashboard.md
   - Use atomic write pattern (write to temp, then rename)

## Example Output

The generated Dashboard.md should look like:

```markdown
# AI Employee Dashboard

**Last Updated**: 2026-02-21 14:50:00

## Status Overview

- **Pending Actions**: 3 items
- **Pending Approvals**: 1 item
- **System Health**: ✅ Healthy

> **Note**: Example with < 100 items. See warning example below for 100+ items.

## Recent Activity

1. [14:45] Plan created: Send January Invoice → /Plans/PLAN_001.md
2. [14:35] File dropped: contract.pdf → /Needs_Action
3. [14:30] Email detected: Urgent invoice request → /Needs_Action/EMAIL_18d4c5f2.md
4. [14:15] Email processed: Meeting confirmed → /Done/EMAIL_xyz789.md
5. [14:00] System started: All watchers initialized

## Watchers Status

- **Gmail Watcher**: ✅ Running (last check: 14:49)
- **File System Watcher**: ✅ Running (last heartbeat: 14:50)
- **Orchestrator**: ✅ Running

---

*This dashboard is automatically updated by the AI Employee system*
```

### Example with 100+ Items Warning (T055 - Edge Case)

When /Needs_Action/ has 100 or more items, the dashboard should display a warning:

```markdown
# AI Employee Dashboard

**Last Updated**: 2026-02-21 15:30:00

## Status Overview

- **Pending Actions**: 127 items ⚠️
- **Pending Approvals**: 2 items
- **System Health**: ⚠️ Degraded

> **⚠️ WARNING: High Pending Item Count**
>
> You have **127 pending items** in /Needs_Action/ (threshold: 100).
>
> **Recommended Actions**:
> 1. Review and prioritize urgent items
> 2. Move non-urgent items to /Done/ or archive
> 3. Check for duplicate detections (Gmail/File watchers)
> 4. Consider pausing watchers temporarily: `pm2 stop gmail-watcher filesystem-watcher`
>
> **Note**: Large backlogs may slow down plan generation and dashboard updates.

## Recent Activity
[... same as above ...]
```


## Python Implementation Reference

This skill should use the following Python code structure:

```python
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

from src.services.vault_service import VaultService
from src.services.logger_service import AuditLogger
from src.models.dashboard import (
    DashboardSummary, Activity, Watcher,
    SystemHealth, WatcherStatus
)
import json

# Get vault path
vault_path = Path(os.getenv('VAULT_PATH', '/path/to/vault'))
vault = VaultService(vault_path)
logger = AuditLogger(vault_path)

# Count pending items
pending_actions = vault.count_files('Needs_Action', '*.md')
pending_approvals = vault.count_files('Pending_Approval', '*.md')

# Read heartbeat data
heartbeat_file = vault_path / 'Logs' / 'heartbeat.json'
heartbeat_data = {}
if heartbeat_file.exists():
    with open(heartbeat_file, 'r') as f:
        heartbeat_data = json.load(f)

# Build watcher status
current_time = datetime.now()
watchers = {}
for watcher_name, watcher_info in heartbeat_data.items():
    timestamp_str = watcher_info.get('timestamp')
    if timestamp_str:
        # Parse ISO timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        status = DashboardSummary.determine_watcher_status(timestamp, current_time)
    else:
        status = WatcherStatus.NOT_STARTED

    watchers[watcher_name] = Watcher(
        name=watcher_name,
        status=status,
        last_check=timestamp if timestamp_str else None
    )

# Get recent activity
recent_logs = logger.get_recent_activity(limit=5)
activities = []
for log_entry in recent_logs:
    activities.append(Activity(
        timestamp=datetime.fromisoformat(log_entry['timestamp'].replace('Z', '')),
        action=log_entry['action_type'].replace('_', ' ').title(),
        target=log_entry['target']
    ))

# Check for high pending count (T055)
has_high_count = pending_actions >= 100
if has_high_count:
    print(f"⚠️  WARNING: High pending item count ({pending_actions} items)")

# Create dashboard summary
dashboard = DashboardSummary(
    last_updated=datetime.now(),
    pending_actions_count=pending_actions,
    pending_approvals_count=pending_approvals,
    system_health=dashboard.calculate_system_health() if watchers else SystemHealth.NOT_STARTED,
    recent_activity=activities,
    watchers_status=watchers
)

# Degrade system health if high count
if has_high_count and dashboard.system_health == SystemHealth.HEALTHY:
    dashboard.system_health = SystemHealth.DEGRADED

# Validate
dashboard.validate()

# Generate markdown with warning if needed
markdown = dashboard.to_markdown()

# Add high count warning after Status Overview section
if has_high_count:
    warning = f"""
> **⚠️ WARNING: High Pending Item Count**
>
> You have **{pending_actions} pending items** in /Needs_Action/ (threshold: 100).
>
> **Recommended Actions**:
> 1. Review and prioritize urgent items
> 2. Move non-urgent items to /Done/ or archive
> 3. Check for duplicate detections (Gmail/File watchers)
> 4. Consider pausing watchers temporarily: `pm2 stop gmail-watcher filesystem-watcher`
>
> **Note**: Large backlogs may slow down plan generation and dashboard updates.
"""
    # Insert warning after Status Overview section
    markdown = markdown.replace(
        "## Recent Activity",
        warning + "\n## Recent Activity"
    )

# Write Dashboard.md
vault.write_markdown('Dashboard.md', markdown)

print(f"✅ Dashboard updated successfully")
print(f"  - Pending Actions: {pending_actions}")
print(f"  - Pending Approvals: {pending_approvals}")
print(f"  - System Health: {dashboard.system_health.value}")
```

## Error Handling

- If vault path is invalid: Exit with error message
- If heartbeat.json missing: Show "Unknown" status for all watchers
- If today's log file missing: Show "No recent activity"
- If folder scan fails: Show last known count with "(stale)" indicator

## Integration

This skill is automatically invoked by:
1. **Orchestrator**: After processing items in /Needs_Action/
2. **Watchers**: After creating new Email/FileDrop entities (optional)
3. **Manual trigger**: User can invoke via Claude Code CLI

## Success Criteria

- Dashboard.md updates within 60 seconds of state changes (SC-006)
- Counts accurately match folder contents
- Watcher statuses reflect true heartbeat state
- Recent activity shows last 5 user-visible actions
- File writes are atomic (no corruption)
