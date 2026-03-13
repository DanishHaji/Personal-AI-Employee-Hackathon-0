"""
Sync Queue Item Model - Platinum Tier US4

Represents a queued change waiting for sync when offline/network unavailable.

Part of Phase 8: Offline Resilience
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum


class QueueItemStatus(str, Enum):
    """Status of queued sync item."""
    PENDING = "pending"  # Waiting to be synced
    SYNCING = "syncing"  # Currently being synced
    COMPLETED = "completed"  # Successfully synced
    FAILED = "failed"  # Sync failed (will retry)
    ABANDONED = "abandoned"  # Too many failures, manual intervention needed


class QueueItemType(str, Enum):
    """Type of queued change."""
    FILE_CHANGE = "file_change"  # Modified/created/deleted file
    GIT_COMMIT = "git_commit"  # Committed changes ready to push
    CLAIM_DELEGATION = "claim_delegation"  # Claim delegated to other instance
    APPROVAL_ACTION = "approval_action"  # Approval decision made


@dataclass
class SyncQueueItem:
    """
    Represents a queued change waiting to be synced.

    When network is unavailable or sync fails, changes are queued locally
    and automatically retried when connection is restored.

    Storage: vault/Sync_Queue/{queue_id}.json
    """

    queue_id: str  # Unique identifier (QUEUE_{timestamp}_{seq})
    item_type: QueueItemType  # Type of queued change
    instance: str  # "cloud" or "local" - where item was created
    created_at: str  # ISO 8601 timestamp

    # File information
    file_paths: List[str] = field(default_factory=list)  # Files affected
    change_type: Optional[str] = None  # "modified", "created", "deleted"

    # Git information
    commit_hash: Optional[str] = None  # Git commit hash if applicable
    commit_message: Optional[str] = None  # Commit message

    # Queue management
    status: QueueItemStatus = QueueItemStatus.PENDING
    retry_count: int = 0
    max_retries: int = 10
    last_attempt: Optional[str] = None  # ISO 8601 timestamp
    last_error: Optional[str] = None

    # Priority (higher = more urgent)
    priority: int = 5  # 1-10, default 5

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context

    def __post_init__(self):
        """Validate queue item after initialization."""
        # Convert enum strings to enums
        if isinstance(self.item_type, str):
            self.item_type = QueueItemType(self.item_type)

        if isinstance(self.status, str):
            self.status = QueueItemStatus(self.status)

    def can_retry(self) -> bool:
        """
        Check if item can be retried.

        Returns:
            bool: True if retry count < max_retries
        """
        return self.retry_count < self.max_retries

    def mark_attempt(self, error: Optional[str] = None):
        """
        Mark a sync attempt (successful or failed).

        Args:
            error: Error message if failed, None if successful
        """
        self.last_attempt = datetime.now().isoformat()
        self.retry_count += 1

        if error:
            self.last_error = error
            self.status = QueueItemStatus.FAILED

            # Check if should abandon
            if not self.can_retry():
                self.status = QueueItemStatus.ABANDONED
        else:
            self.status = QueueItemStatus.COMPLETED

    def mark_syncing(self):
        """Mark item as currently being synced."""
        self.status = QueueItemStatus.SYNCING

    def is_stale(self, max_age_hours: int = 48) -> bool:
        """
        Check if queue item is stale (too old).

        Args:
            max_age_hours: Maximum age in hours before considered stale

        Returns:
            bool: True if item is older than max_age_hours
        """
        created = datetime.fromisoformat(self.created_at)
        age_hours = (datetime.now() - created).total_seconds() / 3600
        return age_hours > max_age_hours

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            dict: Queue item data
        """
        data = asdict(self)

        # Convert enums to strings
        data["item_type"] = self.item_type.value
        data["status"] = self.status.value

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncQueueItem":
        """
        Create SyncQueueItem from dictionary.

        Args:
            data: Queue item data

        Returns:
            SyncQueueItem instance
        """
        return cls(**data)

    @classmethod
    def create(
        cls,
        item_type: QueueItemType,
        instance: str,
        file_paths: Optional[List[str]] = None,
        change_type: Optional[str] = None,
        commit_hash: Optional[str] = None,
        commit_message: Optional[str] = None,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "SyncQueueItem":
        """
        Create a new queue item.

        Args:
            item_type: Type of queue item
            instance: Instance where created ("cloud" or "local")
            file_paths: List of affected file paths
            change_type: Type of change (modified/created/deleted)
            commit_hash: Git commit hash if applicable
            commit_message: Commit message
            priority: Priority level (1-10)
            metadata: Additional metadata

        Returns:
            SyncQueueItem instance
        """
        now = datetime.now()
        queue_id = f"QUEUE_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond:06d}"

        return cls(
            queue_id=queue_id,
            item_type=item_type,
            instance=instance,
            created_at=now.isoformat(),
            file_paths=file_paths or [],
            change_type=change_type,
            commit_hash=commit_hash,
            commit_message=commit_message,
            priority=priority,
            metadata=metadata or {}
        )

    def save_to_file(self, queue_dir: Path) -> Path:
        """
        Save queue item to JSON file.

        Args:
            queue_dir: Directory for queue files

        Returns:
            Path to saved file
        """
        queue_dir.mkdir(parents=True, exist_ok=True)

        file_path = queue_dir / f"{self.queue_id}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return file_path

    @classmethod
    def load_from_file(cls, file_path: Path) -> "SyncQueueItem":
        """
        Load queue item from JSON file.

        Args:
            file_path: Path to queue item file

        Returns:
            SyncQueueItem instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls.from_dict(data)


# Helper functions

def get_queue_directory(vault_path: Path) -> Path:
    """
    Get the Sync_Queue directory path.

    Args:
        vault_path: Path to vault root

    Returns:
        Path to Sync_Queue directory
    """
    return vault_path / "Sync_Queue"


def load_pending_queue_items(vault_path: Path) -> List[SyncQueueItem]:
    """
    Load all pending queue items from Sync_Queue directory.

    Args:
        vault_path: Path to vault root

    Returns:
        List of pending SyncQueueItem instances
    """
    queue_dir = get_queue_directory(vault_path)

    if not queue_dir.exists():
        return []

    items = []

    for queue_file in queue_dir.glob("QUEUE_*.json"):
        try:
            item = SyncQueueItem.load_from_file(queue_file)

            # Only load pending or failed items (not completed or abandoned)
            if item.status in (QueueItemStatus.PENDING, QueueItemStatus.FAILED):
                items.append(item)

        except Exception as e:
            # Log error but continue loading other items
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to load queue item {queue_file}: {e}")

    # Sort by priority (high to low), then by creation time (old to new)
    items.sort(key=lambda x: (-x.priority, x.created_at))

    return items


def cleanup_completed_queue_items(vault_path: Path, max_age_hours: int = 24):
    """
    Remove completed/abandoned queue items older than max_age_hours.

    Args:
        vault_path: Path to vault root
        max_age_hours: Maximum age in hours for completed items
    """
    queue_dir = get_queue_directory(vault_path)

    if not queue_dir.exists():
        return

    import logging
    logger = logging.getLogger(__name__)

    removed_count = 0

    for queue_file in queue_dir.glob("QUEUE_*.json"):
        try:
            item = SyncQueueItem.load_from_file(queue_file)

            # Remove if completed/abandoned and old
            if item.status in (QueueItemStatus.COMPLETED, QueueItemStatus.ABANDONED):
                if item.is_stale(max_age_hours):
                    queue_file.unlink()
                    removed_count += 1

        except Exception as e:
            logger.error(f"Failed to cleanup queue item {queue_file}: {e}")

    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old queue items")
