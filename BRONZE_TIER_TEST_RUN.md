# 🧪 Bronze Tier - Complete Test Run Guide

**Version**: 1.0 (Bronze Tier MVP)
**Last Updated**: 2026-02-24
**Estimated Time**: 30-40 minutes

Ye file Bronze Tier ko test aur run karne ke liye complete guide hai. Step-by-step follow karein.

---

## ✅ Pre-Requisites Check

Sabse pehle ye check kar lein ke sab installed hai:

```bash
# 1. Python version (3.13+ chahiye)
python3 --version

# Agar purana version hai to:
# Download from: https://www.python.org/downloads/

# 2. UV package manager check
uv --version

# Agar nahi hai to install:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Phir terminal restart karein

# 3. Node.js check (v24+ chahiye)
node --version

# Agar nahi hai to:
# Download from: https://nodejs.org/

# 4. PM2 install
npm install -g pm2

# 5. Obsidian
# Download from: https://obsidian.md/download

# 6. Claude Code CLI (optional for plan generation)
claude --version
# Install from: https://docs.anthropic.com/claude/docs/claude-code
```

**✅ Checklist**:
- [ ] Python 3.13+
- [ ] UV package manager
- [ ] Node.js v24+
- [ ] PM2
- [ ] Obsidian
- [ ] Claude Code (optional)

---

## 📦 Step 1: Project Setup (2 minutes)

```bash
# Project directory mein jao
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# Dependencies install (UV se - FR-021 requirement)
uv sync
```

**Expected Output**:
```
Resolved XX packages in XXXms
Installed XX packages in XXXms
```

**❌ Agar Error Aaye:**

### Error: "uv: command not found"
```bash
# UV install karein
curl -LsSf https://astral.sh/uv/install.sh | sh

# Terminal restart
source ~/.bashrc  # Linux/WSL
source ~/.zshrc   # macOS

# Retry
uv sync
```

### Error: "Python 3.13+ required"
```bash
# Python 3.13 install karein
# Ubuntu/WSL:
sudo apt update
sudo apt install python3.13

# macOS:
brew install python@3.13

# Windows: Download from python.org

# Retry
uv sync
```

---

## 🗂️ Step 2: Obsidian Vault Create (3 minutes)

```bash
# Vault path decide karein (apni marzi ka location)
# Example paths:
# Windows: C:/Users/YourName/Desktop/AI-Employee-Vault
# Linux/macOS: $HOME/Desktop/AI-Employee-Vault
# WSL: /mnt/c/Users/YourName/Desktop/AI-Employee-Vault

# Path set karein (apna path yahan dalein)
export VAULT_PATH="$HOME/Desktop/AI-Employee-Vault"

# .env file mein save (important!)
echo "VAULT_PATH=$VAULT_PATH" > .env

# Verify .env file
cat .env
# Output: VAULT_PATH=/your/vault/path

# Vault structure create
uv run python scripts/init_vault.py --path "$VAULT_PATH"
```

**Expected Output**:
```
Creating Obsidian vault structure at: /your/vault/path
✓ Created folders: Inbox, Needs_Action, Plans, Pending_Approval, Approved, Done, Logs, Quarantine
✓ Created Dashboard.md
✓ Created Company_Handbook.md
Vault initialization complete!
```

**Verify Vault:**
```bash
ls -la "$VAULT_PATH"
```

**Expected Folders**:
```
Inbox/              ← Drop files here
Needs_Action/       ← Detected items appear here
Plans/              ← AI plans
Pending_Approval/   ← Approval needed
Approved/           ← Approved items
Done/               ← Completed
Logs/               ← System logs
Quarantine/         ← Unsafe files
Dashboard.md        ← Main dashboard
Company_Handbook.md ← AI rules
```

**❌ Agar Error Aaye:**

### Error: "VAULT_PATH not set"
```bash
# Manually .env file banao
nano .env
# Add this line (apna path):
VAULT_PATH=/your/actual/vault/path
# Save: Ctrl+X, Y, Enter

# Verify
cat .env
```

### Error: "Permission denied"
```bash
# Different path try karein jahan write permission hai
export VAULT_PATH="$HOME/AI-Employee-Vault"
echo "VAULT_PATH=$VAULT_PATH" > .env
uv run python scripts/init_vault.py --path "$VAULT_PATH"
```

---

