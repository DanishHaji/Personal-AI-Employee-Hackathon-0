#!/usr/bin/env python3
"""
Executor - Silver Tier US1 Main Process

Monitors /Approved/ folder for new plans and executes them via ExecutorService.
Uses watchdog for file system monitoring with event-driven architecture.

Workflow:
1. Monitor /Approved/ folder for new .md files
2. Detect plan type from frontmatter
3. Execute plan via ExecutorService
4. Handle errors gracefully with MCP connection failure detection
5. Log heartbeat every 60 seconds for health monitoring

PM2 Configuration:
    pm2 start src/executor.py --name executor --interpreter python3
    pm2 logs executor
    pm2 stop executor
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
except ImportError:
    print("ERROR: watchdog library not found. Install with: uv pip install watchdog")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not found. Install with: uv pip install python-dotenv")
    sys.exit(1)

from src.services.executor_service import ExecutorService
from src.services.vault_service import VaultService
from src.services.rate_limiter import RateLimiter
from src.services.plan_validator import PlanValidator, PlanType
from src.services.social_media_service import SocialMediaService
from src.services.mcp_client import MCPClient
from src.models.social_media_post import SocialMediaPost, Platform, PostStatus
from src.models.execution_log import ExecutionLog, ActionType, Actor, Result


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ApprovedFolderHandler(FileSystemEventHandler):
    """
    Watchdog event handler for /Approved/ folder.

    Detects new plan files and triggers execution via ExecutorService.
    """

    def __init__(
        self,
        executor_service: ExecutorService,
        social_media_service: SocialMediaService
    ):
        """
        Initialize handler.

        Args:
            executor_service: ExecutorService instance for plan execution
            social_media_service: SocialMediaService instance for social posts
        """
        self.executor_service = executor_service
        self.social_media_service = social_media_service
        self.processing = set()  # Track files currently being processed

    def on_created(self, event):
        """
        Handle file creation events.

        Args:
            event: FileSystemEvent from watchdog
        """
        # Only process markdown files
        if event.is_directory or not event.src_path.endswith('.md'):
            return

        file_path = Path(event.src_path)

        # Skip if already processing
        if file_path in self.processing:
            logger.debug(f"Already processing: {file_path.name}")
            return

        logger.info(f"New plan detected: {file_path.name}")

        # Process the plan
        self._process_plan(file_path)

    def _process_plan(self, file_path: Path):
        """
        Process a plan file by determining type and executing.

        Args:
            file_path: Path to plan file
        """
        # Mark as processing
        self.processing.add(file_path)

        try:
            # Small delay to ensure file write is complete
            time.sleep(0.5)

            # Read plan frontmatter to determine type
            vault_service = self.executor_service.vault_service

            try:
                frontmatter, _ = vault_service.read_markdown_with_frontmatter(file_path)
            except Exception as e:
                logger.error(f"Failed to read plan file {file_path.name}: {e}")
                self.processing.discard(file_path)
                return

            # Determine plan type
            plan_type = frontmatter.get('type', '').lower()

            if plan_type == 'email_send':
                logger.info(f"Executing email plan: {file_path.name}")
                success, exec_log = self.executor_service.execute_email_plan(file_path)

                if success:
                    logger.info(
                        f"Email execution successful: {file_path.name} "
                        f"(log_id: {exec_log.log_id})"
                    )
                else:
                    logger.warning(
                        f"Email execution failed: {file_path.name} "
                        f"(error: {exec_log.error if exec_log else 'unknown'})"
                    )

            elif plan_type == 'social_media_post':
                logger.info(f"Executing social media post: {file_path.name}")
                success = self._execute_social_post(file_path, frontmatter)

                if success:
                    logger.info(f"Social post execution successful: {file_path.name}")
                else:
                    logger.warning(f"Social post execution failed: {file_path.name}")

            elif plan_type == 'scheduled_task':
                logger.info(f"Scheduled task detected: {file_path.name}")
                logger.warning("Scheduled task execution not yet implemented (US4)")

            else:
                logger.warning(
                    f"Unknown plan type '{plan_type}' in {file_path.name} - skipping"
                )

        except Exception as e:
            logger.exception(f"Error processing plan {file_path.name}: {e}")

        finally:
            # Remove from processing set
            self.processing.discard(file_path)

    def _execute_social_post(
        self,
        file_path: Path,
        frontmatter: Dict[str, Any]
    ) -> bool:
        """
        Execute social media post plan.

        Args:
            file_path: Path to social post plan file
            frontmatter: Parsed frontmatter from plan file

        Returns:
            bool: True if execution succeeded (fully or partially)
        """
        start_time = time.time()
        vault_service = self.executor_service.vault_service

        try:
            # Read full post data
            frontmatter, body = vault_service.read_markdown_with_frontmatter(file_path)

            # Check if scheduled for future (T047)
            scheduled_time_str = frontmatter.get('scheduled_time')
            if scheduled_time_str:
                from datetime import datetime, timezone
                scheduled_time = datetime.fromisoformat(
                    scheduled_time_str.replace('Z', '+00:00')
                )
                now = datetime.now(timezone.utc)

                if scheduled_time > now:
                    logger.info(
                        f"Post scheduled for future: {scheduled_time_str} "
                        f"- skipping execution"
                    )
                    return False  # Not an error, just not time yet

            # Create SocialMediaPost from plan
            post = SocialMediaPost.from_yaml_frontmatter(frontmatter, body)

            # Validate content length
            is_valid, errors = self.social_media_service.validate_platform_limits(post)
            if not is_valid:
                error_msg = "; ".join(f"{p.value}: {e}" for p, e in errors.items())
                logger.error(f"Content validation failed: {error_msg}")

                # Move back to Needs_Action with error
                post.error_details = error_msg
                vault_service.write_markdown_with_frontmatter(
                    file_path,
                    post.to_yaml_frontmatter(),
                    post.content
                )
                vault_service.move_file(file_path, "Needs_Action")
                return False

            # Execute post to all platforms
            all_succeeded, results = self.social_media_service.post_multi_platform(post)

            # Create execution log (T048)
            duration_ms = int((time.time() - start_time) * 1000)

            # Determine overall result
            if all_succeeded:
                result = Result.SUCCESS
            elif any(r.status.value == 'success' for r in results.values()):
                result = Result.PARTIAL
            else:
                result = Result.FAILURE

            # Get error details if any
            error_details = None
            if not all_succeeded:
                error_details = self.social_media_service.handle_partial_failure(post)

            exec_log = ExecutionLog.create(
                action_type=ActionType.SOCIAL_POST,
                actor=Actor.EXECUTOR,
                plan_id=file_path.name,
                target=", ".join(p.value for p in post.platforms),
                parameters={
                    'platforms': [p.value for p in post.platforms],
                    'content_preview': post.content[:100],
                    'needs_thread': post.needs_thread()
                },
                result=result,
                duration_ms=duration_ms,
                mcp_server="multiple",
                response={
                    'platform_results': {
                        p.value: r.to_dict() for p, r in results.items()
                    }
                },
                error=error_details
            )

            # Save execution log
            self.executor_service.create_execution_log(exec_log)

            # Update post file with results
            vault_service.write_markdown_with_frontmatter(
                file_path,
                post.to_yaml_frontmatter(),
                post.content
            )

            # Move to Done (even if partial - user can review platform_results)
            if result != Result.FAILURE:
                vault_service.move_file(file_path, "Done")
                return True
            else:
                # Total failure - move back to Needs_Action
                vault_service.move_file(file_path, "Needs_Action")
                return False

        except Exception as e:
            logger.exception(f"Error executing social post {file_path.name}: {e}")

            # Create failure log
            duration_ms = int((time.time() - start_time) * 1000)
            exec_log = ExecutionLog.create(
                action_type=ActionType.SOCIAL_POST,
                actor=Actor.EXECUTOR,
                plan_id=file_path.name,
                target="unknown",
                parameters={'error_type': 'unexpected_error'},
                result=Result.FAILURE,
                duration_ms=duration_ms,
                error=str(e)
            )
            self.executor_service.create_execution_log(exec_log)

            return False


class Executor:
    """
    Main executor process for Silver Tier US1.

    Monitors /Approved/ folder and executes approved plans.
    """

    def __init__(self, vault_path: str):
        """
        Initialize Executor.

        Args:
            vault_path: Absolute path to Obsidian vault
        """
        self.vault_path = Path(vault_path).resolve()
        self.approved_folder = self.vault_path / "Approved"

        # Ensure /Approved/ folder exists
        self.approved_folder.mkdir(parents=True, exist_ok=True)

        # Initialize services
        logger.info("Initializing services...")

        self.vault_service = VaultService(vault_path=self.vault_path)

        self.rate_limiter = RateLimiter(
            state_file=str(self.vault_path / "Logs" / "rate_limit_state.json")
        )

        self.plan_validator = PlanValidator(
            schema_base_path=project_root
        )

        # Get MCP URLs from environment
        mcp_urls = {
            "gmail": os.getenv("GMAIL_MCP_URL", "http://localhost:3001/gmail"),
            "linkedin": os.getenv("LINKEDIN_MCP_URL", "http://localhost:3002/linkedin"),
            "facebook": os.getenv("FACEBOOK_MCP_URL", "http://localhost:3003/facebook"),
            "twitter": os.getenv("TWITTER_MCP_URL", "http://localhost:3004/twitter"),
            "whatsapp": os.getenv("WHATSAPP_MCP_URL", "http://localhost:3005/whatsapp"),
        }

        self.executor_service = ExecutorService(
            vault_service=self.vault_service,
            rate_limiter=self.rate_limiter,
            plan_validator=self.plan_validator,
            mcp_urls=mcp_urls
        )

        # Initialize SocialMediaService (US2)
        social_mcp_clients = {}
        for platform in ['linkedin', 'facebook', 'twitter']:
            if platform in mcp_urls:
                social_mcp_clients[platform] = MCPClient(
                    server_url=mcp_urls[platform],
                    dry_run=os.getenv("DRY_RUN", "false").lower() == "true"
                )

        self.social_media_service = SocialMediaService(
            mcp_clients=social_mcp_clients,
            rate_limiter=self.rate_limiter
        )

        # Initialize watchdog
        self.observer = Observer()
        self.event_handler = ApprovedFolderHandler(
            self.executor_service,
            self.social_media_service
        )

        logger.info(f"Executor initialized (vault: {self.vault_path})")

    def start(self):
        """Start the executor process."""
        logger.info("Starting Executor...")
        logger.info(f"Monitoring folder: {self.approved_folder}")
        logger.info(f"DRY_RUN mode: {os.getenv('DRY_RUN', 'false')}")

        # Start watchdog observer
        self.observer.schedule(
            self.event_handler,
            str(self.approved_folder),
            recursive=False
        )
        self.observer.start()

        logger.info("Executor started successfully")

        # Log system start
        from src.services.logger_service import AuditLogger, ActionType, Actor, Result
        audit_logger = AuditLogger(vault_path=self.vault_path)
        audit_logger.log(
            action_type=ActionType.SYSTEM_START,
            actor=Actor.EXECUTOR,
            target="executor",
            parameters={"vault_path": str(self.vault_path)},
            result=Result.SUCCESS
        )

        # Main loop with heartbeat
        self._main_loop()

    def _main_loop(self):
        """
        Main event loop with heartbeat logging.

        Logs heartbeat every 60 seconds for health monitoring.
        Handles MCP connection failures gracefully.
        """
        from src.services.logger_service import AuditLogger, ActionType, Actor, Result

        audit_logger = AuditLogger(vault_path=self.vault_path)
        last_heartbeat = time.time()
        heartbeat_interval = 60  # seconds

        try:
            while True:
                # Check for heartbeat
                now = time.time()
                if now - last_heartbeat >= heartbeat_interval:
                    # Log heartbeat
                    audit_logger.log(
                        action_type=ActionType.HEARTBEAT,
                        actor=Actor.EXECUTOR,
                        target="executor",
                        parameters={
                            "uptime_seconds": int(now - last_heartbeat),
                            "approved_folder": str(self.approved_folder)
                        },
                        result=Result.SUCCESS
                    )
                    logger.debug("Heartbeat logged")
                    last_heartbeat = now

                # Sleep briefly to avoid busy loop
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Executor interrupted by user")
            self.stop()

        except Exception as e:
            logger.exception(f"Fatal error in main loop: {e}")
            self.stop()
            sys.exit(1)

    def stop(self):
        """Stop the executor process gracefully."""
        logger.info("Stopping Executor...")

        # Stop watchdog observer
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

        # Close executor service
        self.executor_service.close()

        # Close social media service MCP clients
        for client in self.social_media_service.mcp_clients.values():
            try:
                client.close()
            except Exception as e:
                logger.error(f"Error closing social media MCP client: {e}")

        # Log system stop
        from src.services.logger_service import AuditLogger, ActionType, Actor, Result
        audit_logger = AuditLogger(vault_path=self.vault_path)
        audit_logger.log(
            action_type=ActionType.SYSTEM_STOP,
            actor=Actor.EXECUTOR,
            target="executor",
            parameters={"reason": "graceful_shutdown"},
            result=Result.SUCCESS
        )

        logger.info("Executor stopped")


def main():
    """Main entry point for executor process."""
    # Load environment variables
    load_dotenv()

    # Get vault path from environment
    vault_path = os.getenv("VAULT_PATH")
    if not vault_path:
        logger.error("VAULT_PATH environment variable not set")
        sys.exit(1)

    vault_path = Path(vault_path).resolve()
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        sys.exit(1)

    # Create and start executor
    try:
        executor = Executor(vault_path=str(vault_path))
        executor.start()

    except KeyboardInterrupt:
        logger.info("Executor interrupted")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Failed to start executor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
