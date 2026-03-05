# Feature Specification: Platinum Tier - Always-On Cloud + Local Executive

**Feature Branch**: `004-platinum-tier-upgrade`
**Created**: 2026-03-04
**Status**: Draft
**Input**: User description: "Platinum Tier - Always-On Cloud + Local Executive with 24/7 deployment, work-zone specialization (Cloud for triage/drafts, Local for approvals/sensitive actions), vault syncing via Git/Syncthing, and complete security separation ensuring secrets never leave local machine"

## Overview

Platinum Tier transforms the Personal AI Employee into a distributed, always-available system that operates 24/7 through intelligent work-zone specialization. While the Cloud instance handles routine triage and drafts responses continuously, the Local instance maintains control over sensitive approvals and secret-dependent actions, with seamless vault synchronization ensuring both zones work in harmony.

**Tier Progression**:
- **Bronze Tier**: Monitoring & Planning (read-only)
- **Silver Tier**: Execution with HITL approval (every action requires approval)
- **Gold Tier**: Autonomous execution with trust framework (trusted actions execute automatically)
- **Platinum Tier**: Distributed always-on execution with cloud-local specialization and offline resilience

**Key Innovation**: The system operates continuously even when the local machine is offline. The Cloud instance triages incoming events, drafts responses, and prepares action plans. When the Local instance comes online, it reviews cloud-drafted work, approves sensitive actions, and executes anything requiring secrets (WhatsApp, banking, local files). This creates a true "always-on executive assistant" experience.

## User Scenarios & Testing

### User Story 1 - Cloud-Local Work-Zone Specialization (Priority: P1)

As a user, I want my AI Employee to operate across two specialized work zones (Cloud for triage/drafts, Local for approvals/sensitive actions) so that routine work happens 24/7 while I maintain control and security over sensitive operations.

**Why this priority**: This is the foundational Platinum Tier capability that enables always-on operation. Without work-zone specialization, the system cannot function when local machine is offline. This is the primary differentiator from Gold Tier and delivers the core value proposition.

**Independent Test**: Can be fully tested by configuring cloud and local instances, sending an email to the cloud instance while local is offline, verifying the cloud drafts a response, then bringing local online and verifying it receives the draft for approval. Delivers immediate value by demonstrating 24/7 availability.

**Acceptance Scenarios**:

1. **Given** Cloud instance is running and Local is offline, **When** an email arrives requiring a reply, **Then** Cloud instance triages the email, drafts a response, and stores it in `/Cloud_Drafts/` in the synced vault
2. **Given** Cloud has drafted a response, **When** Local instance comes online and syncs vault, **Then** Local detects the draft in `/Cloud_Drafts/`, moves it to `/Pending_Approval/`, and notifies me for review
3. **Given** a task requires WhatsApp access (local-only secret), **When** Cloud instance detects this task, **Then** it creates a plan in `/Needs_Local/` and does NOT attempt to access WhatsApp credentials
4. **Given** Local instance approves a cloud-drafted email, **When** approval is granted, **Then** Local executes the send action using Gmail credentials that never sync to cloud
5. **Given** both Cloud and Local are online, **When** a routine email triage happens, **Then** Cloud handles it automatically while Local processes approval queue and sensitive actions in parallel
6. **Given** work-zone rules are configured in `Company_Handbook.md`, **When** an action is classified, **Then** the system correctly routes it to Cloud (triage/drafts) or Local (approvals/secrets) based on action type and trust level

---

### User Story 2 - Vault Synchronization with Security Separation (Priority: P2)

As a user, I want my Obsidian vault to sync automatically between Cloud and Local instances with intelligent secret filtering so that both instances share knowledge while secrets never leave my local machine.

**Why this priority**: Vault sync is the communication backbone between Cloud and Local zones. Without it, the two instances cannot coordinate or delegate work. Security separation ensures compliance with the "secrets never sync" rule, which is critical for trust and safety.

**Independent Test**: Can be fully tested by creating a file with secrets (API keys, passwords) on Local, triggering a sync, and verifying the secrets are filtered out before reaching Cloud. Then create a non-sensitive document on Cloud and verify it syncs to Local. Delivers standalone value as a secure sync system.

**Acceptance Scenarios**:

1. **Given** I have Git or Syncthing configured for vault sync, **When** Local creates a new file in the vault, **Then** it syncs to Cloud within 30 seconds (excluding secret files)
2. **Given** Cloud creates a draft email in `/Cloud_Drafts/`, **When** sync runs, **Then** Local receives the draft and moves it to the appropriate folder based on local rules
3. **Given** Local has a `.env` file with WhatsApp credentials, **When** vault sync runs, **Then** the `.env` file is excluded from sync (Cloud never receives it)
4. **Given** a sync conflict occurs (same file modified on both sides), **When** sync detects the conflict, **Then** it creates both versions (`file.md` and `file-cloud.md`) and logs a conflict notification in `/Logs/sync_conflicts.jsonl`
5. **Given** Cloud instance is unreachable, **When** Local tries to sync, **Then** Local queues changes locally and continues operating, syncing when Cloud becomes available
6. **Given** `.gitignore` or `.stignore` is configured with secret patterns, **When** sync runs, **Then** all files matching patterns (`.env`, `*_credentials.json`, `whatsapp_session/`) are excluded from cloud sync

---

### User Story 3 - 24/7 Cloud Deployment with Health Monitoring (Priority: P3)

As a user, I want my Cloud instance deployed on a VM with always-on watchers and health monitoring so that my AI Employee operates continuously even when my local machine is off.

**Why this priority**: 24/7 availability is the promise of Platinum Tier. Cloud deployment with health monitoring ensures the system stays running, auto-recovers from failures, and alerts me when intervention is needed. This builds on work-zone specialization by ensuring the Cloud zone is truly "always on".

**Independent Test**: Can be fully tested by deploying to a cloud VM, stopping a critical watcher process, and verifying the watchdog detects the failure, auto-restarts the process, and logs the event. Delivers value as a production-ready deployment with reliability guarantees.

**Acceptance Scenarios**:

1. **Given** Cloud instance is deployed on a VM, **When** the VM starts, **Then** all watchers (Gmail, filesystem, scheduler) auto-start and log their PID to `/Logs/health.jsonl`
2. **Given** a watcher process crashes, **When** the watchdog detects the missing PID, **Then** it auto-restarts the watcher and logs the restart event with failure reason
3. **Given** a watcher fails 3 times consecutively within 10 minutes, **When** the third failure occurs, **Then** the watchdog stops auto-restart and sends an alert notification (email or webhook)
4. **Given** Cloud watchers are running 24/7, **When** the daily health check runs, **Then** it generates a health report showing uptime, watcher status, action counts, and vault sync status
5. **Given** Cloud instance runs out of disk space, **When** log rotation detects the issue, **Then** it archives old logs, frees space, and logs a warning
6. **Given** I want to deploy to a cloud VM, **When** I run the deployment script, **Then** it installs dependencies, configures environment variables, sets up systemd services, and starts all watchers with health monitoring enabled

---

### User Story 4 - Offline Resilience & Delegation (Priority: P4)

As a user, I want Cloud and Local instances to operate independently when disconnected and seamlessly delegate work when reconnected so that system functionality degrades gracefully rather than failing completely.

**Why this priority**: Offline resilience ensures the system continues working even during network outages or when local machine is off. The "claim-by-move" delegation pattern allows whichever instance is online to pick up work, enabling flexible work distribution.

**Independent Test**: Can be fully tested by disconnecting network, having Cloud queue several actions, reconnecting, and verifying Local claims and processes queued work. Delivers value as a fault-tolerant system that handles intermittent connectivity.

**Acceptance Scenarios**:

1. **Given** Cloud is online but Local is offline, **When** an email requiring approval arrives, **Then** Cloud drafts a response and stores it in `/Cloud_Drafts/` for Local to claim later
2. **Given** Local is online but Cloud is unreachable, **When** a local action is needed, **Then** Local processes it immediately without waiting for Cloud sync
3. **Given** Cloud has created multiple drafts in `/Cloud_Drafts/`, **When** Local comes online and syncs, **Then** Local moves all drafts to `/Pending_Approval/` using the "claim-by-move" rule (whoever moves the file claims ownership)
4. **Given** both instances try to claim the same task simultaneously, **When** sync conflict occurs, **Then** the instance with the earliest timestamp wins, and the other instance backs off
5. **Given** Cloud detects Local has been offline for 24+ hours, **When** urgent tasks accumulate, **Then** Cloud escalates by sending a summary notification to my backup email
6. **Given** vault sync is broken, **When** Local or Cloud cannot sync for 1 hour, **Then** the system logs a sync failure alert and continues operating in isolated mode

---

### User Story 5 - Cloud-Hosted Odoo Integration (Priority: P5)

