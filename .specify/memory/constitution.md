<!--
Sync Impact Report:
- Version change: NONE → 1.0.0
- Modified principles: NONE (initial creation)
- Added sections:
  * Core Principles (7 principles)
  * Architecture Components
  * Security Requirements
  * Development Workflow
  * Governance
- Templates requiring updates:
  ✅ plan-template.md (reviewed - Constitution Check section aligns)
  ✅ spec-template.md (reviewed - requirements align with principles)
  ✅ tasks-template.md (reviewed - task categorization aligns)
- Follow-up TODOs: None

Rationale for version 1.0.0:
- Initial constitution creation for Personal AI Employee Hackathon 0
- Establishes foundational principles for local-first autonomous agent system
- MAJOR version as this is the first ratified constitution
-->

# Personal AI Employee Constitution

## Core Principles

### I. Local-First Privacy (NON-NEGOTIABLE)

All sensitive data MUST remain local in the Obsidian vault. External APIs may be called
for actions, but persistent storage of personal information (emails, messages, bank
transactions, credentials) MUST be local-only.

**Rationale**: Privacy is paramount. Users retain full control over their data. No cloud
vendor lock-in. Data portability guaranteed through markdown files.

**Rules**:
- Obsidian vault is the single source of truth for all state
- Secrets never stored in vault (use .env files with .gitignore)
- Vault contains only markdown/JSON state files
- WhatsApp sessions, banking credentials, payment tokens MUST NOT sync to cloud
- Encryption at rest recommended for sensitive vaults

### II. Human-in-the-Loop (HITL) - Critical Actions

Sensitive actions MUST require explicit human approval via file-based workflow. The AI
writes approval requests to `/Pending_Approval/` folder. Humans review and move to
`/Approved/` to authorize execution.

**Rationale**: Prevents AI accidents. Maintains human agency. Builds trust through
transparency. Provides audit trail.

**Auto-Approve Thresholds** (configurable in Company_Handbook.md):
- Email replies: To known contacts only
- Payments: < $50 to recurring payees only
- Social media: Scheduled posts only (no replies/DMs)
- File operations: Create/read only (never delete/move outside vault)

**Always Require Approval**:
- New email contacts or bulk sends
- All new payees or payments > $100
- Social media replies or direct messages
- File deletions or moves outside vault
- Any irreversible action

### III. Security & Credential Management (NON-NEGOTIABLE)

Credentials MUST be managed securely. Never hardcode secrets. Never commit credentials
to version control. Every action MUST be logged for audit.

**Rules**:
- Use environment variables for all API keys/tokens (.env files)
- Use OS secrets manager (Keychain/Credential Manager/1Password CLI) for banking creds
- Rotate credentials monthly and after any suspected breach
- Development mode (DRY_RUN=true) prevents real external actions during testing
- Audit logs stored in `/Vault/Logs/YYYY-MM-DD.json` with 90-day minimum retention

**Audit Log Format** (required fields):
```json
{
  "timestamp": "ISO 8601 format",
  "action_type": "email_send|payment|social_post|file_op",
  "actor": "claude_code|human",
  "target": "destination/recipient",
  "parameters": {},
  "approval_status": "approved|rejected|pending",
  "approved_by": "human|auto",
  "result": "success|failure|error"
}
```

### IV. Agent Skills Architecture (NON-NEGOTIABLE)

All AI functionality MUST be implemented as Agent Skills. Skills are reusable,
composable, and independently testable capabilities that Claude Code can invoke.

**Rationale**: Promotes modularity. Enables skill reuse across features. Simplifies
testing. Follows Anthropic best practices.

**Rules**:
- Create `.claude/commands/` skill files for all major capabilities
- Each skill has clear inputs, outputs, and error handling
- Skills follow single responsibility principle
- Skills can invoke other skills but must avoid circular dependencies
- Document skill dependencies and usage examples

**Required Skills** (minimum for Bronze tier):
- Vault management (read/write/move files)
- Email triage and drafting
- Task planning (create Plan.md files)
- Approval workflow handling

### V. Tiered Implementation - Progressive Delivery

Features MUST be built incrementally following Bronze → Silver → Gold → Platinum tiers.
Each tier adds capabilities while maintaining all previous tier requirements.

**Bronze Tier** (Minimum Viable Deliverable - 8-12 hours):
- Obsidian vault with Dashboard.md and Company_Handbook.md
- One working Watcher script (Gmail OR file system monitoring)
- Claude Code successfully reading from and writing to vault
- Basic folder structure: /Inbox, /Needs_Action, /Done
- All AI functionality implemented as Agent Skills

