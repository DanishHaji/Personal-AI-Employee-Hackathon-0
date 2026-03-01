"""
Analytics Engine - Gold Tier US4

Schedules weekly analytics generation every Friday at 5 PM.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading

from src.services.analytics_service import AnalyticsService
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Background engine for scheduled analytics generation.

    Generates weekly insights every Friday at 5:00 PM.
    """

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 3600,  # 1 hour
        generate_hour: int = 17,  # 5 PM
        generate_day: int = 4  # Friday (0=Monday, 4=Friday)
    ):
        """
        Initialize AnalyticsEngine.

        Args:
            vault_path: Path to Obsidian vault
            check_interval: How often to check schedule (seconds, default: 1 hour)
            generate_hour: Hour of day to generate (0-23, default: 17 for 5 PM)
            generate_day: Day of week to generate (0=Monday, 4=Friday)
        """
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.generate_hour = generate_hour
        self.generate_day = generate_day

        # Initialize services
        self.analytics_service = AnalyticsService(vault_path=vault_path)
        self.audit_service = AuditService(vault_path=vault_path)

        # Track last generation time
        self.last_generation: Optional[datetime] = None

        # Background thread
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        logger.info(
            f"AnalyticsEngine initialized (day={generate_day}, hour={generate_hour}, "
            f"interval={check_interval}s)"
        )

    def start(self):
        """Start the background analytics engine thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("AnalyticsEngine already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("AnalyticsEngine started")

    def stop(self):
        """Stop the background analytics engine thread."""
        if not self._thread or not self._thread.is_alive():
            logger.warning("AnalyticsEngine not running")
            return

        self._stop_event.set()
        self._thread.join(timeout=5)
        logger.info("AnalyticsEngine stopped")

    def _run(self):
        """Background thread main loop."""
        while not self._stop_event.is_set():
            try:
                self._check_schedule()
            except Exception as e:
                logger.error(f"Error in AnalyticsEngine: {e}", exc_info=True)

            # Sleep with periodic wake-up checks
            for _ in range(int(self.check_interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _check_schedule(self):
        """Check if weekly insights should be generated."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

        if self._should_generate(now):
            self._generate_weekly_insight(now)

    def _should_generate(self, now: datetime) -> bool:
        """Check if weekly insight should be generated."""
        # Check if it's the correct day of week
        if now.weekday() != self.generate_day:
            return False

        # Check if it's the correct hour or later
        if now.hour < self.generate_hour:
            return False

        # Check if we already generated this week
        if self.last_generation:
            # If we generated in the last 6 days, skip
            if (now - self.last_generation).days < 6:
                return False

        return True

    def _generate_weekly_insight(self, now: datetime):
        """Generate weekly insight."""
        try:
            # Get last Monday
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            logger.info(f"Generating weekly insight for week of {week_start}")

            # Generate insight
            insight, file_path = self.analytics_service.generate_weekly_insight(
                week_start=week_start
            )

            # Update last generation time
            self.last_generation = now

            # Log to audit
            self.audit_service.log_action(
                action="analytics_generated",
                details=f"Weekly insight: {insight.insight_id}",
                outcome="success",
                metadata={
                    "insight_id": insight.insight_id,
                    "file_path": str(file_path),
                    "total_recommendations": len(insight.recommendations),
                    "high_priority_count": len(insight.get_high_priority_recommendations())
                }
            )

            # Create alerts for high-priority recommendations
            self._create_alerts(insight)

            logger.info(f"Weekly insight generated: {file_path}")

        except Exception as e:
            logger.error(f"Failed to generate weekly insight: {e}", exc_info=True)

            # Log failure to audit
            self.audit_service.log_action(
                action="analytics_generation_failed",
                details=f"Weekly insight generation failed: {str(e)}",
                outcome="failure"
            )

    def _create_alerts(self, insight):
        """Create alerts for high-priority recommendations."""
        high_priority = insight.get_high_priority_recommendations()

        if not high_priority:
            return

        # Create Needs_Action directory if it doesn't exist
        needs_action_dir = Path(self.vault_path) / "Needs_Action"
        needs_action_dir.mkdir(parents=True, exist_ok=True)

        # Create alert file
        for rec in high_priority:
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in rec.recommendation[:50])
            safe_title = safe_title.replace(' ', '_')

            alert_file = needs_action_dir / f"INSIGHT_{insight.week_start.strftime('%Y_%m_%d')}_{safe_title}.md"

            # Build alert content
            content = f"""# {rec.recommendation}

**Priority:** {rec.priority.upper()}
**Category:** {rec.category}
**Generated:** {insight.generated_at.strftime('%Y-%m-%d %H:%M UTC')}

## Rationale

{rec.rationale}

## Action Items

"""
            for item in rec.action_items:
                content += f"- [ ] {item}\n"

            content += f"""
## Related Insight

See full weekly insight at: `/Insights/{insight.week_start.strftime('%Y-%m-%d')}.json`

---

*This alert was automatically generated by the Analytics Engine.*
"""

            alert_file.write_text(content, encoding='utf-8')
            logger.info(f"Created alert: {alert_file}")

    def generate_now(self) -> Optional[Path]:
        """
        Manually trigger weekly insight generation (for testing/debugging).

        Returns:
            Path to generated insight file, or None if failed
        """
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

        try:
            week_start = now - timedelta(days=now.weekday())
            insight, file_path = self.analytics_service.generate_weekly_insight(
                week_start=week_start
            )
            self.last_generation = now
            self._create_alerts(insight)
            return file_path

        except Exception as e:
            logger.error(f"Failed to generate weekly insight: {e}", exc_info=True)
            return None
