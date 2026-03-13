#!/usr/bin/env python3
"""
Scheduler - Silver Tier US4 Main Process

Executes scheduled tasks (daily briefings, weekly summaries, custom tasks) using APScheduler.
Monitors Company_Handbook.md for task configuration changes and reloads without restart.

Workflow:
1. Initialize APScheduler BackgroundScheduler
2. Load scheduled tasks from Company_Handbook.md
3. Add jobs with CronTrigger based on schedule_pattern
4. Execute tasks at scheduled times via SchedulerService
5. Handle missed executions (within grace period)
6. Reload tasks when handbook changes

PM2 Configuration:
    pm2 start src/scheduler.py --name scheduler --interpreter python3
    pm2 logs scheduler
    pm2 stop scheduler
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not found. Install with: uv pip install python-dotenv")
    sys.exit(1)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
except ImportError:
    print("ERROR: APScheduler not found. Install with: uv pip install apscheduler")
    sys.exit(1)

from src.services.scheduler_service import SchedulerService
from src.services.vault_service import VaultService
from src.services.logger_service import AuditLogger, Actor, ActionType, Result
from src.models.scheduled_task import ScheduledTask, TaskType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Scheduler:
    """
    Main scheduler process for Silver Tier US4.

    Uses APScheduler to execute scheduled tasks at specified times.
    Monitors Company_Handbook.md for configuration changes.
    """

    def __init__(self, vault_path: str, instance: str = "local"):
        """
        Initialize Scheduler.

        Args:
            vault_path: Absolute path to Obsidian vault
            instance: Instance identifier ("cloud" or "local")
        """
        self.vault_path = Path(vault_path).resolve()
        self.instance = instance

        # Initialize services
        self.vault_service = VaultService(vault_path=self.vault_path)
        self.audit_logger = AuditLogger(vault_path=self.vault_path)
        self.scheduler_service = SchedulerService(
            vault_service=self.vault_service,
            audit_logger=self.audit_logger
        )

        # Initialize APScheduler
        self.scheduler = BackgroundScheduler(timezone='UTC')

        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        self.scheduler.add_listener(
            self._job_missed_listener,
            EVENT_JOB_MISSED
        )

        # Track handbook modification time for reload detection
        self.handbook_path = self.vault_path / "Company_Handbook.md"
        self.last_handbook_mtime: Optional[float] = None

        # Task registry
        self.tasks: Dict[str, ScheduledTask] = {}

        logger.info(f"Scheduler initialized (vault: {self.vault_path})")

    def start(self):
        """Start the scheduler process."""
        logger.info("Starting Scheduler...")

        # Load tasks from handbook
        self._load_tasks()

        # Start APScheduler
        self.scheduler.start()

        logger.info("✅ Scheduler started successfully")

        # Log system start
        self.audit_logger.log(
            action_type=ActionType.SYSTEM_START,
            actor=Actor.SCHEDULER,
            target="scheduler",
            parameters={"vault_path": str(self.vault_path)},
            result=Result.SUCCESS
        )

        # Main loop - monitor handbook for changes
        self._main_loop()

    def _load_tasks(self):
        """Load scheduled tasks from Company_Handbook.md."""
        logger.info("Loading scheduled tasks from handbook")

        # Update handbook modification time
        if self.handbook_path.exists():
            self.last_handbook_mtime = self.handbook_path.stat().st_mtime

        # Load tasks
        tasks = self.scheduler_service.load_tasks_from_handbook()

        if not tasks:
            logger.warning("No scheduled tasks found in handbook")
            return

        # Remove existing jobs
        for job_id in list(self.tasks.keys()):
            self.scheduler.remove_job(job_id)
            logger.debug(f"Removed existing job: {job_id}")

        # Clear task registry
        self.tasks.clear()

        # Add tasks to scheduler
        for task in tasks:
            if not task.enabled:
                logger.info(f"Skipping disabled task: {task.task_id}")
                continue

            try:
                # Create CronTrigger from schedule_pattern
                trigger = CronTrigger.from_crontab(task.schedule_pattern)

                # Add job to scheduler
                self.scheduler.add_job(
                    func=self._execute_task,
                    trigger=trigger,
                    id=task.task_id,
                    name=task.task_name,
                    args=[task],
                    replace_existing=True
                )

                # Store task in registry
                self.tasks[task.task_id] = task

                # Calculate next execution
                task.calculate_next_execution()

                logger.info(
                    f"✅ Scheduled task: {task.task_id} ({task.task_name}) "
                    f"- Next: {task.next_execution}"
                )

                # Check for missed executions
                if task.was_missed(grace_period_minutes=60):
                    logger.warning(f"Task {task.task_id} has missed execution - catching up")
                    self.scheduler_service.handle_missed_execution(task)

            except Exception as e:
                logger.error(f"Failed to schedule task {task.task_id}: {e}")
                continue

        logger.info(f"Loaded {len(self.tasks)} scheduled tasks")

        # Update schedule state
        self.scheduler_service.update_schedule_state()

    def _execute_task(self, task: ScheduledTask):
        """
        Execute a scheduled task.

        Args:
            task: ScheduledTask to execute
        """
        logger.info(f"Executing scheduled task: {task.task_id} ({task.task_name})")

        try:
            # Execute based on task type
            if task.task_type == TaskType.DAILY_BRIEFING:
                result_path = self.scheduler_service.generate_daily_briefing(task)
                success = result_path is not None

            elif task.task_type == TaskType.WEEKLY_SUMMARY:
                result_path = self.scheduler_service.generate_weekly_summary(task)
                success = result_path is not None

            elif task.task_type == TaskType.MONTHLY_REPORT:
                # Platinum Tier US5 - Financial reports
                success = self._generate_monthly_financial_report(task)

            elif task.task_type == TaskType.CUSTOM:
                success = self.scheduler_service.execute_custom_task(task)

            else:
                logger.warning(f"Unknown task type: {task.task_type}")
                success = False

            if success:
                logger.info(f"✅ Task executed successfully: {task.task_id}")

                # Update task execution state
                task.mark_executed(datetime.now(timezone.utc))

                # Update schedule state
                self.scheduler_service.update_schedule_state()

            else:
                logger.error(f"❌ Task execution failed: {task.task_id}")

        except Exception as e:
            logger.exception(f"Error executing task {task.task_id}: {e}")

            # Log error
            self.audit_logger.log_error(
                actor=Actor.SCHEDULER,
                error_message=str(e),
                error_type=type(e).__name__,
                target=task.task_id
            )

    def _job_executed_listener(self, event):
        """APScheduler job executed event listener."""
        job_id = event.job_id
        logger.debug(f"Job executed: {job_id}")

    def _job_error_listener(self, event):
        """APScheduler job error event listener."""
        job_id = event.job_id
        exception = event.exception
        logger.error(f"Job error: {job_id} - {exception}")

        # Log to audit
        self.audit_logger.log_error(
            actor=Actor.SCHEDULER,
            error_message=str(exception),
            error_type=type(exception).__name__,
            target=job_id
        )

    def _job_missed_listener(self, event):
        """APScheduler job missed event listener."""
        job_id = event.job_id
        logger.warning(f"Job missed: {job_id}")

        # Attempt to handle missed execution
        if job_id in self.tasks:
            task = self.tasks[job_id]
            self.scheduler_service.handle_missed_execution(task)

    def _check_handbook_changes(self) -> bool:
        """
        Check if Company_Handbook.md has been modified.

        Returns:
            True if handbook was modified, False otherwise
        """
        if not self.handbook_path.exists():
            return False

        current_mtime = self.handbook_path.stat().st_mtime

        if self.last_handbook_mtime is None:
            self.last_handbook_mtime = current_mtime
            return False

        if current_mtime > self.last_handbook_mtime:
            logger.info("📋 Company_Handbook.md changed - reloading tasks")
            self.last_handbook_mtime = current_mtime
            return True

        return False

    def _main_loop(self):
        """
        Main event loop.

        Monitors handbook for changes and reloads tasks without restart.
        Writes heartbeat every 60 seconds.
        """
        heartbeat_interval = 60  # seconds
        handbook_check_interval = 30  # seconds
        last_heartbeat = time.time()
        last_handbook_check = time.time()

        try:
            while True:
                now = time.time()

                # Check for heartbeat
                if now - last_heartbeat >= heartbeat_interval:
                    self._write_heartbeat()
                    last_heartbeat = now

                # Check for handbook changes
                if now - last_handbook_check >= handbook_check_interval:
                    if self._check_handbook_changes():
                        self._load_tasks()
                    last_handbook_check = now

                # Sleep briefly to avoid busy loop
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
            self.stop()

        except Exception as e:
            logger.exception(f"Fatal error in main loop: {e}")
            self.stop()
            sys.exit(1)

    def _write_heartbeat(self):
        """Write heartbeat timestamp to /Logs/heartbeat.json."""
        import json

        heartbeat_file = self.vault_path / "Logs" / "heartbeat.json"

        # Read existing heartbeat data
        heartbeat_data = {}
        if heartbeat_file.exists():
            try:
                with open(heartbeat_file, 'r', encoding='utf-8') as f:
                    heartbeat_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                heartbeat_data = {}

        # Update scheduler entry
        heartbeat_data['scheduler'] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "instance": self.instance,
            "status": "running",
            "tasks_loaded": len(self.tasks),
            "next_task": self._get_next_task_time()
        }

        # Atomic write
        temp_file = heartbeat_file.with_suffix('.tmp')
        try:
            heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(heartbeat_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(heartbeat_file)
            logger.debug("Heartbeat written")
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")
            if temp_file.exists():
                temp_file.unlink()

    def _get_next_task_time(self) -> Optional[str]:
        """Get the next scheduled task execution time."""
        next_times = []
        for task in self.tasks.values():
            if task.enabled and task.next_execution:
                next_times.append(task.next_execution)

        if next_times:
            return min(next_times)
        return None

    def _generate_monthly_financial_report(self, task: ScheduledTask) -> bool:
        """
        Generate monthly financial report (Platinum Tier US5).

        Args:
            task: ScheduledTask to execute

        Returns:
            bool: True if successful, False otherwise
        """
        import subprocess
        from datetime import date

        try:
            # Get month from task parameters or use current
            month = task.parameters.get("month") or date.today().strftime("%Y-%m")

            logger.info(f"Generating monthly financial report for {month}")

            # Run monthly report generator
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.scripts.generate_monthly_report",
                    month
                ],
                cwd=str(self.vault_path.parent),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info(f"✅ Monthly report generated successfully for {month}")

                # Log to audit
                self.audit_logger.log(
                    action_type=ActionType.TASK_EXECUTION,
                    actor=Actor.SCHEDULER,
                    target=task.task_id,
                    parameters={"month": month, "task_type": "monthly_report"},
                    result=Result.SUCCESS
                )

                return True
            else:
                logger.error(f"Monthly report generation failed: {result.stderr}")

                # Log error
                self.audit_logger.log_error(
                    actor=Actor.SCHEDULER,
                    error_message=result.stderr,
                    error_type="MonthlyReportError",
                    target=task.task_id
                )

                return False

        except subprocess.TimeoutExpired:
            logger.error("Monthly report generation timed out after 5 minutes")
            return False

        except Exception as e:
            logger.exception(f"Error generating monthly report: {e}")

            # Log error
            self.audit_logger.log_error(
                actor=Actor.SCHEDULER,
                error_message=str(e),
                error_type=type(e).__name__,
                target=task.task_id
            )

            return False

    def stop(self):
        """Stop the scheduler process gracefully."""
        logger.info("Stopping Scheduler...")

        # Shutdown APScheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

        # Log system stop
        self.audit_logger.log(
            action_type=ActionType.SYSTEM_STOP,
            actor=Actor.SCHEDULER,
            target="scheduler",
            parameters={"reason": "graceful_shutdown"},
            result=Result.SUCCESS
        )

        logger.info("Scheduler stopped")


def main():
    """Main entry point for scheduler process."""
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

    # Create and start scheduler
    try:
        scheduler = Scheduler(vault_path=str(vault_path))
        scheduler.start()

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Failed to start scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
