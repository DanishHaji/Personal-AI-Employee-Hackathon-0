# Feature Specification: Silver Tier - Autonomous Task Execution & Multi-Channel Communication

**Feature Branch**: `002-silver-tier-upgrade`
**Created**: 2026-02-25
**Status**: Draft
**Input**: User description: "Upgrade to Silver Tier with following features building on Bronze foundation: Email Sending & Replying, WhatsApp Business Monitoring, Social Media Auto-Posting (LinkedIn, Facebook, Twitter), HITL Approval Workflow Execution, Scheduled Tasks & Automation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Email Reply & HITL Execution Engine (Priority: P1)

The AI Employee can send and reply to emails automatically once plans are approved, transforming from a passive observer to an active participant in email communication. Users approve email drafts in the Obsidian vault, and the system executes them autonomously.

**Why this priority**: This is the core differentiator for Silver Tier - moving from "monitoring" (Bronze) to "acting" (Silver). Email is the primary business communication channel, so automating responses delivers immediate time savings.

**Independent Test**: Can be fully tested by: (1) Creating a plan to reply to an email, (2) Moving it to /Approved/ folder, (3) System automatically sends the email via Gmail API, (4) Verifying sent email in Gmail Sent folder and updating dashboard.

**Acceptance Scenarios**:

1. **Given** a plan file in /Needs_Action/ with type "email_reply", **When** user moves it to /Approved/, **Then** system detects approval, executes email send via Gmail API, moves plan to /Done/, and updates dashboard with execution timestamp
2. **Given** an approved plan with email reply action, **When** Gmail API returns success, **Then** system logs successful send to audit log, attaches sent message ID to plan metadata, and archives in /Done/
3. **Given** an approved plan with email reply action, **When** Gmail API returns error (rate limit, network failure, auth issue), **Then** system moves plan back to /Needs_Action/, creates alert file in /Inbox/ with error details, and updates dashboard with failure status
4. **Given** multiple approved plans in /Approved/, **When** executor runs, **Then** system processes plans in chronological order (oldest first), respects rate limits (1 email per 5 seconds), and logs all executions
5. **Given** an email reply plan, **When** original email no longer exists (deleted/archived), **Then** system marks plan as "cannot execute", moves to /Quarantine/, and logs reason

---

### User Story 2 - Social Media Auto-Posting (Priority: P2)

The AI Employee can automatically post approved content to LinkedIn, Facebook, and Twitter/X on behalf of the user, managing multi-platform social media presence from a single Obsidian vault.

**Why this priority**: Social media management is time-consuming and requires consistency. Automating posts across three major platforms (LinkedIn, Facebook, Twitter) provides significant leverage for personal branding and business marketing.

**Independent Test**: Can be fully tested by: (1) Creating a social media post plan in /Needs_Action/ with platform and content, (2) Approving it, (3) System posts to specified platform(s) via MCP servers, (4) Verifying post appears on social media and plan moves to /Done/.

**Acceptance Scenarios**:

1. **Given** an approved LinkedIn post plan, **When** executor processes it, **Then** system posts content to LinkedIn via MCP server, captures post URL, updates plan with post link, moves to /Done/, and updates dashboard
2. **Given** an approved Facebook post plan with page target, **When** executor processes it, **Then** system posts to specified Facebook page, captures post ID, and logs success
3. **Given** an approved Twitter thread plan (array of tweets), **When** executor processes it, **Then** system posts tweets sequentially as a thread, maintains thread continuity, and captures all tweet IDs
4. **Given** a multi-platform post plan (LinkedIn + Twitter + Facebook), **When** executor processes it, **Then** system posts to all platforms sequentially, logs each platform result separately, and only marks complete when all succeed
5. **Given** a scheduled post plan with future timestamp, **When** executor runs before scheduled time, **Then** system skips the plan and re-checks on next execution cycle
6. **Given** a post plan, **When** platform API returns error (authentication, rate limit, content policy), **Then** system moves plan back to /Needs_Action/, creates detailed alert with platform-specific error, and marks platform as failed

