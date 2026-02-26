# WhatsApp Processor Skill - Silver Tier US3

**Purpose**: Process and respond to incoming WhatsApp Business messages with priority detection and media handling.

**Capability**: Silver Tier - Human-in-the-Loop (HITL) message monitoring and entity creation.

---

## Overview

The WhatsApp Processor enables the AI Employee to monitor WhatsApp Business API for incoming messages. Messages are detected automatically and created as entities in `/Needs_Action/` for review and response planning.

**Core Workflow**:
1. WhatsApp watcher polls API every 60 seconds
2. Detects new messages from customers/contacts
3. Checks sender against priority contacts list
4. Downloads media attachments (if any) to `/Inbox/`
5. Creates WhatsAppMessage entity in `/Needs_Action/`
6. User reviews message and creates response plan

---

## Message Processing Workflow

### 1. Message Detection

**Polling Interval**: 60 seconds (configurable via `WHATSAPP_CHECK_INTERVAL`)

**Detection Process**:
```
WhatsAppWatcher (PM2) → Poll MCP Server every 60s
                      ↓
            WhatsApp MCP Server → GET /messages?status=unread
                      ↓
            WhatsApp Business API → Return new messages
                      ↓
            Parse messages → Filter duplicates
                      ↓
            Create entities in /Needs_Action/
```

**Duplicate Prevention**:
- Message IDs tracked in `/Logs/whatsapp_state.json`
- Each message processed only once
- State persists across watcher restarts

### 2. Priority Contact Detection

**Priority Contacts**: Configured in `Company_Handbook.md`

**Handbook Format**:
```yaml
---
whatsapp_priority_contacts:
  - phone: "+14155552671"
    name: "CEO - John Smith"
    reason: "Executive leadership"
  - phone: "+442071838750"
    name: "CFO - Jane Doe"
    reason: "Financial approvals"
  - phone: "+551155256325"
    name: "VIP Customer - Acme Corp"
    reason: "Enterprise customer"
---
```

**Priority Assignment**:
- **HIGH**: Sender phone matches priority contacts list
- **MEDIUM**: All other contacts (default)

**Benefits**:
- High priority messages surfaced in Dashboard
- Can trigger immediate notifications (future)
- Helps triage urgent vs routine messages

### 3. Media Attachment Handling

**Supported Media Types**:
- **Image**: JPEG, PNG, GIF, WebP
- **Video**: MP4, 3GPP
- **Audio**: AAC, MP3, OGG (including voice notes)
- **Document**: PDF, Excel, Word, etc.
- **Sticker**: WhatsApp stickers

**Download Process**:
1. Watcher detects message with media
2. Calls WhatsApp MCP `/media/{media_id}/download`
3. MCP server fetches media from WhatsApp API
4. Returns Base64-encoded file content
5. Watcher decodes and saves to `/Inbox/whatsapp_{media_id}_{timestamp}{ext}`
6. Updates entity with local file path

**Storage Location**: `/Inbox/` folder

**Filename Format**: `whatsapp_{media_id}_{timestamp}.{ext}`

**Example**:
```
/Inbox/whatsapp_ABGGFlA5FpafAgo6tHcNmNjXmuSf_1740000000.jpg
/Inbox/whatsapp_ABEGkYaZW7tJAgkO8Ai5P33whGM_1740000001.pdf
```

### 4. Entity Creation

**File Location**: `/Needs_Action/WHATSAPP_{short_id}.md`

**Entity Format**:
```markdown
---
type: whatsapp_message
message_id: wamid.HBgLMTU1MTU1NTU1NTUVAgARGBI5QTNDQTU5M0U3QzBGRjQ4MDkA
sender_phone: "+14155552671"
sender_name: "John Smith"
timestamp: "2026-02-25T14:30:00Z"
priority: high
status: new
created_at: "2026-02-25T14:30:15Z"
conversation_id: "conv_abc123"
media_attachments:
  - media_id: ABGGFlA5FpafAgo6tHcNmNjXmuSf
    media_type: image
    mime_type: image/jpeg
    file_size: 245678
    local_path: /Inbox/whatsapp_ABGGFlA5FpafAgo6tHcNmNjXmuSf_1740000000.jpg
    caption: "Here's the invoice for review"
reply_context:
  conversation_id: conv_abc123
  message_id: wamid.HBgLMTU1MTU1NTU1NTUVAgARGBI5QTNDQTU5M0U3QzBGRjQ4MDkA
  sender_phone: "+14155552671"
---

# WhatsApp Message from John Smith

**Received**: 2026-02-25T14:30:00Z
**Priority**: high

**Media Attachments**: 1

1. image - image/jpeg (245678 bytes)
   Path: `/Inbox/whatsapp_ABGGFlA5FpafAgo6tHcNmNjXmuSf_1740000000.jpg`
   Caption: Here's the invoice for review

## Message

Hi, I'm sending the invoice for February. Please review and confirm payment by EOD.

Thanks!
```

---

## Priority Contact Management

