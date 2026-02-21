---
description: "Implementation tasks for Bronze Tier MVP - Personal AI Employee"
---

# Tasks: Bronze Tier MVP - Personal AI Employee

**Input**: Design documents from `/specs/001-bronze-tier-mvp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/file-interfaces.md, quickstart.md

**Tests**: Tests are NOT explicitly requested in the spec. Tasks focus on implementation and manual acceptance testing per user stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single Python project**: `src/`, `tests/`, `.claude/commands/` at repository root
- All paths relative to repository root `/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, UV package manager setup, and basic structure

- [x] T001 Initialize UV Python project with pyproject.toml (Python 3.13+, UV package manager)
- [x] T002 [P] Add dependencies via UV: google-auth, google-api-python-client, watchdog, python-dotenv, pyyaml
- [x] T003 [P] Create project structure: src/watchers/, src/models/, src/services/, tests/unit/, tests/integration/, scripts/
- [x] T004 [P] Create .env.example file with template variables: GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, VAULT_PATH, DEV_MODE
- [x] T005 [P] Create .gitignore excluding: .env, token.json, credentials.json, .watcher_state.json, /Logs/*.json
- [x] T006 [P] Create README.md with quickstart setup instructions referencing specs/001-bronze-tier-mvp/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create vault initialization script: scripts/init_vault.py that creates Obsidian folder structure (FR-001)
- [x] T008 [P] Implement base Email model in src/models/email.py with YAML frontmatter serialization (data-model.md Entity 1)
- [x] T009 [P] Implement FileDrop model in src/models/file_drop.py with YAML frontmatter serialization (data-model.md Entity 2)
- [x] T010 [P] Implement DashboardSummary model in src/models/dashboard.py (data-model.md Entity 4)
- [x] T011 Implement VaultService in src/services/vault_service.py for reading/writing markdown files with frontmatter parsing
- [x] T012 [P] Implement AuditLogger service in src/services/logger_service.py with structured JSON logging to /Logs/YYYY-MM-DD.json (FR-018)
- [x] T013 Create base Watcher abstract class in src/watchers/base_watcher.py with heartbeat mechanism (FR-020)

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automated Email Triage and Inbox Visibility (Priority: P1) 🎯 MVP

**Goal**: Monitor Gmail inbox, identify important/urgent emails, surface them in Dashboard.md within 2 minutes

**Independent Test**: Send test important email to Gmail account → verify EMAIL_{id}.md appears in /Needs_Action/ within 2 minutes → verify Dashboard.md shows pending count

### Implementation for User Story 1

- [x] T014 [P] [US1] Implement GmailService in src/services/gmail_service.py with OAuth2 authentication and API query methods (research.md Section 2)
- [x] T015 [P] [US1] Create Gmail Watcher in src/watchers/gmail_watcher.py that polls Gmail API every 2 minutes (FR-004)
- [x] T016 [US1] Implement email detection logic in gmail_watcher.py: filter by "important" label and urgent keywords (FR-004, FR-005)
- [x] T017 [US1] Implement Email entity creation in gmail_watcher.py: write EMAIL_{id}.md to /Needs_Action/ with frontmatter and snippet (FR-005, FR-006, Contract 1)
- [x] T018 [US1] Implement duplicate detection in gmail_watcher.py using .watcher_state.json to track processed email IDs (FR-007)
- [x] T019 [US1] Implement Gmail API rate limit handling with exponential backoff (1s, 2s, 4s, 8s) (FR-008, research.md)
- [x] T020 [US1] Add heartbeat mechanism to gmail_watcher.py writing to /Logs/heartbeat.json every 60 seconds (FR-020, Contract 5)
- [x] T021 [US1] Add audit logging to gmail_watcher.py for email_detected actions (FR-018, Contract 6)
- [x] T022 [US1] Create Dashboard updater skill in .claude/commands/dashboard-updater.md that counts /Needs_Action/ items and formats Dashboard.md (FR-002, FR-013, Contract 4)
- [x] T023 [US1] Implement Dashboard.md template generation in scripts/init_vault.py with placeholders for counts and recent activity (FR-002)
- [x] T024 [US1] Create Company_Handbook.md template in scripts/init_vault.py with default rules (FR-003)

**Checkpoint**: ✅ User Story 1 is fully functional - emails detected, surfaced in vault, Dashboard shows counts

---

## Phase 4: User Story 2 - Manual File Drop for AI Processing (Priority: P2)

**Goal**: Monitor /Inbox/ folder, copy files to /Needs_Action/ with metadata within 30 seconds

**Independent Test**: Drop PDF file into /Inbox/ → verify file copied to /Needs_Action/ with FILE_{timestamp}_{filename}.md metadata within 30 seconds

### Implementation for User Story 2

- [x] T025 [P] [US2] Create File System Watcher in src/watchers/filesystem_watcher.py using watchdog library (FR-009, research.md Section 3)
- [x] T026 [US2] Implement file creation event handler in filesystem_watcher.py to detect new files in /Inbox/ (FR-009)
- [x] T027 [US2] Implement file copy logic in filesystem_watcher.py: copy file to /Needs_Action/ with timestamp suffix to avoid conflicts (FR-010, Contract 2)
- [x] T028 [US2] Implement FileDrop metadata creation in filesystem_watcher.py: write FILE_{timestamp}_{filename}.md with frontmatter (FR-010, Contract 2)
- [x] T029 [US2] Implement unsafe file type quarantine logic in filesystem_watcher.py for .exe, .dmg, .app, .bat, .sh, .cmd, .msi, .dll (FR-011, Contract 2)
- [x] T030 [US2] Implement quarantine alert creation in filesystem_watcher.py: write ALERT_quarantined_{filename}.md to /Needs_Action/ (FR-011, Contract 2)
- [x] T031 [US2] Add heartbeat mechanism to filesystem_watcher.py writing to /Logs/heartbeat.json every 60 seconds (FR-020, Contract 5)
- [x] T032 [US2] Add audit logging to filesystem_watcher.py for file_dropped actions (FR-018, Contract 6)
- [x] T033 [US2] Update dashboard-updater.md skill to include FileDrop entities in Dashboard.md recent activity (Contract 4)

**Checkpoint**: ✅ User Stories 1 AND 2 are both working independently - emails and files both surface in /Needs_Action/

---

## Phase 5: User Story 3 - AI-Generated Task Plans (Priority: P3)

**Goal**: Process items in /Needs_Action/, create Plan.md files with 3-7 actionable steps in /Plans/

**Independent Test**: Place invoice request email in /Needs_Action/ → trigger Claude Code → verify PLAN_{id}.md created in /Plans/ with steps: identify client, calculate amount, generate invoice, get approval, send invoice

### Implementation for User Story 3

- [x] T034 [P] [US3] Implement ActionPlan model in src/models/action_plan.py with frontmatter serialization (data-model.md Entity 3)
- [x] T035 [US3] Create vault-manager skill in .claude/commands/vault-manager.md with actions: read, plan, move (FR-012, research.md Section 6)
- [x] T036 [US3] Implement read action in vault-manager.md: parse frontmatter from /Needs_Action/ files and analyze content
- [x] T037 [US3] Implement plan action in vault-manager.md: generate Plan.md with Objective and 3-7 Steps based on Email/FileDrop content (FR-014, Contract 3)
- [x] T038 [US3] Implement approval detection logic in vault-manager.md: set approval_required=true for email sends, payments >$100, deletions, social posts (Contract 3)
- [x] T039 [US3] Implement approval file creation in vault-manager.md: write APPROVAL_{context}_{date}.md to /Pending_Approval/ if approval_required (FR-014, Contract 3)
- [x] T040 [US3] Implement plan_id generation logic in vault-manager.md: sequential PLAN_001, PLAN_002, etc. (Contract 3)
- [x] T041 [US3] Add Company_Handbook.md reading to vault-manager.md for context rules (FR-003, Contract 3)
- [x] T042 [US3] Create orchestrator in src/orchestrator.py that monitors /Needs_Action/ folder for new .md files (FR-015)
- [x] T043 [US3] Implement Claude Code invocation in orchestrator.py: trigger vault-manager skill with file path when new item detected (FR-015)
- [x] T044 [US3] Add dashboard update trigger in orchestrator.py: invoke dashboard-updater skill after plan creation (FR-013, Contract 4)
- [x] T045 [US3] Add audit logging to orchestrator.py for plan_created actions (FR-018, Contract 6)
- [x] T046 [US3] Create email-triage skill in .claude/commands/email-triage.md for email-specific analysis and priority determination
- [x] T047 [US3] Create file-processor skill in .claude/commands/file-processor.md for file-specific analysis and action suggestions

**Checkpoint**: ✅ All user stories are now independently functional - emails triaged, files processed, plans generated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, PM2 setup, documentation

- [x] T048 [P] Create PM2 ecosystem.config.js for managing all watchers and orchestrator as background processes (FR-019, research.md Section 5)
- [x] T049 [P] Add PM2 startup instructions to README.md with commands: pm2 start, pm2 status, pm2 logs (FR-019)
- [x] T050 [P] Create credentials setup guide in docs/gmail-api-setup.md with OAuth2 flow instructions (quickstart.md Step 3)
- [x] T051 [P] Validate all 8 success criteria from spec.md: SC-001 through SC-008
- [x] T052 Run full end-to-end test following quickstart.md: setup vault → start watchers → send test email → drop test file → verify plans created
- [x] T053 [P] Add error handling for Gmail API credential expiration with alert file creation (Edge Case from spec.md)
- [x] T054 [P] Add error handling for vault inaccessibility with temporary queue mechanism (Edge Case from spec.md)
- [x] T055 Validate Dashboard.md shows warning when /Needs_Action/ has 100+ items (Edge Case from spec.md)
- [x] T056 [P] Security audit: verify no credentials in vault, check .gitignore coverage (FR-017, SC-008)
- [x] T057 [P] Performance validation: confirm system runs 24 hours without crashes (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational (Phase 2) completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories (Phase 3, 4, 5) being complete

### User Story Dependencies

- **User Story 1 - Email Triage (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 - File Drop (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1 (completely independent)
- **User Story 3 - AI Plans (P3)**: Can start after Foundational (Phase 2) - Integrates with US1 and US2 but processes their outputs independently

### Within Each User Story

- Models must be created before services that use them (though foundational models already done in Phase 2)
- Watchers before orchestrator (for US3)
- Skills before orchestrator invocation (for US3)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002, T003, T004, T005, T006 can all run in parallel

**Phase 2 (Foundational)**:
- T008, T009, T010 (all models) can run in parallel
- T012 (AuditLogger) can run in parallel with models

**Phase 3 (User Story 1)**:
- T014 (GmailService), T015 (Gmail Watcher skeleton), T022 (Dashboard skill), T023 (Dashboard template), T024 (Handbook template) can run in parallel

**Phase 4 (User Story 2)**:
- T025 (FS Watcher) can start while US1 is still in progress if foundational phase is complete

**Phase 5 (User Story 3)**:
- T034 (ActionPlan model), T035 (vault-manager skeleton), T046 (email-triage skill), T047 (file-processor skill) can run in parallel

**Phase 6 (Polish)**:
- T048, T049, T050, T051, T053, T054, T056 can all run in parallel

**Cross-Story Parallelization**:
- Once Phase 2 complete, US1 (Phase 3) and US2 (Phase 4) can proceed in parallel by different developers
- US3 (Phase 5) can start in parallel with US1/US2 if team capacity allows, since it processes their outputs

---

## Parallel Example: User Story 1

```bash
# Launch parallel tasks for User Story 1 setup:
Task T014: "Implement GmailService in src/services/gmail_service.py"
Task T015: "Create Gmail Watcher skeleton in src/watchers/gmail_watcher.py"
Task T022: "Create dashboard-updater skill in .claude/commands/dashboard-updater.md"
Task T023: "Implement Dashboard.md template in scripts/init_vault.py"
Task T024: "Create Company_Handbook.md template in scripts/init_vault.py"

# These all touch different files and have no dependencies on each other
```

## Parallel Example: User Story 3

```bash
# Launch parallel tasks for User Story 3 setup:
Task T034: "Implement ActionPlan model in src/models/action_plan.py"
Task T035: "Create vault-manager skill in .claude/commands/vault-manager.md"
Task T046: "Create email-triage skill in .claude/commands/email-triage.md"
Task T047: "Create file-processor skill in .claude/commands/file-processor.md"

# These all touch different files and can start together
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (UV initialization, dependencies, project structure)
2. Complete Phase 2: Foundational (vault script, models, services, base watcher) - **CRITICAL**
3. Complete Phase 3: User Story 1 (Email Triage)
4. **STOP and VALIDATE**: Test User Story 1 independently using acceptance scenarios from spec.md
5. Deploy/demo if ready - **This is a viable MVP**: Emails surface in Dashboard within 2 minutes

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)** - Email triage working
3. Add User Story 2 → Test independently → **Deploy/Demo** - Email + File drop working
4. Add User Story 3 → Test independently → **Deploy/Demo** - Full Bronze Tier with AI plans
5. Complete Polish phase → **Final Bronze Tier release**
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phase 1 + 2)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (Email Triage) - Tasks T014-T024
   - **Developer B**: User Story 2 (File Drop) - Tasks T025-T033
   - **Developer C**: User Story 3 (AI Plans) - Tasks T034-T047
3. Stories complete and integrate independently
4. Team completes Polish phase together (Phase 6)

---

## Task Summary

**Total Tasks**: 57 tasks

**Task Count per Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 7 tasks
- Phase 3 (User Story 1 - Email Triage): 11 tasks
- Phase 4 (User Story 2 - File Drop): 9 tasks
- Phase 5 (User Story 3 - AI Plans): 14 tasks
- Phase 6 (Polish): 10 tasks

**Task Count per User Story**:
- User Story 1 (P1 - Email Triage): 11 tasks
- User Story 2 (P2 - File Drop): 9 tasks
- User Story 3 (P3 - AI Plans): 14 tasks

**Parallel Opportunities Identified**: 18 tasks marked with [P] for parallelization

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 24 tasks for a viable MVP demonstrating email triage

**Independent Test Criteria**:
- **US1**: Send important email → verify EMAIL_{id}.md in /Needs_Action/ within 2 minutes → verify Dashboard.md count
- **US2**: Drop PDF to /Inbox/ → verify file + metadata in /Needs_Action/ within 30 seconds
- **US3**: Place invoice email in /Needs_Action/ → run Claude Code → verify PLAN_{id}.md with 3-7 steps in /Plans/

---

## Notes

- **UV Package Manager**: All Python dependency management MUST use UV (FR-021) - commands: `uv sync`, `uv add`, `uv run`
- **[P] tasks**: Different files, no dependencies, can run in parallel
- **[Story] label**: Maps task to specific user story for traceability (US1, US2, US3)
- **Each user story is independently completable and testable** per spec requirements
- **No tests explicitly requested**: Focus on implementation and manual acceptance testing per user stories
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- **Success Criteria Validation**: Task T051 ensures all 8 success criteria (SC-001 to SC-008) are verified
- **Edge Cases**: Tasks T053-T055 address edge cases from spec.md
- **Security**: Task T056 validates FR-017 (.gitignore) and SC-008 (no credentials in vault)
