# Data Model Design - Silver Tier

**Feature**: Silver Tier - Autonomous Task Execution & Multi-Channel Communication
**Date**: 2026-02-25
**Status**: Complete

## Overview

This document defines the data models for Silver Tier entities. All entities follow Bronze Tier patterns: Python dataclasses with YAML frontmatter serialization to Markdown files.

**New Entities**:
1. WhatsAppMessage - Incoming WhatsApp Business messages (US3)
2. SocialMediaPost - Social media post plans and execution results (US2)
3. ScheduledTask - Recurring scheduled task definitions (US4)
4. ExecutionLog - Audit records for all executed actions (US1)

**Existing Entities** (from Bronze Tier):
- Email - Incoming email entity (read-only)
- FileDrop - Dropped file entity
- ActionPlan - Generated plan with actions and approval status

---

## Entity 1: WhatsAppMessage

### Purpose

Represents incoming WhatsApp Business message detected by WhatsApp watcher.

### User Story

**US3 - WhatsApp Business Monitoring**: AI Employee monitors WhatsApp Business API for incoming messages and creates action items in the vault.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | string | Yes | WhatsApp message ID from API (unique, PK) |
| `sender_phone` | string | Yes | Sender's phone number (E.164 format: +[country][number]) |
| `sender_name` | string | Yes | Sender's contact name (from WhatsApp profile or phone number) |
| `message_content` | string | Yes | Full message text content |
| `timestamp` | datetime (ISO 8601) | Yes | Message received timestamp from WhatsApp API |
| `media_attachments` | list[dict] | No | List of media files (images, documents, audio, video) |
| `priority` | enum | Yes | low \| medium \| high (based on Company_Handbook.md priority contacts) |
| `status` | enum | Yes | pending \| processed \| archived |
| `created_at` | datetime (ISO 8601) | Yes | Entity creation time in vault |
| `processed_at` | datetime (ISO 8601) | No | When plan was generated for this message |

### Media Attachment Structure

Each item in `media_attachments` list:

| Field | Type | Description |
|-------|------|-------------|
| `media_type` | enum | image \| document \| audio \| video |
| `media_url` | string | URL from WhatsApp API (temporary, expires after download) |
| `local_path` | string | Path in /Inbox/ after download (e.g., `/vault/Inbox/whatsapp_image_123.jpg`) |
| `filename` | string | Original filename from WhatsApp |

### Validation Rules

1. **Uniqueness**: `message_id` must be unique to prevent duplicate processing
2. **Phone Format**: `sender_phone` must match E.164 format (`+[1-9]\d{1,14}`)
3. **Timestamp**: Cannot be in future (must be <= current time)
4. **Priority Detection**: Auto-set based on `sender_phone` in Company_Handbook.md `priority_contacts` list
5. **Status Transitions**: pending → processed → archived (unidirectional)

### Relationships

- **Links to ActionPlan**: One WhatsApp message → one or more generated plans
- **Links to ExecutionLog**: Message detection logged as `whatsapp_detect` action

### State Transitions

```
pending (initial state after watcher creates entity)
   ↓
processed (orchestrator generates ActionPlan for this message)
   ↓
archived (message moved to /Done/ after plan execution)
```

### File Format (Markdown with YAML Frontmatter)

**Location**: `/vault/Needs_Action/WHATSAPP_[message_id].md`

```markdown
---
type: whatsapp
message_id: wamid.HBgNOTIzMDA1NjU0MzIxFQIAERgSQkUzNzBDMDVERkQ2MDc5QUYA
sender_phone: "+923001234567"
sender_name: "John Doe"
timestamp: "2026-02-25T14:30:00Z"
priority: high
status: pending
media_attachments:
  - media_type: image
    media_url: "https://mmg.whatsapp.net/d/f/abc123xyz.enc"
    local_path: "/vault/Inbox/whatsapp_image_1708876200.jpg"
    filename: "proposal_diagram.jpg"
created_at: "2026-02-25T14:30:15Z"
processed_at: null
---

## Message Content

Urgent: Need your approval on the proposal by EOD. Please review the attached diagram and let me know if we can proceed.

## Context

Priority contact detected (listed in Company_Handbook.md). Flagged as high priority.

## Next Steps

- Review attached diagram
- Provide approval or feedback
- Respond before end of day
```