### Adding Priority Contacts

Edit `Company_Handbook.md` and add to `whatsapp_priority_contacts` section:

```yaml
whatsapp_priority_contacts:
  - phone: "+14155552671"
    name: "New VIP Contact"
    reason: "Description of why this contact is high priority"
```

**Phone Format**: E.164 format required (`+[country][number]`, no spaces/dashes)

**Valid Examples**:
- `+14155552671` (US)
- `+442071838750` (UK)
- `+551155256325` (Brazil)

**Invalid Examples**:
- `4155552671` (missing +)
- `+1-415-555-2671` (contains dashes)
- `+1 415 555 2671` (contains spaces)

### Reloading Priority Contacts

Priority contacts are loaded:
1. **On watcher startup** (first check)
2. **Automatically on handbook changes** (if watcher detects file modification)

**Manual Reload**:
```bash
# Restart watcher to reload priority contacts
pm2 restart whatsapp-watcher
```

---

## Error Handling & Recovery

### Error Type 1: MCP Connection Failure

**Symptoms**: Watcher logs "WhatsApp MCP connection failed"

**Exponential Backoff**:
- **Attempt 1**: Wait 5 seconds, retry
- **Attempt 2**: Wait 30 seconds, retry
- **Attempt 3+**: Wait 2 minutes (120s), retry

**Behavior**:
- Watcher continues retrying indefinitely
- No messages are lost (WhatsApp stores unread messages)
- Once connection restored, watcher processes backlog

**Recovery**:
1. Check MCP server status: `pm2 status whatsapp-mcp-server`
2. View MCP logs: `pm2 logs whatsapp-mcp-server`
3. Restart MCP if needed: `pm2 restart whatsapp-mcp-server`
4. Watcher will auto-recover on next poll

### Error Type 2: API Down >10 Minutes

**Symptoms**: Alert created in `/Needs_Action/ALERT_whatsapp_api_down_*.md`

**Alert Triggers**: After 10 consecutive failures (~10 minutes)

**Alert Content**:
- Downtime duration
- Connection failure count
- Diagnostic steps
- Recovery instructions

**Recovery Steps**:
1. Check MCP server: `curl http://localhost:3005/whatsapp/health`
2. Expected: `{"status": "healthy"}`
3. If unhealthy, check MCP server logs
4. Verify WhatsApp API credentials in `.env`
5. Restart MCP server: `pm2 restart whatsapp-mcp-server`
6. Restart watcher: `pm2 restart whatsapp-watcher`

### Error Type 3: Media Download Failure

**Symptoms**: Entity created but `local_path` missing for media attachment

**Possible Causes**:
- Media expired (WhatsApp media URLs expire after 24 hours)
- MCP server download endpoint error
- Disk space full in `/Inbox/`

**Recovery**:
- Media not critical for message understanding
- Entity still created with message text
- User can request re-send if media needed

### Error Type 4: Duplicate Messages

**Symptoms**: Same message detected multiple times

**Prevention**:
- Message IDs tracked in `/Logs/whatsapp_state.json`
- Duplicate check before entity creation
- State persists across restarts

**If Duplicates Occur**:
- Check state file exists and is valid JSON
- Verify watcher not running multiple instances: `pm2 list`
- Restart watcher: `pm2 restart whatsapp-watcher`

---

## Dashboard Integration

WhatsApp statistics appear on `Dashboard.md`:

```markdown
## WhatsApp Messages

- **Messages Received Today**: 12 messages
- **High Priority**: 3 messages
- **Last Message**: 14:30 (30 minutes ago)
- **Watcher Status**: ✅ Running
```

**Metrics Tracked**:
- Total messages received today
- High priority message count
- Last message timestamp
- Watcher heartbeat status

---

## PM2 Management

### Start Watcher

```bash
pm2 start ecosystem.config.js --only whatsapp-watcher
```

### View Logs

```bash
pm2 logs whatsapp-watcher
```

### Restart Watcher

```bash
pm2 restart whatsapp-watcher
```

### Stop Watcher

```bash
pm2 stop whatsapp-watcher
```

### Monitor Status

```bash
pm2 status
```

Expected output:
```
┌────┬─────────────────┬─────────┬─────────┬─────────┬──────────┐
│ id │ name            │ mode    │ ↺       │ status  │ cpu      │
├────┼─────────────────┼─────────┼─────────┼─────────┼──────────┤
│ 3  │ whatsapp-watcher│ fork    │ 0       │ online  │ 0.1%     │
└────┴─────────────────┴─────────┴─────────┴─────────┴──────────┘
```

---

## Configuration

### Environment Variables

**Required**:
```bash
VAULT_PATH=/path/to/vault
WHATSAPP_MCP_URL=http://localhost:3005/whatsapp
```

**Optional**:
```bash
# Polling interval (default: 60 seconds)
WHATSAPP_CHECK_INTERVAL=60

# Dry run mode (no actual MCP calls)
DRY_RUN=false
```

### MCP Server Configuration

