"""
VaultSyncService for Personal AI Employee - Platinum Tier

Handles Git-based vault synchronization between Cloud and Local instances with secret filtering.

Core functionality:
- Bidirectional Git sync (pull, push, bidirectional)
- Secret detection and filtering using detect-secrets
- Conflict detection and resolution
- Sync event logging

Constitutional Compliance:
- Local-First Privacy (Principle I): Secrets never sync to cloud
- Security & Credential Management (Principle III): All sync events logged
"""

import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging


@dataclass
class SyncResult:
    """Result of a vault synchronization operation."""

    sync_id: str
    direction: str  # "pull", "push", "bidirectional"
    status: str  # "success", "conflict", "error"
    files_changed: int
    secrets_filtered: int
    secrets_blocked: List[str] = field(default_factory=list)
    conflicts_detected: int = 0
    conflict_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: int = 0


@dataclass
class SyncConflict:
    """Represents a Git merge conflict."""

    conflict_id: str
    file_path: str
    conflict_type: str  # "content", "both_modified", "deleted_by_one"
    local_version: Optional[str] = None
    cloud_version: Optional[str] = None
    resolved: bool = False
    resolution_strategy: Optional[str] = None  # "keep_local", "keep_cloud", "keep_both", "manual_merge"
    resolved_at: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