## 📧 Step 3: Gmail API Setup (15 minutes)

**Ye sabse important step hai!**

### Part A: Google Cloud Console Setup

1. **Browser open**: https://console.cloud.google.com/

2. **Sign in** apne Gmail se

3. **New Project banao**:
   - Top bar mein "Select a project" click
   - "NEW PROJECT" click
   - Project name: `Personal AI Employee`
   - Click "CREATE"
   - Wait ~30 seconds

4. **Project select karo** (top bar se newly created project)

5. **Gmail API enable**:
   - Left menu → "APIs & Services" → "Library"
   - Search box mein type: `Gmail API`
   - "Gmail API" click
   - "ENABLE" button click
   - Wait ~10 seconds

6. **OAuth Consent Screen**:
   - Left menu → "APIs & Services" → "OAuth consent screen"
   - Select: **"External"**
   - "CREATE" click
   - Fill karo:
     - **App name**: `Personal AI Employee`
     - **User support email**: (dropdown se apna email select)
     - **Developer contact email**: (apna email type)
   - "SAVE AND CONTINUE" click

7. **Scopes Add**:
   - "ADD OR REMOVE SCOPES" click
   - Filter box mein: `Gmail API`
   - Check karo:
     - ☑️ `.../auth/gmail.readonly` (Read all resources)
   - "UPDATE" click
   - "SAVE AND CONTINUE" click

8. **Test Users Add**:
   - "+ ADD USERS" click
   - Apna email address type
   - "ADD" click
   - "SAVE AND CONTINUE" click
   - "BACK TO DASHBOARD" click

9. **Credentials Create**:
   - Left menu → "Credentials"
   - "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: **"Desktop app"**
   - Name: `AI Employee Desktop`
   - "CREATE" click
   - **Pop-up dikhega** → "DOWNLOAD JSON" click
   - File save ho jayegi (default name: `client_secret_...json`)

### Part B: Credentials File Setup

```bash
# Downloads folder se credentials file copy (apna actual path use karein)
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# Windows (from Downloads):
cp /mnt/c/Users/YourUsername/Downloads/client_secret_*.json ./credentials.json

# macOS:
# cp ~/Downloads/client_secret_*.json ./credentials.json

# Linux:
# cp ~/Downloads/client_secret_*.json ./credentials.json

# Verify file hai
ls -la credentials.json
```

**Expected**: File size ~500-600 bytes

**❌ Agar credentials.json nahi mili:**
```bash
# Downloads folder mein dekho
ls /mnt/c/Users/*/Downloads/client_secret*.json  # Windows/WSL
# ls ~/Downloads/client_secret*.json  # macOS/Linux

# Manually copy karo
```

### Part C: First Time Authentication

```bash
# Gmail watcher run (authentication trigger)
uv run python src/watchers/gmail_watcher.py
```

**Kya Hoga:**
1. Browser **automatically khulega** (agar nahi khula to manually URL copy paste)
2. Google sign-in screen
3. Apna Gmail account select
4. **Warning dikhegi**: "Google hasn't verified this app"
   - Click: **"Advanced"** → **"Go to Personal AI Employee (unsafe)"**
   - Ye normal hai test apps ke liye ✅
5. Permissions screen: **"Allow"** click
6. Browser mein success message
7. Terminal mein: `[GmailWatcher] Started at ...` dikhega

**Ab watcher ko STOP karo**: Press `Ctrl+C`

**Verify token created**:
```bash
ls -la token.json
```

**Expected**: `token.json` file dikhai degi (~1-2 KB)

**❌ Common Authentication Errors:**

### Error: "credentials.json not found"
```bash
# File check
ls -la credentials.json

# Agar nahi hai to Google Cloud Console se phir download karo
# Aur project root mein exactly "credentials.json" naam se save karo
```

### Error: "Browser didn't open"
```bash
# URL manually copy paste karo
# Terminal mein URL dikhega starting with: https://accounts.google.com/o/oauth2/...
# Copy karo aur browser mein paste
```

### Error: "Redirect URI mismatch"
```bash
# Credentials phir se download karo
# Application type "Desktop app" hona chahiye (NOT Web app)
rm credentials.json
# Google Cloud Console → Credentials → Download again
```

### Error: "Access blocked"
```bash
# Test users check:
# Google Cloud Console → OAuth consent screen → Test users
# Apna email add hai ya nahi verify karo
# Agar nahi to add karo, phir retry
rm token.json
uv run python src/watchers/gmail_watcher.py
```

