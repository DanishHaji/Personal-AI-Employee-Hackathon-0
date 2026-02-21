#!/usr/bin/env python3
"""
Orchestrator for Personal AI Employee - Bronze Tier MVP

Monitors /Needs_Action/ folder and triggers Claude Code processing automatically.

Implements:
- FR-015: Orchestrator that detects new files and triggers Claude Code
- FR-013: Dashboard updates after processing
- T042: Monitor /Needs_Action/ for new .md files
- T043: Invoke Claude Code vault-manager skill
- T044: Trigger dashboard-updater skill after plan creation
- T045: Audit logging for plan_created actions

Features:
- File system monitoring with watchdog
- Automatic Claude Code skill invocation
- Dashboard refresh after processing
- Structured audit logging
- Graceful shutdown handling

Usage:
    # Run orchestrator
    python src/orchestrator.py

    # Run with PM2
    pm2 start src/orchestrator.py --name orchestrator --interpreter python3
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from src.watchers.base_watcher import BaseWatcher
from src.services.vault_service import VaultService
from src.services.logger_service import AuditLogger, ActionType, Actor, Result


class NeedsActionHandler(FileSystemEventHandler):
    """Event handler for new files in /Needs_Action/ folder."""

    def __init__(self, orchestrator: 'Orchestrator'):
        """
        Initialize event handler.

        Args:
            orchestrator: Reference to parent Orchestrator
        """
        self.orchestrator = orchestrator
        super().__init__()

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Handle file creation event in /Needs_Action/.

        Args:
            event: File system event
        """
        # Ignore directory creation
        if event.is_directory:
            return

        # Get file path
        file_path = Path(event.src_path)

        # Only process .md files
        if file_path.suffix != '.md':
            return

        # Ignore temp files
        if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
            return

        # Ignore alert files (already processed by watchers)
        if file_path.name.startswith('ALERT_'):
            print(f"[Orchestrator] Skipping alert file: {file_path.name}")
            return

        print(f"[Orchestrator] Detected new item: {file_path.name}")

        # Process the file
        self.orchestrator.process_item(file_path)


