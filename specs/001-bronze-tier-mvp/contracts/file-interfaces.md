# File Interface Contracts: Bronze Tier MVP

**Feature**: 001-bronze-tier-mvp
**Date**: 2026-02-21
**Type**: File-based interfaces (no HTTP APIs in Bronze tier)

## Overview

Bronze Tier MVP uses file-based interfaces instead of HTTP APIs. All components interact by reading/writing Markdown files in the Obsidian vault. This document defines the contracts for these file-based interfaces.

---

## Contract 1: Gmail Watcher → Vault (Email Detection)

**Interface**: Write Email entity to `/Needs_Action/EMAIL_{email_id}.md`

**Trigger**: Gmail Watcher detects new important/urgent email via Gmail API

**Input**:
- Gmail message object from API
- Configured urgent keywords list

**Output File Format**:

```yaml
# Frontmatter (YAML)
---
type: email
email_id: string                # Gmail message ID
from: string                    # Sender email address
subject: string                 # Email subject
received: datetime              # ISO 8601 timestamp
priority: "high" | "medium"     # Based on importance/keywords
status: "pending"               # Always "pending" when created
---

# Body (Markdown)
## Email Content

{snippet - first 200 chars of email body}

## Suggested Actions

- [ ] {action 1}
- [ ] {action 2}
...
```

**Validation**:
- email_id must be unique (check existing files before creating)
- received timestamp in UTC (ISO 8601)
- priority="high" if Gmail "important" label OR urgent keyword in subject
- File created atomically (write to temp file, then move)

**Error Handling**:
- If file already exists: Skip (duplicate detection via .watcher_state.json)
- If vault folder missing: Create `/Needs_Action/` folder
- If write fails: Log error, retry with exponential backoff (3 attempts)

---

## Contract 2: File System Watcher → Vault (File Drop)

**Interface**: Copy file + create metadata in `/Needs_Action/`

**Trigger**: File System Watcher detects new file in `/Inbox/`

**Input**:
- File path from watchdog event
- File metadata (size, extension, modification time)

**Output 1**: Actual file copied to `/Needs_Action/{filename_with_timestamp}`

**Output 2**: Metadata file at `/Needs_Action/FILE_{timestamp}_{filename}.md`

```yaml
# Frontmatter (YAML)
---
type: file_drop
original_name: string           # Original filename
file_path: string               # Absolute path to copied file
size: integer                   # File size in bytes
file_type: string               # File extension with dot (.pdf, .docx)
received: datetime              # ISO 8601 timestamp
status: "pending" | "quarantined"
quarantined: boolean            # true if unsafe file type
---

# Body (Markdown)
## File Information

A new file was dropped into the Inbox for processing.

**Location**: `{relative_path_to_file}`
**Size**: {human_readable_size}
**Type**: {file_type_description}

## Suggested Actions

- [ ] Review file content
- [ ] {context-specific action}
```

**Unsafe File Types** (FR-011):
- Extensions: `.exe`, `.dmg`, `.app`, `.bat`, `.sh`, `.cmd`, `.msi`, `.dll`
- Action: Move file to `/Quarantine/`, set quarantined=true, create alert

**Alert File** (if quarantined):
- Path: `/Needs_Action/ALERT_quarantined_{filename}.md`
- Content: Warning message with quarantine reason

**Validation**:
- Filename conflicts resolved by appending timestamp
- size must be > 0 and < 100MB (practical limit for Bronze tier)
- file_type must start with "."

**Error Handling**:
- If copy fails: Log error, leave file in /Inbox, retry after 5 seconds
- If quarantine folder missing: Create `/Quarantine/` folder
- If disk full: Create alert, stop processing

---

## Contract 3: Claude Code (vault-manager skill) → Plans

**Interface**: Read from `/Needs_Action/`, write Plan to `/Plans/`

**Trigger**: Orchestrator detects new file in `/Needs_Action/`, invokes vault-manager skill

**Input**:
- Path to Email or FileDrop .md file
- Company_Handbook.md rules for context

**Output File Format**: `/Plans/PLAN_{id}_{title_slug}.md`

