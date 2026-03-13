# Vault Sync API Contract

**Feature**: 004-platinum-tier-upgrade
**Component**: Vault Synchronization Service
**Version**: 1.0.0

## Overview

Defines the internal API contract for vault synchronization between Cloud and Local instances using Git with secret filtering.

**Implementation**: Python service (`src/services/vault_sync_service.py`)
**Protocol**: File-based (Git commands), no network API

---

## VaultSyncService

### `sync(direction: str) -> SyncResult`

Performs vault synchronization in the specified direction.

**Parameters**:
- `direction` (str): Sync direction - `"pull"`, `"push"`, or `"bidirectional"`

**Returns**: `SyncResult` object

**Behavior**:
1. If `direction="pull"`: Git pull from remote
2. If `direction="push"`: Filter secrets, git add, commit, push
3. If `direction="bidirectional"`: Pull first, then push

**Secret Filtering** (push only):
- Runs `detect-secrets` scan before commit
- Blocks commit if secrets detected
- Logs filtered files to `sync.jsonl`

**Conflict Handling**:
- If merge conflict detected: Creates `SyncConflict` entity, returns `status="conflict"`
- Preserves both versions: `file.md` (local), `file-cloud.md` (cloud)

**Errors**:
- `GitConflictError`: Merge conflict detected
- `SecretDetectedError`: Secret found in staged files
- `NetworkError`: Cannot reach remote

**Example**:
```python
sync_service = VaultSyncService(vault_path="/path/to/vault")
result = sync_service.sync(direction="bidirectional")

if result.status == "success":
    print(f"Synced {result.files_changed} files")
elif result.status == "conflict":
    print(f"Conflict in {result.conflicts[0].file_path}")
```

---

### `filter_secrets() -> List[str]`

Scans staged files for secrets before commit.

**Returns**: List of file paths containing secrets

**Behavior**:
- Runs `detect-secrets` on staged files
- Checks patterns from `.gitignore`
- Returns list of files to exclude

**Example**:
```python
secret_files = sync_service.filter_secrets()
# [".env", "whatsapp_session/qr.png"]
```

---

### `resolve_conflict(conflict_id: str, strategy: str) -> None`

Manually resolves a sync conflict.

**Parameters**:
- `conflict_id` (str): Conflict ID from `sync_conflicts.jsonl`
- `strategy` (str): Resolution strategy - `"keep_local"`, `"keep_cloud"`, `"keep_both"`, `"manual_merge"`

**Behavior**:
- Applies resolution strategy to conflicting files
- Updates `SyncConflict` entity with resolution
- Commits resolution to Git

**Errors**:
- `ConflictNotFoundError`: Invalid conflict ID
- `InvalidStrategyError`: Unknown resolution strategy

**Example**:
```python
sync_service.resolve_conflict(
    conflict_id="CONFLICT_20260304_153045",
    strategy="keep_local"
)
```

---

## Data Structures

### SyncResult

```python
@dataclass
class SyncResult:
    sync_id: str
    timestamp: datetime
    direction: str
    status: str  # "success", "conflict", "failed"
    files_changed: int
    files_added: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    secrets_filtered: int
    secrets_blocked: List[str]
    conflicts_detected: int
    conflicts: List[SyncConflict]
    duration_ms: int
    git_commit: Optional[str]
    error: Optional[str]
```

### SyncConflict

```python
@dataclass
class SyncConflict:
    conflict_id: str
    sync_id: str
    timestamp: datetime
    file_path: str
    conflict_type: str  # "simultaneous_edit", "delete_modify", "rename_rename"
    local_version: str
    cloud_version: str
    local_modified: datetime
    cloud_modified: datetime
    resolved: bool
    resolution_strategy: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]  # "cloud" or "local"
```

---

## Configuration

**Environment Variables**:
```bash
VAULT_PATH=/path/to/vault
GIT_REMOTE_URL=https://github.com/user/vault.git
GIT_BRANCH=main
SYNC_INTERVAL_SECONDS=300  # 5 minutes
SECRET_DETECTION_ENABLED=true
```

**Git Configuration** (auto-applied):
```bash
git config user.name "AI Employee Cloud"
git config user.email "cloud@aiemployee.local"
git config pull.rebase true
git config core.autocrlf false
```

