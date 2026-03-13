# Platinum Tier Testing Guide

**Version**: 0.4.0 (Platinum Tier - Phase 1)
**Components**: VaultSyncService, ClaimManager
**Last Updated**: 2026-03-06

## Overview

This guide provides comprehensive testing procedures for Platinum Tier foundational components before moving to production deployment.

---

## Test Suite 1: VaultSyncService

### Test 1.1: Basic Pull Sync

**Objective**: Verify Cloud instance can pull changes from Local

**Prerequisites**:
- Git repository configured with remote
- Both instances have repository cloned

**Steps (Local)**:
```bash
# Create test file
echo "Test Pull Sync $(date)" > test-pull.md

# Commit and push
git add test-pull.md
git commit -m "test: pull sync validation"
git push origin 004-platinum-tier-upgrade
```

**Steps (Cloud)**:
```bash
# Pull changes
uv run python -m src.services.vault_sync_service sync --direction pull --instance cloud

# Verify file exists
cat test-pull.md
```

**Expected Result**:
- ✅ File `test-pull.md` exists on Cloud
- ✅ Content matches Local
- ✅ Sync logged to `Logs/sync.jsonl` with status="success"

---

### Test 1.2: Basic Push Sync

**Objective**: Verify Cloud instance can push changes to Local

**Steps (Cloud)**:
```bash
# Create test file
echo "Test Push Sync $(date)" > test-push.md

# Sync (auto-commits and pushes)
uv run python -m src.services.vault_sync_service sync --direction push --instance cloud

# Verify pushed
git log -1 --oneline
```

**Steps (Local)**:
```bash
# Pull changes
uv run python -m src.services.vault_sync_service sync --direction pull --instance local

# Verify file exists
cat test-push.md
```

**Expected Result**:
- ✅ File `test-push.md` exists on Local
- ✅ Content matches Cloud
- ✅ Git commit message: "[cloud] Auto-sync at <timestamp>"

---

### Test 1.3: Bidirectional Sync

**Objective**: Verify changes propagate both ways

**Steps (Local)**:
```bash
# Create file A
echo "From Local" > file-a.md
uv run python -m src.services.vault_sync_service sync --direction push --instance local
```

**Steps (Cloud)**:
```bash
# Create file B
echo "From Cloud" > file-b.md
uv run python -m src.services.vault_sync_service sync --direction bidirectional --instance cloud

# Verify both files exist
ls -la file-a.md file-b.md
```

**Steps (Local)**:
```bash
# Sync
uv run python -m src.services.vault_sync_service sync --direction pull --instance local

# Verify both files exist
ls -la file-a.md file-b.md
```

**Expected Result**:
- ✅ Both instances have both files
- ✅ No conflicts detected

---

### Test 1.4: Secret Filtering

**Objective**: Verify secrets are blocked from syncing

**Steps (Local)**:
```bash
# Create secret file
echo "SECRET_KEY=test123" > .env.secret
echo "API_TOKEN=abc456" >> .env.secret

# Try to sync
git add .env.secret
uv run python -m src.services.vault_sync_service sync --direction push --instance local

# Check sync log
cat Logs/sync.jsonl | tail -1 | jq '.secrets_blocked'
```

**Expected Result**:
- ✅ `.env.secret` in secrets_blocked array
- ✅ File NOT pushed to remote
- ✅ File unstaged by filter_secrets()

**Cleanup**:
```bash
rm .env.secret
git reset HEAD .env.secret
```

---

### Test 1.5: Conflict Detection

**Objective**: Verify conflicts are detected when both instances edit same file

**Steps (Local)**:
```bash
# Create base file
echo "Line 1" > conflict-test.md
git add conflict-test.md
git commit -m "test: conflict base"
git push origin 004-platinum-tier-upgrade
```

**Steps (Cloud)**:
```bash
# Pull base
uv run python -m src.services.vault_sync_service sync --direction pull --instance cloud

# Edit file (don't sync yet)
echo "Cloud Edit" >> conflict-test.md
```

