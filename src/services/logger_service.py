"""
AuditLogger Service for Personal AI Employee - Bronze Tier MVP

Implements structured JSON logging to /Logs/YYYY-MM-DD.json files.
Follows Contract 6 from contracts/file-interfaces.md

All actions by watchers and Claude Code are logged with:
- timestamp (ISO 8601 UTC)
- action_type (email_detected, file_dropped, plan_created, etc.)
- actor (gmail_watcher, filesystem_watcher, claude_code, orchestrator, human)
- target (email address, filename, or file path)
- parameters (action-specific details as JSON)
- approval_status (pending, awaiting_approval, approved, rejected)
- approved_by (human, auto, null)
- result (success, failure, error)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Literal, Optional
from enum import Enum


class ActionType(str, Enum):
    """Valid action types for audit logging."""
    EMAIL_DETECTED = "email_detected"
    FILE_DROPPED = "file_dropped"
    PLAN_CREATED = "plan_created"
    TASK_COMPLETED = "task_completed"
    ERROR = "error"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    HEARTBEAT = "heartbeat"


class Actor(str, Enum):
    """Valid actors for audit logging."""
    GMAIL_WATCHER = "gmail_watcher"
    FILESYSTEM_WATCHER = "filesystem_watcher"
    CLAUDE_CODE = "claude_code"
    ORCHESTRATOR = "orchestrator"
    HUMAN = "human"


class ApprovalStatus(str, Enum):
    """Approval status for actions."""
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


class Result(str, Enum):
    """Result status for actions."""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class AuditLogger:
    """Structured JSON audit logger with daily rotation."""

    def __init__(self, vault_path: str | Path):
        """
        Initialize AuditLogger with vault path.

        Args:
            vault_path: Absolute path to Obsidian vault root
        """
        self.vault_path = Path(vault_path).resolve()
        self.logs_dir = self.vault_path / "Logs"

        # Ensure Logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action_type: ActionType | str,
        actor: Actor | str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        approval_status: ApprovalStatus | str = ApprovalStatus.NOT_APPLICABLE,
        approved_by: Optional[str] = None,
        result: Result | str = Result.SUCCESS,
        duration_ms: Optional[int] = None
    ) -> None:
        """
        Log an action to the daily audit log file.

        Creates entry in /Logs/YYYY-MM-DD.json using newline-delimited JSON format.

        Args:
            action_type: Type of action being logged
            actor: Who/what performed the action
            target: What was affected (email, file, etc.)
            parameters: Action-specific details (optional)
            approval_status: Approval state (default: not_applicable)
            approved_by: Who approved (human/auto/null)
            result: Success/failure/error (default: success)
            duration_ms: Optional execution duration in milliseconds

        Example:
            logger.log(
                action_type=ActionType.EMAIL_DETECTED,
                actor=Actor.GMAIL_WATCHER,
                target="client@example.com",
                parameters={"subject": "Urgent invoice", "email_id": "ABC123"},
                result=Result.SUCCESS
            )
        """
        # Convert enums to strings if necessary
        if isinstance(action_type, ActionType):
            action_type = action_type.value
        if isinstance(actor, Actor):
            actor = actor.value
        if isinstance(approval_status, ApprovalStatus):
            approval_status = approval_status.value
        if isinstance(result, Result):
            result = result.value

        # Create log entry per Contract 6 schema
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC with Z suffix
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result,
        }

        # Add optional duration
        if duration_ms is not None:
            log_entry["duration_ms"] = duration_ms

        # Get today's log file
        log_file = self._get_log_file()

        # Append entry as single-line JSON (newline-delimited JSON format)
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            # If log write fails, print to stderr but don't crash
            print(f"ERROR: Failed to write audit log: {e}", file=__import__('sys').stderr)

    def log_email_detected(
        self,
        email_id: str,
        from_addr: str,
        subject: str,
        priority: str,
        result: Result | str = Result.SUCCESS
    ) -> None:
        """
        Convenience method for logging email detection.

        Args:
            email_id: Gmail message ID
            from_addr: Sender email address
            subject: Email subject
            priority: Priority level (high/medium)
            result: Operation result (default: success)
        """
        self.log(
            action_type=ActionType.EMAIL_DETECTED,
            actor=Actor.GMAIL_WATCHER,
            target=from_addr,
            parameters={
                "email_id": email_id,
                "subject": subject,
                "priority": priority
            },
            approval_status=ApprovalStatus.PENDING,
            result=result
        )

    def log_file_dropped(
        self,
        filename: str,
        size: int,
        file_type: str,
        quarantined: bool = False,
        result: Result | str = Result.SUCCESS
    ) -> None:
        """
        Convenience method for logging file drop detection.

        Args:
            filename: Original filename
            size: File size in bytes
            file_type: File extension
            quarantined: Whether file was quarantined
            result: Operation result (default: success)
        """
        self.log(
            action_type=ActionType.FILE_DROPPED,
            actor=Actor.FILESYSTEM_WATCHER,
            target=filename,
            parameters={
                "size": size,
                "file_type": file_type,
                "quarantined": quarantined
            },
            approval_status=ApprovalStatus.QUARANTINED if quarantined else ApprovalStatus.PENDING,
            result=result
        )

    def log_plan_created(
        self,
        plan_id: str,
        source_type: str,
        source_id: str,
        approval_required: bool,
        result: Result | str = Result.SUCCESS
    ) -> None:
        """
        Convenience method for logging plan creation.

        Args:
            plan_id: Plan identifier (e.g., "PLAN_001")
            source_type: Type of source (email/file_drop)
            source_id: Source entity ID
            approval_required: Whether plan needs approval
            result: Operation result (default: success)
        """
        self.log(
            action_type=ActionType.PLAN_CREATED,
            actor=Actor.CLAUDE_CODE,
            target=f"/Plans/{plan_id}.md",
            parameters={
                "source_type": source_type,
                "source_id": source_id,
                "approval_required": approval_required
            },
            approval_status=ApprovalStatus.AWAITING_APPROVAL if approval_required else ApprovalStatus.NOT_APPLICABLE,
            result=result
        )

    def log_error(
        self,
        actor: Actor | str,
        error_message: str,
        error_type: str,
        target: str = "system"
    ) -> None:
        """
        Convenience method for logging errors.

        Args:
            actor: Component that encountered the error
            error_message: Error description
            error_type: Type/class of error
            target: What was being operated on
        """
        self.log(
            action_type=ActionType.ERROR,
            actor=actor,
            target=target,
            parameters={
                "error_message": error_message,
                "error_type": error_type
            },
            approval_status=ApprovalStatus.NOT_APPLICABLE,
            result=Result.ERROR
        )

    def read_today_logs(self) -> list[Dict[str, Any]]:
        """
        Read all log entries from today's log file.

        Returns:
            list: List of log entry dictionaries

        Raises:
            FileNotFoundError: If today's log file doesn't exist
        """
        log_file = self._get_log_file()

        if not log_file.exists():
            return []

        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

        return entries

    def get_recent_activity(self, limit: int = 5) -> list[Dict[str, Any]]:
        """
        Get recent activity entries for Dashboard display.

        Filters for user-visible actions (not heartbeats/system events).

        Args:
            limit: Maximum number of entries to return (default: 5)

        Returns:
            list: Recent activity entries (newest first)
        """
        # Read today's logs
        all_logs = self.read_today_logs()

        # Filter for user-visible actions
        visible_actions = {
            ActionType.EMAIL_DETECTED.value,
            ActionType.FILE_DROPPED.value,
            ActionType.PLAN_CREATED.value,
            ActionType.TASK_COMPLETED.value,
        }

        filtered = [
            log for log in all_logs
            if log.get("action_type") in visible_actions
        ]

        # Return most recent N entries
        return filtered[-limit:][::-1]  # Reverse to get newest first

    def _get_log_file(self) -> Path:
        """
        Get path to today's log file.

        Format: /Logs/YYYY-MM-DD.json

        Returns:
            Path: Path to current day's log file
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.logs_dir / f"{today}.json"

    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Remove log files older than retention period.

        Per Constitution Principle VII: 90-day minimum retention.

        Args:
            retention_days: Number of days to keep (default: 90)

        Returns:
            int: Number of files deleted
        """
        if retention_days < 90:
            raise ValueError("Retention period must be at least 90 days per constitution")

        cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        deleted_count = 0

        for log_file in self.logs_dir.glob("*.json"):
            if log_file.stat().st_mtime < cutoff_date:
                log_file.unlink()
                deleted_count += 1

        return deleted_count
