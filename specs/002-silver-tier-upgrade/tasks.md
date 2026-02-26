# Implementation Tasks: Silver Tier - Autonomous Task Execution & Multi-Channel Communication

**Feature Branch**: `002-silver-tier-upgrade`
**Created**: 2026-02-25
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Overview

This document contains all implementation tasks for Silver Tier, organized by user story to enable independent development and testing. Each user story can be implemented as a complete, testable increment.

**Total Tasks**: 78 tasks
**Estimated Time**: 20-28 hours
**Test Approach**: Manual integration testing per user story (no unit tests generated)

---

## Phase 1: Setup & Infrastructure (1-2 hours)

**Goal**: Prepare development environment and configure dependencies for Silver Tier implementation.

**Tasks**:

- [x] T001 Update pyproject.toml to add Silver Tier dependencies (mcp, apscheduler, requests, jsonschema) via UV
- [x] T002 Run `uv sync` to install new dependencies and verify installation
- [x] T003 Update .env.example with MCP server configuration templates (GMAIL_MCP_URL, LINKEDIN_MCP_URL, FACEBOOK_MCP_URL, TWITTER_MCP_URL, WHATSAPP_MCP_URL, DRY_RUN)
- [x] T004 Create /Approved/ folder in vault structure via src/init_vault.py extension
- [x] T005 Update ecosystem.config.js to add executor, scheduler, and whatsapp-watcher PM2 process configurations
- [x] T006 Create vault state files directory structure in /Logs/ (execution_state.json, schedule_state.json, rate_limit_state.json placeholders)

**Validation**:
- `uv pip list | grep -E "(mcp|apscheduler|requests|jsonschema)"` shows all 4 packages installed
- `/Approved/` folder exists in vault
- `ecosystem.config.js` contains 5-6 process definitions (existing + new)

---

## Phase 2: Foundational Components (2-3 hours)

**Goal**: Build shared infrastructure components required by all user stories.

**Tasks**:

- [x] T007 [P] Create MCP client base class in src/services/mcp_client.py with connection management and error handling
- [x] T008 [P] Implement MCP authentication handling in mcp_client.py (token passing, refresh on 401)
- [x] T009 [P] Implement retry logic with exponential backoff in mcp_client.py (1s, 2s, 4s, 8s, max 60s, 3 max retries)
- [x] T010 [P] Create rate limiter class in src/services/rate_limiter.py using token bucket algorithm with JSON state persistence
- [x] T011 [P] Implement per-platform rate limits in rate_limiter.py (Gmail: 500/day, LinkedIn: 100/day, Twitter: 2400/day, Facebook: 200/day)
- [x] T012 [P] Create plan validator class in src/services/plan_validator.py using jsonschema library
- [x] T013 [P] Implement schema validation methods in plan_validator.py for email, social post, and scheduled task schemas
- [x] T014 Extend AuditLogger in src/services/logger_service.py to support new action types (email_send, social_post, whatsapp_detect, scheduled_task)
- [x] T015 Extend VaultService in src/services/vault_service.py with methods for new entity types (WhatsAppMessage, SocialMediaPost, ScheduledTask, ExecutionLog)

**Validation**:
- MCP client can connect to mock server, handle auth errors, and retry transient failures
- Rate limiter respects daily limits and persists state to JSON
- Plan validator successfully validates valid plans and rejects invalid ones with clear error messages
- Logger service can create audit log entries for new action types

**Dependencies**: None (foundational layer)

---

## Phase 3: User Story 1 - Email Sending & HITL Execution (P1) (6-8 hours)

**Story Goal**: Enable autonomous email sending from approved plans via Gmail API, transforming the AI Employee from passive observer to active participant.

**Independent Test Criteria**:
1. Create email reply plan in /Needs_Action/ with recipient, subject, body
2. Move plan to /Approved/ folder
3. Executor detects approval within 10 seconds
4. Email sent via Gmail MCP server within 2 minutes
5. Plan moved to /Done/ with execution metadata
6. Audit log contains email_send entry with success status
7. Dashboard shows "Emails sent today: 1"

