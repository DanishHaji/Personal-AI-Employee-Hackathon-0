# Personal AI Employee - Gold Tier

**Fully autonomous AI employee with 8 intelligent user stories**

## Overview

A complete autonomous AI Employee system that monitors, plans, executes, and learns from your work patterns to provide proactive assistance across email, social media, calendar, meetings, expenses, and more.

### Bronze Tier (Monitoring & Planning)
- ✅ Automated Gmail monitoring (detects important emails within 2 minutes)
- ✅ File drop processing via Obsidian vault /Inbox folder
- ✅ AI-generated task plans using Claude Code
- ✅ Real-time Dashboard in Obsidian showing pending actions

### Silver Tier (Execution & Automation)
- ✅ **Email Sending**: Send and reply to emails via Gmail API with approval
- ✅ **Social Media Posting**: Auto-post to LinkedIn, Facebook, Twitter
- ✅ **WhatsApp Monitoring**: Monitor WhatsApp Business for incoming messages
- ✅ **Scheduled Tasks**: Daily briefings, weekly summaries, custom automation

### Gold Tier (Intelligent Autonomy) **NEW**
- ✅ **US1: Scheduler Skill** - Email-based task scheduling with natural language parsing
- ✅ **US2: Social Media Manager** - Autonomous multi-platform posting with approval workflow
- ✅ **US3: WhatsApp Processor** - Intelligent message triage and response routing
- ✅ **US4: Executor Skill** - Autonomous task execution with trust-based approval
- ✅ **US5: Calendar Integration** - Google Calendar sync with meeting preparation
- ✅ **US6: Meeting Attendant** - Zoom integration with AI transcription and notes
- ✅ **US7: Proactive Suggestions** - Weekly analytics with actionable recommendations
- ✅ **US8: Financial Tracking** - OCR-based expense tracking with budget management

## Quick Start

### Bronze Tier (Monitoring)

For detailed Bronze Tier setup instructions, see: **[specs/001-bronze-tier-mvp/quickstart.md](specs/001-bronze-tier-mvp/quickstart.md)**

### Silver Tier (Execution)

For detailed Silver Tier setup instructions, see: **[SILVER_TIER_SETUP.md](SILVER_TIER_SETUP.md)**

### Gold Tier (Intelligent Autonomy) **NEW**

For detailed Gold Tier setup instructions, see: **[docs/gold-tier-setup.md](docs/gold-tier-setup.md)**

**Quick Setup**:
```bash
# 1. Install Gold Tier dependencies
uv pip install easyocr pillow openai google-cloud-vision google-auth

# 2. Configure API keys in .env (see docs/gold-tier-setup.md)

# 3. Set up Google Calendar and Zoom credentials

# 4. Configure default budgets in Budgets/default_budgets.json

# 5. Start all processes (10 total: 3 Bronze + 3 Silver + 4 Gold)
pm2 start ecosystem.config.js

# 6. Verify all processes running
pm2 status
```

**Troubleshooting**: See **[docs/gold-tier-troubleshooting.md](docs/gold-tier-troubleshooting.md)** for 50+ common scenarios

**Data Export**: See **[docs/encryption-backup.md](docs/encryption-backup.md)** for GDPR-compliant data portability

### Prerequisites

- Python 3.13+
- UV package manager (recommended) or pip
- Node.js v24+ (for PM2 process management)
- Obsidian v1.10.6+
- Claude Code CLI
- Gmail account with API access

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ai-employee

# Install UV package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with UV
uv sync

# Or with pip (if UV not available)
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env and set your VAULT_PATH and Gmail credentials
```

### Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `credentials.json` to project root
6. Run first-time authentication:

```bash
uv run python src/watchers/gmail_watcher.py --auth-only
```

### Create Obsidian Vault

```bash
# Initialize vault structure
uv run python scripts/init_vault.py --path /path/to/your/vault

# Open vault in Obsidian
# File → Open folder as vault → Select /path/to/your/vault
```

### Start Watchers with PM2

```bash
# Install PM2 globally (if not already installed)
npm install -g pm2

