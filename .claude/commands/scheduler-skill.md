# Scheduler Skill - Silver Tier US4

**Purpose**: Configure and execute time-based automated tasks (daily briefings, weekly summaries, custom tasks).

**Capability**: Silver Tier - Autonomous execution of scheduled tasks using APScheduler.

---

## Overview

The Scheduler enables the AI Employee to execute tasks automatically at specified times using cron-based scheduling. Tasks are configured in `Company_Handbook.md` and executed by the scheduler background process.

**Supported Task Types**:
- **Daily Briefing**: Morning/evening summaries with pending items, completions, urgent tasks
- **Weekly Summary**: Weekly performance metrics, completed tasks, time saved
- **Custom Tasks**: User-defined automated actions (reminders, archiving, notifications)

**Core Workflow**:
1. Configure scheduled tasks in Company_Handbook.md
2. Scheduler loads tasks on startup
3. APScheduler executes tasks at specified times
4. Output created in /Needs_Action/ (or custom folder)
5. Missed executions caught up (within 1-hour grace period)
6. Handbook changes reload tasks automatically

---

## Configuring Scheduled Tasks

### Company_Handbook.md Format

Add scheduled tasks to handbook frontmatter:

```yaml
---
scheduled_tasks:
  - task_id: daily_briefing_morning
    task_name: "Morning Briefing"
    task_type: daily_briefing
    schedule_pattern: "0 9 * * *"
    recurrence_rule: "Daily at 9:00 AM"
    enabled: true
    output_path: "Needs_Action"
    parameters:
      include_urgent: true
      include_completions: true

  - task_id: weekly_summary_friday
    task_name: "Weekly Summary"
    task_type: weekly_summary
    schedule_pattern: "0 17 * * 5"
    recurrence_rule: "Weekly on Friday at 5:00 PM"
    enabled: true
    output_path: "Needs_Action"
    parameters:
      include_metrics: true

  - task_id: custom_reminder
    task_name: "End of Month Reminder"
    task_type: custom
    schedule_pattern: "0 9 28-31 * *"
    recurrence_rule: "Last few days of month at 9:00 AM"
    enabled: true
    output_path: "Needs_Action"
    parameters:
      action: "create_reminder"
      reminder_text: "Review monthly expenses and prepare report"
---
```

### Schedule Patterns (Cron Format)

Format: `minute hour day month weekday`

**Common Patterns**:
```
0 9 * * *       # Daily at 9:00 AM
0 17 * * 5      # Weekly on Friday at 5:00 PM
0 0 1 * *       # Monthly on 1st at midnight
*/15 * * * *    # Every 15 minutes
0 9,17 * * *    # Daily at 9 AM and 5 PM
```

**Field Values**:
- **minute**: 0-59
- **hour**: 0-23 (UTC timezone)
- **day**: 1-31
- **month**: 1-12
- **weekday**: 0-6 (0=Sunday, 1=Monday, ..., 6=Saturday)

**Special Characters**:
- `*` - Any value
- `*/N` - Every N units (e.g., */15 = every 15 minutes)
- `N-M` - Range (e.g., 9-17 = 9 AM to 5 PM)
- `N,M` - List (e.g., 1,15 = 1st and 15th)

### Task Configuration Fields

**Required**:
- `task_id`: Unique identifier (e.g., "daily_briefing_001")
- `task_name`: Human-readable name
- `task_type`: daily_briefing | weekly_summary | custom
- `schedule_pattern`: Cron expression

**Optional**:
- `recurrence_rule`: Human-readable description (for documentation)
- `enabled`: true | false (default: true)
- `output_path`: Folder for output (default: "Needs_Action")
- `parameters`: Task-specific settings (dict)

---

## Task Types

### 1. Daily Briefing

**Purpose**: Generate morning/evening briefings with system status and action items.

**Configuration**:
```yaml
- task_id: morning_briefing
  task_name: "Morning Briefing"
  task_type: daily_briefing
  schedule_pattern: "0 9 * * *"
  enabled: true
  parameters:
    include_urgent: true
    include_completions: true
```

