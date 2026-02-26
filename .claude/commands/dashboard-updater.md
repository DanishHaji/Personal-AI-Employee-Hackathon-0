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
7. **Calculate execution statistics** (Silver Tier - T032):
   - Read today's execution logs: /Logs/YYYY-MM-DD.json
   - Filter for `action_type: email_send` entries
   - Count total executions today
   - Count successful executions (`result: success`)
   - Calculate success rate percentage
   - Find most recent execution timestamp
   - Get rate limit remaining from RateLimiter state file
8. **Generate Dashboard.md**:
   - Use the DashboardSummary model to generate markdown
   - Include high count warning if applicable
   - Include execution statistics section (Silver Tier)
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

## Execution Statistics (Silver Tier)

**Email Sending:**
- **Emails Sent Today**: 5 emails
- **Last Execution**: 14:45 (2 minutes ago)
- **Success Rate**: 100% (5/5 successful)
- **Rate Limit Status**: 495 emails remaining today

**Social Media Posting:**
- **Posts Published Today**: 3 posts
- **Platforms**: LinkedIn (2), Twitter (2), Facebook (1)
- **Last Post**: 14:30 (15 minutes ago)
- **Success Rate**: 100% (3/3 successful)

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

# Calculate execution statistics (Silver Tier - T032)
execution_stats = {
    'emails_sent_today': 0,
    'last_execution': None,
    'success_count': 0,
    'total_count': 0,
    'rate_limit_remaining': 0
}

