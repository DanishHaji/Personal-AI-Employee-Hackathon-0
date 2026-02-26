#!/usr/bin/env python3
"""
ExecutorService - Silver Tier US1

Handles execution of approved plans (email sends, social posts, etc.) from /Approved/ folder.
Validates plans, executes actions via MCP servers, handles errors, and creates audit logs.

Core workflow:
1. Detect plan in /Approved/ folder
2. Validate plan against JSON schema
3. Check rate limits
4. Execute action via MCP client
5. Create execution log
6. Move plan to /Done/ (success) or /Needs_Action/ (failure)
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from src.services.mcp_client import MCPClient, MCPResponse, MCPErrorType
from src.services.rate_limiter import RateLimiter, Platform
from src.services.plan_validator import PlanValidator, PlanType, ValidationResult
from src.services.vault_service import VaultService
from src.models.execution_log import (
    ExecutionLog,
    ActionType,
    Actor,
    ApprovalStatus,
    ApprovedBy,
    Result
)


logger = logging.getLogger(__name__)


class ExecutorService:
    """
    Service for executing approved plans via MCP servers.

    Coordinates plan validation, rate limiting, MCP execution, audit logging,
    and plan lifecycle management (Approved → Done/Needs_Action).

    Usage:
        executor = ExecutorService(
            vault_service=vault_service,
            rate_limiter=rate_limiter,
            plan_validator=plan_validator,
            mcp_urls={
                "gmail": "http://localhost:3001/gmail",
                "linkedin": "http://localhost:3002/linkedin",
                # ...
            }
        )

        # Execute an email plan
        result = executor.execute_email_plan(plan_path)
        if result.success:
            print("Email sent successfully")
    """

    def __init__(
        self,
        vault_service: VaultService,
        rate_limiter: RateLimiter,
        plan_validator: PlanValidator,
        mcp_urls: Dict[str, str],
        dry_run: bool = False
    ):
        """
        Initialize ExecutorService.

        Args:
            vault_service: VaultService instance for file operations
            rate_limiter: RateLimiter instance for quota management
            plan_validator: PlanValidator instance for schema validation
            mcp_urls: Dictionary of MCP server URLs by platform
            dry_run: If True, validate but don't execute (read from env if not specified)
        """
        self.vault_service = vault_service
        self.rate_limiter = rate_limiter
        self.plan_validator = plan_validator
        self.mcp_urls = mcp_urls
        self.dry_run = dry_run or os.getenv("DRY_RUN", "false").lower() == "true"

        # Initialize MCP clients (lazy initialization)
        self.mcp_clients: Dict[str, MCPClient] = {}

        logger.info(
            f"ExecutorService initialized (dry_run={self.dry_run}, "
            f"mcp_urls={list(mcp_urls.keys())})"
        )

    def _get_mcp_client(self, platform: str) -> Optional[MCPClient]:
        """
        Get or create MCP client for platform.

        Args:
            platform: Platform name (gmail, linkedin, etc.)

        Returns:
            MCPClient instance or None if URL not configured
        """
        if platform not in self.mcp_urls:
            logger.error(f"No MCP URL configured for platform: {platform}")
            return None

        # Create client if not already cached
        if platform not in self.mcp_clients:
            self.mcp_clients[platform] = MCPClient(
                server_url=self.mcp_urls[platform],
                dry_run=self.dry_run
            )

        return self.mcp_clients[platform]

    def validate_plan(
        self,
        plan_path: Path,
        plan_type: PlanType
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate plan file against JSON schema.

        Args:
            plan_path: Path to plan file
            plan_type: Expected plan type

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]:
                (is_valid, plan_data, error_message)
        """
        try:
            # Read plan file
            frontmatter, body = self.vault_service.read_markdown_with_frontmatter(
                plan_path
            )

            # Merge frontmatter and body into plan_data
            plan_data = dict(frontmatter)
            if body.strip():
                plan_data['body'] = body.strip()

            # Validate against schema
            if plan_type == PlanType.EMAIL_SEND:
                result = self.plan_validator.validate_email_plan(plan_data)
            elif plan_type == PlanType.SOCIAL_POST:
                result = self.plan_validator.validate_social_post(plan_data)
            elif plan_type == PlanType.SCHEDULED_TASK:
                result = self.plan_validator.validate_scheduled_task(plan_data)
            else:
                result = ValidationResult(
                    valid=False,
                    errors=[f"Unsupported plan type: {plan_type}"]
                )

            if result.valid:
                logger.info(f"Plan validation successful: {plan_path.name}")
                return True, plan_data, None
            else:
                error_msg = f"Plan validation failed: {result.error_message}"
                logger.warning(f"{error_msg} (file: {plan_path.name})")
                return False, plan_data, error_msg

        except Exception as e:
            error_msg = f"Error reading plan file: {str(e)}"
            logger.error(f"{error_msg} (file: {plan_path.name})")
            return False, None, error_msg

    def execute_email_plan(
        self,
        plan_path: Path,
        plan_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[ExecutionLog]]:
        """
        Execute email send plan via Gmail MCP server.

        Workflow:
        1. Validate plan (if not already validated)
        2. Check rate limits (Gmail: 500/day, 1 per 5 seconds)
        3. Send email via MCP client
        4. Create execution log
        5. Move plan to /Done/ or /Needs_Action/

        Args:
            plan_path: Path to email plan file
            plan_data: Optional pre-validated plan data (validates if None)

        Returns:
            Tuple[bool, Optional[ExecutionLog]]: (success, execution_log)
        """
        start_time = time.time()

        # Validate plan if not provided
        if plan_data is None:
            is_valid, plan_data, error_msg = self.validate_plan(
                plan_path,
                PlanType.EMAIL_SEND
            )

            if not is_valid:
                # Create failure log
                exec_log = ExecutionLog.create(
                    action_type=ActionType.EMAIL_SEND,
                    actor=Actor.EXECUTOR,
                    plan_id=plan_path.name,
                    target=plan_data.get('recipient', 'unknown') if plan_data else 'unknown',
                    parameters={'error_type': 'validation_error'},
                    result=Result.FAILURE,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=error_msg
                )
                self.create_execution_log(exec_log)
                self.handle_execution_error(plan_path, error_msg or "Validation failed")
                return False, exec_log

        # Check rate limits
        if not self.rate_limiter.can_perform(Platform.GMAIL):
            wait_time = self.rate_limiter.get_wait_time(Platform.GMAIL)
            error_msg = f"Rate limit exceeded - wait {wait_time:.0f}s before next email"
            logger.warning(error_msg)

            exec_log = ExecutionLog.create(
                action_type=ActionType.EMAIL_SEND,
                actor=Actor.EXECUTOR,
                plan_id=plan_path.name,
                target=plan_data.get('recipient', 'unknown'),
                parameters={'error_type': 'rate_limit'},
                result=Result.FAILURE,
                duration_ms=int((time.time() - start_time) * 1000),
                error=error_msg
            )
            self.create_execution_log(exec_log)
            # Don't move plan - will retry later
            return False, exec_log

        # Consume rate limit token
        self.rate_limiter.consume(Platform.GMAIL)

        # Get Gmail MCP client
        mcp_client = self._get_mcp_client("gmail")
        if not mcp_client:
            error_msg = "Gmail MCP client not configured"
            exec_log = ExecutionLog.create(
                action_type=ActionType.EMAIL_SEND,
                actor=Actor.EXECUTOR,
                plan_id=plan_path.name,
                target=plan_data.get('recipient', 'unknown'),
                parameters={'error_type': 'configuration_error'},
                result=Result.FAILURE,
                duration_ms=int((time.time() - start_time) * 1000),
                error=error_msg
            )
            self.create_execution_log(exec_log)
            self.handle_execution_error(plan_path, error_msg)
            return False, exec_log

        # Execute email send via MCP
        try:
            # Build email data from plan
            email_data = {
                'action': plan_data.get('action', 'send'),
                'to': plan_data.get('recipient'),
                'subject': plan_data.get('subject'),
                'body': plan_data.get('body', plan_data.get('body')),
            }

            # Add optional fields
            if 'thread_id' in plan_data:
                email_data['thread_id'] = plan_data['thread_id']
            if 'in_reply_to' in plan_data:
                email_data['in_reply_to'] = plan_data['in_reply_to']

            # Call MCP server
            response = mcp_client.post("/send_email", data=email_data)

            duration_ms = int((time.time() - start_time) * 1000)

            if response.success:
                # Success - create log and move to Done
                exec_log = ExecutionLog.create(
                    action_type=ActionType.EMAIL_SEND,
                    actor=Actor.EXECUTOR,
                    plan_id=plan_path.name,
                    target=plan_data.get('recipient'),
                    parameters={
                        'subject': plan_data.get('subject'),
                        'body_preview': plan_data.get('body', '')[:100]
                    },
                    result=Result.SUCCESS,
                    duration_ms=duration_ms,
                    mcp_server=self.mcp_urls.get('gmail'),
                    response=response.data
                )
                self.create_execution_log(exec_log)
                self.move_to_done(plan_path, exec_log)

                logger.info(
                    f"Email sent successfully to {plan_data.get('recipient')} "
                    f"({duration_ms}ms)"
                )
                return True, exec_log

            else:
                # MCP error - create log and handle error
                exec_log = ExecutionLog.create(
                    action_type=ActionType.EMAIL_SEND,
                    actor=Actor.EXECUTOR,
                    plan_id=plan_path.name,
                    target=plan_data.get('recipient'),
                    parameters={
                        'subject': plan_data.get('subject'),
                        'error_type': response.error_type.value if response.error_type else 'unknown'
                    },
                    result=Result.FAILURE,
                    duration_ms=duration_ms,
                    mcp_server=self.mcp_urls.get('gmail'),
                    error=response.error
                )
                self.create_execution_log(exec_log)
                self.handle_execution_error(plan_path, response.error or "MCP error")

                logger.error(
                    f"Email send failed: {response.error} "
                    f"(recipient: {plan_data.get('recipient')})"
                )
                return False, exec_log

        except Exception as e:
            # Unexpected error
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"

            exec_log = ExecutionLog.create(
                action_type=ActionType.EMAIL_SEND,
                actor=Actor.EXECUTOR,
                plan_id=plan_path.name,
                target=plan_data.get('recipient', 'unknown'),
                parameters={'error_type': 'unexpected_error'},
                result=Result.FAILURE,
                duration_ms=duration_ms,
                error=error_msg
            )
            self.create_execution_log(exec_log)
            self.handle_execution_error(plan_path, error_msg)

            logger.exception(f"Unexpected error executing email plan: {e}")
            return False, exec_log

    def handle_execution_error(self, plan_path: Path, error_message: str):
        """
        Handle execution failure by moving plan back to /Needs_Action/ with error details.

        Args:
            plan_path: Path to failed plan file
            error_message: Error description
        """
        try:
            # Read current plan
            frontmatter, body = self.vault_service.read_markdown_with_frontmatter(
                plan_path
            )

            # Add error metadata
            frontmatter['execution_error'] = error_message
            frontmatter['execution_error_timestamp'] = datetime.now(timezone.utc).isoformat()
            frontmatter['status'] = 'failed'

            # Update plan file with error details
            self.vault_service.write_markdown_with_frontmatter(
                plan_path,
                frontmatter,
                body
            )

            # Move back to Needs_Action
            self.vault_service.move_file(
                plan_path,
                "Needs_Action",
                new_name=plan_path.name
            )

            logger.info(f"Moved failed plan to /Needs_Action/: {plan_path.name}")

        except Exception as e:
            logger.error(f"Failed to handle execution error: {e}")

    def move_to_done(self, plan_path: Path, exec_log: ExecutionLog):
        """
        Archive successful execution by moving plan to /Done/ with metadata.

        Args:
            plan_path: Path to successful plan file
            exec_log: Execution log with result details
        """
        try:
            # Read current plan
            frontmatter, body = self.vault_service.read_markdown_with_frontmatter(
                plan_path
            )

            # Add success metadata
            frontmatter['executed_at'] = exec_log.timestamp
            frontmatter['execution_log_id'] = exec_log.log_id
            frontmatter['status'] = 'completed'

            # Add MCP response data if available
            if exec_log.response:
                frontmatter['mcp_response'] = exec_log.response

            # Update plan file
            self.vault_service.write_markdown_with_frontmatter(
                plan_path,
                frontmatter,
                body
            )

            # Move to Done
            self.vault_service.move_file(
                plan_path,
                "Done",
                new_name=plan_path.name
            )

            logger.info(f"Moved completed plan to /Done/: {plan_path.name}")

        except Exception as e:
            logger.error(f"Failed to move plan to Done: {e}")

    def create_execution_log(self, exec_log: ExecutionLog):
        """
        Write execution log entry to daily audit log file.

        Args:
            exec_log: ExecutionLog instance to write
        """
        try:
            # Get today's date string
            date_str = datetime.now().strftime("%Y-%m-%d")

            # Write log entry using VaultService
            self.vault_service.write_execution_log(
                exec_log.to_dict(),
                date_str
            )

            logger.debug(
                f"Created execution log: {exec_log.log_id} "
                f"(action: {exec_log.action_type.value}, result: {exec_log.result.value})"
            )

        except Exception as e:
            logger.error(f"Failed to create execution log: {e}")

    def close(self):
        """Close all MCP clients and clean up resources."""
        for platform, client in self.mcp_clients.items():
            try:
                client.close()
                logger.debug(f"Closed MCP client for {platform}")
            except Exception as e:
                logger.error(f"Error closing MCP client for {platform}: {e}")

        self.mcp_clients.clear()


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Initialize services
    vault_service = VaultService(vault_path="./vault")
    rate_limiter = RateLimiter(state_file="./Logs/rate_limit_state.json")
    plan_validator = PlanValidator()

    # Create executor
    executor = ExecutorService(
        vault_service=vault_service,
        rate_limiter=rate_limiter,
        plan_validator=plan_validator,
        mcp_urls={
            "gmail": os.getenv("GMAIL_MCP_URL", "http://localhost:3001/gmail")
        },
        dry_run=True
    )

    print("\n=== ExecutorService Example ===")
    print("Executor initialized in DRY_RUN mode")
    print(f"Gmail MCP URL: {executor.mcp_urls.get('gmail')}")
    print(f"Rate limit remaining (Gmail): {rate_limiter.get_remaining(Platform.GMAIL)}")

    # Clean up
    executor.close()
