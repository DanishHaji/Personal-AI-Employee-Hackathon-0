# Silver Tier Quickstart Guide

**Feature**: Silver Tier - Autonomous Task Execution & Multi-Channel Communication
**Date**: 2026-02-25
**Audience**: Developers implementing or testing Silver Tier

## Overview

This guide walks through setting up, configuring, and testing Silver Tier features. Expected time: 30-45 minutes (excluding MCP server setup).

**Prerequisites**:
- Bronze Tier fully functional (email monitoring, file drop, vault management)
- UV installed (0.10+)
- Python 3.12+ (3.13+ recommended)
- Obsidian vault initialized
- PM2 installed globally (`npm install -g pm2`)

---

## Step 1: Install Dependencies

### 1.1 Add Silver Tier Packages

```bash
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# Add Silver Tier dependencies via UV
uv add mcp apscheduler requests jsonschema

# Verify installation
uv pip list | grep -E "(mcp|apscheduler|requests|jsonschema)"
```

**Expected output**:
```
apscheduler      3.10.4
jsonschema       4.20.0
mcp              0.9.2
requests         2.31.0
```

### 1.2 Sync Dependencies

```bash
uv sync
```

**Expected**: No errors, all dependencies resolved.

---

## Step 2: Configure MCP Servers

Silver Tier requires 5 MCP servers (Gmail send, LinkedIn, Facebook, Twitter, WhatsApp). You can configure some or all based on your testing needs.

### 2.1 Update .env File

Copy `.env.example` to `.env` if not already done:

```bash
cp .env.example .env
```

Edit `.env` to add MCP server URLs:

```bash
# Gmail MCP Server (for sending emails)
GMAIL_MCP_URL=http://localhost:3001
# If using hosted MCP service, use their URL instead

# Social Media MCP Servers
LINKEDIN_MCP_URL=http://localhost:3002
FACEBOOK_MCP_URL=http://localhost:3003
TWITTER_MCP_URL=http://localhost:3004

# WhatsApp Business MCP Server
WHATSAPP_MCP_URL=http://localhost:3005
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id

# Development Mode (prevents real API calls during testing)
DRY_RUN=false  # Set to true for testing without real API calls
```

### 2.2 MCP Server Setup (Optional)

**If you have MCP servers running**:
- Ensure each MCP server is accessible at the configured URL
- Test connectivity: `curl http://localhost:3001/health` (should return 200 OK)

**If you don't have MCP servers**:
- Set `DRY_RUN=true` in .env
- Executor will log actions without making real MCP calls
- Useful for testing workflow without external integrations

**MCP Server Documentation**: See `docs/mcp-server-setup.md` (to be created) for detailed MCP server configuration.

---

## Step 3: Initialize Vault for Silver Tier

Silver Tier adds `/Approved/` folder and extends `/Logs/` with state files.

### 3.1 Run Init Script

```bash
uv run python src/init_vault.py --vault-path "$VAULT_PATH"
```

**Expected**: Creates `/Approved/` folder if not exists.

### 3.2 Verify Vault Structure

```bash
ls "$VAULT_PATH"
```

**Expected folders**:
- Inbox/
- Needs_Action/
- Plans/
- Approved/ ← NEW for Silver Tier
- Pending_Approval/ (placeholder for Gold Tier)
- Done/
- Logs/
- Quarantine/

---

## Step 4: Configure Scheduled Tasks

Define scheduled tasks in Company_Handbook.md.

### 4.1 Edit Company_Handbook.md

```bash
nano "$VAULT_PATH/Company_Handbook.md"
```

Add scheduled tasks section at the end:

