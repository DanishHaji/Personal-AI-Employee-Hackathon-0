---
id: 0002
title: Platinum Tier Implementation Plan
stage: plan
date: 2026-03-04
surface: agent
model: claude-sonnet-4-5
feature: 004-platinum-tier-upgrade
branch: 004-platinum-tier-upgrade
user: DanishHaji
command: /sp.plan
labels: ["platinum-tier", "planning", "cloud-deployment", "vault-sync", "health-monitoring", "odoo-integration"]
links:
  spec: specs/004-platinum-tier-upgrade/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/004-platinum-tier-upgrade/plan.md
 - specs/004-platinum-tier-upgrade/research.md
 - specs/004-platinum-tier-upgrade/data-model.md
 - specs/004-platinum-tier-upgrade/quickstart.md
 - specs/004-platinum-tier-upgrade/contracts/vault_sync_api.md
 - specs/004-platinum-tier-upgrade/contracts/claim_manager_api.md
 - specs/004-platinum-tier-upgrade/contracts/health_monitor_api.md
 - specs/004-platinum-tier-upgrade/contracts/odoo_mcp_api.md
tests:
 - Research validation (5 technical decisions researched and documented)
 - Data model completeness (9 entities with schemas and state machines)
 - Contract specification (4 API contracts with error handling)
 - Constitution compliance (7/7 principles verified)
---

## Prompt

User executed `/sp.plan` command after completing specification with `/sp.specify`.

**Context**:
- Platinum Tier specification created and validated (14/14 checklist criteria passed)
- User requested to continue work after Odoo discussion ("thek hai phir rehne do, acha chalo hum platinium tier ki tarf move karty hain")
- User confirmed to read root constitution document for requirements ("document parh lena jo root file me hai us k mutabiq platinium tier par kaam karna hai")
- Previous conversation: Completed Gold Tier implementation and testing with comprehensive test vault

**Requirements from Constitution**:
- 24/7 Cloud VM deployment with always-on watchers and health monitoring
- Work-Zone Specialization (Cloud: triage/drafts, Local: approvals/sensitive actions)
- Delegation via synced vault (Git/Syncthing) with claim-by-move rule
- Security rule: Secrets never sync (Cloud never has WhatsApp sessions/banking creds)
- Cloud-hosted Odoo Community with HTTPS, backups, health monitoring

**Goal**: Create complete implementation plan with technical decisions, architecture, contracts, and quickstart guide.

## Response snapshot

Successfully completed comprehensive Platinum Tier implementation plan:

### Phase 0: Research (Completed)

Researched and documented 5 critical technical decisions:

1. **Vault Sync: Git (with Secret Filtering)**
   - Rationale: Built-in version control, mature conflict resolution, excellent for text-heavy Markdown vaults
   - Tools: `detect-secrets` + `gitleaks` pre-commit hooks
   - Alternative rejected: Syncthing (data loss issues with multi-device setups, no version history)

2. **Cloud Deployment: systemd with WatchdogSec**
   - Rationale: Native Ubuntu 22.04 integration, built-in auto-restart, resource limits, journald logging
   - Implementation: systemd services with Type=notify and WatchdogSec=90s
   - Alternative rejected: Supervisor (redundant), Docker (overkill for single app)

3. **Odoo Integration: JSON-2 API (not XML-RPC)**
   - Rationale: XML-RPC deprecated and will be removed in Odoo 20 (Fall 2026)
   - Modern JSON-RPC with Bearer token authentication
   - MCP server pattern for clean abstraction

4. **Work-Zone Routing: File-Based Claim Pattern**
   - Rationale: Aligns with file-based architecture, Git automatically detects simultaneous claims via merge conflicts
   - TTL-based expiration (15 minutes), human-readable Markdown + YAML
   - Alternative rejected: Redis locks (requires database, violates constitution)

5. **Health Monitoring: psutil + systemd-watchdog**
   - Rationale: Industry-standard process monitoring, native systemd integration, lightweight compared to full monitoring stacks
   - Implementation: HealthMonitor + AlertManager with custom email/webhook alerts
   - Alternative rejected: Prometheus/Grafana (too heavy for single-instance deployment)

### Phase 1: Design & Contracts (Completed)

**Data Model** (9 entities defined):
- Work Zone Configuration
- Sync Event (JSONL log)
- Sync Conflict
- Claim (advisory lock with TTL)
- Health Status (snapshots every 5 min)
- Cloud Draft
- Odoo Entry (synced to Odoo database)
- Secret Filter Rule (.gitignore patterns)
- Delegation Metadata (embedded in task entities)

**API Contracts** (4 contracts specified):

1. **VaultSyncService** (`vault_sync_api.md`):
   - `sync(direction)` → SyncResult
   - `filter_secrets()` → List[str]
   - `resolve_conflict(conflict_id, strategy)` → None
   - Pre-commit hook integration with detect-secrets
   - Systemd timer (every 5 minutes)

