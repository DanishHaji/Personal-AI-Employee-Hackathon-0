# Encryption Key Backup and Recovery

**Personal AI Employee - Gold Tier**
**Version**: 1.0.0
**Last Updated**: 2026-03-02

⚠️ **CRITICAL**: Losing your encryption key means permanent data loss. Follow this guide carefully.

---

## Table of Contents

1. [Overview](#overview)
2. [What is Encrypted](#what-is-encrypted)
3. [How Encryption Works](#how-encryption-works)
4. [Backup Encryption Key](#backup-encryption-key)
5. [Key Recovery](#key-recovery)
6. [Key Rotation](#key-rotation)
7. [Emergency Procedures](#emergency-procedures)

---

## Overview

Gold Tier uses **AES-256-GCM encryption** for sensitive data:
- VIP contact information
- Financial receipts with PII
- Meeting notes with confidential content
- Any entity marked `encrypted: true`

**Encryption Key Storage**: System keyring (OS-managed secure storage)

**Backup Location**: Encrypted file in `$VAULT_PATH/.keys/` (user responsibility)

---

## What is Encrypted

### Always Encrypted
- **VIP Contacts** (`/Contacts/CONTACT_*.md` with `vip: true`)
  - Email addresses
  - Phone numbers
  - Conversation history
  - Personal notes

- **Sensitive Receipts** (`/Receipts/*.pdf` with `amount > $1000` or manual flag)
  - Receipt PDFs containing credit card info
  - Invoices with account numbers
  - Payment confirmations

- **Confidential Meeting Notes** (`/Meetings/*.md` with `confidential: true`)
  - Meeting transcripts
  - Action items with sensitive data
  - Participant details

### Never Encrypted (by default)
- Audit logs
- Budget tracking data
- Analytics insights
- Public documents
- Non-VIP contacts

---

## How Encryption Works

### Encryption Service

**Location**: `src/services/encryption_service.py`

**Algorithm**: AES-256-GCM (authenticated encryption)

**Key Derivation**: PBKDF2-HMAC-SHA256 (600,000 iterations)

**Key Storage**: Python `keyring` library
- **Linux**: GNOME Keyring, KWallet, or SecretService
- **macOS**: Keychain
- **Windows**: Credential Manager

### Encryption Flow

```
1. User creates VIP contact
2. encryption_service.py generates encryption key (first time only)
3. Key stored in system keyring: service="ai-employee-gold", username="encryption_key"
4. Contact data encrypted with AES-256-GCM
5. Encrypted data + nonce + tag stored in markdown file
6. Frontmatter marked: encrypted: true
```

### Decryption Flow

```
1. User opens encrypted contact
2. encryption_service.py retrieves key from keyring
3. Data decrypted with stored nonce and tag
4. Plaintext returned to application
```

---

## Backup Encryption Key

### Why Backup?

**Permanent Data Loss Scenarios**:
- System reinstall or OS upgrade
- Keyring corruption or reset
- Migration to new machine
- Keyring backend change

### Backup Methods

#### Method 1: Export to Encrypted File (Recommended)

```bash
# Export encryption key to password-protected file
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter backup password: ')
es.export_key_to_file('.keys/master.key.enc', backup_password)
print('✅ Key backed up to .keys/master.key.enc')
"
```

**Security**:
- Backup file is itself encrypted with your password
- Use strong password (16+ chars, mixed case, numbers, symbols)
- Store backup file in secure location (encrypted USB, password manager, etc.)

**DO NOT**:
- ❌ Commit `.keys/` to git (already in .gitignore)
- ❌ Upload to cloud without additional encryption
- ❌ Email backup file
- ❌ Store password with backup file

---

#### Method 2: Manual Export (Advanced)

```bash
# Export key as base64 string
uv run python -c "
from src.services.encryption_service import EncryptionService
import base64

es = EncryptionService('$VAULT_PATH')
key_bytes = es._get_or_create_key()
key_b64 = base64.b64encode(key_bytes).decode('utf-8')
print(f'Encryption Key: {key_b64}')
print('⚠️  Store this securely! Anyone with this key can decrypt your data.')
"
```

**Store in**:
- Password manager (1Password, Bitwarden, etc.) as secure note
- Encrypted USB drive
- Hardware security module (HSM)
- Paper backup in safe deposit box

---

### Backup Checklist

```
□ Export key to encrypted file (.keys/master.key.enc)
□ Test backup file recovery (see Key Recovery section)
□ Store backup in secure location (NOT on same machine)
□ Document backup password in password manager
□ Set reminder to rotate key annually
□ Verify backup before deleting original keyring
```

---

## Key Recovery

### Scenario 1: Lost Keyring (Have Backup File)

```bash
# Restore from encrypted backup file
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter backup password: ')
es.import_key_from_file('.keys/master.key.enc', backup_password)
print('✅ Key restored to system keyring')
"

# Verify restoration
uv run python -c "
from src.services.encryption_service import EncryptionService
es = EncryptionService('$VAULT_PATH')
print('✅ Key verified - can decrypt data')
"
```

---

### Scenario 2: Lost Keyring (Have Base64 Key)

```bash
# Import base64 key manually
uv run python -c "
from src.services.encryption_service import EncryptionService
import base64
import keyring

key_b64 = input('Enter base64 encryption key: ')
key_bytes = base64.b64decode(key_b64)

# Store in keyring
keyring.set_password('ai-employee-gold', 'encryption_key', key_bytes.hex())

# Verify
es = EncryptionService('$VAULT_PATH')
print('✅ Key imported successfully')
"
```

---

### Scenario 3: Migrating to New Machine

**On Old Machine**:
```bash
# Export key to encrypted file
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter backup password: ')
es.export_key_to_file('/tmp/migration.key.enc', backup_password)
"

# Copy to USB drive
cp /tmp/migration.key.enc /media/usb/
rm /tmp/migration.key.enc  # Delete from temp
```

**On New Machine**:
```bash
# Copy from USB
cp /media/usb/migration.key.enc ~/

# Import key
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter backup password: ')
es.import_key_from_file('~/migration.key.enc', backup_password)
print('✅ Migration complete')
"

# Delete backup file
rm ~/migration.key.enc
```

---

## Key Rotation

**When to Rotate**:
- Annually (recommended)
- After suspected key exposure
- Before sharing machine access
- After employee departure (team environments)

### Rotation Process

```bash
# 1. Backup old key first!
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter backup password: ')
es.export_key_to_file('.keys/old_key_2026-03-02.enc', backup_password)
"

# 2. Rotate encryption key (re-encrypts all data)
uv run python -c "
from src.services.encryption_service import EncryptionService

es = EncryptionService('$VAULT_PATH')
print('Rotating encryption key...')
es.rotate_key()
print('✅ Key rotation complete')
print('⚠️  Old backup files cannot decrypt new data!')
"

# 3. Create new backup
uv run python -c "
from src.services.encryption_service import EncryptionService
import getpass

es = EncryptionService('$VAULT_PATH')
backup_password = getpass.getpass('Enter NEW backup password: ')
es.export_key_to_file('.keys/master.key.enc', backup_password)
print('✅ New key backed up')
"

# 4. Securely delete old key backup (if desired)
shred -vfz -n 10 .keys/old_key_2026-03-02.enc
```

**⚠️ WARNING**: After rotation, old backup files cannot decrypt new data. Keep old backups if you have archived encrypted files.

---

## Emergency Procedures

### Emergency Scenario Matrix

| Scenario | Have Backup? | Recovery Possible? | Action |
|----------|-------------|-------------------|--------|
| Keyring corrupted | ✅ Yes | ✅ Yes | Restore from backup |
| Keyring corrupted | ❌ No | ❌ No | Permanent data loss |
| Forgot backup password | ✅ Have key | ✅ Yes | Import base64 key |
| Machine stolen | ✅ Yes (offsite) | ✅ Yes | Restore on new machine |
| Machine stolen | ❌ No | ❌ No | Permanent data loss |
| Key exposed | ✅ Yes | ✅ Yes | Rotate key immediately |

---

### Emergency Recovery Steps

#### Step 1: Assess Damage

```bash
# Check if keyring still has key
uv run python -c "
import keyring
key = keyring.get_password('ai-employee-gold', 'encryption_key')
print('✅ Key found in keyring' if key else '❌ Key not found')
"

# Check encrypted files
find "$VAULT_PATH" -name "*.md" -exec grep -l "encrypted: true" {} \; | wc -l
```

---

#### Step 2: Attempt Recovery

**Try in order**:

1. **Restore from backup file** (if exists)
2. **Import base64 key** (if stored in password manager)
3. **Check old machine backup** (if available)
4. **Contact system admin** (if team environment)

---

#### Step 3: Damage Control

If no recovery possible:

```bash
# List affected files
find "$VAULT_PATH" -name "*.md" -exec grep -l "encrypted: true" {} \;

# Mark as inaccessible
for file in $(find "$VAULT_PATH" -name "*.md" -exec grep -l "encrypted: true" {} \;); do
  echo "⚠️ ENCRYPTED - KEY LOST" >> "$file"
done

# Create incident report
cat > "$VAULT_PATH/INCIDENT_encryption_key_lost_$(date +%Y-%m-%d).md" << EOF
# Encryption Key Loss Incident

**Date**: $(date)
**Status**: ❌ Key permanently lost
**Affected Files**: $(find "$VAULT_PATH" -name "*.md" -exec grep -l "encrypted: true" {} \; | wc -l)

## Impact
- VIP contacts inaccessible
- Sensitive receipts inaccessible
- Confidential meeting notes inaccessible

## Root Cause
[Describe what happened]

## Prevention
- [ ] Implement backup automation
- [ ] Store backup offsite
- [ ] Test recovery quarterly
EOF
```

---

### Prevention Best Practices

**Backup Automation** (Recommended):

```bash
# Create cron job for weekly backups
crontab -e

# Add line:
0 0 * * 0 /path/to/backup_encryption_key.sh
```

**backup_encryption_key.sh**:
```bash
#!/bin/bash
set -e

VAULT_PATH="$VAULT_PATH"
BACKUP_DIR="$HOME/secure_backups"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

# Export key
uv run python -c "
from src.services.encryption_service import EncryptionService
es = EncryptionService('$VAULT_PATH')
es.export_key_to_file('$BACKUP_DIR/key_backup_$DATE.enc', '$BACKUP_PASSWORD')
"

# Keep last 4 weekly backups
ls -t "$BACKUP_DIR"/key_backup_*.enc | tail -n +5 | xargs rm -f

echo "✅ Backup completed: $BACKUP_DIR/key_backup_$DATE.enc"
```

---

## Testing Recovery

**Test Quarterly**:

```bash
# 1. Export key
uv run python -c "
from src.services.encryption_service import EncryptionService
es = EncryptionService('$VAULT_PATH')
es.export_key_to_file('/tmp/test_backup.key.enc', 'test_password')
"

# 2. Temporarily rename keyring key
uv run python -c "
import keyring
old_key = keyring.get_password('ai-employee-gold', 'encryption_key')
keyring.set_password('ai-employee-gold', 'encryption_key_backup', old_key)
keyring.delete_password('ai-employee-gold', 'encryption_key')
"

# 3. Restore from backup
uv run python -c "
from src.services.encryption_service import EncryptionService
es = EncryptionService('$VAULT_PATH')
es.import_key_from_file('/tmp/test_backup.key.enc', 'test_password')
print('✅ Recovery test successful')
"

# 4. Cleanup
rm /tmp/test_backup.key.enc
uv run python -c "
import keyring
keyring.delete_password('ai-employee-gold', 'encryption_key_backup')
"
```

---

## Summary Checklist

**Setup** (One-time):
- [ ] Verify keyring backend: `uv run python -c "import keyring; print(keyring.get_keyring())"`
- [ ] Create initial backup: Run export script
- [ ] Store backup offsite: USB drive, password manager, etc.
- [ ] Document backup password securely

**Ongoing** (Regular):
- [ ] Weekly automated backups (cron job)
- [ ] Quarterly recovery testing
- [ ] Annual key rotation
- [ ] Update backup after rotation

**Emergency**:
- [ ] Attempt recovery from backup file
- [ ] Try base64 key import if backup password lost
- [ ] Document incident if key permanently lost
- [ ] Implement preventive measures

---

**⚠️ REMEMBER**: Encrypted data without the key is **permanently inaccessible**. No recovery is possible.

**Version**: Gold Tier 1.0.0
**Last Updated**: 2026-03-02