---

## 🖥️ Step 4: Obsidian Vault Open (2 minutes)

```bash
# Obsidian app open karo
# Windows: Start menu → Obsidian
# macOS: Applications → Obsidian
# Linux: Application menu → Obsidian

# Obsidian mein:
# File → Open folder as vault → Select your vault path
# Example: C:/Users/YourName/Desktop/AI-Employee-Vault
```

**Obsidian mein aapko dikhega**:
- Left sidebar: Folders (Inbox, Needs_Action, etc.)
- `Dashboard.md` file (ye aapka main control panel)
- `Company_Handbook.md` (AI rules)

**Dashboard.md open karo** - ye aapka main dashboard hai

**Initial Dashboard Status**:
```markdown
## Status Overview
- Pending Actions: 0 items
- Pending Approvals: 0 items
- System Health: ⚠️ Not Started

## Watchers Status
- Gmail Watcher: ❌ Not running
- Filesystem Watcher: ❌ Not running
- Orchestrator: ❌ Not running
```

---

## 🚀 Step 5: System Start with PM2 (2 minutes)

```bash
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# All watchers start (ecosystem config se)
pm2 start ecosystem.config.js

# Wait 5 seconds
sleep 5

# Status check
pm2 status
```

**Expected Output**:
```
┌────┬───────────────────────┬─────────┬─────┬─────────┬──────────┐
│ id │ name                  │ status  │ ↺   │ cpu     │ memory   │
├────┼───────────────────────┼─────────┼─────┼─────────┼──────────┤
│ 0  │ gmail-watcher         │ online  │ 0   │ 0%      │ 45.2mb   │
│ 1  │ filesystem-watcher    │ online  │ 0   │ 0%      │ 40.1mb   │
│ 2  │ orchestrator          │ online  │ 0   │ 0%      │ 38.5mb   │
└────┴───────────────────────┴─────────┴─────┴─────────┴──────────┘
```

**✅ Check Points**:
- All status = **"online"** ✅
- Restart count (↺) = **0** ✅
- Memory < 100mb ✅

**Logs dekho (optional)**:
```bash
pm2 logs --lines 20
```

**Expected Log Messages**:
```
[gmail-watcher] Started at 2026-02-24T...
[gmail-watcher] Watching Gmail inbox every 120 seconds
[filesystem-watcher] Started at 2026-02-24T...
[filesystem-watcher] Watching /path/to/vault/Inbox
[orchestrator] Started at 2026-02-24T...
[orchestrator] Watching /Needs_Action/ folder
```

**Obsidian mein Dashboard.md refresh karo** (Ctrl+R ya file close/open):
```markdown
## Watchers Status
- Gmail Watcher: ✅ Running (last check: HH:MM)
- Filesystem Watcher: ✅ Running
- Orchestrator: ✅ Running
```

**❌ PM2 Errors:**

### Error: "pm2: command not found"
```bash
# PM2 install
npm install -g pm2

# Agar npm nahi hai
# Node.js install: https://nodejs.org/
```

### Error: "VAULT_PATH not set"
```bash
# .env file check
cat .env

# Agar empty ya wrong:
export VAULT_PATH="$HOME/Desktop/AI-Employee-Vault"
echo "VAULT_PATH=$VAULT_PATH" > .env

# Retry
pm2 restart all
```

### Error: Process "errored" or "stopped"
```bash
# Logs check for specific error
pm2 logs gmail-watcher --err --lines 50
pm2 logs filesystem-watcher --err --lines 50

# Common fixes:
# 1. token.json missing → Re-authenticate
# 2. VAULT_PATH wrong → Fix .env
# 3. Python error → Check uv sync completed
```

---

## ✉️ Step 6: Test Email Detection (5 minutes)

**Ab actual test karenge!**

### 6.1: Test Email Bhejo

**Gmail web open karo**: https://mail.google.com/

**Compose new email**:
- **To**: Your own email (apne aap ko)
- **Subject**: `URGENT: Testing AI Employee System`
- **Body**:
  ```
  This is a test email to verify my AI Employee is detecting emails.

  Please process this and create a plan.

  Thanks!
  ```
- Click **Send**

### 6.2: Wait & Monitor (2-3 minutes)