class VaultSyncService:
    """Service for Git-based vault synchronization with secret filtering."""

    def __init__(self, vault_path: str | Path, instance: str = "local", remote: str = "origin"):
        """
        Initialize VaultSyncService.

        Args:
            vault_path: Path to vault root (should be a Git repository)
            instance: Instance identifier ("cloud" or "local")
            remote: Git remote name (default: "origin")
        """
        self.vault_path = Path(vault_path).resolve()
        self.instance = instance
        self.remote = remote
        self.logger = logging.getLogger(f"vault_sync.{instance}")

        # Validate vault path
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")

        # Validate Git repository
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Vault path is not a Git repository: {self.vault_path}")

        # Ensure log directories exist
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.sync_log_path = self.logs_dir / "sync.jsonl"
        self.conflicts_log_path = self.logs_dir / "sync_conflicts.jsonl"

        self.logger.info(f"VaultSyncService initialized: vault={self.vault_path}, instance={self.instance}")

    def filter_secrets(self) -> List[str]:
        """
        Scan staged files for secrets using detect-secrets.

        Returns:
            List of file paths containing secrets

        Raises:
            RuntimeError: If detect-secrets execution fails
        """
        try:
            # Get list of staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )

            staged_files = [f for f in result.stdout.strip().split("\n") if f]

            if not staged_files:
                self.logger.debug("No staged files to scan for secrets")
                return []

            # Scan staged files with detect-secrets
            secrets_found = []

            for file_path in staged_files:
                full_path = self.vault_path / file_path

                # Skip if file doesn't exist (deleted files)
                if not full_path.exists():
                    continue

                # Run detect-secrets on the file
                try:
                    detect_result = subprocess.run(
                        ["detect-secrets", "scan", "--baseline", ".secrets.baseline", str(full_path)],
                        cwd=self.vault_path,
                        capture_output=True,
                        text=True
                    )

                    # If detect-secrets found secrets (exit code 1), add to list
                    if "True" in detect_result.stdout or detect_result.returncode == 1:
                        secrets_found.append(file_path)
                        self.logger.warning(f"Secret detected in staged file: {file_path}")

                        # Unstage the file
                        subprocess.run(
                            ["git", "reset", "HEAD", file_path],
                            cwd=self.vault_path,
                            capture_output=True,
                            check=True
                        )
                        self.logger.info(f"Unstaged file with secrets: {file_path}")

                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Error scanning {file_path} for secrets: {e}")
                    # Don't raise, continue scanning other files

            return secrets_found

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to filter secrets: {e.stderr}")

    def sync(self, direction: str = "bidirectional") -> SyncResult:
        """
        Perform vault synchronization.

        Args:
            direction: Sync direction ("pull", "push", "bidirectional")

        Returns:
            SyncResult object with sync status and metrics
        """
        start_time = datetime.now()
        sync_id = f"SYNC_{self.instance.upper()}_{start_time.strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(f"Starting sync: {sync_id}, direction={direction}")

        try:
            files_changed = 0
            secrets_blocked = []
            conflicts = []

            # Bidirectional: pull first, then push
            if direction == "bidirectional":
                # Pull from remote
                pull_result = self._git_pull()
                files_changed += pull_result["files_changed"]
                conflicts.extend(pull_result["conflicts"])

                # Push to remote (with secret filtering)
                push_result = self._git_push()
                files_changed += push_result["files_changed"]
                secrets_blocked = push_result["secrets_blocked"]

            elif direction == "pull":
                pull_result = self._git_pull()
                files_changed = pull_result["files_changed"]
                conflicts.extend(pull_result["conflicts"])

            elif direction == "push":
                push_result = self._git_push()
                files_changed = push_result["files_changed"]
                secrets_blocked = push_result["secrets_blocked"]

            else:
                raise ValueError(f"Invalid sync direction: {direction}")

            # Determine status
            status = "success" if not conflicts else "conflict"

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create result
            result = SyncResult(
                sync_id=sync_id,
                direction=direction,
                status=status,
                files_changed=files_changed,
                secrets_filtered=len(secrets_blocked),
                secrets_blocked=secrets_blocked,
                conflicts_detected=len(conflicts),
                conflict_files=[c["file"] for c in conflicts],
                duration_ms=duration_ms
            )

            # Log sync event
            self._log_sync_event(result)

            # Log conflicts if any
            for conflict in conflicts:
                self._log_conflict(conflict)

            self.logger.info(f"Sync completed: {sync_id}, status={status}, files={files_changed}")

            return result

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            result = SyncResult(
                sync_id=sync_id,
                direction=direction,
                status="error",
                files_changed=0,
                secrets_filtered=0,
                error_message=str(e),
                duration_ms=duration_ms
            )

            self._log_sync_event(result)

            self.logger.error(f"Sync failed: {sync_id}, error={str(e)}")
            raise

    def _git_pull(self) -> Dict[str, Any]:
        """
        Pull changes from remote repository.

        Returns:
            Dict with files_changed and conflicts
        """
        try:
            # Fetch from remote
            subprocess.run(
                ["git", "fetch", self.remote],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()

            # Count files that will change
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", f"HEAD..{self.remote}/{current_branch}"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )
            files_before = len([f for f in diff_result.stdout.strip().split("\n") if f])

            # Attempt merge
            merge_result = subprocess.run(
                ["git", "merge", f"{self.remote}/{current_branch}"],
                cwd=self.vault_path,
                capture_output=True,
                text=True
            )

            # Check for conflicts
            if merge_result.returncode != 0:
                conflicts = self._detect_conflicts()
                return {
                    "files_changed": files_before,
                    "conflicts": conflicts
                }

            return {
                "files_changed": files_before,
                "conflicts": []
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git pull failed: {e.stderr}")

    def _git_push(self) -> Dict[str, Any]:
        """
        Push changes to remote repository with secret filtering.

        Returns:
            Dict with files_changed and secrets_blocked
        """
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()

            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )

            uncommitted_files = [line[3:] for line in status_result.stdout.strip().split("\n") if line]

            if uncommitted_files:
                # Stage all changes
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.vault_path,
                    capture_output=True,
                    check=True
                )

                # Filter secrets
                secrets_blocked = self.filter_secrets()

                # Get remaining staged files
                staged_result = subprocess.run(
                    ["git", "diff", "--cached", "--name-only"],
                    cwd=self.vault_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                staged_files = [f for f in staged_result.stdout.strip().split("\n") if f]

                if staged_files:
                    # Commit changes
                    commit_message = f"[{self.instance}] Auto-sync at {datetime.now().isoformat()}"
                    subprocess.run(
                        ["git", "commit", "-m", commit_message],
                        cwd=self.vault_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )

                    files_changed = len(staged_files)
                else:
                    # All files filtered out as secrets
                    files_changed = 0

                    # Reset if nothing to commit
                    subprocess.run(
                        ["git", "reset", "HEAD"],
                        cwd=self.vault_path,
                        capture_output=True,
                        check=True
                    )
            else:
                secrets_blocked = []
                files_changed = 0

            # Push to remote
            if files_changed > 0:
                subprocess.run(
                    ["git", "push", self.remote, current_branch],
                    cwd=self.vault_path,
                    capture_output=True,
                    text=True,
                    check=True
                )

            return {
                "files_changed": files_changed,
                "secrets_blocked": secrets_blocked
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git push failed: {e.stderr}")

    def _detect_conflicts(self) -> List[Dict[str, str]]:
        """
        Detect Git merge conflicts.

        Returns:
            List of conflict dictionaries
        """
        try:
            # Get list of conflicted files
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=True
            )

            conflicted_files = [f for f in result.stdout.strip().split("\n") if f]

            conflicts = []
            for file_path in conflicted_files:
                conflict_id = f"CONFLICT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(conflicts)}"
                conflicts.append({
                    "conflict_id": conflict_id,
                    "file": file_path,
                    "type": "both_modified"
                })

            return conflicts

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to detect conflicts: {e}")
            return []

    def resolve_conflict(self, conflict_id: str, strategy: str) -> None:
        """
        Resolve a Git merge conflict.

        Args:
            conflict_id: Conflict identifier
            strategy: Resolution strategy ("keep_local", "keep_cloud", "keep_both", "manual_merge")

        Raises:
            ValueError: If strategy is invalid
            RuntimeError: If conflict resolution fails
        """
        # Load conflict from log
        conflict = self._load_conflict(conflict_id)

        if not conflict:
            raise ValueError(f"Conflict not found: {conflict_id}")

        if conflict.resolved:
            self.logger.warning(f"Conflict already resolved: {conflict_id}")
            return

        file_path = self.vault_path / conflict.file_path

        try:
            if strategy == "keep_local":
                # Use --ours (local version)
                subprocess.run(
                    ["git", "checkout", "--ours", conflict.file_path],
                    cwd=self.vault_path,
                    capture_output=True,
                    check=True
                )

            elif strategy == "keep_cloud":
                # Use --theirs (remote version)
                subprocess.run(
                    ["git", "checkout", "--theirs", conflict.file_path],
                    cwd=self.vault_path,
                    capture_output=True,
                    check=True
                )

            elif strategy == "keep_both":
                # Keep conflict markers for manual review
                self.logger.info(f"Keeping both versions for manual merge: {conflict.file_path}")
                # File remains with conflict markers

            elif strategy == "manual_merge":
                self.logger.info(f"Manual merge required: {conflict.file_path}")
                # User must edit file manually
                return

            else:
                raise ValueError(f"Invalid resolution strategy: {strategy}")

            # Stage resolved file
            subprocess.run(
                ["git", "add", conflict.file_path],
                cwd=self.vault_path,
                capture_output=True,
                check=True
            )

            # Update conflict status
            conflict.resolved = True
            conflict.resolution_strategy = strategy
            conflict.resolved_at = datetime.now().isoformat()

            self._log_conflict(asdict(conflict))

            self.logger.info(f"Conflict resolved: {conflict_id}, strategy={strategy}")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to resolve conflict: {e.stderr}")

    def _log_sync_event(self, result: SyncResult) -> None:
        """Log sync event to sync.jsonl."""
        try:
            with open(self.sync_log_path, "a") as f:
                json.dump(asdict(result), f)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to log sync event: {e}")

    def _log_conflict(self, conflict: Dict[str, Any]) -> None:
        """Log conflict to sync_conflicts.jsonl."""
        try:
            with open(self.conflicts_log_path, "a") as f:
                json.dump(conflict, f)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to log conflict: {e}")

    def _load_conflict(self, conflict_id: str) -> Optional[SyncConflict]:
        """Load conflict from sync_conflicts.jsonl."""
        try:
            if not self.conflicts_log_path.exists():
                return None

            with open(self.conflicts_log_path, "r") as f:
                for line in f:
                    conflict_data = json.loads(line)
                    if conflict_data.get("conflict_id") == conflict_id:
                        return SyncConflict(**conflict_data)

            return None
        except Exception as e:
            self.logger.error(f"Failed to load conflict: {e}")
            return None


# CLI Interface for manual sync operations
if __name__ == "__main__":
    import argparse
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Vault Sync Service - Git-based vault synchronization")
    parser.add_argument(
        "command",
        choices=["sync", "resolve"],
        help="Command to execute"
    )
    parser.add_argument(
        "--direction",
        choices=["pull", "push", "bidirectional"],
        default="bidirectional",
        help="Sync direction (default: bidirectional)"
    )
    parser.add_argument(
        "--vault-path",
        default=".",
        help="Path to vault directory (default: current directory)"
    )
    parser.add_argument(
        "--instance",
        default="local",
        help="Instance identifier (cloud or local, default: local)"
    )
    parser.add_argument(
        "--conflict-id",
        help="Conflict ID for resolve command"
    )
    parser.add_argument(
        "--strategy",
        choices=["keep_local", "keep_cloud", "keep_both", "manual_merge"],
        help="Conflict resolution strategy"
    )

    args = parser.parse_args()

    # Initialize service
    try:
        service = VaultSyncService(
            vault_path=args.vault_path,
            instance=args.instance
        )

        if args.command == "sync":
            result = service.sync(direction=args.direction)
            print(f"\nSync completed: {result.sync_id}")
            print(f"  Status: {result.status}")
            print(f"  Files changed: {result.files_changed}")
            print(f"  Secrets filtered: {result.secrets_filtered}")
            print(f"  Conflicts detected: {result.conflicts_detected}")
            print(f"  Duration: {result.duration_ms}ms")

            if result.secrets_blocked:
                print(f"\n  Secrets blocked:")
                for secret_file in result.secrets_blocked:
                    print(f"    - {secret_file}")

            if result.conflict_files:
                print(f"\n  Conflict files:")
                for conflict_file in result.conflict_files:
                    print(f"    - {conflict_file}")

            sys.exit(0 if result.status == "success" else 1)

        elif args.command == "resolve":
            if not args.conflict_id:
                print("Error: --conflict-id required for resolve command")
                sys.exit(1)
            if not args.strategy:
                print("Error: --strategy required for resolve command")
                sys.exit(1)

            service.resolve_conflict(args.conflict_id, args.strategy)
            print(f"\nConflict resolved: {args.conflict_id}")
            print(f"  Strategy: {args.strategy}")
            sys.exit(0)

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)