# Start all watchers using ecosystem config (recommended)
pm2 start ecosystem.config.js

# OR start individually (alternative method)
pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3
pm2 start src/watchers/filesystem_watcher.py --name fs-watcher --interpreter python3
pm2 start src/orchestrator.py --name orchestrator --interpreter python3

# Check status
pm2 status

# View logs
pm2 logs

# View logs for specific process
pm2 logs gmail-watcher
pm2 logs filesystem-watcher
pm2 logs orchestrator

# Stop all processes
pm2 stop all

# Restart all processes
pm2 restart all

# Enable auto-start on system boot (optional)
pm2 startup
pm2 save
```

**PM2 Process Management**:
- `pm2 status` - View all running processes
- `pm2 logs` - Tail all logs in real-time
- `pm2 logs <name>` - View logs for specific process
- `pm2 monit` - Real-time CPU/memory monitoring
- `pm2 restart all` - Restart all processes
- `pm2 stop all` - Stop all processes
- `pm2 delete all` - Remove all processes from PM2

## Architecture

### Components (10 Processes)

**Bronze Tier (3 processes)**:
- **Gmail Watcher**: Monitors inbox every 2 minutes, surfaces important emails
- **File System Watcher**: Monitors /Inbox folder for dropped files
- **Orchestrator**: Detects new items, triggers Claude Code processing

**Silver Tier (3 processes)**:
- **Scheduler**: Manages scheduled tasks (daily briefings, weekly summaries)
- **Social Media Poster**: Handles LinkedIn, Facebook, Twitter posts
- **WhatsApp Watcher**: Monitors WhatsApp Business for incoming messages

**Gold Tier (4 processes)**:
- **Calendar Watcher**: Google Calendar sync with meeting preparation
- **Meeting Recorder**: Zoom integration with AI transcription
- **Analytics Engine**: Weekly insights with proactive recommendations
- **Expense Processor**: OCR-based receipt processing and budget tracking

**Core Services**:
- **Claude Code Skills**: 15+ AI-powered skills for autonomous task execution
- **Obsidian Vault**: Local-first storage and real-time dashboard
- **Trust Evaluator**: <10ms trust rule evaluation for approval decisions
- **Rate Limiter**: Token bucket algorithm protecting 8+ API quotas
- **GDPR Exporter**: Complete data portability for Article 20 compliance

### Folder Structure

```
/path/to/vault/
├── Inbox/              # Drop files here for processing
├── Needs_Action/       # Detected emails and files
├── Plans/              # AI-generated action plans
├── Pending_Approval/   # Items requiring human approval
├── Approved/           # Approved actions (Silver tier+)
├── Done/               # Completed items
├── Logs/               # JSON audit logs and performance metrics
├── Quarantine/         # Unsafe files
├── Contacts/           # CRM contact entities (CONTACT_*.md)
├── Expenses/           # Expense tracking entities (EXPENSE_*.md)
├── Budgets/            # Monthly budget files (YYYY-MM.json)
├── Receipts/           # OCR-processed receipt images
├── Meetings/           # Meeting notes and transcriptions
├── Calendar/           # Synced calendar events (events.json)
├── Insights/           # Weekly analytics insights (INSIGHT_*.json)
├── Dashboard.md        # Real-time status summary
└── Company_Handbook.md # AI behavior rules and trust policies
```

## Usage

### Daily Workflow

1. Open Obsidian vault
2. Check `Dashboard.md` for pending items
3. Review `/Needs_Action/` for urgent emails/files
4. Check `/Plans/` for AI-generated action plans
5. Move completed items to `/Done/`

### Adding Files

Drop any file into `/Inbox/` folder → File appears in `/Needs_Action/` within 30 seconds

### Monitoring System

```bash
# Check watcher status
pm2 status

# View recent logs
pm2 logs --lines 50

