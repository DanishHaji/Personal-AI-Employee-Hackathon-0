# Gmail API Setup Guide

**Complete guide to setting up Gmail API OAuth2 credentials for the Personal AI Employee**

This guide walks you through creating Gmail API credentials, authenticating your account, and troubleshooting common issues.

---

## Prerequisites

- Gmail account (personal or Google Workspace)
- Access to Google Cloud Console
- Chrome or Firefox browser (for OAuth flow)

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Gmail account
3. Click **Select a project** dropdown (top navigation bar)
4. Click **New Project**
5. Enter project details:
   - **Project name**: `Personal AI Employee`
   - **Organization**: Leave as "No organization" (for personal use)
   - **Location**: Leave as default
6. Click **Create**
7. Wait for project creation (10-30 seconds)
8. Select your new project from the dropdown

---

## Step 2: Enable Gmail API

1. In Google Cloud Console, ensure your project is selected
2. Navigate to **APIs & Services** → **Library** (left sidebar)
3. Search for "Gmail API" in the search box
4. Click on **Gmail API** in search results
5. Click **Enable** button
6. Wait for API to be enabled (5-10 seconds)

---

## Step 3: Create OAuth 2.0 Credentials

### Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen** (left sidebar)
2. Select **External** user type (unless you have Google Workspace)
3. Click **Create**
4. Fill in consent screen details:
   - **App name**: `Personal AI Employee`
   - **User support email**: Your Gmail address
   - **Developer contact email**: Your Gmail address
   - Leave other fields empty/default
5. Click **Save and Continue**
6. On **Scopes** page, click **Add or Remove Scopes**
7. Filter for "Gmail API" and select:
   - `https://www.googleapis.com/auth/gmail.readonly` (Read all emails)
   - Or: `https://www.googleapis.com/auth/gmail.modify` (Silver tier for sending)
8. Click **Update** → **Save and Continue**
9. On **Test users** page, click **Add Users**
10. Enter your Gmail address
11. Click **Add** → **Save and Continue**
12. Click **Back to Dashboard**

### Create OAuth2 Client ID

1. Navigate to **APIs & Services** → **Credentials** (left sidebar)
2. Click **+ Create Credentials** → **OAuth client ID**
3. Select **Application type**: **Desktop app**
4. **Name**: `Personal AI Employee Desktop`
5. Click **Create**
6. **Important**: Click **Download JSON** in the popup
7. Save file as `credentials.json` in your project root directory

---

## Step 4: Authenticate Your Account

### First-Time Authentication

1. Ensure `credentials.json` is in project root:

```bash
ls credentials.json  # Should exist
```

2. Set VAULT_PATH in .env file:

```bash
echo "VAULT_PATH=/path/to/your/vault" >> .env
```

3. Run the Gmail Watcher for first-time authentication:

```bash
uv run python src/watchers/gmail_watcher.py
```

4. **OAuth Flow**:
   - Browser window will automatically open
   - Select your Gmail account
   - Click **Continue** on "Google hasn't verified this app" warning (expected for test apps)
   - Click **Continue** again to confirm
   - Review permissions and click **Allow**
   - See "The authentication flow has completed" → Close browser tab

5. **Verify token.json created**:

```bash
ls token.json  # Should now exist
```

6. **Stop the watcher** (Ctrl+C)

### Token Storage

- `credentials.json`: OAuth2 client credentials (downloaded from Google Cloud)
- `token.json`: Access + refresh tokens (auto-generated after authentication)

**Security Notes**:
- ✅ `credentials.json` and `token.json` are in `.gitignore` (never commit)
- ✅ Both files stored outside Obsidian vault (FR-017)
- ✅ Bronze tier uses `gmail.readonly` scope (cannot send emails)

---

## Step 5: Start Watchers with PM2

Once authentication is complete, start all watchers:

```bash
# Start all processes
pm2 start ecosystem.config.js

# Verify Gmail Watcher is running
pm2 logs gmail-watcher --lines 20
```

**Expected output**:
```
[Gmail Watcher] Started at 2026-02-21T...
[Gmail Watcher] Watching Gmail inbox every 120 seconds
[Gmail Watcher] Checking for important emails...
```

---

## Troubleshooting

### Issue: "credentials.json not found"

**Solution**:
1. Verify you downloaded `credentials.json` from Google Cloud Console
2. Place file in project root (same directory as `ecosystem.config.js`)
3. Check filename is exactly `credentials.json` (not `credentials (1).json`)

```bash
# Verify file location
ls -la credentials.json
```

### Issue: "token.json is invalid"

**Cause**: Token expired or OAuth scopes changed

**Solution**:
1. Delete `token.json`:

```bash
rm token.json
```

2. Re-authenticate:

```bash
uv run python src/watchers/gmail_watcher.py
```

3. Browser will open for re-authorization