**Steps (Local)**:
```bash
# Edit same file
echo "Local Edit" >> conflict-test.md
git add conflict-test.md
git commit -m "test: local edit"
git push origin 004-platinum-tier-upgrade
```

**Steps (Cloud)**:
```bash
# Try to sync (should detect conflict)
uv run python -m src.services.vault_sync_service sync --direction bidirectional --instance cloud

# Check sync log
cat Logs/sync.jsonl | tail -1 | jq '.status'
# Should show: "conflict"

cat Logs/sync.jsonl | tail -1 | jq '.conflict_files'
# Should show: ["conflict-test.md"]
```

**Expected Result**:
- ✅ Status: "conflict"
- ✅ conflict_files contains "conflict-test.md"
- ✅ Conflict logged to sync_conflicts.jsonl

**Cleanup**:
```bash
# Resolve conflict (keep local version)
git checkout --theirs conflict-test.md
git add conflict-test.md
git commit -m "test: resolve conflict"
```

---

### Test 1.6: Large File Sync Performance

**Objective**: Measure sync performance with multiple files

**Steps (Local)**:
```bash
# Create 50 test files
for i in {1..50}; do
  echo "Test file $i content $(date)" > test-file-$i.md
done

# Measure sync time
time uv run python -m src.services.vault_sync_service sync --direction push --instance local

# Check sync duration
cat Logs/sync.jsonl | tail -1 | jq '.duration_ms'
```

**Expected Result**:
- ✅ All 50 files synced successfully
- ✅ Duration < 30 seconds (per spec SC-002)
- ✅ Status: "success"

**Cleanup**:
```bash
rm test-file-*.md
git add .
git commit -m "test: cleanup performance test files"
git push
```

---

## Test Suite 2: ClaimManager

### Test 2.1: Basic Claim Creation

**Objective**: Verify claims can be created

**Steps**:
```bash
# Claim task from cloud instance
uv run python -m src.services.claim_manager claim \
  --task-id TEST_CLAIM_001 \
  --zone cloud \
  --action-type email_reply

# Verify claim file created
ls -la Claims/TEST_CLAIM_001.claim.md
cat Claims/TEST_CLAIM_001.claim.md

# Check claim log
cat Logs/claims.jsonl | tail -1 | jq
```

**Expected Result**:
- ✅ Claim file exists in `Claims/TEST_CLAIM_001.claim.md`
- ✅ Claimed by: cloud
- ✅ Expires at: ~15 minutes from now
- ✅ Status: active
- ✅ Event logged to claims.jsonl

---

### Test 2.2: Claim Conflict Detection

**Objective**: Verify task claimed by one zone cannot be claimed by another

**Steps**:
```bash
# Cloud claims task
uv run python -m src.services.claim_manager claim \
  --task-id TEST_CONFLICT \
  --zone cloud \
  --action-type test

# Try to claim from local (should fail)
uv run python -m src.services.claim_manager claim \
  --task-id TEST_CONFLICT \
  --zone local \
  --action-type test
```

**Expected Result**:
- ✅ Second claim fails with TaskAlreadyClaimedError
- ✅ Error message: "Task TEST_CONFLICT already claimed by cloud until <timestamp>"

---

### Test 2.3: Claim Checking

**Objective**: Verify claim status can be checked

**Steps**:
```bash
# Create claim
uv run python -m src.services.claim_manager claim \
  --task-id TEST_CHECK \
  --zone cloud \
  --action-type test

# Check claim
uv run python -m src.services.claim_manager check \
  --task-id TEST_CHECK

# Check non-existent claim
uv run python -m src.services.claim_manager check \
  --task-id NONEXISTENT
```

**Expected Result**:
- ✅ First check shows claim details (claim ID, claimed by, expires at)
- ✅ Second check shows "Task unclaimed: NONEXISTENT"

---

### Test 2.4: Claim Release

**Objective**: Verify claims can be released