**Silver Tier** (Functional Assistant - 20-30 hours):
- All Bronze requirements plus:
- Two or more Watcher scripts (Gmail + WhatsApp + LinkedIn)
- Automatically post on LinkedIn about business to generate sales
- Claude reasoning loop that creates Plan.md files
- One working MCP server for external action (e.g., sending emails)
- Human-in-the-loop approval workflow for sensitive actions
- Basic scheduling via cron or Task Scheduler
- All AI functionality implemented as Agent Skills

**Gold Tier** (Autonomous Employee - 40+ hours):
- All Silver requirements plus:
- Full cross-domain integration (Personal + Business)
- Odoo Community accounting system integration via MCP server
- Facebook, Instagram, Twitter (X) integration with posting and summaries
- Multiple MCP servers for different action types
- Weekly Business and Accounting Audit with CEO Briefing generation
- Error recovery and graceful degradation
- Comprehensive audit logging (90+ days)
- Ralph Wiggum loop for autonomous multi-step task completion
- Documentation of architecture and lessons learned
- All AI functionality implemented as Agent Skills

**Platinum Tier** (Always-On Cloud + Local Executive - 60+ hours):
- All Gold requirements plus:
- 24/7 Cloud VM deployment with always-on watchers and health monitoring
- Work-Zone Specialization (Cloud: triage/drafts, Local: approvals/sensitive actions)
- Delegation via synced vault (Git/Syncthing) with claim-by-move rule
- Security rule: Secrets never sync (Cloud never has WhatsApp sessions/banking creds)
- Cloud-hosted Odoo Community with HTTPS, backups, health monitoring
- Platinum demo: Email arrives while Local offline → Cloud drafts reply → Local approves → send
- All AI functionality implemented as Agent Skills

### VI. Autonomous Operation - Ralph Wiggum Loop

For multi-step tasks, the AI MUST continue iterating until completion using the Ralph
Wiggum pattern (Stop hook that checks completion and re-injects prompt if needed).

**Rationale**: Prevents lazy agents. Ensures tasks finish. Mimics human work-until-done behavior.

**Completion Strategies**:
1. Promise-based (simple): Claude outputs `<promise>TASK_COMPLETE</promise>`
2. File movement (advanced): Stop hook detects task file moved to `/Done/`

**Rules**:
- Maximum iterations configurable (default: 10)
- Exponential backoff on repeated failures (1s, 2s, 4s, 8s...)
- Human can interrupt by creating `/STOP` file in vault root
- Failed loops logged with reason and iteration count
- Reference implementation: `https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum`

### VII. Observability & Audit Logging

Every action the AI takes MUST be logged. Logs MUST be human-readable and queryable.
Watchers and orchestrators MUST report health status.

**Rationale**: Debugging requires visibility. Compliance requires audit trails. Trust
requires transparency.

**Logging Requirements**:
- Structured logs in JSON format (parseable and human-readable)
- Log rotation daily, retention minimum 90 days
- Separate log streams: watcher logs, action logs, error logs, audit logs
- Include: timestamp, actor, action, target, result, duration
- Errors include full stack traces and context

**Health Monitoring** (Gold tier+):
- Watchdog process monitors critical process PIDs
- Auto-restart failed watchers/orchestrators
- Alert human on repeated failures (>3 consecutive restarts)
- Weekly health summary in Dashboard.md

## Architecture Components

**The Brain**: Claude Code acts as the reasoning engine. Uses File System tools to read
tasks from vault and write reports/plans. Invokes MCP servers for external actions.
Ralph Wiggum loop keeps it working until multi-step tasks complete.

**The Memory/GUI**: Obsidian vault (local Markdown) serves as both the knowledge base
and user interface. Contains:
- `/Needs_Action/` - Incoming tasks from watchers
- `/Plans/` - Multi-step plan files created by Claude
- `/Pending_Approval/` - Actions awaiting human approval
- `/Approved/` - Human-approved actions ready for execution
- `/Done/` - Completed tasks (archive)
- `/Logs/` - Audit logs
- `Dashboard.md` - Real-time summary (bank balance, pending messages, active projects)
- `Company_Handbook.md` - Rules of Engagement for AI behavior
- `Business_Goals.md` - Metrics, targets, and audit rules

