# Executor Skill - Silver Tier US1

**Purpose**: Execute approved plans (email sends, social posts, etc.) from /Approved/ folder via MCP servers.

**Capability**: Silver Tier - Autonomous task execution with Human-in-the-Loop (HITL) approval workflow.

---

## Overview

The Executor is a background process that transforms the AI Employee from passive observer (Bronze) to active participant (Silver). It monitors `/Approved/` folder for approved plans and executes them via MCP (Model Context Protocol) servers.

**Core Workflow**:
1. Human reviews plan in `/Needs_Action/`
2. Human moves plan to `/Approved/` (approval signal)
3. Executor detects new file (watchdog)
4. Validates plan against JSON schema
5. Checks rate limits
6. Executes action via MCP server
7. Creates audit log
8. Moves plan to `/Done/` (success) or `/Needs_Action/` (failure with error details)

---

## Plan Execution Workflow

### Email Send Plan (US1)

**File**: `PLAN_email_[timestamp].md` in `/Approved/`

**Frontmatter Schema** (required fields):
```yaml
type: email_send
action: send|reply|forward
recipient: user@example.com
subject: Email subject line
status: pending
```

**Body**: Email body content (plain text or markdown)

**Execution Steps**:
1. **Validation**: Check required fields (type, action, recipient, subject, body)
2. **Rate Limit Check**: Gmail allows 500 emails/day, 1 per 5 seconds
3. **MCP Call**: POST to `$GMAIL_MCP_URL/send_email` with email data
4. **Success**: Move to `/Done/` with `executed_at` timestamp and `mcp_response`
5. **Failure**: Move back to `/Needs_Action/` with `execution_error` details

**Expected Timing**:
- Detection: <10 seconds after file move
- Execution: <2 minutes total (per SC-001)

**Example Plan**:
```markdown
---
type: email_send
action: reply
recipient: client@example.com
subject: Re: Invoice Payment
thread_id: thread_abc123
status: pending
created_at: 2026-02-25T14:30:00Z
---

Hi Client,

Thank you for your payment. The invoice has been marked as paid.

Best regards,
AI Employee
```

### Social Media Post Plan (US2)

**Status**: Detected but not executed (US2 implementation pending)

**File**: `POST_[platform]_[timestamp].md` in `/Approved/`

**Frontmatter Schema**:
```yaml
type: social_media_post
post_id: POST_linkedin_123456
platforms: [linkedin, facebook, twitter]
content: Post content text
status: pending
```

**Planned Execution**: Route to SocialMediaService (not yet implemented)

### Scheduled Task Plan (US4)

**Status**: Detected but not executed (US4 implementation pending)

**File**: Stored in `Company_Handbook.md` frontmatter, not as separate files

---

## Error Handling & Recovery

### Error Types

1. **Validation Errors**:
   - Missing required fields
   - Invalid email format
   - Schema violations
   - **Recovery**: Plan moved to `/Needs_Action/` with `execution_error` field

2. **Rate Limit Errors**:
   - Daily quota exceeded (Gmail: 500/day)
   - Burst limit exceeded (Gmail: 1 per 5 seconds)
   - **Recovery**: Plan stays in `/Approved/`, executor retries automatically after wait time

3. **MCP Connection Errors**:
   - MCP server unreachable
   - Network timeout
   - **Recovery**: Executor logs error, retries with exponential backoff (1s, 2s, 4s, max 60s, 3 retries)

4. **MCP Authentication Errors**:
   - Invalid API key
   - Expired OAuth token
   - **Recovery**: Executor attempts token refresh (if callback configured), otherwise moves plan to `/Needs_Action/`

5. **MCP Server Errors** (5xx):
   - Gmail API errors
   - Temporary service unavailability
   - **Recovery**: Executor retries with exponential backoff, then moves to `/Needs_Action/` if all retries fail

6. **Unexpected Errors**:
   - Code bugs
   - Corrupted plan files
   - **Recovery**: Executor logs full stack trace, moves plan to `/Needs_Action/` with error details

### Error Metadata

When execution fails, the plan file is updated with error information:

```yaml
execution_error: "Rate limit exceeded - wait 45s before next email"
execution_error_timestamp: 2026-02-25T14:35:22Z
status: failed
```

User can:
- Fix the error (e.g., wait for rate limit reset)
- Modify the plan
- Move back to `/Approved/` to retry

### Graceful Degradation

If one MCP server fails, other services continue working:
- Gmail MCP down → Email execution paused, social media still works
- LinkedIn MCP down → LinkedIn posts paused, Twitter/Facebook still work

---

## Monitoring & Audit Logs

### Heartbeat Logging

Executor logs heartbeat every 60 seconds to `/Logs/YYYY-MM-DD.json`:

```json
{
  "timestamp": "2026-02-25T14:30:00Z",
  "action_type": "heartbeat",
  "actor": "executor",
  "target": "executor",
  "parameters": {
    "uptime_seconds": 60,
    "approved_folder": "/vault/Approved"
  },
  "result": "success"
}
```

**Health Check**: If no heartbeat for >5 minutes, executor may be down.

### Execution Logs

Every execution (success or failure) creates an audit log entry:

```json
{
  "log_id": "LOG_1735144800_email_send",
  "timestamp": "2026-02-25T14:30:00Z",
  "action_type": "email_send",
  "actor": "executor",
  "plan_id": "PLAN_email_123456.md",
  "target": "client@example.com",
  "parameters": {
    "subject": "Re: Invoice Payment",
    "body_preview": "Hi Client, Thank you for your payment..."
  },
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success",
  "mcp_server": "http://localhost:3001/gmail",
  "response": {
    "message_id": "abc123xyz",
    "thread_id": "thread_456"
  },
  "duration_ms": 1250,
  "retry_count": 0
}
```