**Steps**:
```bash
# Create claim
uv run python -m src.services.claim_manager claim \
  --task-id TEST_RELEASE \
  --zone cloud \
  --action-type test

# Get claim ID from output
CLAIM_ID="CLAIM_<timestamp>_TEST_RELEASE"

# Release claim
uv run python -m src.services.claim_manager release \
  --claim-id $CLAIM_ID \
  --zone cloud

# Verify claim file deleted
ls Claims/TEST_RELEASE.claim.md
# Should show: No such file or directory

# Check claim log
cat Logs/claims.jsonl | grep "claim_released" | tail -1 | jq
```

**Expected Result**:
- ✅ Claim file deleted
- ✅ Event logged: "claim_released"
- ✅ No errors

---

### Test 2.5: Claim Auto-Expiry

**Objective**: Verify claims expire after 15 minutes

**Steps**:
```bash
# Create claim with short TTL for testing
# (Manually edit claim file to set expires_at to past time)
uv run python -m src.services.claim_manager claim \
  --task-id TEST_EXPIRY \
  --zone cloud \
  --action-type test

# Edit claim file
nano Claims/TEST_EXPIRY.claim.md
# Change expires_at to: 2026-03-06T00:00:00 (past time)

# Trigger expiry check
uv run python -m src.services.claim_manager expire

# Verify claim deleted
ls Claims/TEST_EXPIRY.claim.md
# Should show: No such file or directory

# Check claim log
cat Logs/claims.jsonl | grep "claim_expired" | tail -1 | jq
```

**Expected Result**:
- ✅ Expired claims count: 1
- ✅ Claim file deleted
- ✅ Event logged: "claim_expired"

---

### Test 2.6: Work-Zone Routing

**Objective**: Verify routing rules work correctly

**Test Email Routing**:
```bash
# Email reply draft → should route to cloud
uv run python -m src.services.claim_manager route \
  --task-id EMAIL_TEST_001 \
  --action-type reply_draft

# Expected: "Task should be routed to: cloud"
```

**Test WhatsApp Routing**:
```bash
# WhatsApp send → should route to local (secrets required)
uv run python -m src.services.claim_manager route \
  --task-id WHATSAPP_TEST_001 \
  --action-type send_message

# Expected: "Task should be routed to: local"
```

**Test Payment Routing**:
```bash
# Payment execution → should route to local (banking credentials)
uv run python -m src.services.claim_manager route \
  --task-id PAYMENT_TEST_001 \
  --action-type execute

# Expected: "Task should be routed to: local"
```

**Expected Result**:
- ✅ EMAIL_* → cloud (for drafting)
- ✅ WHATSAPP_* → local (secrets)
- ✅ PAYMENT_* → local (banking)

---

### Test 2.7: Task Delegation

**Objective**: Verify Cloud can delegate tasks to Local

**Steps**:
```bash
# Create test task file
mkdir -p Needs_Action
cat > Needs_Action/WHATSAPP_DELEGATE_TEST.md <<EOF
---
task_id: WHATSAPP_DELEGATE_TEST
type: whatsapp_message
status: pending
---

# WhatsApp Message Task

Send message to contact.
EOF

# Delegate from cloud to local
uv run python -m src.services.claim_manager delegate \
  --task-id WHATSAPP_DELEGATE_TEST \
  --reason "whatsapp_session_required"

# Verify file moved
ls Needs_Action/WHATSAPP_DELEGATE_TEST.md
# Should show: No such file or directory

ls Needs_Local/WHATSAPP_DELEGATE_TEST.md
# Should exist

# Check delegation metadata
cat Needs_Local/WHATSAPP_DELEGATE_TEST.md
```

**Expected Result**:
- ✅ File moved from Needs_Action/ to Needs_Local/
- ✅ YAML frontmatter updated with delegation metadata:
  - created_by: cloud
  - requires_zone: local
  - delegated_at: <timestamp>
  - reason: whatsapp_session_required
- ✅ Event logged to claims.jsonl

---

## Test Suite 3: Integration Tests

### Test 3.1: Cloud-Local Workflow

**Objective**: Simulate complete Cloud-Local workflow

**Scenario**: Email arrives → Cloud drafts → Local approves → sends