**Generated Content**:
- **Overview**: Pending actions count, pending approvals count, system health
- **Recent Completions**: Tasks completed in last 24 hours
- **Urgent Items**: High priority messages, overdue plans
- **System Health**: Watcher statuses (Gmail, WhatsApp, etc.)
- **Recommended Actions**: Prioritized next steps

**Output**: `/Needs_Action/BRIEFING_YYYYMMDD.md`

### 2. Weekly Summary

**Purpose**: Generate weekly performance reports with metrics and trends.

**Configuration**:
```yaml
- task_id: weekly_summary
  task_name: "Weekly Summary"
  task_type: weekly_summary
  schedule_pattern: "0 17 * * 5"
  enabled: true
  parameters:
    include_metrics: true
```

**Generated Content**:
- **Highlights**: Total tasks completed, emails processed, social posts, WhatsApp messages
- **Estimated Time Saved**: Hours saved by automation
- **Breakdown by Day**: Task distribution across week
- **System Performance**: Success rate, uptime, response time
- **Trends**: Comparison with previous week

**Output**: `/Needs_Action/SUMMARY_WEEK_YYYYMMDD.md`

### 3. Custom Tasks

**Purpose**: Execute user-defined automated actions.

**Supported Actions**:

#### create_reminder
```yaml
- task_id: reminder_monthly_report
  task_name: "Monthly Report Reminder"
  task_type: custom
  schedule_pattern: "0 9 1 * *"
  enabled: true
  parameters:
    action: "create_reminder"
    reminder_text: "Prepare monthly report for team meeting"
```

**Output**: `/Needs_Action/REMINDER_YYYYMMDD_HHMMSS.md`

#### archive_old_items
```yaml
- task_id: archive_old_done
  task_name: "Archive Old Items"
  task_type: custom
  schedule_pattern: "0 2 1 * *"
  enabled: true
  parameters:
    action: "archive_old_items"
    days_old: 30
```

**Behavior**: Moves items in /Done/ older than 30 days to archive

#### send_notification
```yaml
- task_id: notify_backup
  task_name: "Backup Reminder"
  task_type: custom
  schedule_pattern: "0 20 * * 0"
  enabled: true
  parameters:
    action: "send_notification"
    notification_text: "Time to backup vault"
```

**Behavior**: Creates notification (future: integrate with notification service)

---

## Scheduler Management

### Start Scheduler

```bash
pm2 start ecosystem.config.js --only scheduler
```

### View Logs

```bash
pm2 logs scheduler
```

### Restart Scheduler

```bash
pm2 restart scheduler
```

### Stop Scheduler

```bash
pm2 stop scheduler
```

### Monitor Status

```bash
pm2 status
```

---

## Task Execution

### Normal Execution

When scheduled time arrives:
1. Scheduler detects task is due
2. Executes task via SchedulerService
3. Creates output in specified folder
4. Updates last_execution and next_execution
5. Persists state to schedule_state.json
6. Logs execution to audit log

### Missed Execution Handling

**Grace Period**: 1 hour

**Behavior**:
- If task missed due to scheduler downtime
- And within grace period (1 hour)
- Task executes immediately on startup
- Next execution calculated from actual execution time

**Example**:
```
Scheduled: 9:00 AM
Scheduler down: 8:30 AM - 9:30 AM
Result: Task executes at 9:30 AM (within grace period)
Next: Calculated for next day at 9:00 AM
```

### State Persistence

**State File**: `/Logs/schedule_state.json`

**Contents**:
```json
{
  "last_updated": "2026-02-25T14:30:00Z",
  "tasks": {
    "daily_briefing_morning": {
      "task_id": "daily_briefing_morning",
      "task_name": "Morning Briefing",
      "last_execution": "2026-02-25T09:00:15Z",
      "next_execution": "2026-02-26T09:00:00Z",
      "enabled": true,
      "updated_at": "2026-02-25T09:00:15Z"
    }
  }
}
```

**Purpose**: Tracks execution history across scheduler restarts

---

## Dynamic Reloading

**Feature**: Handbook changes reload tasks automatically (no restart needed)