---

## Systemd Timer Integration

**Service**: `vault-sync.service`
**Timer**: `vault-sync.timer`

**Timer Configuration**:
```ini
[Unit]
Description=Vault Sync Timer (every 5 minutes)

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
AccuracySec=10s

[Install]
WantedBy=timers.target
```

**Service Configuration**:
```ini
[Unit]
Description=Vault Sync Service
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -m src.services.vault_sync_service sync --direction bidirectional
WorkingDirectory=/opt/ai-employee
Environment="VAULT_PATH=/opt/ai-employee/vault"
User=aiemployee

[Install]
WantedBy=multi-user.target
```

---

## Error Handling

### Secret Detection Failure

**Scenario**: `.env` file accidentally staged for commit

**Behavior**:
1. `filter_secrets()` detects `.env` in staged files
2. Raises `SecretDetectedError`
3. Unstages `.env` automatically
4. Logs to `sync.jsonl` with `secrets_blocked=[".env"]`
5. Continues with non-secret files

**Log Entry**:
```json
{
  "sync_id": "SYNC_20260304_154000",
  "status": "completed",
  "secrets_filtered": 1,
  "secrets_blocked": [".env"],
  "error": "Secret detected in .env, file excluded from sync"
}
```

### Merge Conflict

**Scenario**: Cloud and Local both modified `Dashboard.md`

**Behavior**:
1. `sync(direction="pull")` detects merge conflict
2. Creates `SyncConflict` entity in `sync_conflicts.jsonl`
3. Preserves both versions:
   - `Dashboard.md` (local version)
   - `Dashboard-cloud.md` (cloud version)
4. Returns `SyncResult` with `status="conflict"`
5. Waits for manual resolution via `resolve_conflict()`

**Conflict Entry**:
```json
{
  "conflict_id": "CONFLICT_20260304_154030",
  "file_path": "Dashboard.md",
  "conflict_type": "simultaneous_edit",
  "resolved": false
}
```

### Network Failure

**Scenario**: Cloud VM loses internet connectivity

**Behavior**:
1. `sync(direction="pull")` fails with `NetworkError`
2. Logs error to `sync.jsonl`
3. Queues changes locally
4. Retries on next timer interval (5 minutes)
5. Success on reconnect triggers full sync

---

## Security Guarantees

1. **Secrets Never Sync**: Pre-commit hook blocks any commit containing secrets
2. **Encryption at Rest**: Cloud VM uses disk encryption (LUKS)
3. **SSH Authentication**: Git push/pull uses SSH keys (no passwords)
4. **Atomic Commits**: Git ensures atomic operations (no partial syncs)
5. **Audit Trail**: Every sync logged with files changed, duration, errors

---

## Performance Characteristics

**Typical Sync (10 files changed)**:
- Duration: 1-3 seconds
- Network: ~50 KB (compressed text)
- CPU: Minimal (<5% for 1s)

**Large Sync (100+ files changed)**:
- Duration: 5-10 seconds
- Network: ~500 KB
- CPU: <10% for 5-10s

**Secret Scan Overhead**:
- Duration: +0.5-1s per sync
- Negligible CPU impact

---

## Testing

### Unit Tests
```python
def test_sync_success():
    result = sync_service.sync(direction="bidirectional")
    assert result.status == "success"
    assert result.files_changed >= 0

def test_secret_filtering():
    # Stage .env file
    secret_files = sync_service.filter_secrets()
    assert ".env" in secret_files

def test_conflict_resolution():
    sync_service.resolve_conflict(
        conflict_id="test_conflict",
        strategy="keep_local"
    )
    conflict = get_conflict("test_conflict")
    assert conflict.resolved == True
```

### Integration Tests
- Real Git repository sync
- Secret detection with actual `.env` file
- Conflict resolution workflow
- Network failure handling

---

## Migration Notes

**From Gold Tier**:
- Gold Tier has no vault sync (local-only)
- Platinum Tier introduces Git-based sync
- No data migration needed (Git starts fresh)

**Initial Setup**:
```bash
cd vault/
git init
git add .
git commit -m "Initial vault commit"
git remote add origin <remote-url>
git push -u origin main
```

---

*Contract complete. Ready for implementation in `/sp.tasks`.*
