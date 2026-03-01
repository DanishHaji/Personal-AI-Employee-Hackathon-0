"""
Calendar Watcher - Gold Tier US2

Hourly background sync of Google Calendar events to local cache.
"""

import logging
import time
from pathlib import Path
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)


class CalendarWatcher:
    """
    Background watcher for Google Calendar sync.

    Features:
    - Hourly sync of calendar events
    - Automatic conflict detection
    - Error recovery and retry logic
    - Graceful handling of API unavailability
    """

    def __init__(self, vault_path: Path, sync_interval_minutes: int = 60):
        """
        Initialize CalendarWatcher.

        Args:
            vault_path: Path to Obsidian vault
            sync_interval_minutes: Sync interval (default: 60 minutes)
        """
        self.vault_path = Path(vault_path)
        self.sync_interval_seconds = sync_interval_minutes * 60
        self.calendar_service = None
        self.running = False

        logger.info(
            f"CalendarWatcher initialized (sync every {sync_interval_minutes} minutes)"
        )

    def start(self) -> None:
        """
        Start the calendar watcher loop.

        This is a blocking call - runs until stopped.
        """
        self.running = True
        logger.info("CalendarWatcher started")

        while self.running:
            try:
                self._sync_cycle()
            except KeyboardInterrupt:
                logger.info("CalendarWatcher interrupted by user")
                self.stop()
                break
            except Exception as e:
                logger.error(f"CalendarWatcher sync cycle error: {e}", exc_info=True)
                # Continue running despite errors

            # Sleep until next sync
            if self.running:
                logger.debug(f"Sleeping for {self.sync_interval_seconds} seconds")
                time.sleep(self.sync_interval_seconds)

    def stop(self) -> None:
        """Stop the calendar watcher."""
        self.running = False
        logger.info("CalendarWatcher stopped")

    def _sync_cycle(self) -> None:
        """Execute one sync cycle."""
        logger.info("Starting calendar sync cycle")

        try:
            # Initialize calendar service if not already done
            if self.calendar_service is None:
                self.calendar_service = CalendarService(vault_path=self.vault_path)

            # Check if Google Calendar credentials are configured
            if not self.calendar_service.credentials_path:
                logger.warning(
                    "Google Calendar credentials not configured, skipping sync"
                )
                return

            # Sync events from Google Calendar
            synced_count = self.calendar_service.sync_from_google_calendar(
                days_ahead=30,
                days_back=7
            )

            # Detect conflicts
            conflicts = self.calendar_service.detect_conflicts()

            if conflicts:
                logger.warning(
                    f"Detected {len(conflicts)} events with conflicts: "
                    f"{list(conflicts.keys())}"
                )

                # Update conflict information in cached events
                for event_id, conflicting_ids in conflicts.items():
                    event = self.calendar_service._cached_events.get(event_id)
                    if event:
                        event.conflicts = conflicting_ids
                        event.last_modified = datetime.now(
                            datetime.UTC if hasattr(datetime, 'UTC') else None
                        )

                # Save updated cache
                self.calendar_service._save_cache()

            logger.info(
                f"Sync cycle complete: {synced_count} events synced, "
                f"{len(conflicts)} conflicts detected"
            )

        except RuntimeError as e:
            # Google Calendar API not available - expected error
            logger.warning(f"Calendar sync skipped: {e}")
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point for calendar watcher."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get vault path from environment or use current directory
    vault_path = os.getenv('VAULT_PATH', '.')

    # Get sync interval from environment (default: 60 minutes)
    sync_interval = int(os.getenv('CALENDAR_SYNC_INTERVAL_MINUTES', '60'))

    logger.info(f"Starting Calendar Watcher (vault: {vault_path})")

    # Create and start watcher
    watcher = CalendarWatcher(
        vault_path=Path(vault_path),
        sync_interval_minutes=sync_interval
    )

    try:
        watcher.start()
    except KeyboardInterrupt:
        logger.info("Calendar Watcher stopped by user")
    finally:
        watcher.stop()


if __name__ == '__main__':
    main()
