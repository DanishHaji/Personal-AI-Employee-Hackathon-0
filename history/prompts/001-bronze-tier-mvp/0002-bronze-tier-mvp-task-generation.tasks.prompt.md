---
id: 0002
title: bronze-tier-mvp-task-generation
stage: tasks
date: 2026-02-21
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-bronze-tier-mvp
branch: 001-bronze-tier-mvp
user: dani
command: /sp.tasks
labels: ["task-generation", "bronze-tier", "mvp", "user-stories"]
links:
  spec: specs/001-bronze-tier-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-bronze-tier-mvp/tasks.md
tests:
  - Manual acceptance testing per user stories (no automated tests requested)
---

## Prompt

User invoked `/sp.tasks` command to generate actionable task list from Bronze Tier MVP planning documents.

Context: SpecKit Plus workflow continuation - constitution → specify → plan → **tasks** → implementation

Input documents:
- plan.md (technical context, constitution check, project structure)
- spec.md (3 user stories with priorities P1, P2, P3)
- research.md (7 technology decisions)
- data-model.md (4 core entities)
- contracts/file-interfaces.md (6 file-based interface contracts)
- quickstart.md (10-minute setup guide)

Requirements:
- Organize tasks by user story for independent implementation and testing
- Use UV package manager (NOT pip) per FR-021
- Follow strict checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- Mark parallelizable tasks with [P]
- Enable MVP delivery with just User Story 1 (Email Triage)

## Response snapshot

Generated comprehensive tasks.md with 57 tasks organized into 6 phases:

**Phase 1: Setup (6 tasks)**
- UV project initialization with Python 3.13+
- Dependency management via UV (google-auth, watchdog, pyyaml, etc.)
- Project structure creation (src/, tests/, .claude/commands/)
- Environment configuration (.env.example, .gitignore)

**Phase 2: Foundational (7 tasks)**
- Vault initialization script
- Core models (Email, FileDrop, DashboardSummary, ActionPlan)
- Base services (VaultService, AuditLogger)
- Base watcher abstract class with heartbeat

**Phase 3: User Story 1 - Email Triage (11 tasks, P1 - MVP)**
- Gmail API service with OAuth2
- Gmail Watcher with 2-minute polling
- Email entity creation with frontmatter
- Duplicate detection via .watcher_state.json
- Rate limit handling with exponential backoff
- Dashboard updater skill
- Company Handbook template

**Phase 4: User Story 2 - File Drop (9 tasks, P2)**
- File System Watcher using watchdog
- File copy to /Needs_Action/ with metadata
- Unsafe file type quarantine (.exe, .dmg, etc.)
- Quarantine alert creation
- Dashboard integration for FileDrop entities

**Phase 5: User Story 3 - AI Plans (14 tasks, P3)**
- ActionPlan model implementation
- vault-manager skill (read, plan, move actions)
- Approval detection and file creation
- Sequential plan ID generation
- Orchestrator for monitoring /Needs_Action/
- Claude Code skill invocation
- email-triage and file-processor skills

**Phase 6: Polish (10 tasks)**
- PM2 ecosystem configuration
- Documentation (Gmail API setup guide)
- Success criteria validation (SC-001 to SC-008)
- End-to-end testing per quickstart.md
- Edge case handling (credential expiration, vault inaccessibility)
- Security audit

**Key Features**:
- 18 tasks marked [P] for parallel execution
- MVP scope: 24 tasks (Phase 1 + 2 + 3)
- Independent test criteria for each user story
- Dependency graph showing story completion order
- Parallel team strategy examples
- All tasks reference exact file paths

## Outcome

- ✅ Impact: Complete actionable task list enabling immediate Bronze Tier MVP implementation with clear MVP scope (User Story 1 only = 24 tasks)
- 🧪 Tests: Manual acceptance testing per user stories (no automated tests explicitly requested in spec)
- 📁 Files: 1 file created (specs/001-bronze-tier-mvp/tasks.md - 400+ lines)
- 🔁 Next prompts: Begin implementation with Phase 1 (Setup) or Phase 2 (Foundational), then tackle User Story 1 for MVP
- 🧠 Reflection: Task organization by user story enables independent implementation and incremental delivery - MVP is clearly defined as Phase 1 + 2 + 3 (Email Triage only)

## Evaluation notes (flywheel)

- Failure modes observed: None - task generation completed successfully with all required components
- Graders run and results (PASS/FAIL): Format validation PASS (all tasks follow checklist format with ID, optional [P], [Story] labels, file paths)
- Prompt variant (if applicable): Standard /sp.tasks workflow following tasks-template.md structure
- Next experiment (smallest change to try): Begin implementation starting with T001 (UV project initialization)
