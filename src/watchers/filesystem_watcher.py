#!/usr/bin/env python3
"""
File System Watcher for Personal AI Employee - Bronze Tier MVP

Monitors /Inbox/ folder for manually dropped files.
Creates FileDrop entity metadata files in /Needs_Action/.

Implements:
- FR-009 to FR-011: File system monitoring, file processing, quarantine
- Contract 2: FileDrop entity file creation
- FR-020: Heartbeat mechanism

Features:
- Real-time file detection using watchdog library
- Automatic file copy to /Needs_Action/ with timestamp suffix
- Unsafe file type quarantine (.exe, .dmg, .app, .bat, .sh, .cmd, .msi, .dll)
- Quarantine alerts for security
- Structured audit logging

Usage:
    # Run watcher
    python src/watchers/filesystem_watcher.py

    # Run with PM2
    pm2 start src/watchers/filesystem_watcher.py --name fs-watcher --interpreter python3
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from src.watchers.base_watcher import BaseWatcher
from src.services.vault_service import VaultService
from src.models.file_drop import (
    FileDrop,
    create_filedrop_filename,
    create_copied_filename,
    UNSAFE_EXTENSIONS
)
from src.services.logger_service import Result


class InboxFileHandler(FileSystemEventHandler):
    """Event handler for file creation events in /Inbox folder."""

    def __init__(self, watcher: 'FilesystemWatcher'):
        """
        Initialize event handler.

        Args:
            watcher: Reference to parent FilesystemWatcher
        """
        self.watcher = watcher
        super().__init__()

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Handle file creation event.

        Implements T026: Detect new files in /Inbox/.

        Args:
            event: File system event
        """
        # Ignore directory creation
        if event.is_directory:
            return

        # Get file path
        file_path = Path(event.src_path)

        # Ignore hidden files and temp files
        if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
            return

        print(f"[FilesystemWatcher] Detected new file: {file_path.name}")

        # Process the file
        self.watcher.process_file(file_path)