---

### User Story 3 - WhatsApp Business Monitoring (Priority: P3)

The AI Employee monitors WhatsApp Business API for incoming messages and creates action items in the vault, extending monitoring capabilities beyond email to instant messaging.

**Why this priority**: WhatsApp is increasingly used for business communication, especially for customer support and quick queries. Monitoring it alongside email provides comprehensive message coverage.

**Independent Test**: Can be fully tested by: (1) Sending a test WhatsApp message to connected business number, (2) System detects message via MCP server, (3) Creates entity in /Needs_Action/ with message content, (4) Dashboard shows new WhatsApp item.

**Acceptance Scenarios**:

1. **Given** a new WhatsApp message arrives, **When** WhatsApp watcher polls API, **Then** system creates WHATSAPP_[id].md entity in /Needs_Action/ with sender, message content, timestamp, and metadata
2. **Given** a WhatsApp message from priority contact (defined in Company_Handbook.md), **When** processing message, **Then** system marks as high priority, triggers immediate plan generation, and adds priority indicator to dashboard
3. **Given** a WhatsApp message with media (image, document), **When** processing message, **Then** system downloads media file, saves to /Inbox/, and links in message entity metadata
4. **Given** duplicate WhatsApp message (same message ID), **When** watcher encounters it, **Then** system skips processing, logs duplicate detection, and does not create new entity
5. **Given** WhatsApp API is unreachable, **When** watcher tries to poll, **Then** system logs connection error, retries with exponential backoff (5s, 30s, 2m), and creates alert if down for >10 minutes

---

### User Story 4 - Scheduled Tasks & Daily Briefings (Priority: P4)

The AI Employee executes time-based tasks automatically, such as generating daily briefings at 9 AM or weekly summaries every Monday, providing proactive value without user intervention.

**Why this priority**: Scheduled automation transforms the AI from reactive to proactive. Daily briefings and recurring tasks provide consistent value and reduce cognitive load on the user.

**Independent Test**: Can be fully tested by: (1) Creating a scheduled task (e.g., "daily briefing at 09:00"), (2) System checks schedule on each cycle, (3) At 09:00, generates briefing in /Needs_Action/, (4) Briefing contains summary of pending items, recent completions, and upcoming tasks.

**Acceptance Scenarios**:

1. **Given** a scheduled task "daily_briefing" set for 09:00, **When** scheduler runs at 09:00, **Then** system generates briefing document with pending item count, recent completions (last 24h), urgent items, and saves to /Needs_Action/
2. **Given** a scheduled task "weekly_summary" set for Monday 08:00, **When** scheduler runs on Monday at 08:00, **Then** system generates weekly summary with completed tasks, time saved metrics, and upcoming priorities
3. **Given** a scheduled task with custom recurrence (every 3 days at 14:00), **When** scheduler calculates next run, **Then** system correctly schedules 3 days from last execution and runs at 14:00
4. **Given** multiple scheduled tasks with same time, **When** scheduler runs, **Then** system executes all tasks in definition order and logs each completion
5. **Given** a scheduled task execution fails (e.g., briefing generation error), **When** error occurs, **Then** system logs failure, creates alert in /Inbox/, and retries next scheduled time (does not block future executions)
6. **Given** scheduled task definitions in Company_Handbook.md, **When** user updates schedule (changes time or recurrence), **Then** system detects change on next cycle and updates internal schedule without restart

---

### Edge Cases

**Email Sending & HITL Execution**:
- What happens when approved plan references a non-existent email thread? → Move to /Quarantine/ with "original context lost" reason
- How does system handle Gmail quota exceeded (500 emails/day limit)? → Pause execution, create alert, resume next day automatically
- What if user revokes Gmail OAuth token while execution is running? → Detect auth error, pause all email executions, create urgent alert requesting re-authentication
- How to handle plans approved while system is offline? → Queue all approved plans on startup, process in chronological order with rate limiting

