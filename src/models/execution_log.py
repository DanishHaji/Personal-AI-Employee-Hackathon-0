#!/usr/bin/env python3
"""
ExecutionLog Model - Silver Tier

Represents an audit log entry for executed actions (email sends, social posts, etc.).
Stores execution metadata, results, and error details for accountability and debugging.

Contract: specs/002-silver-tier-upgrade/contracts/execution-log-schema.json
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from enum import Enum


class ActionType(str, Enum):
    """Types of actions that can be logged."""
    EMAIL_SEND = "email_send"
    SOCIAL_POST = "social_post"
    WHATSAPP_DETECT = "whatsapp_detect"
    SCHEDULED_TASK = "scheduled_task"


class Actor(str, Enum):
    """Components that execute actions."""
    EXECUTOR = "executor"
    SCHEDULER = "scheduler"
    WHATSAPP_WATCHER = "whatsapp_watcher"
    ORCHESTRATOR = "orchestrator"


class ApprovalStatus(str, Enum):
    """Approval status for actions."""
    APPROVED = "approved"
    AUTO_APPROVED = "auto_approved"
    PENDING = "pending"


class ApprovedBy(str, Enum):
    """Who approved the action."""
    HUMAN = "human"
    AUTO = "auto"


class Result(str, Enum):
    """Execution result status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class ExecutionLog:
    """
    Audit log entry for executed actions.

    Stores complete execution details including plan reference, approval metadata,
    MCP server response, timing, and error information.

    All executions (successful or failed) must be logged for accountability
    and debugging purposes.
    """

    # Required fields
    log_id: str  # Format: LOG_[timestamp]_[action_type]
    timestamp: str  # ISO 8601 format (e.g., "2026-02-25T14:30:00Z")
    action_type: ActionType
    actor: Actor
    plan_id: str  # Reference to plan file that triggered this action
    target: str  # Destination (email address, platform name, phone number, etc.)
    parameters: Dict[str, Any]  # Action-specific parameters
    approval_status: ApprovalStatus
    approved_by: ApprovedBy
    result: Result
    duration_ms: int  # Execution time in milliseconds
    retry_count: int  # Number of retry attempts (0 = first attempt)

    # Optional fields
    approval_timestamp: Optional[str] = None  # When approval was granted
    mcp_server: Optional[str] = None  # MCP server URL used
    response: Optional[Dict[str, Any]] = None  # MCP server response
    error: Optional[str] = None  # Error message if result is failure

    @classmethod
    def create(
        cls,
        action_type: ActionType,
        actor: Actor,
        plan_id: str,
        target: str,
        parameters: Dict[str, Any],
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        approved_by: ApprovedBy = ApprovedBy.HUMAN,
        result: Result = Result.SUCCESS,
        duration_ms: int = 0,
        retry_count: int = 0,
        approval_timestamp: Optional[str] = None,
        mcp_server: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> 'ExecutionLog':
        """
        Create a new ExecutionLog with auto-generated ID and timestamp.

        Args:
            action_type: Type of action executed
            actor: Component that executed the action
            plan_id: Plan file reference
            target: Destination (email, platform, phone, etc.)
            parameters: Action-specific parameters
            approval_status: Approval state (default: approved)
            approved_by: Who approved (default: human)
            result: Execution result (default: success)
            duration_ms: Execution time in milliseconds
            retry_count: Number of retries (0 = first attempt)
            approval_timestamp: When approval was granted
            mcp_server: MCP server URL used
            response: MCP server response
            error: Error message if failed

        Returns:
            ExecutionLog instance
        """
        # Generate log ID
        timestamp_int = int(datetime.now(timezone.utc).timestamp())
        log_id = f"LOG_{timestamp_int}_{action_type.value}"

        # Generate ISO 8601 timestamp
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        return cls(
            log_id=log_id,
            timestamp=timestamp,
            action_type=action_type,
            actor=actor,
            plan_id=plan_id,
            target=target,
            parameters=parameters,
            approval_status=approval_status,
            approved_by=approved_by,
            result=result,
            duration_ms=duration_ms,
            retry_count=retry_count,
            approval_timestamp=approval_timestamp,
            mcp_server=mcp_server,
            response=response,
            error=error
        )

    def to_json(self) -> str:
        """
        Serialize to JSON string for logging to daily log files.

        Returns:
            JSON string representation
        """
        data = self.to_dict()
        return json.dumps(data, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Converts enum values to strings and excludes None values for cleaner output.

        Returns:
            Dictionary representation
        """
        data = asdict(self)

        # Convert enums to strings
        data['action_type'] = self.action_type.value
        data['actor'] = self.actor.value
        data['approval_status'] = self.approval_status.value
        data['approved_by'] = self.approved_by.value
        data['result'] = self.result.value

        # Remove None values for cleaner JSON
        data = {k: v for k, v in data.items() if v is not None}

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionLog':
        """
        Create ExecutionLog from dictionary.

        Handles enum conversion and optional field defaults.

        Args:
            data: Dictionary with log data

        Returns:
            ExecutionLog instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Convert string values to enums
        if isinstance(data.get('action_type'), str):
            data['action_type'] = ActionType(data['action_type'])

        if isinstance(data.get('actor'), str):
            data['actor'] = Actor(data['actor'])

        if isinstance(data.get('approval_status'), str):
            data['approval_status'] = ApprovalStatus(data['approval_status'])

        if isinstance(data.get('approved_by'), str):
            data['approved_by'] = ApprovedBy(data['approved_by'])

        if isinstance(data.get('result'), str):
            data['result'] = Result(data['result'])

        # Create instance
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExecutionLog':
        """
        Create ExecutionLog from JSON string.

        Args:
            json_str: JSON string

        Returns:
            ExecutionLog instance

        Raises:
            json.JSONDecodeError: If JSON is invalid
            ValueError: If required fields are missing
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def was_successful(self) -> bool:
        """
        Check if execution was successful.

        Returns:
            True if result is SUCCESS, False otherwise
        """
        return self.result == Result.SUCCESS

    def was_approved_by_human(self) -> bool:
        """
        Check if action was approved by a human.

        Returns:
            True if approved_by is HUMAN, False otherwise
        """
        return self.approved_by == ApprovedBy.HUMAN

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ExecutionLog(log_id='{self.log_id}', action_type={self.action_type.value}, "
            f"result={self.result.value}, target='{self.target}')"
        )


# Example usage
if __name__ == "__main__":
    # Example: Create email send log
    log = ExecutionLog.create(
        action_type=ActionType.EMAIL_SEND,
        actor=Actor.EXECUTOR,
        plan_id="PLAN_email_123456.md",
        target="user@example.com",
        parameters={
            "recipient": "user@example.com",
            "subject": "Test Email",
            "body_preview": "Hello, this is a test..."
        },
        result=Result.SUCCESS,
        duration_ms=1250,
        mcp_server="http://localhost:3001/gmail",
        response={
            "message_id": "abc123xyz",
            "thread_id": "thread_456"
        }
    )

    print("=== ExecutionLog Example ===")
    print(f"Log ID: {log.log_id}")
    print(f"Timestamp: {log.timestamp}")
    print(f"Was successful: {log.was_successful()}")
    print(f"\nJSON representation:")
    print(log.to_json())

    # Example: Deserialize from JSON
    print("\n=== Deserialization Test ===")
    json_str = log.to_json()
    restored_log = ExecutionLog.from_json(json_str)
    print(f"Restored log: {restored_log}")
    print(f"IDs match: {log.log_id == restored_log.log_id}")
