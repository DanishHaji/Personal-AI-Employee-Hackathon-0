# Gold Tier Data Model

**Feature**: 003-gold-tier-upgrade
**Date**: 2026-02-27
**Purpose**: Entity definitions for autonomous AI employee capabilities

---

## Entity Overview

Gold Tier introduces 9 new entities building on Silver Tier's foundation:

**Autonomous Execution**:
1. **TrustRule** - Configurable rules for auto-approval
2. **Insight** - Analytics-generated productivity insights
3. **ProactiveSuggestion** - AI-initiated task recommendations

**Calendar & Meetings**:
4. **CalendarEvent** - Google Calendar events with conflict tracking
5. **MeetingNote** - Transcribed meeting notes with action items

**Content Management**:
6. **Document** - Generated documents from templates
7. **Contact** - CRM relationship tracking

**Financial**:
8. **Expense** - Tracked business expenses with OCR
9. **Budget** - Monthly budget allocations by category

---

## 1. TrustRule

Defines which actions can be auto-approved without HITL review.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rule_id | string | Yes | Unique identifier (e.g., `RULE_email_known_contacts`) |
| rule_name | string | Yes | Human-readable name |
| action_type | enum | Yes | Type of action (email_send, social_post, calendar_create, expense_record, etc.) |
| trust_level | enum | Yes | 0=Always approve, 1=Auto-approve, 2=Auto+notify, 3=Silent auto |
| contact_filter | list[string] | No | Allowed contacts (emails, phone numbers, or group names like "Team") |
| content_pattern | string | No | Regex pattern for content matching (e.g., ".*urgent.*") |
| time_pattern | string | No | Time-based filter (e.g., "weekdays 9am-5pm") |
| max_value | float | No | Maximum financial amount for auto-approval |
| created_at | datetime | Yes | Rule creation timestamp |
| created_by | string | Yes | Always "user" (human-created rules only) |
| last_used | datetime | No | Last time rule triggered auto-approval |
| usage_count | integer | Yes | Number of times rule has auto-approved (default: 0) |
| effectiveness_score | float | Yes | Approval accuracy (0.0-1.0, calculated from feedback) |
| enabled | boolean | Yes | Whether rule is active (default: true) |

### Storage Format

Stored in Company_Handbook.md YAML frontmatter:

```yaml
---
trust_rules:
  - rule_id: RULE_email_known_contacts
    rule_name: "Email Replies to Known Contacts"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@example.com", "Team"]
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: 2026-02-01T10:00:00Z
    created_by: user
    last_used: 2026-02-26T14:30:00Z
    usage_count: 45
    effectiveness_score: 0.956
    enabled: true
---
```

### Validation Rules

- **rule_id**: Must be unique, format `RULE_{lowercase_description}`
- **trust_level**: 0-3 only
- **action_type**: Must match existing action types (email_send, social_post, calendar_create, expense_record, document_generate)
- **contact_filter**: Email regex validation for email addresses
- **content_pattern**: Must be valid regex
- **effectiveness_score**: Calculated as (approved_actions / total_actions_would_approve)

### State Transitions

1. **Created** → enabled=true, usage_count=0, effectiveness_score=1.0
2. **Used** → usage_count++, last_used=now
3. **Feedback received** → effectiveness_score recalculated
4. **Disabled** → enabled=false (user revokes trust)
5. **Auto-disabled** → enabled=false if effectiveness_score < 0.80 (safety threshold)

### Relationships

- **TrustRule** → **ExecutionLog** (many-to-many): Logs reference rules that auto-approved them
- **TrustRule** ← **Feedback**: User feedback adjusts effectiveness_score

---

## 2. CalendarEvent

Represents Google Calendar events with local caching for conflict detection.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| event_id | string | Yes | Google Calendar event ID (e.g., `CAL_abc123xyz`) |
| title | string | Yes | Event summary/title |
| start_time | datetime | Yes | Event start (ISO 8601 with timezone) |
| end_time | datetime | Yes | Event end (ISO 8601 with timezone) |
| attendees | list[dict] | No | Attendee list `[{email, name, response_status}]` |
| location | string | No | Physical location or video link |
| video_link | string | No | Zoom/Meet/Teams URL |
| agenda | string | No | Meeting agenda/description |
| recurring_pattern | string | No | RRULE format for recurring events |
| recurrence_id | string | No | Parent event ID for recurring series |
| priority | enum | Yes | high, medium, low (default: medium) |
| conflicts | list[string] | No | List of conflicting event_ids |
| created_by | enum | Yes | ai, user |
| created_at | datetime | Yes | Creation timestamp |
| last_modified | datetime | Yes | Last modification timestamp |
| status | enum | Yes | confirmed, tentative, cancelled |