**Tasks**:

### Models

- [x] T016 [P] [US1] Create ExecutionLog model in src/models/execution_log.py with fields (log_id, timestamp, action_type, actor, plan_id, target, parameters, approval_status, result, mcp_server, response, error, duration_ms, retry_count)
- [x] T017 [P] [US1] Implement ExecutionLog.to_json() method for JSON serialization to daily log files
- [x] T018 [P] [US1] Implement ExecutionLog.from_dict() class method for deserialization from JSON

### Services

- [x] T019 [US1] Create ExecutorService class in src/services/executor_service.py with plan processing logic
- [x] T020 [US1] Implement ExecutorService.validate_plan() method using plan_validator for email plans
- [x] T021 [US1] Implement ExecutorService.execute_email_plan() method to send emails via Gmail MCP client
- [x] T022 [US1] Implement ExecutorService.handle_execution_error() to move failed plans back to /Needs_Action/ with error details
- [x] T023 [US1] Implement ExecutorService.move_to_done() to archive successful executions with metadata
- [x] T024 [US1] Implement ExecutorService.create_execution_log() to write audit log entries to /Logs/YYYY-MM-DD.json
- [x] T025 [US1] Implement rate limiting in ExecutorService.execute_email_plan() using rate_limiter for Gmail (1 email per 5 seconds)

### Main Process

- [x] T026 [US1] Create executor.py main script with watchdog monitoring of /Approved/ folder
- [x] T027 [US1] Implement executor.py main loop to detect new plans, validate, and execute via ExecutorService
- [x] T028 [US1] Implement executor.py error handling for MCP connection failures with graceful degradation
- [x] T029 [US1] Add executor.py heartbeat logging every 60 seconds for health monitoring

### Skills

- [x] T030 [P] [US1] Create executor-skill.md in .claude/commands/ with plan execution workflow documentation
- [x] T031 [P] [US1] Document error scenarios and recovery procedures in executor-skill.md

### Extensions

- [x] T032 [US1] Extend dashboard-updater.md skill to include email execution statistics (emails sent today, last execution time, success rate)
- [x] T033 [US1] Update Dashboard.md template to show execution stats section

**Parallel Opportunities**:
- T016, T017, T018 (ExecutionLog model) can run in parallel with T019-T025 (ExecutorService)
- T030, T031 (executor-skill.md) can run in parallel with main implementation

**Acceptance**:
- Executor process starts successfully via PM2
- Approved email plan is detected within 10 seconds
- Email sent via Gmail MCP within 2 minutes
- Plan moved to /Done/ with sent message ID
- Audit log entry created in /Logs/YYYY-MM-DD.json
- Dashboard updated with "Emails sent today: N"

---

## Phase 4: User Story 2 - Social Media Auto-Posting (P2) (6-8 hours)

**Story Goal**: Enable autonomous social media posting to LinkedIn, Facebook, and Twitter from approved plans.

**Independent Test Criteria**:
1. Create social media post plan in /Needs_Action/ with platform (linkedin), content, and optional media
2. Move plan to /Approved/ folder
3. Executor processes plan and posts to LinkedIn via MCP server
4. Post URL captured and stored in plan metadata
5. Plan moved to /Done/ with platform_results showing success
6. Dashboard shows "Posts published today: 1"

**Tasks**:

### Models

- [x] T034 [P] [US2] Create SocialMediaPost model in src/models/social_media_post.py with fields (post_id, platforms, content, media_attachments, scheduled_time, status, platform_results, created_at, approved_at, posted_at, error_details)
- [x] T035 [P] [US2] Implement SocialMediaPost.validate_content_length() method to check character limits per platform (LinkedIn: 3000, Twitter: 280, Facebook: 63206)
- [x] T036 [P] [US2] Implement SocialMediaPost.needs_thread() method to detect if Twitter content requires threading (>280 chars)
- [x] T037 [P] [US2] Implement SocialMediaPost.to_yaml_frontmatter() for Markdown serialization