```yaml
## Scheduled Tasks

scheduled_tasks:
  - task_id: TASK_daily_briefing_1708876200
    task_name: "daily_briefing"
    task_type: briefing
    schedule_pattern: "0 9 * * *"
    recurrence_rule:
      frequency: daily
      time: "09:00"
    last_execution: null
    next_execution: "2026-02-26T09:00:00Z"
    enabled: true
    output_path: "/Needs_Action/"
    parameters:
      include_pending: true
      include_completed_24h: true
      include_urgent: true
    created_at: "2026-02-25T10:00:00Z"
    updated_at: "2026-02-25T10:00:00Z"
```

Save and exit (Ctrl+X, Y, Enter).

---

## Step 5: Update PM2 Configuration

Add executor and scheduler processes to ecosystem.config.js.

### 5.1 Edit ecosystem.config.js

```bash
nano ecosystem.config.js
```

Add two new process configurations:

```javascript
// Executor (HITL Execution Engine)
apps.push({
  name: 'executor',
  script: 'src/executor.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/executor-error.log',
  out_file: './logs/pm2/executor-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000
});

// Scheduler (Scheduled Tasks Engine)
apps.push({
  name: 'scheduler',
  script: 'src/scheduler.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/scheduler-error.log',
  out_file: './logs/pm2/scheduler-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000
});
```

Save and exit.

---

## Step 6: Start Silver Tier Processes

### 6.1 Stop Existing PM2 Processes (if running)

```bash
pm2 stop all
```

### 6.2 Start All Processes

```bash
pm2 start ecosystem.config.js
```

### 6.3 Verify All Processes Running

```bash
pm2 status
```

**Expected output** (5-6 processes depending on Gmail enabled):
```
┌─────┬────────────────────┬─────────┬─────────┬──────────┐
│ id  │ name               │ status  │ restart │ uptime   │
├─────┼────────────────────┼─────────┼─────────┼──────────┤
│ 0   │ gmail-watcher      │ online  │ 0       │ 5s       │ (optional)
│ 1   │ filesystem-watcher │ online  │ 0       │ 5s       │
│ 2   │ orchestrator       │ online  │ 0       │ 5s       │
│ 3   │ executor           │ online  │ 0       │ 5s       │ ← NEW
│ 4   │ scheduler          │ online  │ 0       │ 5s       │ ← NEW
│ 5   │ whatsapp-watcher   │ online  │ 0       │ 5s       │ ← NEW (if enabled)
└─────┴────────────────────┴─────────┴─────────┴──────────┘
```

### 6.4 Check Logs for Errors

```bash
pm2 logs executor --lines 10
pm2 logs scheduler --lines 10
```

**Expected**: No errors, logs show "Started" or "Watching" messages.

---

## Test Scenario 1: Email Sending (US1 - P1)

**Objective**: Test HITL execution workflow for email sending.

**Time**: 5 minutes

### 1.1 Create Email Reply Plan

```bash
cat > "$VAULT_PATH/Needs_Action/PLAN_email_test_$(date +%s).md" << 'EOF'
---
type: email_send
action: reply
recipient: "test@example.com"
subject: "Re: Test Email"
thread_id: "thread_abc123"
status: pending
---

## Email Body

This is a test email reply from Silver Tier executor.

Thanks!
EOF
```

### 1.2 Approve Plan

Move plan from /Needs_Action/ to /Approved/:

```bash
mv "$VAULT_PATH/Needs_Action/PLAN_email_test_*.md" "$VAULT_PATH/Approved/"
```

### 1.3 Monitor Executor

Watch executor logs in real-time:

```bash
pm2 logs executor --lines 20
```

**Expected logs**:
```
[executor] Detected new plan in /Approved/: PLAN_email_test_1708876800.md
[executor] Validating plan against email-plan-schema.json
[executor] Plan valid
[executor] Sending email via Gmail MCP server
[executor] Email sent successfully. Message ID: <abc123@mail.gmail.com>
[executor] Moving plan to /Done/
[executor] Audit log updated
```

### 1.4 Verify Results

