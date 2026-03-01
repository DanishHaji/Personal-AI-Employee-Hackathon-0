"""
Document Watcher - Gold Tier US3

Schedules automatic document generation:
- Weekly status reports (every Monday)
- Monthly summaries (first day of each month)
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading

from src.services.document_service import DocumentService
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class DocumentWatcher:
    """
    Background watcher for scheduled document generation.

    Generates documents on a schedule:
    - Weekly status reports: Every Monday at 9:00 AM
    - Monthly summaries: First day of month at 10:00 AM
    """

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 3600,  # 1 hour
        schedule_weekly: bool = True,
        schedule_monthly: bool = True,
        encrypt_documents: bool = False
    ):
        """
        Initialize DocumentWatcher.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: How often to check schedule (seconds, default: 1 hour)
            schedule_weekly: Enable weekly status reports
            schedule_monthly: Enable monthly summaries
            encrypt_documents: Encrypt sensitive fields in documents
        """
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.schedule_weekly = schedule_weekly
        self.schedule_monthly = schedule_monthly
        self.encrypt_documents = encrypt_documents

        # Initialize services
        self.document_service = DocumentService(
            vault_path=vault_path,
            audit_service=AuditService()
        )

        # Track last generation times
        self.last_weekly_generation: Optional[datetime] = None
        self.last_monthly_generation: Optional[datetime] = None

        # Background thread
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        logger.info(
            f"DocumentWatcher initialized (weekly={schedule_weekly}, "
            f"monthly={schedule_monthly}, interval={check_interval}s)"
        )

    def start(self):
        """Start the background watcher thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("DocumentWatcher already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("DocumentWatcher started")

    def stop(self):
        """Stop the background watcher thread."""
        if not self._thread or not self._thread.is_alive():
            logger.warning("DocumentWatcher not running")
            return

        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("DocumentWatcher stopped")

    def _run(self):
        """Background thread main loop."""
        while not self._stop_event.is_set():
            try:
                self._check_schedules()
            except Exception as e:
                logger.error(f"Error in DocumentWatcher: {e}", exc_info=True)

            # Sleep with periodic wake-up checks
            for _ in range(int(self.check_interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _check_schedules(self):
        """Check if any scheduled documents need generation."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

        # Check weekly status report (Mondays at 9 AM)
        if self.schedule_weekly and self._should_generate_weekly(now):
            self._generate_weekly_status(now)

        # Check monthly summary (first day of month at 10 AM)
        if self.schedule_monthly and self._should_generate_monthly(now):
            self._generate_monthly_summary(now)

    def _should_generate_weekly(self, now: datetime) -> bool:
        """Check if weekly status report should be generated."""
        # Check if it's Monday
        if now.weekday() != 0:  # 0 = Monday
            return False

        # Check if it's 9 AM or later
        if now.hour < 9:
            return False

        # Check if we already generated this week
        if self.last_weekly_generation:
            # If we generated in the last 6 days, skip
            if (now - self.last_weekly_generation).days < 6:
                return False

        return True

    def _should_generate_monthly(self, now: datetime) -> bool:
        """Check if monthly summary should be generated."""
        # Check if it's the first day of the month
        if now.day != 1:
            return False

        # Check if it's 10 AM or later
        if now.hour < 10:
            return False

        # Check if we already generated this month
        if self.last_monthly_generation:
            # If we generated in the last 28 days, skip
            if (now - self.last_monthly_generation).days < 28:
                return False

        return True

    def _generate_weekly_status(self, now: datetime):
        """Generate weekly status report."""
        try:
            # Get last Monday
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            logger.info(f"Generating weekly status report for week of {week_start}")

            # Generate document
            doc, file_path = self.document_service.generate_weekly_status(
                week_start=week_start,
                encrypt=self.encrypt_documents
            )

            # Update last generation time
            self.last_weekly_generation = now

            # Log to audit
            self.document_service.audit_service.log_action(
                action="document_generated",
                details=f"Weekly status report: {doc.title}",
                outcome="success",
                metadata={
                    "document_id": doc.document_id,
                    "file_path": str(file_path),
                    "document_type": doc.document_type
                }
            )

            logger.info(f"Weekly status report generated: {file_path}")

        except Exception as e:
            logger.error(f"Failed to generate weekly status report: {e}", exc_info=True)

            # Log failure to audit
            self.document_service.audit_service.log_action(
                action="document_generation_failed",
                details=f"Weekly status report failed: {str(e)}",
                outcome="failure"
            )

    def _generate_monthly_summary(self, now: datetime):
        """Generate monthly summary report."""
        try:
            # Get last month
            last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)

            logger.info(f"Generating monthly summary for {last_month.strftime('%B %Y')}")

            # Generate document
            doc, file_path = self.document_service.generate_monthly_summary(
                month=last_month,
                encrypt=self.encrypt_documents
            )

            # Update last generation time
            self.last_monthly_generation = now

            # Log to audit
            self.document_service.audit_service.log_action(
                action="document_generated",
                details=f"Monthly summary: {doc.title}",
                outcome="success",
                metadata={
                    "document_id": doc.document_id,
                    "file_path": str(file_path),
                    "document_type": doc.document_type
                }
            )

            logger.info(f"Monthly summary generated: {file_path}")

        except Exception as e:
            logger.error(f"Failed to generate monthly summary: {e}", exc_info=True)

            # Log failure to audit
            self.document_service.audit_service.log_action(
                action="document_generation_failed",
                details=f"Monthly summary failed: {str(e)}",
                outcome="failure"
            )

    def generate_now(self, document_type: str = "weekly") -> Optional[Path]:
        """
        Manually trigger document generation (for testing/debugging).

        Args:
            document_type: Type of document to generate ("weekly" or "monthly")

        Returns:
            Path to generated document, or None if failed
        """
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

        try:
            if document_type == "weekly":
                doc, file_path = self.document_service.generate_weekly_status(
                    week_start=now - timedelta(days=now.weekday()),
                    encrypt=self.encrypt_documents
                )
                self.last_weekly_generation = now
                return file_path

            elif document_type == "monthly":
                last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                doc, file_path = self.document_service.generate_monthly_summary(
                    month=last_month,
                    encrypt=self.encrypt_documents
                )
                self.last_monthly_generation = now
                return file_path

            else:
                logger.error(f"Unknown document type: {document_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate {document_type} document: {e}", exc_info=True)
            return None
