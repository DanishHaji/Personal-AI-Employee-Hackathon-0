# Implementation Plan: Silver Tier - Autonomous Task Execution & Multi-Channel Communication

**Branch**: `002-silver-tier-upgrade` | **Date**: 2026-02-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-silver-tier-upgrade/spec.md`

## Summary

Silver Tier transforms the AI Employee from a passive observer (Bronze) to an active executor. The system will autonomously execute approved plans by sending emails, posting to social media (LinkedIn, Facebook, Twitter), monitoring WhatsApp Business messages, and running scheduled tasks like daily briefings. All outbound actions require manual approval via HITL workflow (move files from /Needs_Action/ to /Approved/). The architecture builds on Bronze Tier foundation (vault, watchers, orchestrator) and adds: (1) Execution Engine that processes approved plans, (2) MCP Client Library for external integrations, (3) Scheduling Engine for time-based tasks, (4) WhatsApp watcher for instant messaging monitoring.

**Technical Approach**: Extend existing Python codebase with three new components: `executor.py` (monitors /Approved/, executes plans via MCP servers), `scheduler.py` (manages scheduled tasks, generates briefings), and `mcp_client.py` (common MCP protocol client). Add four new entity models (WhatsAppMessage, SocialMediaPost, ScheduledTask, ExecutionLog). Integrate five MCP servers (Gmail send, LinkedIn, Facebook, Twitter, WhatsApp). All dependencies managed via UV. All state persisted in vault Markdown files and JSON logs. No database, no cloud storage.

## Technical Context

**Language/Version**: Python 3.12+ (3.13+ recommended, 3.12.3 validated in Bronze Tier)
**Primary Dependencies**:
- **Existing (Bronze Tier)**: google-auth (2.48.0), google-api-python-client (2.190.0), watchdog (6.0.0), python-dotenv (1.2.1), pyyaml (6.0.3)
- **New (Silver Tier)**: mcp (MCP SDK for Python client), apscheduler (3.10+, for cron-like scheduling), requests (2.31+, for HTTP calls to MCP servers), jsonschema (4.20+, for plan validation)

**Storage**: File-based only (Markdown with YAML frontmatter for entities, JSON for logs and state). No database (per constitution).
**Testing**: pytest (7.0+), pytest-cov (4.0+) for coverage (Bronze Tier development dependencies already configured)
**Target Platform**: Cross-platform (Windows/WSL, macOS, Linux) - pathlib for path handling
**Project Type**: Single Python project with modular components (extends Bronze Tier structure)
**Performance Goals**:
- Email sends: <2 minutes from approval to Gmail API call completion
- Social posts: <3 minutes from approval to platform publish
- WhatsApp detection: <2 minutes from message receipt to /Needs_Action/ entity
- Scheduled tasks: 95% punctuality (execute within 60-second window of scheduled time)
- Dashboard updates: <60 seconds for execution status reflection

**Constraints**:
- **UV Package Manager**: All dependencies via UV, pyproject.toml updates only (NO pip)
- **No Database**: File-based state only (Markdown, JSON logs)
- **MCP Protocol**: All external integrations via MCP servers (Gmail send, social media, WhatsApp) - NO direct API calls
- **Local-First**: All data in Obsidian vault, credentials in .env (never in vault)
- **PM2 Management**: All background processes (watchers, executor, scheduler, orchestrator) manageable via PM2
- **Rate Limiting**: Respect API limits (Gmail: 500/day, LinkedIn: 100/day, Twitter: 2400/day, Facebook: 200/day, WhatsApp: 1000/day inbound)
- **Graceful Degradation**: If one MCP server fails, others continue working
- **HITL Approval**: All outbound actions require manual approval (move to /Approved/)

**Scale/Scope**:
- Support 50+ email sends per day, 20+ social posts per day, 100+ WhatsApp messages per day
- Handle 10+ scheduled tasks with various recurrence patterns
- Maintain audit logs with 90-day retention
- Dashboard updates for 1000+ vault items

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### I. Local-First Privacy (NON-NEGOTIABLE)

**Status**: ✅ **COMPLIANT**

- All entity data (WhatsAppMessage, SocialMediaPost, ScheduledTask, ExecutionLog) stored as Markdown in vault
- OAuth credentials for MCP servers stored in .env (outside vault, in .gitignore)
- WhatsApp Business API tokens never synced to cloud (local .env only)
- Vault remains single source of truth for all state
- No cloud databases or external persistent storage

**Implementation**:
- New entities in /Needs_Action/ (WhatsApp), /Approved/ (social posts, email plans), /Logs/ (execution logs)
- MCP server credentials in .env with keys: GMAIL_MCP_URL, LINKEDIN_MCP_URL, FACEBOOK_MCP_URL, TWITTER_MCP_URL, WHATSAPP_MCP_URL
- Sensitive tokens (OAuth refresh tokens) use OS secrets manager or .env with strict .gitignore

### II. Human-in-the-Loop (HITL) - Critical Actions

**Status**: ✅ **COMPLIANT**

- All outbound actions (email sends, social posts) require manual approval
- Approval workflow: AI creates plan in /Needs_Action/ → Human reviews and moves to /Approved/ → Executor runs
- No auto-approval for Silver Tier (deferred to Gold Tier with configurable thresholds)
- Approval audit trail: plan metadata includes approved_by, approval_timestamp

**Auto-Approve Thresholds**: None for Silver Tier (always require approval)

**Always Require Approval** (Silver Tier):
- All email sends (replies, new emails, forwards)
- All social media posts (LinkedIn, Facebook, Twitter)
- All WhatsApp replies (monitoring only in Silver, replies deferred to Gold)
- All scheduled task outputs (briefings, summaries)

**Implementation**:
- Executor.py monitors /Approved/ folder using watchdog library
- Plan validation checks for approval metadata before execution
- Failed executions move plan back to /Needs_Action/ with error details

### III. Security & Credential Management (NON-NEGOTIABLE)

**Status**: ✅ **COMPLIANT**

- All MCP server URLs and credentials in .env file
- No hardcoded secrets in source code
- Development mode support (DRY_RUN=true prevents real API calls)
- All executions logged to audit log with full traceability

**Audit Log Format** (extended for Silver Tier):
```json
{
  "timestamp": "2026-02-25T14:30:00Z",
  "action_type": "email_send|social_post|whatsapp_detect|scheduled_task",
  "actor": "executor|scheduler|whatsapp_watcher",
  "target": "recipient@example.com|linkedin|facebook|twitter|whatsapp",
  "plan_id": "PLAN_email_reply_1234567890.md",
  "parameters": {
    "platform": "linkedin",
    "content_preview": "First 100 chars...",
    "scheduled_time": "2026-02-25T15:00:00Z"
  },
  "approval_status": "approved",
  "approved_by": "human",
  "approval_timestamp": "2026-02-25T14:25:00Z",
  "result": "success|failure|partial",
  "mcp_server": "linkedin_mcp",
  "response": {
    "post_url": "https://linkedin.com/posts/123",
    "post_id": "abc123"
  },
  "error": "null or error message",
  "duration_ms": 1234
}
```

**Implementation**:
- .env.example updated with MCP server configuration templates
- Audit logger extended with new action types and MCP response fields
- DRY_RUN mode: executor logs actions but skips MCP calls
- Credential rotation: Monthly reminder in dashboard (manual process)

### IV. Agent Skills Architecture (NON-NEGOTIABLE)

**Status**: ✅ **COMPLIANT**

- All Silver Tier functionality implemented as Agent Skills in `.claude/commands/`
- Existing skills extended: vault-manager.md, email-triage.md, dashboard-updater.md
- New skills created: executor-skill.md, scheduler-skill.md, social-media-manager.md, whatsapp-processor.md

**Required Skills (Silver Tier)**:
- **executor-skill.md**: Processes approved plans, calls MCP servers, handles errors
- **scheduler-skill.md**: Manages scheduled tasks, generates briefings/summaries
- **social-media-manager.md**: Validates post content, handles multi-platform posting
- **whatsapp-processor.md**: Processes WhatsApp messages, detects priority contacts
- **vault-manager.md** (extended): New entity types (WhatsAppMessage, SocialMediaPost, ScheduledTask)

**Skill Dependencies**:
- executor-skill.md → vault-manager.md (read/write plans)
- scheduler-skill.md → dashboard-updater.md (update stats)
- social-media-manager.md → executor-skill.md (invoked for posting)
- whatsapp-processor.md → vault-manager.md (create entities)

**Implementation**:
- Each skill has clear input schema, output format, error handling
- Skills follow single responsibility principle
- No circular dependencies (enforced in skill design)

### V. Tiered Implementation - Progressive Delivery

**Status**: ✅ **COMPLIANT**

- Silver Tier builds on Bronze Tier foundation (all Bronze requirements maintained)
- Bronze Tier capabilities preserved: Gmail monitoring, file drop, vault management, basic orchestrator
- Silver Tier adds: Email sending, social media posting, WhatsApp monitoring, scheduled tasks
- No Bronze Tier regressions (validated via Bronze Tier test suite)

**Bronze Tier Preserved**:
- ✅ Obsidian vault with Dashboard.md and Company_Handbook.md
- ✅ Gmail watcher (optional, can be enabled later)
- ✅ Filesystem watcher (always enabled)
- ✅ Orchestrator (monitors /Needs_Action/)
- ✅ Vault structure: /Inbox, /Needs_Action, /Plans, /Done, /Logs, /Quarantine

**Silver Tier Added**:
- ✅ Executor (monitors /Approved/, executes plans)
- ✅ Scheduler (manages scheduled tasks)
- ✅ WhatsApp watcher (polls WhatsApp Business API)
- ✅ MCP client library (common integration layer)
- ✅ Extended vault structure: /Approved folder, /Pending_Approval (future)

**Implementation**:
- Executor and scheduler run as separate PM2 processes
- Bronze Tier code unchanged (no refactoring unless necessary)
- New dependencies added to pyproject.toml via UV
- ecosystem.config.js updated with executor and scheduler processes

### VI. Autonomous Operation - Ralph Wiggum Loop

**Status**: ⚠️ **PARTIAL COMPLIANCE** (Not required for Silver Tier)

- Ralph Wiggum loop not implemented in Silver Tier (deferred to Gold Tier)
- Silver Tier executions are single-step (approve plan → execute action → done)
- Multi-step task completion deferred to Gold Tier with full Ralph Wiggum implementation

**Rationale**: Silver Tier focuses on single-action execution (send email, post to LinkedIn). Multi-step orchestration (e.g., "research topic, draft post, publish, monitor engagement") requires Ralph Wiggum loop and is a Gold Tier feature.

**Future**: Gold Tier will add Ralph Wiggum loop for autonomous multi-step completion.

### VII. Observability & Audit Logging

**Status**: ✅ **COMPLIANT**

- All executions logged to `/Logs/YYYY-MM-DD.json` in structured JSON format
- Audit log includes: timestamp, actor, action, target, plan_id, approval_status, result, duration, MCP server response
- Execution errors include full error message and context
- Log rotation: Daily files, 90-day retention minimum

**Health Monitoring** (Silver Tier):
- PM2 provides process monitoring (auto-restart on crashes)
- Executor and scheduler log heartbeat every 60 seconds
- Dashboard.md updated with last execution time for each component
- Error alerts: Failed executions create alert files in /Inbox/

**Logging Streams**:
- Watcher logs: `logs/pm2/whatsapp-watcher-out.log`, `logs/pm2/whatsapp-watcher-error.log`
- Executor logs: `logs/pm2/executor-out.log`, `logs/pm2/executor-error.log`
- Scheduler logs: `logs/pm2/scheduler-out.log`, `logs/pm2/scheduler-error.log`
- Audit logs: `vault/Logs/YYYY-MM-DD.json`

**Implementation**:
- AuditLogger extended with new action types (social_post, whatsapp_detect, scheduled_task)
- Error context includes: plan ID, MCP server, API response, stack trace
- Dashboard updater reads last 24h of audit logs to calculate execution stats

**Constitution Compliance Summary**:
- ✅ 6 out of 7 principles fully compliant
- ⚠️ 1 principle partially compliant (Ralph Wiggum loop deferred to Gold Tier)
- 🚫 0 violations
- **GATE PASSED**: Proceed to Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/002-silver-tier-upgrade/
├── spec.md                  # Feature specification (created by /sp.specify)
├── plan.md                  # This file (created by /sp.plan)
├── research.md              # Phase 0 output (created by /sp.plan)
├── data-model.md            # Phase 1 output (created by /sp.plan)
├── quickstart.md            # Phase 1 output (created by /sp.plan)
├── contracts/               # Phase 1 output (created by /sp.plan)
│   ├── email-plan-schema.json      # Email send plan validation schema
│   ├── social-post-plan-schema.json # Social media post plan schema
│   ├── scheduled-task-schema.json   # Scheduled task definition schema
│   └── execution-log-schema.json    # Execution log format schema
├── checklists/
│   └── requirements.md      # Spec quality validation (already created)
└── tasks.md                 # Phase 2 output (created by /sp.tasks - NOT created by /sp.plan)
```

