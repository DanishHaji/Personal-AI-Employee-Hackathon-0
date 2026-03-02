---
description: "Task breakdown for Gold Tier - Autonomous AI Employee"
---

# Tasks: Gold Tier - Autonomous AI Employee

**Input**: Design documents from `/specs/003-gold-tier-upgrade/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: No explicit test tasks in this breakdown - tests will be integrated into implementation tasks as validations

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/`, `tests/` at repository root
- Extends existing Bronze/Silver Tier architecture

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Gold Tier dependencies

- [X] T001 Add Gold Tier dependencies to pyproject.toml (google-api-python-client, jinja2, pandas, cryptography, openai, easyocr, fuzzywuzzy, zoomus, keyring)
- [X] T002 Run uv sync to install new dependencies
- [X] T003 [P] Create .specify/templates/documents/ directory for Jinja2 templates
- [X] T004 [P] Create document template stubs in .specify/templates/documents/ (weekly-status.md.j2, meeting-notes.md.j2, monthly-summary.md.j2)
- [X] T005 [P] Update .gitignore with Gold Tier patterns (Calendar/events.json, Insights/*.json, Budgets/*.json, *.encrypted)
- [X] T006 [P] Create vault directories for Gold Tier (Calendar/, Insights/, Budgets/, Receipts/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create src/services/encryption_service.py with AES-256-GCM encryption using cryptography library
- [X] T008 Implement keyring integration in encryption_service.py for key management
- [X] T009 [P] Create audit log query utilities in src/services/audit_service.py (needed by Analytics US4)
- [X] T010 [P] Extend Company_Handbook.md YAML frontmatter schema with trust_rules section
- [X] T011 Create base model class in src/models/base_model.py with encryption support and JSON Schema validation
- [X] T012 Update executor service in src/executor.py to support trust evaluation integration point

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Autonomous Workflows & Trust Levels (Priority: P1) 🎯 MVP

**Goal**: Implement trust framework to auto-approve trusted actions without HITL, reducing approval friction by 60%

**Independent Test**: Configure trust rule for email replies to known contacts, receive test email, verify auto-approval without /Pending_Approval/ file, check audit log shows trust_rule_id

### Implementation for User Story 1

- [X] T013 [P] [US1] Create TrustRule model in src/models/trust_rule.py with validation against contracts/trust-rule-schema.json
- [X] T014 [P] [US1] Create src/services/trust_evaluator.py with rule loading from Company_Handbook.md
- [X] T015 [US1] Implement rule matching logic in trust_evaluator.py (action_type, contact_filter, content_pattern, time_pattern matching)
- [X] T016 [US1] Implement effectiveness tracking in trust_evaluator.py (usage_count, effectiveness_score calculation)
- [X] T017 [US1] Add auto-disable logic when effectiveness_score drops below 0.80
- [X] T018 [US1] Integrate TrustEvaluator into executor.py process_approved() method
- [X] T019 [US1] Update audit log schema to include trust_rule_id and approved_by fields
- [X] T020 [US1] Create .claude/commands/trust-evaluator.md agent skill for trust rule management
- [X] T021 [US1] Add trust evaluation to action plan execution flow with logging
- [X] T022 [US1] Create pytest tests in tests/unit/test_trust_evaluator.py for rule matching and effectiveness tracking
- [X] T023 [US1] Run quickstart.md US1 integration test (Test Scenario 1.1)

**Checkpoint**: At this point, trust framework is fully functional - all other autonomous features can now use trust evaluation

---

## Phase 4: User Story 2 - Calendar & Meeting Management (Priority: P2)

**Goal**: Autonomous Google Calendar integration with conflict resolution and meeting scheduling

**Independent Test**: Connect to test Google Calendar, create meeting request with preferred times, verify conflict detection and alternative time suggestion, confirm calendar invite sent

### Implementation for User Story 2

- [X] T024 [P] [US2] Create CalendarEvent model in src/models/calendar_event.py with validation against contracts/calendar-event-schema.json
- [X] T025 [P] [US2] Create src/services/calendar_service.py with Google Calendar API authentication
- [X] T026 [US2] Implement calendar event query in calendar_service.py (list events, check availability)
- [X] T027 [US2] Implement conflict detection logic in calendar_service.py (time overlap detection for 100 events <500ms)
- [X] T028 [US2] Implement event creation with conflict resolution in calendar_service.py
- [X] T029 [US2] Add local event cache to /Calendar/events.json with sync logic
- [X] T030 [US2] Implement recurring event support (RRULE parsing) in calendar_service.py
- [X] T031 [US2] Add calendar preference validation (work hours, no-meeting blocks) in calendar_service.py
- [X] T032 [US2] Create .claude/commands/calendar-manager.md agent skill
- [X] T033 [US2] Integrate calendar operations with trust framework (auto-schedule trusted meeting types)
- [X] T034 [US2] Add hourly background sync task to src/watchers/calendar_watcher.py
- [X] T035 [US2] Create pytest tests in tests/unit/test_calendar_service.py for conflict detection and availability checks
- [X] T036 [US2] Run quickstart.md US2 integration test (Test Scenario 2.1)

**Checkpoint**: Calendar management fully functional - can schedule meetings autonomously with conflict detection

---

## Phase 5: User Story 3 - Document Generation & Editing (Priority: P3)

**Goal**: Template-based document generation using audit log data and Jinja2 templates

**Independent Test**: Manually trigger weekly status report generation, verify document created with correct metrics from audit logs, check frontmatter metadata

### Implementation for User Story 3

- [X] T037 [P] [US3] Create Document model in src/models/document.py with version tracking and encryption support
- [X] T038 [P] [US3] Create src/services/document_service.py with Jinja2 template loading
- [X] T039 [US3] Implement template context building in document_service.py (load audit log data, meeting notes, user data)
- [X] T040 [US3] Implement document rendering with frontmatter generation in document_service.py
- [X] T041 [US3] Add document versioning logic (track previous versions) in document_service.py
- [X] T042 [US3] Create weekly-status.md.j2 template with audit log metrics placeholders
- [X] T043 [P] [US3] Create meeting-notes.md.j2 template with structured sections
- [X] T044 [P] [US3] Create monthly-summary.md.j2 template with aggregated stats
- [X] T045 [US3] Implement scheduled document generation in Company_Handbook.md scheduled_tasks
- [X] T046 [US3] Create .claude/commands/document-generator.md agent skill
- [X] T047 [US3] Integrate document generation with trust framework (auto-generate trusted document types)
- [X] T048 [US3] Create pytest tests in tests/unit/test_document_service.py for template rendering and context building
- [X] T049 [US3] Run quickstart.md US3 integration test (Test Scenario 3.1)

**Checkpoint**: Document automation functional - can generate status reports, meeting notes, summaries autonomously

---

## Phase 6: User Story 4 - Advanced Analytics & Insights (Priority: P4)

**Goal**: Weekly analytics from audit logs with productivity metrics and pattern detection

**Independent Test**: Run analytics on 30+ days of test audit logs, verify insights JSON contains metrics, patterns, and recommendations with correct calculations

### Implementation for User Story 4

- [X] T050 [P] [US4] Create Insight model in src/models/insight.py with metrics and recommendations structure
- [X] T051 [P] [US4] Create src/services/analytics_service.py with pandas DataFrame loading from audit logs
- [X] T052 [US4] Implement metrics calculation in analytics_service.py (actions per day, email volume, meeting attendance, response times)
- [X] T053 [US4] Implement pattern detection in analytics_service.py (day-of-week clustering, 3-sigma anomaly detection)
- [X] T054 [US4] Implement trust rule effectiveness analysis in analytics_service.py
- [X] T055 [US4] Implement recommendation generation based on detected patterns in analytics_service.py
- [X] T056 [US4] Add insights output to /Insights/YYYY-MM-DD.json with structured format
- [X] T057 [US4] Create weekly analytics scheduled task (Friday 5pm) in analytics_engine.py
- [X] T058 [US4] Create .claude/commands/analytics-insights.md agent skill
- [X] T059 [US4] Add high-priority insight alerting to /Needs_Action/ dashboard
- [X] T060 [US4] Create pytest tests in tests/unit/test_analytics_service.py for metrics calculations and pattern detection
- [X] T061 [US4] Run quickstart.md US4 integration test (Test Scenario 4.1)

**Checkpoint**: Analytics engine operational - weekly insights generated with actionable recommendations

---

## Phase 7: User Story 5 - Proactive Task Suggestions (Priority: P5)

**Goal**: AI-initiated task suggestions based on patterns (follow-ups, reminders, relationship maintenance)

**Independent Test**: Send important test email, wait 3+ days with no reply, verify proactive follow-up suggestion created in /Needs_Action/ with context and draft message

### Implementation for User Story 5

- [ ] T062 [P] [US5] Create ProactiveSuggestion model in src/models/proactive_suggestion.py with context and confidence scoring
- [ ] T063 [P] [US5] Create src/services/suggestion_engine.py with pattern detection logic
- [ ] T064 [US5] Implement follow-up detection in suggestion_engine.py (unanswered important emails 3+ days old)
- [ ] T065 [US5] Implement incomplete task chain detection in suggestion_engine.py (scheduled meeting but no agenda)
- [ ] T066 [US5] Implement recurring pattern detection in suggestion_engine.py (monthly expense reports)
- [ ] T067 [US5] Add suggestion volume limits (max 3 per category per day) in suggestion_engine.py
- [ ] T068 [US5] Implement opt-in/opt-out category management in Company_Handbook.md
- [ ] T069 [US5] Implement feedback learning (track dismissed suggestions) in suggestion_engine.py
- [ ] T070 [US5] Create hourly suggestion engine task in suggestion_engine.py main process
- [ ] T071 [US5] Add proactive suggestion creation to /Needs_Action/ with SUGGEST_ prefix
- [ ] T072 [US5] Create pytest tests in tests/unit/test_suggestion_engine.py for pattern detection and volume limits
- [ ] T073 [US5] Run quickstart.md US5 integration test (Test Scenario 5.1)

**Checkpoint**: Proactive suggestions working - AI initiates relevant follow-up tasks based on patterns

---

## Phase 8: User Story 6 - Meeting Attendance & Notes (Priority: P6)

**Goal**: Join video meetings, transcribe with Whisper API, generate structured notes with action items

**Independent Test**: Schedule test Zoom meeting, have AI join and record, verify transcript generated, meeting notes created with sections, action items extracted to /Needs_Action/

### Implementation for User Story 6

- [ ] T074 [P] [US6] Create MeetingNote model in src/models/meeting_note.py with transcript and action item tracking
- [ ] T075 [P] [US6] Create src/services/transcription_service.py with OpenAI Whisper API integration
- [ ] T076 [P] [US6] Create src/services/meeting_service.py with Zoom SDK integration
- [ ] T077 [US6] Implement Zoom meeting join logic in meeting_service.py with consent request
- [ ] T078 [US6] Implement audio download and upload to Whisper API in transcription_service.py
- [ ] T079 [US6] Implement transcript parsing and structured note generation in meeting_service.py
- [ ] T080 [US6] Implement action item extraction from transcript in meeting_service.py
- [ ] T081 [US6] Add action item task creation to /Needs_Action/ with meeting context
- [ ] T082 [US6] Create meeting notes file in /Meetings/YYYY-MM-DD_meeting_name.md with encryption
- [ ] T083 [US6] Integrate meeting attendance with calendar events (join 1 minute after start)
- [ ] T084 [US6] Create .claude/commands/meeting-attendant.md agent skill
- [ ] T085 [US6] Add local Whisper model fallback if API unavailable
- [ ] T086 [US6] Create pytest tests in tests/unit/test_meeting_service.py for transcript parsing and action extraction
- [ ] T087 [US6] Run quickstart.md US6 integration test (Test Scenario 6.1)

**Checkpoint**: Meeting automation complete - AI can attend meetings, transcribe, and extract action items

---

## Phase 9: User Story 7 - CRM Integration (Priority: P7)

**Goal**: Contact tracking across all interactions with relationship strength scoring and stale relationship detection

**Independent Test**: Send test email from new contact, verify contact profile auto-created in /Contacts/, manually set last_contact_date 31 days ago on VIP contact, verify stale relationship suggestion created

### Implementation for User Story 7

- [ ] T088 [P] [US7] Create Contact model in src/models/contact.py with validation against contracts/contact-schema.json
- [ ] T089 [P] [US7] Create src/services/contact_service.py with contact profile management
- [ ] T090 [US7] Implement contact auto-creation from email interactions in contact_service.py
- [ ] T091 [US7] Implement contact deduplication with fuzzywuzzy in contact_service.py (email/name matching)
- [ ] T092 [US7] Implement relationship strength calculation in contact_service.py (interaction_count * 10 - days_since_last_contact)
- [ ] T093 [US7] Implement conversation history tracking in contact profile files
- [ ] T094 [US7] Add important dates extraction from interactions in contact_service.py
- [ ] T095 [US7] Implement VIP stale relationship detection (30+ days no contact) in contact_service.py
- [ ] T096 [US7] Create follow-up suggestions for stale relationships in /Needs_Action/
- [ ] T097 [US7] Add contact data encryption for VIP contacts using encryption_service.py
- [ ] T098 [US7] Create daily CRM monitoring task in contact_service.py
- [ ] T099 [US7] Create .claude/commands/crm-manager.md agent skill
- [ ] T100 [US7] Create pytest tests in tests/unit/test_contact_service.py for deduplication and relationship scoring
- [ ] T101 [US7] Run quickstart.md US7 integration tests (Test Scenarios 7.1 and 7.2)

**Checkpoint**: CRM fully operational - contact profiles maintained, relationships tracked, follow-ups suggested

---

## Phase 10: User Story 8 - Financial Tracking (Priority: P8)

**Goal**: Expense tracking with OCR extraction from receipts and budget monitoring with alerts

**Independent Test**: Send test email with receipt PDF attachment, verify OCR extraction of amount/vendor/date, expense entity created in /Expenses/, budget checked and updated

### Implementation for User Story 8

- [X] T102 [P] [US8] Create Expense model in src/models/expense.py with OCR confidence tracking
- [X] T103 [P] [US8] Create Budget model in src/models/budget.py with monthly allocations
- [X] T104 [P] [US8] Create src/services/expense_service.py with EasyOCR integration
- [X] T105 [P] [US8] Create src/services/budget_service.py with budget tracking and alert logic
- [X] T106 [US8] Implement receipt detection in Gmail watcher for expense processing
- [X] T107 [US8] Implement OCR text extraction from receipts (PDF and images) in expense_service.py
- [X] T108 [US8] Implement expense parsing with Claude Code in expense_service.py (amount, vendor, date, category)
- [X] T109 [US8] Add category keyword matching in expense_service.py
- [X] T110 [US8] Implement budget validation in budget_service.py (check against monthly limits)
- [X] T111 [US8] Add budget threshold alerts (80% spending) to /Needs_Action/
- [X] T112 [US8] Implement unusual expense detection (3x category average) in expense_service.py
- [X] T113 [US8] Create expense entity files in /Expenses/YYYY-MM/ with encryption
- [X] T114 [US8] Update budget JSON files in /Budgets/YYYY-MM.json
- [X] T115 [US8] Create .claude/commands/expense-tracker.md agent skill
- [X] T116 [US8] Add Google Vision API fallback for low OCR confidence (<0.75)
- [X] T117 [US8] Create pytest tests in tests/unit/test_expense_service.py for OCR parsing and budget validation
- [ ] T118 [US8] Run quickstart.md US8 integration test (Test Scenario 8.1)

**Checkpoint**: Financial tracking complete - expenses auto-tracked, budgets monitored, alerts generated

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [ ] T119 [P] Create comprehensive README updates in docs/ for Gold Tier setup and usage
- [ ] T120 [P] Add Gold Tier troubleshooting guide to docs/ (trust rules, calendar quota, OCR accuracy)
- [ ] T121 [P] Create .env.example with all Gold Tier API keys (GOOGLE_CALENDAR_CREDENTIALS_PATH, OPENAI_API_KEY, ZOOM_API_KEY)
- [ ] T122 Update PM2 ecosystem.config.js with new Gold Tier processes (analytics_engine, suggestion_engine, calendar_watcher)
- [ ] T123 [P] Add performance monitoring for trust evaluation (<10ms target)
- [ ] T124 [P] Add rate limiting for Google Calendar API (1M queries/day) and Whisper API (50 req/min)
- [ ] T125 Create encryption key backup instructions in docs/
- [ ] T126 [P] Add data export functionality for GDPR compliance (FR-044)
- [ ] T127 Run full end-to-end integration test from quickstart.md (auto-reply → meeting schedule → notes → follow-up)
- [ ] T128 [P] Add feedback UI elements to entity frontmatter (thumbs up/down for suggestions, insights, actions)
- [ ] T129 Code review and refactoring for consistency across all 8 user stories
- [ ] T130 Final validation of all 12 quickstart.md test scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
  - **CRITICAL**: US1 Trust Framework (Phase 3) MUST complete before other stories can use trust evaluation
  - US2-US8 can proceed in priority order after US1
  - US4 Analytics should complete before US5 Suggestions (suggestions use insight data)
  - Other stories (US2, US3, US6, US7, US8) are independent and can be parallelized
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 Trust Framework (P1)**: MUST complete first - all other autonomous features depend on trust evaluation
- **US2 Calendar (P2)**: Can start after US1 - Independent
- **US3 Documents (P3)**: Can start after US1 - Independent (can run parallel with US2)
- **US4 Analytics (P4)**: Can start after US1 - Independent (requires 30+ days audit log history)
- **US5 Suggestions (P5)**: Should start after US4 - Uses insights data (can work with mock data for development)
- **US6 Meetings (P6)**: Can start after US1 - Independent (can run parallel with US7)
- **US7 CRM (P7)**: Can start after US1 - Independent (can run parallel with US6)
- **US8 Financial (P8)**: Can start after US1 - Independent

### Within Each User Story

- Models before services (models are dependencies for service logic)
- Services before integration (service logic tested before wiring)
- Core implementation before agent skills (skills wrap completed functionality)
- Story validation before moving to next priority

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T003, T004, T005, T006 can all run in parallel (different directories/files)

**Within Foundational (Phase 2)**:
- T009 (audit service) and T010 (handbook schema) can run in parallel

**User Story Parallelization** (after US1 Trust Framework completes):
- **Group A** (can run parallel): US2 Calendar + US3 Documents (different services, no shared dependencies)
- **Group B** (can run parallel): US6 Meetings + US7 CRM (different APIs, share Contact entity but non-blocking)
- **Sequential**: US4 Analytics → US5 Suggestions (suggestions consume analytics data)

**Within Each User Story**:
- Model creation tasks marked [P] can run in parallel (different entity files)
- Service tests can run in parallel with implementation if using TDD

---

## Parallel Example: User Story 1

```bash
# Launch model creation together:
Task T013: "Create TrustRule model in src/models/trust_rule.py"
Task T014: "Create src/services/trust_evaluator.py"

# After models complete, these can run in parallel:
Task T019: "Update audit log schema"
Task T020: "Create trust-evaluator.md agent skill"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T012) - CRITICAL BLOCKER
3. Complete Phase 3: User Story 1 Trust Framework (T013-T023)
4. **STOP and VALIDATE**: Test US1 independently with quickstart.md Test Scenario 1.1
5. **MVP DELIVERED**: Trust framework functional - 60% approval friction reduction achieved

**MVP Estimated Effort**: 8-12 hours (Setup: 1h, Foundation: 2-3h, US1: 5-8h)

### Incremental Delivery

**Week 1** (MVP):
- Setup + Foundational + US1 Trust Framework → Deploy/Demo

**Week 2-3**:
- US2 Calendar + US3 Documents → Test independently → Deploy/Demo

**Week 4**:
- US4 Analytics + US5 Suggestions → Test independently → Deploy/Demo

**Week 5-6**:
- US6 Meetings + US7 CRM (parallel development) → Test independently → Deploy/Demo

**Week 7**:
- US8 Financial → Test independently → Deploy/Demo

**Week 8**:
- Phase 11 Polish → Full validation → Final release

Each increment adds standalone value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational + US1 together** (critical path)
2. Once US1 is done (trust framework operational):
   - **Developer A**: US2 Calendar
   - **Developer B**: US3 Documents
3. After US2/US3 complete:
   - **Developer A**: US4 Analytics
   - **Developer B**: US5 Suggestions (can use mock insight data initially)
4. After analytics complete:
   - **Developer A**: US6 Meetings
   - **Developer B**: US7 CRM
5. Final developer available:
   - US8 Financial
6. All developers: Phase 11 Polish together

---

## Task Summary

**Total Tasks**: 130 tasks
- Phase 1 Setup: 6 tasks
- Phase 2 Foundational: 6 tasks (CRITICAL BLOCKER)
- Phase 3 US1 Trust Framework (P1 - MVP): 11 tasks
- Phase 4 US2 Calendar (P2): 13 tasks
- Phase 5 US3 Documents (P3): 13 tasks
- Phase 6 US4 Analytics (P4): 12 tasks
- Phase 7 US5 Suggestions (P5): 12 tasks
- Phase 8 US6 Meetings (P6): 14 tasks
- Phase 9 US7 CRM (P7): 14 tasks
- Phase 10 US8 Financial (P8): 17 tasks
- Phase 11 Polish: 12 tasks

**Parallel Opportunities**: 45 tasks marked [P] can run in parallel within their phase

**Independent Test Scenarios**: 12 scenarios defined in quickstart.md

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1 Trust Framework only) = 23 tasks

---

## Notes

- All tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks can run in parallel (different files, no dependencies)
- [Story] label maps task to user story for traceability (US1-US8)
- Each user story is independently completable and testable per quickstart.md scenarios
- US1 Trust Framework MUST complete before other stories can leverage autonomous execution
- Commit after each task or logical group for incremental validation
- Stop at any checkpoint to validate story independently
- Avoid cross-story dependencies that break independent testing
