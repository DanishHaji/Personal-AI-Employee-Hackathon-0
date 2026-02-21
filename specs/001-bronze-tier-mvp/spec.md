# Feature Specification: Bronze Tier MVP - Personal AI Employee

**Feature Branch**: `001-bronze-tier-mvp`
**Created**: 2026-02-21
**Status**: Draft
**Input**: User description: "Bronze Tier MVP: Obsidian vault setup with Gmail watcher, basic folder structure, and Claude Code integration for autonomous email triage"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Email Triage and Inbox Visibility (Priority: P1)

As a busy professional, I receive dozens of emails daily and need to quickly identify which ones require my immediate attention. The AI Employee should monitor my Gmail inbox, identify important/urgent messages, and surface them in my personal dashboard where I can review them at a glance.

**Why this priority**: This is the core value proposition of the Bronze Tier. Email overload is the primary pain point for most professionals. Automating triage immediately delivers measurable time savings.

**Independent Test**: Can be fully tested by sending test emails (marked important/urgent) to the Gmail account and verifying they appear in the Obsidian vault Dashboard.md within 2 minutes. Delivers immediate value by showing which emails need attention without opening Gmail.

**Acceptance Scenarios**:

1. **Given** Gmail Watcher is running and monitoring my inbox, **When** an important email arrives from a client, **Then** the email summary appears in `/Needs_Action/EMAIL_[id].md` within 2 minutes
2. **Given** multiple emails arrive simultaneously (5+ emails), **When** the Gmail Watcher detects them, **Then** all emails are captured and prioritized (important first, then by timestamp)
3. **Given** an email arrives that is NOT marked important and is from an unknown sender, **When** the Watcher filters emails, **Then** it is logged but not added to `/Needs_Action/` (avoids spam/noise)
4. **Given** Dashboard.md exists, **When** new emails are added to `/Needs_Action/`, **Then** Dashboard.md shows a count of pending emails requiring review

---

### User Story 2 - Manual File Drop for AI Processing (Priority: P2)

As a user, I sometimes receive documents or files via other channels (Slack, WhatsApp, downloads) that I want my AI Employee to process. I should be able to drop these files into a designated folder and have them automatically queued for review.

**Why this priority**: This extends the AI Employee's utility beyond just email. It provides a simple, universal input mechanism for any content that needs AI attention.

**Independent Test**: Drop a PDF file into the `/Inbox/` folder and verify it appears in `/Needs_Action/` with metadata within 30 seconds. Delivers value by creating a single "catch-all" inbox for all work items.

**Acceptance Scenarios**:

1. **Given** File System Watcher is monitoring `/Inbox/` folder, **When** I drop a PDF document into `/Inbox/`, **Then** the file is copied to `/Needs_Action/` with a metadata .md file containing filename, size, and timestamp within 30 seconds
2. **Given** I drop an unsupported file type (e.g., .exe, .dmg), **When** the Watcher detects it, **Then** the file is moved to `/Quarantine/` and an alert is logged (security measure)
3. **Given** multiple files are dropped simultaneously, **When** the Watcher processes them, **Then** all files are processed in the order they were added (FIFO queue)

---

### User Story 3 - AI-Generated Task Plans (Priority: P3)

As a user, when my AI Employee identifies an actionable email or file, I want it to automatically create a Plan.md file outlining the steps needed to address it. This helps me understand what needs to be done without having to think through the entire workflow myself.

**Why this priority**: This demonstrates the AI's reasoning capability and provides actionable next steps. It transforms raw inputs (emails, files) into structured action plans.

**Independent Test**: Place a client email requesting an invoice in `/Needs_Action/`, trigger Claude Code processing, and verify a Plan.md file is created in `/Plans/` with checkboxes for: identify client, calculate amount, generate invoice, get approval, send invoice. Delivers value by turning vague requests into clear action items.

**Acceptance Scenarios**:

1. **Given** an email in `/Needs_Action/` contains a clear request (e.g., "Please send invoice for January"), **When** Claude Code processes it, **Then** a Plan.md file is created in `/Plans/` with 3-5 actionable steps and checkboxes
2. **Given** a Plan.md is created, **When** it involves a sensitive action (payment, sending email to new contact), **Then** the Plan includes an approval step with a link to `/Pending_Approval/` file
3. **Given** Claude Code cannot determine clear next steps from an email, **When** processing it, **Then** it creates a Plan.md with a summary and a question for the user (human-in-the-loop escalation)