class Orchestrator(BaseWatcher):
    """Orchestrator that monitors /Needs_Action/ and triggers Claude Code processing."""

    def __init__(
        self,
        vault_path: str | Path,
        check_interval: int = 30,  # Check every 30 seconds
        claude_available: bool = True  # Whether Claude Code CLI is available
    ):
        """
        Initialize Orchestrator.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: Health check interval (default: 30 seconds)
            claude_available: Whether to invoke Claude Code (False for testing)
        """
        super().__init__(
            vault_path=vault_path,
            watcher_name="orchestrator",
            check_interval=check_interval
        )

        # Initialize services
        self.vault_service = VaultService(vault_path)
        self.logger = AuditLogger(vault_path)

        # Folder to monitor
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.needs_action_path.mkdir(parents=True, exist_ok=True)

        # Observer for file system events
        self.observer = Observer()
        self.event_handler = NeedsActionHandler(self)

        # Track processed files to avoid duplicates
        self.processed_files: Set[str] = set()

        # Claude Code availability
        self.claude_available = claude_available

        print(f"[Orchestrator] Initialized")
        print(f"  - Vault: {vault_path}")
        print(f"  - Monitoring: {self.needs_action_path}")
        print(f"  - Claude Code: {'Available' if claude_available else 'Disabled (testing mode)'}")

    def run(self) -> None:
        """
        Main run loop with watchdog observer.

        Overrides BaseWatcher.run() to integrate watchdog.
        """
        self.running = True
        self.start_time = datetime.now()

        # Log startup
        self.logger.log(
            action_type=ActionType.SYSTEM_START,
            actor=Actor.ORCHESTRATOR,
            target="system",
            parameters={"needs_action_path": str(self.needs_action_path)},
            result=Result.SUCCESS
        )

        print(f"[Orchestrator] Started at {self.start_time.isoformat()}")

        try:
            # Start watchdog observer (T042)
            self.observer.schedule(
                self.event_handler,
                str(self.needs_action_path),
                recursive=False
            )
            self.observer.start()
            print(f"[Orchestrator] Watching {self.needs_action_path} for new items")

            # Initial heartbeat
            self._write_heartbeat()

            # Start heartbeat thread
            import threading
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True
            )
            heartbeat_thread.start()

            # Process existing files on startup
            self._process_existing_files()

            # Keep running - watchdog runs in background
            while self.running and not self.shutdown_requested:
                self._perform_check()  # Health check
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print(f"\n[Orchestrator] Received interrupt signal")
        except Exception as e:
            self.logger.log_error(
                actor=Actor.ORCHESTRATOR,
                error_message=str(e),
                error_type=type(e).__name__,
                target="main_loop"
            )
            print(f"[Orchestrator] FATAL ERROR: {e}", file=sys.stderr)
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

    def _process_existing_files(self) -> None:
        """
        Process any existing files in /Needs_Action/ on startup.

        This handles the case where files were added while orchestrator was down.
        """
        existing_files = self.vault_service.list_files('Needs_Action', '*.md')

        if not existing_files:
            print("[Orchestrator] No existing files to process")
            return

        print(f"[Orchestrator] Found {len(existing_files)} existing files")

        for file_path in existing_files:
            # Skip alert files
            if file_path.name.startswith('ALERT_'):
                continue

            # Process file
            self.process_item(file_path)
            time.sleep(2)  # Small delay between processing

    def process_item(self, file_path: Path) -> None:
        """
        Process a newly detected item by invoking Claude Code.

        Implements:
        - T043: Invoke vault-manager skill with file path
        - T044: Trigger dashboard-updater skill after plan creation
        - T045: Audit logging for plan_created actions

        Args:
            file_path: Path to the item file in /Needs_Action/
        """
        try:
            # Avoid duplicate processing
            file_key = f"{file_path.name}_{file_path.stat().st_mtime}"
            if file_key in self.processed_files:
                return
            self.processed_files.add(file_key)

            # Read entity type from frontmatter
            frontmatter, _ = self.vault_service.read_markdown_with_frontmatter(file_path)
            entity_type = frontmatter.get('type', 'unknown')

            print(f"[Orchestrator] Processing {entity_type}: {file_path.name}")

            # Invoke Claude Code vault-manager skill (T043)
            if self.claude_available:
                success = self._invoke_claude_code_plan(file_path)

                if success:
                    # Update dashboard after plan creation (T044)
                    self._update_dashboard()

                    # Increment processed count
                    self.increment_processed_count()

                    print(f"[Orchestrator] ✅ Successfully processed {file_path.name}")
                else:
                    print(f"[Orchestrator] ⚠️ Failed to process {file_path.name}")
            else:
                print(f"[Orchestrator] [TEST MODE] Would process: {file_path.name}")
                self.increment_processed_count()

        except Exception as e:
            # Log error
            self.logger.log_error(
                actor=Actor.ORCHESTRATOR,
                error_message=str(e),
                error_type=type(e).__name__,
                target=str(file_path)
            )
            print(f"[Orchestrator] Error processing {file_path}: {e}", file=sys.stderr)

    def _invoke_claude_code_plan(self, file_path: Path) -> bool:
        """
        Invoke Claude Code vault-manager skill to create plan.

        Implements T043: Claude Code invocation with vault-manager skill.

        Args:
            file_path: Path to item file

        Returns:
            bool: True if successful
        """
        try:
            # Build Claude Code command
            prompt = (
                f"Use vault-manager skill with action=plan and "
                f"file_path={file_path}"
            )

            # Invoke Claude Code CLI
            result = subprocess.run(
                ["claude", prompt],
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
                cwd=str(self.vault_path.parent)  # Run from project root
            )

            if result.returncode == 0:
                print(f"[Orchestrator] Claude Code output:\n{result.stdout}")
                return True
            else:
                print(f"[Orchestrator] Claude Code error: {result.stderr}", file=sys.stderr)
                return False

        except subprocess.TimeoutExpired:
            print("[Orchestrator] Claude Code invocation timed out", file=sys.stderr)
            return False
        except FileNotFoundError:
            print("[Orchestrator] Claude Code CLI not found - install from https://docs.anthropic.com/claude/docs/claude-code", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[Orchestrator] Error invoking Claude Code: {e}", file=sys.stderr)
            return False

    def _update_dashboard(self) -> None:
        """
        Update Dashboard.md after plan creation.

        Implements T044: Trigger dashboard-updater skill.
        """
        try:
            # Invoke Claude Code dashboard-updater skill
            result = subprocess.run(
                ["claude", "Use dashboard-updater skill to refresh Dashboard.md"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.vault_path.parent)
            )

            if result.returncode == 0:
                print("[Orchestrator] Dashboard updated successfully")
            else:
                print(f"[Orchestrator] Dashboard update failed: {result.stderr}", file=sys.stderr)

        except Exception as e:
            print(f"[Orchestrator] Error updating dashboard: {e}", file=sys.stderr)

    def _get_processed_count_key(self) -> str:
        """
        Get the key name for processed items count.

        Returns:
            str: "tasks_triggered_today"
        """
        return "tasks_triggered_today"


def main():
    """Main entry point for Orchestrator."""
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

    # Check if Claude Code is available
    claude_available = True
    try:
        subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  WARNING: Claude Code CLI not found", file=sys.stderr)
        print("Install from: https://docs.anthropic.com/claude/docs/claude-code", file=sys.stderr)
        print("Running in test mode (processing disabled)", file=sys.stderr)
        claude_available = False

    # Create and run orchestrator
    try:
        orchestrator = Orchestrator(
            vault_path=vault_path,
            claude_available=claude_available
        )
        orchestrator.run()

    except KeyboardInterrupt:
        print("\n[Orchestrator] Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[Orchestrator] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