### Source Code (repository root)

**Structure Decision**: Extend existing Bronze Tier single-project structure. Silver Tier adds new modules to `src/` without changing Bronze Tier layout.

```text
src/
├── models/                          # Data models (Bronze + Silver entities)
│   ├── __init__.py
│   ├── email.py                     # EXISTING (Bronze Tier)
│   ├── file_drop.py                 # EXISTING (Bronze Tier)
│   ├── action_plan.py               # EXISTING (Bronze Tier)
│   ├── whatsapp_message.py          # NEW (Silver Tier - US3)
│   ├── social_media_post.py         # NEW (Silver Tier - US2)
│   ├── scheduled_task.py            # NEW (Silver Tier - US4)
│   └── execution_log.py             # NEW (Silver Tier - US1)
│
├── services/                        # Business logic services
│   ├── __init__.py
│   ├── gmail_service.py             # EXISTING (Bronze Tier - read-only)
│   ├── vault_service.py             # EXISTING (Bronze Tier)
│   ├── logger_service.py            # EXISTING (Bronze Tier - extended for Silver)
│   ├── mcp_client.py                # NEW (Silver Tier - common MCP client)
│   ├── executor_service.py          # NEW (Silver Tier - US1)
│   ├── scheduler_service.py         # NEW (Silver Tier - US4)
│   ├── social_media_service.py      # NEW (Silver Tier - US2)
│   └── whatsapp_service.py          # NEW (Silver Tier - US3)
│
├── watchers/                        # Background monitoring scripts
│   ├── __init__.py
│   ├── base_watcher.py              # EXISTING (Bronze Tier)
│   ├── gmail_watcher.py             # EXISTING (Bronze Tier - optional)
│   ├── filesystem_watcher.py        # EXISTING (Bronze Tier)
│   └── whatsapp_watcher.py          # NEW (Silver Tier - US3)
│
├── executor.py                      # NEW (Silver Tier - US1 main process)
├── scheduler.py                     # NEW (Silver Tier - US4 main process)
├── orchestrator.py                  # EXISTING (Bronze Tier - extended)
└── init_vault.py                    # EXISTING (Bronze Tier - extended for new folders)

.claude/commands/                    # Agent Skills
├── vault-manager.md                 # EXISTING (extended for new entities)
├── email-triage.md                  # EXISTING (Bronze Tier)
├── file-processor.md                # EXISTING (Bronze Tier)
├── dashboard-updater.md             # EXISTING (extended for execution stats)
├── executor-skill.md                # NEW (Silver Tier - plan execution)
├── scheduler-skill.md               # NEW (Silver Tier - scheduled tasks)
├── social-media-manager.md          # NEW (Silver Tier - post management)
└── whatsapp-processor.md            # NEW (Silver Tier - message processing)

tests/                               # Test suite
├── contract/                        # Contract tests (plan schema validation)
│   ├── test_email_plan_contract.py
│   ├── test_social_plan_contract.py
│   └── test_scheduled_task_contract.py
│
├── integration/                     # Integration tests (with MCP mocks)
│   ├── test_executor_integration.py
│   ├── test_scheduler_integration.py
│   ├── test_social_media_integration.py
│   └── test_whatsapp_integration.py
│
└── unit/                            # Unit tests
    ├── models/
    │   ├── test_whatsapp_message.py
    │   ├── test_social_media_post.py
    │   ├── test_scheduled_task.py
    │   └── test_execution_log.py
    │
    └── services/
        ├── test_mcp_client.py
        ├── test_executor_service.py
        ├── test_scheduler_service.py
        ├── test_social_media_service.py
        └── test_whatsapp_service.py

vault/                               # Obsidian vault (user's vault path)
├── Inbox/                           # EXISTING (Bronze Tier)
├── Needs_Action/                    # EXISTING (Bronze Tier)
├── Plans/                           # EXISTING (Bronze Tier)
├── Approved/                        # NEW (Silver Tier - for HITL workflow)
├── Pending_Approval/                # FUTURE (Gold Tier - placeholder)
├── Done/                            # EXISTING (Bronze Tier)
├── Logs/                            # EXISTING (Bronze Tier - extended)
│   ├── YYYY-MM-DD.json              # Daily audit logs
│   ├── execution_state.json         # Execution queue and retry state
│   └── schedule_state.json          # Scheduled task last run times
├── Quarantine/                      # EXISTING (Bronze Tier)
├── Dashboard.md                     # EXISTING (extended with execution stats)
├── Company_Handbook.md              # EXISTING (extended with scheduled task definitions)
└── README.md                        # EXISTING (Bronze Tier)
```