**Social Media Auto-Posting**:
- What happens when post content exceeds platform character limit? → Detect before posting, move back to /Needs_Action/ with truncation warning, suggest splitting into thread
- How does system handle duplicate posts (same content posted recently)? → Check last 50 posts, warn if exact duplicate, allow user to confirm or cancel
- What if media file referenced in post is missing? → Move plan to /Needs_Action/ with "media not found" error, list expected file path
- How to handle partial failure (LinkedIn succeeds, Twitter fails)? → Log partial success, move to /Needs_Action/ with platform-specific status, allow retry of failed platforms only

**WhatsApp Monitoring**:
- What happens when WhatsApp Business API subscription expires? → Detect API error, disable watcher gracefully, create alert with renewal instructions
- How does system handle high message volume (>100 messages/hour)? → Process all messages, batch into summary entities if >50/hour to avoid dashboard clutter
- What if message language is not English? → Detect language, preserve original content, add language tag to metadata for context

**Scheduled Tasks**:
- What happens when system is offline during scheduled time? → Execute missed task on next startup if within 1-hour window, otherwise skip and log missed execution
- How does system handle daylight saving time changes? → Store schedules in UTC, convert to local time for execution, adjust for DST automatically
- What if briefing generation takes longer than schedule interval? → Skip next execution if previous still running, log overlap warning, increase interval if happens frequently

**Cross-Cutting Concerns**:
- How does system handle concurrent approval of multiple plans? → Process sequentially using file system locks, maintain queue, prevent race conditions
- What happens when vault becomes full (disk space)? → Monitor disk usage, create alert at 90% full, auto-archive /Done/ items older than 90 days to compressed archive
- How to handle MCP server connection failures? → Retry with exponential backoff, fall back to disabled mode for that integration, continue other operations
- What if execution takes longer than orchestrator cycle (60s)? → Allow execution to complete, skip next cycle, log slow execution warning, suggest increasing cycle time

## Requirements *(mandatory)*

### Functional Requirements

**Email Sending & HITL Execution (P1)**:
- **FR-001**: System MUST detect plans moved to /Approved/ folder within 60 seconds of file modification
- **FR-002**: System MUST execute approved email reply plans by sending via Gmail API with sender authentication
- **FR-003**: System MUST capture sent message ID and timestamp from Gmail API response
- **FR-004**: System MUST move successfully executed plans from /Approved/ to /Done/ with execution metadata
- **FR-005**: System MUST handle Gmail API errors gracefully by moving failed plans back to /Needs_Action/ with error details
- **FR-006**: System MUST respect Gmail API rate limits (1 email per 5 seconds minimum)
- **FR-007**: System MUST log all email send attempts to audit log with plan ID, recipient, subject, status, and timestamp
- **FR-008**: System MUST validate email plans before execution (recipient exists, subject non-empty, body present)
- **FR-009**: System MUST support email replies (in-reply-to header), new emails, and forwards
- **FR-010**: System MUST update dashboard statistics with sent email count and last execution time

**Social Media Auto-Posting (P2)**:
- **FR-011**: System MUST connect to LinkedIn via MCP server for authenticated posting
- **FR-012**: System MUST connect to Facebook via MCP server for page/group posting
- **FR-013**: System MUST connect to Twitter/X via MCP server for tweet and thread posting
- **FR-014**: System MUST support text-only posts for all platforms
- **FR-015**: System MUST support image attachments for LinkedIn, Facebook, and Twitter posts
- **FR-016**: System MUST support link previews in social media posts
- **FR-017**: System MUST validate post content against platform limits (LinkedIn: 3000 chars, Twitter: 280 chars, Facebook: 63,206 chars)
- **FR-018**: System MUST support Twitter threads by posting tweets sequentially with thread continuity
- **FR-019**: System MUST capture post URLs/IDs from platform responses and store in plan metadata
- **FR-020**: System MUST support multi-platform posting (single plan posts to multiple platforms)
- **FR-021**: System MUST support scheduled posts with future timestamp execution
- **FR-022**: System MUST log all social media post attempts with platform, content preview, status, and post URL