# Restart if needed
pm2 restart all
```

## Development

### Project Structure

```
ai-employee/
├── src/
│   ├── watchers/          # Gmail and File System watchers
│   ├── models/            # Data models (Email, FileDrop, etc.)
│   ├── services/          # Gmail, Vault, Logger services
│   └── orchestrator.py    # Main coordinator
├── .claude/commands/      # Claude Code skills
├── tests/                 # Unit and integration tests
├── scripts/               # Setup utilities
└── specs/                 # Feature specifications
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Documentation

### Bronze Tier
- **[Quickstart Guide](specs/001-bronze-tier-mvp/quickstart.md)** - 10-minute setup
- **[Feature Specification](specs/001-bronze-tier-mvp/spec.md)** - Requirements and user stories
- **[Implementation Plan](specs/001-bronze-tier-mvp/plan.md)** - Architecture and decisions
- **[Data Model](specs/001-bronze-tier-mvp/data-model.md)** - Entity definitions
- **[File Interfaces](specs/001-bronze-tier-mvp/contracts/file-interfaces.md)** - Communication contracts

### Silver Tier
- **[Setup Guide](SILVER_TIER_SETUP.md)** - Silver Tier installation and configuration
- **[Feature Specification](specs/002-silver-tier-upgrade/spec.md)** - Silver Tier requirements

### Gold Tier **NEW**
- **[Setup Guide](docs/gold-tier-setup.md)** - Complete setup for all 8 user stories
- **[Troubleshooting Guide](docs/gold-tier-troubleshooting.md)** - 50+ common scenarios and fixes
- **[Encryption & Backup](docs/encryption-backup.md)** - Key management and GDPR data export
- **[Feature Specification](specs/003-gold-tier-upgrade/spec.md)** - Gold Tier requirements and architecture
- **[Task List](specs/003-gold-tier-upgrade/tasks.md)** - Implementation tasks and progress

## Security & Privacy

- ✅ **Local-first**: All data stored locally in Obsidian vault
- ✅ **AES-256-GCM Encryption**: Sensitive contact data encrypted at rest
- ✅ **No cloud sync of credentials**: Gmail tokens stored outside vault
- ✅ **Audit logging**: All actions logged to `/Logs/` with 90-day retention
- ✅ **File quarantine**: Executable files automatically isolated
- ✅ **Rate limiting**: Token bucket algorithm protects 8+ API quotas
- ✅ **Trust evaluation**: <10ms policy enforcement for autonomous actions
- ✅ **GDPR compliance**: Article 20 data portability with one-command export
- ✅ **Encryption key backup**: Secure key rotation and recovery procedures

## Troubleshooting

### Gmail Watcher not detecting emails

```bash
# Check PM2 logs
pm2 logs gmail-watcher --lines 50

# Common fixes:
# - Delete token.json and re-authenticate
# - Verify credentials.json exists
# - Check internet connection
```

### File System Watcher not detecting files

```bash
# Verify vault path
echo $VAULT_PATH

# Check watcher logs
pm2 logs fs-watcher

# Ensure /Inbox folder exists
ls /path/to/vault/Inbox
```

### Dashboard not updating

```bash
# Restart orchestrator
pm2 restart orchestrator

# Manually trigger update
claude "Use dashboard-updater skill to refresh Dashboard.md"
```

## Next Steps

Gold Tier is now complete with 8 fully autonomous user stories!

**Recommended Next Steps**:
1. **Production Hardening**: Add error recovery, retry logic, and comprehensive logging
2. **Multi-user Support**: Extend to support team workflows and shared calendars
3. **Mobile App**: Build companion mobile app for on-the-go approvals
4. **Advanced Analytics**: Machine learning models for predictive task suggestions
5. **Integration Expansion**: Add Slack, Microsoft Teams, Notion, Asana integrations

**Current Implementation Status**:
- ✅ Bronze Tier: Monitoring & Planning (3 processes)
- ✅ Silver Tier: Execution & Automation (3 processes)
- ✅ Gold Tier: Intelligent Autonomy (4 processes, 8 user stories)

See `specs/003-gold-tier-upgrade/tasks.md` for detailed implementation checklist.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