As a user, I want Odoo Community accounting system hosted on the cloud VM and integrated with my AI Employee so that financial tracking, invoicing, and accounting happen automatically with professional-grade tools.

**Why this priority**: Odoo provides enterprise-level accounting, invoicing, and financial management. Cloud hosting ensures it's always accessible. Integration with AI Employee enables automated expense tracking, invoice generation, and financial reporting. This complements Gold Tier's basic expense tracking with full accounting capabilities.

**Independent Test**: Can be fully tested by deploying Odoo to cloud VM, creating an expense via AI Employee, and verifying it syncs to Odoo as an accounting entry. Delivers standalone value as a cloud-hosted accounting system even without full AI integration.

**Acceptance Scenarios**:

1. **Given** Odoo Community is installed on Cloud VM with HTTPS, **When** I access the Odoo URL, **Then** I can log in securely and view the accounting dashboard
2. **Given** AI Employee processes an expense (receipt via email), **When** the expense is approved, **Then** it creates an entry in Odoo via MCP server with correct category, amount, vendor, and date
3. **Given** Odoo tracks monthly budgets, **When** an expense exceeds category budget, **Then** Odoo alerts AI Employee, which creates a budget warning in `/Needs_Action/`
4. **Given** I need a monthly financial report, **When** the scheduled job runs, **Then** AI Employee queries Odoo via MCP, generates a formatted report, and saves it to `/Documents/`
5. **Given** Odoo database needs backup, **When** daily backup job runs, **Then** Odoo database is exported, compressed, and stored in cloud storage (S3 or equivalent)
6. **Given** Odoo MCP server is down, **When** AI Employee tries to sync an expense, **Then** it queues the expense locally and retries when Odoo becomes available

---

### User Story 6 - Always-On Watchers with Cloud Monitoring (Priority: P6)

As a user, I want watchers (Gmail, WhatsApp, filesystem) running 24/7 on Cloud instance with real-time monitoring so that incoming events are detected immediately regardless of my local machine status.

**Why this priority**: Always-on watchers are the "senses" of the Platinum Tier system. Cloud-hosted watchers ensure emails and events are detected 24/7, feeding work to the Cloud instance for triage. This completes the always-on experience.

**Independent Test**: Can be fully tested by deploying Gmail watcher to Cloud VM, sending a test email, and verifying the watcher detects it within 1 minute and creates an entity in the vault. Delivers value as a reliable event detection system.

**Acceptance Scenarios**:

1. **Given** Gmail watcher is running on Cloud VM, **When** a new email arrives in my inbox, **Then** the watcher detects it within 1 minute and creates an entity in `/Needs_Action/`
2. **Given** filesystem watcher monitors a cloud-accessible drop folder, **When** a file is added, **Then** the watcher processes it and routes it to the appropriate vault folder
3. **Given** Cloud watchers have been running for 7 days, **When** the weekly health report runs, **Then** it shows total events detected, processing success rate, and average detection latency
4. **Given** a watcher encounters an error (API rate limit), **When** the error occurs, **Then** the watcher backs off exponentially and logs the error with retry schedule
5. **Given** WhatsApp watcher requires local-only access, **When** Cloud instance starts, **Then** it does NOT start WhatsApp watcher (Local-only security rule)
6. **Given** Cloud watchers detect high-priority events (urgent email, payment due), **When** detected, **Then** Cloud prioritizes these events and marks them in `/Needs_Action/` with `priority: urgent`

---

### Edge Cases

- What happens when Cloud and Local both process the same task simultaneously?
  - First-to-move wins (claim-by-move rule). Sync conflict resolution creates duplicate detection, losing instance backs off.

- What happens when vault sync is completely broken for 24+ hours?
  - Both instances continue operating independently. Cloud queues drafts locally. Local processes approvals locally. Manual intervention required to reconcile.

- What happens when Cloud VM runs out of resources (CPU/memory)?
  - Health monitoring detects resource exhaustion, pauses non-critical watchers, sends alert notification, attempts auto-recovery by freeing resources.

- What happens when Odoo database becomes corrupted?
  - Daily backups allow restore to previous state. AI Employee falls back to basic expense tracking (Gold Tier mode) until Odoo is restored.

- What happens when a secret accidentally gets committed to vault?
  - Pre-commit hook detects secret patterns and blocks the commit. If sync already happened, Cloud instance never decrypts the secret (encrypted at rest with Local-only key).