**WhatsApp Business Monitoring (P3)**:
- **FR-023**: System MUST poll WhatsApp Business API every 60 seconds for new messages
- **FR-024**: System MUST create WHATSAPP_[message_id].md entity for each new message in /Needs_Action/
- **FR-025**: System MUST extract sender name, phone number, message content, and timestamp from API response
- **FR-026**: System MUST detect priority contacts defined in Company_Handbook.md and mark messages as high priority
- **FR-027**: System MUST download media attachments (images, documents, audio) to /Inbox/ and link in message entity
- **FR-028**: System MUST prevent duplicate processing by tracking message IDs
- **FR-029**: System MUST handle WhatsApp API authentication using stored credentials
- **FR-030**: System MUST log all WhatsApp message retrievals to audit log

**Scheduled Tasks & Daily Briefings (P4)**:
- **FR-031**: System MUST support scheduled task definitions in Company_Handbook.md with time and recurrence pattern
- **FR-032**: System MUST execute scheduled tasks at specified time (within 60-second window)
- **FR-033**: System MUST support daily, weekly, and custom recurrence patterns (e.g., every N days)
- **FR-034**: System MUST generate daily briefing with pending item count, recent completions (24h), and urgent items
- **FR-035**: System MUST generate weekly summary with completed task count, time saved estimate, and upcoming priorities
- **FR-036**: System MUST store schedule state persistently to track last execution and calculate next run
- **FR-037**: System MUST handle missed executions (system offline during scheduled time) by executing on next startup if within 1-hour grace period
- **FR-038**: System MUST log all scheduled task executions with task name, execution time, status, and output location

**Cross-Cutting Requirements**:
- **FR-039**: System MUST use MCP servers for all external integrations (Gmail send, social media, WhatsApp)
- **FR-040**: System MUST maintain Bronze Tier capabilities (email monitoring, file drop, vault management) while adding Silver features
- **FR-041**: System MUST store all credentials and tokens outside vault in .env file or secure storage
- **FR-042**: System MUST validate all plans before execution against schema defined in plan template
- **FR-043**: System MUST support graceful degradation (if one integration fails, others continue working)
- **FR-044**: System MUST update dashboard with real-time execution statistics (emails sent, posts published, tasks completed)
- **FR-045**: System MUST create execution summary in plan metadata including timestamps, API responses, and links to sent/posted content

### Key Entities

**Existing Entities (from Bronze Tier)**:
- **Email**: Incoming email entity with sender, subject, body, priority, and status (Bronze Tier - read-only)
- **FileDrop**: Dropped file entity with file path, metadata, and processing status (Bronze Tier)
- **ActionPlan**: Generated plan with actions, dependencies, and approval status (Bronze Tier)

**New Entities (Silver Tier)**:
- **WhatsAppMessage**: WhatsApp message entity with sender phone, sender name, message content, timestamp, media attachments, priority flag, message ID, and processing status
- **SocialMediaPost**: Social media post entity with platform (LinkedIn/Facebook/Twitter), content, media attachments, scheduled time, post URL/ID, execution status, and error details
- **ScheduledTask**: Scheduled task definition with task name, schedule pattern (cron-like), last execution time, next execution time, recurrence rule, and enabled flag
- **ExecutionLog**: Execution record for approved plans with plan ID, execution type (email/social/whatsapp/task), execution time, status (success/failure/partial), API response, error details, and result metadata

### Assumptions

1. **MCP Server Availability**: We assume MCP servers for Gmail (send), LinkedIn, Facebook, Twitter/X, and WhatsApp Business API are available and properly configured. If a server is unavailable, that integration will be disabled gracefully while others continue working.

2. **OAuth Credentials**: We assume users will provide OAuth credentials for Gmail, LinkedIn, Facebook, and Twitter via standard OAuth flows. Gmail credentials can be added later (currently optional as per Bronze Tier setup).