**Key Structure Decisions**:

1. **Models**: Four new entity classes following Bronze Tier pattern (dataclass with YAML frontmatter serialization)
2. **Services**: MCP client as shared service, executor/scheduler/social/whatsapp as specialized services
3. **Watchers**: WhatsApp watcher follows base_watcher.py pattern from Bronze Tier
4. **Main Processes**: executor.py and scheduler.py as top-level scripts (similar to orchestrator.py)
5. **Vault**: Add /Approved/ folder for HITL workflow, extend /Logs/ with new state files
6. **Tests**: Contract tests for plan schemas, integration tests with MCP mocks, unit tests for new components

## Complexity Tracking

> No constitution violations requiring justification. All gates passed.

*This section intentionally left empty as no complexity exceptions needed.*

## Phase 0: Research & Technology Decisions

### Research Task 1: MCP Server Integration Patterns

**Objective**: Determine best practices for integrating MCP servers in Python, including authentication, error handling, retry logic, and connection pooling.

**Research Questions**:
1. What is the canonical Python MCP SDK and how to use it?
2. How to handle MCP server authentication (OAuth2 tokens, API keys)?
3. What retry strategies work best for transient MCP failures?
4. How to implement connection pooling for multiple concurrent MCP calls?
5. How to mock MCP servers for integration testing?