```yaml
# Frontmatter (YAML)
---
plan_id: string                 # Sequential: PLAN_001, PLAN_002, etc.
title: string                   # Brief plan title (3-10 words)
source_type: "email" | "file_drop"
source_id: string               # email_id or FileDrop timestamp
created: datetime               # ISO 8601 timestamp
objective: string               # 1-2 sentence goal
approval_required: boolean      # true if sensitive action detected
approval_file: string | null    # Path to /Pending_Approval file if needed
status: "draft" | "awaiting_approval" | "complete"
---

# Body (Markdown)
## Objective

{1-2 sentence description of what needs to be done}

## Steps

- [ ] 1. {first step}
- [ ] 2. {second step}
- [ ] 3. {third step}
...
- [ ] N. {final step}

{IF approval_required}
## Approval Required

This plan involves {sensitive action description}.

**Review approval request**: [{approval_file_name}]({relative_link})

To approve: Move approval file to `/Approved/` folder (Silver tier feature)
{END IF}
```

**Step Count Validation** (FR-014):
- Minimum: 3 steps
- Maximum: 7 steps
- If source is unclear, include "Request clarification from user" as first step

**Approval Detection**:
- Set approval_required=true if steps mention:
  - "send email" to new contact
  - "payment" over $100
  - "delete" or "remove" (irreversible)
  - "post" on social media (DM/reply)

**Approval File Creation** (if approval_required=true):
- Path: `/Pending_Approval/APPROVAL_{context}_{date}.md`
- Content: Summary of action + approval instructions
- Link from Plan.md to approval file

**Error Handling**:
- If source file malformed: Create plan with "Review malformed input" step
- If plan_id collision: Increment ID and retry
- If Company_Handbook.md missing: Use default rules from constitution

---

## Contract 4: Dashboard Updater → Dashboard.md

**Interface**: Update `/Dashboard.md` with current system state

**Trigger**:
- New file added to /Needs_Action
- Plan created in /Plans
- File moved to /Done
- Every 60 seconds (periodic refresh)

**Input**:
- Scan `/Needs_Action/` folder (count .md files)
- Scan `/Pending_Approval/` folder (count .md files)
- Read `/Logs/heartbeat.json` for watcher status
- Read recent entries from `/Logs/{date}.json` for activity

**Output File Format**: `/Dashboard.md` (overwrite entire file)

```markdown
# AI Employee Dashboard

**Last Updated**: {ISO 8601 timestamp}

## Status Overview

- **Pending Actions**: {count} items
- **Pending Approvals**: {count} items
- **System Health**: {✅ Healthy | ⚠️ Degraded | ❌ Down}

## Recent Activity

1. [{HH:MM}] {action}: {description} → {target_path}
2. [{HH:MM}] {action}: {description} → {target_path}
3. [{HH:MM}] {action}: {description} → {target_path}
4. [{HH:MM}] {action}: {description} → {target_path}
5. [{HH:MM}] {action}: {description} → {target_path}

## Watchers Status

- **Gmail Watcher**: {✅ Running | ⚠️ Stale | ❌ Stopped} (last check: {HH:MM})
- **File System Watcher**: {✅ Running | ⚠️ Stale | ❌ Stopped} (last heartbeat: {HH:MM})
- **Orchestrator**: {✅ Running | ❌ Stopped}

---

*This dashboard is automatically updated by the AI Employee system*
```

**Counts Calculation**:
```python
pending_actions = len([f for f in Path(vault/"Needs_Action").glob("*.md")])
pending_approvals = len([f for f in Path(vault/"Pending_Approval").glob("*.md")])
```

**Health Status Logic**:
- ✅ Healthy: All watchers have heartbeat within last 5 minutes
- ⚠️ Degraded: Some watchers stale (heartbeat 5-15 minutes old)
- ❌ Down: All watchers stopped (no heartbeat in 15+ minutes)

**Recent Activity**:
- Read last 50 entries from current day's log file
- Filter for user-visible actions (email_detected, file_dropped, plan_created, task_completed)
- Take most recent 5 entries
- Format as bullet list with timestamp, action, target

**Update Frequency**:
- Target: <60 seconds from state change (SC-006)
- Periodic: Every 60 seconds via orchestrator cron
- Event-driven: Immediately after new file/plan created

**Error Handling**:
- If folder scan fails: Show last known count with "(stale)" indicator
- If heartbeat.json missing: Show "Unknown" status for watchers
- If log file missing: Show "No recent activity"

---

