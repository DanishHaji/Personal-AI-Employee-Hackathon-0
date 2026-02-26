# Silver Tier Setup Guide

**Version**: 0.2.0
**Last Updated**: 2026-02-25
**Prerequisites**: Bronze Tier installed and working

---

## Overview

Silver Tier upgrades your AI Employee from read-only monitoring (Bronze) to autonomous execution with Human-in-the-Loop (HITL) approval. New capabilities include:

1. **Email Sending & Replying** - Send emails via Gmail API
2. **Social Media Auto-Posting** - Post to LinkedIn, Facebook, Twitter
3. **WhatsApp Business Monitoring** - Monitor incoming WhatsApp messages
4. **Scheduled Tasks & Automation** - Daily briefings, weekly summaries, custom tasks

---

## Quick Start (10 minutes)

### 1. Install Dependencies

```bash
# Install Silver Tier Python dependencies
uv pip install apscheduler

# Dependencies already installed from Bronze:
# - mcp, requests, jsonschema, watchdog, python-dotenv
```

### 2. Configure Environment

Edit `.env` file:

```bash
# Silver Tier MCP Servers
DRY_RUN=false  # Set to true for testing without real API calls

# Email (Gmail MCP)
GMAIL_MCP_URL=http://localhost:3001/gmail
GMAIL_ENABLED=false  # Enable when credentials ready

# Social Media MCP Servers
LINKEDIN_MCP_URL=http://localhost:3002/linkedin
FACEBOOK_MCP_URL=http://localhost:3003/facebook
TWITTER_MCP_URL=http://localhost:3004/twitter

# WhatsApp Business MCP
WHATSAPP_MCP_URL=http://localhost:3005/whatsapp

# Polling intervals (seconds)
WHATSAPP_CHECK_INTERVAL=60
```

### 3. Start Silver Tier Processes

```bash
# Start all processes
pm2 start ecosystem.config.js

# Or start individually
pm2 start ecosystem.config.js --only executor
pm2 start ecosystem.config.js --only scheduler
pm2 start ecosystem.config.js --only whatsapp-watcher

# View status
pm2 status

# View logs
pm2 logs
```

### 4. Verify Installation

```bash
# Check all processes running
pm2 list

# Should see:
# - gmail-watcher (Bronze)
# - filesystem-watcher (Bronze)
# - executor (Silver - NEW)
# - scheduler (Silver - NEW)
# - whatsapp-watcher (Silver - NEW)

# Check heartbeat
cat vault/Logs/heartbeat.json

# Check Dashboard
cat vault/Dashboard.md
```

---

## Detailed Setup

### MCP Server Setup

Silver Tier requires MCP servers for external integrations. These run as separate processes and provide standardized APIs.

#### Gmail MCP Server (Optional - US1)

**When to enable**: When you have Gmail API credentials

**Setup**:
```bash
# 1. Get Gmail API credentials
# - Visit: https://console.cloud.google.com/
# - Enable Gmail API
# - Create OAuth 2.0 credentials
# - Download credentials.json

# 2. Start Gmail MCP server
# (MCP server setup varies by provider - see MCP documentation)

# 3. Enable in .env
GMAIL_ENABLED=true
GMAIL_MCP_URL=http://localhost:3001/gmail
```

**Verification**:
```bash
curl http://localhost:3001/gmail/health
# Expected: {"status": "healthy"}
```

#### LinkedIn MCP Server (US2)

**Setup**:
```bash
# 1. Get LinkedIn API access
# - Create LinkedIn App: https://www.linkedin.com/developers/
# - Get Client ID and Client Secret
# - Configure OAuth redirect URI

# 2. Configure .env with credentials

# 3. Start LinkedIn MCP server

# 4. Verify
curl http://localhost:3002/linkedin/health
```

#### Facebook MCP Server (US2)

**Setup**:
```bash
# 1. Create Facebook App: https://developers.facebook.com/
# 2. Get Page Access Token
# 3. Configure MCP server with credentials
# 4. Verify
curl http://localhost:3003/facebook/health
```

#### Twitter/X MCP Server (US2)

**Setup**:
```bash
# 1. Get Twitter API access: https://developer.twitter.com/
# 2. Get API Key, API Secret, Access Token, Access Token Secret
# 3. Configure MCP server
# 4. Verify
curl http://localhost:3004/twitter/health
```

#### WhatsApp Business MCP Server (US3)

**Setup**:
```bash
# 1. Set up WhatsApp Business API
# 2. Get Phone Number ID, Access Token, Business Account ID
# 3. Configure MCP server
# 4. Verify
curl http://localhost:3005/whatsapp/health
```

---

## Feature Configuration

### Email Sending (US1)