2. **ClaimManager** (`claim_manager_api.md`):
   - `claim_task(task_id, zone)` → Claim
   - `release_claim(claim_id, zone)` → None
   - `check_claim(task_id)` → Optional[Claim]
   - `route_task(task_id, task_file, action_type)` → str
   - `delegate_to_local(task_id, reason)` → None
   - Claim lifecycle with 15-minute TTL, first-to-sync wins on conflicts

3. **HealthMonitor** (`health_monitor_api.md`):
   - `collect_health_snapshot()` → HealthStatus
   - `check_watcher_health(watcher_name)` → WatcherHealth
   - `start_watchdog()` → None (background process)
   - `restart_watcher(watcher_name)` → bool
   - Max 3 restart attempts, exponential backoff, critical alerts after 3 failures

4. **Odoo MCP Server** (`odoo_mcp_api.md`):
   - `odoo_create_expense(expense_id, amount, category, vendor, date)` → {success, odoo_entry_id}
   - `odoo_get_budget_status(category, month)` → {budget_limit, spent, remaining, status}
   - `odoo_generate_financial_report(report_type, month)` → {total_expenses, categories, compliance}
   - JSON-2 API with Bearer token auth, category mapping (cloud_services→15, software→16, etc.)

**Quickstart Guide** (5 implementation phases):
- Phase 1: Vault Sync (8-10 hours) - Git setup, secret filtering, conflict resolution
- Phase 2: Work-Zone Specialization (12-15 hours) - Claims, routing, delegation
- Phase 3: Cloud Deployment (10-12 hours) - VM provisioning, systemd services, health monitoring
- Phase 4: Odoo Integration (8-10 hours) - Odoo installation, HTTPS setup, MCP server
- Phase 5: Offline Resilience (6-8 hours) - Offline queueing, escalation alerts
- End-to-end test scenario: Email arrives while Local offline → Cloud drafts → Local approves → send

**Implementation Plan** (plan.md):
- Technical Context: Python 3.12+, Git, systemd, psutil, detect-secrets, httpx, file-based storage
- Constitution Check: ✅ All 7 principles verified (Local-First Privacy, No Database, Trust Framework, etc.)
- Project Structure: Extends Gold Tier with new services (vault_sync, claim_manager, health_monitor), vault folders (Cloud_Drafts/, Needs_Local/, Claims/, Health/), MCP server (odoo/)
- Testing Strategy: 80%+ coverage, unit/integration/contract/acceptance tests per phase
- Deployment: cloud-deploy.sh automated script, systemd services, Odoo with Let's Encrypt HTTPS
- Risk Analysis: 7 risks identified (secret leak, sync conflicts, resource exhaustion, Odoo corruption, local offline, Git failure, claim conflicts) with mitigation and contingency
- ADR Candidates: Git vs Syncthing, file-based claims vs Redis, systemd vs Docker, JSON-2 vs XML-RPC

**Total Implementation Estimate**: 44-55 hours (within 60-hour Platinum scope)

## Outcome

- ✅ Impact: Complete implementation plan created with research, data model, 4 API contracts, quickstart guide, and deployment strategy. All technical unknowns resolved. Constitutional compliance verified. Ready for task generation.
- 🧪 Tests: Research validation (5 decisions), data model completeness (9 entities), contract specification (4 APIs), constitution compliance (7/7 principles)
- 📁 Files: plan.md (683 lines), research.md, data-model.md (500+ lines), quickstart.md (500+ lines), 4 contract files (vault_sync, claim_manager, health_monitor, odoo_mcp)
- 🔁 Next prompts: `/sp.tasks` to generate detailed implementation tasks from plan, or `/sp.adr` to document architectural decisions (Git vs Syncthing, file-based claims, systemd choice, Odoo API choice)
- 🧠 Reflection: Platinum Tier represents significant architectural complexity (distributed system vs Gold Tier's single machine). Key innovations: work-zone specialization enables 24/7 operation while maintaining security (secrets never leave local), file-based claim pattern aligns with constitutional no-database principle, Git merge detection naturally handles concurrent claims. Research phase critical to resolving 5 major technology choices upfront.

## Evaluation notes (flywheel)

- Failure modes observed: None - planning completed successfully with all technical decisions resolved through research
- Graders run and results (PASS/FAIL): Constitution compliance - PASS (7/7 principles), Data model completeness - PASS (9 entities with state machines), Contract specification - PASS (4 APIs with error handling)
- Prompt variant (if applicable): N/A - initial planning
- Next experiment (smallest change to try): Generate tasks with `/sp.tasks` and validate implementation complexity estimates (44-55 hours) against actual task breakdown. Consider running `/sp.adr` for 4 significant decisions before implementation starts.
