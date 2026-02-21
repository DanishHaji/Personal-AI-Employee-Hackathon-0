# Quickstart Guide: Bronze Tier MVP Setup

**Feature**: 001-bronze-tier-mvp
**Estimated Setup Time**: 10 minutes (SC-001)
**Prerequisites**: Python 3.13+, UV package manager, Node.js v24+, Obsidian v1.10.6+, Claude Code

---

## Overview

This quickstart guide walks you through setting up the Bronze Tier MVP Personal AI Employee from scratch. By the end, you'll have:

✅ Obsidian vault with proper folder structure
✅ Gmail Watcher monitoring your inbox
✅ File System Watcher monitoring /Inbox folder
✅ Claude Code skills for AI-powered processing
✅ Dashboard.md showing real-time system status

---

## Step 1: Prerequisites Check (2 minutes)

Run these commands to verify you have all required software:

```bash
# Check Python version (must be 3.13+)
python3 --version

# Check UV package manager
uv --version

# Check Node.js version (must be v24+)
node --version

# Check PM2 (install if missing)
pm2 --version

# Check Claude Code
claude --version
```

**If any are missing**:
```bash
# Install UV (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install PM2 globally
npm install -g pm2

# Install Claude Code
# Follow: https://docs.anthropic.com/claude/docs/claude-code
```

**Verify Obsidian**:
- Open Obsidian app
- Version should be 1.10.6 or higher
- Know how to open a vault from a folder

---

## Step 2: Clone Repository & Install Dependencies (3 minutes)

```bash
# Clone the repository
git clone <repository-url> ai-employee
cd ai-employee

# Checkout Bronze Tier branch
git checkout 001-bronze-tier-mvp

# Initialize UV project (creates pyproject.toml and uv.lock)
uv sync

# Verify dependencies installed
uv run python --version
```

---

## Step 3: Gmail API Setup (3 minutes)

**Enable Gmail API**:

1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Desktop app"
   - Download `credentials.json`

**Configure credentials**:

```bash
# Copy credentials.json to project root
cp ~/Downloads/credentials.json .

# Create .env file from template
cp .env.example .env

# Edit .env file
nano .env
```

**.env contents**:
```ini
# Gmail API credentials
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json

# Vault location (will be created in next step)
VAULT_PATH=/path/to/your/vault

# Development mode (set to false for production)
DEV_MODE=true
```

**First-time authentication**:
```bash
# Run Gmail Watcher once to authenticate
uv run python src/watchers/gmail_watcher.py --auth-only

# Browser will open, authorize the app
# token.json will be created automatically
```

---

## Step 4: Create Obsidian Vault (1 minute)

```bash
# Create vault structure
uv run python scripts/init_vault.py --path /path/to/your/vault

# This creates:
# /Inbox/
# /Needs_Action/
# /Plans/
# /Pending_Approval/
# /Approved/
# /Done/
# /Logs/
# /Quarantine/
# Dashboard.md
# Company_Handbook.md
```

**Open vault in Obsidian**:
1. Open Obsidian app
2. Click "Open folder as vault"
3. Select `/path/to/your/vault`
4. You should see Dashboard.md and folder structure

---

## Step 5: Install Claude Code Skills (1 minute)

```bash
# Copy skills to .claude/commands/
mkdir -p .claude/commands
cp skills/*.md .claude/commands/

# Verify skills installed
ls .claude/commands/
# Should show:
# - vault-manager.md
# - email-triage.md
# - file-processor.md
# - dashboard-updater.md

# Test vault-manager skill
claude "Use vault-manager skill to check if vault is accessible"
```

---

## Step 6: Start Watchers with PM2 (1 minute)

```bash
# Start all watchers as background processes
pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3
pm2 start src/watchers/filesystem_watcher.py --name fs-watcher --interpreter python3
pm2 start src/orchestrator.py --name orchestrator --interpreter python3

# Verify all running
pm2 status

# Expected output:
# ┌─────┬───────────────────┬─────────┬─────────┐
# │ id  │ name              │ status  │ uptime  │
# ├─────┼───────────────────┼─────────┼─────────┤
# │ 0   │ gmail-watcher     │ online  │ 0s      │
# │ 1   │ fs-watcher        │ online  │ 0s      │
# │ 2   │ orchestrator      │ online  │ 0s      │
# └─────┴───────────────────┴─────────┴─────────┘

# View logs
pm2 logs gmail-watcher --lines 20

# Enable auto-start on system boot
pm2 startup
pm2 save
```

---

## Step 7: Verify Everything Works (<1 minute)

**Test Email Detection**:
1. Send yourself an important email with subject "Test: Urgent task"
2. Mark it as important in Gmail
3. Wait 2 minutes (Gmail Watcher poll interval)
4. Check Obsidian vault → /Needs_Action/
5. Should see `EMAIL_{id}.md` file

**Test File Drop**:
1. Drop a test PDF into vault's /Inbox/ folder
2. Wait 30 seconds
3. Check /Needs_Action/
4. Should see `FILE_{timestamp}_test.md` and copied PDF

