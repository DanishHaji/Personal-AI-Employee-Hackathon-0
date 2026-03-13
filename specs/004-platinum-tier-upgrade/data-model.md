# Data Model: Platinum Tier - Always-On Cloud + Local Executive

**Feature**: 004-platinum-tier-upgrade
**Created**: 2026-03-04
**Status**: Design Complete

## Overview

Platinum Tier extends Gold Tier's file-based data model with distributed system entities supporting Cloud-Local work-zone specialization, vault synchronization, health monitoring, and Odoo integration.

**Storage Pattern**: Markdown files with YAML frontmatter + JSON for structured logs (consistent with Bronze/Silver/Gold Tiers)

**New Vault Folders**:
- `/Cloud_Drafts/` - Drafts created by Cloud instance awaiting Local review
- `/Needs_Local/` - Tasks requiring Local-only execution (secrets, WhatsApp, banking)
- `/Claims/` - Advisory lock files for task ownership (Cloud or Local)
- `/Health/` - Health status snapshots from Cloud and Local instances

---

## Entities

### 1. Work Zone Configuration

**Purpose**: Defines Cloud vs Local capabilities and routing rules

**File**: `vault/Company_Handbook.md` (extends existing)

**Schema**:
```yaml
work_zones:
  cloud:
    enabled: true
    capabilities:
      - email_triage
      - draft_responses
      - schedule_monitoring
      - odoo_read
      - analytics_generation
    restrictions:
      - no_whatsapp_access
      - no_banking_credentials
      - no_local_file_write

  local:
    enabled: true
    capabilities:
      - approve_cloud_drafts
      - whatsapp_send
      - banking_transactions
      - secret_management
      - local_file_operations
    exclusive_secrets:
      - whatsapp_session
      - banking_credentials
      - oauth_tokens_sensitive

routing_rules:
  - pattern: "EMAIL_*"
    action: "reply_draft"
    zone: "cloud"
    requires_approval: true

  - pattern: "WHATSAPP_*"
    action: "send_message"
    zone: "local"
    requires_approval: false  # Trust level determines

  - pattern: "EXPENSE_*"
    action: "sync_to_odoo"
    zone: "cloud"
    requires_approval: true
```

**Relationships**:
- References trust rules from Gold Tier
- Used by ClaimManager to route tasks
- Consulted by Executor to determine work zone

**Validation Rules**:
- At least one zone must be enabled
- No capability can be listed in both zones
- Exclusive secrets must never appear in cloud capabilities

**State Transitions**: N/A (configuration file)

---

### 2. Sync Event

**Purpose**: Tracks vault synchronization operations between Cloud and Local

**File**: `vault/Logs/sync.jsonl` (append-only log)

**Schema**:
```json
{
  "sync_id": "SYNC_20260304_153022",
  "timestamp": "2026-03-04T15:30:22.451Z",
  "direction": "local_to_cloud",
  "initiator": "local",
  "status": "completed",
  "files_changed": 5,
  "files_added": ["Needs_Action/EMAIL_001.md"],
  "files_modified": ["Dashboard.md", "Contacts/CONTACT_005.md"],
  "files_deleted": [],
  "secrets_filtered": 2,
  "secrets_blocked": [".env", "whatsapp_session/qr.png"],
  "conflicts_detected": 0,
  "conflicts": [],
  "duration_ms": 1847,
  "git_commit": "a3f5c2d",
  "error": null
}
```

**Relationships**:
- References files in vault
- Links to Git commits
- Creates SyncConflict entities when conflicts detected

**Validation Rules**:
- `direction` must be one of: `local_to_cloud`, `cloud_to_local`, `bidirectional`
- `status` must be one of: `started`, `completed`, `failed`, `conflict`
- `secrets_filtered` must equal length of `secrets_blocked` array
- If `status=conflict`, `conflicts` array must not be empty

**State Transitions**:
```
started → completed (success)
started → failed (error)
started → conflict (merge conflict detected)
conflict → completed (after manual resolution)
```

---

### 3. Sync Conflict

**Purpose**: Records merge conflicts requiring manual resolution

**File**: `vault/Logs/sync_conflicts.jsonl`