```bash
# Gmail Watcher har 2 minute (120 seconds) mein check karta hai
# So maximum 2 minutes wait

# Logs dekho live
pm2 logs gmail-watcher
```

**Expected Logs**:
```
[gmail-watcher] Checking for important emails...
[gmail-watcher] Found 1 important/urgent emails
[gmail-watcher] Created 1 new email entities
```

Press `Ctrl+C` to stop watching logs

### 6.3: Verify Email Detected

```bash
# Check Needs_Action folder
ls "$VAULT_PATH/Needs_Action/"
```

**Expected Output**:
```
EMAIL_abc123_20260224_143022.md
```

**File content dekho**:
```bash
cat "$VAULT_PATH/Needs_Action/EMAIL_"*.md | head -30
```

**Expected Content**:
```markdown
---
type: email
from: your-email@gmail.com
subject: URGENT: Testing AI Employee System
received: 2026-02-24T14:30:00Z
priority: high
status: pending
email_id: abc123xyz
---

## Email Content

This is a test email to verify my AI Employee...
```

### 6.4: Obsidian Check

**Obsidian mein check karo**:
1. `Needs_Action/` folder open karo
2. Email file dikhai degi
3. Click karke open karo - poora email dikhega
4. `Dashboard.md` open karo

**Dashboard mein updated count**:
```markdown
## Status Overview
- Pending Actions: 1 item  ← Ye 1 ho gaya!
- System Health: ✅ Healthy

## Recent Activity
1. [14:30] Email detected: URGENT: Testing AI Employee → /Needs_Action/EMAIL_...
```

**✅ SUCCESS! Email detection kaam kar raha hai! 🎉**

**❌ Agar Email Detect Nahi Hua:**

### Problem: No email in Needs_Action

```bash
# 1. Check Gmail watcher logs
pm2 logs gmail-watcher --lines 50

# 2. Possible issues:

# Issue A: Token expired
# Fix:
rm token.json
uv run python src/watchers/gmail_watcher.py
# Re-authenticate, then:
pm2 restart gmail-watcher

# Issue B: Email doesn't match query
# Fix: Subject mein "URGENT" ya "IMPORTANT" word hona chahiye
# Ya Gmail mein email ko "Important" mark karo

# Issue C: Watcher crashed
pm2 status
# Agar "errored" hai to:
pm2 restart gmail-watcher
pm2 logs gmail-watcher --err

# Issue D: Time nahi hua abhi (< 2 minutes)
# Wait full 2 minutes, then check again
```

---

## 📁 Step 7: Test File Drop (2 minutes)

Ab file drop test karte hain.

### 7.1: File Drop Karo

```bash
# Simple test file banao
echo "This is a test document for AI Employee testing." > "$VAULT_PATH/Inbox/test-document.txt"

# Wait 10 seconds (filesystem watcher real-time hai)
sleep 10

# Check Needs_Action
ls "$VAULT_PATH/Needs_Action/"
```

**Expected**:
```
EMAIL_abc123_20260224_143022.md     ← Previous email
test-document.txt                   ← Your file (moved from Inbox)
test-document.txt.md                ← Metadata file
```

### 7.2: Metadata File Dekho

```bash
cat "$VAULT_PATH/Needs_Action/test-document.txt.md"
```

**Expected Content**:
```markdown
---
type: file_drop
original_name: test-document.txt
size: 52
file_type: .txt
received: 2026-02-24T14:35:00Z
status: pending
quarantined: false
---

## File Information

A new file was dropped into the Inbox for processing.

**Location**: `/Needs_Action/test-document.txt`
**Size**: 0.05 KB
**Type**: Text File
```

### 7.3: Obsidian Check

**Obsidian mein**:
1. `Needs_Action/` folder refresh
2. `test-document.txt` aur `test-document.txt.md` dikhegi
3. `Dashboard.md` check:

```markdown
## Status Overview
- Pending Actions: 3 items  ← 1 email + 2 files (file + metadata)

## Recent Activity
1. [14:35] File dropped: test-document.txt → /Needs_Action
2. [14:30] Email detected: URGENT: Testing AI Employee → /Needs_Action/...
```

**✅ SUCCESS! File drop bhi kaam kar raha hai! 🎉**

### 7.4: Test Quarantine (Optional - Security Test)

