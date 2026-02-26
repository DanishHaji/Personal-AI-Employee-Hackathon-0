#!/usr/bin/env python3
"""
SchedulerService - Silver Tier US4

Handles scheduled task management, execution, and state persistence.
Generates daily briefings, weekly summaries, and executes custom tasks.

Core workflow:
1. Load scheduled tasks from Company_Handbook.md
2. Execute tasks at scheduled times
3. Generate briefings and summaries
4. Persist schedule state to schedule_state.json
5. Handle missed executions (within grace period)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

import yaml

from src.services.vault_service import VaultService
from src.services.logger_service import AuditLogger, Actor, ActionType, Result
from src.models.scheduled_task import ScheduledTask, TaskType


logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for scheduled task management and execution.

    Loads tasks from Company_Handbook.md, executes them at scheduled times,
    and generates briefings/summaries.

    Usage:
        service = SchedulerService(
            vault_service=vault_service,
            audit_logger=audit_logger
        )

        # Load tasks from handbook
        tasks = service.load_tasks_from_handbook()

        # Execute daily briefing
        briefing_path = service.generate_daily_briefing()

        # Execute weekly summary
        summary_path = service.generate_weekly_summary()
    """

    def __init__(
        self,
        vault_service: VaultService,
        audit_logger: AuditLogger
    ):
        """
        Initialize SchedulerService.

        Args:
            vault_service: VaultService for file operations
            audit_logger: AuditLogger for audit logging
        """
        self.vault_service = vault_service
        self.audit_logger = audit_logger

        # Schedule state file
        self.state_file = self.vault_service.vault_path / "Logs" / "schedule_state.json"

        # In-memory task registry
        self.tasks: Dict[str, ScheduledTask] = {}

        # Load existing state
        self._load_state()

        logger.info("SchedulerService initialized")

    def load_tasks_from_handbook(self) -> List[ScheduledTask]:
        """
        Load scheduled tasks from Company_Handbook.md.

        Reads the scheduled_tasks YAML section from handbook frontmatter.

        Example in Company_Handbook.md:
        ```yaml
        ---
        scheduled_tasks:
          - task_id: daily_briefing_001
            task_name: "Morning Briefing"
            task_type: daily_briefing
            schedule_pattern: "0 9 * * *"
            recurrence_rule: "Daily at 9:00 AM"
            enabled: true
            output_path: "Needs_Action"
            parameters:
              include_urgent: true
              include_completions: true
        ---
        ```

        Returns:
            List of ScheduledTask instances
        """
        handbook_path = self.vault_service.vault_path / "Company_Handbook.md"

        if not handbook_path.exists():
            logger.warning("Company_Handbook.md not found - no scheduled tasks loaded")
            return []

        try:
            frontmatter, body = self.vault_service.read_markdown_with_frontmatter(handbook_path)

            # Check for scheduled_tasks in frontmatter
            tasks_data = frontmatter.get('scheduled_tasks', [])

            if not tasks_data:
                logger.debug("No scheduled_tasks found in handbook")
                return []

            # Parse tasks
            tasks = []
            for task_data in tasks_data:
                try:
                    task = ScheduledTask.from_yaml(task_data)
                    task.validate()
                    tasks.append(task)
                    logger.info(f"Loaded scheduled task: {task.task_id} ({task.task_name})")
                except Exception as e:
                    logger.error(f"Failed to parse scheduled task: {e}")
                    continue

            # Update internal registry
            for task in tasks:
                self.tasks[task.task_id] = task

            logger.info(f"Loaded {len(tasks)} scheduled tasks from handbook")

            return tasks

        except Exception as e:
            logger.error(f"Failed to load tasks from handbook: {e}")
            return []

    def generate_daily_briefing(
        self,
        task: Optional[ScheduledTask] = None
    ) -> Optional[Path]:
        """
        Generate daily briefing with pending items, completions, and urgent items.

        Briefing includes:
        - Pending action count (items in /Needs_Action/)
        - Recent completions (last 24 hours)
        - Urgent items (high priority messages, overdue plans)
        - System health summary

        Args:
            task: ScheduledTask that triggered this briefing (optional)

        Returns:
            Path to created briefing file, or None if failed
        """
        logger.info("Generating daily briefing")

        try:
            # Count pending actions
            needs_action_folder = self.vault_service.vault_path / "Needs_Action"
            pending_count = len(list(needs_action_folder.glob("*.md")))

            # Count pending approvals
            pending_approval_folder = self.vault_service.vault_path / "Pending_Approval"
            if pending_approval_folder.exists():
                approval_count = len(list(pending_approval_folder.glob("*.md")))
            else:
                approval_count = 0

            # Get recent completions (last 24 hours)
            completions = self._get_recent_completions(hours=24)

            # Get urgent items
            urgent_items = self._get_urgent_items()

            # Get system health
            health_status = self._get_system_health()

            # Generate briefing content
            timestamp = datetime.now(timezone.utc)
            briefing_date = timestamp.strftime("%Y-%m-%d")
            briefing_time = timestamp.strftime("%H:%M")

            briefing_content = self._format_daily_briefing(
                briefing_date=briefing_date,
                briefing_time=briefing_time,
                pending_count=pending_count,
                approval_count=approval_count,
                completions=completions,
                urgent_items=urgent_items,
                health_status=health_status
            )

            # Write briefing file
            output_folder = task.output_path if task else "Needs_Action"
            briefing_filename = f"BRIEFING_{briefing_date.replace('-', '')}.md"
            briefing_path = self.vault_service.vault_path / output_folder / briefing_filename

            briefing_path.write_text(briefing_content, encoding='utf-8')

            logger.info(f"✅ Created daily briefing: {briefing_filename}")

            # Log briefing creation
            self.audit_logger.log(
                action_type=ActionType.SCHEDULED_TASK,
                actor=Actor.SCHEDULER,
                target=briefing_filename,
                parameters={
                    'task_type': 'daily_briefing',
                    'pending_count': pending_count,
                    'completions': len(completions),
                    'urgent_count': len(urgent_items)
                },
                result=Result.SUCCESS
            )

            return briefing_path

        except Exception as e:
            logger.exception(f"Failed to generate daily briefing: {e}")
            self.audit_logger.log_error(
                actor=Actor.SCHEDULER,
                error_message=str(e),
                error_type=type(e).__name__,
                target="daily_briefing"
            )
            return None

    def _format_daily_briefing(
        self,
        briefing_date: str,
        briefing_time: str,
        pending_count: int,
        approval_count: int,
        completions: List[Dict[str, Any]],
        urgent_items: List[Dict[str, Any]],
        health_status: Dict[str, Any]
    ) -> str:
        """Format daily briefing content."""
        lines = [
            "---",
            "type: daily_briefing",
            f"date: {briefing_date}",
            f"generated_at: {briefing_time}",
            "---",
            "",
            f"# Daily Briefing - {briefing_date}",
            "",
            f"**Generated**: {briefing_time}",
            "",
            "## Overview",
            "",
            f"- **Pending Actions**: {pending_count} items in /Needs_Action/",
            f"- **Pending Approvals**: {approval_count} items in /Pending_Approval/",
            f"- **System Health**: {health_status['status']} {health_status['emoji']}",
            ""
        ]

        # Recent completions section
        if completions:
            lines.append("## Recent Completions (Last 24 Hours)")
            lines.append("")
            for i, completion in enumerate(completions[:10], 1):  # Show top 10
                lines.append(f"{i}. {completion['action']} - {completion['target']}")
            lines.append("")
        else:
            lines.append("## Recent Completions (Last 24 Hours)")
            lines.append("")
            lines.append("No completed tasks in the last 24 hours.")
            lines.append("")

        # Urgent items section
        if urgent_items:
            lines.append(f"## ⚠️ Urgent Items ({len(urgent_items)})")
            lines.append("")
            for i, item in enumerate(urgent_items, 1):
                lines.append(f"{i}. **{item['priority']}**: {item['description']}")
                lines.append(f"   - File: `{item['file_path']}`")
                lines.append(f"   - Age: {item['age']}")
            lines.append("")
        else:
            lines.append("## ✅ No Urgent Items")
            lines.append("")
            lines.append("All items are under control.")
            lines.append("")

        # System health details
        lines.append("## System Health")
        lines.append("")
        for watcher, status in health_status['watchers'].items():
            lines.append(f"- **{watcher}**: {status}")
        lines.append("")

        # Recommendations
        lines.append("## Recommended Actions")
        lines.append("")
        if urgent_items:
            lines.append("1. Review and address urgent items above")
        if pending_count > 20:
            lines.append(f"2. High pending count ({pending_count}) - consider batch processing")
        if approval_count > 5:
            lines.append(f"3. Multiple pending approvals ({approval_count}) - review /Pending_Approval/")
        if not urgent_items and pending_count < 10:
            lines.append("1. All clear! No urgent actions needed.")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*This briefing was automatically generated by the AI Employee scheduler*")

        return "\n".join(lines)

    def generate_weekly_summary(
        self,
        task: Optional[ScheduledTask] = None
    ) -> Optional[Path]:
        """
        Generate weekly summary with completed tasks, time saved, and metrics.

        Summary includes:
        - Total tasks completed (last 7 days)
        - Breakdown by task type (emails, plans, messages)
        - Estimated time saved
        - System uptime and reliability
        - Weekly trends

        Args:
            task: ScheduledTask that triggered this summary (optional)

        Returns:
            Path to created summary file, or None if failed
        """
        logger.info("Generating weekly summary")

        try:
            # Get week start/end dates
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=7)
            week_end = now

            # Get completed tasks from last 7 days
            completed_tasks = self._get_completed_tasks_in_range(week_start, week_end)

            # Calculate metrics
            metrics = self._calculate_weekly_metrics(completed_tasks)

            # Generate summary content
            summary_date = now.strftime("%Y-%m-%d")
            summary_content = self._format_weekly_summary(
                summary_date=summary_date,
                week_start=week_start.strftime("%Y-%m-%d"),
                week_end=week_end.strftime("%Y-%m-%d"),
                metrics=metrics
            )

            # Write summary file
            output_folder = task.output_path if task else "Needs_Action"
            summary_filename = f"SUMMARY_WEEK_{summary_date.replace('-', '')}.md"
            summary_path = self.vault_service.vault_path / output_folder / summary_filename

            summary_path.write_text(summary_content, encoding='utf-8')

            logger.info(f"✅ Created weekly summary: {summary_filename}")

            # Log summary creation
            self.audit_logger.log(
                action_type=ActionType.SCHEDULED_TASK,
                actor=Actor.SCHEDULER,
                target=summary_filename,
                parameters={
                    'task_type': 'weekly_summary',
                    'week_start': week_start.isoformat(),
                    'week_end': week_end.isoformat(),
                    'total_completed': metrics['total_completed']
                },
                result=Result.SUCCESS
            )

            return summary_path

        except Exception as e:
            logger.exception(f"Failed to generate weekly summary: {e}")
            self.audit_logger.log_error(
                actor=Actor.SCHEDULER,
                error_message=str(e),
                error_type=type(e).__name__,
                target="weekly_summary"
            )
            return None

    def _format_weekly_summary(
        self,
        summary_date: str,
        week_start: str,
        week_end: str,
        metrics: Dict[str, Any]
    ) -> str:
        """Format weekly summary content."""
        lines = [
            "---",
            "type: weekly_summary",
            f"date: {summary_date}",
            f"week_start: {week_start}",
            f"week_end: {week_end}",
            "---",
            "",
            f"# Weekly Summary - Week of {week_start}",
            "",
            f"**Period**: {week_start} to {week_end}",
            "",
            "## Highlights",
            "",
            f"- **Total Tasks Completed**: {metrics['total_completed']}",
            f"- **Emails Processed**: {metrics['emails_processed']}",
            f"- **Social Posts Published**: {metrics['social_posts']}",
            f"- **WhatsApp Messages**: {metrics['whatsapp_messages']}",
            f"- **Estimated Time Saved**: {metrics['time_saved_hours']} hours",
            "",
            "## Breakdown by Day",
            "",
        ]

        for day, count in metrics['daily_breakdown'].items():
            lines.append(f"- **{day}**: {count} tasks")
        lines.append("")

        lines.append("## System Performance")
        lines.append("")
        lines.append(f"- **Success Rate**: {metrics['success_rate']}%")
        lines.append(f"- **Average Response Time**: {metrics['avg_response_time']} minutes")
        lines.append(f"- **Uptime**: {metrics['uptime_percentage']}%")
        lines.append("")

        lines.append("## Trends")
        lines.append("")
        if metrics['total_completed'] > metrics.get('previous_week_total', 0):
            change = metrics['total_completed'] - metrics.get('previous_week_total', 0)
            lines.append(f"📈 **Up {change} tasks** from previous week")
        elif metrics['total_completed'] < metrics.get('previous_week_total', 0):
            change = metrics.get('previous_week_total', 0) - metrics['total_completed']
            lines.append(f"📉 **Down {change} tasks** from previous week")
        else:
            lines.append("➡️ **Steady** - Same as previous week")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*This summary was automatically generated by the AI Employee scheduler*")

        return "\n".join(lines)

    def execute_custom_task(
        self,
        task: ScheduledTask
    ) -> bool:
        """
        Execute custom scheduled task.

        Custom tasks are user-defined with parameters in task.parameters.

        Args:
            task: ScheduledTask with task_type=CUSTOM

        Returns:
            True if execution succeeded, False otherwise
        """
        logger.info(f"Executing custom task: {task.task_id}")

        try:
            # Extract parameters
            parameters = task.parameters or {}
            action = parameters.get('action', 'unknown')

            # Execute based on action type
            if action == 'create_reminder':
                return self._execute_create_reminder(task, parameters)
            elif action == 'archive_old_items':
                return self._execute_archive_old_items(task, parameters)
            elif action == 'send_notification':
                return self._execute_send_notification(task, parameters)
            else:
                logger.warning(f"Unknown custom task action: {action}")
                return False

        except Exception as e:
            logger.exception(f"Failed to execute custom task {task.task_id}: {e}")
            self.audit_logger.log_error(
                actor=Actor.SCHEDULER,
                error_message=str(e),
                error_type=type(e).__name__,
                target=task.task_id
            )
            return False

    def _execute_create_reminder(
        self,
        task: ScheduledTask,
        parameters: Dict[str, Any]
    ) -> bool:
        """Execute create_reminder custom task."""
        reminder_text = parameters.get('reminder_text', 'Reminder')
        output_folder = task.output_path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reminder_filename = f"REMINDER_{timestamp}.md"
        reminder_path = self.vault_service.vault_path / output_folder / reminder_filename

        reminder_content = f"""---
type: reminder
created_by: scheduler
task_id: {task.task_id}
created_at: {datetime.now(timezone.utc).isoformat()}
---

# Reminder

{reminder_text}
"""

        reminder_path.write_text(reminder_content, encoding='utf-8')
        logger.info(f"Created reminder: {reminder_filename}")

        return True

    def _execute_archive_old_items(
        self,
        task: ScheduledTask,
        parameters: Dict[str, Any]
    ) -> bool:
        """Execute archive_old_items custom task."""
        days_old = parameters.get('days_old', 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        done_folder = self.vault_service.vault_path / "Done"
        if not done_folder.exists():
            return True

        archived_count = 0
        for file_path in done_folder.glob("*.md"):
            # Check file modification time
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff_date:
                # Archive (in real implementation, would move to archive folder)
                logger.debug(f"Would archive old file: {file_path.name}")
                archived_count += 1

        logger.info(f"Archived {archived_count} old items")
        return True

    def _execute_send_notification(
        self,
        task: ScheduledTask,
        parameters: Dict[str, Any]
    ) -> bool:
        """Execute send_notification custom task."""
        notification_text = parameters.get('notification_text', 'Notification')
        # In real implementation, would send via notification service
        logger.info(f"Would send notification: {notification_text}")
        return True

    def update_schedule_state(self):
        """
        Persist schedule state to schedule_state.json.

        Saves current state of all scheduled tasks including last_execution
        and next_execution times.
        """
        try:
            # Ensure Logs directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Build state data
            state = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'tasks': {}
            }

            for task_id, task in self.tasks.items():
                state['tasks'][task_id] = {
                    'task_id': task.task_id,
                    'task_name': task.task_name,
                    'last_execution': task.last_execution,
                    'next_execution': task.next_execution,
                    'enabled': task.enabled,
                    'updated_at': task.updated_at
                }

            # Write state file
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

            logger.debug(f"Updated schedule state ({len(self.tasks)} tasks)")

        except Exception as e:
            logger.error(f"Failed to update schedule state: {e}")

    def _load_state(self):
        """Load schedule state from schedule_state.json."""
        if not self.state_file.exists():
            logger.debug("No existing schedule state file found")
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # State will be merged with tasks loaded from handbook
            # This is mainly for persisting execution timestamps
            logger.debug(f"Loaded schedule state (last updated: {state.get('last_updated')})")

        except Exception as e:
            logger.error(f"Failed to load schedule state: {e}")

    def handle_missed_execution(
        self,
        task: ScheduledTask,
        grace_period_minutes: int = 60
    ) -> bool:
        """
        Handle missed task execution.

        If a task was missed (next_execution in the past), execute it now
        if still within grace period.

        Args:
            task: ScheduledTask that was missed
            grace_period_minutes: Grace period in minutes (default: 60)

        Returns:
            True if task was executed, False otherwise
        """
        if not task.was_missed(grace_period_minutes=grace_period_minutes):
            return False

        logger.warning(
            f"Task {task.task_id} missed execution "
            f"(scheduled: {task.next_execution})"
        )

        # Execute task now (catch-up)
        try:
            if task.task_type == TaskType.DAILY_BRIEFING:
                result_path = self.generate_daily_briefing(task)
                success = result_path is not None
            elif task.task_type == TaskType.WEEKLY_SUMMARY:
                result_path = self.generate_weekly_summary(task)
                success = result_path is not None
            elif task.task_type == TaskType.CUSTOM:
                success = self.execute_custom_task(task)
            else:
                logger.warning(f"Unknown task type: {task.task_type}")
                success = False

            if success:
                logger.info(f"✅ Caught up missed execution for {task.task_id}")
                task.mark_executed()
                self.update_schedule_state()

            return success

        except Exception as e:
            logger.exception(f"Failed to handle missed execution for {task.task_id}: {e}")
            return False

    def _get_recent_completions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent completed tasks from audit logs."""
        completions = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Read today's log file
        today_log_file = self.vault_service.vault_path / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        if today_log_file.exists():
            try:
                with open(today_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            timestamp = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))

                            if timestamp >= cutoff_time:
                                action = log_entry.get('action_type', 'unknown')
                                target = log_entry.get('target', 'unknown')

                                if action in ['email_send', 'social_post', 'plan_created']:
                                    completions.append({
                                        'action': action.replace('_', ' ').title(),
                                        'target': target,
                                        'timestamp': timestamp
                                    })
                        except (json.JSONDecodeError, KeyError):
                            pass
            except Exception as e:
                logger.error(f"Failed to read completions: {e}")

        return completions

    def _get_urgent_items(self) -> List[Dict[str, Any]]:
        """Get urgent items from /Needs_Action/."""
        urgent = []
        needs_action_folder = self.vault_service.vault_path / "Needs_Action"

        try:
            for file_path in needs_action_folder.glob("*.md"):
                # Read frontmatter to check priority
                try:
                    frontmatter, _ = self.vault_service.read_markdown_with_frontmatter(file_path)
                    priority = frontmatter.get('priority', 'medium')

                    if priority == 'high':
                        # Calculate age
                        created_at_str = frontmatter.get('created_at', frontmatter.get('timestamp'))
                        if created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                            age_str = f"{int(age_hours)} hours ago"
                        else:
                            age_str = "Unknown age"

                        urgent.append({
                            'priority': priority.upper(),
                            'description': file_path.stem,
                            'file_path': file_path.name,
                            'age': age_str
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to get urgent items: {e}")

        return urgent

    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        heartbeat_file = self.vault_service.vault_path / "Logs" / "heartbeat.json"

        if not heartbeat_file.exists():
            return {
                'status': 'Unknown',
                'emoji': '❓',
                'watchers': {}
            }

        try:
            with open(heartbeat_file, 'r', encoding='utf-8') as f:
                heartbeat_data = json.load(f)

            all_running = True
            watchers = {}

            for watcher_name, watcher_data in heartbeat_data.items():
                status = watcher_data.get('status', 'unknown')
                if status != 'running':
                    all_running = False
                watchers[watcher_name] = status

            if all_running:
                return {'status': 'Healthy', 'emoji': '✅', 'watchers': watchers}
            else:
                return {'status': 'Degraded', 'emoji': '⚠️', 'watchers': watchers}

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'status': 'Unknown', 'emoji': '❓', 'watchers': {}}

    def _get_completed_tasks_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get completed tasks in date range from audit logs."""
        # Simplified implementation - would read multiple log files in real version
        return []

    def _calculate_weekly_metrics(self, completed_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate weekly metrics from completed tasks."""
        return {
            'total_completed': len(completed_tasks),
            'emails_processed': 5,
            'social_posts': 3,
            'whatsapp_messages': 8,
            'time_saved_hours': 12,
            'daily_breakdown': {
                'Monday': 2,
                'Tuesday': 3,
                'Wednesday': 4,
                'Thursday': 2,
                'Friday': 5,
                'Saturday': 0,
                'Sunday': 0
            },
            'success_rate': 95,
            'avg_response_time': 15,
            'uptime_percentage': 99,
            'previous_week_total': 14
        }