**Schema**:
```json
{
  "conflict_id": "CONFLICT_20260304_153045",
  "sync_id": "SYNC_20260304_153022",
  "timestamp": "2026-03-04T15:30:45.128Z",
  "file_path": "Needs_Action/ACTION_send_reply.md",
  "conflict_type": "simultaneous_edit",
  "local_version": "vault/Needs_Action/ACTION_send_reply.md",
  "cloud_version": "vault/Needs_Action/ACTION_send_reply-cloud.md",
  "local_modified": "2026-03-04T15:28:12Z",
  "cloud_modified": "2026-03-04T15:29:33Z",
  "resolved": false,
  "resolution_strategy": null,
  "resolved_at": null,
  "resolved_by": null
}
```

**Relationships**:
- Child of SyncEvent
- References conflicting files in vault

**Validation Rules**:
- `conflict_type` must be one of: `simultaneous_edit`, `delete_modify`, `rename_rename`
- If `resolved=true`, `resolution_strategy`, `resolved_at`, and `resolved_by` must be set

**State Transitions**:
```
created (resolved=false) → resolved (resolved=true)
```

**Resolution Strategies**:
- `keep_local` - Discard cloud changes
- `keep_cloud` - Discard local changes
- `manual_merge` - Human merged both versions
- `keep_both` - Both versions saved with suffixes

---

### 4. Claim

**Purpose**: Establishes task ownership by Cloud or Local instance (advisory lock)

**File**: `vault/Claims/{task_id}.claim.md`

**Schema**:
```yaml
---
claim_id: CLAIM_20260304_153100
task_id: EMAIL_20260304_152150
task_file: Needs_Action/EMAIL_20260304_152150_Meeting_Request.md
claimed_by: cloud
claimed_at: 2026-03-04T15:31:00Z
expires_at: 2026-03-04T15:46:00Z  # 15-minute TTL
zone: cloud
action_type: draft_response
status: active
released_at: null
released_by: null
---

# Claim: EMAIL_20260304_152150

**Claimed By**: Cloud Instance
**Purpose**: Drafting response to meeting request

## Claim Details

- **Task**: Process meeting request email
- **Zone**: Cloud (triage and draft)
- **Expected Duration**: ~5 minutes
- **Expiry**: 15 minutes from claim

## Status

Active claim. Local instance should not process this task.
```

**Relationships**:
- References task file in vault
- Enforced by ClaimManager
- Checked by Executor before processing tasks

**Validation Rules**:
- `claimed_by` must be one of: `cloud`, `local`
- `zone` must match `claimed_by` zone capabilities
- `expires_at` must be future timestamp
- `status` must be one of: `active`, `released`, `expired`, `violated`

**State Transitions**:
```
created (status=active) → released (manual release)
created (status=active) → expired (TTL reached)
active → violated (other instance processed despite claim)
```

**TTL Behavior**:
- Claims expire after 15 minutes by default
- Expired claims automatically become `status=expired`
- Either instance can claim expired tasks

---

### 5. Health Status

**Purpose**: Snapshots system health for monitoring and alerting

**File**: `vault/Health/{instance}_{timestamp}.health.json`

**Schema**:
```json
{
  "health_id": "HEALTH_cloud_20260304_153000",
  "instance": "cloud",
  "timestamp": "2026-03-04T15:30:00Z",
  "uptime_seconds": 86420,
  "status": "healthy",
  "watchers": {
    "gmail_watcher": {
      "pid": 12345,
      "status": "running",
      "uptime_seconds": 86400,
      "last_check": "2026-03-04T15:29:55Z",
      "events_processed_today": 47,
      "errors_last_hour": 0
    },
    "filesystem_watcher": {
      "pid": 12346,
      "status": "running",
      "uptime_seconds": 86400,
      "last_check": "2026-03-04T15:29:58Z",
      "events_processed_today": 12,
      "errors_last_hour": 0
    },
    "scheduler": {
      "pid": 12347,
      "status": "running",
      "uptime_seconds": 86400,
      "last_check": "2026-03-04T15:30:00Z",
      "jobs_run_today": 8,
      "errors_last_hour": 0
    }
  },
  "resources": {
    "cpu_percent": 12.5,
    "memory_mb": 487,
    "disk_usage_percent": 42,
    "disk_free_gb": 28.3
  },
  "vault_sync": {
    "last_sync": "2026-03-04T15:28:15Z",
    "sync_status": "success",
    "seconds_since_sync": 105,
    "pending_changes": 0
  },
  "alerts": []
}
```

**Relationships**:
- Referenced by HealthMonitor
- Used by AlertManager to trigger notifications
- Aggregated for weekly health reports

**Validation Rules**:
- `instance` must be one of: `cloud`, `local`
- `status` must be one of: `healthy`, `degraded`, `critical`, `offline`
- All watcher PIDs must be positive integers
- Resource percentages must be 0-100