3. **WhatsApp Business API Access**: We assume users have WhatsApp Business API access (not regular WhatsApp) with valid API credentials. The free WhatsApp Web API is not supported for business automation.

4. **Rate Limits**: We assume standard API rate limits: Gmail (500 emails/day), LinkedIn (100 posts/day), Twitter (2400 tweets/day), Facebook (200 posts/day), WhatsApp (1000 messages/day inbound). System will respect these limits.

5. **Approval Workflow**: We assume users will review and approve plans manually by moving files from /Needs_Action/ to /Approved/. The system will not auto-approve any outbound actions (email sends, posts, replies).

6. **Vault Availability**: We assume the Obsidian vault is always accessible (local file system or synced drive). If vault becomes temporarily unavailable, system will queue operations and retry.

7. **Time Zone**: We assume all scheduled tasks use system local time. Users can specify UTC times by prefixing with "UTC:" in schedule definitions.

8. **Content Moderation**: We assume users are responsible for content compliance with platform policies. The system will not perform content moderation or policy checks beyond basic validation (character limits, required fields).

9. **Single User**: Silver Tier assumes single-user operation (one Gmail account, one set of social media accounts, one WhatsApp Business number). Multi-user support is deferred to Gold/Platinum tiers.

10. **MCP Server Security**: We assume MCP servers are trusted and secure. The system will not validate or sandbox MCP server responses beyond basic error handling.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Email Sending & HITL Execution (P1)**:
- **SC-001**: Users can approve email reply plans and system sends them via Gmail API within 2 minutes of approval
- **SC-002**: System successfully sends 95% of approved email plans on first attempt (5% failure rate acceptable for transient network/API issues)
- **SC-003**: Failed email sends are moved back to /Needs_Action/ with clear error messages within 60 seconds of failure
- **SC-004**: System processes multiple approved plans (5+ emails) sequentially without manual intervention
- **SC-005**: All sent emails appear in Gmail Sent folder with correct threading and metadata

**Social Media Auto-Posting (P2)**:
- **SC-006**: Users can approve social media posts and system publishes to LinkedIn, Facebook, or Twitter within 3 minutes
- **SC-007**: System supports multi-platform posting (single approval publishes to 2+ platforms) with per-platform status tracking
- **SC-008**: Twitter threads maintain correct reply chain structure with all tweets linked
- **SC-009**: Posted content URLs are captured and visible in plan metadata and dashboard within 1 minute of posting
- **SC-010**: System detects and prevents duplicate posts (same content within 7 days) with 100% accuracy

**WhatsApp Business Monitoring (P3)**:
- **SC-011**: New WhatsApp messages appear in /Needs_Action/ folder within 2 minutes of receipt
- **SC-012**: Priority contact messages are marked with high priority flag within 60 seconds
- **SC-013**: Media attachments (images, documents) are downloaded and linked correctly in 90% of messages containing media
- **SC-014**: System handles 100+ WhatsApp messages per day without message loss or duplicate processing

**Scheduled Tasks & Daily Briefings (P4)**:
- **SC-015**: Daily briefings are generated within 5 minutes of scheduled time (09:00 ± 5 minutes)
- **SC-016**: Weekly summaries accurately count completed tasks and calculate time saved metrics
- **SC-017**: Custom scheduled tasks execute at specified times with 95% punctuality (within 60-second window)
- **SC-018**: Missed executions (system offline during scheduled time) are caught up within 1-hour grace period

**System-Wide (Cross-Cutting)**:
- **SC-019**: Dashboard updates reflect execution status changes within 60 seconds (emails sent, posts published, tasks completed)
- **SC-020**: System maintains Bronze Tier functionality (email monitoring, file drop) while executing Silver Tier actions simultaneously
- **SC-021**: MCP server connection failures are handled gracefully with automatic retry and clear error alerts
- **SC-022**: System recovers from crashes and resumes operations within 2 minutes without data loss
- **SC-023**: All executions are logged to audit log with complete traceability (plan → approval → execution → result)
- **SC-024**: Users can review execution history for any plan by reading plan metadata and audit logs

