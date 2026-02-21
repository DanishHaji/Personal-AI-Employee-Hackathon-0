"""
DashboardSummary Model for Personal AI Employee - Bronze Tier MVP

Represents real-time system state summary displayed in Dashboard.md
Implements Entity 4 from data-model.md

Attributes:
    last_updated: Last refresh timestamp (ISO 8601)
    pending_actions_count: Items in /Needs_Action (>= 0)
    pending_approvals_count: Items in /Pending_Approval (>= 0)
    system_health: Overall health status ("healthy", "degraded", "down")
    recent_activity: Last 5 actions (list of Activity objects)
    watchers_status: Watcher health checks (dict of WatcherStatus)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Literal
from enum import Enum


class SystemHealth(str, Enum):
    """System health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    NOT_STARTED = "not_started"


class WatcherStatus(str, Enum):
    """Watcher status enum."""
    RUNNING = "running"
    STALE = "stale"
    STOPPED = "stopped"
    NOT_STARTED = "not_started"


@dataclass
class Activity:
    """Recent activity entry."""
    timestamp: datetime
    action: str  # What happened (verb + object)
    target: str  # File/entity affected


@dataclass
class Watcher:
    """Watcher health status."""
    name: str
    status: WatcherStatus
    last_check: datetime | None = None


@dataclass
class DashboardSummary:
    """Dashboard summary model for rendering Dashboard.md."""

    last_updated: datetime
    pending_actions_count: int
    pending_approvals_count: int
    system_health: SystemHealth
    recent_activity: List[Activity]
    watchers_status: Dict[str, Watcher]

    def to_markdown(self) -> str:
        """
        Generate complete Dashboard.md content.

        Format matches Contract 4 from contracts/file-interfaces.md

        Returns:
            str: Complete markdown content for Dashboard.md
        """
        # Format health status with emoji
        health_icons = {
            SystemHealth.HEALTHY: "✅ Healthy",
            SystemHealth.DEGRADED: "⚠️ Degraded",
            SystemHealth.DOWN: "❌ Down",
            SystemHealth.NOT_STARTED: "⚙️ Not Started",
        }
        health_display = health_icons.get(self.system_health, str(self.system_health))

        # Format recent activity (max 5 items)
        activity_lines = []
        for i, activity in enumerate(self.recent_activity[:5], 1):
            time_str = activity.timestamp.strftime("%H:%M")
            activity_lines.append(
                f"{i}. [{time_str}] {activity.action} → {activity.target}"
            )

        # Fill with placeholders if less than 5 activities
        while len(activity_lines) < 5:
            activity_lines.append(f"{len(activity_lines) + 1}. No activity yet")

        # Format watcher statuses
        watcher_lines = []
        for watcher_name, watcher in self.watchers_status.items():
            icon = self._get_watcher_icon(watcher.status)
            last_check = "N/A"
            if watcher.last_check:
                last_check = watcher.last_check.strftime("%H:%M")

            display_name = watcher_name.replace("_", " ").title()
            watcher_lines.append(
                f"- **{display_name}**: {icon} {watcher.status.value.title()} "
                f"(last check: {last_check})"
            )

        markdown_content = f"""# AI Employee Dashboard

**Last Updated**: {self.last_updated.strftime('%Y-%m-%d %H:%M:%S')}

## Status Overview

- **Pending Actions**: {self.pending_actions_count} items
- **Pending Approvals**: {self.pending_approvals_count} items
- **System Health**: {health_display}

## Recent Activity

{chr(10).join(activity_lines)}

## Watchers Status

{chr(10).join(watcher_lines)}

---

*This dashboard is automatically updated by the AI Employee system*
"""
        return markdown_content

    def _get_watcher_icon(self, status: WatcherStatus) -> str:
        """
        Get emoji icon for watcher status.

        Args:
            status: Watcher status

        Returns:
            str: Emoji icon
        """
        icons = {
            WatcherStatus.RUNNING: "✅",
            WatcherStatus.STALE: "⚠️",
            WatcherStatus.STOPPED: "❌",
            WatcherStatus.NOT_STARTED: "⚙️",
        }
        return icons.get(status, "❓")

    def calculate_system_health(self) -> SystemHealth:
        """
        Calculate overall system health based on watcher statuses.

        Logic from Contract 4:
        - ✅ Healthy: All watchers running (heartbeat within last 5 minutes)
        - ⚠️ Degraded: Some watchers stale (heartbeat 5-15 minutes old)
        - ❌ Down: All watchers stopped (no heartbeat in 15+ minutes)

        Returns:
            SystemHealth: Calculated health status
        """
        if not self.watchers_status:
            return SystemHealth.NOT_STARTED

        running_count = sum(
            1 for w in self.watchers_status.values()
            if w.status == WatcherStatus.RUNNING
        )
        stopped_count = sum(
            1 for w in self.watchers_status.values()
            if w.status == WatcherStatus.STOPPED
        )
        total_count = len(self.watchers_status)

        # All running = healthy
        if running_count == total_count:
            return SystemHealth.HEALTHY

        # All stopped = down
        if stopped_count == total_count:
            return SystemHealth.DOWN

        # Some running, some not = degraded
        return SystemHealth.DEGRADED

    @classmethod
    def determine_watcher_status(
        cls,
        heartbeat_timestamp: datetime | None,
        current_time: datetime
    ) -> WatcherStatus:
        """
        Determine watcher status based on heartbeat timestamp.

        Logic from Contract 5:
        - Fresh: timestamp within last 5 minutes → RUNNING
        - Stale: timestamp 5-15 minutes old → STALE
        - Dead: timestamp 15+ minutes old or None → STOPPED

        Args:
            heartbeat_timestamp: Last heartbeat timestamp
            current_time: Current time for comparison

        Returns:
            WatcherStatus: Determined status
        """
        if heartbeat_timestamp is None:
            return WatcherStatus.NOT_STARTED

        age_seconds = (current_time - heartbeat_timestamp).total_seconds()

        if age_seconds < 5 * 60:  # < 5 minutes
            return WatcherStatus.RUNNING
        elif age_seconds < 15 * 60:  # 5-15 minutes
            return WatcherStatus.STALE
        else:  # > 15 minutes
            return WatcherStatus.STOPPED

    def validate(self) -> bool:
        """
        Validate DashboardSummary attributes.

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        # Validate counts (must be >= 0)
        if self.pending_actions_count < 0:
            raise ValueError(
                f"pending_actions_count must be >= 0: {self.pending_actions_count}"
            )

        if self.pending_approvals_count < 0:
            raise ValueError(
                f"pending_approvals_count must be >= 0: {self.pending_approvals_count}"
            )

        # Validate recent_activity (max 5 items per data-model.md)
        if len(self.recent_activity) > 5:
            raise ValueError(
                f"recent_activity limited to 5 items: {len(self.recent_activity)}"
            )

        return True
