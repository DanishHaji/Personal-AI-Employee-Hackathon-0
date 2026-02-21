---
id: 0001
title: Create AI Employee Constitution
stage: constitution
date: 2026-02-21
surface: agent
model: claude-sonnet-4-5-20250929
feature: none
branch: master
user: hackathon-participant
command: sp.constitution
labels: ["constitution", "hackathon", "setup", "ai-employee", "local-first", "privacy", "security"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - none (constitution work - no tests required)
---

## Prompt

Create constitution for Personal AI Employee Hackathon project - a local-first autonomous agent system that manages personal and business affairs using Claude Code as the brain, Obsidian as memory/GUI, Python watchers as sensors, and MCP servers as action handlers. Focus on Bronze to Platinum tier implementation following hackathon requirements.

## Response snapshot

Successfully created Personal AI Employee Constitution v1.0.0 at `.specify/memory/constitution.md`.

The constitution establishes 7 core principles:
1. **Local-First Privacy (NON-NEGOTIABLE)** - All sensitive data stays local in Obsidian vault
2. **Human-in-the-Loop (HITL)** - Critical actions require approval via `/Pending_Approval/` workflow
3. **Security & Credential Management (NON-NEGOTIABLE)** - Environment variables, secrets manager, audit logging
4. **Agent Skills Architecture (NON-NEGOTIABLE)** - All AI functionality as reusable Agent Skills
5. **Tiered Implementation** - Bronze → Silver → Gold → Platinum progressive delivery
6. **Autonomous Operation** - Ralph Wiggum loop for multi-step task completion
7. **Observability & Audit Logging** - All actions logged with 90-day retention

Additional sections defined:
- **Architecture Components**: Brain (Claude Code), Memory (Obsidian), Senses (Watchers), Hands (MCP), Orchestrator
- **Security Requirements**: Sandboxing, error recovery, watchdog process
- **Development Workflow**: SpecKit Plus methodology (constitution → specify → plan → tasks → implement)
- **Governance**: Amendment procedures, compliance reviews, semantic versioning

Reviewed and validated alignment with existing templates (plan-template.md, spec-template.md, tasks-template.md).

## Outcome

- ✅ Impact: Foundation established for entire Personal AI Employee project. All features must align with these 7 principles.
- 🧪 Tests: N/A (constitution document)
- 📁 Files: Created `.specify/memory/constitution.md` (1 file, 321 lines)
- 🔁 Next prompts: Run `/sp.specify` to create first feature specification (e.g., Bronze Tier MVP: Obsidian vault setup with Gmail watcher)
- 🧠 Reflection: Constitution successfully captures hackathon requirements (Bronze to Platinum tiers), emphasizes security (HITL, secrets management, audit logging), and mandates Agent Skills architecture. The 4-tier progression provides clear milestones.

## Evaluation notes (flywheel)

- Failure modes observed: None - constitution creation successful
- Graders run and results (PASS/FAIL): N/A (no automated graders for constitution)
- Prompt variant (if applicable): N/A (initial creation)
- Next experiment (smallest change to try): Proceed to feature specification phase with `/sp.specify` command for Bronze Tier implementation
