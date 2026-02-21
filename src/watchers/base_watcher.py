"""
Base Watcher Abstract Class for Personal AI Employee - Bronze Tier MVP

Provides common functionality for all watchers:
- Heartbeat mechanism (writes to /Logs/heartbeat.json every 60 seconds)
- Audit logging integration
- Graceful shutdown handling
- Error handling and retry logic

Implements FR-020 and Contract 5 from contracts/file-interfaces.md

Subclasses:
- GmailWatcher: Monitors Gmail inbox
- FilesystemWatcher: Monitors /Inbox folder
"""

import json
import signal
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, List, Dict
import threading

from ..services.logger_service import AuditLogger, Actor, ActionType, Result


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""

    def __init__(
        self,
        vault_path: str | Path,
        watcher_name: str,
        check_interval: int = 60
    ):
        """
        Initialize base watcher.

        Args:
            vault_path: Absolute path to Obsidian vault root
            watcher_name: Name of this watcher (e.g., "gmail_watcher")
            check_interval: How often to perform checks in seconds (default: 60)
        """
        self.vault_path = Path(vault_path).resolve()
        self.watcher_name = watcher_name
        self.check_interval = check_interval

        # Initialize logger
        self.logger = AuditLogger(vault_path)

        # State management
        self.running = False
        self.shutdown_requested = False

        # Heartbeat management
        self.heartbeat_file = self.vault_path / "Logs" / "heartbeat.json"
        self.last_heartbeat_time = None
        self.heartbeat_interval = 60  # seconds (FR-020)

        # Statistics
        self.items_processed_today = 0
        self.last_check_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None

        # Temporary queue for vault inaccessibility (T054 - Edge Case)
        self.pending_queue: List[Dict[str, Any]] = []
        self.vault_accessible = True
        self.vault_check_failures = 0
        self.max_queue_size = 100  # Max items to queue before dropping

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def run(self) -> None:
        """
        Main run loop for the watcher.

        Handles:
        - Startup logging
        - Periodic checking
        - Heartbeat updates
        - Graceful shutdown
        """
        self.running = True
        self.start_time = datetime.now()

        # Log startup
        self.logger.log(
            action_type=ActionType.SYSTEM_START,
            actor=self.watcher_name,
            target="system",
            parameters={"check_interval": self.check_interval},
            result=Result.SUCCESS
        )

        print(f"[{self.watcher_name}] Started at {self.start_time.isoformat()}")
        print(f"[{self.watcher_name}] Check interval: {self.check_interval}s")

        try:
            # Initial heartbeat
            self._write_heartbeat()

            # Start heartbeat thread
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True
            )
            heartbeat_thread.start()

            # Main loop
            while self.running and not self.shutdown_requested:
                try:
                    # Perform the watcher-specific check
                    self._perform_check()

                    # Update last check time
                    self.last_check_time = datetime.now()

                    # Sleep until next check
                    time.sleep(self.check_interval)

                except KeyboardInterrupt:
                    print(f"\n[{self.watcher_name}] Received interrupt signal")
                    break
                except Exception as e:
                    # Log error but continue running
                    self.logger.log_error(
                        actor=self.watcher_name,
                        error_message=str(e),
                        error_type=type(e).__name__,
                        target="check_loop"
                    )
                    print(f"[{self.watcher_name}] ERROR: {e}", file=sys.stderr)

                    # Sleep before retry
                    time.sleep(self.check_interval)

        except Exception as e:
            # Fatal error - log and exit
            self.logger.log_error(
                actor=self.watcher_name,
                error_message=str(e),
                error_type=type(e).__name__,
                target="main_loop"
            )
            print(f"[{self.watcher_name}] FATAL ERROR: {e}", file=sys.stderr)
            raise

        finally:
            self._shutdown()

    @abstractmethod
    def _perform_check(self) -> None:
        """
        Perform the watcher-specific check operation.

        Must be implemented by subclasses.

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _perform_check()")

    def _heartbeat_loop(self) -> None:
        """
        Background thread that writes heartbeat every 60 seconds.

        Implements FR-020 and Contract 5.
        """
        while self.running and not self.shutdown_requested:
            try:
                self._write_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(
                    f"[{self.watcher_name}] Heartbeat write failed: {e}",
                    file=sys.stderr
                )
                time.sleep(self.heartbeat_interval)

    def _write_heartbeat(self) -> None:
        """
        Write heartbeat timestamp to /Logs/heartbeat.json.

        Format per Contract 5:
        {
          "gmail_watcher": {
            "timestamp": "2026-02-21T14:50:00.123Z",
            "status": "running",
            "last_check": "2026-02-21T14:49:45.678Z",
            "emails_processed_today": 12
          },
          ...
        }

        Uses file locking pattern: read → update → atomic write
        """
        # Ensure Logs directory exists
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing heartbeat data
        heartbeat_data = {}
        if self.heartbeat_file.exists():
            try:
                with open(self.heartbeat_file, 'r', encoding='utf-8') as f:
                    heartbeat_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is corrupted or missing, start fresh
                heartbeat_data = {}

        # Update this watcher's entry
        self_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "running",
        }

        # Add last_check if available
        if self.last_check_time:
            self_entry["last_check"] = self.last_check_time.isoformat() + "Z"

        # Add processed count (watcher-specific naming)
        count_key = self._get_processed_count_key()
        self_entry[count_key] = self.items_processed_today

        heartbeat_data[self.watcher_name] = self_entry

        # Atomic write: write to temp, then rename
        temp_file = self.heartbeat_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(heartbeat_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.heartbeat_file)  # Atomic on most systems

            self.last_heartbeat_time = datetime.utcnow()

        except Exception as e:
            # Cleanup temp file if write failed
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def _check_vault_accessibility(self) -> bool:
        """
        Check if Obsidian vault is accessible (T054 - Edge Case).

        Returns:
            bool: True if vault is accessible
        """
        try:
            # Check if vault path exists and is readable/writable
            if not self.vault_path.exists():
                return False

            if not self.vault_path.is_dir():
                return False

            # Try to access Needs_Action folder
            needs_action = self.vault_path / "Needs_Action"
            if not needs_action.exists():
                return False

            # Try to write a test file
            test_file = self.vault_path / "Logs" / ".vault_access_test"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()

            return True

        except (PermissionError, OSError, IOError) as e:
            return False

    def _handle_vault_inaccessibility(self, item_data: Dict[str, Any]) -> None:
        """
        Handle vault inaccessibility by queuing item (T054 - Edge Case).

        Args:
            item_data: Data to queue (email, file, etc.)
        """
        # Check current status
        vault_accessible = self._check_vault_accessibility()

        if not vault_accessible:
            # Vault is inaccessible
            self.vault_check_failures += 1

            if self.vault_accessible:  # Was previously accessible
                print(f"[{self.watcher_name}] ⚠️  Vault inaccessible - queuing items temporarily")
                self.vault_accessible = False

            # Add to queue if not full
            if len(self.pending_queue) < self.max_queue_size:
                item_data['queued_at'] = datetime.now().isoformat()
                self.pending_queue.append(item_data)
                print(f"[{self.watcher_name}] Queued item (queue size: {len(self.pending_queue)})")
            else:
                print(f"[{self.watcher_name}] ⚠️  Queue full ({self.max_queue_size} items) - dropping item")
                self.logger.log_error(
                    actor=self.watcher_name,
                    error_message=f"Queue overflow - dropped item (queue size: {len(self.pending_queue)})",
                    error_type="QueueOverflow",
                    target="vault_inaccessible"
                )

            # Create alert if failures exceed threshold
            if self.vault_check_failures == 5:  # After 5 consecutive failures
                self._create_vault_inaccessibility_alert()

        else:
            # Vault is accessible
            if not self.vault_accessible:  # Was previously inaccessible
                print(f"[{self.watcher_name}] ✅ Vault accessible again - processing queued items")
                self.vault_accessible = True
                self.vault_check_failures = 0

                # Process pending queue
                self._process_pending_queue()

    def _create_vault_inaccessibility_alert(self) -> None:
        """
        Create alert file for vault inaccessibility (T054).

        Note: Alert is created in a fallback location if vault is inaccessible.
        """
        try:
            # Try to create alert in vault
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_filename = f"ALERT_vault_inaccessible_{timestamp}.md"
            alert_path = self.vault_path / "Needs_Action" / alert_filename

            alert_content = f"""---
