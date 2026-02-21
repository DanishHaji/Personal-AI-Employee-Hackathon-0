# Implementation Plan: Bronze Tier MVP - Personal AI Employee

**Branch**: `001-bronze-tier-mvp` | **Date**: 2026-02-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-bronze-tier-mvp/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a local-first Personal AI Employee (Bronze Tier MVP) that autonomously monitors Gmail for important emails, processes manually dropped files, and generates actionable task plans using Claude Code. The system uses Obsidian as the knowledge base/dashboard, Python watchers as sensors, and implements all AI functionality as Agent Skills. Target implementation time: 8-12 hours.

**Core Value**: Automate email triage to reduce inbox overwhelm, surface urgent messages in under 2 minutes, and transform requests into structured action plans.

## Technical Context

**Language/Version**: Python 3.13+
**Package Manager**: UV (pyproject.toml + uv.lock) - pip NOT permitted per FR-021
**Primary Dependencies**:
- google-auth, google-api-python-client (Gmail API)
- watchdog (file system monitoring)
- python-dotenv (environment variables)
- pyyaml (frontmatter parsing)

**Storage**: Local file system only (Obsidian vault as markdown files, JSON for logs/state)
**Testing**: pytest for Python components, manual acceptance testing for user stories
**Target Platform**: Cross-platform (Windows/macOS/Linux) - local development environment
**Project Type**: Single project (Python scripts + Claude Code skills)
**Performance Goals**:
- Email detection: <2 minutes from arrival to vault (FR-004)
- File processing: <30 seconds from drop to metadata creation (FR-010)
- Dashboard updates: <60 seconds after state changes (SC-006)

**Constraints**:
- Local-only operation (no cloud deployment in Bronze tier)
- Read-only Gmail access (no sending/replying)
- No MCP servers (deferred to Silver tier)
- <100 emails/day volume assumption

**Scale/Scope**:
- Single user, single Gmail account
- ~20 LOC for each watcher script (~100-150 LOC total for watchers)
- 4 Agent Skills (~50-100 LOC each in markdown)
- 1 orchestrator script (~100-150 LOC)
- Estimated total: ~600-800 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Local-First Privacy ✅ PASS

- ✅ Obsidian vault is single source of truth (FR-001, FR-002)
- ✅ Secrets stored in .env files, never in vault (FR-016, FR-017)
- ✅ Vault contains only markdown/JSON state files (FR-005, FR-010, FR-018)
- ✅ No cloud sync of credentials (FR-016, .gitignore excludes sensitive files)

**Compliance**: Full compliance. All data persisted locally in vault. Gmail API credentials in .env outside vault.

### Principle II: Human-in-the-Loop (HITL) ✅ PASS

- ✅ Approval workflow files created in `/Pending_Approval/` (FR-014)
- ⚠️ **Bronze Limitation**: Approval files created but NOT executed (deferred to Silver tier per spec "Out of Scope")
- ✅ Read-only Gmail access prevents accidental email sends
- ✅ File quarantine for unsafe types (FR-011)

**Compliance**: Partial compliance appropriate for Bronze tier. HITL placeholders created (FR-014) but execution deferred to Silver tier as documented in spec.

### Principle III: Security & Credential Management ✅ PASS

- ✅ .env files for Gmail credentials (FR-016)
- ✅ .gitignore excludes secrets (FR-017)
- ✅ Audit logging in JSON format (FR-018)
- ✅ 90-day log retention (FR-018 references constitution requirement)
- ✅ No hardcoded secrets

**Compliance**: Full compliance. Credentials isolated, audit logs structured, secrets excluded from version control.

### Principle IV: Agent Skills Architecture ✅ PASS

- ✅ All AI functionality as Agent Skills (spec requirement repeated in FR-012)
- ✅ vault-manager.md skill for read/write/plan generation (FR-012)
- ✅ Skills in `.claude/commands/` directory structure

**Required Skills for Bronze Tier**:
1. `vault-manager.md` - Read /Needs_Action, write Plan.md, update Dashboard.md
2. `email-triage.md` - Analyze email content, determine priority
3. `file-processor.md` - Process file drops, create metadata
4. `dashboard-updater.md` - Aggregate counts, format recent activity

**Compliance**: Full compliance. Four skills planned matching constitutional requirement.

### Principle V: Tiered Implementation ✅ PASS

- ✅ Bronze Tier scope clearly defined (spec sections: User Stories, Requirements, Out of Scope)
- ✅ Progressive delivery: P1 (email triage) → P2 (file drop) → P3 (AI plans)
- ✅ 8-12 hour estimate aligns with constitutional Bronze tier guidance
- ✅ Silver/Gold/Platinum features explicitly deferred

**Compliance**: Full compliance. Bronze scope honored, no tier creep.