### Storage Format

Cached locally in `/Calendar/events.json` for offline conflict detection:

```json
{
  "event_id": "CAL_abc123xyz",
  "title": "Q2 Planning Meeting",
  "start_time": "2026-03-15T14:00:00-07:00",
  "end_time": "2026-03-15T15:00:00-07:00",
  "attendees": [
    {"email": "john@example.com", "name": "John Smith", "response_status": "accepted"},
    {"email": "jane@example.com", "name": "Jane Doe", "response_status": "tentative"}
  ],
  "location": "Conference Room A",
  "video_link": "https://zoom.us/j/123456789",
  "agenda": "Discuss Q2 objectives and resource allocation",
  "recurring_pattern": null,
  "recurrence_id": null,
  "priority": "high",
  "conflicts": [],
  "created_by": "ai",
  "created_at": "2026-02-27T10:00:00Z",
  "last_modified": "2026-02-27T10:00:00Z",
  "status": "confirmed"
}
```

### Validation Rules

- **start_time < end_time**: Event must have positive duration
- **recurring_pattern**: Must be valid RRULE format (RFC 5545)
- **attendees[].email**: Valid email format
- **priority**: One of [high, medium, low]
- **status**: One of [confirmed, tentative, cancelled]

### State Transitions

1. **Created** → status=tentative, conflicts checked
2. **Confirmed** → status=confirmed, invites sent
3. **Rescheduled** → start_time/end_time updated, conflicts rechecked
4. **Cancelled** → status=cancelled, cancellation notices sent

### Relationships

- **CalendarEvent** ← **MeetingNote** (one-to-one): Each event can have meeting notes
- **CalendarEvent** → **Contact** (many-to-many): Attendees linked to contact profiles

---

## 3. Document

Generated documents from templates with version tracking.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| document_id | string | Yes | Unique identifier (e.g., `DOC_status_2026_02_27`) |
| title | string | Yes | Document title |
| document_type | enum | Yes | meeting_notes, status_report, proposal, summary, custom |
| template_used | string | Yes | Template filename (e.g., `weekly-status.md.j2`) |
| generation_date | datetime | Yes | When document was generated |
| version | integer | Yes | Version number (starts at 1) |
| metadata | dict | Yes | Template context variables used |
| content | string | Yes | Document body (Markdown) |
| encryption_status | boolean | Yes | Whether content is encrypted (default: false) |
| generated_by | enum | Yes | ai, scheduled_task |
| edited | boolean | Yes | Whether user has edited after generation (default: false) |
| folder_path | string | Yes | Vault subfolder (e.g., "Documents/Status Reports") |

### Storage Format

Markdown file with YAML frontmatter in `/Documents/{folder_path}/{title}.md`:

```markdown
---
document_id: DOC_status_2026_02_27
title: "Weekly Status Report - Week of Feb 27"
document_type: status_report
template_used: weekly-status.md.j2
generation_date: 2026-02-27T17:00:00Z
version: 1
metadata:
  week_start: 2026-02-24
  week_end: 2026-02-28
  emails_sent: 23
  meetings_attended: 5
  tasks_completed: 12
encryption_status: false
generated_by: scheduled_task
edited: false
folder_path: Documents/Status Reports
---

# Weekly Status Report
**Week of February 27, 2026**

## Summary
This week saw high productivity with 23 emails sent, 5 meetings attended, and 12 tasks completed.

## Key Accomplishments
- Completed Silver Tier implementation (90/98 tasks)
- Created Gold Tier specification
- Reviewed Q2 roadmap with team

## Metrics
...
```

### Validation Rules

- **document_id**: Unique, format `DOC_{type}_{date}`
- **template_used**: Must exist in `.specify/templates/documents/`
- **version**: Auto-incremented on edit
- **document_type**: Must be one of defined types
- **encryption_status**: If true, content must be encrypted

