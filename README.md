# Personal AI Employee - Silver Tier

**Local-first autonomous agent with HITL execution capabilities**

## Overview

A fully autonomous AI Employee system that monitors, plans, and executes tasks with Human-in-the-Loop approval.

### Bronze Tier (Monitoring & Planning)
- ✅ Automated Gmail monitoring (detects important emails within 2 minutes)
- ✅ File drop processing via Obsidian vault /Inbox folder
- ✅ AI-generated task plans using Claude Code
- ✅ Real-time Dashboard in Obsidian showing pending actions

### Silver Tier (Execution & Automation) **NEW**
- ✅ **Email Sending**: Send and reply to emails via Gmail API with approval
- ✅ **Social Media Posting**: Auto-post to LinkedIn, Facebook, Twitter
- ✅ **WhatsApp Monitoring**: Monitor WhatsApp Business for incoming messages
- ✅ **Scheduled Tasks**: Daily briefings, weekly summaries, custom automation

## Quick Start

### Bronze Tier (Monitoring)

For detailed Bronze Tier setup instructions, see: **[specs/001-bronze-tier-mvp/quickstart.md](specs/001-bronze-tier-mvp/quickstart.md)**

### Silver Tier (Execution) **NEW**

For detailed Silver Tier setup instructions, see: **[SILVER_TIER_SETUP.md](SILVER_TIER_SETUP.md)**

**Quick Setup**:
```bash
# 1. Install additional dependencies
uv pip install apscheduler

# 2. Configure MCP servers in .env (see SILVER_TIER_SETUP.md)

# 3. Start Silver Tier processes
pm2 start ecosystem.config.js

# 4. Verify all processes running
pm2 status
```

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

### Components

- **Gmail Watcher**: Monitors inbox every 2 minutes, surfaces important emails
- **File System Watcher**: Monitors /Inbox folder for dropped files
- **Orchestrator**: Detects new items, triggers Claude Code processing
- **Claude Code Skills**: AI-powered email triage, file processing, plan generation
- **Obsidian Vault**: Local-first storage and dashboard

### Folder Structure

```
/path/to/vault/
├── Inbox/              # Drop files here for processing
├── Needs_Action/       # Detected emails and files
├── Plans/              # AI-generated action plans
├── Pending_Approval/   # Items requiring human approval
├── Approved/           # Approved actions (Silver tier+)
├── Done/               # Completed items
├── Logs/               # JSON audit logs
├── Quarantine/         # Unsafe files
├── Dashboard.md        # Real-time status summary
└── Company_Handbook.md # AI behavior rules
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

- **[Quickstart Guide](specs/001-bronze-tier-mvp/quickstart.md)** - 10-minute setup
- **[Feature Specification](specs/001-bronze-tier-mvp/spec.md)** - Requirements and user stories
- **[Implementation Plan](specs/001-bronze-tier-mvp/plan.md)** - Architecture and decisions
- **[Data Model](specs/001-bronze-tier-mvp/data-model.md)** - Entity definitions
- **[File Interfaces](specs/001-bronze-tier-mvp/contracts/file-interfaces.md)** - Communication contracts

## Security & Privacy

- ✅ **Local-first**: All data stored locally in Obsidian vault
- ✅ **No cloud sync of credentials**: Gmail tokens stored outside vault
- ✅ **Audit logging**: All actions logged to `/Logs/` with 90-day retention
- ✅ **File quarantine**: Executable files automatically isolated
- ✅ **Read-only Gmail**: Bronze tier cannot send emails

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

## Next Steps (Silver Tier)

After Bronze Tier is stable, upgrade to Silver Tier for:
- ✅ Email sending/replying via MCP server
- ✅ WhatsApp monitoring
- ✅ LinkedIn auto-posting
- ✅ HITL approval workflow execution
- ✅ Scheduled tasks (daily briefings)

See: `specs/002-silver-tier/spec.md` (create with `/sp.specify` when ready)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
