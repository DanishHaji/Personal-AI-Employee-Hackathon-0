# 🚀 Quick Start - Test Mode (Gmail ke bina)

## Sirf 3 Steps mein apna Project Test karo!

---

## ✅ Step 1: Terminal kholo

```bash
cd "/mnt/e/Hackathon 0 AI Employee/Personal AI Employee Hackathon 0"
```

---

## ✅ Step 2: Test Script Run karo

```bash
python test_run.py
```

**Script puchega**: `Start watchers now? (y/n)`

**Type karo**: `y`

---

## ✅ Step 3: Test karo!

### Option A: Sample Files Already Created hain

Script ne automatically 2 sample files banayi hain:
1. Email: `test-vault/Mock_Inbox/sample_email_meeting.txt`
2. File: `test-vault/Inbox/project_proposal.txt`

**Wait 30 seconds**, phir check karo:

```bash
ls test-vault/Needs_Action/
```

**Result**: 2 new files bani hongi! ✅

---

### Option B: Khud Test Email banao

```bash
cat > test-vault/Mock_Inbox/my_test_email.txt <<EOF
FROM: boss@example.com
SUBJECT: Important Task
DATE: 2026-03-03T10:00:00

Please review the attached document.

Thanks!
EOF
```

**Wait 30 seconds**, phir:

```bash
ls test-vault/Needs_Action/
# EMAIL_* file bani hogi
```

---

## 📊 Results Check karo

### 1. Detected Items
```bash
ls -la test-vault/Needs_Action/
```

### 2. Audit Logs
```bash
cat test-vault/Logs/audit_log.jsonl
```

### 3. Dashboard
```bash
cat test-vault/Dashboard.md
```

---

## 🎉 Success!

Agar ye sab kuch dikh raha hai, toh **project kaam kar raha hai**! ✅

- ✅ Mock Gmail watcher chal raha hai
- ✅ File watcher chal raha hai
- ✅ Emails detect ho rahe hain
- ✅ Entities ban rahe hain

---

## 🛑 Stop karne ke liye

Terminal mein:
```
Ctrl + C
```

---

## 🔄 Phir se Start karne ke liye

### Option 1: Automatic (Recommended)
```bash
python test_run.py
# Type 'y' when asked
```

### Option 2: Manual
```bash
# Terminal 1
python src/watchers/mock_gmail_watcher.py

# Terminal 2
python src/watchers/filesystem_watcher.py
```

---

## 📁 Important Folders

| Folder | Purpose | Test karne ke liye |
|--------|---------|------------------|
| `test-vault/Mock_Inbox/` | Mock emails | Email `.txt` files yahan daalo |
| `test-vault/Inbox/` | Files | Koi bhi file yahan daalo |
| `test-vault/Needs_Action/` | Results | Detected items yahan aati hain |
| `test-vault/Logs/` | Audit logs | Activity log yahan hai |

---

## 🧪 Test Examples

### Email Test
```bash
echo "FROM: test@example.com
SUBJECT: Test Email
DATE: 2026-03-03T10:00:00

This is a test." > test-vault/Mock_Inbox/test1.txt
```

### File Test
```bash
echo "Test document" > test-vault/Inbox/test_file.txt
```

**Wait 10-30 seconds**, check `Needs_Action/` ✅

---

## ❓ Problems?

### "python: command not found"
```bash
python3 test_run.py
```

### "Module not found"
```bash
pip install watchdog pyyaml
```

### Kuch detect nahi ho raha
1. Check watcher chal raha hai? (Terminal mein logs dikhenge)
2. File correct folder mein hai?
3. Wait kiya 30 seconds?

---

## 📖 Detailed Guide

Jyada details ke liye dekho:
- `TESTING_GUIDE_HINGLISH.md` - Complete testing guide
- `README.md` - Project overview

---

## 💡 Pro Tips

1. **Terminal open rakho** - Logs dekhne ke liye
2. **Sample files use karo** - Already created hain
3. **Ek-ek test karo** - Step by step
4. **Logs dekhte raho** - Problems pata chalengi

---

## 🎯 What Works in Test Mode?

### ✅ Can Test (No APIs needed)
- Bronze Tier: Email detection, File processing
- Gold Tier: Trust rules, CRM contacts, Analytics, Documents

### ❌ Cannot Test (Requires APIs)
- Silver Tier: Email sending, Social media, WhatsApp
- Gold Tier: Google Calendar, Zoom meetings, Real OCR

---

## 🚀 After Testing

Jab satisfied ho jao test mode se, toh:

1. Gmail verify kara lo Google Cloud par
2. Real credentials add karo `.env` mein
3. Production mode mein switch karo

---

**Bas itna! Ab test karo! 🎊**

Gmail ki tension chhodo - Test mode se sab kuch check kar sakte ho!