# Read today's execution logs
today_log_file = vault_path / 'Logs' / f"{datetime.now().strftime('%Y-%m-%d')}.json"
if today_log_file.exists():
    with open(today_log_file, 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get('action_type') == 'email_send':
                    execution_stats['total_count'] += 1
                    if log_entry.get('result') == 'success':
                        execution_stats['success_count'] += 1
                    # Track most recent execution
                    exec_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    if execution_stats['last_execution'] is None or exec_time > execution_stats['last_execution']:
                        execution_stats['last_execution'] = exec_time
            except (json.JSONDecodeError, KeyError):
                pass  # Skip malformed lines

execution_stats['emails_sent_today'] = execution_stats['success_count']

# Calculate success rate
if execution_stats['total_count'] > 0:
    success_rate = (execution_stats['success_count'] / execution_stats['total_count']) * 100
else:
    success_rate = 100  # No executions = 100% (no failures)

# Get rate limit remaining
rate_limit_file = vault_path / 'Logs' / 'rate_limit_state.json'
if rate_limit_file.exists():
    with open(rate_limit_file, 'r') as f:
        rate_limit_data = json.load(f)
        if 'gmail' in rate_limit_data:
            execution_stats['rate_limit_remaining'] = int(rate_limit_data['gmail'].get('tokens', 0))

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

# Calculate social media statistics (Silver Tier - T051)
social_stats = {
    'posts_published_today': 0,
    'last_post': None,
    'success_count': 0,
    'total_count': 0,
    'platform_breakdown': {'linkedin': 0, 'facebook': 0, 'twitter': 0}
}

# Read today's execution logs for social posts
if today_log_file.exists():
    with open(today_log_file, 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get('action_type') == 'social_post':
                    social_stats['total_count'] += 1

                    # Track success/partial as published
                    result = log_entry.get('result', '')
                    if result in ['success', 'partial']:
                        social_stats['success_count'] += 1

                        # Count per-platform posts
                        platforms = log_entry.get('parameters', {}).get('platforms', [])
                        for platform in platforms:
                            if platform in social_stats['platform_breakdown']:
                                social_stats['platform_breakdown'][platform] += 1

                    # Track most recent post
                    post_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    if social_stats['last_post'] is None or post_time > social_stats['last_post']:
                        social_stats['last_post'] = post_time
            except (json.JSONDecodeError, KeyError):
                pass

social_stats['posts_published_today'] = social_stats['success_count']

# Calculate social media success rate
if social_stats['total_count'] > 0:
    social_success_rate = (social_stats['success_count'] / social_stats['total_count']) * 100
else:
    social_success_rate = 100

# Format platform breakdown
platform_breakdown_str = ", ".join(
    f"{platform.capitalize()} ({count})"
    for platform, count in social_stats['platform_breakdown'].items()
    if count > 0
) or "None"

# Add execution statistics section (Silver Tier - T032, T051)
exec_stats_section = f"""
## Execution Statistics (Silver Tier)

**Email Sending:**
- **Emails Sent Today**: {execution_stats['emails_sent_today']} emails
- **Last Execution**: {execution_stats['last_execution'].strftime('%H:%M') if execution_stats['last_execution'] else 'Never'} ({_format_time_ago(execution_stats['last_execution']) if execution_stats['last_execution'] else 'N/A'})
- **Success Rate**: {success_rate:.0f}% ({execution_stats['success_count']}/{execution_stats['total_count']} successful)
- **Rate Limit Status**: {execution_stats['rate_limit_remaining']} emails remaining today

**Social Media Posting:**
- **Posts Published Today**: {social_stats['posts_published_today']} posts
- **Platforms**: {platform_breakdown_str}
- **Last Post**: {social_stats['last_post'].strftime('%H:%M') if social_stats['last_post'] else 'Never'} ({_format_time_ago(social_stats['last_post']) if social_stats['last_post'] else 'N/A'})
- **Success Rate**: {social_success_rate:.0f}% ({social_stats['success_count']}/{social_stats['total_count']} successful)

"""

# Calculate WhatsApp message statistics (Silver Tier - T068)
whatsapp_stats = {
    'messages_received_today': 0,
    'high_priority_count': 0,
    'last_message': None
}

# Count WhatsApp messages from today's logs
if today_log_file.exists():
    with open(today_log_file, 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get('action_type') == 'whatsapp_detect':
                    whatsapp_stats['messages_received_today'] += 1

                    # Count high priority messages
                    priority = log_entry.get('parameters', {}).get('priority', 'medium')
                    if priority == 'high':
                        whatsapp_stats['high_priority_count'] += 1

                    # Track most recent message
                    msg_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    if whatsapp_stats['last_message'] is None or msg_time > whatsapp_stats['last_message']:
                        whatsapp_stats['last_message'] = msg_time
            except (json.JSONDecodeError, KeyError):
                pass

# Add WhatsApp statistics to execution section (Silver Tier - T068)
exec_stats_section += f"""
**WhatsApp Messages:**
- **Messages Received Today**: {whatsapp_stats['messages_received_today']} messages
- **High Priority**: {whatsapp_stats['high_priority_count']} messages
- **Last Message**: {whatsapp_stats['last_message'].strftime('%H:%M') if whatsapp_stats['last_message'] else 'Never'} ({_format_time_ago(whatsapp_stats['last_message']) if whatsapp_stats['last_message'] else 'N/A'})

"""

# Calculate scheduled task statistics (Silver Tier - T087)
scheduler_stats = {
    'tasks_executed_today': 0,
    'last_execution': None,
    'next_execution': None,
    'tasks_configured': 0
}

# Count scheduled task executions from today's logs
if today_log_file.exists():
    with open(today_log_file, 'r') as f:
        for line in f:
            try:
                log_entry = json.loads(line.strip())
                if log_entry.get('action_type') == 'scheduled_task':
                    scheduler_stats['tasks_executed_today'] += 1

                    # Track most recent execution
                    task_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    if scheduler_stats['last_execution'] is None or task_time > scheduler_stats['last_execution']:
                        scheduler_stats['last_execution'] = task_time
            except (json.JSONDecodeError, KeyError):
                pass

# Read schedule state for next execution
schedule_state_file = vault_path / 'Logs' / 'schedule_state.json'
if schedule_state_file.exists():
    try:
        with open(schedule_state_file, 'r') as f:
            schedule_state = json.load(f)
            scheduler_stats['tasks_configured'] = len(schedule_state.get('tasks', {}))

            # Find next scheduled task
            next_times = []
            for task_data in schedule_state.get('tasks', {}).values():
                if task_data.get('enabled') and task_data.get('next_execution'):
                    next_times.append(task_data['next_execution'])

            if next_times:
                next_time_str = min(next_times)
                scheduler_stats['next_execution'] = datetime.fromisoformat(next_time_str.replace('Z', '+00:00'))
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        pass

# Add scheduled task statistics to execution section (Silver Tier - T087)
exec_stats_section += f"""
**Scheduled Tasks:**
- **Tasks Configured**: {scheduler_stats['tasks_configured']} tasks
- **Executed Today**: {scheduler_stats['tasks_executed_today']} tasks
- **Last Execution**: {scheduler_stats['last_execution'].strftime('%H:%M') if scheduler_stats['last_execution'] else 'Never'} ({_format_time_ago(scheduler_stats['last_execution']) if scheduler_stats['last_execution'] else 'N/A'})
- **Next Execution**: {scheduler_stats['next_execution'].strftime('%H:%M') if scheduler_stats['next_execution'] else 'Not scheduled'} ({_format_time_until(scheduler_stats['next_execution']) if scheduler_stats['next_execution'] else 'N/A'})

"""

# Insert execution statistics before the footer
markdown = markdown.replace(
    "---\n\n*This dashboard is automatically updated",
    exec_stats_section + "---\n\n*This dashboard is automatically updated"
)

# Write Dashboard.md
vault.write_markdown('Dashboard.md', markdown)

# Helper function for time ago formatting
def _format_time_ago(timestamp):
    """Format timestamp as 'X minutes ago' or 'X hours ago'."""
    if not timestamp:
        return 'N/A'
    delta = datetime.now(timezone.utc) - timestamp
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = int(minutes / 60)
    return f"{hours} hour{'s' if hours != 1 else ''} ago"

# Helper function for time until formatting
def _format_time_until(timestamp):
    """Format timestamp as 'in X minutes' or 'in X hours'."""
    if not timestamp:
        return 'N/A'
    delta = timestamp - datetime.now(timezone.utc)
    if delta.total_seconds() < 0:
        return 'Overdue'
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"in {minutes} minute{'s' if minutes != 1 else ''}"
    hours = int(minutes / 60)
    return f"in {hours} hour{'s' if hours != 1 else ''}"

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