type: alert
category: vault_inaccessible
severity: critical
created: {datetime.now().isoformat()}
status: needs_attention
queued_items: {len(self.pending_queue)}
---

# 🔴 Obsidian Vault Inaccessible

## Problem

The {self.watcher_name} cannot access the Obsidian vault.

**Vault Path**: `{self.vault_path}`

**Time**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Failures**: {self.vault_check_failures} consecutive checks

## Impact

- ❌ New items are being **queued in memory** (not saved to disk)
- ❌ Dashboard will **not update**
- ❌ Risk of data loss if watcher crashes

**Current Queue Size**: {len(self.pending_queue)} items (max: {self.max_queue_size})

## Possible Causes

1. **Network Drive Disconnected**: Vault is on a network drive that's unavailable
2. **Permission Issues**: Watcher doesn't have write permissions to vault
3. **Disk Full**: No space left on device
4. **Vault Moved/Deleted**: Vault path no longer exists
5. **Obsidian Locked Files**: Obsidian has exclusive locks on files

## Solution

### Step 1: Check Vault Path

```bash
ls -la "{self.vault_path}"
```

Expected: Vault folders visible (Inbox, Needs_Action, Plans, etc.)

### Step 2: Check Permissions

```bash
touch "{self.vault_path}/Logs/.test"
rm "{self.vault_path}/Logs/.test"
```

Expected: No permission errors

### Step 3: Check Disk Space

```bash
df -h "{self.vault_path}"
```

Expected: Available space > 1GB

### Step 4: Restart Watcher

