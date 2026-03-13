# Claim Manager API Contract

**Feature**: 004-platinum-tier-upgrade
**Component**: Claim Management Service (Work-Zone Delegation)
**Version**: 1.0.0

## Overview

Defines the internal API contract for task claim management enabling Cloud-Local work-zone specialization and delegation.

**Implementation**: Python service (`src/services/claim_manager.py`)
**Protocol**: File-based advisory locks

---

## ClaimManager

### `claim_task(task_id: str, zone: str) -> Claim`

Claims ownership of a task for the specified work zone.

**Parameters**:
- `task_id` (str): Task identifier (e.g., `"EMAIL_20260304_152150"`)
- `zone` (str): Work zone claiming the task - `"cloud"` or `"local"`

**Returns**: `Claim` object

**Behavior**:
1. Checks if task already claimed (not expired)
2. If claimed by other zone: raises `TaskAlreadyClaimedError`
3. If claimed by same zone: returns existing claim
4. If unclaimed or expired: creates new claim file in `/Claims/`
5. Sets TTL to 15 minutes from now
6. Returns `Claim` object

**Errors**:
- `TaskAlreadyClaimedError`: Task claimed by other zone
- `TaskNotFoundError`: Task file doesn't exist
- `InvalidZoneError`: Zone is not "cloud" or "local"

**Example**:
```python
claim_manager = ClaimManager(vault_path="/path/to/vault")
try:
    claim = claim_manager.claim_task(
        task_id="EMAIL_20260304_152150",
        zone="cloud"
    )
    print(f"Claimed task, expires at {claim.expires_at}")
except TaskAlreadyClaimedError as e:
    print(f"Task already claimed by {e.claimed_by}")
```

---

### `release_claim(claim_id: str, zone: str) -> None`

Releases a task claim when processing is complete.

**Parameters**:
- `claim_id` (str): Claim identifier (e.g., `"CLAIM_20260304_153100"`)
- `zone` (str): Work zone releasing the claim - must match claim owner

**Behavior**:
1. Loads claim file from `/Claims/`
2. Verifies `zone` matches `claim.claimed_by`
3. Updates claim status to `"released"`
4. Deletes claim file (released claims not persisted)

**Errors**:
- `ClaimNotFoundError`: Invalid claim ID
- `UnauthorizedReleaseError`: Zone doesn't own the claim

**Example**:
```python
claim_manager.release_claim(
    claim_id="CLAIM_20260304_153100",
    zone="cloud"
)
```

---

### `check_claim(task_id: str) -> Optional[Claim]`

Checks if a task is currently claimed.

**Parameters**:
- `task_id` (str): Task identifier

**Returns**: `Claim` object if claimed, `None` if unclaimed or expired

**Behavior**:
1. Looks for claim file in `/Claims/{task_id}.claim.md`
2. If found: checks expiry
3. If expired: auto-expires claim and returns `None`
4. If active: returns `Claim` object

**Example**:
```python
claim = claim_manager.check_claim(task_id="EMAIL_20260304_152150")
if claim:
    print(f"Task claimed by {claim.claimed_by} until {claim.expires_at}")
else:
    print("Task unclaimed, safe to process")
```

---

### `auto_expire_claims() -> int`

Background task to expire stale claims (TTL exceeded).

**Returns**: Number of claims expired

**Behavior**:
1. Scans all claim files in `/Claims/`
2. For each claim: checks if `expires_at < now()`
3. If expired: updates status to `"expired"`, deletes file
4. Returns count of expired claims

**Scheduled**: Every 1 minute via systemd timer

**Example**:
```python
expired_count = claim_manager.auto_expire_claims()
print(f"Expired {expired_count} stale claims")
```

---

### `route_task(task_id: str, task_file: str, action_type: str) -> str`

Determines which work zone should process a task based on routing rules.

**Parameters**:
- `task_id` (str): Task identifier
- `task_file` (str): Path to task file in vault
- `action_type` (str): Type of action (e.g., `"email_reply"`, `"whatsapp_send"`)

**Returns**: Work zone - `"cloud"`, `"local"`, or `"any"`

**Behavior**:
1. Loads routing rules from `Company_Handbook.md`
2. Checks if action requires secrets (WhatsApp, banking)
3. If secrets required: returns `"local"`
4. If triage/draft action: returns `"cloud"`
5. Otherwise: returns `"any"` (either zone can process)

**Example**:
```python
zone = claim_manager.route_task(
    task_id="EMAIL_20260304_152150",
    task_file="Needs_Action/EMAIL_20260304_152150.md",
    action_type="email_reply"
)
# Returns: "cloud" (email triage is cloud capability)
```

---

### `delegate_to_local(task_id: str, reason: str) -> None`

Delegates a task from Cloud to Local zone (requires local-only capabilities).

**Parameters**:
- `task_id` (str): Task identifier
- `reason` (str): Reason for delegation (e.g., `"whatsapp_send_required"`)

**Behavior**:
1. Moves task file from `/Needs_Action/` to `/Needs_Local/`
2. Updates task YAML frontmatter with delegation metadata:
   ```yaml
   delegation:
     created_by: cloud
     requires_zone: local
     delegated_at: 2026-03-04T15:40:00Z
     reason: whatsapp_send_required
   ```
3. Logs delegation event

**Example**:
```python
claim_manager.delegate_to_local(
    task_id="WHATSAPP_20260304_160000",
    reason="whatsapp_session_required"
)
# Task moved to /Needs_Local/ for local processing
```

---

## Data Structures

### Claim

