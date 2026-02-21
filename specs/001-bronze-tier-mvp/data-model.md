# Data Model: Bronze Tier MVP - Personal AI Employee

**Feature**: 001-bronze-tier-mvp
**Date**: 2026-02-21
**Phase**: 1 - Data Model Design

## Overview

This document defines the data entities for the Bronze Tier MVP. All entities are persisted as Markdown files with YAML frontmatter in the Obsidian vault (Local-First Privacy principle).

---

## Entity 1: Email

**Purpose**: Represents an incoming Gmail message detected by the Gmail Watcher

**Storage Location**: `/Needs_Action/EMAIL_{email_id}.md`

**Attributes**:

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| type | string | Yes | Entity type identifier | Must be "email" |
| email_id | string | Yes | Gmail message ID (unique) | Alphanumeric, from Gmail API |
| from | string | Yes | Sender email address | Valid email format |
| subject | string | Yes | Email subject line | Max 255 chars |
| received | datetime | Yes | Timestamp when email was received | ISO 8601 format |
| priority | enum | Yes | Priority level | "high" or "medium" |
| status | enum | Yes | Processing status | "pending", "processing", "done" |
| snippet | string | No | Email body preview (first 200 chars) | Max 200 chars |

**State Transitions**:
```
pending → processing (when Claude Code starts analyzing)
processing → done (when Plan.md created or moved to /Done)
```

**Relationships**:
- One Email can generate one Action Plan (1:1)
- Email file is moved to `/Done/` after processing

**Example** (Markdown + YAML):
```markdown
---
type: email
email_id: 18d4c5f2a3b1e9f0
from: client@example.com
subject: Urgent invoice request
received: 2026-02-21T14:30:00Z
priority: high
status: pending
---

## Email Content

Hi, can you send me the invoice for January? Need it ASAP for accounting.

Thanks,
Client
```

**Validation Rules**:
- email_id must be unique (no duplicates in /Needs_Action)
- priority assigned based on: Gmail "important" label OR urgent keywords in subject
- received timestamp in UTC

---

## Entity 2: FileDrop

**Purpose**: Represents a file manually dropped into the Inbox folder

**Storage Location**:
- Metadata: `/Needs_Action/FILE_{timestamp}_{filename}.md`
- Actual file: `/Needs_Action/{filename}` (or `/Quarantine/` if unsafe)

**Attributes**:

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| type | string | Yes | Entity type identifier | Must be "file_drop" |
| original_name | string | Yes | Original filename | Valid filename chars |
| file_path | string | Yes | Path to actual file in vault | Absolute path |
| size | integer | Yes | File size in bytes | > 0 |
| file_type | string | Yes | File extension | Must start with "." |
| received | datetime | Yes | Timestamp when file was detected | ISO 8601 format |
| status | enum | Yes | Processing status | "pending", "quarantined", "done" |
| quarantined | boolean | Yes | Whether file was quarantined | true/false |

**State Transitions**:
```
pending → quarantined (if unsafe file type detected)
pending → done (after processing by Claude Code)
```

**Quarantine Criteria** (FR-011):
- File extensions: .exe, .dmg, .app, .bat, .sh, .cmd, .msi, .dll
- Action: Move to `/Quarantine/`, create alert in /Needs_Action

**Relationships**:
- One FileDrop can generate one Action Plan (1:1)
- File and metadata both moved to `/Done/` after processing

**Example** (Markdown + YAML):
```markdown
---
type: file_drop
original_name: contract.pdf
file_path: /path/to/vault/Needs_Action/contract_20260221_143500.pdf
size: 524288
file_type: .pdf
received: 2026-02-21T14:35:00Z
status: pending
quarantined: false
---

## File Information

A new file was dropped into the Inbox for processing.

**Location**: `/Needs_Action/contract_20260221_143500.pdf`
**Size**: 512.00 KB
**Type**: PDF Document

## Suggested Actions

- [ ] Review contract content
- [ ] Extract key terms
- [ ] File in appropriate folder
```