### Python Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

class WhatsAppPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class WhatsAppStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    ARCHIVED = "archived"

class MediaType(Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"

@dataclass
class MediaAttachment:
    media_type: MediaType
    media_url: str
    local_path: str
    filename: str

@dataclass
class WhatsAppMessage:
    message_id: str
    sender_phone: str
    sender_name: str
    message_content: str
    timestamp: datetime
    priority: WhatsAppPriority
    status: WhatsAppStatus
    created_at: datetime
    media_attachments: List[MediaAttachment] = field(default_factory=list)
    processed_at: Optional[datetime] = None

    def to_yaml_frontmatter(self) -> dict:
        """Convert to YAML frontmatter dict"""
        return {
            'type': 'whatsapp',
            'message_id': self.message_id,
            'sender_phone': self.sender_phone,
            'sender_name': self.sender_name,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'status': self.status.value,
            'media_attachments': [
                {
                    'media_type': att.media_type.value,
                    'media_url': att.media_url,
                    'local_path': att.local_path,
                    'filename': att.filename
                }
                for att in self.media_attachments
            ],
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
```

---

## Entity 2: SocialMediaPost

### Purpose

Represents social media post plan awaiting approval or execution. Supports multi-platform posting (LinkedIn, Facebook, Twitter) with per-platform results.

### User Story

**US2 - Social Media Auto-Posting**: AI Employee automatically posts approved content to LinkedIn, Facebook, and Twitter/X.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `post_id` | string | Yes | Generated post ID (format: `POST_[platform]_[timestamp]`, PK) |
| `platforms` | list[enum] | Yes | Target platforms: linkedin, facebook, twitter (multi-select) |
| `content` | string | Yes | Post text content |
| `media_attachments` | list[dict] | No | Images or videos for post |
| `scheduled_time` | datetime (ISO 8601) | No | Future posting time (null = immediate post after approval) |
| `status` | enum | Yes | draft \| approved \| posted \| failed \| partial |
| `platform_results` | dict | Yes | Per-platform execution results (keys match `platforms`) |
| `created_at` | datetime (ISO 8601) | Yes | Plan creation time |
| `approved_at` | datetime (ISO 8601) | No | Approval timestamp (when moved to /Approved/) |
| `posted_at` | datetime (ISO 8601) | No | Actual posting time (when executor completed) |
| `error_details` | string | No | Error message if status is failed or partial |

### Media Attachment Structure

Each item in `media_attachments` list:

| Field | Type | Description |
|-------|------|-------------|
| `media_type` | enum | image \| video |
| `local_path` | string | Path in /Inbox/ (e.g., `/vault/Inbox/feature_screenshot.png`) |
| `filename` | string | Filename |

### Platform Results Structure

Dictionary with keys matching `platforms` list:

```yaml
platform_results:
  linkedin:
    status: success | failed
    post_url: "https://linkedin.com/posts/user_123456"
    post_id: "ugc:post:123456"
    error: null | "error message"
  facebook:
    status: success | failed
    post_url: "https://facebook.com/user/posts/123456"
    post_id: "123456_789012"
    error: null
  twitter:
    status: success | failed
    post_url: "https://twitter.com/user/status/987654321"
    tweet_ids: ["987654321"]  # Array for threads
    error: null
```

### Validation Rules

1. **Content Length**: Validated per platform before posting
   - LinkedIn: Max 3000 characters
   - Twitter: Max 280 characters (if > 280, split into thread)
   - Facebook: Max 63,206 characters
2. **Scheduled Time**: If provided, must be in future (> current time)
3. **Platform Results**: Keys must match `platforms` list
4. **Status Logic**:
   - `posted`: All platforms succeeded
   - `partial`: Some platforms succeeded, some failed
   - `failed`: All platforms failed
5. **Thread Handling**: If Twitter in platforms and content > 280 chars, executor auto-splits into thread

### Relationships

- **Created from ActionPlan**: Orchestrator suggests social post → creates SocialMediaPost entity
- **Links to ExecutionLog**: One post → one or more execution attempts (logged as `social_post` action)

### State Transitions

```
draft (initial state after creation in /Needs_Action/)
   ↓
approved (human moves to /Approved/)
   ↓
posted (executor successfully posts to all platforms)
 OR
partial (executor posts to some platforms, some fail)
 OR
failed (executor cannot post to any platform)
   ↓
archived (moved to /Done/ after execution)
```

### File Format (Markdown with YAML Frontmatter)

**Location**: `/vault/Approved/POST_linkedin_1708876200.md` (during approval), then `/vault/Done/` after posting

```markdown
---
type: social_media_post
post_id: POST_linkedin_1708876200
platforms:
  - linkedin
  - twitter
content: "Excited to share our new feature release! 🚀 Check out how we're transforming productivity with AI-powered automation. #AI #Productivity #TechInnovation"
media_attachments:
  - media_type: image
    local_path: "/vault/Inbox/feature_screenshot.png"
    filename: "feature_screenshot.png"
scheduled_time: null
status: posted
platform_results:
  linkedin:
    status: success
    post_url: "https://linkedin.com/posts/user_123456"
    post_id: "ugc:post:123456"
    error: null
  twitter:
    status: success
    post_url: "https://twitter.com/user/status/987654321"
    tweet_ids: ["987654321"]
    error: null
created_at: "2026-02-25T14:00:00Z"
approved_at: "2026-02-25T14:15:00Z"
posted_at: "2026-02-25T14:17:30Z"
error_details: null
---

## Post Content

Excited to share our new feature release! 🚀 Check out how we're transforming productivity with AI-powered automation. #AI #Productivity #TechInnovation

## Execution Summary

**Posted Successfully** at 14:17:30 on 2026-02-25

**LinkedIn**:
- Status: ✅ Success
- Post URL: https://linkedin.com/posts/user_123456
- Post ID: ugc:post:123456
- Impressions: 500+ (estimated after 24h)

**Twitter**:
- Status: ✅ Success
- Tweet URL: https://twitter.com/user/status/987654321
- Tweet ID: 987654321
- Impressions: 200+ (estimated after 24h)

**Total Reach**: 700+ impressions across 2 platforms
```

### Python Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

class Platform(Enum):
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    TWITTER = "twitter"

class PostStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class PlatformResult:
    status: str  # "success" | "failed"
    post_url: Optional[str] = None
    post_id: Optional[str] = None
    tweet_ids: Optional[List[str]] = None  # For Twitter threads
    error: Optional[str] = None

@dataclass
class SocialMediaPost:
    post_id: str
    platforms: List[Platform]
    content: str
    status: PostStatus
    created_at: datetime
    media_attachments: List[Dict] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    platform_results: Dict[str, PlatformResult] = field(default_factory=dict)
    approved_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    error_details: Optional[str] = None

    def validate_content_length(self) -> Dict[str, bool]:
        """Validate content length per platform"""
        limits = {
            Platform.LINKEDIN: 3000,
            Platform.FACEBOOK: 63206,
            Platform.TWITTER: 280
        }
        results = {}
        for platform in self.platforms:
            limit = limits[platform]
            results[platform.value] = len(self.content) <= limit
        return results

    def needs_thread(self) -> bool:
        """Check if Twitter content needs threading"""
        if Platform.TWITTER in self.platforms:
            return len(self.content) > 280
        return False
```

---

## Entity 3: ScheduledTask

### Purpose

Represents recurring scheduled task definition. Tasks are configured in Company_Handbook.md and executed by scheduler.py at specified times.

### User Story

**US4 - Scheduled Tasks & Daily Briefings**: AI Employee executes time-based tasks automatically, such as generating daily briefings at 9 AM or weekly summaries every Monday.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | Yes | Generated task ID (format: `TASK_[name]_[created_timestamp]`, PK) |
| `task_name` | string | Yes | Human-readable task name (e.g., "daily_briefing") |
| `task_type` | enum | Yes | briefing \| summary \| custom |
| `schedule_pattern` | string | Yes | Cron-like pattern (e.g., "0 9 * * *" = daily at 09:00) |
| `recurrence_rule` | dict | Yes | Parsed recurrence details (frequency, time, day_of_week, interval) |
| `last_execution` | datetime (ISO 8601) | No | Last successful run time |
| `next_execution` | datetime (ISO 8601) | Yes | Calculated next run time |
| `enabled` | boolean | Yes | Whether task is active (true = runs, false = skipped) |
| `output_path` | string | Yes | Where to create output (e.g., "/Needs_Action/") |
| `parameters` | dict | No | Task-specific parameters (varies by task_type) |
| `created_at` | datetime (ISO 8601) | Yes | Task definition creation time |
| `updated_at` | datetime (ISO 8601) | Yes | Last modification time |

### Recurrence Rule Structure

| Field | Type | Description |
|-------|------|-------------|
| `frequency` | enum | daily \| weekly \| custom |
| `time` | string | HH:MM format (24-hour, e.g., "09:00") |
| `day_of_week` | int | 0-6 (0=Monday, 6=Sunday, for weekly tasks) |
| `interval` | int | N (for "every N days" custom tasks) |

### Parameters Structure (by task_type)

**For briefing**:
```yaml
parameters:
  include_pending: true
  include_completed_24h: true
  include_urgent: true
```

**For summary**:
```yaml
parameters:
  period: "week"  # day | week | month
  metrics:
    - "completed_tasks"
    - "time_saved"
    - "emails_sent"
    - "posts_published"
```

**For custom**:
```yaml
parameters:
  # Task-specific parameters (varies by task)
```

### Validation Rules

1. **Schedule Pattern**: Must be valid cron syntax (validated by APScheduler)
2. **Next Execution**: Calculated based on current time + schedule pattern
3. **Time Format**: Must match HH:MM (24-hour format)
4. **Day of Week**: If frequency is weekly, day_of_week must be 0-6
5. **Uniqueness**: task_name should be unique within Company_Handbook.md

### Relationships

- **Outputs create files**: Scheduler creates new files in output_path (e.g., `/Needs_Action/BRIEFING_2026-02-25.md`)
- **Links to ExecutionLog**: One task → multiple execution records (logged as `scheduled_task` action)

### State Transitions

```
enabled=true (scheduler processes this task)
   ↓
execution time reached (APScheduler triggers job)
   ↓
generate output (create briefing/summary file)
   ↓
last_execution updated, next_execution calculated
   ↓
(repeat cycle)

enabled=false (scheduler skips this task)
```

### File Format (YAML in Company_Handbook.md)

**Location**: `/vault/Company_Handbook.md` (YAML section)

```yaml
scheduled_tasks:
  - task_id: TASK_daily_briefing_1708876200
    task_name: "daily_briefing"
    task_type: briefing
    schedule_pattern: "0 9 * * *"
    recurrence_rule:
      frequency: daily
      time: "09:00"
    last_execution: "2026-02-25T09:00:15Z"
    next_execution: "2026-02-26T09:00:00Z"
    enabled: true
    output_path: "/Needs_Action/"
    parameters:
      include_pending: true
      include_completed_24h: true
      include_urgent: true
    created_at: "2026-02-01T10:00:00Z"
    updated_at: "2026-02-25T09:00:15Z"

  - task_id: TASK_weekly_summary_1708876300
    task_name: "weekly_summary"
    task_type: summary
    schedule_pattern: "0 8 * * 1"
    recurrence_rule:
      frequency: weekly
      time: "08:00"
      day_of_week: 1  # Monday
    last_execution: "2026-02-19T08:00:10Z"
    next_execution: "2026-02-26T08:00:00Z"
    enabled: true
    output_path: "/Needs_Action/"
    parameters:
      period: "week"
      metrics:
        - "completed_tasks"
        - "time_saved"
        - "emails_sent"
        - "posts_published"
    created_at: "2026-02-01T10:00:00Z"
    updated_at: "2026-02-19T08:00:10Z"
```

### Python Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

class TaskType(Enum):
    BRIEFING = "briefing"
    SUMMARY = "summary"
    CUSTOM = "custom"

class Frequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"

@dataclass
class RecurrenceRule:
    frequency: Frequency
    time: str  # HH:MM format
    day_of_week: Optional[int] = None  # 0-6 for weekly
    interval: Optional[int] = None  # N days for custom

@dataclass
class ScheduledTask:
    task_id: str
    task_name: str
    task_type: TaskType
    schedule_pattern: str
    recurrence_rule: RecurrenceRule
    next_execution: datetime
    enabled: bool
    output_path: str
    created_at: datetime
    updated_at: datetime
    last_execution: Optional[datetime] = None
    parameters: Dict = field(default_factory=dict)

    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time based on recurrence rule"""
        # Implementation uses APScheduler CronTrigger
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(self.schedule_pattern)
        return trigger.get_next_fire_time(None, current_time)
```

---

## Entity 4: ExecutionLog

### Purpose

Audit record for all executed actions. Provides full traceability from plan approval to execution to result.

### User Story

**US1 - Email Sending & HITL Execution Engine** (cross-cutting for all user stories): System logs all executions for audit trail and debugging.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `log_id` | string | Yes | Generated log ID (format: `LOG_[timestamp]_[action_type]`, PK) |
| `timestamp` | datetime (ISO 8601) | Yes | Execution time |
| `action_type` | enum | Yes | email_send \| social_post \| whatsapp_detect \| scheduled_task |
| `actor` | enum | Yes | executor \| scheduler \| whatsapp_watcher \| orchestrator |
| `plan_id` | string | Yes | Reference to plan file that triggered action |
| `target` | string | Yes | Destination (email address, platform name, phone number, etc.) |
| `parameters` | dict | Yes | Action-specific parameters (varies by action_type) |
| `approval_status` | enum | Yes | approved \| auto_approved \| pending |
| `approved_by` | enum | Yes | human \| auto |
| `approval_timestamp` | datetime (ISO 8601) | No | When approval granted (for approved actions) |
| `result` | enum | Yes | success \| failure \| partial |
| `mcp_server` | string | No | MCP server URL used for this action |
| `response` | dict | No | MCP server response (varies by action_type) |
| `error` | string | No | Error message if result is failure |
| `duration_ms` | int | Yes | Execution time in milliseconds |
| `retry_count` | int | Yes | Number of retry attempts (0 = first attempt, 1+ = retries) |

### Parameters Structure (by action_type)

**For email_send**:
```json
{
  "recipient": "user@example.com",
  "subject": "Re: Proposal Review",
  "body_preview": "Thank you for your feedback. I've updated..."
}
```

**For social_post**:
```json
{
  "platform": "linkedin",
  "content_preview": "Excited to share our new feature...",
  "scheduled": false
}
```

**For whatsapp_detect**:
```json
{
  "sender_phone": "+923001234567",
  "message_preview": "Urgent: Need your approval..."
}
```

**For scheduled_task**:
```json
{
  "task_name": "daily_briefing",
  "output_file": "BRIEFING_2026-02-25.md"
}
```

### Response Structure (by action_type)

**For email_send**:
```json
{
  "message_id": "<abc123@mail.gmail.com>",
  "thread_id": "thread_xyz789"
}
```

**For social_post**:
```json
{
  "post_url": "https://linkedin.com/posts/123",
  "post_id": "abc123"
}
```

**For whatsapp_detect**:
```json
{
  "message_id": "wamid.abc123xyz",
  "media_downloaded": true
}
```

**For scheduled_task**:
```json
{
  "output_file": "BRIEFING_2026-02-25.md",
  "items_included": 15
}
```

### Validation Rules

1. **Timestamp**: Cannot be in future (must be <= current time)
2. **Result-Error Relationship**: If result is failure, error must be present
3. **Result-Response Relationship**: If result is success, response should be present
4. **Duration**: Must be non-negative (>= 0)
5. **Retry Count**: Must be non-negative (>= 0)

### Relationships

- **References ActionPlan**: Via `plan_id` field
- **References other entities**: Contextual links via plan_id (email plans, social post plans, etc.)

### Storage Format

**Daily JSON log files**: `/vault/Logs/YYYY-MM-DD.json` (append-only)

Each log entry is a JSON object on a single line (JSON Lines format for easy parsing).

### File Format (JSON Lines)

**Location**: `/vault/Logs/2026-02-25.json`

```json
{"log_id": "LOG_1708876800_email_send", "timestamp": "2026-02-25T14:20:00Z", "action_type": "email_send", "actor": "executor", "plan_id": "PLAN_email_reply_1708876700.md", "target": "client@example.com", "parameters": {"recipient": "client@example.com", "subject": "Re: Proposal Review", "body_preview": "Thank you for your feedback. I've updated..."}, "approval_status": "approved", "approved_by": "human", "approval_timestamp": "2026-02-25T14:15:00Z", "result": "success", "mcp_server": "gmail_mcp", "response": {"message_id": "<abc123@mail.gmail.com>", "thread_id": "thread_xyz789"}, "error": null, "duration_ms": 1234, "retry_count": 0}
{"log_id": "LOG_1708877000_social_post", "timestamp": "2026-02-25T14:25:00Z", "action_type": "social_post", "actor": "executor", "plan_id": "POST_linkedin_1708876200.md", "target": "linkedin", "parameters": {"platform": "linkedin", "content_preview": "Excited to share our new feature...", "scheduled": false}, "approval_status": "approved", "approved_by": "human", "approval_timestamp": "2026-02-25T14:15:00Z", "result": "success", "mcp_server": "linkedin_mcp", "response": {"post_url": "https://linkedin.com/posts/user_123456", "post_id": "ugc:post:123456"}, "error": null, "duration_ms": 2150, "retry_count": 0}
```

### Python Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

class ActionType(Enum):
    EMAIL_SEND = "email_send"
    SOCIAL_POST = "social_post"
    WHATSAPP_DETECT = "whatsapp_detect"
    SCHEDULED_TASK = "scheduled_task"

class Actor(Enum):
    EXECUTOR = "executor"
    SCHEDULER = "scheduler"
    WHATSAPP_WATCHER = "whatsapp_watcher"
    ORCHESTRATOR = "orchestrator"

class ApprovalStatus(Enum):
    APPROVED = "approved"
    AUTO_APPROVED = "auto_approved"
    PENDING = "pending"

class Result(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"

@dataclass
class ExecutionLog:
    log_id: str
    timestamp: datetime
    action_type: ActionType
    actor: Actor
    plan_id: str
    target: str
    parameters: Dict
    approval_status: ApprovalStatus
    approved_by: str  # "human" | "auto"
    result: Result
    duration_ms: int
    retry_count: int = 0
    approval_timestamp: Optional[datetime] = None
    mcp_server: Optional[str] = None
    response: Optional[Dict] = None
    error: Optional[str] = None

    def to_json(self) -> dict:
        """Convert to JSON for log file"""
        return {
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat(),
            'action_type': self.action_type.value,
            'actor': self.actor.value,
            'plan_id': self.plan_id,
            'target': self.target,
            'parameters': self.parameters,
            'approval_status': self.approval_status.value,
            'approved_by': self.approved_by,
            'approval_timestamp': self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            'result': self.result.value,
            'mcp_server': self.mcp_server,
            'response': self.response,
            'error': self.error,
            'duration_ms': self.duration_ms,
            'retry_count': self.retry_count
        }
```

---

## Entity Relationships Diagram

```
[Email] (Bronze Tier)
   ↓ (triggers)
[ActionPlan] (Bronze Tier)
   ↓ (creates)
[SocialMediaPost] (Silver Tier)
   ↓ (approved)
[Executor] processes → [ExecutionLog] (Silver Tier)


[WhatsAppMessage] (Silver Tier)
   ↓ (triggers)
[ActionPlan] (Bronze Tier)
   ↓ (approved)
[Executor] processes → [ExecutionLog] (Silver Tier)


[ScheduledTask] (Silver Tier)
   ↓ (time trigger)
[Scheduler] executes → [ExecutionLog] (Silver Tier)
   ↓ (creates)
[Briefing/Summary file] in /Needs_Action/
```

---

## Summary

**Total Entities**: 7 (3 existing from Bronze + 4 new for Silver)

**New Files Created**:
1. WhatsAppMessage: `/vault/Needs_Action/WHATSAPP_[id].md`
2. SocialMediaPost: `/vault/Approved/POST_[platform]_[timestamp].md` → `/vault/Done/`
3. ScheduledTask: Embedded in `/vault/Company_Handbook.md` (YAML section)
4. ExecutionLog: `/vault/Logs/YYYY-MM-DD.json` (append-only JSON Lines)

**Vault Folders Extended**:
- `/vault/Approved/` - NEW for Silver Tier (HITL workflow)
- `/vault/Logs/` - EXTENDED with execution_state.json, schedule_state.json, rate_limit_state.json

---

**Data Model Status**: ✅ **COMPLETE**

**Date Completed**: 2026-02-25

**Next Phase**: Contracts (JSON Schemas), Quickstart Guide