```python
@dataclass
class Claim:
    claim_id: str
    task_id: str
    task_file: str
    claimed_by: str  # "cloud" or "local"
    claimed_at: datetime
    expires_at: datetime  # claimed_at + 15 minutes
    zone: str
    action_type: str
    status: str  # "active", "released", "expired", "violated"
    released_at: Optional[datetime]
    released_by: Optional[str]
```

### RoutingRule

```python
@dataclass
class RoutingRule:
    pattern: str  # e.g., "EMAIL_*", "WHATSAPP_*"
    action: str   # e.g., "reply_draft", "send_message"
    zone: str     # "cloud", "local", "any"
    requires_approval: bool
```

---

## Configuration

**Work Zone Configuration** (`Company_Handbook.md`):
```yaml
work_zones:
  cloud:
    enabled: true
    capabilities:
      - email_triage
      - draft_responses
      - schedule_monitoring
    restrictions:
      - no_whatsapp_access
      - no_banking_credentials

  local:
    enabled: true
    capabilities:
      - approve_cloud_drafts
      - whatsapp_send
      - banking_transactions
    exclusive_secrets:
      - whatsapp_session
      - banking_credentials

routing_rules:
  - pattern: "EMAIL_*"
    action: "reply_draft"
    zone: "cloud"
    requires_approval: true

  - pattern: "WHATSAPP_*"
    action: "send_message"
    zone: "local"
    requires_approval: false
```

**Environment Variables**:
```bash
VAULT_PATH=/path/to/vault
CLAIM_TTL_MINUTES=15
CLAIM_EXPIRE_INTERVAL_SECONDS=60
```

---

## Claim Lifecycle

```
┌─────────────────────────────────────────────────┐
│ 1. Task arrives in /Needs_Action/              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. route_task() determines zone (cloud/local)  │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   zone=cloud        zone=local
        │                 │
        ▼                 ▼
┌─────────────┐   ┌──────────────┐
│ 3. Cloud    │   │ 3. Delegate  │
│ claim_task()│   │ to /Needs_   │
│             │   │ Local/       │
└──────┬──────┘   └──────┬───────┘
       │                 │
       ▼                 ▼
┌─────────────┐   ┌──────────────┐
│ 4. Process  │   │ 4. Local     │
│ (draft/     │   │ claim_task() │
│ triage)     │   │              │
└──────┬──────┘   └──────┬───────┘
       │                 │
       ▼                 ▼
┌─────────────┐   ┌──────────────┐
│ 5. release_ │   │ 5. Process   │
│ claim()     │   │ (execute)    │
└─────────────┘   └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ 6. release_  │
                  │ claim()      │
                  └──────────────┘
```

---

## Claim Conflict Resolution

### Scenario: Cloud and Local both claim same task

**Problem**: Sync conflict causes both instances to see task as unclaimed

**Solution**: First-to-sync wins (Git conflict detection)

**Flow**:
```
1. Cloud creates: Claims/EMAIL_001.claim.md (claimed_by=cloud)
2. Local creates: Claims/EMAIL_001.claim.md (claimed_by=local)
3. Both sync to Git
4. Git detects conflict (same file, different content)
5. Sync service creates SyncConflict entity
6. Resolution strategy: earliest timestamp wins
   - If cloud.claimed_at < local.claimed_at: Keep cloud claim
   - Else: Keep local claim
7. Losing instance backs off, releases claim
```

**Violation Detection**:
- If task is processed despite claim conflict → `status="violated"`
- Logged in audit trail for manual review

---

## Error Handling

### Task Already Claimed

**Scenario**: Cloud tries to claim task already claimed by Local

**Behavior**:
```python
try:
    claim = claim_manager.claim_task(task_id="EMAIL_001", zone="cloud")
except TaskAlreadyClaimedError as e:
    print(f"Task claimed by {e.claimed_by}, expires {e.expires_at}")
    # Wait or skip task
```

### Expired Claim

**Scenario**: Claim TTL exceeded (15 minutes)

**Behavior**:
1. `check_claim()` detects expiry
2. Auto-updates claim status to `"expired"`
3. Deletes claim file
4. Task becomes unclaimed (can be re-claimed)

### Stale Claims Cleanup

**Scenario**: Claims left behind by crashed processes

**Behavior**:
- `auto_expire_claims()` runs every 1 minute
- Expires all claims with `expires_at < now()`
- Prevents permanent locks on tasks

---

## Testing

### Unit Tests
```python
def test_claim_task_success():
    claim = claim_manager.claim_task(task_id="EMAIL_001", zone="cloud")
    assert claim.claimed_by == "cloud"
    assert claim.status == "active"

def test_claim_already_claimed():
    claim_manager.claim_task(task_id="EMAIL_001", zone="cloud")
    with pytest.raises(TaskAlreadyClaimedError):
        claim_manager.claim_task(task_id="EMAIL_001", zone="local")

def test_claim_expiry():
    claim = claim_manager.claim_task(task_id="EMAIL_001", zone="cloud")
    # Fast-forward time 16 minutes
    with freeze_time(claim.claimed_at + timedelta(minutes=16)):
        assert claim_manager.check_claim("EMAIL_001") is None

def test_route_task():
    zone = claim_manager.route_task(
        task_id="WHATSAPP_001",
        task_file="Needs_Action/WHATSAPP_001.md",
        action_type="whatsapp_send"
    )
    assert zone == "local"  # WhatsApp requires local zone
```

### Integration Tests
- Claim file creation/deletion
- Routing rules from Company_Handbook
- Delegation to /Needs_Local/
- Expiry cleanup process

---

## Performance

**Claim Operation**: <10ms (file write)
**Check Claim**: <5ms (file read)
**Route Task**: <5ms (rule matching)
**Auto-Expire (100 claims)**: <50ms

---

*Contract complete. Ready for implementation in `/sp.tasks`.*
