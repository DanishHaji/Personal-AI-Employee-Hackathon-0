---
id: 0001
title: Bronze Tier MVP Specification
stage: spec
date: 2026-02-21
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-bronze-tier-mvp
branch: 001-bronze-tier-mvp
user: hackathon-participant
command: sp.specify
labels: ["specification", "bronze-tier", "mvp", "email-triage", "obsidian", "gmail-watcher"]
links:
  spec: specs/001-bronze-tier-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-bronze-tier-mvp/spec.md
  - specs/001-bronze-tier-mvp/checklists/requirements.md
tests:
  - none (specification phase - no tests yet)
---

## Prompt

Bronze Tier MVP: Obsidian vault setup with Gmail watcher, basic folder structure, and Claude Code integration for autonomous email triage

## Response snapshot

Successfully created Bronze Tier MVP specification on branch `001-bronze-tier-mvp`.

**Specification includes:**

**3 Prioritized User Stories:**
1. **P1 - Automated Email Triage** (Core MVP): Monitor Gmail for important/urgent emails, surface them in Dashboard.md within 2 minutes
2. **P2 - Manual File Drop**: Universal inbox for documents from any source (Slack, WhatsApp, downloads)
3. **P3 - AI-Generated Task Plans**: Transform emails/files into structured action plans with checkboxes

**20 Functional Requirements** organized into 6 categories:
- Obsidian Vault Setup (FR-001 to FR-003): Folder structure, Dashboard.md, Company_Handbook.md
- Gmail Watcher (FR-004 to FR-008): Poll API every 2 minutes, extract snippets, handle rate limits
- File System Watcher (FR-009 to FR-011): Monitor /Inbox/, quarantine unsafe files
- Claude Code Integration (FR-012 to FR-015): vault-manager skill, Plan.md generation, orchestrator
- Security & Privacy (FR-016 to FR-018): .env credentials, .gitignore, audit logging
- Process Management (FR-019 to FR-020): PM2 setup, health checks

**8 Success Criteria** (all measurable and technology-agnostic):
- SC-001: Setup in under 10 minutes
- SC-002: Email detection within 2 minutes (95% reliability)
- SC-003: File processing within 30 seconds
- SC-004: Plan generation for 80% of clear requests
- SC-005: 24-hour uptime without crashes
- SC-006: Dashboard accuracy within 60 seconds
- SC-007: 90% user satisfaction for email visibility
- SC-008: Zero credentials in vault

**Quality Validation**: 16/16 checklist items passing (100%)
- No [NEEDS CLARIFICATION] markers
- All requirements testable and unambiguous
- Success criteria measurable and technology-agnostic
- Edge cases identified (5 scenarios)
- Scope clearly bounded with "Out of Scope" section
- Assumptions documented (8 prerequisites)

**Key Entities:**
- Email, File Drop, Action Plan, Dashboard Summary

## Outcome

- ✅ Impact: Bronze Tier MVP fully specified. Provides foundation for 8-12 hour hackathon implementation. Clear acceptance criteria enable TDD approach.
- 🧪 Tests: N/A (specification phase)
- 📁 Files: Created specs/001-bronze-tier-mvp/spec.md (217 lines), specs/001-bronze-tier-mvp/checklists/requirements.md (60 lines)
- 🔁 Next prompts: Run `/sp.plan` to design architecture and implementation approach for Bronze Tier MVP
- 🧠 Reflection: Specification successfully balances detail with clarity. 3 user stories provide incremental value (P1 alone is viable MVP). 20 functional requirements are specific enough for implementation without being prescriptive about technology. Success criteria focus on user outcomes (time savings, reliability) rather than technical metrics.

## Evaluation notes (flywheel)

- Failure modes observed: None - specification creation successful
- Graders run and results (PASS/FAIL): Manual validation - 16/16 checklist items PASS (100% quality score)
- Prompt variant (if applicable): N/A (initial specification)
- Next experiment (smallest change to try): Proceed to planning phase with `/sp.plan` command to design Bronze Tier architecture
