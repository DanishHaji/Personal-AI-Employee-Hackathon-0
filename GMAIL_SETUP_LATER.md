# 📧 Gmail Setup - Add Later When Credentials Ready

**Status**: Gmail currently **DISABLED** (waiting for Google Cloud verification)

**Ye file explain karti hai kaise Gmail ko baad mein enable karna hai jab credentials ready ho jayein.**

---

## 🔴 Current Status

Gmail Watcher is currently **DISABLED** because:
- Google Cloud Gmail API verification pending
- credentials.json not available yet
- OAuth flow blocked

**System is still functional without Gmail:**
- ✅ File Drop monitoring working
- ✅ Vault management working
- ✅ Dashboard updates working
- ✅ Orchestrator working
- ✅ Plan generation working (with non-Gmail sources)
- ❌ Gmail monitoring disabled (temporary)

---

## ✅ When Gmail Credentials Are Ready

Jab Google Cloud verification complete ho jaye, follow these steps:

### Step 1: Get Credentials (Google Cloud Console)

1. Complete Gmail API verification in Google Cloud Console
2. Download `credentials.json`
3. Save to project root:
   ```bash
   cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"
   # Copy downloaded credentials.json here
   ```

### Step 2: Enable Gmail in Configuration

```bash
# Edit .env file
nano .env

# Change this line:
GMAIL_ENABLED=false

# To:
GMAIL_ENABLED=true

# Save (Ctrl+X, Y, Enter)
```

### Step 3: Authenticate Gmail

```bash
# Run Gmail watcher for first-time OAuth
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"
uv run python src/watchers/gmail_watcher.py

# Browser will open
# Sign in with Gmail
# Grant permissions
# token.json will be created
# Press Ctrl+C to stop
```

### Step 4: Verify Token Created

```bash
# Check token exists
ls -la token.json

# Should show file (~1-2 KB)
```

### Step 5: Restart PM2 Processes

```bash
# Restart all watchers to pick up new credentials
pm2 restart all

# Check status
pm2 status

# View logs
pm2 logs gmail-watcher --lines 20
```

**Expected logs:**
```
[gmail-watcher] Started at 2026-02-XX...
[gmail-watcher] Watching Gmail inbox every 120 seconds
[gmail-watcher] Checking for important emails...
```

### Step 6: Test Email Detection

```bash
# Send test email to yourself
# Subject: URGENT: Test Email
# Wait 2-3 minutes

# Check Needs_Action folder
ls "$VAULT_PATH/Needs_Action/"

# Should see: EMAIL_xxx.md file
```

---

## 🔧 Alternative: Manual PM2 Config Update

Agar ecosystem.config.js manually edit karna ho:

```bash
# Edit ecosystem.config.js
nano ecosystem.config.js

# Gmail watcher entry already hai, just ensure env variables set:
# env: {
#   GMAIL_ENABLED: 'true',  ← Add this
#   VAULT_PATH: process.env.VAULT_PATH
# }
```

---

## 📋 Gmail Setup Complete Checklist

Jab ye sab done ho to Gmail fully working:

- [ ] Google Cloud verification complete
- [ ] credentials.json downloaded
- [ ] credentials.json in project root
- [ ] GMAIL_ENABLED=true in .env
- [ ] OAuth authentication done (token.json created)
- [ ] PM2 restarted
- [ ] Gmail watcher logs showing "Checking for emails"
- [ ] Test email detected successfully

---

## 🚀 Current System Works Without Gmail

**Abhi ye sab kaam kar raha hai:**

1. **File Drop Monitoring** ✅
   - Drop files in /Inbox/
   - Automatically process to /Needs_Action/
   - Metadata created

2. **Vault Management** ✅
   - Dashboard.md updates
   - Folder organization
   - Audit logging

3. **Orchestrator** ✅
   - Monitors /Needs_Action/
   - Triggers plan generation
   - Updates dashboard

4. **Plan Generation** ✅
   - For file drops
   - For manually created items
   - Claude Code skills working

**Sirf Gmail auto-detection disabled hai - baaki sab working!**

---

## 💡 Testing Without Gmail

Abhi testing ke liye:

### Test File Drop:
```bash
# Create test file
echo "Test document" > "$VAULT_PATH/Inbox/test.txt"

# Wait 30 seconds
sleep 30

# Check Needs_Action
ls "$VAULT_PATH/Needs_Action/"
# Should show: test.txt and test.txt.md
```

### Manually Create Email Entity:
```bash
# You can manually create email files for testing
cat > "$VAULT_PATH/Needs_Action/EMAIL_test_$(date +%s).md" << 'EOF'
---
type: email
from: test@example.com
subject: Test Manual Email
received: $(date -Iseconds)
priority: medium
status: pending
email_id: manual_test_123
---

## Email Content

This is a manually created email for testing plan generation.

Please process this item.
EOF

# Orchestrator will pick it up and create plan
```

---

## 📞 Support

**Agar Gmail enable karne mein issue aaye:**

1. Check credentials.json exists:
   ```bash
   ls -la credentials.json
   ```

2. Check .env file:
   ```bash
   cat .env | grep GMAIL
   ```

3. Check PM2 logs:
   ```bash
   pm2 logs gmail-watcher --err --lines 50
   ```

4. Re-authenticate if token expired:
   ```bash
   rm token.json
   uv run python src/watchers/gmail_watcher.py
   ```

---

## 🎯 Summary

**Now (Gmail Disabled)**:
- System is functional
- File drop working
- Can test other features
- No Gmail auto-detection

**Later (When Credentials Ready)**:
- Follow steps above
- Add credentials.json
- Set GMAIL_ENABLED=true
- Authenticate once
- Restart PM2
- Gmail detection starts working

**Time to Enable**: ~5 minutes (when credentials ready)

---

**This is a temporary state - Gmail can be added anytime later without re-implementing anything!**

**Focus on Silver Tier development now - Gmail will be plugged in when ready.**
