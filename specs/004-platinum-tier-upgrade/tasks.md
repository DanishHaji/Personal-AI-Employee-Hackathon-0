# Tasks: Platinum Tier - Always-On Cloud + Local Executive

**Input**: Design documents from `/specs/004-platinum-tier-upgrade/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all complete)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Note**: Tests are OPTIONAL and not included per spec.md requirements (Platinum spec doesn't require TDD).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify Gold Tier (003-gold-tier-upgrade) fully implemented and tested
- [ ] T002 Create deployment directory structure at deployment/
- [ ] T003 [P] Create new vault folders: vault/Cloud_Drafts/, vault/Needs_Local/, vault/Claims/, vault/Health/
- [ ] T004 [P] Install system dependencies: pip install psutil systemd-watchdog detect-secrets pre-commit httpx

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Initialize Git repository in vault/ directory with git init and initial commit
- [ ] T006 Configure .gitignore patterns for secrets in vault/.gitignore (see data-model.md Entity 8)
- [ ] T007 [P] Setup pre-commit hooks with detect-secrets in .pre-commit-config.yaml
- [ ] T008 [P] Create work zone configuration in vault/Company_Handbook.md (work_zones section)
- [ ] T009 [P] Create routing rules configuration in vault/Company_Handbook.md (routing_rules section)
- [ ] T010 Install pre-commit hooks with pre-commit install command

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: US2 - Vault Synchronization (Priority: P2) 🎯 FOUNDATION

**Goal**: Enable Git-based vault sync with secret filtering (MUST implement first - foundational for all other stories)

**Independent Test**: Create .env file locally, sync to remote, verify secrets filtered out. Create file on cloud, verify syncs to local.

**Why First**: Vault sync is the communication backbone between Cloud and Local zones. Without it, distributed operation is impossible.

### Implementation for US2

- [ ] T011 [P] [US2] Create SyncResult dataclass in src/services/vault_sync_service.py
- [ ] T012 [P] [US2] Create SyncConflict dataclass in src/services/vault_sync_service.py
- [ ] T013 [US2] Implement VaultSyncService.__init__() with vault path and Git config in src/services/vault_sync_service.py
- [ ] T014 [US2] Implement VaultSyncService.filter_secrets() method using detect-secrets in src/services/vault_sync_service.py
- [ ] T015 [US2] Implement VaultSyncService.sync(direction="pull") with Git pull logic in src/services/vault_sync_service.py
- [ ] T016 [US2] Implement VaultSyncService.sync(direction="push") with secret filtering in src/services/vault_sync_service.py
- [ ] T017 [US2] Implement VaultSyncService.sync(direction="bidirectional") combining pull+push in src/services/vault_sync_service.py
- [ ] T018 [US2] Implement conflict detection logic in sync() method in src/services/vault_sync_service.py
- [ ] T019 [US2] Implement VaultSyncService.resolve_conflict() method with keep_local/keep_cloud/keep_both strategies in src/services/vault_sync_service.py
- [ ] T020 [US2] Add sync event logging to vault/Logs/sync.jsonl in src/services/vault_sync_service.py
- [ ] T021 [US2] Add conflict logging to vault/Logs/sync_conflicts.jsonl in src/services/vault_sync_service.py
- [ ] T022 [US2] Create systemd service file at deployment/systemd/vault-sync.service
- [ ] T023 [US2] Create systemd timer file at deployment/systemd/vault-sync.timer (5-minute interval)
- [ ] T024 [US2] Add CLI interface for manual sync with python -m src.services.vault_sync_service sync --direction bidirectional

**US2 Acceptance Test Tasks**:

- [ ] T025 [US2] Manual test: Create .env file, attempt sync, verify secret blocked and logged in sync.jsonl
- [ ] T026 [US2] Manual test: Create non-sensitive file on local, sync to remote, verify received
- [ ] T027 [US2] Manual test: Simulate conflict by editing same file on cloud and local, verify both versions preserved
- [ ] T028 [US2] Manual test: Verify sync completes in <30 seconds with 10 files changed

**Checkpoint**: Vault sync operational - Cloud and Local can now coordinate

---

## Phase 4: US1 - Work-Zone Specialization (Priority: P1) 🎯 CORE FEATURE

**Goal**: Implement Cloud-Local routing and claim management enabling 24/7 operation

**Independent Test**: Send email to cloud instance while local offline, verify cloud drafts response, bring local online, verify draft moves to Pending_Approval

**Why After US2**: Requires vault sync to coordinate between Cloud and Local zones

### Implementation for US1

- [ ] T029 [P] [US1] Create Claim dataclass in src/services/claim_manager.py
- [ ] T030 [P] [US1] Create RoutingRule dataclass in src/services/claim_manager.py
- [ ] T031 [US1] Implement ClaimManager.__init__() with vault path in src/services/claim_manager.py
- [ ] T032 [US1] Implement ClaimManager.claim_task() method with TTL and Git commit in src/services/claim_manager.py
- [ ] T033 [US1] Implement ClaimManager.release_claim() method deleting claim file in src/services/claim_manager.py
- [ ] T034 [US1] Implement ClaimManager.check_claim() with expiry checking in src/services/claim_manager.py
- [ ] T035 [US1] Implement ClaimManager.auto_expire_claims() background task in src/services/claim_manager.py
- [ ] T036 [US1] Implement ClaimManager.route_task() using Company_Handbook routing rules in src/services/claim_manager.py
- [ ] T037 [US1] Implement ClaimManager.delegate_to_local() moving files to Needs_Local/ in src/services/claim_manager.py
- [ ] T038 [US1] Add claim logging to audit trail in src/services/claim_manager.py
- [ ] T039 [US1] Update Executor to check claims before processing tasks in src/services/executor_service.py
- [ ] T040 [US1] Update Executor to route tasks based on work zone in src/services/executor_service.py
- [ ] T041 [US1] Add CloudDraft entity creation in vault/Cloud_Drafts/ when cloud drafts responses in src/services/executor_service.py
- [ ] T042 [US1] Add logic to detect cloud drafts and move to Pending_Approval on local instance in src/services/executor_service.py
- [ ] T043 [US1] Create systemd service for claim expiry task at deployment/systemd/claim-expiry.service (runs every 1 minute)
- [ ] T044 [US1] Add delegation metadata to task YAML frontmatter when delegating in src/services/claim_manager.py

**US1 Acceptance Test Tasks**:

- [ ] T045 [US1] Manual test: Cloud instance processes email, verify draft created in Cloud_Drafts/
- [ ] T046 [US1] Manual test: Local instance detects cloud draft, verify moved to Pending_Approval/
- [ ] T047 [US1] Manual test: Create WhatsApp task, verify cloud delegates to Needs_Local/
- [ ] T048 [US1] Manual test: Verify cloud never accesses local-only secrets (WhatsApp, banking)
- [ ] T049 [US1] Manual test: Both instances online, verify work distributed correctly by zone

**Checkpoint**: Work-zone specialization functional - Cloud drafts, Local approves/executes

---

## Phase 5: US3 - Cloud Deployment & Health Monitoring (Priority: P3)

**Goal**: Deploy to Cloud VM with 24/7 operation and health monitoring ensuring always-on availability

**Independent Test**: Deploy to cloud VM, stop a watcher process, verify watchdog detects and auto-restarts within 60 seconds

**Why After US1**: Requires work-zone specialization to know what cloud instance should monitor

### Implementation for US3

- [ ] T050 [P] [US3] Create HealthStatus dataclass in src/services/health_monitor.py
- [ ] T051 [P] [US3] Create WatcherHealth dataclass in src/services/health_monitor.py
- [ ] T052 [P] [US3] Create ResourceMetrics dataclass in src/services/health_monitor.py
- [ ] T053 [P] [US3] Create HealthReport dataclass in src/services/health_monitor.py
- [ ] T054 [US3] Implement HealthMonitor.__init__() with thresholds and psutil setup in src/services/health_monitor.py
- [ ] T055 [US3] Implement HealthMonitor.collect_health_snapshot() gathering metrics in src/services/health_monitor.py
- [ ] T056 [US3] Implement HealthMonitor.check_watcher_health() for individual watcher PID checks in src/services/health_monitor.py
- [ ] T057 [US3] Implement HealthMonitor.start_watchdog() main monitoring loop in src/services/health_monitor.py
- [ ] T058 [US3] Implement HealthMonitor.restart_watcher() via systemctl restart in src/services/health_monitor.py
- [ ] T059 [US3] Implement HealthMonitor.generate_daily_report() aggregating 24h snapshots in src/services/health_monitor.py
- [ ] T060 [US3] Add health snapshot saving to vault/Health/{instance}_{timestamp}.health.json in src/services/health_monitor.py
- [ ] T061 [US3] Add systemd watchdog notification with sd_notify("WATCHDOG=1") in src/services/health_monitor.py
- [ ] T062 [P] [US3] Create AlertManager class with email and webhook support in src/services/health_monitor.py
- [ ] T063 [P] [US3] Implement AlertManager.send_alert() with rate limiting in src/services/health_monitor.py
- [ ] T064 [P] [US3] Implement AlertManager.check_disk_space() with auto log rotation in src/services/health_monitor.py
- [ ] T065 [US3] Create systemd service file for health monitor at deployment/systemd/health-monitor.service
- [ ] T066 [US3] Create systemd service file for Gmail watcher at deployment/systemd/gmail-watcher.service
- [ ] T067 [US3] Create systemd service file for filesystem watcher at deployment/systemd/filesystem-watcher.service
- [ ] T068 [US3] Create cloud deployment script at deployment/cloud-deploy.sh
- [ ] T069 [US3] Add dependency installation to cloud-deploy.sh (Python, Git, systemd-dev)
- [ ] T070 [US3] Add systemd service setup to cloud-deploy.sh (copy files, enable, start)
- [ ] T071 [US3] Add environment configuration to cloud-deploy.sh (create .env.cloud)
- [ ] T072 [US3] Add vault Git clone to cloud-deploy.sh
- [ ] T073 [US3] Add health check verification to cloud-deploy.sh

**US3 Acceptance Test Tasks**:

- [ ] T074 [US3] Manual test: Run cloud-deploy.sh on test VM, verify all services start successfully
- [ ] T075 [US3] Manual test: Stop gmail-watcher.service, verify watchdog restarts within 60s
- [ ] T076 [US3] Manual test: Check vault/Health/ snapshots generated every 5 minutes
- [ ] T077 [US3] Manual test: Monitor Cloud VM for 7 days, verify 99%+ uptime
- [ ] T078 [US3] Manual test: Send email, verify Cloud instance detects within 1 minute

**Checkpoint**: Cloud deployment operational - 24/7 monitoring and auto-recovery active

---

## Phase 6: US6 - Always-On Watchers (Priority: P6)

**Goal**: Watchers running 24/7 on Cloud instance with real-time monitoring for continuous event detection

**Independent Test**: Deploy Gmail watcher to Cloud VM, send test email, verify detection within 1 minute

**Why After US3**: Requires cloud deployment infrastructure and health monitoring

### Implementation for US6

- [ ] T079 [US6] Update Gmail watcher to run continuously (24/7 mode) in src/watchers/gmail_watcher.py
- [ ] T080 [US6] Add exponential backoff on Gmail API errors in src/watchers/gmail_watcher.py
- [ ] T081 [US6] Update filesystem watcher for cloud drop folder monitoring in src/watchers/filesystem_watcher.py
- [ ] T082 [US6] Add watcher PID logging to vault/Logs/health.jsonl on startup in src/watchers/gmail_watcher.py
- [ ] T083 [US6] Add event counting metrics to watcher processes in src/watchers/gmail_watcher.py
- [ ] T084 [US6] Add error rate tracking to watcher processes in src/watchers/gmail_watcher.py
- [ ] T085 [US6] Add priority detection for urgent events (high-priority emails) in src/watchers/gmail_watcher.py
- [ ] T086 [US6] Verify WhatsApp watcher marked local-only (never runs on cloud) in src/watchers/whatsapp_watcher.py
- [ ] T087 [US6] Add watcher configuration file at config/watchers.yaml with TTLs and retry settings
- [ ] T088 [US6] Add weekly health report generation for watcher statistics in src/services/health_monitor.py

**US6 Acceptance Test Tasks**:

- [ ] T089 [US6] Manual test: Gmail watcher detects email within 1 minute on Cloud VM
- [ ] T090 [US6] Manual test: Filesystem watcher processes cloud drop folder file
- [ ] T091 [US6] Manual test: Check 7-day health report showing watcher uptime and event counts
- [ ] T092 [US6] Manual test: Trigger Gmail API rate limit, verify watcher backs off correctly
- [ ] T093 [US6] Manual test: Verify WhatsApp watcher never starts on Cloud instance

**Checkpoint**: Always-on watchers operational - Cloud instance detects events 24/7

---

## Phase 7: US5 - Odoo Integration (Priority: P5)

**Goal**: Cloud-hosted Odoo accounting with expense sync for professional financial management

**Independent Test**: Deploy Odoo to cloud VM, create expense via AI Employee, verify syncs to Odoo within 2 minutes

**Why After US3**: Requires cloud VM deployment for Odoo hosting

### Implementation for US5

- [ ] T094 [US5] Create Odoo MCP server structure at mcp-servers/odoo/server.py
- [ ] T095 [US5] Implement Odoo authentication with Bearer token in mcp-servers/odoo/server.py
- [ ] T096 [US5] Implement odoo_create_expense tool in mcp-servers/odoo/server.py
- [ ] T097 [US5] Implement odoo_get_budget_status tool in mcp-servers/odoo/server.py
- [ ] T098 [US5] Implement odoo_generate_financial_report tool in mcp-servers/odoo/server.py
- [ ] T099 [US5] Implement odoo_sync_all_expenses batch sync tool in mcp-servers/odoo/server.py
- [ ] T100 [US5] Implement odoo_backup_database tool in mcp-servers/odoo/server.py
- [ ] T101 [US5] Create category mapping configuration in mcp-servers/odoo/config.json
- [ ] T102 [US5] Add vendor lookup/creation logic in mcp-servers/odoo/server.py
- [ ] T103 [US5] Add expense sync logging to vault/Logs/odoo_sync.jsonl
- [ ] T104 [US5] Create Odoo installation script at deployment/install-odoo.sh
- [ ] T105 [US5] Add PostgreSQL setup to install-odoo.sh
- [ ] T106 [US5] Add Odoo Community Edition clone to install-odoo.sh
- [ ] T107 [US5] Add Odoo systemd service file at deployment/systemd/odoo.service
- [ ] T108 [US5] Create nginx configuration for Odoo HTTPS at deployment/nginx/odoo.conf
- [ ] T109 [US5] Add Let's Encrypt SSL setup script at deployment/setup-ssl.sh
- [ ] T110 [US5] Create daily backup script at deployment/scripts/backup-odoo.sh
- [ ] T111 [US5] Add cron job for daily backups in deployment/cron/odoo-backup.cron
- [ ] T112 [US5] Update expense service to sync approved expenses to Odoo in src/services/expense_service.py
- [ ] T113 [US5] Add budget warning detection from Odoo in src/services/expense_service.py
- [ ] T114 [US5] Add monthly financial report generation job in src/scheduler.py

**US5 Acceptance Test Tasks**:

- [ ] T115 [US5] Manual test: Deploy Odoo to Cloud VM, access via HTTPS, login successfully
- [ ] T116 [US5] Manual test: Create expense via AI Employee, verify syncs to Odoo within 2 minutes
- [ ] T117 [US5] Manual test: Check Odoo accounting dashboard shows correct expense entry
- [ ] T118 [US5] Manual test: Trigger budget warning in Odoo, verify AI Employee creates alert in Needs_Action/
- [ ] T119 [US5] Manual test: Generate monthly financial report, verify saved to vault/Documents/
- [ ] T120 [US5] Manual test: Run backup script, verify Odoo database backed up successfully

**Checkpoint**: Odoo integration operational - Financial tracking syncs to professional accounting system

---

## Phase 8: US4 - Offline Resilience (Priority: P4)

**Goal**: Cloud and Local operate independently when disconnected with queue-based delegation

**Independent Test**: Disconnect network, have Cloud queue 10 actions, reconnect, verify Local claims and processes all queued work

**Why After US1+US2**: Requires vault sync and work-zone delegation

### Implementation for US4

- [ ] T121 [US4] Add offline queueing to VaultSyncService in src/services/vault_sync_service.py
- [ ] T122 [US4] Create vault/Sync_Queue/ directory for pending changes
- [ ] T123 [US4] Implement queue management on sync failure in src/services/vault_sync_service.py
- [ ] T124 [US4] Add automatic sync resumption on network restore in src/services/vault_sync_service.py
- [ ] T125 [US4] Implement escalation alert for Local offline >24 hours in src/services/health_monitor.py
- [ ] T126 [US4] Add backup email notification channel for escalations in src/services/health_monitor.py
- [ ] T127 [US4] Add conflict resolution for simultaneous claim conflicts in src/services/claim_manager.py
- [ ] T128 [US4] Implement earliest timestamp wins strategy for claim conflicts in src/services/claim_manager.py
- [ ] T129 [US4] Add offline period logging to vault/Logs/sync.jsonl
- [ ] T130 [US4] Add isolated mode operation for prolonged sync failures in src/services/vault_sync_service.py

**US4 Acceptance Test Tasks**:

- [ ] T131 [US4] Manual test: Disconnect Cloud VM network, queue 10 drafts, reconnect, verify all synced
- [ ] T132 [US4] Manual test: Local offline 26 hours, verify Cloud sends escalation email
- [ ] T133 [US4] Manual test: Simultaneous claim conflict, verify earliest timestamp wins
- [ ] T134 [US4] Manual test: 24-hour network outage, verify zero data loss on reconnect
- [ ] T135 [US4] Manual test: Local processes approval backlog after coming online from 6-hour offline

**Checkpoint**: Offline resilience operational - System handles disconnections gracefully

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T136 [P] Update vault/Company_Handbook.md with Platinum Tier work zone documentation
- [ ] T137 [P] Create deployment README at deployment/README.md with setup instructions
- [ ] T138 [P] Add secret detection validation script at deployment/scripts/validate-secrets.sh
- [ ] T139 [P] Create troubleshooting guide at docs/troubleshooting-platinum.md
- [ ] T140 [P] Add monitoring dashboard documentation at docs/monitoring.md
- [ ] T141 Update vault/Dashboard.md to show Cloud/Local status and last sync time
- [ ] T142 Add Cloud/Local instance identification to all log entries
- [ ] T143 Code cleanup: remove debug logging, add production-ready error messages
- [ ] T144 Performance optimization: verify sync completes in <30s for 95% of cases
- [ ] T145 Security audit: verify no secrets in Cloud VM vault/, check .gitignore patterns
- [ ] T146 Run complete end-to-end test from quickstart.md (email while local offline scenario)
- [ ] T147 Verify all acceptance criteria from spec.md (SC-001 through SC-010)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **US2 Vault Sync (Phase 3)**: Depends on Foundational - MUST complete first (foundation for distributed operation)
- **US1 Work-Zone (Phase 4)**: Depends on US2 completion - Core feature enabling Cloud/Local specialization
- **US3 Cloud Deploy (Phase 5)**: Depends on US1 completion - Deploys cloud instance with work-zone routing
- **US6 Always-On Watchers (Phase 6)**: Depends on US3 completion - Requires cloud deployment infrastructure
- **US5 Odoo Integration (Phase 7)**: Depends on US3 completion - Requires cloud VM for Odoo hosting
- **US4 Offline Resilience (Phase 8)**: Depends on US1+US2 completion - Builds on vault sync and delegation
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### Critical Path

```
Setup → Foundational → US2 (Vault Sync) → US1 (Work-Zone) → US3 (Cloud Deploy) → US6/US5/US4 (parallel) → Polish
```

### User Story Dependencies

- **US2 (P2 - Vault Sync)**: FOUNDATION - Must complete first, no dependencies
- **US1 (P1 - Work-Zone)**: Depends on US2 (needs vault sync for coordination)
- **US3 (P3 - Cloud Deploy)**: Depends on US1 (needs work-zone routing for deployment)
- **US6 (P6 - Watchers)**: Depends on US3 (needs cloud infrastructure)
- **US5 (P5 - Odoo)**: Depends on US3 (needs cloud VM)
- **US4 (P4 - Offline)**: Depends on US1+US2 (needs sync and delegation)

### Parallel Opportunities After US3

Once US3 (Cloud Deployment) is complete, these can proceed in parallel:
- US6 (Always-On Watchers) - Different files from US5/US4
- US5 (Odoo Integration) - Different files from US6/US4
- US4 (Offline Resilience) - Different files from US5/US6

---

## Implementation Strategy

### Recommended Order (Sequential)

1. **Phase 1**: Setup (T001-T004)
2. **Phase 2**: Foundational (T005-T010)
3. **Phase 3**: US2 - Vault Sync (T011-T028) - CRITICAL FOUNDATION
4. **Phase 4**: US1 - Work-Zone (T029-T049) - CORE FEATURE
5. **Phase 5**: US3 - Cloud Deploy (T050-T078) - ENABLES 24/7
6. **Phase 6**: US6 - Watchers (T079-T093) - COMPLETES 24/7
7. **Phase 7**: US5 - Odoo (T094-T120) - ADDS ACCOUNTING
8. **Phase 8**: US4 - Offline (T121-T135) - ADDS RESILIENCE
9. **Phase 9**: Polish (T136-T147)

### MVP Delivery (Minimum Viable Platinum)

For fastest path to 24/7 operation:
1. Setup + Foundational (T001-T010)
2. US2 Vault Sync (T011-T028)
3. US1 Work-Zone (T029-T049)
4. US3 Cloud Deploy (T050-T078)
5. **STOP and VALIDATE**: Test complete email-while-offline scenario

This delivers core Platinum value: 24/7 cloud operation with local control

### Parallel Team Strategy

With 3 developers after US3 completion:
- Developer A: US6 (Watchers) - Files: src/watchers/*, config/watchers.yaml
- Developer B: US5 (Odoo) - Files: mcp-servers/odoo/*, deployment/install-odoo.sh
- Developer C: US4 (Offline) - Files: src/services/vault_sync_service.py, src/services/claim_manager.py

---

## Total Task Count

- **Setup**: 4 tasks
- **Foundational**: 6 tasks
- **US2 (Vault Sync)**: 18 tasks
- **US1 (Work-Zone)**: 21 tasks
- **US3 (Cloud Deploy)**: 29 tasks
- **US6 (Watchers)**: 15 tasks
- **US5 (Odoo)**: 27 tasks
- **US4 (Offline)**: 15 tasks
- **Polish**: 12 tasks

**Total**: 147 tasks

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability (US1-US6)
- US2 (Vault Sync) MUST be implemented first despite P2 priority - it's the foundation for distributed operation
- Each user story has acceptance test tasks for independent validation
- No unit tests included per spec.md (Platinum spec doesn't require TDD)
- All tasks include specific file paths for clarity
- Cloud deployment tasks require Ubuntu 22.04 VM with 2 CPU, 4GB RAM, 50GB disk
- Security validation (T145) is CRITICAL - must verify zero secrets on Cloud VM
- End-to-end test (T146) validates complete Platinum Tier functionality