**Expected Findings**:
- Python MCP SDK: `mcp` package (official Anthropic SDK)
- Authentication: Pass tokens via MCP context, refresh on 401 errors
- Retry: Exponential backoff with jitter (1s, 2s, 4s, 8s, max 60s)
- Pooling: Connection pool per MCP server (max 5 concurrent)
- Testing: MCP mock server or VCR-style request recording

**Decision Rationale**: MCP servers are the primary integration mechanism for Silver Tier. Robust client implementation is critical for reliability.

### Research Task 2: Scheduling Library Selection

**Objective**: Choose Python scheduling library for cron-like scheduled tasks with persistent state.

**Options Considered**:
1. **APScheduler** (AsyncIO-based job scheduling)
   - Pros: Cron syntax support, persistent job stores, well-maintained
   - Cons: Requires event loop management
2. **schedule** (Lightweight job scheduling)
   - Pros: Simple API, no dependencies
   - Cons: No persistence, no cron syntax, manual state management
3. **Celery** (Distributed task queue)
   - Pros: Production-grade, Redis/RabbitMQ backends
   - Cons: Overkill for single-user system, requires message broker

**Decision**: **APScheduler 3.10+**

**Rationale**:
- Supports cron-like scheduling patterns (daily, weekly, custom)
- Persistent job stores (can use JSON file store, no Redis needed)
- Missed execution handling (catch-up within grace period)
- Well-documented and actively maintained
- No external dependencies (can use MemoryJobStore or JSON file)

**Implementation**:
- Use APScheduler with custom JSON-based job store (write to vault/Logs/schedule_state.json)
- Schedule definitions loaded from Company_Handbook.md on startup
- Scheduler runs as PM2 process, checks every 10 seconds

### Research Task 3: Rate Limiting Strategies

**Objective**: Implement rate limiting for API calls to stay within platform quotas.

**Requirements**:
- Gmail: Max 500 emails/day (1 per 5 seconds minimum)
- LinkedIn: Max 100 posts/day
- Twitter: Max 2400 tweets/day
- Facebook: Max 200 posts/day
- WhatsApp: Max 1000 messages/day inbound (no sending in Silver)

**Options Considered**:
1. **Token Bucket** (allows bursts, refills over time)
2. **Leaky Bucket** (constant rate, no bursts)
3. **Fixed Window** (count per time window, resets)
4. **Sliding Window** (count per rolling time window)

**Decision**: **Token Bucket with persistent state**

**Rationale**:
- Allows short bursts (send 3 emails quickly if quota available)
- Prevents long-term quota exhaustion
- Easy to implement with JSON state file
- Matches platform behavior (most APIs use token bucket internally)

**Implementation**:
- Rate limiter class with tokens, refill rate, max bucket size
- State persisted to vault/Logs/rate_limit_state.json
- Checked before each MCP call, block if no tokens available
- Per-platform buckets (separate limits for Gmail, LinkedIn, etc.)

### Research Task 4: Plan Validation Schema

**Objective**: Define JSON schema for plan validation before execution.

**Plan Types**:
1. **Email Send Plan**: Recipient, subject, body, thread_id (optional), in_reply_to (optional)
2. **Social Media Post Plan**: Platform(s), content, media (optional), scheduled_time (optional)
3. **Scheduled Task Definition**: Task name, schedule (cron pattern), last_run, next_run
4. **Execution Log**: Plan ID, action type, result, MCP response

**Decision**: **JSON Schema with jsonschema library**

**Rationale**:
- Standard validation format
- Generates clear error messages for plan creators
- Reusable across different plan types
- Integrates with pytest for contract testing

**Implementation**:
- Schema files in specs/002-silver-tier-upgrade/contracts/
- Validator service validates plans before executor processes them
- Invalid plans moved to /Quarantine/ with validation error details

### Research Task 5: WhatsApp Business API Integration

**Objective**: Determine how to connect to WhatsApp Business API for message monitoring.

**Options Considered**:
1. **WhatsApp Business Cloud API** (official Meta API)
   - Pros: Official, reliable, webhook support
   - Cons: Requires Meta app approval, complex setup
2. **WhatsApp Business On-Premises API** (self-hosted)
   - Pros: Full control, no Meta approval
   - Cons: Expensive, complex infrastructure
3. **Third-Party MCP Server** (community-built)
   - Pros: Abstracted complexity, MCP protocol
   - Cons: Depends on third-party reliability

**Decision**: **WhatsApp Business Cloud API via MCP server**

**Rationale**:
- Official API is most reliable long-term
- MCP server abstracts authentication complexity
- Polling mode simpler than webhook setup for MVP
- User provides WhatsApp Business credentials during setup