**Check Dashboard**:
1. Open Dashboard.md in Obsidian
2. Should show:
   - Pending Actions: 2 items (test email + test file)
   - Watchers Status: All ✅ Running
   - Recent Activity: Latest actions listed

**Test Claude Code Processing**:
```bash
# Manually trigger processing
claude "Use vault-manager skill to process items in /Needs_Action and create plans"

# Check /Plans/ folder
ls /path/to/your/vault/Plans/
# Should see PLAN_001.md created
```

---

## Troubleshooting

### Gmail Watcher not detecting emails

**Check PM2 logs**:
```bash
pm2 logs gmail-watcher --lines 50
```

**Common issues**:
- **"Token expired"**: Delete token.json and re-run auth: `uv run python src/watchers/gmail_watcher.py --auth-only`
- **"No credentials file"**: Verify `credentials.json` exists and path in .env is correct
- **"Rate limited"**: Wait 1 minute, watcher has exponential backoff

### File System Watcher not detecting files

**Check folder path**:
```bash
# Verify /Inbox exists
ls /path/to/your/vault/Inbox

# Check PM2 logs
pm2 logs fs-watcher
```

**Common issues**:
- **"Path not found"**: Verify VAULT_PATH in .env matches actual vault location
- **"Permission denied"**: Ensure vault folder has read/write permissions

### Dashboard not updating

**Manual refresh**:
```bash
# Trigger dashboard update
claude "Use dashboard-updater skill to refresh Dashboard.md"
```

**Check orchestrator logs**:
```bash
pm2 logs orchestrator
```

**Common issues**:
- **Orchestrator not running**: Restart with `pm2 restart orchestrator`
- **Vault locked**: Close Obsidian, restart orchestrator

### Claude Code skills not found

**Verify skills path**:
```bash
# Check skills installed
ls .claude/commands/

# Should show 4 .md files

# If missing, re-copy
cp skills/*.md .claude/commands/
```

---

## Daily Usage

**Morning Routine**:
1. Open Obsidian vault
2. Check Dashboard.md for pending items
3. Review /Needs_Action/ for urgent emails/files
4. Check /Plans/ for AI-generated task plans

**Adding Files to Process**:
- Drop any file into vault's /Inbox/ folder
- Wait 30 seconds
- File appears in /Needs_Action/ with metadata

**Monitoring System Health**:
```bash
# Check PM2 status
pm2 status

# View recent logs
pm2 logs --lines 20

# Restart if needed
pm2 restart all
```

**Manually Trigger Processing** (if orchestrator not running):
```bash
claude "Use vault-manager to process all items in /Needs_Action"
```

---

## Next Steps (Silver Tier)

After Bronze Tier is working, you can upgrade to Silver Tier which adds:
- ✅ Email sending/replying (MCP server)
- ✅ WhatsApp monitoring
- ✅ LinkedIn auto-posting
- ✅ HITL approval workflow execution
- ✅ Scheduled tasks (daily briefings)

**See**: `specs/002-silver-tier/spec.md` (create with `/sp.specify` when ready)

---

## Configuration Reference

**.env variables**:
```ini
# Required
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json
VAULT_PATH=/absolute/path/to/vault

# Optional
DEV_MODE=true                    # Dry run mode
CHECK_INTERVAL=120               # Gmail poll interval (seconds)
URGENT_KEYWORDS=urgent,asap,invoice,payment,help  # Comma-separated
```

**Company_Handbook.md** (edit to customize AI behavior):
```markdown
# AI Employee Rules

## Email Response Guidelines
- Always be polite and professional
- Respond to client emails within 24 hours
- Flag any payment request over $100 for approval

## File Processing
- Quarantine executable files immediately
- Alert on files over 50MB

## Plan Generation
- Include 3-7 specific steps
- First step should always clarify objective
- Last step should verify completion
```

---

## Uninstall

**Stop and remove PM2 processes**:
```bash
pm2 stop all
pm2 delete all
pm2 unstartup
```

**Remove vault** (CAUTION: deletes all data):
```bash
rm -rf /path/to/your/vault
```

**Uninstall dependencies**:
```bash
cd ai-employee
rm -rf .venv uv.lock
```

---

## Success Criteria Checklist

After setup, verify these success criteria from spec.md:

- [ ] **SC-001**: Setup completed in under 10 minutes ✓
- [ ] **SC-002**: Gmail detects emails within 2 minutes ✓
- [ ] **SC-003**: File System processes files within 30 seconds ✓
- [ ] **SC-004**: Claude Code generates plans for clear requests ✓
- [ ] **SC-005**: System runs 24 hours without crashes (test overnight)
- [ ] **SC-006**: Dashboard updates within 60 seconds of changes ✓
- [ ] **SC-007**: Can identify urgent emails from Dashboard only ✓
- [ ] **SC-008**: No credentials in vault (search for "password", "token") ✓

**If all checked**: Bronze Tier MVP is fully operational! 🎉