**The Senses (Watchers)**: Lightweight Python scripts monitor external sources and
create actionable .md files in `/Needs_Action/`:
- Gmail Watcher: Polls Gmail API for important unread emails
- WhatsApp Watcher: Uses Playwright to monitor WhatsApp Web for urgent keywords
- Finance Watcher: Downloads bank transactions or calls banking APIs
- File System Watcher: Monitors drop folder for manual file inputs

**The Hands (MCP Servers)**: Model Context Protocol servers handle external actions:
- Email MCP: Send, draft, search emails via Gmail API
- Browser MCP: Navigate, click, fill forms (for payment portals)
- Calendar MCP: Create, update events
- Social MCP: Post to LinkedIn, Twitter, Facebook, Instagram

**The Orchestrator**: Master Python process (`orchestrator.py`) handles:
- Scheduled tasks (cron-like triggers for daily briefings)
- Folder watching (detects new files in `/Needs_Action/` and triggers Claude)
- Process management (starts/monitors Watchers)
- Approval workflow (moves approved actions to execution queue)

## Security Requirements

### Sandboxing & Isolation

During development, protect against unintended actions:

- **Development Mode**: Set `DEV_MODE=true` to prevent real external actions
- **Dry Run**: All action scripts MUST support `--dry-run` flag that logs without executing
- **Separate Accounts**: Use test/sandbox accounts for Gmail and banking during development
- **Rate Limiting**: Maximum actions per hour (configurable, default: 10 emails, 3 payments)

### Error Recovery

System MUST degrade gracefully when components fail:

- **Gmail API down**: Queue outgoing emails locally, process when restored
- **Banking API timeout**: Never retry payments automatically, always require fresh approval
- **Claude Code unavailable**: Watchers continue collecting, queue grows for later processing
- **Obsidian vault locked**: Write to temporary folder, sync when available

**Retry Logic** (for transient errors only):
- Exponential backoff: 1s, 2s, 4s, 8s... up to 60s max delay
- Maximum 3 attempts before human notification
- Never retry: payments, deletions, irreversible actions

### Watchdog Process

`watchdog.py` monitors critical process health:
- Checks PIDs every 60 seconds
- Auto-restarts crashed processes
- Logs restart events
- Notifies human after 3+ consecutive failures

## Development Workflow

This project MUST follow SpecKit Plus methodology:

1. **Constitution** (this file) - Establishes principles and constraints
2. **Specify** (`/sp.specify`) - Create feature specification with user stories and requirements
3. **Plan** (`/sp.plan`) - Design architecture and implementation approach
4. **Tasks** (`/sp.tasks`) - Generate dependency-ordered actionable tasks
5. **Implement** (`/sp.implement`) - Execute tasks following TDD where applicable

### Prompt History Records (PHR)

After completing any significant work (implementation, planning, debugging, spec creation),
a PHR MUST be created using `/sp.phr` command. PHRs are routed automatically:
- Constitution work → `history/prompts/constitution/`
- Feature work → `history/prompts/<feature-name>/`
- General work → `history/prompts/general/`

### Architecture Decision Records (ADR)

When significant architectural decisions are made (typically during `/sp.plan` or `/sp.tasks`),
suggest documenting with: "📋 Architectural decision detected: <brief> — Document reasoning
and tradeoffs? Run `/sp.adr <decision-title>`"

Wait for user consent; never auto-create ADRs.

**Significance Test** (all must be true):
- Impact: Long-term consequences? (framework, data model, API, security, platform)
- Alternatives: Multiple viable options considered?
- Scope: Cross-cutting and influences system design?

## Governance

This constitution supersedes all other development practices and decisions. When in doubt,
refer to the principles above.

**Amendment Procedure**:
1. Proposed changes documented with rationale
2. Impact assessment on existing features
3. User/team approval required
4. Version increment following semantic versioning
5. Update dependent templates and documentation
6. Create migration plan if breaking changes

**Compliance Reviews**:
- All pull requests MUST verify constitutional compliance
- Security principles (III) reviewed on every sensitive feature
- HITL principles (II) validated on every action-taking feature
- Agent Skills requirement (IV) enforced on all AI functionality

**Version Management**:
- MAJOR: Backward incompatible principle removals or redefinitions
- MINOR: New principle/section added or materially expanded
- PATCH: Clarifications, wording, typo fixes

**Version**: 1.0.0 | **Ratified**: 2026-02-21 | **Last Amended**: 2026-02-21