**Implementation**:
- WhatsApp watcher polls MCP server every 60 seconds
- MCP server wraps WhatsApp Cloud API (users configure their own)
- Message IDs tracked to prevent duplicate processing
- Media downloads via MCP server (saves to /Inbox/)

## Phase 1: Design & Data Models

### Data Model Design (data-model.md)

**New Entities for Silver Tier**:

#### 1. WhatsAppMessage (User Story 3)

**Purpose**: Represents incoming WhatsApp Business message

**Fields**:
- `message_id` (string, unique, PK): WhatsApp message ID from API
- `sender_phone` (string): Sender's phone number (E.164 format)
- `sender_name` (string): Sender's contact name (from WhatsApp profile)
- `message_content` (string): Full message text content
- `timestamp` (datetime): Message received timestamp (ISO 8601)
- `media_attachments` (list[dict]): List of media files (image, document, audio)
  - `media_type`: image|document|audio|video
  - `media_url`: URL from WhatsApp API
  - `local_path`: Path in /Inbox/ after download
  - `filename`: Original filename
- `priority` (enum): low|medium|high (based on Company_Handbook.md priority contacts)
- `status` (enum): pending|processed|archived
- `created_at` (datetime): Entity creation time in vault
- `processed_at` (datetime, optional): When plan was generated

**Relationships**:
- Links to ActionPlan (one WhatsApp message → one or more plans)

**Validation Rules**:
- `message_id` must be unique (prevent duplicates)
- `sender_phone` must match E.164 format (+[country][number])
- `timestamp` cannot be in future
- `priority` auto-set based on Company_Handbook.md priority_contacts list

**State Transitions**:
```
pending → processed (when plan generated)
processed → archived (when moved to /Done/)
```

**File Format** (Markdown with YAML frontmatter):
```markdown
---
type: whatsapp
message_id: wamid.abc123xyz
sender_phone: "+923001234567"
sender_name: "John Doe"
timestamp: "2026-02-25T14:30:00Z"
priority: high
status: pending
media_attachments:
  - media_type: image
    media_url: "https://whatsapp-api.../media/123"
    local_path: "/vault/Inbox/whatsapp_image_123.jpg"
    filename: "photo.jpg"
created_at: "2026-02-25T14:30:15Z"
---

## Message Content

Urgent: Need your approval on the proposal by EOD. Please review and let me know.

## Context

Priority contact detected. Flagged as high priority.
```

#### 2. SocialMediaPost (User Story 2)

**Purpose**: Represents social media post plan awaiting approval or execution

**Fields**:
- `post_id` (string, unique, PK): Generated post ID (POST_[platform]_[timestamp])
- `platforms` (list[enum]): [linkedin, facebook, twitter] (multi-platform support)
- `content` (string): Post text content
- `media_attachments` (list[dict], optional): Images/videos for post
  - `media_type`: image|video
  - `local_path`: Path in /Inbox/
  - `filename`: Filename
- `scheduled_time` (datetime, optional): Future posting time (null = immediate)
- `status` (enum): draft|approved|posted|failed|partial
- `platform_results` (dict): Per-platform execution results
  - `linkedin`: {status: success|failed, post_url: "...", post_id: "...", error: null}
  - `facebook`: {status: success|failed, post_url: "...", post_id: "...", error: null}
  - `twitter`: {status: success|failed, post_url: "...", tweet_ids: [...], error: null}
- `created_at` (datetime): Plan creation time
- `approved_at` (datetime, optional): Approval timestamp
- `posted_at` (datetime, optional): Actual posting time
- `error_details` (string, optional): Error message if failed

**Relationships**:
- Created from ActionPlan (plan suggests social post → creates SocialMediaPost entity)
- Links to ExecutionLog (one post → one or more execution attempts)

**Validation Rules**:
- `content` length validated per platform (LinkedIn: 3000 chars, Twitter: 280 chars, Facebook: 63,206 chars)
- If `platforms` includes twitter and `content` > 280 chars, must split into thread
- `scheduled_time` cannot be in past (must be future or null)
- `platform_results` keys must match `platforms` list

**State Transitions**:
```
draft → approved (moved to /Approved/)
approved → posted (all platforms succeed)
approved → partial (some platforms succeed, some fail)
approved → failed (all platforms fail)
posted → archived (moved to /Done/)
```

**File Format** (Markdown with YAML frontmatter):
```markdown
---
type: social_media_post
post_id: POST_linkedin_1708876200
platforms:
  - linkedin
  - twitter
content: "Excited to share our new feature release! 🚀 Check out how we're transforming productivity with AI-powered automation. #AI #Productivity"
media_attachments:
  - media_type: image
    local_path: "/vault/Inbox/feature_screenshot.png"
    filename: "feature_screenshot.png"
scheduled_time: null
status: approved
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
---

## Post Content

Excited to share our new feature release! 🚀 Check out how we're transforming productivity with AI-powered automation. #AI #Productivity

## Execution Summary

- LinkedIn: Posted successfully at 14:17:30
- Twitter: Posted successfully at 14:17:30
- Total reach: 500+ impressions (LinkedIn), 200+ impressions (Twitter)
```

#### 3. ScheduledTask (User Story 4)

**Purpose**: Represents recurring scheduled task definition

**Fields**:
- `task_id` (string, unique, PK): Generated task ID (TASK_[name]_[created])
- `task_name` (string): Human-readable task name (e.g., "daily_briefing")
- `task_type` (enum): briefing|summary|custom
- `schedule_pattern` (string): Cron-like pattern (e.g., "0 9 * * *" = daily at 09:00)
- `recurrence_rule` (dict): Parsed recurrence details
  - `frequency`: daily|weekly|custom
  - `time`: "09:00" (HH:MM format)
  - `day_of_week`: 0-6 (0=Monday, for weekly tasks)
  - `interval`: N (for "every N days" custom tasks)
- `last_execution` (datetime, optional): Last successful run time
- `next_execution` (datetime): Calculated next run time
- `enabled` (boolean): Whether task is active
- `output_path` (string): Where to create output (e.g., "/Needs_Action/")
- `parameters` (dict, optional): Task-specific parameters
  - For briefing: {include_pending: true, include_completed_24h: true}
  - For summary: {period: "week", metrics: ["completed_tasks", "time_saved"]}