**Steps (Cloud)**:
```bash
# 1. Email task arrives (simulated)
cat > Needs_Action/EMAIL_WORKFLOW_TEST.md <<EOF
---
task_id: EMAIL_WORKFLOW_TEST
type: email
action: reply_draft
status: pending
---

# Email Reply Task

Reply to: test@example.com
Subject: Test Email
EOF

# 2. Cloud claims task
uv run python -m src.services.claim_manager claim \
  --task-id EMAIL_WORKFLOW_TEST \
  --zone cloud \
  --action-type reply_draft

# 3. Cloud drafts response (simulated)
mkdir -p Cloud_Drafts
cat > Cloud_Drafts/DRAFT_EMAIL_WORKFLOW_TEST.md <<EOF
---
draft_id: DRAFT_EMAIL_WORKFLOW_TEST
original_task: EMAIL_WORKFLOW_TEST
created_by: cloud
created_at: $(date -Iseconds)
status: pending_approval
---

# Email Draft

To: test@example.com
Subject: Re: Test Email

Thank you for your email. Here is the drafted response.

Best regards,
AI Employee
EOF

# 4. Sync to Local
uv run python -m src.services.vault_sync_service sync --direction push --instance cloud

# 5. Release claim
CLAIM_ID=$(cat Claims/EMAIL_WORKFLOW_TEST.claim.md | grep "claim_id:" | awk '{print $2}')
uv run python -m src.services.claim_manager release --claim-id $CLAIM_ID --zone cloud
```

**Steps (Local)**:
```bash
# 6. Pull changes
uv run python -m src.services.vault_sync_service sync --direction pull --instance local

# 7. Verify draft received
ls Cloud_Drafts/DRAFT_EMAIL_WORKFLOW_TEST.md

# 8. Human approves (move to Approved/)
mkdir -p Approved
mv Cloud_Drafts/DRAFT_EMAIL_WORKFLOW_TEST.md Approved/

# 9. Local executes (claim and process)
uv run python -m src.services.claim_manager claim \
  --task-id EMAIL_WORKFLOW_TEST \
  --zone local \
  --action-type send

# 10. Sync execution result
uv run python -m src.services.vault_sync_service sync --direction push --instance local
```

**Expected Result**:
- ✅ Cloud drafted response without sending
- ✅ Draft synced to Local via vault
- ✅ Local processed and "sent" (simulated)
- ✅ All claims logged correctly
- ✅ No secrets leaked to Cloud

---

### Test 3.2: Concurrent Claims (First-to-Sync Wins)

**Objective**: Verify Git conflict detection handles concurrent claims

**Steps (Cloud)**:
```bash
# Cloud claims task
uv run python -m src.services.claim_manager claim \
  --task-id CONCURRENT_TEST \
  --zone cloud \
  --action-type test

# DON'T sync yet
```

**Steps (Local - Simultaneously)**:
```bash
# Local claims same task (before Cloud syncs)
uv run python -m src.services.claim_manager claim \
  --task-id CONCURRENT_TEST \
  --zone local \
  --action-type test

# Sync immediately
uv run python -m src.services.vault_sync_service sync --direction push --instance local
```

**Steps (Cloud - After Local syncs)**:
```bash
# Now Cloud tries to sync
uv run python -m src.services.vault_sync_service sync --direction push --instance cloud

# Check sync status
cat Logs/sync.jsonl | tail -1 | jq '.status'
```

**Expected Result**:
- ✅ Local's claim wins (first to sync)
- ✅ Cloud detects conflict or overwrites based on Git merge
- ✅ Conflict logged if simultaneous push

---

## Test Suite 4: Systemd Integration

### Test 4.1: Vault Sync Timer

**Objective**: Verify vault-sync.timer runs every 5 minutes

**Steps (Cloud VM)**:
```bash
# Start timer
sudo systemctl start vault-sync.timer

# Check next trigger
systemctl list-timers | grep vault-sync

# Wait 6 minutes and check logs
sleep 360
journalctl -u vault-sync.service -n 20 --no-pager

# Check sync count
cat /opt/ai-employee/Logs/sync.jsonl | wc -l
```

**Expected Result**:
- ✅ Timer triggers within 5 minutes
- ✅ Sync executes successfully
- ✅ Next trigger scheduled for +5 minutes

---