### State Transitions

1. **Generated** → version=1, edited=false
2. **Edited** → version++, edited=true
3. **Regenerated** → new version created, old version archived

### Relationships

- **Document** ← **MeetingNote** (one-to-one): Meeting notes are a document type
- **Document** ← **ScheduledTask** (one-to-many): Tasks generate recurring documents

---

## 4. Insight

Analytics-generated productivity insights and recommendations.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| insight_id | string | Yes | Unique identifier (e.g., `INSIGHT_2026_02_27_001`) |
| insight_type | enum | Yes | pattern, anomaly, recommendation, trend, bottleneck |
| date_generated | datetime | Yes | When insight was generated |
| title | string | Yes | Short insight title |
| description | string | Yes | Detailed insight explanation |
| metrics | dict | Yes | Supporting data (e.g., `{emails_per_day: 15, avg_response_time: "2h"}`) |
| trend_direction | enum | No | improving, declining, stable, null |
| recommendations | list[string] | No | Actionable recommendations |
| priority | enum | Yes | high, medium, low |
| category | enum | Yes | productivity, communication, time_management, trust_effectiveness |
| confidence | float | Yes | Confidence score 0.0-1.0 |
| data_source | string | Yes | Source of analysis (e.g., "audit_logs_30d") |
| user_response | enum | No | null, acknowledged, acted_upon, dismissed |

### Storage Format

JSON file in `/Insights/YYYY-MM-DD.json` (one file per week):

```json
{
  "insights": [
    {
      "insight_id": "INSIGHT_2026_02_27_001",
      "insight_type": "pattern",
      "date_generated": "2026-02-27T17:00:00Z",
      "title": "High Email Volume on Mondays",
      "description": "Analysis shows 40% of weekly emails are sent on Mondays, suggesting potential for scheduling distribution.",
      "metrics": {
        "monday_emails": 60,
        "weekly_total": 150,
        "monday_percentage": 0.40
      },
      "trend_direction": "stable",
      "recommendations": [
        "Consider scheduling non-urgent emails for Tuesday-Thursday",
        "Enable auto-reply trust rule for Monday routine emails"
      ],
      "priority": "medium",
      "category": "communication",
      "confidence": 0.85,
      "data_source": "audit_logs_30d",
      "user_response": null
    }
  ]
}
```

### Validation Rules

- **insight_id**: Unique, format `INSIGHT_{date}_{sequence}`
- **insight_type**: Must be one of defined types
- **confidence**: Range 0.0-1.0
- **metrics**: Must be valid JSON dict
- **trend_direction**: One of [improving, declining, stable] or null

### State Transitions

1. **Generated** → user_response=null
2. **Acknowledged** → user_response=acknowledged
3. **Acted Upon** → user_response=acted_upon (user created trust rule from recommendation)
4. **Dismissed** → user_response=dismissed (confidence decreases for similar future insights)

### Relationships

- **Insight** → **ExecutionLog** (one-to-many): Insights derived from audit log analysis
- **Insight** → **TrustRule** (one-to-many): Recommendations may suggest new trust rules

---

## 5. ProactiveSuggestion

AI-initiated task suggestions based on patterns and context.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| suggestion_id | string | Yes | Unique identifier (e.g., `SUGGEST_followup_2026_02_27`) |
| category | enum | Yes | follow_up, reminder, relationship_maintenance, task_chain |
| reason | string | Yes | Why suggestion was made |
| confidence_score | float | Yes | 0.0-1.0 confidence in suggestion relevance |
| context | string | Yes | Contextual information (e.g., "No reply in 3 days to email about Q2 project") |
| suggested_action | string | Yes | What action to take |
| draft_content | string | No | Pre-drafted email/message if applicable |
| related_entities | list[string] | Yes | Entity IDs this suggestion relates to (email_id, contact_id, etc.) |
| created_at | datetime | Yes | Suggestion creation timestamp |
| expires_at | datetime | No | When suggestion becomes stale (e.g., +7 days) |
| priority | enum | Yes | high, medium, low |
| user_response | enum | No | null, accepted, rejected, modified, expired |
| user_feedback | string | No | Optional feedback text |

### Storage Format

Markdown file in `/Needs_Action/SUGGEST_{category}_{id}.md`:

```markdown
---
suggestion_id: SUGGEST_followup_2026_02_27
type: proactive_suggestion
category: follow_up
reason: "No reply received to important email within 3 days"
confidence_score: 0.82
context: "Email sent 2026-02-24 to john@example.com regarding Q2 project timeline"
suggested_action: "Send follow-up email to check status"
related_entities: ["EMAIL_abc123"]
created_at: 2026-02-27T10:00:00Z
expires_at: 2026-03-06T10:00:00Z
priority: high
user_response: null
user_feedback: null
---

# Proactive Suggestion: Follow-up Email

**Reason**: You sent an email 3 days ago to John Smith about Q2 project timeline with no reply.

**Suggested Action**: Send a polite follow-up email

**Draft Message**:
```
Hi John,

Just wanted to follow up on my email from Monday about the Q2 project timeline.

Do you have any updates on the deliverable dates we discussed?

Best regards
```

**Context**: Original email discussed Q2 milestones and requested timeline confirmation by end of week.

---

**Actions**:
- ✅ **Accept**: Move to /Approved/ to send follow-up
- ❌ **Reject**: Move to /Done/ if not needed
- ✏️ **Modify**: Edit draft message before approving
```

### Validation Rules

- **suggestion_id**: Unique, format `SUGGEST_{category}_{id}`
- **category**: One of defined categories
- **confidence_score**: Range 0.0-1.0
- **expires_at**: Must be after created_at
- **user_response**: One of [accepted, rejected, modified, expired] or null

### State Transitions

1. **Created** → user_response=null, placed in /Needs_Action/
2. **Accepted** → user_response=accepted, moved to /Approved/ or executed
3. **Rejected** → user_response=rejected, moved to /Done/, confidence decreased for similar suggestions
4. **Modified** → user_response=modified, user edited before accepting
5. **Expired** → user_response=expired if no action before expires_at

### Relationships

- **ProactiveSuggestion** → **Contact** (many-to-one): Follow-ups link to contacts
- **ProactiveSuggestion** → **Email** (many-to-one): Follow-ups reference original emails
- **ProactiveSuggestion** → **ExecutionLog** (one-to-one): Accepted suggestions create execution logs

---

## 6. MeetingNote

Transcribed and structured notes from meetings the AI attended.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| note_id | string | Yes | Unique identifier (e.g., `MEETING_2026_02_27_abc`) |
| meeting_id | string | Yes | Reference to CalendarEvent event_id |
| meeting_date | datetime | Yes | When meeting occurred |
| attendees | list[dict] | Yes | Attendee list `[{name, email, role}]` |
| duration_minutes | integer | Yes | Meeting duration |
| transcript | string | Yes | Full meeting transcript (may be encrypted) |
| summary | string | Yes | AI-generated summary |
| key_points | list[string] | Yes | Main discussion points |
| decisions_made | list[string] | No | Decisions reached during meeting |
| action_items | list[dict] | No | `[{task, assignee, deadline}]` |
| highlights | list[dict] | No | `[{timestamp, content}]` important moments |
| recording_link | string | No | Link to audio/video recording file |
| recording_consent | boolean | Yes | Whether consent was obtained |
| encryption_status | boolean | Yes | Whether transcript/recording are encrypted |
| confidence | float | Yes | Transcript accuracy confidence 0.0-1.0 |

### Storage Format

Markdown file in `/Meetings/YYYY-MM-DD_{title}.md`:

```markdown
---
note_id: MEETING_2026_02_27_abc
meeting_id: CAL_abc123xyz
meeting_date: 2026-02-27T14:00:00Z
attendees:
  - name: John Smith
    email: john@example.com
    role: Product Manager
  - name: Jane Doe
    email: jane@example.com
    role: Engineering Lead
duration_minutes: 60
recording_link: /Meetings/Recordings/2026-02-27_planning.m4a
recording_consent: true
encryption_status: false
confidence: 0.92
---

# Q2 Planning Meeting Notes
**Date**: February 27, 2026 | **Duration**: 60 minutes

## Attendees
- John Smith (Product Manager)
- Jane Doe (Engineering Lead)
- AI Assistant (Note Taker)

## Summary
Team discussed Q2 objectives and resource allocation. Key decisions made on feature prioritization and timeline.

## Key Discussion Points
- Gold Tier feature scope and MVP definition
- Resource allocation for Q2 sprint planning
- Timeline constraints and dependencies

## Decisions Made
1. Gold Tier MVP will focus on Trust Framework (US1) and Calendar Management (US2)
2. Development timeline: 6 weeks for MVP
3. Weekly check-ins scheduled for Fridays at 2pm

## Action Items
- [ ] **John**: Send updated roadmap by EOW (Due: 2026-03-01)
- [ ] **Jane**: Review technical architecture plan (Due: 2026-03-03)
- [ ] **Team**: Begin sprint planning next Monday

## Highlights
- [00:15:30] John: "Trust framework is critical path for all autonomous features"
- [00:42:15] Jane: "We should validate Google Calendar API rate limits early"

---

**Full Transcript**: [View encrypted transcript](/Meetings/Transcripts/2026-02-27_planning.encrypted.txt)
```