- What happens when Local approves an action but send fails (network down)?
  - Local queues the approved action in `/Approved_Queue/` and retries with exponential backoff. Action stays in queue until successful or manually cancelled.

## Requirements

### Functional Requirements

#### Work-Zone Specialization

- **FR-001**: System MUST operate in two distinct zones: Cloud (triage/drafts/monitoring) and Local (approvals/secrets/sensitive actions)
- **FR-002**: System MUST route actions to appropriate zones based on action type, trust level, and secret requirements as defined in `Company_Handbook.md`
- **FR-003**: Cloud zone MUST be able to draft responses, create plans, and triage events without access to secrets (API keys, passwords, WhatsApp sessions)
- **FR-004**: Local zone MUST have exclusive access to secrets and MUST be the only zone that executes secret-dependent actions (WhatsApp send, banking transactions)
- **FR-005**: System MUST support the "claim-by-move" delegation pattern where moving a file between folders assigns ownership to the moving instance

#### Vault Synchronization

- **FR-006**: System MUST sync vault bidirectionally between Cloud and Local using Git or Syncthing
- **FR-007**: System MUST filter secrets during sync using `.gitignore` or `.stignore` patterns (`.env`, credentials, sessions, keys)
- **FR-008**: System MUST detect sync conflicts (same file modified on both sides) and create both versions with clear naming (`file.md`, `file-cloud.md`)
- **FR-009**: System MUST queue local changes during Cloud outage and sync when connectivity restores
- **FR-010**: System MUST sync within 30 seconds of file changes under normal conditions
- **FR-011**: System MUST log all sync events, conflicts, and failures to `/Logs/sync.jsonl`

#### Cloud Deployment

- **FR-012**: Cloud instance MUST be deployable to a Linux VM (Ubuntu 22.04+) via automated deployment script
- **FR-013**: Cloud instance MUST auto-start all watchers and services on VM boot using systemd or equivalent
- **FR-014**: Cloud instance MUST run 24/7 with automatic restart on crash
- **FR-015**: System MUST provide deployment script that installs dependencies, configures environment, sets up watchers, and starts health monitoring

#### Health Monitoring

- **FR-016**: System MUST run a watchdog process that monitors critical watcher PIDs every 60 seconds
- **FR-017**: Watchdog MUST auto-restart crashed watchers up to 3 times within 10 minutes
- **FR-018**: Watchdog MUST send alert notification after 3 consecutive watcher failures
- **FR-019**: System MUST generate daily health report showing uptime, watcher status, action counts, vault sync status
- **FR-020**: System MUST monitor disk space and auto-rotate logs when disk usage exceeds 80%

#### Odoo Integration

- **FR-021**: System MUST deploy Odoo Community Edition on Cloud VM with HTTPS and authentication
- **FR-022**: System MUST integrate with Odoo via MCP server for expense tracking, invoicing, and financial queries
- **FR-023**: System MUST sync approved expenses from AI Employee to Odoo accounting entries
- **FR-024**: System MUST backup Odoo database daily to cloud storage with 30-day retention
- **FR-025**: System MUST generate monthly financial reports by querying Odoo data

#### Always-On Watchers

- **FR-026**: Cloud instance MUST run Gmail watcher 24/7 with 1-minute polling interval
- **FR-027**: Cloud instance MUST run filesystem watcher for cloud drop folder
- **FR-028**: Cloud instance MUST run scheduler for daily/weekly automation tasks
- **FR-029**: Local instance MUST run WhatsApp watcher (local-only, never on Cloud)
- **FR-030**: Watchers MUST implement exponential backoff on errors (1s, 2s, 4s, 8s, up to 60s)

#### Offline Resilience

- **FR-031**: Cloud instance MUST operate fully when Local is offline (triage, drafts, monitoring)
- **FR-032**: Local instance MUST operate fully when Cloud is offline (approvals, secret actions, local tasks)
- **FR-033**: System MUST queue work for the offline instance and sync when reconnected
- **FR-034**: System MUST escalate urgent tasks (24+ hour queue) via backup notification channel
- **FR-035**: System MUST log all offline periods and sync resumptions to audit trail

#### Security Requirements

- **FR-036**: System MUST never sync secret files to Cloud (`.env`, credentials, sessions, banking data)
- **FR-037**: System MUST encrypt vault at rest on Cloud VM using disk encryption
- **FR-038**: System MUST use HTTPS for all Cloud services (Odoo, health dashboard, API endpoints)
- **FR-039**: System MUST authenticate Cloud-Local sync using SSH keys or secure tokens
- **FR-040**: System MUST implement pre-commit hooks to detect and block accidental secret commits

