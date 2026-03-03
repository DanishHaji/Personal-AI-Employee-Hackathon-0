# AI Employee Dashboard

**Last Updated**: 2026-03-03 15:21:11

## Status

🟢 **RUNNING IN TEST MODE** (No Gmail API required)

## Quick Stats

- **Mode**: Test Mode (Mock Gmail)
- **Vault**: `/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0/test-vault`
- **Items Needing Action**: Check `/Needs_Action/` folder

## Recent Activity

Check `/Logs/audit_log.jsonl` for detailed activity.

## How to Test

### 1. Test Email Processing (Bronze Tier)
Drop a `.txt` file in `/Mock_Inbox/` with this format:
```
FROM: test@example.com
SUBJECT: Test Email
DATE: 2026-03-03T15:21:11.606422

This is a test email body.
```

### 2. Test File Processing (Bronze Tier)
Drop any file in `/Inbox/` folder.

### 3. Test Expense Tracking (Gold Tier)
Create a file in `/Mock_Inbox/`:
```
FROM: receipts@adobe.com
SUBJECT: Receipt - Software Purchase
DATE: 2026-03-03T15:21:11.606445

Amount: $45.99
Vendor: Adobe Creative Cloud
Category: software
```

### 4. Check Results
- New items appear in `/Needs_Action/`
- Plans generated in `/Plans/`
- Audit logs in `/Logs/audit_log.jsonl`

---

**Test Mode**: No Google Cloud verification needed!