## Out of Scope *(optional)*

The following features are explicitly **not** included in Silver Tier and are deferred to future tiers:

1. **Multi-User Support**: Silver Tier supports single-user operation only. Multi-user collaboration, role-based permissions, and team workflows are deferred to Gold Tier.

2. **Advanced AI Capabilities**: Autonomous decision-making (auto-approval based on confidence), sentiment analysis for emails/WhatsApp, and intelligent content generation for social posts are deferred to Gold/Platinum Tiers. Silver Tier requires manual approval for all outbound actions.

3. **Calendar Integration**: Meeting scheduling, calendar event creation, and appointment management via Google Calendar or Outlook are not included. This may be added in Gold Tier.

4. **Voice/Phone Integration**: Phone call monitoring, voicemail transcription, and voice command support are out of scope for Silver Tier.

5. **Advanced Analytics**: Detailed time tracking, productivity metrics, AI performance dashboards, and ROI calculations are deferred to Platinum Tier.

6. **Mobile App**: Native mobile applications (iOS/Android) for on-the-go approval and monitoring are not included. Silver Tier relies on Obsidian desktop/mobile for vault access.

7. **Custom Workflows**: Visual workflow builder, conditional logic (if-then rules), and custom automation scripts are deferred to Gold Tier. Silver Tier uses predefined workflows only.

8. **Third-Party SaaS Integrations**: Integrations with project management tools (Asana, Jira), CRM systems (Salesforce), or communication platforms (Slack, Discord) are not included beyond the specified platforms (Gmail, WhatsApp, LinkedIn, Facebook, Twitter).

9. **Content Moderation**: Automated content policy checking, brand safety verification, and compliance scanning for social posts are out of scope. Users are responsible for content compliance.

10. **Rollback/Undo**: The ability to unsend emails, delete posts, or recall WhatsApp messages after execution is not supported. All executions are final.

## Dependencies *(optional)*

### External Dependencies

1. **MCP Servers (Critical)**:
   - **Gmail MCP Server**: Required for email sending (FR-002). Must support OAuth2 authentication and Gmail API v1 send endpoint.
   - **LinkedIn MCP Server**: Required for LinkedIn posting (FR-011). Must support OAuth2 and LinkedIn Share API.
   - **Facebook MCP Server**: Required for Facebook posting (FR-012). Must support Facebook Graph API with pages_manage_posts permission.
   - **Twitter/X MCP Server**: Required for Twitter posting (FR-013). Must support Twitter API v2 with write permissions.
   - **WhatsApp Business MCP Server**: Required for WhatsApp monitoring (FR-023). Must support WhatsApp Business API webhook or polling.