### Validation Rules

- **note_id**: Unique, format `MEETING_{date}_{short_id}`
- **meeting_id**: Must reference existing CalendarEvent
- **attendees**: At least 1 attendee
- **recording_consent**: Must be true (legal requirement)
- **confidence**: Range 0.0-1.0

### State Transitions

1. **Recording Started** → consent announced and obtained
2. **Meeting Ended** → audio saved, transcription queued
3. **Transcribed** → notes generated, action items extracted
4. **Reviewed** → user can edit/approve notes

### Relationships

- **MeetingNote** → **CalendarEvent** (many-to-one): Notes link to calendar events
- **MeetingNote** → **Contact** (many-to-many): Attendees linked to contact profiles
- **MeetingNote** → **ActionPlan** (one-to-many): Action items become tasks

---

## 7. Contact

CRM profile for relationship tracking and management.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| contact_id | string | Yes | Unique identifier (e.g., `CONTACT_john_smith`) |
| name | string | Yes | Full name |
| email | string | Yes | Primary email (unique key) |
| phone | string | No | Phone number (E.164 format) |
| organization | string | No | Company/organization |
| title | string | No | Job title |
| first_contact_date | datetime | Yes | When first interaction occurred |
| last_contact_date | datetime | Yes | Most recent interaction |
| interaction_count | integer | Yes | Total interactions (emails, meetings, WhatsApp) |
| relationship_strength | integer | Yes | Score: `interaction_count * 10 - days_since_last_contact` |
| vip | boolean | Yes | Whether contact is VIP (default: false) |
| important_dates | list[dict] | No | `[{date, event}]` birthdays, anniversaries, etc. |
| tags | list[string] | No | Custom tags (client, vendor, team, executive, etc.) |
| notes | string | No | Freeform notes |
| encryption_status | boolean | Yes | Whether contact data is encrypted (default: false) |

### Storage Format

Markdown file in `/Contacts/{contact_id}.md`:

```markdown
---
contact_id: CONTACT_john_smith
name: John Smith
email: john.smith@example.com
phone: +14155551234
organization: Acme Corp
title: VP Engineering
first_contact_date: 2025-11-15T10:00:00Z
last_contact_date: 2026-02-27T14:00:00Z
interaction_count: 28
relationship_strength: 176
vip: true
important_dates:
  - date: 2026-05-15
    event: Birthday
  - date: 2026-09-01
    event: Work Anniversary (5 years)
tags: [client, executive, decision_maker]
encryption_status: false
---

# John Smith
**VP Engineering at Acme Corp** | [john.smith@example.com](mailto:john.smith@example.com) | +14155551234

## Relationship Summary
- **First Contact**: November 2025
- **Interactions**: 28 (emails, meetings, calls)
- **Last Contact**: 3 days ago
- **Relationship Strength**: 176 (Strong)

## Conversation History

### 2026-02-27 - Q2 Planning Discussion
**Medium**: Meeting
- Discussed Gold Tier roadmap
- Action: Send technical architecture plan by March 3
- Topics: Resource allocation, timeline, MVP scope

### 2026-02-20 - Project Update
**Medium**: Email
- Confirmed Q1 deliverables on track
- Requested timeline for Q2 features
- Follow-up: Proposal sent Feb 21

### 2025-12-15 - Initial Project Kickoff
**Medium**: Meeting
- Introduced team members
- Discussed project requirements and timeline
- Action: Technical proposal delivered Dec 20

## Important Notes
- Decision maker for technical purchases
- Prefers early morning meetings (8-9am)
- Responds quickly to urgent emails (avg 2h response time)
- Annual budget planning happens in November
```

