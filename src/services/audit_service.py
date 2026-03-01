"""
Audit Service for Personal AI Employee - Gold Tier

Provides query utilities for audit log analysis. Extends logger_service.py
with advanced querying, filtering, and aggregation capabilities needed for analytics.

Features:
- Query logs by date range, action type, actor
- Filter logs by parameters (e.g., contact, trust_rule_id)
- Aggregate metrics (count, sum, average)
- Efficient iteration over large log files

Usage:
    audit_service = AuditService(vault_path="/path/to/vault")

    # Query last 30 days
    logs = audit_service.query_logs(days=30, action_type="email_send")

    # Get metrics
    metrics = audit_service.get_metrics(
        days=90,
        metrics=["total_actions", "avg_response_time"]
    )

    # Query by actor
    ai_actions = audit_service.query_by_actor(actor="executor", days=7)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from collections import defaultdict

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit log query and analysis service.

    Provides efficient querying and aggregation of audit logs for analytics,
    trust framework effectiveness tracking, and productivity insights.
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize AuditService.

        Args:
            vault_path: Absolute path to Obsidian vault root
        """
        self.vault_path = Path(vault_path).resolve()
        self.logs_dir = self.vault_path / "Logs"

        # Ensure Logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_files_for_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Path]:
        """
        Get log file paths for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List[Path]: Sorted list of log file paths
        """
        log_files = []
        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            log_file = self.logs_dir / f"{current_date.isoformat()}.json"
            if log_file.exists():
                log_files.append(log_file)
            current_date += timedelta(days=1)

        return sorted(log_files)

    def query_logs(
        self,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_type: Optional[str | List[str]] = None,
        actor: Optional[str | List[str]] = None,
        result: Optional[str | List[str]] = None,
        target: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            days: Number of days to query (from today backward)
            start_date: Start date (if days not provided)
            end_date: End date (defaults to now)
            action_type: Filter by action type(s)
            actor: Filter by actor(s)
            result: Filter by result(s) (success, failure, error)
            target: Filter by target (partial match)
            limit: Maximum number of results to return

        Returns:
            List[Dict]: List of matching log entries (newest first)
        """
        # Determine date range
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            # Default to last 90 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
        elif end_date is None:
            end_date = datetime.now()

        # Get log files for date range
        log_files = self._get_log_files_for_date_range(start_date, end_date)

        # Collect matching logs
        matching_logs = []

        # Convert filters to lists for consistent handling
        action_types = [action_type] if isinstance(action_type, str) else action_type or []
        actors = [actor] if isinstance(actor, str) else actor or []
        results = [result] if isinstance(result, str) else result or []

        # Iterate through log files (newest first for efficiency with limit)
        for log_file in reversed(log_files):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue

                        log_entry = json.loads(line)

                        # Apply filters
                        if action_types and log_entry.get("action_type") not in action_types:
                            continue
                        if actors and log_entry.get("actor") not in actors:
                            continue
                        if results and log_entry.get("result") not in results:
                            continue
                        if target and target not in log_entry.get("target", ""):
                            continue

                        matching_logs.append(log_entry)

                        # Check limit
                        if limit and len(matching_logs) >= limit:
                            return matching_logs

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error reading log file {log_file}: {e}")
                continue

        return matching_logs

    def query_by_trust_rule(
        self,
        rule_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Query logs for actions auto-approved by a specific trust rule.

        Args:
            rule_id: Trust rule ID (e.g., "RULE_email_known_contacts")
            days: Number of days to query

        Returns:
            List[Dict]: Logs where trust_rule_id matches
        """
        logs = self.query_logs(days=days)
        return [
            log for log in logs
            if log.get("parameters", {}).get("trust_rule_id") == rule_id
        ]

    def get_trust_rule_effectiveness(
        self,
        rule_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate effectiveness metrics for a trust rule.

        Args:
            rule_id: Trust rule ID
            days: Number of days to analyze

        Returns:
            Dict: Effectiveness metrics
                - total_auto_approved: Count of auto-approved actions
                - success_count: Count of successful executions
                - failure_count: Count of failures
                - effectiveness_score: success_count / total_auto_approved
        """
        logs = self.query_by_trust_rule(rule_id, days=days)

        total = len(logs)
        success = sum(1 for log in logs if log.get("result") == "success")
        failure = total - success

        effectiveness_score = success / total if total > 0 else 1.0

        return {
            "rule_id": rule_id,
            "total_auto_approved": total,
            "success_count": success,
            "failure_count": failure,
            "effectiveness_score": effectiveness_score,
            "analysis_period_days": days
        }

    def get_metrics(
        self,
        days: int = 30,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate productivity metrics from audit logs.

        Args:
            days: Number of days to analyze
            metrics: List of metrics to calculate (default: all)

        Available Metrics:
            - total_actions: Total logged actions
            - emails_sent: Count of email_send actions
            - emails_received: Count of email_detected actions
            - meetings_attended: Count of meeting attendance
            - tasks_completed: Count of task_completed actions
            - auto_approval_count: Count of auto-approved actions
            - auto_approval_rate: Percentage of actions auto-approved

        Returns:
            Dict: Calculated metrics
        """
        all_logs = self.query_logs(days=days)

        # Calculate all available metrics
        calculated_metrics = {
            "total_actions": len(all_logs),
            "analysis_period_days": days,
            "emails_sent": sum(1 for log in all_logs if log.get("action_type") == "email_send"),
            "emails_received": sum(1 for log in all_logs if log.get("action_type") == "email_detected"),
            "tasks_completed": sum(1 for log in all_logs if log.get("action_type") == "task_completed"),
            "social_posts": sum(1 for log in all_logs if log.get("action_type") == "social_post"),
        }

        # Auto-approval metrics
        auto_approved = [
            log for log in all_logs
            if log.get("approval_status") == "approved"
            and log.get("approved_by") in ["auto", "trust_rule"]
        ]
        calculated_metrics["auto_approval_count"] = len(auto_approved)
        calculated_metrics["auto_approval_rate"] = (
            len(auto_approved) / len(all_logs) if all_logs else 0.0
        )

        # Response time metrics (if available in parameters)
        response_times = [
            log.get("parameters", {}).get("response_time_seconds")
            for log in all_logs
            if log.get("parameters", {}).get("response_time_seconds") is not None
        ]
        if response_times:
            calculated_metrics["avg_response_time_seconds"] = sum(response_times) / len(response_times)
            calculated_metrics["min_response_time_seconds"] = min(response_times)
            calculated_metrics["max_response_time_seconds"] = max(response_times)

        # Filter to requested metrics if specified
        if metrics:
            calculated_metrics = {
                k: v for k, v in calculated_metrics.items()
                if k in metrics or k == "analysis_period_days"
            }

        return calculated_metrics

    def get_top_contacts(
        self,
        days: int = 30,
        limit: int = 10,
        action_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently contacted contacts from audit logs.

        Args:
            days: Number of days to analyze
            limit: Maximum number of contacts to return
            action_types: Filter by action types (default: email_send, email_detected)

        Returns:
            List[Dict]: Top contacts with interaction counts
        """
        if action_types is None:
            action_types = ["email_send", "email_detected"]

        logs = self.query_logs(days=days, action_type=action_types)

        # Count interactions by contact (target)
        contact_counts = defaultdict(int)
        for log in logs:
            target = log.get("target", "")
            if target:
                contact_counts[target] += 1

        # Sort by count and return top N
        sorted_contacts = sorted(
            contact_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"contact": contact, "interactions": count}
            for contact, count in sorted_contacts
        ]

    def get_action_timeline(
        self,
        days: int = 30,
        action_type: Optional[str] = None,
        granularity: Literal["hour", "day", "week"] = "day"
    ) -> List[Dict[str, Any]]:
        """
        Get action counts over time (for trend analysis).

        Args:
            days: Number of days to analyze
            action_type: Filter by specific action type
            granularity: Time bucket size (hour, day, week)

        Returns:
            List[Dict]: Timeline with counts
                [{timestamp, count, action_type}, ...]
        """
        logs = self.query_logs(days=days, action_type=action_type)

        # Group by time bucket
        time_buckets = defaultdict(int)
        for log in logs:
            timestamp_str = log.get("timestamp")
            if not timestamp_str:
                continue

            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Determine bucket
            if granularity == "hour":
                bucket = timestamp.replace(minute=0, second=0, microsecond=0)
            elif granularity == "day":
                bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # week
                bucket = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                bucket = bucket - timedelta(days=bucket.weekday())

            bucket_str = bucket.isoformat()
            time_buckets[bucket_str] += 1

        # Convert to sorted list
        timeline = [
            {"timestamp": bucket, "count": count}
            for bucket, count in sorted(time_buckets.items())
        ]

        return timeline

    def query_by_parameter(
        self,
        parameter_key: str,
        parameter_value: Any,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Query logs by a specific parameter value.

        Args:
            parameter_key: Parameter key to filter by
            parameter_value: Parameter value to match
            days: Number of days to query

        Returns:
            List[Dict]: Matching log entries
        """
        logs = self.query_logs(days=days)
        return [
            log for log in logs
            if log.get("parameters", {}).get(parameter_key) == parameter_value
        ]

    def get_error_logs(
        self,
        days: int = 7,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent error logs for debugging.

        Args:
            days: Number of days to query
            limit: Maximum number of errors to return

        Returns:
            List[Dict]: Error log entries (newest first)
        """
        return self.query_logs(
            days=days,
            result=["error", "failure"],
            limit=limit
        )
