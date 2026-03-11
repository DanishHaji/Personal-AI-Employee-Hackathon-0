# Personal AI Employee - Platinum Tier

**Professional-grade autonomous AI employee with 24/7 cloud operation and intelligent work-zone specialization**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

## Overview

A complete autonomous AI Employee system that monitors, plans, executes, and learns from your work patterns to provide proactive assistance. Features local-first privacy with optional cloud deployment for 24/7 availability, intelligent work-zone specialization, and comprehensive health monitoring.

### Progressive Tier Architecture

#### Bronze Tier - Monitoring & Planning ✅
Foundation for autonomous operation with real-time monitoring and AI-powered planning.

- ✅ **Gmail Monitoring**: Automated inbox scanning every 2 minutes with priority detection
- ✅ **File Drop Processing**: Real-time file monitoring via Obsidian vault `/Inbox` folder
- ✅ **AI Task Planning**: Intelligent plan generation using Claude Code
- ✅ **Real-time Dashboard**: Live status updates in Obsidian showing pending actions
- ✅ **Audit Logging**: Complete event tracking with structured JSONL logs

#### Silver Tier - Execution & Automation ✅
Autonomous execution with human-in-the-loop approval for sensitive actions.

- ✅ **Email Automation**: Send and reply to emails via Gmail API with approval workflow
- ✅ **Social Media Publishing**: Multi-platform posting (LinkedIn, Facebook, Twitter)
- ✅ **WhatsApp Integration**: Business message monitoring and auto-response
- ✅ **Task Scheduling**: Daily briefings, weekly summaries, custom automation
- ✅ **Approval Workflows**: Trust-based decision engine for autonomous actions

#### Gold Tier - Intelligent Autonomy ✅
Advanced intelligence with 8 fully autonomous user stories.

- ✅ **US1: Scheduler Skill** - Email-based task scheduling with natural language parsing
- ✅ **US2: Social Media Manager** - Autonomous multi-platform content distribution
- ✅ **US3: WhatsApp Processor** - Intelligent message triage and response routing
- ✅ **US4: Executor Skill** - Trust-based autonomous task execution
- ✅ **US5: Calendar Integration** - Google Calendar sync with meeting preparation
- ✅ **US6: Meeting Attendant** - Zoom integration with AI transcription and automated notes
- ✅ **US7: Proactive Suggestions** - Weekly analytics with actionable recommendations
- ✅ **US8: Financial Tracking** - OCR-based expense tracking with budget management

#### Platinum Tier - Cloud & Enterprise ⚡ **IN PROGRESS** (60% Complete)
24/7 cloud operation with work-zone specialization and enterprise-grade reliability.

**Completed Features**:
- ✅ **Vault Synchronization**: Git-based bidirectional sync between cloud and local instances
- ✅ **Secret Filtering**: Automatic detection and prevention of secrets syncing to cloud
- ✅ **Work-Zone Specialization**: Cloud handles triage/drafts, Local handles approvals/secrets
- ✅ **Claim Management**: Advisory file-based locks with 15-minute TTL for task coordination
- ✅ **Health Monitoring**: System resource tracking, watcher supervision, auto-restart
- ✅ **Cloud Deployment**: One-command Ubuntu VM setup with systemd integration
- ✅ **24/7 Watcher Operation**: Continuous Gmail and filesystem monitoring
- ✅ **Priority Detection**: Urgent email identification with intelligent routing
- ✅ **Weekly Health Reports**: Comprehensive system analytics and uptime tracking
- ✅ **Alert Management**: Rate-limited notifications with email/webhook support

**In Progress** (40% remaining):
- ⏳ Odoo Integration: Cloud-hosted accounting with expense sync
- ⏳ Offline Resilience: Queue-based operation during network outages
- ⏳ System Polish: Production hardening and documentation

**Progress**: 88 of 147 tasks complete (59.9%)

## Quick Start

### Prerequisites