**Validation Rules**:
- Size must be realistic (<100MB for Bronze tier)
- Filename conflicts resolved by appending timestamp
- quarantined=true if file_type in UNSAFE_EXTENSIONS

---

## Entity 3: ActionPlan

**Purpose**: AI-generated task plan created by Claude Code based on Email or FileDrop

**Storage Location**: `/Plans/PLAN_{id}_{title_slug}.md`

**Attributes**:

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| plan_id | string | Yes | Unique plan identifier | Sequential: PLAN_001, PLAN_002, etc. |
| title | string | Yes | Brief plan title | 3-10 words |
| source_type | enum | Yes | Origin of plan | "email" or "file_drop" |
| source_id | string | Yes | ID of source entity | email_id or FileDrop timestamp |
| created | datetime | Yes | Plan creation timestamp | ISO 8601 format |
| objective | string | Yes | 1-2 sentence goal | Max 500 chars |
| steps | array[Step] | Yes | Action steps | 3-7 steps |
| approval_required | boolean | Yes | HITL approval needed | true/false |
| approval_file | string | No | Path to approval request | If approval_required=true |
| status | enum | Yes | Execution status | "draft", "awaiting_approval", "complete" |

**Step Sub-Entity**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| step_number | integer | Yes | Sequential step number |
| description | string | Yes | What to do |
| completed | boolean | Yes | Checkbox state |

**State Transitions**:
```
draft → awaiting_approval (if approval_required=true)
draft → complete (if no approval needed and all steps checked)
awaiting_approval → complete (after human approval in Silver tier)
```

**Relationships**:
- One ActionPlan belongs to one Email OR one FileDrop (1:1)
- ActionPlan may reference one Approval Request file (1:0..1)

**Example** (Markdown + YAML):
```markdown
---
plan_id: PLAN_001
title: Send January Invoice to Client
source_type: email
source_id: 18d4c5f2a3b1e9f0
created: 2026-02-21T14:45:00Z
objective: Generate and prepare January invoice for client@example.com based on email request.
approval_required: true
approval_file: /Pending_Approval/APPROVAL_invoice_client_20260221.md
status: awaiting_approval
---

## Objective

Generate and prepare January invoice for client@example.com based on email request.

## Steps

- [ ] 1. Identify client account in records
- [ ] 2. Calculate January charges/hours
- [ ] 3. Generate invoice PDF
- [ ] 4. Create approval request for sending
- [ ] 5. [REQUIRES APPROVAL] Send invoice to client@example.com

## Approval Required

This plan involves sending an email to client@example.com.

**Review approval request**: [/Pending_Approval/APPROVAL_invoice_client_20260221.md](../Pending_Approval/APPROVAL_invoice_client_20260221.md)

To approve: Move approval file to `/Approved/` folder (Silver tier feature)
```

**Validation Rules**:
- steps must contain 3-7 items (per FR-014)
- approval_required=true if steps contain: email sends, payments, irreversible actions
- plan_id must be unique and sequential

---

## Entity 4: DashboardSummary

**Purpose**: Real-time system state summary displayed in Dashboard.md

**Storage Location**: `/Dashboard.md` (single file, updated in-place)

**Attributes**:

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| last_updated | datetime | Yes | Last refresh timestamp | ISO 8601 format |
| pending_actions_count | integer | Yes | Items in /Needs_Action | >= 0 |
| pending_approvals_count | integer | Yes | Items in /Pending_Approval | >= 0 |
| system_health | enum | Yes | Overall health status | "healthy", "degraded", "down" |
| recent_activity | array[Activity] | Yes | Last 5 actions | Max 5 entries |
| watchers_status | object | Yes | Watcher health checks | See Watcher Status |

**Activity Sub-Entity**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| timestamp | datetime | Yes | When activity occurred |
| action | string | Yes | What happened (verb + object) |
| target | string | Yes | File/entity affected |

**Watcher Status Sub-Entity**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Watcher name (gmail_watcher, filesystem_watcher) |
| status | enum | Yes | "running", "stopped", "error" |
| last_check | datetime | Yes | Last heartbeat timestamp |