### Services

- [x] T038 [US2] Create SocialMediaService class in src/services/social_media_service.py with platform-specific posting logic
- [x] T039 [US2] Implement SocialMediaService.post_to_linkedin() method using LinkedIn MCP client
- [x] T040 [US2] Implement SocialMediaService.post_to_facebook() method using Facebook MCP client
- [x] T041 [US2] Implement SocialMediaService.post_to_twitter() method with thread support using Twitter MCP client
- [x] T042 [US2] Implement SocialMediaService.post_multi_platform() method to handle posting to multiple platforms sequentially
- [x] T043 [US2] Implement SocialMediaService.validate_platform_limits() to check content length before posting
- [x] T044 [US2] Implement SocialMediaService.handle_partial_failure() to update platform_results when some platforms succeed and others fail
- [x] T045 [US2] Implement rate limiting in SocialMediaService for each platform (LinkedIn: 100/day, Twitter: 2400/day, Facebook: 200/day)

### Executor Extension

- [x] T046 [US2] Extend executor.py to detect social_media_post plan type and route to SocialMediaService
- [x] T047 [US2] Extend executor.py to handle scheduled posts (skip if scheduled_time is in future)
- [x] T048 [US2] Extend ExecutorService.create_execution_log() to include social_post action type

### Skills

- [x] T049 [P] [US2] Create social-media-manager.md skill in .claude/commands/ documenting multi-platform posting workflow
- [x] T050 [P] [US2] Document platform-specific validation rules and error handling in social-media-manager.md

### Extensions

- [X] T051 [US2] Extend dashboard-updater.md to include social media execution statistics (posts published today, per-platform breakdown)
- [X] T052 [US2] Extend vault-manager.md to handle SocialMediaPost entity creation and updates

**Parallel Opportunities**:
- T034, T035, T036, T037 (SocialMediaPost model) can run in parallel with T038-T045 (SocialMediaService)
- T049, T050 (social-media-manager.md skill) can run in parallel with service implementation

**Acceptance**:
- Social media post plan approved and detected by executor
- Post successfully published to LinkedIn with URL captured
- Multi-platform post (LinkedIn + Twitter) publishes to both platforms
- Twitter thread (3 tweets) posts sequentially with correct reply chain
- Dashboard shows "Posts published today: N" with per-platform breakdown

---

## Phase 5: User Story 3 - WhatsApp Business Monitoring (P3) (3-4 hours)

**Story Goal**: Monitor WhatsApp Business API for incoming messages and create action items in the vault.

**Independent Test Criteria**:
1. Send test WhatsApp message to business number
2. WhatsApp watcher polls API every 60 seconds
3. Message detected and WhatsAppMessage entity created in /Needs_Action/ within 2 minutes
4. Entity includes sender phone, message content, timestamp
5. Priority contacts (from Company_Handbook.md) flagged as high priority
6. Dashboard shows "WhatsApp messages today: 1"

**Tasks**:

### Models

- [X] T053 [P] [US3] Create WhatsAppMessage model in src/models/whatsapp_message.py with fields (message_id, sender_phone, sender_name, message_content, timestamp, media_attachments, priority, status, created_at, processed_at)
- [X] T054 [P] [US3] Implement WhatsAppMessage.to_yaml_frontmatter() for Markdown serialization
- [X] T055 [P] [US3] Implement WhatsAppMessage.validate_phone_format() to check E.164 format (+[country][number])

### Services

- [X] T056 [US3] Create WhatsAppService class in src/services/whatsapp_service.py with message polling and processing logic
- [X] T057 [US3] Implement WhatsAppService.poll_messages() method to fetch new messages from WhatsApp MCP server
- [X] T058 [US3] Implement WhatsAppService.detect_priority_contacts() to check sender_phone against Company_Handbook.md priority_contacts list
- [X] T059 [US3] Implement WhatsAppService.download_media() to save media attachments to /Inbox/ via MCP server
- [X] T060 [US3] Implement WhatsAppService.create_message_entity() to generate WHATSAPP_[message_id].md file in /Needs_Action/
- [X] T061 [US3] Implement WhatsAppService.prevent_duplicates() using message_id tracking in processed set

