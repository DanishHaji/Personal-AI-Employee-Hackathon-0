# Personal AI Employee - Testing Guide (बिना Gmail के)

**Problem**: Gmail ID Google Cloud par verify nahi ho rahi
**Solution**: Test Mode use karo - NO GMAIL API REQUIRED! ✅

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Test Mode Setup

```bash
# Terminal kholo
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"

# Test script run karo
python test_run.py
```

**Ye script automatically**:
- ✅ Test vault bana dega
- ✅ Sample files create karega
- ✅ Gmail ke bina kaam karega!

### Step 2: Watchers Start Karo

Script puchega: `Start watchers now? (y/n)`

**Option 1**: `y` type karo (Automatic)
- Dono watchers automatically start ho jayenge

**Option 2**: `n` type karo (Manual)
```bash
# Terminal 1: Mock Gmail Watcher
python src/watchers/mock_gmail_watcher.py

# Terminal 2: File System Watcher
python src/watchers/filesystem_watcher.py
```

### Step 3: Test Karo!

**3 sample files already bane honge**:
1. `Mock_Inbox/sample_email_meeting.txt` - Email test ke liye
2. `Inbox/project_proposal.txt` - File test ke liye

**Results check karo**:
```bash
# Detected items
ls test-vault/Needs_Action/

# Audit logs
cat test-vault/Logs/audit_log.jsonl
```

---

## 🧪 Test Scenarios (Detailed)

### Test 1: Email Processing (Bronze Tier)

**Mock email banao**:

1. File create karo: `test-vault/Mock_Inbox/test_email.txt`

```
FROM: boss@example.com
SUBJECT: Urgent: Budget Approval Needed
DATE: 2026-03-03T10:00:00

Hi,

Please review and approve the Q2 budget by Friday.

Thanks,
Boss
```

2. **Wait 30 seconds** (watcher check karega)

3. Result dekho:
```bash
ls test-vault/Needs_Action/
# EMAIL_20260303_100000_Urgent_Budget_Approval.md bana hoga
```

4. Email entity kholo aur dekho:
```bash
cat test-vault/Needs_Action/EMAIL_*.md
```

---

### Test 2: File Drop (Bronze Tier)

1. Koi bhi file `test-vault/Inbox/` mein daalo:
```bash
# Example: Text file
echo "Important document" > test-vault/Inbox/important_doc.txt

# Ya koi existing file copy karo
cp ~/Desktop/proposal.pdf test-vault/Inbox/
```

2. **Wait 10 seconds**

3. Result:
```bash
ls test-vault/Needs_Action/
# FILEDROP_20260303_*.md file bani hogi
```

---

### Test 3: Meeting Request Email

Mock email:
```
FROM: colleague@example.com
SUBJECT: Meeting Request: Q2 Planning
DATE: 2026-03-03T14:00:00

Hi,

Can we schedule a meeting to discuss Q2 planning?

I'm available:
- Tomorrow 2pm
- Thursday 10am

Thanks,
John
```

**Expected Result**:
- Email entity ban jayegi
- AI detect karega ki meeting request hai
- (Gold Tier calendar nahi hai toh manual review hoga)

---

### Test 4: Expense Receipt Email (Gold Tier)

Mock receipt email:
```
FROM: receipts@adobe.com
SUBJECT: Receipt - Adobe Creative Cloud
DATE: 2026-03-03T09:00:00

Your receipt for Adobe Creative Cloud subscription

Amount: $45.99
Date: 2026-03-03
Category: Software

Thank you!
```

**Expected Result**:
- Email entity `Needs_Action/` mein
- Keywords detect honge: "receipt", "amount"
- (Full OCR ke liye image chahiye, but detection hoga)

---

## 📊 Project Features Test Karna

### Bronze Tier ✅ (Gmail ke bina test kar sakte ho)

| Feature | Test Method | Expected Result |
|---------|-------------|-----------------|
| Email Detection | Mock email file drop | Entity in Needs_Action/ |
| File Processing | File drop in Inbox/ | Entity in Needs_Action/ |
| Dashboard | Check Dashboard.md | Updated status |
| Audit Logging | Check Logs/audit_log.jsonl | Events logged |

### Silver Tier ⚠️ (Partial testing)

| Feature | Test Method | Status |
|---------|-------------|---------|
| Email Sending | Requires Gmail API | ❌ Skip |
| Social Media | Requires API keys | ❌ Skip |
| WhatsApp | Requires API | ❌ Skip |
| Scheduler | Mock events | ✅ Can test |

### Gold Tier ⚠️ (Partial testing)