**Approve Email Plans**:
1. Email plans created by Bronze Tier in `/Plans/`
2. Review email plan content
3. Move to `/Approved/` folder
4. Executor detects and sends email via Gmail MCP
5. Plan moves to `/Done/` with execution log

**Rate Limits**:
- Gmail: 500 emails/day (1 per 5 seconds minimum)
- State persisted in `/Logs/rate_limit_state.json`

**Verification**:
```bash
# Create test email plan
# (Use vault-manager skill via Claude Code)

# Move to Approved
mv vault/Plans/PLAN_email_test.md vault/Approved/

# Check logs
pm2 logs executor

# Verify execution log
cat vault/Logs/$(date +%Y-%m-%d).json | grep email_send
```

### Social Media Posting (US2)

**Create Social Post**:
```yaml
# vault/Needs_Action/POST_linkedin_123.md
---
type: social_media_post
post_id: POST_linkedin_123
platforms: [linkedin, twitter]
status: draft
created_at: 2026-02-25T14:30:00Z
---

Excited to announce our new feature!

Key benefits:
- 40% productivity increase
- 95% accuracy rate
- Cost reduction of 60%

Learn more: https://example.com

#AI #Automation #ProductLaunch
```

**Approve Post**:
```bash
# Review content
cat vault/Needs_Action/POST_linkedin_123.md

# Approve
mv vault/Needs_Action/POST_linkedin_123.md vault/Approved/

# Check logs
pm2 logs executor

# Verify posted
cat vault/Done/POST_linkedin_123.md
# Check platform_results section
```

**Rate Limits**:
- LinkedIn: 100 posts/day
- Twitter: 2400 tweets/day (auto-threads >280 chars)
- Facebook: 200 posts/day

### WhatsApp Monitoring (US3)

**Configure Priority Contacts**:

Edit `vault/Company_Handbook.md` frontmatter:
```yaml
---
whatsapp_priority_contacts:
  - phone: "+14155552671"
    name: "CEO - John Smith"
    reason: "Executive leadership"
  - phone: "+442071838750"
    name: "VIP Customer - Acme Corp"
    reason: "Enterprise customer"
---
```

**Verification**:
```bash
# Send test message to WhatsApp Business number

# Check watcher logs
pm2 logs whatsapp-watcher

# Verify entity created
ls vault/Needs_Action/WHATSAPP_*.md

# Check priority detection
cat vault/Needs_Action/WHATSAPP_*.md | grep priority
```

**Media Handling**:
- Images, videos, documents downloaded to `/Inbox/`
- Linked in entity frontmatter and body
- Max file size varies by WhatsApp limits

### Scheduled Tasks (US4)

**Configure Daily Briefing**:

Edit `vault/Company_Handbook.md` frontmatter:
```yaml
---
scheduled_tasks:
  - task_id: daily_briefing_morning
    task_name: "Morning Briefing"
    task_type: daily_briefing
    schedule_pattern: "0 9 * * *"  # 9 AM UTC daily
    recurrence_rule: "Daily at 9:00 AM UTC"
    enabled: true
    output_path: "Needs_Action"
    parameters:
      include_urgent: true
      include_completions: true
---
```

**Important**: Schedule patterns use UTC timezone. Adjust for your local time.

**Verification**:
```bash
# Check scheduler loaded task
pm2 logs scheduler | grep "Scheduled task"

# Check schedule state
cat vault/Logs/schedule_state.json

# Wait for scheduled time (or test with current time + 2 minutes)

# Verify briefing created
ls vault/Needs_Action/BRIEFING_*.md
```

**Custom Tasks**:
```yaml
- task_id: custom_reminder
  task_name: "End of Month Reminder"
  task_type: custom
  schedule_pattern: "0 9 28-31 * *"
  enabled: true
  parameters:
    action: "create_reminder"
    reminder_text: "Review monthly expenses"
```

---

## Monitoring

### Dashboard

`vault/Dashboard.md` shows real-time statistics:

```markdown
## Execution Statistics (Silver Tier)

**Email Sending:**
- Emails Sent Today: 5 emails
- Last Execution: 14:45 (2 minutes ago)
- Success Rate: 100% (5/5 successful)
- Rate Limit Status: 495 emails remaining today

**Social Media Posting:**
- Posts Published Today: 3 posts
- Platforms: LinkedIn (2), Twitter (2), Facebook (1)
- Last Post: 14:30 (15 minutes ago)
- Success Rate: 100% (3/3 successful)

**WhatsApp Messages:**
- Messages Received Today: 8 messages
- High Priority: 2 messages
- Last Message: 14:35 (10 minutes ago)

**Scheduled Tasks:**
- Tasks Configured: 3 tasks
- Executed Today: 2 tasks
- Last Execution: 09:00 (5 hours ago)
- Next Execution: 17:00 (in 2 hours)
```

### Audit Logs

All actions logged to `/Logs/YYYY-MM-DD.json`:

```bash
# View today's logs
cat vault/Logs/$(date +%Y-%m-%d).json

# Filter by action type
cat vault/Logs/$(date +%Y-%m-%d).json | grep email_send

# Filter by result
cat vault/Logs/$(date +%Y-%m-%d).json | grep '"result": "failure"'
```

### PM2 Monitoring

```bash
# View all processes
pm2 list

# View logs for specific process
pm2 logs executor
pm2 logs scheduler
pm2 logs whatsapp-watcher

# Monitor resource usage
pm2 monit

# Restart a process
pm2 restart executor
```

---

## Troubleshooting

### Executor Not Processing Approved Plans

**Symptoms**: Plans in `/Approved/` not executing

**Check**:
```bash
# 1. Executor running?
pm2 status executor

# 2. Check logs for errors
pm2 logs executor --lines 50

# 3. Verify MCP servers healthy
curl http://localhost:3001/gmail/health
curl http://localhost:3002/linkedin/health

# 4. Check rate limits
cat vault/Logs/rate_limit_state.json
```

**Solution**:
```bash
# Restart executor
pm2 restart executor

# If MCP server down, restart it
# Then restart executor
```

### Scheduler Not Executing Tasks

**Symptoms**: Scheduled tasks not running at expected time

**Check**:
```bash
# 1. Scheduler running?
pm2 status scheduler

# 2. Tasks loaded?
pm2 logs scheduler | grep "Loaded.*scheduled tasks"

# 3. Tasks enabled?
cat vault/Company_Handbook.md | grep "enabled: true"

# 4. Check schedule state
cat vault/Logs/schedule_state.json
```

**Solution**:
```bash
# Verify cron pattern correct (use online cron calculator)
# Ensure UTC timezone accounted for
# Restart scheduler
pm2 restart scheduler
```

### WhatsApp Watcher Not Detecting Messages

**Symptoms**: Messages sent but no entities created

**Check**:
```bash
# 1. Watcher running?
pm2 status whatsapp-watcher

# 2. MCP server healthy?
curl http://localhost:3005/whatsapp/health

# 3. Check logs
pm2 logs whatsapp-watcher --lines 50

# 4. Check processed state
cat vault/Logs/whatsapp_state.json
```

**Solution**:
```bash
# Restart watcher
pm2 restart whatsapp-watcher

# If MCP server down, restart it first
```

### Social Posts Not Publishing

**Symptoms**: Post approved but not published

**Check**:
```bash
# 1. Check execution logs
pm2 logs executor | grep social_post

# 2. Check plan file for errors
cat vault/Done/POST_*.md | grep error

# 3. Verify platform limits
# LinkedIn: 3000 chars
# Twitter: 280 chars (auto-threads)
# Facebook: 63206 chars

# 4. Check rate limits
cat vault/Logs/rate_limit_state.json
```

**Solution**:
- Shorten content if too long
- Wait for rate limit refresh
- Verify MCP server credentials valid

---

## Security Best Practices

1. **Credentials**:
   - Store all API credentials in `.env` (never in vault)
   - Use environment-specific `.env` files (dev, prod)
   - Rotate credentials regularly

2. **Approval Workflow**:
   - Always review plans before approving
   - Verify email recipients before sending
   - Check social post content for sensitive info

3. **Rate Limiting**:
   - Monitor daily quotas in Dashboard
   - Don't disable rate limiting (prevents API bans)
   - Plan high-volume activities in advance

4. **Audit Logs**:
   - Review logs weekly for anomalies
   - Archive old logs monthly
   - Keep logs for compliance (if required)

---

## Upgrading from Bronze Tier

If you have Bronze Tier installed:

1. **Install dependencies**: `uv pip install apscheduler`
2. **Update .env**: Add Silver Tier MCP URLs
3. **Restart watchers**: `pm2 restart all`
4. **Start new processes**: `pm2 start ecosystem.config.js --only executor scheduler whatsapp-watcher`
5. **Verify**: `pm2 status` should show 5-6 processes running

**No data migration needed** - Vault structure is backward compatible.

---

## Next Steps

1. **Configure MCP Servers**: Set up the integrations you need
2. **Test with DRY_RUN=true**: Verify workflows without real API calls
3. **Configure scheduled tasks**: Set up daily briefings
4. **Enable production**: Set `DRY_RUN=false` when ready
5. **Monitor Dashboard**: Check execution statistics daily

---

## Getting Help

- **Documentation**: See `.claude/commands/*.md` skills for detailed guides
- **Logs**: Check `pm2 logs` for error messages
- **Issues**: Report bugs at [GitHub repository]
- **Community**: [Discord/Forum link if applicable]

---

**Congratulations!** Your AI Employee is now Silver Tier - capable of autonomous execution with HITL approval.