### Watcher

- [X] T062 [US3] Create WhatsAppWatcher class in src/watchers/whatsapp_watcher.py extending base_watcher.py
- [X] T063 [US3] Implement WhatsAppWatcher.poll() method to call WhatsAppService.poll_messages() every 60 seconds
- [X] T064 [US3] Implement WhatsAppWatcher error handling for MCP connection failures with exponential backoff (5s, 30s, 2m)
- [X] T065 [US3] Implement WhatsAppWatcher alert creation when API is down for >10 minutes

### Skills

- [X] T066 [P] [US3] Create whatsapp-processor.md skill in .claude/commands/ documenting message processing workflow
- [X] T067 [P] [US3] Document priority contact detection and media handling in whatsapp-processor.md

### Extensions

- [X] T068 [US3] Extend dashboard-updater.md to include WhatsApp message statistics (messages received today, high priority count)
- [X] T069 [US3] Extend vault-manager.md to handle WhatsAppMessage entity creation

**Parallel Opportunities**:
- T053, T054, T055 (WhatsAppMessage model) can run in parallel with T056-T061 (WhatsAppService)
- T066, T067 (whatsapp-processor.md skill) can run in parallel with watcher implementation

**Acceptance**:
- WhatsApp watcher starts successfully via PM2
- Test message sent to business number is detected within 2 minutes
- WhatsAppMessage entity created in /Needs_Action/ with correct metadata
- Priority contact message flagged as high priority
- Media attachment (if sent) downloaded to /Inbox/ and linked in entity
- Dashboard shows "WhatsApp messages today: N"

---

## Phase 6: User Story 4 - Scheduled Tasks & Daily Briefings (P4) (4-6 hours)

**Story Goal**: Execute time-based tasks automatically such as daily briefings and weekly summaries.

**Independent Test Criteria**:
1. Configure daily briefing task in Company_Handbook.md for current time + 2 minutes
2. Scheduler detects task definition on startup
3. At scheduled time, briefing generated in /Needs_Action/
4. Briefing contains pending item count, recent completions (24h), urgent items
5. next_execution calculated for next day
6. Dashboard shows "Scheduled tasks executed today: 1"

**Tasks**:

### Models

- [X] T070 [P] [US4] Create ScheduledTask model in src/models/scheduled_task.py with fields (task_id, task_name, task_type, schedule_pattern, recurrence_rule, last_execution, next_execution, enabled, output_path, parameters, created_at, updated_at)
- [X] T071 [P] [US4] Implement ScheduledTask.calculate_next_execution() method using APScheduler CronTrigger
- [X] T072 [P] [US4] Implement ScheduledTask.to_yaml() for serialization to Company_Handbook.md

### Services

- [X] T073 [US4] Create SchedulerService class in src/services/scheduler_service.py with task management and execution logic
- [X] T074 [US4] Implement SchedulerService.load_tasks_from_handbook() to parse scheduled_tasks YAML from Company_Handbook.md
- [X] T075 [US4] Implement SchedulerService.generate_daily_briefing() to create briefing with pending items, completions, urgent items
- [X] T076 [US4] Implement SchedulerService.generate_weekly_summary() to create summary with completed tasks, time saved, metrics
- [X] T077 [US4] Implement SchedulerService.execute_custom_task() for user-defined scheduled tasks
- [X] T078 [US4] Implement SchedulerService.update_schedule_state() to persist last_execution and next_execution to vault/Logs/schedule_state.json
- [X] T079 [US4] Implement SchedulerService.handle_missed_execution() to catch up tasks missed during offline period (within 1-hour grace period)

### Main Process