**State Determination**:
```python
if any watcher crashed or disk >90% or memory >90%:
    status = "critical"
elif any watcher errors >10/hour or disk >80%:
    status = "degraded"
else:
    status = "healthy"
```

**Alert Triggers**:
- `critical` status → immediate email/webhook alert
- `degraded` for >1 hour → warning notification
- 3 consecutive watcher crashes → escalation alert

---

### 6. Cloud Draft

**Purpose**: Response/action drafted by Cloud instance awaiting Local approval

**File**: `vault/Cloud_Drafts/DRAFT_{task_id}.md`

**Schema**:
```yaml
---
draft_id: DRAFT_EMAIL_20260304_152150
task_id: EMAIL_20260304_152150
task_file: Needs_Action/EMAIL_20260304_152150_Meeting_Request.md
drafted_by: cloud
drafted_at: 2026-03-04T15:35:00Z
action_type: email_reply
status: pending_review
reviewed_at: null
approved_by: null
---

# Draft: Reply to Meeting Request

**Original Task**: Meeting request from client
**Action**: Send email reply with proposed meeting times

## Draft Content

**To**: client@example.com
**Subject**: Re: Meeting Request - Q2 Planning

Hi [Name],

Thank you for reaching out. I'm available for the Q2 planning meeting.

Here are three time slots that work for me:
- Tuesday, March 10 at 2:00 PM
- Wednesday, March 11 at 10:00 AM
- Thursday, March 12 at 3:00 PM

Please let me know which works best for you, and I'll send a calendar invite.

Best regards,
[Your Name]

## Metadata

- **Confidence**: High (similar requests processed successfully)
- **Risk Level**: Low (standard meeting coordination)
- **Estimated Approval Time**: <2 minutes

## Next Steps

Move to `/Pending_Approval/` when Local instance comes online.
```

**Relationships**:
- References original task in Needs_Action
- Moved to Pending_Approval by Local instance
- Becomes Email or Action entity after approval

**Validation Rules**:
- `drafted_by` must be `cloud`
- `status` must be one of: `pending_review`, `approved`, `rejected`, `revised`
- If `status=approved`, `approved_by` must be `local`

**State Transitions**:
```
created (pending_review) → approved (Local approves)
created (pending_review) → rejected (Local rejects)
pending_review → revised (Cloud updates draft based on feedback)
approved → executed (becomes final action)
```

---

### 7. Odoo Entry

**Purpose**: Financial transaction synced between AI Employee and Odoo accounting system

**File**: Stored in Odoo database, referenced in `vault/Logs/odoo_sync.jsonl`

**Log Schema**:
```json
{
  "sync_id": "ODOO_SYNC_20260304_153500",
  "timestamp": "2026-03-04T15:35:00Z",
  "expense_id": "EXPENSE_002_AWS_20260304",
  "expense_file": "vault/Expenses/EXPENSE_002_Amazon_Web_Services_2026-03-04.md",
  "odoo_entry_id": 1247,
  "odoo_journal": "expenses",
  "amount": 289.50,
  "category": "cloud_services",
  "vendor": "Amazon Web Services",
  "date": "2026-03-04",
  "status": "synced",
  "sync_direction": "ai_to_odoo",
  "error": null
}
```

**Odoo Data Model** (via JSON-RPC API):
```json
{
  "id": 1247,
  "model": "account.move.line",
  "fields": {
    "name": "AWS Invoice - March 2026",
    "account_id": 42,  // Expenses account
    "debit": 289.50,
    "credit": 0.0,
    "date": "2026-03-04",
    "partner_id": 89,  // AWS vendor
    "analytic_account_id": 15,  // Cloud Services category
    "ref": "EXPENSE_002_AWS_20260304",
    "ai_employee_synced": true
  }
}
```

**Relationships**:
- References Expense entity from Gold Tier
- Links to Odoo partner (vendor) and account
- Tracked in odoo_sync.jsonl log

**Validation Rules**:
- `status` must be one of: `pending`, `synced`, `failed`
- `amount` must match expense file
- `odoo_entry_id` required if `status=synced`

**State Transitions**:
```
created (pending) → synced (Odoo API success)
created (pending) → failed (Odoo API error)
failed → synced (retry successful)
```

**Sync Strategy**:
- AI Employee is source of truth for expense creation
- Odoo provides accounting reports and budget alerts
- Bidirectional sync for budget warnings (Odoo → AI Employee)

---