### Validation Rules

- **contact_id**: Unique, format `CONTACT_{lowercase_name_slug}`
- **email**: Valid email format, unique across all contacts
- **phone**: E.164 format if provided
- **relationship_strength**: Recalculated on each interaction
- **important_dates**: ISO date format

### State Transitions

1. **Created** → interaction_count=1, relationship_strength calculated
2. **Interaction Added** → interaction_count++, last_contact_date updated, relationship_strength recalculated
3. **VIP Promoted** → vip=true (manual or auto-promotion if relationship_strength > 200)
4. **Stale Detected** → 30 days since last contact for VIP triggers follow-up suggestion

### Relationships

- **Contact** → **Email** (one-to-many): All emails from/to contact
- **Contact** → **MeetingNote** (many-to-many): Meetings attended
- **Contact** → **WhatsAppMessage** (one-to-many): WhatsApp conversations
- **Contact** → **ProactiveSuggestion** (one-to-many): Follow-up suggestions

---

## 8. Expense

Business expense tracking with OCR extraction from receipts.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| expense_id | string | Yes | Unique identifier (e.g., `EXPENSE_2026_02_27_001`) |
| amount | decimal | Yes | Expense amount (e.g., 45.99) |
| currency | string | Yes | ISO 4217 currency code (default: USD) |
| vendor | string | Yes | Merchant/vendor name |
| expense_date | date | Yes | When expense occurred |
| category | enum | Yes | software, travel, office, marketing, meals, transportation, utilities, other |
| description | string | No | Expense description/memo |
| receipt_file | string | Yes | Path to receipt image/PDF in vault |
| budget_category_id | string | Yes | Reference to Budget allocation |
| flagged_for_review | boolean | Yes | Whether expense needs review (default: false) |
| review_reason | string | No | Why flagged (e.g., "3x category average") |
| approval_status | enum | Yes | pending, approved, rejected |
| approved_by | string | No | Who approved (user, auto) |
| approved_at | datetime | No | Approval timestamp |
| ocr_confidence | float | Yes | OCR extraction confidence 0.0-1.0 |
| created_at | datetime | Yes | Creation timestamp |

### Storage Format

Markdown file in `/Expenses/YYYY-MM/{expense_id}.md`:

```markdown
---
expense_id: EXPENSE_2026_02_27_001
amount: 45.99
currency: USD
vendor: "Adobe Creative Cloud"
expense_date: 2026-02-27
category: software
description: "Monthly subscription - Creative Cloud All Apps"
receipt_file: /Receipts/2026-02-27_adobe_receipt.pdf
budget_category_id: BUDGET_software_2026_02
flagged_for_review: false
review_reason: null
approval_status: approved
approved_by: auto
approved_at: 2026-02-27T15:30:00Z
ocr_confidence: 0.95
created_at: 2026-02-27T15:28:00Z
---

# Expense: Adobe Creative Cloud
**Amount**: $45.99 | **Date**: 2026-02-27 | **Category**: Software

## Details
- **Vendor**: Adobe Creative Cloud
- **Description**: Monthly subscription - Creative Cloud All Apps
- **Receipt**: [View PDF](/Receipts/2026-02-27_adobe_receipt.pdf)

## Budget Tracking
- **Category**: Software
- **Monthly Budget**: $500.00
- **Current Spend**: $325.50 (65% used)
- **Remaining**: $174.50

## Approval
- **Status**: ✅ Approved
- **Approved By**: Auto (recurring vendor, within budget)
- **Approved At**: 2026-02-27 3:30 PM
```

### Validation Rules

- **expense_id**: Unique, format `EXPENSE_{date}_{sequence}`
- **amount**: Positive decimal with 2 decimal places
- **currency**: Valid ISO 4217 code
- **expense_date**: Cannot be future date
- **category**: Must be one of defined categories
- **ocr_confidence**: Range 0.0-1.0
- **approval_status**: One of [pending, approved, rejected]

### State Transitions