## Contract 5: Watcher Heartbeat → Logs

**Interface**: Write health status to `/Logs/heartbeat.json`

**Trigger**: Every 60 seconds from each watcher process (FR-020)

**Output File Format**: `/Logs/heartbeat.json` (overwrite)

```json
{
  "gmail_watcher": {
    "timestamp": "2026-02-21T14:50:00.123Z",
    "status": "running",
    "last_check": "2026-02-21T14:49:45.678Z",
    "emails_processed_today": 12
  },
  "filesystem_watcher": {
    "timestamp": "2026-02-21T14:50:00.456Z",
    "status": "running",
    "files_processed_today": 3
  },
  "orchestrator": {
    "timestamp": "2026-02-21T14:50:00.789Z",
    "status": "running",
    "tasks_triggered_today": 15
  }
}
```

**Update Pattern**:
- Each watcher updates only its own section
- Use file locking or atomic write (write to temp, rename) to avoid corruption
- Timestamp must be current UTC time (not cached)

**Staleness Detection**:
- Fresh: timestamp within last 5 minutes
- Stale: timestamp 5-15 minutes old
- Dead: timestamp 15+ minutes old or key missing

---

## Contract 6: Audit Logger → Logs

**Interface**: Append log entry to `/Logs/{YYYY-MM-DD}.json`

**Trigger**: Any significant action by watchers or Claude Code

**Output Format**: One JSON object per line (newline-delimited JSON)

```json
{"timestamp":"2026-02-21T14:30:00.123Z","action_type":"email_detected","actor":"gmail_watcher","target":"client@example.com","parameters":{"subject":"Urgent invoice request","email_id":"ABC123"},"approval_status":"pending","approved_by":null,"result":"success"}
{"timestamp":"2026-02-21T14:35:00.456Z","action_type":"file_dropped","actor":"filesystem_watcher","target":"contract.pdf","parameters":{"size":524288,"file_type":".pdf"},"approval_status":"pending","approved_by":null,"result":"success"}
{"timestamp":"2026-02-21T14:45:00.789Z","action_type":"plan_created","actor":"claude_code","target":"/Plans/PLAN_001.md","parameters":{"source_type":"email","source_id":"ABC123"},"approval_status":"awaiting_approval","approved_by":null,"result":"success"}
```

**Required Fields** (from Constitution Principle III):
- timestamp: ISO 8601 UTC
- action_type: email_detected|file_dropped|plan_created|task_completed|error
- actor: gmail_watcher|filesystem_watcher|claude_code|orchestrator|human
- target: Email address, filename, or file path
- parameters: JSON object with action-specific details
- approval_status: pending|awaiting_approval|approved|rejected
- approved_by: human|auto|null
- result: success|failure|error

**Log Rotation**:
- New file created each day (YYYY-MM-DD.json)
- No automatic deletion (manual cleanup or Silver tier retention script)
- Retention requirement: 90 days minimum (per Constitution)

**Error Handling**:
- If log write fails: Buffer entry in memory, retry after 5 seconds
- If disk full: Alert user, stop processing
- If date changes mid-write: Start new file for new date

---

## Contract Summary Table

| Contract | Producer | Consumer | File Location | Trigger | Frequency |
|----------|----------|----------|---------------|---------|-----------|
| Email Detection | Gmail Watcher | Claude Code | /Needs_Action/EMAIL_*.md | Gmail API poll | Every 2 min |
| File Drop | FS Watcher | Claude Code | /Needs_Action/FILE_*.md | File created in /Inbox | Event-driven |
| Plan Creation | Claude Code | Human/Dashboard | /Plans/PLAN_*.md | Orchestrator | On new item |
| Dashboard Update | Dashboard Updater | Human (Obsidian) | /Dashboard.md | State change | <60 sec |
| Heartbeat | All Watchers | Dashboard | /Logs/heartbeat.json | Timer | Every 60 sec |
| Audit Log | All Components | Human/Analytics | /Logs/YYYY-MM-DD.json | Any action | Immediately |

**All contracts use file-based communication** (no HTTP/network in Bronze tier)

**Interface validation enforced by**:
- Watchers: Validate before writing
- Claude Code skills: Parse and validate frontmatter
- Dashboard updater: Count-based validation

**Ready for quickstart.md creation (Phase 1 continued).**