- **Python**: 3.13+ (required for Platinum Tier dependencies)
- **UV Package Manager**: Recommended for dependency management
- **Node.js**: v24+ for PM2 process management (Local instance)
- **Obsidian**: v1.10.6+ for vault visualization
- **Claude Code CLI**: For AI-powered task execution
- **Gmail Account**: With API access enabled
- **Git**: For vault synchronization (Platinum Tier)
- **Ubuntu 22.04 VM**: For cloud deployment (Platinum Tier, optional)

### Installation

```bash
# Clone repository
git clone https://github.com/DanishHaji/Personal-AI-Employee-Hackathon-0.git
cd Personal-AI-Employee-Hackathon-0

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env and configure VAULT_PATH, API keys, credentials
```

### Gmail API Setup

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project → Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` to project root
5. Authenticate:

```bash
uv run python src/watchers/gmail_watcher.py --auth-only
```

### Initialize Obsidian Vault

```bash
# Create vault structure
uv run python scripts/init_vault.py --path /path/to/your/vault

# Open in Obsidian: File → Open folder as vault
```

### Start Local Instance

**Bronze/Silver/Gold Tier (PM2)**:
```bash
# Install PM2
npm install -g pm2

# Start all processes (10 total)
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs

# Enable auto-start on boot
pm2 startup
pm2 save
```

**Platinum Tier - Local Instance** (Additional):
```bash
# Install systemd services (requires sudo)
sudo cp deployment/systemd/*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload

# Enable vault sync and claim management
sudo systemctl enable --now vault-sync.timer
sudo systemctl enable --now claim-expiry.timer

# Check status
systemctl status vault-sync.timer claim-expiry.timer
```

### Deploy Cloud Instance (Platinum Tier)

**One-Command Deployment**:
```bash
# On fresh Ubuntu 22.04 VM
sudo ./deployment/cloud-deploy.sh
```

**Manual Configuration**:
```bash
# 1. Edit cloud environment
sudo nano /opt/ai-employee/.env.cloud

# 2. Add Gmail credentials
sudo cp gmail_credentials.json /opt/ai-employee/.credentials/

# 3. Configure Git SSH for vault sync
# (follow prompts from deployment script)

# 4. Start services
sudo systemctl start health-monitor.service
sudo systemctl start gmail-watcher.service
sudo systemctl start filesystem-watcher.service

# 5. Check health
sudo journalctl -u health-monitor.service -f
cat /opt/ai-employee/Logs/health.jsonl
```

For detailed deployment instructions, see: **[PLATINUM_TIER_DEPLOYMENT.md](PLATINUM_TIER_DEPLOYMENT.md)**

## Architecture

### System Components

**Bronze Tier (3 processes)**:
- **Gmail Watcher**: Priority email detection every 120s
- **Filesystem Watcher**: Real-time file monitoring with quarantine
- **Orchestrator**: Event coordination and Claude Code triggering

**Silver Tier (3 processes)**:
- **Scheduler**: Automated task scheduling and execution
- **Social Media Poster**: Multi-platform content distribution
- **WhatsApp Watcher**: Business messaging automation

**Gold Tier (4 processes)**:
- **Calendar Watcher**: Google Calendar synchronization
- **Meeting Recorder**: Zoom transcription and note generation
- **Analytics Engine**: Weekly insights and recommendations
- **Expense Processor**: OCR receipt processing and budgeting

**Platinum Tier Services (Cloud + Local)**:
- **VaultSyncService**: Git-based bidirectional vault synchronization (5-minute interval)
- **ClaimManager**: Advisory lock management for distributed task coordination
- **HealthMonitor**: System supervision with auto-restart (60s checks)
- **AlertManager**: Rate-limited notifications (email, webhook)

**Platinum Tier - Cloud Instance**:
- **Gmail Watcher** (24/7 continuous mode)
- **Filesystem Watcher** (monitors Cloud_Dropzone)
- **Health Monitor** (watchdog with systemd integration)

**Platinum Tier - Local Instance**:
- All Bronze/Silver/Gold processes
- **WhatsApp Watcher** (local-only, never on cloud)
- **VaultSync** + **ClaimManager** (coordination services)

### Vault Folder Structure

```
/path/to/vault/
├── Inbox/              # Drop files here (Local only)
├── Needs_Action/       # Detected emails and files requiring action
├── Plans/              # AI-generated action plans
├── Pending_Approval/   # Silver/Gold tier approval queue
├── Approved/           # Approved actions awaiting execution
├── Done/               # Completed tasks archive
├── Quarantine/         # Isolated unsafe files
├── Contacts/           # CRM contact entities (CONTACT_*.md)
├── Expenses/           # Expense tracking (EXPENSE_*.md)
├── Budgets/            # Monthly budget files (YYYY-MM.json)
├── Receipts/           # OCR-processed receipt images
├── Meetings/           # Meeting notes and transcriptions
├── Calendar/           # Synced events (events.json)
├── Insights/           # Weekly analytics (INSIGHT_*.json)
├── Logs/               # Audit logs (*.jsonl)
│   ├── audit.jsonl     # Complete action history
│   ├── sync.jsonl      # Vault synchronization events
│   ├── claims.jsonl    # Task claim/release events
│   ├── health.jsonl    # System health snapshots
│   └── alerts.jsonl    # Alert notifications
├── Cloud_Drafts/       # Platinum: Cloud-generated drafts
├── Needs_Local/        # Platinum: Tasks requiring local execution
├── Claims/             # Platinum: Active task claims
├── Health/             # Platinum: Health snapshots (*.health.json)
├── Dashboard.md        # Real-time status summary
└── Company_Handbook.md # AI behavior rules and trust policies
```

### Technology Stack

**Core**:
- Python 3.13+ (type-safe, modern async/await)
- Obsidian (local-first knowledge vault)
- Claude Code CLI (AI-powered execution)

**APIs & Integrations**:
- Gmail API (email automation)
- Google Calendar API (scheduling)
- Zoom API (meeting transcription)
- WhatsApp Business API (messaging)
- LinkedIn/Facebook/Twitter APIs (social media)

**Infrastructure (Platinum Tier)**:
- Git (vault synchronization)
- systemd (service management)
- Ubuntu 22.04 LTS (cloud deployment)
- psutil (health monitoring)

**Security & Privacy**:
- AES-256-GCM encryption
- detect-secrets (secret scanning)
- pre-commit hooks (Git hygiene)
- Local-first architecture (GDPR compliant)

## Usage

### Daily Workflow

1. **Morning**: Check `Dashboard.md` for overnight activity (Cloud handled triage)
2. **Review**: Process items in `/Needs_Action/` and `/Cloud_Drafts/`
3. **Approve**: Move approved items to `/Approved/` for execution
4. **Monitor**: Check `/Logs/health.jsonl` for system status
5. **Archive**: Move completed items to `/Done/`

### Adding Files

Drop any file into `/Inbox/` → Appears in `/Needs_Action/` within 30 seconds

### Email Processing (Platinum Tier)

**Cloud Instance (24/7)**:
- Detects emails within 1 minute
- Generates draft responses
- Saves to `/Cloud_Drafts/`

**Local Instance**:
- Detects cloud drafts
- Moves to `/Pending_Approval/`
- You approve → Sends email

### Monitoring System

```bash
# Local instance (PM2)
pm2 status
pm2 logs --lines 50

# Cloud instance (systemd)
sudo systemctl status health-monitor.service
sudo journalctl -u gmail-watcher.service -f

# Health snapshots
cat /opt/ai-employee/Logs/health.jsonl | tail -10

# Generate weekly report
python -m src.services.health_monitor weekly-report --instance cloud
```

## Configuration

### Watcher Settings

All watcher configuration is centralized in **`config/watchers.yaml`**:

```yaml
global:
  default_check_interval: 120  # seconds
  max_consecutive_errors: 5
  max_backoff_seconds: 300

gmail_watcher:
  mode: continuous  # "once" or "continuous"
  urgent_keywords: [urgent, asap, invoice, deadline]
  api_rate_limit:
    max_requests_per_minute: 250
  allowed_instances: [local, cloud]

whatsapp_watcher:
  allowed_instances: [local]  # Never on cloud (secrets)
  requires_secrets: true

health_monitor:
  thresholds:
    cpu_percent: 90
    memory_percent: 85
    disk_percent: 90
  reports:
    weekly_enabled: true
```

### Work-Zone Routing Rules

Configure in **`Company_Handbook.md`**:

```yaml
routing_rules:
  - pattern: "EMAIL_*"
    action: "reply_draft"
    zone: "cloud"        # Cloud generates drafts
    requires_approval: true

  - pattern: "WHATSAPP_*"
    action: "send_message"
    zone: "local"        # Local only (secrets)
    requires_approval: false
```

## Documentation

### Tier-Specific Guides

**Bronze Tier**:
- [Quickstart Guide](specs/001-bronze-tier-mvp/quickstart.md) - 10-minute setup
- [Feature Specification](specs/001-bronze-tier-mvp/spec.md)
- [Data Model](specs/001-bronze-tier-mvp/data-model.md)

**Silver Tier**:
- [Setup Guide](SILVER_TIER_SETUP.md)
- [Feature Specification](specs/002-silver-tier-upgrade/spec.md)

**Gold Tier**:
- [Setup Guide](docs/gold-tier-setup.md) - All 8 user stories
- [Troubleshooting](docs/gold-tier-troubleshooting.md) - 50+ scenarios
- [Encryption & Backup](docs/encryption-backup.md) - GDPR compliance

**Platinum Tier**:
- [Deployment Guide](PLATINUM_TIER_DEPLOYMENT.md) - Cloud VM setup
- [Testing Guide](PLATINUM_TIER_TESTING.md) - Complete test suite
- [Feature Specification](specs/004-platinum-tier-upgrade/spec.md)
- [Task Checklist](specs/004-platinum-tier-upgrade/tasks.md) - 147 tasks

### Development Resources

- [Architecture Decision Records](history/adr/) - Technical decisions
- [Prompt History](history/prompts/) - Complete conversation logs
- [Project Constitution](.specify/memory/constitution.md) - Core principles

## Security & Privacy

### Constitutional Principles

The system follows strict privacy and security principles:

**Principle I - Local-First Privacy**:
- ✅ All secrets remain on local instance
- ✅ WhatsApp sessions never sync to cloud
- ✅ Banking credentials local-only
- ✅ AES-256-GCM encryption for sensitive data

**Principle III - Security & Credential Management**:
- ✅ Complete audit logging (all actions tracked)
- ✅ Pre-commit secret scanning (detect-secrets)
- ✅ Git-based vault sync (no secrets)
- ✅ systemd security hardening (NoNewPrivileges, PrivateTmp)

**Principle VII - Observability**:
- ✅ Structured JSONL logging
- ✅ Health monitoring every 60s
- ✅ Weekly analytics reports
- ✅ Real-time metrics dashboard

### GDPR Compliance

- ✅ **Article 20 - Data Portability**: One-command export
- ✅ **Article 17 - Right to Erasure**: Complete data deletion
- ✅ **Article 32 - Security**: AES-256-GCM encryption
- ✅ **Article 30 - Records**: Complete audit logs (90-day retention)

## Troubleshooting

### Common Issues

**Gmail watcher not detecting emails**:
```bash
# Check logs
pm2 logs gmail-watcher --lines 50

# Re-authenticate
rm token.json
uv run python src/watchers/gmail_watcher.py --auth-only
```

**Cloud sync not working**:
```bash
# Check sync logs
tail -f Logs/sync.jsonl

# Manually trigger sync
python -m src.services.vault_sync_service sync --direction bidirectional

# Check Git status
git status
git log --oneline -5
```

**Health monitor showing critical**:
```bash
# Check health snapshot
cat Health/cloud_$(date +%Y%m%d)*.health.json | tail -1

# Check watcher status
systemctl status gmail-watcher.service
systemctl status filesystem-watcher.service

# Restart failed watcher
sudo systemctl restart gmail-watcher.service
```

**High resource usage**:
```bash
# Check resource limits
systemctl cat health-monitor.service | grep -E "CPU|Memory"

# Monitor in real-time
top -p $(pgrep -f gmail_watcher)

# Generate health report
python -m src.services.health_monitor report --date $(date +%Y-%m-%d)
```

For comprehensive troubleshooting, see:
- **Gold Tier**: [docs/gold-tier-troubleshooting.md](docs/gold-tier-troubleshooting.md)
- **Platinum Tier**: [PLATINUM_TIER_DEPLOYMENT.md](PLATINUM_TIER_DEPLOYMENT.md) (Troubleshooting section)

## Performance & Scalability

### Benchmarks

**Bronze/Silver/Gold Tier (Local)**:
- Gmail check latency: <500ms
- File detection latency: <1s (watchdog)
- Dashboard update: <2s
- Memory usage: ~150MB per watcher

**Platinum Tier (Cloud)**:
- Health check interval: 60s
- Vault sync interval: 300s (5 minutes)
- Claim TTL: 900s (15 minutes)
- Cloud VM requirements: 2 CPU, 4GB RAM, 50GB disk

**Resource Limits (systemd)**:
- health-monitor: 20% CPU, 512MB RAM
- gmail-watcher: 15% CPU, 384MB RAM
- filesystem-watcher: 10% CPU, 256MB RAM

## Roadmap

### Current Status (March 2026)

- ✅ **Bronze Tier**: Complete (Monitoring & Planning)
- ✅ **Silver Tier**: Complete (Execution & Automation)
- ✅ **Gold Tier**: Complete (Intelligent Autonomy - 8 user stories)
- ⚡ **Platinum Tier**: 60% Complete (Cloud & Enterprise)
  - ✅ Foundational services (vault sync, claims, health)
  - ✅ Cloud deployment automation
  - ✅ 24/7 watchers with health monitoring
  - ⏳ Odoo integration (in progress)
  - ⏳ Offline resilience (in progress)

### Next Milestones

**Platinum Tier Completion** (Q2 2026):
- [ ] Odoo cloud-hosted accounting with expense sync
- [ ] Offline queue-based operation
- [ ] Production hardening and polish
- [ ] Complete acceptance testing on Cloud VM

**Future Enhancements**:
- Multi-user team support
- Mobile companion app for approvals
- Advanced ML-based task prediction
- Additional integrations (Slack, Teams, Notion)

## License

MIT License - See [LICENSE](LICENSE) for details

## Contributing

Contributions welcome! This project follows:
- **Spec-Driven Development**: All features start with specification
- **Constitutional AI**: Strict adherence to privacy/security principles
- **Test-First**: Acceptance tests before implementation
- **Prompt History**: All work logged as PHR (Prompt History Records)

See [.specify/README.md](.specify/README.md) for development workflow.

## Acknowledgments

Built with:
- **Claude Code** - AI-powered development assistant
- **Anthropic Claude** - Language model (Sonnet 4.5)
- **Obsidian** - Local-first knowledge management
- **Python** - Core implementation language

## Support

- **Issues**: [GitHub Issues](https://github.com/DanishHaji/Personal-AI-Employee-Hackathon-0/issues)
- **Documentation**: See `/docs` and `/specs` directories
- **Prompt History**: Complete conversation logs in `/history/prompts`

---

**Status**: In active development | **Last Updated**: March 12, 2026 | **Version**: 0.4.0 (Platinum Tier)