### Test 4.2: Claim Expiry Timer

**Objective**: Verify claim-expiry.timer runs every 1 minute

**Steps (Cloud VM)**:
```bash
# Start timer
sudo systemctl start claim-expiry.timer

# Create test claim
uv run python -m src.services.claim_manager claim \
  --task-id TIMER_TEST \
  --zone cloud \
  --action-type test

# Edit claim to expire immediately
sudo nano /opt/ai-employee/Claims/TIMER_TEST.claim.md
# Change expires_at to past time

# Wait 2 minutes for timer to trigger
sleep 120

# Check logs
journalctl -u claim-expiry.service -n 10 --no-pager
```

**Expected Result**:
- ✅ Timer triggers within 1 minute
- ✅ Expired claim detected and removed
- ✅ Next trigger scheduled for +1 minute

---

## Performance Benchmarks

### Benchmark 1: Sync Speed

**Target**: Vault sync completes in <30 seconds with 10 files changed (SC-002)

**Test**:
```bash
# Create 10 files
for i in {1..10}; do
  echo "Benchmark file $i" > bench-$i.md
done

# Measure sync time
time uv run python -m src.services.vault_sync_service sync --direction push --instance local

# Check duration from log
cat Logs/sync.jsonl | tail -1 | jq '.duration_ms'
```

**Expected**: Duration < 30000 ms (30 seconds)

---

### Benchmark 2: Claim Creation Speed

**Target**: Claim creation < 100ms

**Test**:
```bash
# Measure claim creation time
time uv run python -m src.services.claim_manager claim \
  --task-id PERF_TEST \
  --zone cloud \
  --action-type test
```

**Expected**: Real time < 0.1s

---

## Security Tests

### Security Test 1: Secret Leak Prevention

**Objective**: Verify pre-commit hook blocks secrets

**Test**:
```bash
# Create file with secret
echo "AWS_SECRET_KEY=abcd1234efgh5678" > credentials.secret

# Try to commit
git add credentials.secret
git commit -m "test: intentional secret"
```

**Expected**:
- ✅ Pre-commit hook detects secret
- ✅ Commit blocked
- ✅ Error message shows file location

---

### Security Test 2: Cloud Cannot Access Local Secrets

**Objective**: Verify Cloud instance doesn't have WhatsApp/banking credentials

**Test (Cloud VM)**:
```bash
# Check for WhatsApp session
ls -la /opt/ai-employee/whatsapp_session/
# Should show: No such file or directory

# Check for banking credentials
cat /opt/ai-employee/.env.cloud | grep BANKING
# Should show: nothing

# Check for local .env
cat /opt/ai-employee/.env
# Should show: No such file or directory (or fail to open)
```

**Expected**:
- ✅ No WhatsApp session files on Cloud
- ✅ No banking credentials on Cloud
- ✅ `.env.cloud` does NOT have local-only secrets

---

## Test Report Template

After running all tests, fill out this report:

### Test Execution Summary

**Date**: ___________
**Tester**: ___________
**Environment**: Local + Cloud VM

| Test Suite | Tests Passed | Tests Failed | Notes |
|------------|-------------|--------------|-------|
| VaultSyncService | __/6 | __/6 | |
| ClaimManager | __/7 | __/7 | |
| Integration | __/2 | __/2 | |
| Systemd | __/2 | __/2 | |
| Performance | __/2 | __/2 | |
| Security | __/2 | __/2 | |
| **TOTAL** | __/21 | __/21 | |

### Issues Found

1. **Issue**: ___________
   - **Severity**: Critical / High / Medium / Low
   - **Component**: ___________
   - **Reproduce**: ___________

### Performance Metrics

- Average sync duration (10 files): _____ ms
- Average claim creation time: _____ ms
- Vault sync success rate: _____%
- Claim expiry accuracy: _____%

### Recommendations

- [ ] Ready for production deployment
- [ ] Needs additional testing in: ___________
- [ ] Known issues acceptable for Phase 1
- [ ] Critical issues must be fixed before deployment

---

**Testing Guide Version**: 1.0.0
**Last Updated**: 2026-03-06