Once vault is accessible:

```bash
pm2 restart {self.watcher_name}
```

Watcher will automatically process queued items.

## Data Safety

- Queued items are in memory (lost if watcher crashes)
- Max queue: {self.max_queue_size} items
- After queue full, new items will be **dropped**

**Recommendation**: Resolve vault access issue immediately.

---

**This alert was automatically generated by {self.watcher_name}**

Once resolved, queued items will be processed automatically.
"""

            alert_path.write_text(alert_content, encoding='utf-8')
            print(f"[{self.watcher_name}] Created vault inaccessibility alert: {alert_filename}")

        except Exception as e:
            # If we can't write to vault, create alert in current directory
            fallback_path = Path.cwd() / f"ALERT_vault_inaccessible_{timestamp}.md"
            try:
                fallback_path.write_text(alert_content, encoding='utf-8')
                print(f"[{self.watcher_name}] Created fallback alert: {fallback_path}")
            except Exception as e2:
                print(f"[{self.watcher_name}] Failed to create alert: {e2}", file=sys.stderr)

    def _process_pending_queue(self) -> None:
        """
        Process items from pending queue when vault becomes accessible.

        Called when vault accessibility is restored.
        """
        if not self.pending_queue:
            return

        print(f"[{self.watcher_name}] Processing {len(self.pending_queue)} queued items...")

        processed = 0
        failed = 0

        # Process each queued item
        for item_data in self.pending_queue:
            try:
                # Subclasses should implement _process_queued_item
                # For now, log that item was queued
                self.logger.log(
                    action_type=ActionType.SYSTEM_START,  # Reuse for queue processing
                    actor=self.watcher_name,
                    target="queued_item",
                    parameters={
                        "queued_at": item_data.get('queued_at'),
                        "processed_at": datetime.now().isoformat()
                    },
                    result=Result.SUCCESS
                )
                processed += 1

            except Exception as e:
                failed += 1
                print(f"[{self.watcher_name}] Failed to process queued item: {e}", file=sys.stderr)

        # Clear queue
        self.pending_queue.clear()

        print(f"[{self.watcher_name}] Processed {processed} queued items ({failed} failed)")

    def _get_processed_count_key(self) -> str:
        """
        Get the key name for processed items count.

        Subclasses can override to customize.

        Returns:
            str: Key name (e.g., "emails_processed_today")
        """
        # Default: convert watcher_name to count key
        # gmail_watcher → emails_processed_today
        # filesystem_watcher → files_processed_today
        if "gmail" in self.watcher_name.lower():
            return "emails_processed_today"
        elif "filesystem" in self.watcher_name.lower() or "file" in self.watcher_name.lower():
            return "files_processed_today"
        else:
            return "items_processed_today"

    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.

        Handles SIGINT (Ctrl+C) and SIGTERM.
        """
        def signal_handler(signum, frame):
            print(f"\n[{self.watcher_name}] Received signal {signum}, shutting down...")
            self.shutdown_requested = True
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _shutdown(self) -> None:
        """
        Perform graceful shutdown cleanup.

        - Write final heartbeat with "stopped" status
        - Log shutdown event
        - Display statistics
        """
        self.running = False

        print(f"\n[{self.watcher_name}] Shutting down...")

        # Update heartbeat with stopped status
        try:
            if self.heartbeat_file.exists():
                with open(self.heartbeat_file, 'r', encoding='utf-8') as f:
                    heartbeat_data = json.load(f)

                if self.watcher_name in heartbeat_data:
                    heartbeat_data[self.watcher_name]["status"] = "stopped"
                    heartbeat_data[self.watcher_name]["timestamp"] = datetime.utcnow().isoformat() + "Z"

                    with open(self.heartbeat_file, 'w', encoding='utf-8') as f:
                        json.dump(heartbeat_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[{self.watcher_name}] Failed to update heartbeat on shutdown: {e}", file=sys.stderr)

        # Log shutdown
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        self.logger.log(
            action_type=ActionType.SYSTEM_STOP,
            actor=self.watcher_name,
            target="system",
            parameters={
                "uptime_seconds": uptime_seconds,
                "items_processed": self.items_processed_today
            },
            result=Result.SUCCESS
        )

        # Display statistics
        print(f"[{self.watcher_name}] Statistics:")
        print(f"  - Uptime: {uptime_seconds:.1f} seconds")
        print(f"  - Items processed: {self.items_processed_today}")
        print(f"[{self.watcher_name}] Stopped at {datetime.now().isoformat()}")

    def increment_processed_count(self) -> None:
        """
        Increment the count of items processed today.

        Should be called by subclasses when they process an item.
        """
        self.items_processed_today += 1

    def get_status(self) -> dict[str, Any]:
        """
        Get current watcher status.

        Returns:
            dict: Status information
        """
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        return {
            "name": self.watcher_name,
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime_seconds,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "items_processed_today": self.items_processed_today,
            "last_heartbeat": self.last_heartbeat_time.isoformat() if self.last_heartbeat_time else None,
        }