---

### Edge Cases

- What happens when Gmail API credentials expire? System should log the error, pause the Watcher, and create an alert file in `/Needs_Action/ALERT_gmail_auth_failed.md`
- What happens when the Obsidian vault is locked or inaccessible? Watchers should queue items in a temporary folder and sync when vault becomes available
- What happens if Claude Code is not running when a Watcher detects new items? Items accumulate in `/Needs_Action/` and are processed when Claude Code next runs (batch processing)
- What happens when `/Needs_Action/` folder has 100+ items? Dashboard.md should show a count and recommend archiving old items to prevent overwhelm
- What happens if a file dropped in `/Inbox/` has the same name as an existing file? System should append a timestamp to the filename to prevent overwriting (e.g., `document.pdf` → `document_20260221_143022.pdf`)

## Requirements *(mandatory)*

### Functional Requirements

#### Obsidian Vault Setup

- **FR-001**: System MUST create an Obsidian vault at a user-specified location with the following folder structure: `/Inbox/`, `/Needs_Action/`, `/Plans/`, `/Pending_Approval/`, `/Approved/`, `/Done/`, `/Logs/`, `/Quarantine/`
- **FR-002**: System MUST create a `Dashboard.md` file in the vault root that displays: current date/time, count of items in `/Needs_Action/`, count of items in `/Pending_Approval/`, recent activity log (last 5 actions)
- **FR-003**: System MUST create a `Company_Handbook.md` file in the vault root with default rules: "Always be polite in email responses", "Flag any payment request over $100 for approval", "Respond to client emails within 24 hours"

#### Gmail Watcher

- **FR-004**: System MUST provide a Gmail Watcher Python script that polls Gmail API every 2 minutes for unread emails marked as "important" or containing urgent keywords (configurable list: "urgent", "asap", "invoice", "payment", "help")
- **FR-005**: Gmail Watcher MUST create an `.md` file in `/Needs_Action/` for each detected email with frontmatter containing: type (email), from, subject, received timestamp, priority (high/medium), status (pending)
- **FR-006**: Gmail Watcher MUST extract the email snippet (first 200 characters of body) and include it in the `.md` file under "Email Content" section
- **FR-007**: Gmail Watcher MUST track processed email IDs in a local state file (`.watcher_state.json`) to avoid duplicate processing
- **FR-008**: Gmail Watcher MUST handle Gmail API rate limits gracefully by implementing exponential backoff (1s, 2s, 4s, 8s delays) and logging rate limit errors

#### File System Watcher

- **FR-009**: System MUST provide a File System Watcher Python script that monitors the `/Inbox/` folder for new files using the watchdog library
- **FR-010**: File System Watcher MUST copy detected files to `/Needs_Action/` and create a metadata `.md` file with frontmatter containing: type (file_drop), original_name, size, received timestamp, status (pending)
- **FR-011**: File System Watcher MUST quarantine unsupported file types (executable extensions: .exe, .dmg, .app, .bat, .sh, .cmd) by moving them to `/Quarantine/` and creating an alert in `/Needs_Action/ALERT_quarantined_file.md`

#### Claude Code Integration

- **FR-012**: System MUST provide a Claude Code skill (`.claude/commands/vault-manager.md`) that can read files from `/Needs_Action/`, analyze their content, and create Plan.md files in `/Plans/`
- **FR-013**: Claude Code MUST update `Dashboard.md` after processing each item to reflect: item moved from `/Needs_Action/` to `/Done/`, Plan created (with link), timestamp of action
- **FR-014**: Claude Code MUST create Plan.md files with the following structure: Objective (1-2 sentences), Steps (3-7 checkboxes), Approval Required section (if applicable with link to `/Pending_Approval/` file)
- **FR-015**: System MUST provide an orchestrator script (`orchestrator.py`) that detects new files in `/Needs_Action/` and triggers Claude Code processing automatically

#### Security & Privacy