The WhatsApp MCP server must be running and configured with WhatsApp Business API credentials:

```bash
# .env for WhatsApp MCP server
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_token
```

---

## Message Response Workflow (HITL)

### Step 1: Review Message

Navigate to `/Needs_Action/` and open `WHATSAPP_{short_id}.md`:

1. Read message content
2. Check priority (high/medium)
3. Review media attachments (if any)
4. Determine required response

### Step 2: Create Response Plan

Use `vault-manager` skill to create a response plan:

```
Use vault-manager skill with action=plan and file_path=/path/to/vault/Needs_Action/WHATSAPP_abc123.md
```

This generates a plan in `/Plans/PLAN_XXX.md` with:
- Objective: Respond to WhatsApp message
- Steps: Draft response, review tone, send via WhatsApp
- Approval requirement: Yes (if sending to new contact)

### Step 3: Draft Response

Edit the plan to include response text:

```markdown
## Response Draft

Hi John,

Thank you for sending the invoice. I've reviewed it and confirmed the following:

- Invoice total: $1,234.56
- Due date: March 1, 2026
- Payment method: Wire transfer

I'll process the payment today. You should receive confirmation by 5 PM.

Best regards
```

### Step 4: Approve for Sending

Move plan to `/Approved/`:

```bash
mv /vault/Plans/PLAN_XXX.md /vault/Approved/
```

### Step 5: Executor Sends Response

Executor detects plan in `/Approved/` and:
1. Validates response plan
2. Calls WhatsApp MCP `/send_message` endpoint
3. Sends response to original sender
4. Logs execution
5. Moves plan to `/Done/`

---

## Best Practices

### 1. Priority Contact Management

**Do**:
- Keep priority contacts list updated in `Company_Handbook.md`
- Include reason for priority (helps future understanding)
- Use E.164 format strictly

**Don't**:
- Add too many priority contacts (defeats purpose of prioritization)
- Forget to restart watcher after handbook changes

### 2. Media Handling

**Do**:
- Regularly clean up `/Inbox/` to save disk space
- Archive important media to external storage
- Check media before responding (open and verify content)

**Don't**:
- Delete media before responding to message
- Trust media content without verification (security risk)

### 3. Response Timing

**Do**:
- Respond to high priority messages within 1 hour
- Set expectations for response times with contacts
- Use scheduled tasks for automatic follow-ups (US4)

**Don't**:
- Let messages sit in `/Needs_Action/` for days
- Send immediate responses without review (quality over speed)

### 4. Security

**Do**:
- Validate phone numbers before adding to priority list
- Review all media attachments for malicious content
- Keep WhatsApp API credentials secure in `.env`

**Don't**:
- Share API credentials in handbook or notes
- Auto-approve responses without review (Silver Tier = HITL)
- Process messages from unknown/suspicious numbers automatically

---

## Troubleshooting

### Issue: Watcher Not Detecting Messages

**Check**:
1. Watcher running: `pm2 status whatsapp-watcher`
2. MCP server running: `pm2 status whatsapp-mcp-server`
3. Heartbeat updating: Check `/Logs/heartbeat.json` timestamp
4. Connection successful: `pm2 logs whatsapp-watcher` (no error logs)

### Issue: Duplicate Messages Created

**Check**:
1. State file exists: `cat /vault/Logs/whatsapp_state.json`
2. Single watcher instance: `pm2 list | grep whatsapp-watcher`
3. Message ID in state: Search for `message_id` in state file

**Fix**:
```bash
# Restart watcher to reload state
pm2 restart whatsapp-watcher
```

### Issue: Media Not Downloading

**Check**:
1. Disk space: `df -h /vault/Inbox`
2. Permissions: `ls -la /vault/Inbox`
3. MCP download endpoint: `curl http://localhost:3005/whatsapp/media/{media_id}/download`

**Fix**:
```bash
# Ensure Inbox folder exists and is writable
mkdir -p /vault/Inbox
chmod 755 /vault/Inbox
```

### Issue: Priority Contacts Not Working

**Check**:
1. Handbook format: `cat /vault/Company_Handbook.md` (verify YAML syntax)
2. Phone format: Ensure E.164 format (+[country][number])
3. Watcher reloaded: Restart after handbook changes

**Fix**:
```bash
# Restart watcher to reload priority contacts
pm2 restart whatsapp-watcher
```

---

## Future Enhancements (Gold Tier)

- **Auto-Responses**: Configure automatic replies for common questions
- **Smart Routing**: Route messages to specific team members based on content
- **Sentiment Analysis**: Detect urgent/angry messages for immediate escalation
- **Message Templates**: Pre-written responses for common scenarios
- **WhatsApp Sending**: Send messages directly from plans (currently receive-only)
- **Group Message Support**: Handle WhatsApp group messages
- **Status Updates**: Send status updates (read receipts, typing indicators)

---

**Version**: Silver Tier 0.2.0
**Last Updated**: 2026-02-25
**Related**: vault-manager.md, dashboard-updater.md