### Principle VI: Autonomous Operation (Ralph Wiggum Loop) ⚠️ DEFERRED

- ⚠️ **Bronze Limitation**: Ralph Wiggum loop explicitly deferred to Gold tier per spec "Out of Scope"
- ✅ Basic orchestrator provides file-triggered automation (FR-015)
- ⚠️ No continuous iteration until task completion

**Compliance**: Acceptable deferral. Constitution allows tiered implementation. Bronze provides foundation (orchestrator) for future Ralph Wiggum integration.

### Principle VII: Observability & Audit Logging ✅ PASS

- ✅ Structured JSON logs (FR-018)
- ✅ Daily log rotation implied by YYYY-MM-DD format (FR-018)
- ✅ 90-day retention (FR-018 references constitution)
- ✅ Health check via heartbeat (FR-020)
- ⚠️ **Bronze Limitation**: Weekly health summaries deferred (Gold tier feature)

**Compliance**: Full compliance for Bronze tier. Core logging implemented, advanced monitoring deferred appropriately.

### Gate Summary

**Status**: ✅ **PASS** - Proceed to Phase 0 Research

**Justifications for Deferrals**:
- HITL execution: Workflow placeholders created, execution needs MCP servers (Silver tier)
- Ralph Wiggum loop: Foundation (orchestrator) in place, full automation is Gold tier
- Advanced monitoring: Basic health checks sufficient for Bronze, weekly summaries are Gold

**No complexity violations requiring justification** - all deferrals align with constitutional tiered implementation principle.

## Project Structure

### Documentation (this feature)

```text
specs/001-bronze-tier-mvp/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command - minimal for Bronze)
├── checklists/          # Quality validation checklists
│   └── requirements.md  # Spec validation (already complete)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

**Selected Structure**: Single Python project (Option 1) - no frontend/backend split needed

```text
# Repository root structure
/
├── .claude/
│   └── commands/                    # Agent Skills (Principle IV)
│       ├── vault-manager.md         # FR-012: Read/write vault, create plans
│       ├── email-triage.md          # Analyze email priority
│       ├── file-processor.md        # Handle file drops
│       └── dashboard-updater.md     # Update Dashboard.md
│
├── src/                             # Python source code
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py          # Abstract base class (DRY)
│   │   ├── gmail_watcher.py         # FR-004 to FR-008
│   │   └── filesystem_watcher.py    # FR-009 to FR-011
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── email.py                 # Email entity from spec
│   │   ├── file_drop.py             # FileDrop entity from spec
│   │   └── dashboard.py             # Dashboard summary model
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gmail_service.py         # Gmail API wrapper
│   │   ├── vault_service.py         # Obsidian file operations
│   │   └── logger_service.py        # FR-018: Structured logging
│   │
│   └── orchestrator.py              # FR-015: Main coordinator
│
├── tests/
│   ├── unit/                        # Unit tests for models/services
│   │   ├── test_email_model.py
│   │   ├── test_gmail_service.py
│   │   └── test_vault_service.py
│   │
│   ├── integration/                 # Integration tests for watchers
│   │   ├── test_gmail_watcher.py
│   │   └── test_filesystem_watcher.py
│   │
│   └── fixtures/                    # Test data
│       ├── sample_emails.json
│       └── test_vault/              # Mock Obsidian vault
│
├── scripts/                         # Setup and utility scripts
│   └── init_vault.py                # FR-001: Create vault structure
│
├── pyproject.toml                   # UV dependency management (FR-021)
├── uv.lock                          # Locked dependencies
├── .env.example                     # Template for credentials (FR-016)
├── .gitignore                       # FR-017: Exclude secrets
└── README.md                        # Setup instructions
```

**Structure Decision**: Single Python project selected because:
- No web UI needed (Obsidian is the GUI)
- All components are Python scripts/services
- Simple CLI-based tools and background watchers
- Complexity appropriate for 8-12 hour Bronze tier scope

### Obsidian Vault Structure (created by scripts/init_vault.py)

```text
[User-specified vault location]/
├── Inbox/                   # FR-009: File drop folder
├── Needs_Action/            # FR-005, FR-010: Watcher output
├── Plans/                   # FR-014: AI-generated plans
├── Pending_Approval/        # FR-014: HITL placeholders
├── Approved/                # HITL workflow (Silver tier+)
├── Done/                    # Completed tasks archive
├── Logs/                    # FR-018: JSON audit logs
├── Quarantine/              # FR-011: Unsafe files
├── Dashboard.md             # FR-002: Real-time summary
└── Company_Handbook.md      # FR-003: AI behavior rules
```

## Complexity Tracking

> **No violations detected** - All constitutional principles satisfied within Bronze tier scope.

No complexity justifications required.