**Check 1: Plan moved to /Done/**

```bash
ls "$VAULT_PATH/Done/" | grep PLAN_email_test
```

Expected: Plan file present.

**Check 2: Audit log entry**

```bash
cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | jq 'select(.action_type == "email_send")'
```

Expected: JSON log entry with result="success".

**Check 3: Dashboard updated**

```bash
grep "Emails sent" "$VAULT_PATH/Dashboard.md"
```

Expected: "Emails sent today: 1".

**Check 4: Gmail Sent folder (if not DRY_RUN)**

Open Gmail and verify email in Sent folder.

### ✅ Success Criteria

- SC-001: Email sent within 2 minutes of approval ✓
- SC-002: 95% success rate (1/1 = 100%) ✓
- SC-005: Email appears in Gmail Sent folder ✓

---

## Test Scenario 2: Social Media Post (US2 - P2)

**Objective**: Test LinkedIn post execution.

**Time**: 5 minutes

### 2.1 Create LinkedIn Post Plan

```bash
cat > "$VAULT_PATH/Needs_Action/POST_linkedin_$(date +%s).md" << 'EOF'
---
type: social_media_post
post_id: POST_linkedin_1708876900
platforms:
  - linkedin
content: "Test post from Silver Tier executor. Testing automated posting workflow. #AI #Automation"
media_attachments: []
scheduled_time: null
status: draft
platform_results: {}
created_at: "2026-02-25T14:00:00Z"
---

## Post Content

Test post from Silver Tier executor. Testing automated posting workflow. #AI #Automation

## Purpose

Verify LinkedIn MCP integration and posting workflow.
EOF
```

### 2.2 Approve Plan

```bash
mv "$VAULT_PATH/Needs_Action/POST_linkedin_*.md" "$VAULT_PATH/Approved/"
```

### 2.3 Monitor Executor

```bash
pm2 logs executor --lines 20
```

**Expected logs**:
```
[executor] Detected new plan in /Approved/: POST_linkedin_1708876900.md
[executor] Validating plan against social-post-plan-schema.json
[executor] Content length valid for linkedin: 76 chars (max 3000)
[executor] Posting to LinkedIn via MCP server
[executor] LinkedIn post successful. Post URL: https://linkedin.com/posts/user_123
[executor] Updating plan with platform results
[executor] Moving plan to /Done/
```

### 2.4 Verify Results

**Check 1: Platform result in plan file**

```bash
cat "$VAULT_PATH/Done/POST_linkedin_*.md" | grep -A5 "platform_results:"
```

Expected: LinkedIn status=success, post_url present.

**Check 2: LinkedIn post live (if not DRY_RUN)**

Open LinkedIn and verify post appears in your feed.

### ✅ Success Criteria

- SC-006: Post published within 3 minutes ✓
- SC-009: Post URL captured in plan metadata ✓

---

## Test Scenario 3: WhatsApp Monitoring (US3 - P3)

**Objective**: Test WhatsApp watcher detects messages.

**Time**: 5 minutes

### 3.1 Send Test WhatsApp Message

From your phone, send a message to your WhatsApp Business number:

```
"Test message from Silver Tier. Please acknowledge receipt."
```

### 3.2 Wait for Detection

WhatsApp watcher polls every 60 seconds. Wait up to 2 minutes.

### 3.3 Monitor Watcher Logs

```bash
pm2 logs whatsapp-watcher --lines 20
```

**Expected logs**:
```
[whatsapp-watcher] Polling WhatsApp Business API
[whatsapp-watcher] Found 1 new message
[whatsapp-watcher] Message ID: wamid.abc123xyz
[whatsapp-watcher] Sender: +923001234567 (John Doe)
[whatsapp-watcher] Creating entity in /Needs_Action/
[whatsapp-watcher] Entity created: WHATSAPP_wamid.abc123xyz.md
```

### 3.4 Verify Entity Created

```bash
ls "$VAULT_PATH/Needs_Action/" | grep WHATSAPP
```

Expected: WHATSAPP_[message_id].md file present.

### 3.5 Check Message Content

```bash
cat "$VAULT_PATH/Needs_Action/WHATSAPP_"*.md
```

Expected: YAML frontmatter with sender_phone, message_content, priority.

### ✅ Success Criteria

- SC-011: Message appears within 2 minutes ✓
- SC-014: No duplicates (send same message again, should not create duplicate entity) ✓

---

## Test Scenario 4: Scheduled Task (US4 - P4)

**Objective**: Test daily briefing generation.

**Time**: 2-5 minutes (depending on timing)

### 4.1 Configure Test Briefing

Edit Company_Handbook.md to set briefing for current time + 2 minutes:

```bash
# Calculate time 2 minutes from now
CURRENT_HOUR=$(date +%H)
CURRENT_MINUTE=$(date +%M)
NEXT_MINUTE=$(( ($CURRENT_MINUTE + 2) % 60 ))
NEXT_HOUR=$(( ($CURRENT_HOUR + ($CURRENT_MINUTE + 2) / 60) % 24 ))

echo "Schedule briefing for: ${NEXT_HOUR}:$(printf "%02d" $NEXT_MINUTE)"
```

Update schedule_pattern in Company_Handbook.md:

```yaml
schedule_pattern: "$(printf "%02d" $NEXT_MINUTE) $NEXT_HOUR * * *"
recurrence_rule:
  frequency: daily
  time: "$(printf "%02d" $NEXT_HOUR):$(printf "%02d" $NEXT_MINUTE)"
```

### 4.2 Restart Scheduler

```bash
pm2 restart scheduler
```

### 4.3 Wait for Execution

Wait until scheduled time (2 minutes).

### 4.4 Monitor Scheduler Logs

```bash
pm2 logs scheduler --lines 20
```

**Expected logs**:
```
[scheduler] Loading scheduled tasks from Company_Handbook.md
[scheduler] Found 1 task: daily_briefing
[scheduler] Next execution: 2026-02-25T14:32:00Z
[scheduler] Executing task: daily_briefing
[scheduler] Generating briefing...
[scheduler] Briefing created: BRIEFING_2026-02-25.md
[scheduler] Task completed successfully
```

### 4.5 Verify Briefing Created

```bash
ls "$VAULT_PATH/Needs_Action/" | grep BRIEFING
```

Expected: BRIEFING_2026-02-25.md file present.

### 4.6 Check Briefing Content

```bash
cat "$VAULT_PATH/Needs_Action/BRIEFING_"*.md
```

Expected: Briefing with pending items count, recent completions, urgent items.

### ✅ Success Criteria

- SC-015: Briefing generated within 5 minutes of scheduled time ✓
- SC-016: Briefing includes pending/completed/urgent items ✓

---

## Troubleshooting

### Issue 1: Executor Not Detecting Approved Plans

**Symptoms**: Plan moved to /Approved/ but executor doesn't process it.

**Diagnosis**:
```bash
pm2 logs executor --err --lines 50
```

**Common Causes**:
1. Watchdog not monitoring /Approved/ folder
   - **Fix**: Check executor logs for "Watching /Approved/" message
2. Plan validation failing
   - **Fix**: Check logs for validation errors, verify plan against schema
3. Executor crashed
   - **Fix**: Check error logs, restart executor: `pm2 restart executor`

### Issue 2: MCP Server Connection Errors

**Symptoms**: Logs show "MCP connection failed" or "Timeout calling MCP server".

**Diagnosis**:
```bash
# Test MCP server connectivity
curl -v http://localhost:3001/health
```

**Solutions**:
1. MCP server not running
   - **Fix**: Start MCP server or set DRY_RUN=true for testing
2. Wrong MCP URL in .env
   - **Fix**: Verify GMAIL_MCP_URL, LINKEDIN_MCP_URL, etc.
3. Network firewall blocking
   - **Fix**: Check firewall rules, allow localhost connections

### Issue 3: Scheduled Task Not Executing

**Symptoms**: Scheduled time passed but no briefing generated.

**Diagnosis**:
```bash
pm2 logs scheduler --lines 50
```

**Common Causes**:
1. Task disabled (`enabled: false`)
   - **Fix**: Set `enabled: true` in Company_Handbook.md
2. Cron pattern invalid
   - **Fix**: Validate pattern at crontab.guru, update schedule_pattern
3. Scheduler not reading Company_Handbook.md
   - **Fix**: Restart scheduler: `pm2 restart scheduler`

### Issue 4: Rate Limit Errors

**Symptoms**: Logs show "Rate limit exceeded" or "Quota exhausted".

**Diagnosis**:
```bash
cat "$VAULT_PATH/Logs/rate_limit_state.json"
```

**Solutions**:
1. Too many actions in short time
   - **Fix**: Wait for quota to refill (check wait_time in logs)
2. Rate limit too strict
   - **Fix**: Adjust rate limits in executor configuration
3. State file corrupted
   - **Fix**: Delete rate_limit_state.json, will regenerate

---

## Monitoring & Logs

### PM2 Dashboard

```bash
pm2 monit
```

Shows real-time CPU, memory, logs for all processes.

### View All Logs

```bash
pm2 logs --lines 50
```

### View Specific Process

```bash
pm2 logs executor
pm2 logs scheduler
pm2 logs whatsapp-watcher
```

### Audit Log Analysis

```bash
# Count actions by type
cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | jq '.action_type' | sort | uniq -c

# View failed actions
cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | jq 'select(.result == "failure")'

# Calculate success rate
TOTAL=$(cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | wc -l)
SUCCESS=$(cat "$VAULT_PATH/Logs/$(date +%Y-%m-%d).json" | jq 'select(.result == "success")' | wc -l)
echo "Success rate: $((100 * $SUCCESS / $TOTAL))%"
```

---

## Next Steps

After successful testing:

1. **Configure Real MCP Servers**: Replace localhost URLs with production MCP servers
2. **Set DRY_RUN=false**: Enable real API calls
3. **Customize Scheduled Tasks**: Add weekly summaries, custom briefings
4. **Run 24-Hour Stability Test**: See `docs/24hour-stability-test.md`
5. **Generate Implementation Tasks**: Run `/sp.tasks` to create task list

---

## Quick Reference

### PM2 Commands

```bash
pm2 start ecosystem.config.js   # Start all processes
pm2 stop all                     # Stop all
pm2 restart all                  # Restart all
pm2 logs                         # View logs
pm2 status                       # Process status
pm2 monit                        # Real-time monitoring
```

### Test Email Send

```bash
# 1. Create plan
cat > "$VAULT_PATH/Needs_Action/PLAN_email_test_$(date +%s).md" << 'EOF'
---
type: email_send
action: send
recipient: "test@example.com"
subject: "Test"
body: "Test email"
status: pending
---
Test body
EOF

# 2. Approve
mv "$VAULT_PATH/Needs_Action/PLAN_email_test_"*.md "$VAULT_PATH/Approved/"

# 3. Watch
pm2 logs executor --lines 20
```

### Test Social Post

```bash
# 1. Create plan
cat > "$VAULT_PATH/Needs_Action/POST_linkedin_$(date +%s).md" << 'EOF'
---
type: social_media_post
post_id: POST_linkedin_$(date +%s)
platforms: [linkedin]
content: "Test post"
status: draft
platform_results: {}
---
Test
EOF

# 2. Approve
mv "$VAULT_PATH/Needs_Action/POST_linkedin_"*.md "$VAULT_PATH/Approved/"

# 3. Watch
pm2 logs executor
```

---

**Quickstart Status**: ✅ **COMPLETE**

**Date**: 2026-02-25

**Estimated Setup Time**: 30-45 minutes

**Ready for**: Implementation (`/sp.tasks` → `/sp.implement`)