**Audit Trail**: Complete history of all executions for accountability and debugging.

---

## PM2 Process Management

### Start Executor

```bash
pm2 start ecosystem.config.js
pm2 logs executor
```

### Check Status

```bash
pm2 status
# Should show: executor (online)

pm2 show executor
# Shows: uptime, memory usage, restarts
```

### Stop/Restart

```bash
pm2 stop executor
pm2 restart executor
pm2 reload executor  # Zero-downtime restart
```

### View Logs

```bash
pm2 logs executor           # Live tail
pm2 logs executor --lines 100  # Last 100 lines
pm2 logs executor --err     # Error logs only
```

### Auto-Start on Boot

```bash
pm2 startup
pm2 save
```

---

## DRY_RUN Mode (Testing)

For testing without executing real actions:

**Enable DRY_RUN**:
```bash
# In .env
DRY_RUN=true
```

**Behavior**:
- Plans are validated ✓
- Rate limits are checked ✓
- MCP calls are logged but NOT executed ✓
- Plans are moved to `/Done/` as if successful ✓
- Audit logs created with DRY_RUN indicator ✓

**Use Cases**:
- Testing plan validation
- Testing folder monitoring
- Verifying rate limiting logic
- Debugging without side effects

---

## Rate Limiting Details

### Gmail (Email Sending)

- **Daily Limit**: 500 emails/day
- **Burst Limit**: 1 email per 5 seconds
- **State File**: `/Logs/rate_limit_state.json`
- **Algorithm**: Token bucket (allows short bursts, prevents long-term quota exhaustion)

**Rate Limit State** (persisted to JSON):
```json
{
  "gmail": {
    "platform": "gmail",
    "capacity": 500,
    "tokens": 485.3,
    "refill_rate": 0.005787037,
    "last_refill": 1735144800,
    "total_consumed": 15,
    "last_reset": 1735142400
  }
}
```

**Behavior**:
- Tokens refill continuously at constant rate (500 tokens / 86400 seconds)
- Each email consumes 1 token
- If tokens < 1, execution blocked until refill
- Daily reset at midnight (total_consumed resets to 0)

---

## Common Issues & Solutions

### Issue 1: Executor not detecting plans

**Symptoms**: Plans moved to `/Approved/` but not executed

**Diagnosis**:
```bash
pm2 logs executor  # Check for errors
ls -la vault/Approved/  # Verify files exist
```

**Solutions**:
- Check PM2 status: `pm2 status` (should be "online")
- Check VAULT_PATH in .env is correct
- Restart executor: `pm2 restart executor`
- Check file permissions (executor must be able to read/write)

### Issue 2: Rate limit exceeded

**Symptoms**: Plans failing with "Rate limit exceeded" error

**Diagnosis**:
```bash
# Check rate limit state
cat vault/Logs/rate_limit_state.json
```

**Solutions**:
- Wait for rate limit refill (tokens replenish automatically)
- Check if you hit daily limit (500 emails/day)
- Manually reset bucket (admin only): Edit `rate_limit_state.json` to set `tokens: 500`

### Issue 3: MCP server unreachable

**Symptoms**: All executions failing with "Connection error"

**Diagnosis**:
```bash
# Test MCP server connectivity
curl -X POST http://localhost:3001/gmail/health
```

**Solutions**:
- Check MCP server is running
- Verify MCP URLs in .env are correct
- Check firewall/network settings
- Enable DRY_RUN mode for testing: `DRY_RUN=true` in .env

### Issue 4: Plan validation failing

**Symptoms**: Plans moved to `/Needs_Action/` with validation errors

**Diagnosis**:
```bash
# Check execution logs
cat vault/Logs/$(date +%Y-%m-%d).json | grep validation_error
```

**Solutions**:
- Verify plan has required fields: `type`, `action`, `recipient`, `subject`, `body`
- Check email format is valid (RFC 5322)
- Ensure plan follows schema: `specs/002-silver-tier-upgrade/contracts/email-plan-schema.json`

---

## Claude Code Integration

When creating email plans, Claude Code should:

1. **Use the Template**:
```markdown
---
type: email_send
action: send
recipient: {{ email_address }}
subject: {{ subject_line }}
status: pending
created_at: {{ timestamp }}
---

{{ email_body }}
```

2. **Place in Correct Folder**: `/Needs_Action/` (NOT `/Approved/`)
   - Human must manually approve by moving to `/Approved/`

3. **Include Context**: Add helpful metadata in frontmatter
```yaml
original_request: "Reply to invoice inquiry from client"
context: "Client asked about invoice #12345"
```

4. **Validate Before Creating**: Check required fields are present

---

## Security & Privacy

### Credentials

- MCP server URLs stored in `.env` (outside vault)
- OAuth tokens managed by MCP servers (not in vault)
- API keys never hardcoded in plans

### Approval Workflow (HITL)

- **No auto-approval** in Silver Tier (reserved for Gold Tier)
- Every action requires human to move file to `/Approved/`
- Approval timestamp recorded in execution log
- Audit trail tracks who approved (`approved_by: human`)

### Rate Limiting

- Prevents quota exhaustion
- Protects against accidental mass sending
- Persistent state survives executor restarts

---

## Future Enhancements (Gold Tier)

- **Auto-Approval Thresholds**: Configure rules for auto-approving low-risk actions
- **Scheduled Execution**: Execute plans at specific times (not immediately)
- **Batch Execution**: Group multiple emails into batches
- **Priority Queues**: High-priority plans execute first
- **Multi-Tenant**: Support multiple vaults/users

---

**Version**: Silver Tier 0.2.0
**Last Updated**: 2026-02-25
**Related**: vault-manager.md, dashboard-updater.md