- `created_at` (datetime): Task definition creation
- `updated_at` (datetime): Last modification

**Relationships**:
- Outputs create new files in /Needs_Action/ (briefings, summaries)
- Links to ExecutionLog (one task → multiple execution records)

**Validation Rules**:
- `schedule_pattern` must be valid cron syntax
- `next_execution` calculated based on current time + schedule
- `time` format validated as HH:MM (24-hour)
- `day_of_week` must be 0-6 if frequency is weekly

**State Transitions**:
```
enabled=true → scheduler processes → execution → last_execution updated → next_execution calculated
enabled=false → scheduler skips
```

**File Format** (Stored in Company_Handbook.md, not separate files):
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

  - task_id: TASK_weekly_summary_1708876300
    task_name: "weekly_summary"
    task_type: summary
    schedule_pattern: "0 8 * * 1"
    recurrence_rule:
      frequency: weekly
      time: "08:00"
      day_of_week: 1
    last_execution: "2026-02-19T08:00:10Z"
    next_execution: "2026-02-26T08:00:00Z"
    enabled: true
    output_path: "/Needs_Action/"
    parameters:
      period: "week"
      metrics: ["completed_tasks", "time_saved", "emails_sent", "posts_published"]
```

#### 4. ExecutionLog (User Story 1 - Cross-Cutting)

**Purpose**: Audit record for all executed actions

**Fields**:
- `log_id` (string, unique, PK): Generated log ID (LOG_[timestamp]_[action_type])
- `timestamp` (datetime): Execution time (ISO 8601)
- `action_type` (enum): email_send|social_post|whatsapp_detect|scheduled_task
- `actor` (enum): executor|scheduler|whatsapp_watcher
- `plan_id` (string): Reference to plan file that triggered action
- `target` (string): Destination (email address, platform name, etc.)
- `parameters` (dict): Action-specific parameters
  - For email: {recipient, subject, body_preview}
  - For social: {platform, content_preview}
  - For whatsapp: {sender_phone, message_preview}
  - For scheduled: {task_name, output_file}
- `approval_status` (enum): approved|auto_approved|pending
- `approved_by` (enum): human|auto
- `approval_timestamp` (datetime, optional): When approval granted
- `result` (enum): success|failure|partial
- `mcp_server` (string, optional): MCP server URL used
- `response` (dict, optional): MCP server response
  - For email: {message_id, thread_id}
  - For social: {post_url, post_id}
  - For whatsapp: {message_id, media_downloaded}
- `error` (string, optional): Error message if failed
- `duration_ms` (integer): Execution time in milliseconds
- `retry_count` (integer): Number of retry attempts (0 = first attempt)

**Relationships**:
- References ActionPlan via `plan_id`
- References SocialMediaPost, WhatsAppMessage, ScheduledTask via contextual links

**Validation Rules**:
- `timestamp` cannot be in future
- If `result` is failure, `error` must be present
- If `result` is success, `response` should be present
- `duration_ms` must be non-negative

**Storage**: Daily JSON log files in /Logs/YYYY-MM-DD.json (append-only)

**File Format** (JSON lines in daily log):
```json
{
  "log_id": "LOG_1708876800_email_send",
  "timestamp": "2026-02-25T14:20:00Z",
  "action_type": "email_send",
  "actor": "executor",
  "plan_id": "PLAN_email_reply_1708876700.md",
  "target": "client@example.com",
  "parameters": {
    "recipient": "client@example.com",
    "subject": "Re: Proposal Review",
    "body_preview": "Thank you for your feedback. I've updated..."
  },
  "approval_status": "approved",
  "approved_by": "human",
  "approval_timestamp": "2026-02-25T14:15:00Z",
  "result": "success",
  "mcp_server": "gmail_mcp",
  "response": {
    "message_id": "<abc123@mail.gmail.com>",
    "thread_id": "thread_xyz789"
  },
  "error": null,
  "duration_ms": 1234,
  "retry_count": 0
}
```

### API Contracts (contracts/)

**Contract Files Created**:

1. **email-plan-schema.json**: Validation schema for email send plans
2. **social-post-plan-schema.json**: Validation schema for social media post plans
3. **scheduled-task-schema.json**: Validation schema for scheduled task definitions
4. **execution-log-schema.json**: Validation schema for execution log entries

**Example: email-plan-schema.json**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Email Send Plan",
  "description": "Schema for email send plan validation before execution",
  "type": "object",
  "required": ["type", "action", "recipient", "subject", "body"],
  "properties": {
    "type": {
      "type": "string",
      "const": "email_send"
    },
    "action": {
      "type": "string",
      "enum": ["send", "reply", "forward"]
    },
    "recipient": {
      "type": "string",
      "format": "email",
      "description": "Email address of recipient"
    },
    "subject": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500,
      "description": "Email subject line"
    },
    "body": {
      "type": "string",
      "minLength": 1,
      "description": "Email body content"
    },
    "thread_id": {
      "type": "string",
      "description": "Gmail thread ID for replies (optional)"
    },
    "in_reply_to": {
      "type": "string",
      "description": "Message ID being replied to (optional)"
    },
    "attachments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["filename", "path"],
        "properties": {
          "filename": {"type": "string"},
          "path": {"type": "string"},
          "mime_type": {"type": "string"}
        }
      },
      "description": "File attachments (optional)"
    }
  }
}
```

### Quickstart Guide (quickstart.md)

**Purpose**: Developer guide for Silver Tier setup and testing

**Sections**:
1. **Prerequisites**: UV installed, Python 3.12+, Obsidian vault initialized, Bronze Tier working
2. **Installation**: UV sync, MCP server setup, .env configuration
3. **Configuration**: Enable Silver Tier features, configure MCP server URLs, set up scheduled tasks
4. **Testing**:
   - Email send: Create plan in /Needs_Action/, approve, verify sent
   - Social post: Create LinkedIn post plan, approve, verify published
   - WhatsApp: Send test message, verify detected in /Needs_Action/
   - Scheduled task: Configure daily briefing, wait for 09:00, verify generated