### 8. Secret Filter Rule

**Purpose**: Defines patterns to exclude from Cloud sync (security boundary)

**File**: `.gitignore` (extends existing)

**Schema**:
```gitignore
# Platinum Tier - Secret Filtering Rules

# Environment files
.env
.env.*
*.env

# Credentials
*_credentials.json
*_token.txt
secrets/
credentials/

# WhatsApp session data
whatsapp_session/
*.session
*.qr.png

# Banking data
banking/
bank_*.json

# SSH keys
*.pem
*.key
id_rsa*

# OAuth tokens (sensitive services)
oauth_tokens_sensitive.json

# Local-only configuration
local.config.json
```

**Relationships**:
- Enforced by pre-commit hooks (detect-secrets)
- Consulted by sync script before push
- Violations logged in sync.jsonl

**Validation Rules**:
- Patterns must be valid .gitignore syntax
- Critical patterns (`.env`, `*_credentials.json`) cannot be removed

**Detection Tools**:
- `detect-secrets` scans for high-entropy strings
- `gitleaks` scans for known secret patterns
- Pre-commit hook blocks commits containing secrets

---

### 9. Delegation Metadata

**Purpose**: Tracks work delegation from Cloud to Local and vice versa

**File**: Added to existing entity YAML frontmatter

**Schema** (extends EMAIL/ACTION entities):
```yaml
---
# ... existing fields ...
delegation:
  created_by: cloud  # Which instance created this entity
  requires_zone: local  # Which zone must process it
  delegated_at: 2026-03-04T15:40:00Z
  reason: whatsapp_send_required  # Why Local is needed
  claimed_by: local
  claimed_at: 2026-03-04T16:05:00Z
---
```

**Relationships**:
- Embedded in task entities
- Referenced by ClaimManager
- Used by routing logic

**Validation Rules**:
- `created_by` must be one of: `cloud`, `local`
- `requires_zone` must be one of: `cloud`, `local`, `any`
- If `requires_zone=local`, task must not be processed by cloud

**Use Cases**:
- Cloud detects WhatsApp action → creates task with `requires_zone=local`
- Local is offline → Cloud queues task in `/Needs_Local/`
- Local comes online → claims and processes delegated tasks

---

## Entity Relationships Diagram

```
Company_Handbook (Work Zone Config)
    ↓ (defines routing)
Executor → ClaimManager → Claim
    ↓                       ↓
Task Entities ← ─ ─ ─ ─ ─ ┘
    ↓
Cloud Draft (if cloud) OR Direct Execution (if local)
    ↓
Sync Event ← ─ ─ ┐
    ↓            │
Odoo Entry       │ (tracks)
                 │
Health Status ─ ─┘
```

---

## Storage Calculations

**Estimated Storage (30 days)**:

| Entity | Daily Volume | Size per Entry | Monthly Total |
|--------|--------------|----------------|---------------|
| Sync Event | 96 (every 15min) | 0.5 KB | 1.4 MB |
| Claim | 50 tasks/day | 1 KB | 1.5 MB |
| Cloud Draft | 20 drafts/day | 2 KB | 1.2 MB |
| Health Status | 288 (every 5min) | 3 KB | 25.9 MB |
| Odoo Sync Log | 5 expenses/day | 0.3 KB | 45 KB |
| Sync Conflicts | 2/day (rare) | 0.5 KB | 30 KB |
| **Total** | - | - | **~30 MB/month** |

**Vault Size Impact**: Minimal (<1% of 10GB vault assumption)

---

## Migration from Gold Tier

**No Breaking Changes**: Platinum Tier extends Gold Tier entities, does not modify them.

**New Folders**:
```bash
vault/Cloud_Drafts/
vault/Needs_Local/
vault/Claims/
vault/Health/
```

**Extended Files**:
- `Company_Handbook.md` gets `work_zones` section
- Existing task entities get optional `delegation` metadata
- New JSONL logs: `sync.jsonl`, `odoo_sync.jsonl`, `sync_conflicts.jsonl`

**Backward Compatibility**: Gold Tier can continue operating if Platinum Tier cloud instance is offline (local-only mode).

---

## Validation Summary

**Mandatory Fields**: All entities have required fields marked in schemas
**Unique Identifiers**: All entities have unique IDs with timestamp-based generation
**Referential Integrity**: Cross-references validated by entity managers
**State Machines**: All stateful entities have defined state transitions
**Constraints**: Business rules enforced at service layer before write

---

*Data model complete. Ready for contract generation and implementation.*