### Key Entities

- **Work Zone**: Represents Cloud or Local execution environment with specific capabilities (Cloud: triage/drafts, Local: approvals/secrets)
- **Sync Event**: Represents a vault synchronization operation with timestamp, direction (Cloud→Local or Local→Cloud), files changed, conflicts detected
- **Health Status**: Represents system health at a point in time including watcher PIDs, uptime, resource usage, sync status
- **Odoo Entry**: Represents a financial transaction synced between AI Employee and Odoo (expense, invoice, budget entry)
- **Secret Filter Rule**: Represents a pattern or file path that must be excluded from Cloud sync (defined in `.gitignore`/`.stignore`)
- **Claim**: Represents ownership of a task/file by Cloud or Local instance, established by moving the file to a zone-specific folder

## Success Criteria

### Measurable Outcomes

- **SC-001**: Cloud instance operates 24/7 with 99% uptime (measured over 30 days)
- **SC-002**: Vault sync completes within 30 seconds of file changes in 95% of cases
- **SC-003**: Zero secrets leak to Cloud instance (validated by automated secret scanning)
- **SC-004**: Email triage happens within 1 minute of arrival regardless of Local status
- **SC-005**: Watchdog auto-recovers from watcher crashes within 60 seconds in 90% of cases
- **SC-006**: System handles Local offline periods gracefully with zero data loss when reconnected
- **SC-007**: Users can review and approve cloud-drafted responses within 5 minutes of Local coming online
- **SC-008**: Odoo integration syncs 100% of approved expenses to accounting system within 2 minutes
- **SC-009**: Monthly financial reports generated automatically from Odoo data with 100% accuracy
- **SC-010**: Deployment to cloud VM completes in under 30 minutes using automated script

## Assumptions

- Cloud VM will be Ubuntu 22.04+ with minimum 2 CPU cores, 4GB RAM, 50GB disk
- Git or Syncthing is available for vault synchronization (user chooses based on preference)
- User has access to a cloud provider (AWS, DigitalOcean, Linode, etc.) for VM hosting
- Odoo Community Edition is sufficient (no need for Enterprise features)
- HTTPS certificates can be obtained via Let's Encrypt or similar free service
- Cloud instance has reliable internet connectivity with <1% packet loss
- User's Local machine comes online at least once per 24 hours for critical approvals
- Gmail API, calendar API, and social media APIs are available with reasonable rate limits
- Vault size remains under 10GB (suitable for Git/Syncthing performance)

## Dependencies

### External Dependencies

- **Cloud Provider**: Requires VM hosting (AWS EC2, DigitalOcean Droplet, Linode, etc.)
- **Git or Syncthing**: Required for vault synchronization between Cloud and Local
- **Odoo Community**: Open-source accounting system (self-hosted on Cloud VM)
- **HTTPS/SSL**: Let's Encrypt or similar certificate authority for secure Cloud services
- **Systemd**: Required for service management on Cloud VM (standard on Ubuntu 22.04+)

### Internal Dependencies

- **Bronze Tier**: Email monitoring and entity creation
- **Silver Tier**: HITL approval workflow and action execution
- **Gold Tier**: Trust framework, CRM, expense tracking, analytics, document generation
- All Agent Skills from Gold Tier must be converted to work in distributed Cloud-Local mode

### Integration Points

- Gmail API (Cloud and Local)
- Google Calendar API (Cloud and Local)
- Social media APIs (Cloud-hosted, Local-approved)
- Odoo MCP Server (Cloud-hosted)
- Vault sync via Git/Syncthing
- Cloud health monitoring dashboard
- Backup storage (S3, Backblaze B2, or equivalent)

## Out of Scope

The following are explicitly excluded from Platinum Tier:

- Multi-user support (system remains single-user)
- Mobile app or native mobile interface
- Real-time collaboration features
- Advanced AI model fine-tuning or custom model hosting
- Integration with enterprise identity providers (SAML, LDAP)
- Advanced analytics dashboards or BI tools
- Compliance certifications (SOC 2, ISO 27001, etc.)
- Multi-region cloud deployment or geographic redundancy
- Custom Odoo modules or Odoo Enterprise features
- Automated tax filing or legal document generation
- Integration with cryptocurrency wallets or blockchain