class FilesystemWatcher(BaseWatcher):
    """Watcher that monitors /Inbox folder for dropped files."""

    def __init__(
        self,
        vault_path: str | Path,
        check_interval: int = 10  # Check every 10 seconds for watchdog health
    ):
        """
        Initialize File System Watcher.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: Health check interval (default: 10 seconds)
        """
        super().__init__(
            vault_path=vault_path,
            watcher_name="filesystem_watcher",
            check_interval=check_interval
        )

        # Initialize Vault service
        self.vault_service = VaultService(vault_path)

        # Inbox folder to monitor
        self.inbox_path = self.vault_path / "Inbox"
        self.inbox_path.mkdir(parents=True, exist_ok=True)

        # Observer for file system events
        self.observer = Observer()
        self.event_handler = InboxFileHandler(self)

        # Track processed files to avoid duplicates
        self.processed_files: Set[str] = set()

        print(f"[FilesystemWatcher] Initialized")
        print(f"  - Vault: {vault_path}")
        print(f"  - Monitoring: {self.inbox_path}")

    def run(self) -> None:
        """
        Main run loop with watchdog observer.

        Overrides BaseWatcher.run() to integrate watchdog.
        """
        self.running = True
        self.start_time = datetime.now()

        # Log startup
        self.logger.log(
            action_type="system_start",
            actor=self.watcher_name,
            target="system",
            parameters={"inbox_path": str(self.inbox_path)},
            result=Result.SUCCESS
        )

        print(f"[FilesystemWatcher] Started at {self.start_time.isoformat()}")

        try:
            # Start watchdog observer (T026)
            self.observer.schedule(
                self.event_handler,
                str(self.inbox_path),
                recursive=False
            )
            self.observer.start()
            print(f"[FilesystemWatcher] Watching {self.inbox_path} for file drops")

            # Initial heartbeat
            self._write_heartbeat()

            # Start heartbeat thread
            import threading
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True
            )
            heartbeat_thread.start()

            # Keep running - watchdog runs in background
            while self.running and not self.shutdown_requested:
                self._perform_check()  # Health check
                import time
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print(f"\n[FilesystemWatcher] Received interrupt signal")
        except Exception as e:
            self.logger.log_error(
                actor=self.watcher_name,
                error_message=str(e),
                error_type=type(e).__name__,
                target="main_loop"
            )
            print(f"[FilesystemWatcher] FATAL ERROR: {e}", file=sys.stderr)
            raise
        finally:
            # Stop observer
            self.observer.stop()
            self.observer.join()
            self._shutdown()

    def _perform_check(self) -> None:
        """
        Perform health check (watchdog runs independently).

        This is mainly for heartbeat updates and status monitoring.
        """
        self.last_check_time = datetime.now()
        # Watchdog handles file detection automatically

    def process_file(self, file_path: Path) -> None:
        """
        Process a newly detected file.

        Implements:
        - T027: Copy file to /Needs_Action/ with timestamp
        - T028: Create FileDrop metadata file
        - T029: Quarantine unsafe file types
        - T030: Create quarantine alerts
        - T032: Audit logging

        Args:
            file_path: Path to the dropped file
        """
        try:
            # Avoid duplicate processing
            file_key = f"{file_path.name}_{file_path.stat().st_mtime}"
            if file_key in self.processed_files:
                return
            self.processed_files.add(file_key)

            # Get file metadata
            original_name = file_path.name
            file_size = file_path.stat().st_size
            file_type = file_path.suffix
            received_time = datetime.now()

            # Check if file type is unsafe (T029)
            is_unsafe = file_type.lower() in UNSAFE_EXTENSIONS

            if is_unsafe:
                # Quarantine unsafe file (T029, T030)
                self._quarantine_file(file_path, original_name, file_size, file_type, received_time)
            else:
                # Process safe file (T027, T028)
                self._process_safe_file(file_path, original_name, file_size, file_type, received_time)

            # Increment processed count
            self.increment_processed_count()

        except Exception as e:
            # Log error (T032)
            self.logger.log_error(
                actor=self.watcher_name,
                error_message=str(e),
                error_type=type(e).__name__,
                target=str(file_path)
            )
            print(f"[FilesystemWatcher] Error processing {file_path}: {e}", file=sys.stderr)

    def _process_safe_file(
        self,
        file_path: Path,
        original_name: str,
        file_size: int,
        file_type: str,
        received_time: datetime
    ) -> None:
        """
        Process safe file: copy to /Needs_Action/ and create metadata.

        Implements T027, T028.

        Args:
            file_path: Source file path
            original_name: Original filename
            file_size: File size in bytes
            file_type: File extension
            received_time: When file was detected
        """
        # Generate unique filename with timestamp (T027)
        copied_filename = create_copied_filename(original_name, received_time)
        dest_path = self.vault_path / "Needs_Action" / copied_filename

        # Copy file to /Needs_Action/ (T027)
        shutil.copy2(file_path, dest_path)
        print(f"[FilesystemWatcher] Copied: {original_name} → {copied_filename}")

        # Create FileDrop metadata (T028)
        file_drop = FileDrop(
            original_name=original_name,
            file_path=str(dest_path),
            size=file_size,
            file_type=file_type,
            received=received_time,
            status="pending",
            quarantined=False
        )

        # Validate
        file_drop.validate()

        # Generate metadata markdown
        metadata_content = file_drop.to_markdown(self.vault_path)

        # Write metadata file
        metadata_filename = create_filedrop_filename(original_name, received_time)
        metadata_path = Path("Needs_Action") / metadata_filename
        self.vault_service.write_markdown(metadata_path, metadata_content)

        print(f"[FilesystemWatcher] Created metadata: {metadata_filename}")

        # Remove original file from Inbox
        file_path.unlink()

        # Log to audit (T032)
        self.logger.log_file_dropped(
            filename=original_name,
            size=file_size,
            file_type=file_type,
            quarantined=False,
            result=Result.SUCCESS
        )

    def _quarantine_file(
        self,
        file_path: Path,
        original_name: str,
        file_size: int,
        file_type: str,
        received_time: datetime
    ) -> None:
        """
        Quarantine unsafe file and create alert.

        Implements T029, T030.

        Args:
            file_path: Source file path
            original_name: Original filename
            file_size: File size in bytes
            file_type: File extension
            received_time: When file was detected
        """
        print(f"[FilesystemWatcher] ⚠️ UNSAFE FILE DETECTED: {original_name} ({file_type})")

        # Move to quarantine folder (T029)
        quarantine_path = self.vault_path / "Quarantine" / original_name
        shutil.move(str(file_path), str(quarantine_path))

        print(f"[FilesystemWatcher] Quarantined: {original_name} → /Quarantine/")

        # Create quarantine alert in /Needs_Action/ (T030)
        alert_filename = f"ALERT_quarantined_{original_name}.md"
        alert_path = Path("Needs_Action") / alert_filename

        alert_content = f"""---
type: alert
alert_type: quarantine
filename: {original_name}
file_type: {file_type}
size: {file_size}
quarantine_path: /Quarantine/{original_name}
timestamp: {received_time.isoformat()}
severity: high
---

## ⚠️ SECURITY ALERT: Unsafe File Quarantined

A potentially dangerous file was detected and automatically quarantined for your safety.

**File Details**:
- **Filename**: `{original_name}`
- **Type**: {file_type} (UNSAFE EXECUTABLE)
- **Size**: {file_size:,} bytes
- **Quarantined At**: `{received_time.strftime('%Y-%m-%d %H:%M:%S')}`
- **Location**: `/Quarantine/{original_name}`

**Why was this file quarantined?**

The file extension `{file_type}` is classified as unsafe because it can:
- Execute code on your system
- Potentially contain malware or viruses
- Pose a security risk if opened

**Unsafe file types include**: .exe, .dmg, .app, .bat, .sh, .cmd, .msi, .dll

## Recommended Actions

- [ ] **Verify the source**: Do you trust where this file came from?
- [ ] **Scan with antivirus**: Run a virus scan on the quarantined file
- [ ] **Delete if suspicious**: If you don't recognize this file, delete it immediately
- [ ] **Restore if trusted**: If you're certain the file is safe, you can manually move it from /Quarantine/

## How to Handle This File

### If the file is SAFE and expected:
1. Verify its source and purpose
2. Scan it with antivirus software
3. Manually move it from `/Quarantine/` to your desired location
4. Mark this alert as resolved and move to `/Done/`

### If the file is SUSPICIOUS or unexpected:
1. **DO NOT OPEN OR EXECUTE THE FILE**
2. Delete it from `/Quarantine/` folder
3. Investigate how it was added to your /Inbox
4. Mark this alert as resolved and move to `/Done/`

---

**This alert was automatically generated by the AI Employee security system.**
"""

        self.vault_service.write_markdown(alert_path, alert_content)
        print(f"[FilesystemWatcher] Created alert: {alert_filename}")

        # Create FileDrop metadata for the quarantined file
        file_drop = FileDrop(
            original_name=original_name,
            file_path=str(quarantine_path),
            size=file_size,
            file_type=file_type,
            received=received_time,
            status="quarantined",
            quarantined=True
        )

        # Log to audit (T032)
        self.logger.log_file_dropped(
            filename=original_name,
            size=file_size,
            file_type=file_type,
            quarantined=True,
            result=Result.SUCCESS
        )


def main():
    """Main entry point for File System Watcher."""
    # Load environment variables
    load_dotenv()

    # Get vault path from environment
    vault_path = os.getenv('VAULT_PATH')

    if not vault_path:
        print("ERROR: VAULT_PATH not set in .env file", file=sys.stderr)
        sys.exit(1)

    # Validate vault exists
    if not Path(vault_path).exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        print("Run: python scripts/init_vault.py --path /path/to/vault", file=sys.stderr)
        sys.exit(1)

    # Create and run watcher
    try:
        watcher = FilesystemWatcher(vault_path=vault_path)
        watcher.run()

    except KeyboardInterrupt:
        print("\n[FilesystemWatcher] Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[FilesystemWatcher] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