5. **Troubleshooting**: Common errors, MCP connection issues, rate limit handling
6. **Monitoring**: PM2 logs, audit logs, dashboard stats

**Example Test Scenario** (from quickstart.md):
```markdown
### Test Scenario 1: Email Reply Execution

1. **Create Email Reply Plan**:
   ```bash
   cat > "$VAULT_PATH/Needs_Action/PLAN_email_test_$(date +%s).md" << 'EOF'
   ---
   type: email_send
   action: reply
   recipient: "test@example.com"
   subject: "Re: Test Email"
   thread_id: "thread_abc123"
   status: pending
   ---

   ## Email Body

   This is a test email reply from Silver Tier executor.

   Thanks!
   EOF
   ```

2. **Approve Plan**:
   ```bash
   mv "$VAULT_PATH/Needs_Action/PLAN_email_test_*.md" "$VAULT_PATH/Approved/"
   ```

3. **Wait for Executor** (monitors /Approved/ every 10 seconds):
   ```bash
   # Watch executor logs
   pm2 logs executor --lines 20
   ```

4. **Verify Execution**:
   - Check Gmail Sent folder for email
   - Plan moved to /Done/ with execution metadata
   - Audit log entry in /Logs/YYYY-MM-DD.json
   - Dashboard updated with "Emails sent today: 1"

5. **Expected Timeline**:
   - Approval → Detection: <10 seconds
   - Detection → Execution: <30 seconds
   - Execution → Gmail API: <60 seconds
   - **Total: <2 minutes (meets SC-001)**
```

## Phase 2: Architecture Decision Records (ADR)

**Significant Architectural Decisions Detected**:

### ADR Candidate 1: MCP Server Integration Architecture

**Decision**: Use MCP protocol for all external integrations (Gmail send, social media, WhatsApp) instead of direct API calls.

**Context**: Silver Tier requires integration with 5 external platforms (Gmail, LinkedIn, Facebook, Twitter, WhatsApp). Each platform has different authentication, rate limits, and error handling.

**Alternatives Considered**:
1. **Direct API Calls**: Use platform SDKs (google-api-python-client, tweepy, etc.)
   - Pros: No intermediary, full control, fewer dependencies
   - Cons: Complex authentication management, tightly coupled, hard to test
2. **MCP Servers** (chosen): Use MCP protocol for all integrations
   - Pros: Decoupled, testable, reusable, standardized error handling
   - Cons: Requires MCP server setup, adds network hop
3. **Hybrid**: MCP for some, direct for others
   - Pros: Flexibility
   - Cons: Inconsistent patterns, maintenance burden

**Decision Rationale**: MCP servers provide clean separation of concerns, easier testing (mock MCP responses), and alignment with constitution principle IV (Agent Skills Architecture). The network overhead is negligible (<50ms per call) and acceptable given other benefits.

**Tradeoffs**:
- Added complexity: Users must configure MCP servers
- Performance: ~50ms additional latency per call (acceptable for non-realtime actions)
- Reliability: Depends on MCP server availability (mitigated by graceful degradation)

📋 **Architectural decision detected**: MCP Server Integration Architecture — Document reasoning and tradeoffs? Run `/sp.adr mcp-integration-architecture`

### ADR Candidate 2: Scheduling Engine Implementation

**Decision**: Use APScheduler with custom JSON-based job store instead of cron or Celery.

**Context**: Silver Tier needs cron-like scheduling for daily briefings, weekly summaries, and custom recurring tasks. Must persist state across restarts and handle missed executions.

**Alternatives Considered**:
1. **System Cron**: Use OS cron jobs
   - Pros: Proven, reliable, no Python dependencies
   - Cons: OS-specific, hard to test, no cross-platform, can't read Company_Handbook.md dynamically
2. **APScheduler** (chosen): Python scheduling library with persistent job store
   - Pros: Cross-platform, cron syntax, persistent state, dynamic configuration
   - Cons: Requires event loop, adds dependency
3. **Celery**: Distributed task queue
   - Pros: Production-grade, many features
   - Cons: Requires Redis/RabbitMQ, overkill for single-user system

**Decision Rationale**: APScheduler provides the right balance of features and simplicity. JSON-based job store aligns with local-first principle (no Redis needed). Dynamic configuration from Company_Handbook.md enables user customization without code changes.

**Tradeoffs**:
- Added dependency: APScheduler (acceptable, well-maintained)
- Event loop: Requires asyncio management (mitigated by simple scheduler.py main loop)
- File-based state: JSON writes on every execution (acceptable, <1KB files)

📋 **Architectural decision detected**: Scheduling Engine Implementation — Document reasoning and tradeoffs? Run `/sp.adr scheduling-engine-apscheduler`

### ADR Candidate 3: Rate Limiting Strategy

**Decision**: Implement token bucket rate limiter with persistent JSON state per platform.

**Context**: Must respect API rate limits (Gmail: 500/day, LinkedIn: 100/day, Twitter: 2400/day, Facebook: 200/day) to avoid quota exhaustion and API bans.

**Alternatives Considered**:
1. **No Rate Limiting**: Trust user to not exceed limits
   - Pros: Simple, no overhead
   - Cons: Easy to hit quota, hard to debug, no protection
2. **Fixed Window**: Count actions per day, reset at midnight
   - Pros: Simple implementation
   - Cons: Allows burst at window boundary (send 500 emails at 23:59, 500 at 00:01)
3. **Token Bucket** (chosen): Tokens refill over time, allows short bursts
   - Pros: Prevents long-term exhaustion, allows short bursts, smooth rate
   - Cons: Requires state persistence, more complex

**Decision Rationale**: Token bucket best matches platform behavior and user expectations. Allows sending 5 emails quickly if needed, but prevents exhausting daily quota. Persistent state ensures limits survive restarts.