| Feature | Test Method | Status |
|---------|-------------|---------|
| Trust Rules | Mock email + rules | ✅ Can test |
| Calendar | Requires Google API | ❌ Skip |
| Meetings | Requires Zoom | ❌ Skip |
| CRM Contacts | Mock emails | ✅ Can test |
| Analytics | Audit logs | ✅ Can test |
| Expenses | Mock receipts | ⚠️ Partial |
| Documents | Templates | ✅ Can test |
| Suggestions | Audit logs | ✅ Can test |

---

## 🔧 Troubleshooting

### Problem 1: "Module not found" error

```bash
# Solution: Dependencies install karo
pip install watchdog pyyaml
```

### Problem 2: Watcher start nahi ho raha

```bash
# Check: Python path correct hai?
which python3

# Run with full path
python3 src/watchers/mock_gmail_watcher.py
```

### Problem 3: Files detect nahi ho rahe

**Check**:
1. Watcher chal raha hai? (Terminal mein logs dikhengi)
2. File correct folder mein hai?
   - Emails → `Mock_Inbox/`
   - Files → `Inbox/`
3. File format correct hai? (`.txt` for emails)

### Problem 4: Vault path not found

```bash
# .env.test file check karo
cat .env.test

# Ya manually set karo
export VAULT_PATH="/full/path/to/test-vault"
```

---

## 📁 Folder Structure (Test Mode)

```
test-vault/
├── Mock_Inbox/           # 📧 Yahan email files (.txt) daalo
├── Inbox/                # 📁 Yahan koi bhi files daalo
├── Needs_Action/         # ✅ Detected items yahan ayengi
├── Plans/                # 📋 AI plans yahan banengi
├── Done/                 # ✅ Completed items
├── Logs/
│   ├── audit_log.jsonl   # 📊 Har action log hoga
│   └── processed_emails.json
├── Contacts/             # 👥 CRM contacts (Gold)
├── Expenses/             # 💰 Expenses (Gold)
├── Documents/            # 📄 Generated docs (Gold)
├── Dashboard.md          # 📊 Status dashboard
└── Company_Handbook.md   # 📖 Trust rules
```

---

## 🎓 Advanced Testing

### Custom Email Format

Email file ka structure:
```
FROM: sender@example.com
SUBJECT: Subject line here
DATE: 2026-03-03T10:00:00

Email body yahan likho.
Multiple lines allowed.

Attachments mention kar sakte ho but actual attachment nahi.
```

### Multiple Emails Ek Saath

```bash
# 5 test emails generate karo
for i in {1..5}; do
  cat > test-vault/Mock_Inbox/email_$i.txt <<EOF
FROM: user$i@example.com
SUBJECT: Test Email $i
DATE: 2026-03-03T10:0$i:00

This is test email number $i.
EOF
done
```

### Audit Logs Analyze Karna

```bash
# Total emails processed
cat test-vault/Logs/audit_log.jsonl | grep email_detected | wc -l

# Recent activity (last 10)
tail -10 test-vault/Logs/audit_log.jsonl | jq .
```

---

## 🚀 Next Steps (Gmail Verify Hone Ke Baad)

Jab Gmail verify ho jaye:

1. **Real Gmail API enable karo**:
   ```bash
   cp .env.example .env
   # Add real credentials
   ```

2. **Switch to production**:
   ```bash
   # Real Gmail watcher
   python src/watchers/gmail_watcher.py --auth-only  # First time
   python src/watchers/gmail_watcher.py              # Regular use
   ```

3. **PM2 se manage karo**:
   ```bash
   pm2 start ecosystem.config.js
   pm2 status
   ```

---

## 🎉 Success Criteria

Aapka project **successfully test ho gaya** agar:

✅ Mock Gmail watcher chal raha hai
✅ File system watcher chal raha hai
✅ Email files Mock_Inbox/ se detect ho rahe hain
✅ Entities Needs_Action/ mein ban rahe hain
✅ Audit log mein events log ho rahe hain
✅ Dashboard.md update ho raha hai

---

## 💡 Tips

1. **Terminal khula rakho** - Logs dekhne ke liye
2. **Sample files use karo** - Already bane hain
3. **Ek ek feature test karo** - Rush mat karo
4. **Logs check karte raho** - Debugging easy hogi

---

## 🆘 Help

Agar koi problem aa rahi hai:

1. **Logs dekho**:
   ```bash
   tail -f test-vault/Logs/audit_log.jsonl
   ```

2. **Watcher logs dekho**:
   Terminal mein watcher ke logs dikhengi

3. **File structure check karo**:
   ```bash
   tree test-vault/
   ```

---

**Happy Testing! 🎊**

Gmail verification ki tension mat lo - Test mode se poora project check kar sakte ho!
