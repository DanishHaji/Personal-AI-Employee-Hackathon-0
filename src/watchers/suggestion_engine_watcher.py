"""
Suggestion Engine Watcher - Gold Tier US5

Runs proactive suggestion detection every hour.
Detects patterns requiring follow-up, reminders, relationship maintenance, and task chains.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading

from src.services.suggestion_engine import SuggestionEngine
from src.models.proactive_suggestion import expire_old_suggestions

logger = logging.getLogger(__name__)


class SuggestionEngineWatcher:
    """
    Background watcher for hourly proactive suggestion generation.

    Features:
    - Runs detection every hour
    - Expires old suggestions
    - Creates suggestion files in /Needs_Action/
    - Volume limiting per category
    """

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 3600,  # 1 hour
    ):
        """
        Initialize SuggestionEngineWatcher.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: How often to run detection (seconds, default: 3600 = 1 hour)
        """
        self.vault_path = vault_path
        self.check_interval = check_interval

        # Initialize suggestion engine
        self.suggestion_engine = SuggestionEngine(vault_path=vault_path)

        # Track last run time
        self.last_run: Optional[datetime] = None

        # Background thread
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        logger.info(f"SuggestionEngineWatcher initialized (interval={check_interval}s)")

    def start(self):
        """Start the background suggestion engine watcher thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("SuggestionEngineWatcher already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("SuggestionEngineWatcher started")

    def stop(self):
        """Stop the background suggestion engine watcher thread."""
        if not self._thread or not self._thread.is_alive():
            logger.warning("SuggestionEngineWatcher not running")
            return

        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("SuggestionEngineWatcher stopped")

    def _run(self):
        """Background thread main loop."""
        while not self._stop_event.is_set():
            try:
                self._check_schedule()
            except Exception as e:
                logger.error(f"Error in SuggestionEngineWatcher: {e}", exc_info=True)

            # Sleep with periodic wake-up checks
            for _ in range(int(self.check_interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _check_schedule(self):
        """Check if suggestions should be generated."""
        now = datetime.now()

        if self._should_run(now):
            self._run_detection(now)

    def _should_run(self, now: datetime) -> bool:
        """
        Check if suggestion detection should run.

        Runs hourly, but skips if we ran in the last 50 minutes.
        """
        if self.last_run is None:
            return True

        # Check if at least 50 minutes have passed (allow 10-minute buffer)
        minutes_since = (now - self.last_run).total_seconds() / 60
        if minutes_since < 50:
            return False

        return True

    def _run_detection(self, now: datetime):
        """Run proactive suggestion detection."""
        try:
            logger.info("Running proactive suggestion detection...")

            # First, expire old suggestions
            needs_action_dir = Path(self.vault_path) / "Needs_Action"
            expired_count = expire_old_suggestions(needs_action_dir)

            if expired_count > 0:
                logger.info(f"Expired {expired_count} old suggestions")

            # Run detection
            suggestions = self.suggestion_engine.run_detection()

            # Create suggestion files
            created_count = 0
            for suggestion in suggestions:
                try:
                    self.suggestion_engine.create_suggestion(suggestion)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Failed to create suggestion {suggestion.suggestion_id}: {e}")

            # Update last run time
            self.last_run = now

            logger.info(
                f"Suggestion detection complete: {created_count} suggestions created, "
                f"{expired_count} expired"
            )

        except Exception as e:
            logger.error(f"Failed to run suggestion detection: {e}", exc_info=True)

    def run_now(self) -> int:
        """
        Manually trigger suggestion detection (for testing/debugging).

        Returns:
            int: Number of suggestions created
        """
        now = datetime.now()

        try:
            # Expire old suggestions
            needs_action_dir = Path(self.vault_path) / "Needs_Action"
            expired_count = expire_old_suggestions(needs_action_dir)

            # Run detection
            suggestions = self.suggestion_engine.run_detection()

            # Create suggestion files
            created_count = 0
            for suggestion in suggestions:
                try:
                    self.suggestion_engine.create_suggestion(suggestion)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Failed to create suggestion: {e}")

            self.last_run = now

            logger.info(
                f"Manual suggestion detection: {created_count} created, {expired_count} expired"
            )

            return created_count

        except Exception as e:
            logger.error(f"Failed to run suggestion detection: {e}", exc_info=True)
            return 0


def main():
    """Standalone runner for testing."""
    import sys
    import os

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get vault path from environment or argument
    vault_path = os.getenv('VAULT_PATH', '.')
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]

    # Create and start watcher
    watcher = SuggestionEngineWatcher(vault_path=vault_path)

    # Run once immediately
    count = watcher.run_now()
    logger.info(f"Created {count} suggestions")

    # Keep running if --watch flag provided
    if '--watch' in sys.argv:
        watcher.start()
        logger.info("Running in watch mode (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
            watcher.stop()


if __name__ == "__main__":
    main()