**Update Frequency**:
- Updated whenever: new item added to /Needs_Action, plan created, item moved to /Done
- Target: <60 seconds from state change (SC-006)

**Example** (Markdown - no frontmatter):
```markdown
# AI Employee Dashboard

**Last Updated**: 2026-02-21 14:50:00

## Status Overview

- **Pending Actions**: 3 items
- **Pending Approvals**: 1 item
- **System Health**: ✅ Healthy

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

**Validation Rules**:
- Counts must match actual folder contents (count .md files in respective folders)
- recent_activity limited to 5 most recent entries
- system_health="healthy" if all watchers running, "degraded" if some down, "down" if all down

---

## Entity Relationships Diagram

```
Email (1) ----generates----> (0..1) ActionPlan
                                       |
FileDrop (1) -generates----> (0..1)    |
                                       |
                                       v
                              (0..1) ApprovalRequest
                                  (in /Pending_Approval/)

DashboardSummary (1) ----aggregates----> (*) Email
                    |
                    ----aggregates----> (*) FileDrop
                    |
                    ----aggregates----> (*) ActionPlan
```

**Key Relationships**:
- Email OR FileDrop → ActionPlan (0..1 cardinality: one source generates zero or one plan)
- ActionPlan → ApprovalRequest (0..1 cardinality: plan may require approval)
- DashboardSummary → All entities (aggregates counts from all folders)

---

## File Lifecycle

**Email Lifecycle**:
```
Gmail Inbox
    ↓ (Gmail Watcher detects)
/Needs_Action/EMAIL_{id}.md
    ↓ (Claude Code processes)
/Plans/PLAN_{id}.md created
    ↓ (Processing complete)
/Done/EMAIL_{id}.md (moved)
```

**FileDrop Lifecycle**:
```
/Inbox/{filename}
    ↓ (File System Watcher detects)
/Needs_Action/{filename} + FILE_{id}.md
    ↓ (If unsafe: FR-011)
/Quarantine/{filename} (quarantined)
    ↓ (Else: Claude Code processes)
/Plans/PLAN_{id}.md created
    ↓ (Processing complete)
/Done/{filename} + FILE_{id}.md (moved)
```

**ActionPlan Lifecycle**:
```
/Plans/PLAN_{id}.md (created)
    ↓ (If approval_required)
/Pending_Approval/APPROVAL_{id}.md (created)
    ↓ (Silver tier: human approves)
/Approved/APPROVAL_{id}.md (moved)
    ↓ (All steps complete)
/Done/PLAN_{id}.md (moved)
```

---

## Storage Estimates

**Assumptions**:
- 20 emails/day × 30 days = 600 emails/month
- 5 files/day × 30 days = 150 files/month
- 80% plan generation rate = 600 plans/month

**Storage Size**:
- Email .md file: ~1-2 KB each → 600 × 2KB = 1.2 MB/month
- FileDrop metadata: ~1 KB each → 150 × 1KB = 150 KB/month
- ActionPlan .md file: ~2-3 KB each → 600 × 3KB = 1.8 MB/month
- Logs (JSON): ~500 bytes/entry × 1000 actions = 500 KB/month
- **Total**: ~3.7 MB/month markdown/JSON data

**File Count**:
- ~750 .md files/month (emails + filedrops + plans)
- Vault size after 1 year: ~9,000 files, ~45 MB

**Performance Impact**: Negligible. Modern filesystems handle 10,000+ files easily. Obsidian vault remains fast.

---

## Summary

**4 Core Entities**:
1. **Email**: Gmail messages detected by watcher
2. **FileDrop**: Manually added files from Inbox
3. **ActionPlan**: AI-generated task plans
4. **DashboardSummary**: Real-time system state

**All entities stored as Markdown + YAML frontmatter** (Local-First Privacy principle)

**Relationships**: Simple 1:1 and aggregation patterns, no complex joins needed

**Validation**: Frontmatter schema enforced by watchers and Claude Code skills

**Ready for contracts definition (Phase 1 continued).**