- **FR-016**: System MUST store Gmail API credentials in a `.env` file (never in vault or version control) with variables: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_TOKEN_PATH
- **FR-017**: System MUST create a `.gitignore` file in the vault root that excludes: `.env`, `.watcher_state.json`, `/Logs/*.json`, any file containing "credentials" or "token" in the name
- **FR-018**: System MUST log all Watcher and Claude Code actions to `/Logs/YYYY-MM-DD.json` in the audit log format specified in the constitution (timestamp, action_type, actor, target, result)

#### Process Management

- **FR-019**: System MUST provide setup instructions for running Watchers as background processes using PM2 or equivalent process manager
- **FR-020**: System MUST include a health check mechanism where Watchers write a heartbeat timestamp to `/Logs/heartbeat.json` every 60 seconds
- **FR-021**: System MUST use UV package manager for all Python dependency management (pyproject.toml and uv.lock files) - direct pip usage is NOT permitted

### Key Entities

- **Email**: Represents an incoming Gmail message with attributes: id (Gmail message ID), from (sender email), subject, snippet (body preview), received timestamp, priority level, processing status
- **File Drop**: Represents a manually added file with attributes: original filename, file size (bytes), file type/extension, received timestamp, processing status, quarantine flag
- **Action Plan**: Represents AI-generated steps to address an email/file with attributes: objective, list of steps (with completion checkboxes), approval required flag, related email/file reference
- **Dashboard Summary**: Represents current system state with attributes: pending items count, pending approvals count, last updated timestamp, recent activity list (last 5 actions)

### Assumptions

- Users have an active Gmail account with API access enabled (Gmail API setup instructions will be provided in documentation)
- Users have Python 3.13+ installed and can run Python scripts
- **Users have UV package manager installed for Python dependency management** (NOT pip directly - UV is required for this project)
- Users have Node.js v24+ installed for PM2 process management
- Users have Obsidian v1.10.6+ installed and know how to open a vault
- Users have Claude Code installed and configured (active subscription or free Gemini API via Claude Code Router)
- Users are comfortable running terminal commands for initial setup (not a GUI application)
- Email volume is moderate (<100 emails per day) - no optimization for high-volume scenarios in Bronze tier
- Internet connection is stable with 10+ Mbps for API calls

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can complete initial vault setup (folder structure, Dashboard.md, Company_Handbook.md) in under 10 minutes following provided documentation
- **SC-002**: Gmail Watcher detects and surfaces important emails in `/Needs_Action/` within 2 minutes of arrival (95% of the time under normal network conditions)
- **SC-003**: File System Watcher processes dropped files and creates metadata within 30 seconds of detection
- **SC-004**: Claude Code generates a Plan.md with actionable steps for 80% of clear email requests (tested with 20 sample emails: invoice requests, meeting requests, document requests)
- **SC-005**: System runs continuously for 24 hours without crashes or manual intervention (tested with Watchers + Orchestrator running)
- **SC-006**: Dashboard.md accurately reflects system state (pending counts match actual folder contents) with updates occurring within 60 seconds of changes
- **SC-007**: User can identify which emails need attention by checking Dashboard.md without opening Gmail (user survey: 90% find it helpful)
- **SC-008**: Zero credentials or secrets are stored in the Obsidian vault (verified by searching vault for "password", "token", "secret", "client_id")

## Out of Scope

The following are explicitly NOT included in Bronze Tier (deferred to Silver/Gold/Platinum):

- **Email sending/replying**: Bronze tier is read-only for Gmail (triage/monitoring only)
- **MCP servers for external actions**: No integration with external APIs beyond Gmail read access
- **Human-in-the-loop approval workflow execution**: Approval files are created but not acted upon
- **Multiple Watchers**: Only Gmail and File System watchers (no WhatsApp, LinkedIn, bank monitoring)
- **Ralph Wiggum loop**: No continuous iteration until task completion
- **Scheduled tasks/cron jobs**: No daily briefings or weekly audits
- **Cross-domain integration**: No business accounting, social media, or payment integrations
- **Cloud deployment**: Local-only operation
- **Advanced error recovery**: Basic logging only, no auto-restart on failure (manual restart required)