1. **Extracted** → OCR processes receipt, expense created with approval_status=pending
2. **Auto-Approved** → Within budget, recurring vendor → approval_status=approved, approved_by=auto
3. **Flagged** → Unusual amount → flagged_for_review=true, approval_status=pending
4. **Approved** → User approves → approval_status=approved, approved_by=user
5. **Rejected** → User rejects → approval_status=rejected

### Relationships

- **Expense** → **Budget** (many-to-one): Each expense charges against a budget category
- **Expense** → **Email** (many-to-one): Receipt emails link to expenses

---

## 9. Budget

Monthly budget allocations by expense category.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| budget_id | string | Yes | Unique identifier (e.g., `BUDGET_software_2026_02`) |
| category | enum | Yes | Must match Expense categories |
| month | string | Yes | YYYY-MM format |
| monthly_limit | decimal | Yes | Budget allocation for the month |
| current_spend | decimal | Yes | Current total expenses (default: 0.00) |
| alerts_enabled | boolean | Yes | Whether to send budget alerts (default: true) |
| alert_threshold | float | Yes | Percentage to trigger alert (default: 0.80 = 80%) |
| alert_sent | boolean | Yes | Whether threshold alert already sent (default: false) |
| currency | string | Yes | ISO 4217 currency code (default: USD) |
| rollover_enabled | boolean | Yes | Whether unused budget rolls to next month (default: false) |

### Storage Format

JSON file in `/Budgets/YYYY-MM.json`:

```json
{
  "month": "2026-02",
  "budgets": [
    {
      "budget_id": "BUDGET_software_2026_02",
      "category": "software",
      "month": "2026-02",
      "monthly_limit": 500.00,
      "current_spend": 325.50,
      "alerts_enabled": true,
      "alert_threshold": 0.80,
      "alert_sent": false,
      "currency": "USD",
      "rollover_enabled": false
    },
    {
      "budget_id": "BUDGET_travel_2026_02",
      "category": "travel",
      "month": "2026-02",
      "monthly_limit": 1000.00,
      "current_spend": 850.00,
      "alerts_enabled": true,
      "alert_threshold": 0.80,
      "alert_sent": true,
      "currency": "USD",
      "rollover_enabled": false
    }
  ]
}
```

### Validation Rules

- **budget_id**: Unique, format `BUDGET_{category}_{month}`
- **monthly_limit**: Positive decimal
- **current_spend**: Cannot exceed monthly_limit (warning, not hard limit)
- **alert_threshold**: Range 0.0-1.0
- **month**: Valid YYYY-MM format

### State Transitions

1. **Created** → current_spend=0.00, alert_sent=false
2. **Expense Added** → current_spend += expense_amount
3. **Alert Threshold Reached** → alert_sent=true, alert created in /Needs_Action/
4. **Month End** → Budget rolled to next month (if rollover_enabled) or reset

### Relationships

- **Budget** ← **Expense** (one-to-many): Expenses charge against budget categories

---

## Entity Relationship Diagram

```
TrustRule ──────> ExecutionLog (trust_rule_id)
    │
    └──────────> Feedback (effectiveness_score)

CalendarEvent ──> MeetingNote (meeting_id)
    │
    └──────────> Contact (attendees)

Document ────────> ScheduledTask (generated_by)
    │
    └──────────> MeetingNote (one type of document)

Insight ─────────> ExecutionLog (data_source)
    │
    └──────────> TrustRule (recommendations)

ProactiveSuggestion ───> Contact (related_contacts)
    │
    ├──────────> Email (related_emails)
    └──────────> ExecutionLog (accepted → executed)

MeetingNote ─────> CalendarEvent (meeting_id)
    │
    ├──────────> Contact (attendees)
    └──────────> ActionPlan (action_items)

Contact ─────────> Email (many-to-many)
    │
    ├──────────> MeetingNote (many-to-many)
    ├──────────> WhatsAppMessage (one-to-many)
    └──────────> ProactiveSuggestion (one-to-many)

Expense ─────────> Budget (budget_category_id)
    │
    └──────────> Email (receipt source)

Budget ──────────> Expense (one-to-many)
```

---

## Data Model Completion

✅ 9 entities documented with full field definitions
✅ Storage formats defined (Markdown frontmatter, JSON files)
✅ Validation rules specified
✅ State transitions documented
✅ Relationships mapped

**Next Phase**: Generate API contracts (contracts/)