- [X] T080 [US4] Create scheduler.py main script with APScheduler BackgroundScheduler initialization
- [X] T081 [US4] Implement scheduler.py to load tasks from Company_Handbook.md on startup using SchedulerService
- [X] T082 [US4] Implement scheduler.py to add jobs to APScheduler with CronTrigger based on schedule_pattern
- [X] T083 [US4] Implement scheduler.py event listeners for job execution, errors, and missed executions
- [X] T084 [US4] Implement scheduler.py to detect Company_Handbook.md changes and reload tasks without restart

### Skills

- [X] T085 [P] [US4] Create scheduler-skill.md in .claude/commands/ documenting scheduled task configuration and execution
- [X] T086 [P] [US4] Document briefing/summary generation logic and custom task parameters in scheduler-skill.md

### Extensions

- [X] T087 [US4] Extend dashboard-updater.md to include scheduled task statistics (tasks executed today, next execution time)
- [X] T088 [US4] Update Company_Handbook.md template with scheduled_tasks YAML section example

**Parallel Opportunities**:
- T070, T071, T072 (ScheduledTask model) can run in parallel with T073-T079 (SchedulerService)
- T085, T086 (scheduler-skill.md) can run in parallel with scheduler.py implementation

**Acceptance**:
- Scheduler process starts successfully via PM2
- Scheduled task configured for current time + 2 minutes executes on time
- Daily briefing generated in /Needs_Action/ with correct content
- Weekly summary includes completed task metrics
- Schedule state persisted and survives scheduler restart
- Dashboard shows "Scheduled tasks executed today: N"

---

## Phase 7: Polish & Cross-Cutting Concerns (1-2 hours)

**Goal**: Finalize integration, error handling, and documentation.

**Tasks**:

- [ ] T089 Verify all PM2 processes (executor, scheduler, whatsapp-watcher) start correctly with ecosystem.config.js
- [ ] T090 Test graceful degradation when Gmail MCP server is unavailable (other integrations continue working)
- [ ] T091 Test graceful degradation when LinkedIn MCP server is unavailable (executor handles other platforms)
- [ ] T092 Verify rate limiting works across restarts (state persisted in rate_limit_state.json)
- [ ] T093 Verify audit logs created correctly for all action types (email_send, social_post, whatsapp_detect, scheduled_task)
- [ ] T094 Verify dashboard updates reflect execution statistics within 60 seconds
- [ ] T095 Test executor handles multiple approved plans in chronological order (oldest first)
- [ ] T096 Test executor handles plans approved while offline (queue and process on startup)
- [X] T097 Create SILVER_TIER_SETUP.md documentation guide with step-by-step setup instructions
- [X] T098 Update main README.md with Silver Tier capabilities and usage

**Validation**:
- All 5-6 PM2 processes running without errors
- MCP server failures handled gracefully (no crashes, clear alerts)
- Rate limits respected across all platforms
- Audit logs complete and queryable
- Dashboard shows real-time execution statistics
- System recovers from crashes and resumes operations within 2 minutes

---

## Dependencies Between User Stories

```
Setup (Phase 1)
  ↓
Foundational (Phase 2)
  ↓
├─ US1 (P1) - Email Sending ← Can start immediately after Foundational
├─ US2 (P2) - Social Media ← Can start immediately after Foundational
├─ US3 (P3) - WhatsApp ← Can start immediately after Foundational
└─ US4 (P4) - Scheduled Tasks ← Can start immediately after Foundational
```

**Dependency Notes**:
- **US1, US2, US3, US4 are independent**: Each user story can be implemented in parallel after Foundational phase completes
- **Recommended order**: US1 → US2 → US3 → US4 (matches priority order P1-P4)
- **MVP scope**: US1 only (Email Sending & HITL Execution) delivers core Silver Tier value

---

## Parallel Execution Examples

### Foundational Phase (All parallelizable)
```bash
# Run these tasks in parallel:
- T007-T013 (MCP client, rate limiter, plan validator) - Different services
- T014, T015 (Logger and Vault service extensions) - Different files
```