```bash
# Unsafe file banao (.exe extension)
echo "fake malware" > "$VAULT_PATH/Inbox/virus.exe"

# Wait 10 seconds
sleep 10

# Check Quarantine (file yahan honi chahiye)
ls "$VAULT_PATH/Quarantine/"
# Output: virus.exe

# Check Needs_Action for alert
ls "$VAULT_PATH/Needs_Action/ALERT_"*
# Output: ALERT_quarantined_virus.exe_20260224_143522.md
```

**Alert file open karo**:
```bash
cat "$VAULT_PATH/Needs_Action/ALERT_"*.md
```

**Expected**: Security warning with instructions

**✅ Quarantine system bhi kaam kar raha hai!**

**❌ Agar File Detect Nahi Hua:**

```bash
# Check filesystem watcher logs
pm2 logs filesystem-watcher --lines 50

# Check Inbox permissions
ls -la "$VAULT_PATH/Inbox"

# Restart watcher
pm2 restart filesystem-watcher

# Try again
echo "test 2" > "$VAULT_PATH/Inbox/test2.txt"
```

---

## 🤖 Step 8: Test Plan Generation (Optional - 5 minutes)

**Note**: Ye step Claude Code CLI chahiye. Agar nahi hai to skip kar sakte hain.

```bash
# Check Claude Code installed hai
claude --version
```

**Agar installed hai:**

### Manual Plan Trigger:

```bash
# Orchestrator automatically plans banata hai
# But manually bhi trigger kar sakte hain:

claude "Use vault-manager skill with action=plan and file_path=$VAULT_PATH/Needs_Action/EMAIL_*.md"
```

**Wait 30 seconds, then check:**

```bash
# Plans folder check
ls "$VAULT_PATH/Plans/"
```

**Expected**:
```
PLAN_001_respond-to-urgent-test-email.md
```

**Plan file content**:
```bash
cat "$VAULT_PATH/Plans/PLAN_"*.md
```

**Expected Structure**:
```markdown
---
plan_id: PLAN_001
title: Respond to Urgent Test Email
source_type: email
created: 2026-02-24T14:40:00Z
objective: Address email from your-email@gmail.com
approval_required: false
status: draft
---

# Plan: Respond to Urgent Test Email

## Objective
Address urgent test email and respond appropriately.

## Steps
- [ ] 1. Review email thoroughly and clarify objective
- [ ] 2. Draft appropriate response
- [ ] 3. Review response for clarity and tone
- [ ] 4. Send response within 24 hours
- [ ] 5. Verify task completion and move email to /Done/
```

**✅ Plan generation kaam kar raha hai!**

**Agar Claude Code nahi hai:**
- Skip kar do ye step
- Plans manually banayenge later
- System baaki sab kaam kar raha hai

---

## 🔒 Step 9: Security Audit (2 minutes)

```bash
# Security check script chalayen
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"
uv run python scripts/security_audit.py --vault-path "$VAULT_PATH"
```

**Expected Output**:
```
======================================================================
Security Audit - Personal AI Employee Bronze Tier MVP
======================================================================

Check 1: Scanning vault for credentials...
  ✅ PASSED: No credentials found in vault

Check 2: Verifying credentials location...
  ✓ credentials.json correctly in project root
  ✓ token.json correctly in project root
  ✅ PASSED: Credentials correctly stored outside vault

Check 3: Verifying .gitignore coverage...
  ✓ .gitignore includes all required patterns
  ✅ PASSED: .gitignore properly configured

Check 4: Checking git-tracked files...
  ✅ PASSED: No credentials in git-tracked files

======================================================================
AUDIT SUMMARY
======================================================================
✅ ALL CHECKS PASSED

Security status: COMPLIANT
- No credentials in Obsidian vault (SC-008)
- Credentials outside vault (FR-017)
- .gitignore properly configured
- No credentials in version control
======================================================================
```

**✅ Security audit pass ho gaya!**

**❌ Agar Fail Hua:**

```bash
# Check karo kya issue hai output mein
# Common issues:

# Issue: credentials.json in vault
# Fix: Move to project root
mv "$VAULT_PATH/credentials.json" ./credentials.json

# Issue: .gitignore missing patterns
# Fix: Add to .gitignore
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
echo ".env" >> .gitignore
```

---

## 📊 Step 10: Final Dashboard Check (2 minutes)

**Obsidian mein Dashboard.md final check**:

**Expected Final State**:
```markdown
# AI Employee Dashboard

**Last Updated**: 2026-02-24 14:45:00

## Status Overview
- **Pending Actions**: 3 items
- **Pending Approvals**: 0 items
- **System Health**: ✅ Healthy

## Recent Activity
1. [14:40] Plan created: Respond to Urgent Test Email → /Plans/PLAN_001.md
2. [14:35] File dropped: test-document.txt → /Needs_Action
3. [14:30] Email detected: URGENT: Testing AI Employee → /Needs_Action/EMAIL_xxx.md
4. [14:28] System started: All watchers initialized

## Watchers Status
- **Gmail Watcher**: ✅ Running (last check: 14:44)
- **Filesystem Watcher**: ✅ Running (last heartbeat: 14:45)
- **Orchestrator**: ✅ Running

---
*This dashboard is automatically updated by the AI Employee system*
```

**✅ Sab kaam kar raha hai!**

---

## 🎉 SUCCESS! Bronze Tier Running Successfully!

Congratulations! Aapka AI Employee ab live hai aur kaam kar raha hai! 🚀

### ✅ Working Features:

1. **Gmail Monitoring** 📧
   - ✅ Emails detect ho rahe hain (2 minute interval)
   - ✅ Important/urgent emails automatically surface
   - ✅ Needs_Action mein save ho rahe hain

2. **File Drop Processing** 📁
   - ✅ Inbox monitoring real-time
   - ✅ Files automatically process
   - ✅ Metadata creation

3. **Security** 🔒
   - ✅ Unsafe files quarantine
   - ✅ No credentials in vault
   - ✅ Security audit passed

4. **Dashboard** 📊
   - ✅ Real-time updates
   - ✅ Pending counts accurate
   - ✅ System health visible

5. **24/7 Operation** 🔄
   - ✅ PM2 auto-restart
   - ✅ Logging active
   - ✅ Heartbeat monitoring

---

## 📖 Daily Usage Guide

### Morning Routine:

```bash
# 1. System status check
pm2 status

# 2. Obsidian open karo
# Dashboard.md dekho

# 3. Needs_Action items check
# Obsidian mein Needs_Action/ folder
```

### Throughout Day:

- **Emails**: Automatic detect (har 2 min)
- **Files**: Inbox mein drop karo
- **Dashboard**: Current status dekho

### Evening:

```bash
# Processed items move to Done
# Obsidian mein manually drag-drop to /Done/ folder

# Today's audit log dekho
cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | tail -20
```

---

## 🛠️ Useful Commands Reference

```bash
# PM2 Commands
pm2 status                    # All processes status
pm2 logs                      # All logs live
pm2 logs gmail-watcher        # Specific watcher logs
pm2 restart all               # Restart all processes
pm2 stop all                  # Stop all
pm2 delete all                # Remove from PM2

# System Check
pm2 monit                     # Real-time CPU/memory monitor
pm2 list                      # Process list

# Logs
pm2 logs --lines 100          # Last 100 log lines
pm2 logs --err                # Only error logs

# Auto-start on boot (optional)
pm2 startup                   # Setup auto-start
pm2 save                      # Save current process list

# Audit Logs
cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json"  # Today's log
cat "$VAULT_PATH/Logs/heartbeat.json"          # Heartbeat status

# Security Audit
uv run python scripts/security_audit.py --vault-path "$VAULT_PATH"
```

---

## 🆘 Troubleshooting Common Issues

### Issue: Email detect nahi ho rahi

```bash
# Solution 1: Token refresh
rm token.json
uv run python src/watchers/gmail_watcher.py
# Re-authenticate, then:
pm2 restart gmail-watcher

# Solution 2: Check email subject
# Subject mein "URGENT" ya "IMPORTANT" hona chahiye
# Ya Gmail mein email ko "Important" mark karo

# Solution 3: Wait time
# Full 2 minutes wait karo (120 seconds)
```

### Issue: File detect nahi ho rahi

```bash
# Solution 1: Watcher restart
pm2 restart filesystem-watcher

# Solution 2: Permissions check
ls -la "$VAULT_PATH/Inbox"

# Solution 3: Different file try
echo "test $(date +%s)" > "$VAULT_PATH/Inbox/test-$(date +%s).txt"
```

### Issue: Dashboard update nahi ho raha

