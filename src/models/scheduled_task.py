#!/usr/bin/env python3
"""
ScheduledTask Model - Silver Tier US4

Represents a scheduled task for time-based automation (daily briefings,
weekly summaries, custom tasks). Uses APScheduler CronTrigger for scheduling.

Contract: specs/002-silver-tier-upgrade/contracts/scheduled-task-schema.json
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
import yaml

try:
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    print("WARNING: APScheduler not installed. Install with: uv pip install apscheduler")
    CronTrigger = None


class TaskType(str, Enum):
    """Scheduled task types."""
    DAILY_BRIEFING = "daily_briefing"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_REPORT = "monthly_report"  # Platinum Tier US5 - Financial reports
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Task execution status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    RUNNING = "running"
    FAILED = "failed"


@dataclass
class ScheduledTask:
    """
    Scheduled task for automated execution.

    Tasks are defined in Company_Handbook.md and loaded by SchedulerService.
    Supports cron-based scheduling with APScheduler.
    """

    task_id: str  # Unique task identifier (e.g., "daily_briefing_001")
    task_name: str  # Human-readable name (e.g., "Morning Briefing")
    task_type: TaskType  # Type of task
    schedule_pattern: str  # Cron expression (e.g., "0 9 * * *" = 9 AM daily)
    recurrence_rule: Optional[str] = None  # Human-readable recurrence (e.g., "Daily at 9:00 AM")
    last_execution: Optional[str] = None  # ISO 8601 timestamp of last run
    next_execution: Optional[str] = None  # ISO 8601 timestamp of next run
    enabled: bool = True  # Whether task is active
    output_path: str = "Needs_Action"  # Folder to create output (relative to vault)
    parameters: Dict[str, Any] = field(default_factory=dict)  # Task-specific parameters
    created_at: Optional[str] = None  # ISO 8601 timestamp
    updated_at: Optional[str] = None  # ISO 8601 timestamp

    @classmethod
    def create(
        cls,
        task_id: str,
        task_name: str,
        task_type: TaskType,
        schedule_pattern: str,
        recurrence_rule: Optional[str] = None,
        enabled: bool = True,
        output_path: str = "Needs_Action",
        parameters: Optional[Dict[str, Any]] = None
    ) -> 'ScheduledTask':
        """
        Create a new ScheduledTask instance.

        Args:
            task_id: Unique task identifier
            task_name: Human-readable name
            task_type: Type of task
            schedule_pattern: Cron expression
            recurrence_rule: Human-readable recurrence description
            enabled: Whether task is active
            output_path: Output folder (relative to vault)
            parameters: Task-specific parameters

        Returns:
            ScheduledTask instance
        """
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        task = cls(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            schedule_pattern=schedule_pattern,
            recurrence_rule=recurrence_rule,
            last_execution=None,
            next_execution=None,
            enabled=enabled,
            output_path=output_path,
            parameters=parameters or {},
            created_at=now,
            updated_at=now
        )

        # Calculate next execution time
        task.calculate_next_execution()

        return task

    def calculate_next_execution(
        self,
        start_date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Calculate next execution time using APScheduler CronTrigger.

        Updates the next_execution field with calculated time.

        Args:
            start_date: Calculate from this date (defaults to now)

        Returns:
            ISO 8601 timestamp of next execution, or None if calculation fails
        """
        if not CronTrigger:
            # APScheduler not installed - fallback to simple calculation
            return self._calculate_next_execution_fallback(start_date)

        try:
            # Parse cron expression
            trigger = CronTrigger.from_crontab(self.schedule_pattern)

            # Get next fire time
            if start_date is None:
                start_date = datetime.now(timezone.utc)

            next_fire_time = trigger.get_next_fire_time(None, start_date)

            if next_fire_time:
                # Convert to ISO 8601
                self.next_execution = next_fire_time.isoformat().replace('+00:00', 'Z')
                return self.next_execution
            else:
                self.next_execution = None
                return None

        except Exception as e:
            print(f"Error calculating next execution for {self.task_id}: {e}")
            return self._calculate_next_execution_fallback(start_date)

    def _calculate_next_execution_fallback(
        self,
        start_date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Fallback calculation for common cron patterns.

        Handles simple patterns like:
        - "0 9 * * *" (daily at 9 AM)
        - "0 9 * * 1" (weekly on Monday at 9 AM)
        - "*/15 * * * *" (every 15 minutes)

        Args:
            start_date: Calculate from this date (defaults to now)

        Returns:
            ISO 8601 timestamp of next execution
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc)

        # Parse basic cron patterns
        parts = self.schedule_pattern.split()
        if len(parts) != 5:
            # Invalid cron format
            return None

        minute, hour, day, month, weekday = parts

        # Handle simple daily pattern: "0 9 * * *" (9 AM daily)
        if minute.isdigit() and hour.isdigit() and day == '*' and month == '*' and weekday == '*':
            target_hour = int(hour)
            target_minute = int(minute)

            # Calculate next occurrence
            next_time = start_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

            # If time has passed today, move to tomorrow
            if next_time <= start_date:
                next_time += timedelta(days=1)

            self.next_execution = next_time.isoformat().replace('+00:00', 'Z')
            return self.next_execution

        # Handle every N minutes: "*/15 * * * *" (every 15 minutes)
        if minute.startswith('*/') and hour == '*':
            interval = int(minute[2:])
            next_time = start_date + timedelta(minutes=interval)
            # Round to next interval
            minutes_since_hour = next_time.minute
            minutes_until_next = interval - (minutes_since_hour % interval)
            next_time += timedelta(minutes=minutes_until_next)
            next_time = next_time.replace(second=0, microsecond=0)

            self.next_execution = next_time.isoformat().replace('+00:00', 'Z')
            return self.next_execution

        # For complex patterns, default to 24 hours from now
        next_time = start_date + timedelta(days=1)
        self.next_execution = next_time.isoformat().replace('+00:00', 'Z')
        return self.next_execution

    def mark_executed(self, execution_time: Optional[datetime] = None):
        """
        Mark task as executed and calculate next execution time.

        Args:
            execution_time: Time of execution (defaults to now)
        """
        if execution_time is None:
            execution_time = datetime.now(timezone.utc)

        self.last_execution = execution_time.isoformat().replace('+00:00', 'Z')
        self.updated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Calculate next execution from the execution time
        self.calculate_next_execution(execution_time)

    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if task is due for execution.

        Args:
            current_time: Check against this time (defaults to now)

        Returns:
            True if task should be executed now
        """
        if not self.enabled:
            return False

        if not self.next_execution:
            return False

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        next_exec_time = datetime.fromisoformat(self.next_execution.replace('Z', '+00:00'))

        return current_time >= next_exec_time

    def was_missed(
        self,
        current_time: Optional[datetime] = None,
        grace_period_minutes: int = 60
    ) -> bool:
        """
        Check if task execution was missed.

        A task is considered missed if:
        - next_execution is in the past
        - More than grace_period_minutes have passed since next_execution
        - Task is still enabled

        Args:
            current_time: Check against this time (defaults to now)
            grace_period_minutes: Grace period in minutes (default: 60)

        Returns:
            True if task execution was missed
        """
        if not self.enabled:
            return False

        if not self.next_execution:
            return False

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        next_exec_time = datetime.fromisoformat(self.next_execution.replace('Z', '+00:00'))
        grace_period = timedelta(minutes=grace_period_minutes)

        # Missed if next_execution + grace_period < current_time
        return (next_exec_time + grace_period) < current_time

    def disable(self):
        """Disable task execution."""
        self.enabled = False
        self.updated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def enable(self):
        """Enable task execution and recalculate next execution."""
        self.enabled = True
        self.updated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.calculate_next_execution()

    def to_yaml(self) -> str:
        """
        Convert to YAML format for Company_Handbook.md.

        Returns:
            YAML string representation
        """
        data = {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'task_type': self.task_type.value if isinstance(self.task_type, TaskType) else self.task_type,
            'schedule_pattern': self.schedule_pattern,
            'enabled': self.enabled,
            'output_path': self.output_path
        }

        if self.recurrence_rule:
            data['recurrence_rule'] = self.recurrence_rule

        if self.last_execution:
            data['last_execution'] = self.last_execution

        if self.next_execution:
            data['next_execution'] = self.next_execution

        if self.parameters:
            data['parameters'] = self.parameters

        if self.created_at:
            data['created_at'] = self.created_at

        if self.updated_at:
            data['updated_at'] = self.updated_at

        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_data: Dict[str, Any]) -> 'ScheduledTask':
        """
        Create ScheduledTask from YAML data.

        Args:
            yaml_data: Parsed YAML dictionary

        Returns:
            ScheduledTask instance
        """
        # Parse task_type enum
        task_type_str = yaml_data.get('task_type', 'custom')
        task_type = TaskType(task_type_str)

        return cls(
            task_id=yaml_data['task_id'],
            task_name=yaml_data['task_name'],
            task_type=task_type,
            schedule_pattern=yaml_data['schedule_pattern'],
            recurrence_rule=yaml_data.get('recurrence_rule'),
            last_execution=yaml_data.get('last_execution'),
            next_execution=yaml_data.get('next_execution'),
            enabled=yaml_data.get('enabled', True),
            output_path=yaml_data.get('output_path', 'Needs_Action'),
            parameters=yaml_data.get('parameters', {}),
            created_at=yaml_data.get('created_at'),
            updated_at=yaml_data.get('updated_at')
        )

    def validate(self):
        """
        Validate task configuration.

        Raises:
            ValueError: If validation fails
        """
        if not self.task_id:
            raise ValueError("task_id is required")

        if not self.task_name:
            raise ValueError("task_name is required")

        if not self.schedule_pattern:
            raise ValueError("schedule_pattern is required")

        # Validate cron pattern (basic check: 5 parts)
        parts = self.schedule_pattern.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron pattern '{self.schedule_pattern}' - "
                f"must have 5 parts (minute hour day month weekday)"
            )

        if self.task_type not in TaskType:
            raise ValueError(f"Invalid task_type: {self.task_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'task_type': self.task_type.value if isinstance(self.task_type, TaskType) else self.task_type,
            'schedule_pattern': self.schedule_pattern,
            'recurrence_rule': self.recurrence_rule,
            'last_execution': self.last_execution,
            'next_execution': self.next_execution,
            'enabled': self.enabled,
            'output_path': self.output_path,
            'parameters': self.parameters,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __str__(self) -> str:
        """String representation."""
        status = "enabled" if self.enabled else "disabled"
        return (
            f"ScheduledTask({self.task_id}, {self.task_name}, "
            f"{self.schedule_pattern}, {status})"
        )