**Process**:
1. Scheduler monitors Company_Handbook.md every 30 seconds
2. Detects file modification time change
3. Reloads all scheduled tasks from handbook
4. Updates APScheduler jobs
5. Logs reload event

**Use Cases**:
- Add new scheduled task → Reloads within 30 seconds
- Modify schedule pattern → Next execution recalculated
- Disable task → Job removed from scheduler
- Enable disabled task → Job added back to scheduler

---

## Troubleshooting

### Issue: Task Not Executing

**Check**:
1. Scheduler running: `pm2 status scheduler`
2. Task enabled in handbook: `enabled: true`
3. Schedule pattern valid: Check cron syntax
4. Next execution time: Check schedule_state.json
5. Logs for errors: `pm2 logs scheduler`

### Issue: Missed Executions Not Catching Up

**Check**:
1. Grace period (1 hour): Missed time > 1 hour ago won't catch up
2. Task enabled: Disabled tasks don't catch up
3. Scheduler was running: If never started, can't detect missed execution

**Solution**: Adjust grace period in code if needed (default: 60 minutes)

### Issue: Handbook Changes Not Reloading

**Check**:
1. File save completed: Ensure file write finished
2. Modification time updated: Check `ls -la Company_Handbook.md`
3. Scheduler running: Must be running to detect changes
4. Check logs: Look for "reloading tasks" message

**Solution**: Restart scheduler if reload fails: `pm2 restart scheduler`

### Issue: Invalid Cron Pattern

**Symptoms**: Task not loaded, error in logs

**Common Mistakes**:
- Wrong number of fields (need exactly 5)
- Invalid range (e.g., hour=25)
- Spaces in pattern

**Valid Examples**:
```
✓ 0 9 * * *       # Correct
✗ 0 9 * *         # Missing weekday field
✗ 0 25 * * *      # Invalid hour (25)
✗ 0  9 * * *      # Double space
```

---

## Best Practices

### 1. Task Naming

**Good**:
- `daily_briefing_morning` (descriptive, unique)
- `weekly_summary_friday`
- `reminder_monthly_expenses`

**Bad**:
- `task1` (not descriptive)
- `briefing` (too generic, may conflict)
- `my task` (spaces not allowed)

### 2. Schedule Patterns

**Do**:
- Use UTC timezone for consistency
- Test patterns with online cron calculator
- Document recurrence_rule for clarity
- Start with conservative frequency (e.g., daily, not every minute)

**Don't**:
- Schedule too frequently (every minute causes load)
- Forget timezone (9 AM local ≠ 9 AM UTC)
- Overlap tasks (avoid running multiple heavy tasks simultaneously)

### 3. Output Management

**Do**:
- Use descriptive output filenames (include date/time)
- Clean up old briefings/summaries periodically
- Review generated content regularly

**Don't**:
- Ignore accumulated briefings (they pile up)
- Forget to process urgent items from briefings

### 4. Monitoring

**Do**:
- Check scheduler heartbeat in Dashboard.md
- Review execution logs weekly
- Verify scheduled tasks execute on time
- Monitor missed execution alerts

**Don't**:
- Ignore scheduler downtime
- Let schedule_state.json grow indefinitely (future: cleanup old state)

---

## Dashboard Integration

Scheduler statistics appear on Dashboard.md:

```markdown
## Scheduled Tasks

- **Tasks Configured**: 3 tasks
- **Tasks Executed Today**: 2 tasks
- **Next Execution**: Morning Briefing at 09:00 (in 12 hours)
- **Scheduler Status**: ✅ Running
```

---

## Future Enhancements (Gold Tier)

- **Conditional Execution**: Run task only if condition met (e.g., "only if pending > 10")
- **Task Dependencies**: Chain tasks (task B runs after task A completes)
- **Notification Integration**: Send briefings via email/Slack
- **Advanced Custom Actions**: More built-in custom actions
- **Task History Dashboard**: View execution history in Obsidian
- **Manual Task Trigger**: Run scheduled task on-demand via CLI

---

**Version**: Silver Tier 0.2.0
**Last Updated**: 2026-02-25
**Related**: dashboard-updater.md, vault-manager.md