```bash
# Solution 1: Orchestrator restart
pm2 restart orchestrator

# Solution 2: Manual update
claude "Use dashboard-updater skill to refresh Dashboard.md"

# Solution 3: Obsidian refresh
# Ctrl+R ya file close/reopen
```

### Issue: PM2 process crashed (status: errored)

```bash
# Check error logs
pm2 logs <process-name> --err --lines 50

# Restart
pm2 restart <process-name>

# Delete and re-add
pm2 delete all
pm2 start ecosystem.config.js
```

### Issue: VAULT_PATH error

```bash
# Check .env
cat .env

# Re-set if wrong
export VAULT_PATH="/correct/path/to/vault"
echo "VAULT_PATH=$VAULT_PATH" > .env

# Restart all
pm2 restart all
```

### Issue: UV/Python errors

```bash
# Re-sync dependencies
uv sync

# Check Python version
python3 --version  # Should be 3.13+

# Re-install if needed
uv pip install -e .
```

---

## 📝 Customization - Company_Handbook.md

Apne rules add kar sakte hain:

**Obsidian mein `Company_Handbook.md` open karo aur edit:**

```markdown
## Email Rules

### Urgent Keywords (custom)
- urgent
- asap
- critical
- invoice
- payment
- YOUR_CUSTOM_KEYWORDS_HERE

### Priority Contacts
- boss@company.com → Always high priority
- client@important.com → High priority
- team@internal.com → Medium priority

### Auto-Response Rules
- Meeting requests: Check calendar first
- Invoice requests: Verify amount < $100
- Questions: Research before responding
```

Save karo, watchers automatically read karenge!

---

## 🎯 Next Steps

### Aaj (Today):
- ✅ System setup complete
- ✅ Tests passed
- ✅ System running

### Agle 2-3 Din (Next 2-3 days):
- ✅ Daily use karo
- ✅ Real emails/files ko process karo
- ✅ Company_Handbook.md customize karo
- ✅ Dekho kaise kaam kar raha hai

### Phir (Then):
- ✅ Feedback do (kya achha, kya improve)
- ✅ Ready for **Silver Tier**? (email sending, WhatsApp, LinkedIn)
- ✅ Hum aage badhenge!

---

## 📚 Documentation Files

Agar detail chahiye:

```bash
# Gmail setup complete guide
cat docs/gmail-api-setup.md

# Full E2E test
cat docs/e2e-test-guide.md

# Security details
cat docs/success-criteria-validation.md

# 24-hour stability test
cat docs/24hour-stability-test.md

# Specification
cat specs/001-bronze-tier-mvp/spec.md

# Architecture
cat specs/001-bronze-tier-mvp/plan.md
```

---

## ✅ Final Checklist

Ye sab check ho gaya?

- [ ] Python 3.13+ installed
- [ ] UV package manager working
- [ ] Dependencies installed (`uv sync`)
- [ ] Obsidian vault created
- [ ] Gmail API credentials setup
- [ ] `credentials.json` and `token.json` present
- [ ] PM2 running all 3 processes (online status)
- [ ] Test email detected in Needs_Action/
- [ ] Test file detected in Needs_Action/
- [ ] Dashboard showing correct counts
- [ ] Security audit passed
- [ ] Obsidian vault accessible

**Agar sab ✅ hai to system ready hai!** 🎉

---

## 💬 Got Issues?

**Agar koi problem hai:**

1. Is file mein troubleshooting section dekho (upar)
2. Specific error logs share karo:
   ```bash
   pm2 logs --lines 50 --err
   ```
3. Kaunsa step fail hua batao
4. Main help karunga! 💪

---

## 🚀 Silver Tier Preview

**Jab Bronze stable ho jaye, Silver mein ye milega:**

- ✅ **Email Sending** - Reply kar sakte hain
- ✅ **WhatsApp** - Messages monitor
- ✅ **LinkedIn** - Auto-posting
- ✅ **HITL Execution** - Approved plans execute
- ✅ **Scheduled Tasks** - Daily briefings

**Silver start karne ke liye:**
```bash
git checkout -b 002-silver-tier
/sp.specify
```

**Phir mujhe batana!** 🎯

---

**Last Updated**: 2026-02-24
**Version**: Bronze Tier MVP v1.0
**Status**: ✅ Production Ready

---

**Happy Testing! 🧪🚀**

Koi issue ho to turant batana, main help karunga! 💯