**Tradeoffs**:
- Complexity: Requires token calculation, refill rate management
- State management: JSON file writes on every action (acceptable overhead)
- User experience: May delay actions if quota low (acceptable, prevents API ban)

📋 **Architectural decision detected**: Rate Limiting Strategy — Document reasoning and tradeoffs? Run `/sp.adr rate-limiting-token-bucket`

## Implementation Strategy

### Incremental Delivery Plan

**Phase 0**: Setup & Infrastructure (1-2 hours)
- UV dependency updates (mcp, apscheduler, requests, jsonschema)
- MCP client library skeleton (mcp_client.py)
- Executor and scheduler main scripts (empty shells)
- PM2 ecosystem.config.js updates

**Phase 1**: Email Sending & HITL Execution - US1 (6-8 hours)
- Executor service implementation
- Gmail MCP integration
- /Approved/ folder monitoring
- Email send execution
- Error handling and retry logic
- Rate limiting for Gmail
- Audit logging for email sends
- Dashboard updates for sent emails
- **Testing**: Send 5 test emails, verify all succeed, check audit logs

**Phase 2**: Social Media Auto-Posting - US2 (6-8 hours)
- Social media service implementation
- LinkedIn, Facebook, Twitter MCP integrations
- Multi-platform posting logic
- Twitter thread handling
- Scheduled post support
- Platform-specific validation (character limits)
- Rate limiting per platform
- **Testing**: Post to LinkedIn, verify URL captured. Post to Twitter thread (3 tweets), verify chain.

**Phase 3**: WhatsApp Business Monitoring - US3 (3-4 hours)
- WhatsApp watcher implementation
- WhatsApp MCP integration
- Message polling (every 60 seconds)
- Priority contact detection
- Media download handling
- Duplicate prevention
- **Testing**: Send test WhatsApp, verify entity in /Needs_Action/ within 2 minutes

**Phase 4**: Scheduled Tasks & Daily Briefings - US4 (4-6 hours)
- Scheduler service implementation
- APScheduler integration
- Company_Handbook.md parser for task definitions
- Daily briefing generation
- Weekly summary generation
- Missed execution handling
- State persistence
- **Testing**: Configure daily briefing at current time + 2 minutes, verify generated

**Total Estimated Time**: 20-28 hours (within 20-30 hour estimate from spec)

### Risk Mitigation

**Risk 1**: MCP server unavailability during testing
- **Mitigation**: Implement MCP mock server for integration tests, graceful degradation in production

**Risk 2**: Rate limit complexity causing delays
- **Mitigation**: Start with conservative limits (Gmail: 1 email per 10 seconds), tune based on testing

**Risk 3**: WhatsApp Business API setup complexity
- **Mitigation**: Provide detailed MCP server configuration guide, make WhatsApp optional (like Gmail in Bronze)

**Risk 4**: APScheduler state corruption
- **Mitigation**: Atomic JSON writes, backup schedule state on startup, graceful fallback to defaults

**Risk 5**: Multi-platform social posting partial failures
- **Mitigation**: Per-platform status tracking, allow retry of failed platforms only

## Success Criteria Mapping

**User Story 1 (P1) - Email Sending**:
- SC-001: Executor detects approval within 10s (watchdog), sends within 2 min total ✓
- SC-002: 95% success rate (retry logic for transient errors) ✓
- SC-003: Failed sends move to /Needs_Action/ within 60s (error handler) ✓
- SC-004: Sequential processing with rate limiting ✓
- SC-005: Gmail threading preserved (thread_id in plan) ✓

**User Story 2 (P2) - Social Media**:
- SC-006: Multi-platform posting within 3 min (parallel MCP calls) ✓
- SC-007: Per-platform status tracking (platform_results dict) ✓
- SC-008: Twitter thread continuity (sequential posting with reply-to) ✓
- SC-009: Post URLs captured from MCP response ✓
- SC-010: Duplicate detection (check last 50 posts before posting) ✓

**User Story 3 (P3) - WhatsApp**:
- SC-011: Polling every 60s, entity created within 2 min ✓
- SC-012: Priority detection from Company_Handbook.md ✓
- SC-013: Media download via MCP server ✓
- SC-014: Duplicate prevention via message_id tracking ✓

**User Story 4 (P4) - Scheduled Tasks**:
- SC-015: Scheduler checks every 10s, executes within 5 min window ✓
- SC-016: Weekly summary calculates metrics from audit logs ✓
- SC-017: APScheduler ensures 95% punctuality ✓
- SC-018: Missed execution catch-up within 1-hour grace period ✓

**System-Wide**:
- SC-019: Dashboard updates from audit logs every 60s ✓
- SC-020: Bronze Tier unchanged, runs alongside Silver ✓
- SC-021: MCP graceful degradation (per-server error handling) ✓
- SC-022: State persistence enables crash recovery ✓
- SC-023: ExecutionLog provides full traceability ✓
- SC-024: Audit logs human-readable JSON ✓

## Next Steps

**Immediate**:
1. Review this implementation plan for completeness
2. Run `/sp.tasks` to generate dependency-ordered task list
3. Begin Phase 0 (setup & infrastructure)

**Post-Planning**:
1. Update agent context with new technology (APScheduler, MCP SDK)
2. Create ADRs for 3 significant decisions (MCP integration, scheduling engine, rate limiting)
3. Set up MCP server configuration documentation
4. Initialize integration test infrastructure with MCP mocks

**Before Implementation**:
1. Validate MCP server availability (Gmail, LinkedIn, Facebook, Twitter, WhatsApp)
2. Obtain OAuth credentials for each platform
3. Configure .env with MCP server URLs
4. Review Bronze Tier to ensure compatibility

---

**Plan Status**: ✅ **COMPLETE**

**Constitution Check (Re-validation)**: ✅ **PASSED** (all 6 applicable principles compliant)

**Ready for**: `/sp.tasks` command to generate implementation tasks
