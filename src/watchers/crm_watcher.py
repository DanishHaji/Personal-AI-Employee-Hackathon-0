"""
CRM Watcher - Gold Tier US7

Runs daily CRM monitoring tasks:
- Update relationship strengths
- Find stale relationships
- Create follow-up suggestions
- Auto-promote high-value contacts to VIP
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import threading

from src.services.contact_service import ContactService

logger = logging.getLogger(__name__)


class CRMWatcher:
    """
    Background watcher for daily CRM monitoring and relationship maintenance.

    Features:
    - Daily relationship strength updates
    - Stale relationship detection
    - Automatic follow-up suggestions
    - VIP auto-promotion
    """

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 86400,  # 24 hours
        run_hour: int = 9  # 9 AM
    ):
        """
        Initialize CRMWatcher.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: How often to check schedule (seconds, default: 24 hours)
            run_hour: Hour of day to run (0-23, default: 9 AM)
        """
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.run_hour = run_hour

        # Initialize contact service
        self.contact_service = ContactService(vault_path=vault_path)

        # Track last run time
        self.last_run: Optional[datetime] = None

        # Background thread
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        logger.info(f"CRMWatcher initialized (run_hour={run_hour}, interval={check_interval}s)")

    def start(self):
        """Start the background CRM watcher thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("CRMWatcher already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("CRMWatcher started")

    def stop(self):
        """Stop the background CRM watcher thread."""
        if not self._thread or not self._thread.is_alive():
            logger.warning("CRMWatcher not running")
            return

        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("CRMWatcher stopped")

    def _run(self):
        """Background thread main loop."""
        while not self._stop_event.is_set():
            try:
                self._check_schedule()
            except Exception as e:
                logger.error(f"Error in CRMWatcher: {e}", exc_info=True)

            # Sleep with periodic wake-up checks (check every hour)
            for _ in range(3600):  # Check every second for 1 hour
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _check_schedule(self):
        """Check if CRM monitoring should run."""
        now = datetime.now()

        if self._should_run(now):
            self._run_monitoring(now)

    def _should_run(self, now: datetime) -> bool:
        """
        Check if CRM monitoring should run.

        Runs once per day at specified hour.
        """
        # Check if it's the correct hour
        if now.hour != self.run_hour:
            return False

        # Check if we already ran today
        if self.last_run:
            # If we ran in the last 20 hours, skip
            if (now - self.last_run).total_seconds() < (20 * 3600):
                return False

        return True

    def _run_monitoring(self, now: datetime):
        """Run daily CRM monitoring tasks."""
        try:
            logger.info("Running daily CRM monitoring...")

            # Task 1: Update relationship strengths
            logger.info("Task 1: Updating relationship strengths...")
            self.contact_service.update_relationship_strengths()

            # Task 2: Auto-promote high-value contacts
            logger.info("Task 2: Auto-promoting high-value contacts...")
            self.contact_service.auto_promote_to_vip(strength_threshold=200)

            # Task 3: Find stale relationships
            logger.info("Task 3: Finding stale relationships...")
            stale_contacts = self.contact_service.find_stale_relationships(vip_only=True)

            logger.info(f"Found {len(stale_contacts)} stale VIP relationships")

            # Task 4: Create follow-up suggestions
            if stale_contacts:
                logger.info("Task 4: Creating follow-up suggestions...")
                suggestions = self.contact_service.create_follow_up_suggestions(
                    stale_contacts=stale_contacts,
                    max_suggestions=5  # Limit to 5 per day
                )
                logger.info(f"Created {len(suggestions)} follow-up suggestions")

            # Task 5: Get summary
            summary = self.contact_service.get_contacts_summary()

            logger.info(
                f"CRM monitoring complete: "
                f"{summary['total_contacts']} contacts, "
                f"{summary['vip_contacts']} VIP, "
                f"{summary['stale_relationships']} stale"
            )

            # Update last run time
            self.last_run = now

        except Exception as e:
            logger.error(f"Failed to run CRM monitoring: {e}", exc_info=True)

    def run_now(self) -> Dict[str, Any]:
        """
        Manually trigger CRM monitoring (for testing/debugging).

        Returns:
            Dict: Summary of monitoring results
        """
        now = datetime.now()

        try:
            # Update relationship strengths
            self.contact_service.update_relationship_strengths()

            # Auto-promote
            self.contact_service.auto_promote_to_vip(strength_threshold=200)

            # Find stale
            stale_contacts = self.contact_service.find_stale_relationships(vip_only=True)

            # Create suggestions
            suggestions = []
            if stale_contacts:
                suggestions = self.contact_service.create_follow_up_suggestions(
                    stale_contacts=stale_contacts,
                    max_suggestions=5
                )

            # Get summary
            summary = self.contact_service.get_contacts_summary()

            self.last_run = now

            result = {
                **summary,
                "stale_vip_contacts": len(stale_contacts),
                "suggestions_created": len(suggestions),
                "run_time": now.isoformat()
            }

            logger.info(f"Manual CRM monitoring complete: {result}")

            return result

        except Exception as e:
            logger.error(f"Failed to run CRM monitoring: {e}", exc_info=True)
            return {"error": str(e)}


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
    watcher = CRMWatcher(vault_path=vault_path)

    # Run once immediately
    result = watcher.run_now()
    logger.info(f"CRM monitoring result: {result}")

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