2. **OAuth Credentials**:
   - **Gmail OAuth**: Client ID, client secret, and user consent for send scope (https://www.googleapis.com/auth/gmail.send)
   - **LinkedIn OAuth**: App ID, app secret, and user authorization for share scope (w_member_social)
   - **Facebook OAuth**: App ID, app secret, page access token with pages_manage_posts and pages_read_engagement
   - **Twitter OAuth**: API key, API secret, access token, access token secret with read/write permissions
   - **WhatsApp Business**: Business account ID, phone number ID, access token

3. **Bronze Tier Foundation**:
   - All Silver Tier features build on Bronze Tier infrastructure (vault structure, models, services, watchers, orchestrator)
   - Bronze Tier must be fully functional before Silver Tier implementation begins
   - Dependencies: VaultService, AuditLogger, Email/FileDrop models, gmail_watcher.py, filesystem_watcher.py, orchestrator.py

### Internal Dependencies

1. **Execution Engine**: New component (executor.py) that monitors /Approved/ folder and executes plans. Depends on VaultService, AuditLogger, and MCP servers.

2. **Scheduling Engine**: New component (scheduler.py) that manages scheduled tasks. Depends on VaultService for reading Company_Handbook.md and creating briefing documents.

3. **MCP Client Library**: Common client for communicating with MCP servers. Provides authentication, request/response handling, and error management.

4. **Plan Validation**: Schema validation for execution plans. Ensures plans have required fields (action type, target, content) before execution.

5. **State Management**: Persistent storage for execution state (last run times, pending queue, retry state). Uses JSON files in vault Logs/ folder.

## Technical Constraints *(optional)*

1. **Local-First Architecture**: All data must be stored locally in the Obsidian vault. No cloud databases or external storage beyond API calls to configured services.

2. **UV Package Manager**: All Python dependencies must be managed via UV (not pip). New dependencies added to pyproject.toml must be UV-compatible.

3. **No Database**: System must not use SQLite, PostgreSQL, or any database. All data storage uses Markdown files with YAML frontmatter and JSON logs.

4. **File-Based State**: System state (schedules, execution logs, queue) must be persisted in files, not in-memory only. This ensures crash recovery.

5. **PM2 Process Management**: All background processes (watchers, executor, scheduler, orchestrator) must be manageable via PM2 (start, stop, restart, logs).

6. **MCP Protocol**: All external integrations must use MCP servers. Direct API calls to Gmail, social media platforms, or WhatsApp are not allowed (except for Bronze Tier Gmail monitoring which predates MCP requirement).

7. **OAuth2 Only**: All authentication to external services must use OAuth2. Username/password or API keys stored in plaintext are not acceptable (except for MCP server access tokens which may use bearer tokens).

8. **Rate Limiting**: System must respect all API rate limits. Exceeding rate limits should result in automatic backoff, not retries that compound the problem.

9. **Python 3.12+**: Code must be compatible with Python 3.12 or higher. Python 3.13+ is recommended but not required based on Bronze Tier validation.

10. **Cross-Platform**: Code must work on Windows (WSL), macOS, and Linux. File paths must use pathlib for cross-platform compatibility.

## Related Work *(optional)*

### Existing Systems

1. **Zapier/Make**: Commercial automation platforms that connect apps and automate workflows. Silver Tier differs by being local-first, Obsidian-integrated, and requiring manual approval (HITL) for all outbound actions.

2. **IFTTT (If This Then That)**: Consumer automation service for simple triggers and actions. Silver Tier provides more sophisticated plan-based execution with approval workflows.

3. **n8n**: Open-source workflow automation. Similar MCP-based architecture, but Silver Tier is designed specifically for personal AI employee use case with Obsidian as the central hub.

4. **Huginn**: Self-hosted agent system for monitoring and automation. Silver Tier builds on similar concepts but integrates tightly with Claude Code and Obsidian.

### Prior Art from Bronze Tier

- **Gmail Monitoring**: Bronze Tier established Gmail API polling for inbound emails. Silver Tier extends this with send capability.
- **Vault Structure**: Bronze Tier defined /Inbox/, /Needs_Action/, /Approved/, /Done/ workflow. Silver Tier adds execution logic to this structure.
- **Audit Logging**: Bronze Tier created audit log format. Silver Tier extends with execution logs.
- **Company Handbook**: Bronze Tier introduced customizable rules. Silver Tier adds scheduled task definitions to this file.

### Innovation in Silver Tier

1. **Approval-First Execution**: Unlike most automation tools that trigger automatically, Silver Tier requires explicit manual approval by moving files to /Approved/ folder. This provides safety and control.

2. **Multi-Channel Unified Interface**: Managing email, WhatsApp, and social media through a single Obsidian vault interface is unique compared to platform-specific tools.

3. **MCP-Based Extensibility**: Using MCP servers for all integrations provides clean separation of concerns and easy addition of new platforms without core code changes.

4. **Local-First with Cloud Actions**: Data and state remain local (Obsidian vault) while actions execute in cloud services (Gmail, social media). Balances privacy with functionality.