### User Story 1 (Email Sending)
```bash
# Run these in parallel:
- T016-T018 (ExecutionLog model)
- T019-T025 (ExecutorService) - Depends on model being defined but can develop concurrently
- T030-T031 (executor-skill.md documentation)

# Then run sequentially:
- T026-T029 (executor.py main process) - Depends on ExecutorService
- T032-T033 (Dashboard extensions) - Depends on executor working
```

### User Story 2 (Social Media)
```bash
# Run these in parallel:
- T034-T037 (SocialMediaPost model)
- T038-T045 (SocialMediaService)
- T049-T050 (social-media-manager.md skill)

# Then run sequentially:
- T046-T048 (Executor extensions for social posts)
- T051-T052 (Dashboard and vault extensions)
```

### User Story 3 (WhatsApp)
```bash
# Run these in parallel:
- T053-T055 (WhatsAppMessage model)
- T056-T061 (WhatsAppService)
- T066-T067 (whatsapp-processor.md skill)

# Then run sequentially:
- T062-T065 (WhatsAppWatcher)
- T068-T069 (Dashboard and vault extensions)
```

### User Story 4 (Scheduled Tasks)
```bash
# Run these in parallel:
- T070-T072 (ScheduledTask model)
- T073-T079 (SchedulerService)
- T085-T086 (scheduler-skill.md)

# Then run sequentially:
- T080-T084 (scheduler.py main process)
- T087-T088 (Dashboard and handbook extensions)
```

---

## Implementation Strategy

### MVP First (Minimum Viable Product)

**MVP = User Story 1 only (Email Sending & HITL Execution)**

Tasks: T001-T033 (33 tasks, ~9-11 hours)

**MVP Delivers**:
- Email sending from approved plans
- HITL approval workflow (/Needs_Action/ → /Approved/ → /Done/)
- Gmail MCP integration
- Rate limiting
- Audit logging
- Dashboard execution statistics

**MVP Test**:
1. Create email plan in /Needs_Action/
2. Approve by moving to /Approved/
3. Verify email sent within 2 minutes
4. Check audit log entry
5. Verify dashboard updated

### Incremental Delivery

**Iteration 1**: MVP (US1) - Weeks 1
**Iteration 2**: US1 + US2 (Social Media) - Week 2
**Iteration 3**: US1 + US2 + US3 (WhatsApp) - Week 2
**Iteration 4**: US1 + US2 + US3 + US4 (Full Silver Tier) - Week 3

Each iteration delivers working, testable functionality.

---

## Task Summary

**Total Tasks**: 98
**By Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 9 tasks
- Phase 3 (US1): 18 tasks
- Phase 4 (US2): 19 tasks
- Phase 5 (US3): 17 tasks
- Phase 6 (US4): 19 tasks
- Phase 7 (Polish): 10 tasks

**By User Story**:
- US1 (P1 - Email Sending): 18 tasks (6-8 hours)
- US2 (P2 - Social Media): 19 tasks (6-8 hours)
- US3 (P3 - WhatsApp): 17 tasks (3-4 hours)
- US4 (P4 - Scheduled Tasks): 19 tasks (4-6 hours)

**Parallelizable Tasks**: 41 tasks marked with [P] (42% of total)

**Independent Test Criteria**: 4 (one per user story)

**Suggested MVP**: US1 only (33 tasks including setup/foundational, ~9-11 hours)

---

## Format Validation

✅ All tasks follow checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
✅ Task IDs sequential (T001-T098)
✅ [P] marker on parallelizable tasks
✅ [US1]-[US4] labels on user story tasks
✅ Clear file paths in descriptions
✅ Setup/Foundational/Polish phases have no story labels

---

**Tasks Status**: ✅ **READY FOR IMPLEMENTATION**

**Next Step**: Run `/sp.implement` to begin execution, or manually start with Phase 1 tasks.