### Issue: "Google hasn't verified this app" warning

**Cause**: OAuth consent screen is in "Testing" mode (expected for personal use)

**Solution**: This is normal for test apps. Click **Continue** to proceed.

**Optional - Publish App** (if you want to remove warning):
1. Go to **OAuth consent screen** in Google Cloud Console
2. Click **Publish App**
3. Submit for verification (takes 4-6 weeks, NOT required for personal use)

### Issue: "Access blocked: authorization error"

**Cause**: Your email not added as test user

**Solution**:
1. Go to **OAuth consent screen** → **Test users**
2. Click **Add Users**
3. Enter your Gmail address
4. Click **Add**
5. Delete `token.json` and re-authenticate

### Issue: "Rate limit exceeded (429 error)"

**Cause**: Too many Gmail API requests in short time

**Solution**:
- Gmail Watcher uses exponential backoff (1s, 2s, 4s, 8s)
- Wait 1-2 minutes and retry
- Check PM2 logs: `pm2 logs gmail-watcher`
- Default check interval is 120 seconds (sufficient for Bronze tier)

### Issue: "Token refresh failed"

**Solution**:
1. Delete both credential files:

```bash
rm token.json
rm credentials.json
```

2. Re-download fresh `credentials.json` from Google Cloud Console
3. Re-authenticate

### Issue: Gmail Watcher crashes immediately

**Check logs**:

```bash
pm2 logs gmail-watcher --lines 50 --err
```

**Common causes**:
- `VAULT_PATH` not set in `.env` file
- Vault directory doesn't exist (run `uv run python scripts/init_vault.py --path /path/to/vault`)
- credentials.json has wrong format (re-download)
- Python dependencies not installed (run `uv sync`)

---

## Advanced Configuration

### Change Check Interval

Default: 120 seconds (2 minutes)

Edit `src/watchers/gmail_watcher.py`:

```python
watcher = GmailWatcher(
    vault_path=vault_path,
    check_interval=300  # 5 minutes
)
```

Or use environment variable:

```bash
echo "GMAIL_CHECK_INTERVAL=300" >> .env
```

### Add Custom Urgent Keywords

Edit `Company_Handbook.md` in your vault:

```markdown
## Email Rules

### Urgent Keywords
- urgent
- asap
- critical
- invoice
- payment
- [your custom keywords]
```

Gmail Watcher reads these keywords on each check.

### Increase Gmail API Quota

**Default quota**: 250 quota units/user/second (sufficient for <100 emails/day)

**If you need more**:
1. Go to **APIs & Services** → **Gmail API** → **Quotas**
2. Click **Request a quota increase**
3. Justify your use case
4. Approval takes 2-5 business days

---

## Testing Your Setup

### Test 1: Send Test Email

1. Send email to yourself with subject containing "URGENT"
2. Wait 2-3 minutes (Gmail Watcher checks every 120 seconds)
3. Open Obsidian vault
4. Check `/Needs_Action/` folder for new `EMAIL_*.md` file
5. Verify `Dashboard.md` shows +1 pending item

### Test 2: Verify Dashboard Updates

```bash
# Watch dashboard file
watch -n 5 cat /path/to/vault/Dashboard.md

# Send urgent email to yourself
# Dashboard should update within 2-3 minutes
```

### Test 3: Check Audit Logs

```bash
# View today's audit log
cat /path/to/vault/Logs/$(date +%Y-%m-%d).json

# Should show email_detected entries
```

---

## Security Best Practices

✅ **Never commit credentials to Git**
- `.gitignore` includes `credentials.json` and `token.json`
- Verify: `git status` should not show these files

✅ **Store credentials outside vault**
- Project root is outside Obsidian vault (FR-017)
- Vault only contains processed data (no secrets)

✅ **Use readonly scope for Bronze tier**
- `gmail.readonly` prevents accidental email sending
- Upgrade to `gmail.modify` only in Silver tier (with HITL approval)

✅ **Review audit logs regularly**
- All Gmail API calls logged to `/Logs/YYYY-MM-DD.json`
- 90-day retention (Principle VII)

✅ **Rotate credentials if compromised**
1. Delete `credentials.json` and `token.json`
2. In Google Cloud Console → **Credentials**, delete old OAuth2 client
3. Create new OAuth2 client
4. Download new `credentials.json`
5. Re-authenticate

---

## Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth 2.0 Overview](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)

---

## Support

If you encounter issues not covered here:

1. Check PM2 logs: `pm2 logs gmail-watcher --lines 100`
2. Check audit logs: `cat /path/to/vault/Logs/$(date +%Y-%m-%d).json`
3. Review [troubleshooting section in README.md](../README.md#troubleshooting)
4. Check constitution: `.specify/memory/constitution.md` (Principle I - Gmail integration rules)

---

**Setup complete! Your AI Employee can now monitor Gmail for important emails.**
