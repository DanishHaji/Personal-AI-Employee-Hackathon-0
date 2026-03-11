"""
Health Monitor Service for Platinum Tier

Monitors system health, watcher processes, and resource usage for Cloud/Local instances.
Provides watchdog supervision with auto-restart capabilities and alerting.

Constitutional Alignment:
- Principle VII: Observability & Audit Logging (complete health tracking)
- Principle VI: Proactive Intelligence (health predictions and alerts)

Part of Platinum Tier US3: Cloud Deployment & Health Monitoring
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import psutil


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """
    Resource usage metrics for system monitoring.

    Tracks CPU, memory, disk usage for health assessment.
    """
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    disk_free_gb: float
    load_average: tuple[float, float, float]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WatcherHealth:
    """
    Health status for individual watcher process.

    Tracks PID, uptime, restart count, error rate.
    """
    watcher_name: str
    pid: Optional[int]
    status: str  # "running", "stopped", "crashed", "restarting"
    uptime_seconds: int
    restart_count: int
    last_restart: Optional[str]
    error_count: int
    last_error: Optional[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealthStatus:
    """
    Overall health status snapshot for an instance.

    Aggregates resource metrics, watcher health, and system state.
    """
    instance: str  # "cloud" or "local"
    status: str  # "healthy", "degraded", "critical", "down"
    resources: ResourceMetrics
    watchers: Dict[str, WatcherHealth]
    alerts: List[str]
    last_vault_sync: Optional[str]
    uptime_seconds: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealthReport:
    """
    Daily/weekly health report with aggregated statistics.

    Used for trend analysis and proactive alerting.
    """
    instance: str
    report_type: str  # "daily", "weekly"
    start_time: str
    end_time: str
    uptime_percentage: float
    total_restarts: int
    average_cpu: float
    average_memory: float
    peak_cpu: float
    peak_memory: float
    total_alerts: int
    alert_breakdown: Dict[str, int]
    watcher_statistics: Dict[str, Dict[str, Any]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AlertManager:
    """
    Alert management with email, webhook support, and rate limiting.

    Handles critical alerts, disk space monitoring, and notification delivery.
    """

    def __init__(
        self,
        vault_path: Path,
        email_enabled: bool = False,
        webhook_url: Optional[str] = None,
        rate_limit_minutes: int = 30
    ):
        """
        Initialize AlertManager with notification channels.

        Args:
            vault_path: Path to vault for logging
            email_enabled: Enable email notifications
            webhook_url: Webhook URL for alerts (Slack, Discord, etc.)
            rate_limit_minutes: Minimum time between duplicate alerts
        """
        self.vault_path = Path(vault_path)
        self.email_enabled = email_enabled
        self.webhook_url = webhook_url
        self.rate_limit_minutes = rate_limit_minutes

        # Track last alert time for rate limiting
        self.last_alert_time: Dict[str, datetime] = {}

        # Disk space thresholds
        self.disk_warning_threshold_gb = 10.0
        self.disk_critical_threshold_gb = 5.0

        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.alerts_log = self.logs_dir / "alerts.jsonl"

    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert with rate limiting.

        Args:
            alert_type: Type of alert (disk_space, watcher_down, system_critical)
            severity: Severity level (info, warning, critical)
            message: Human-readable alert message
            details: Additional context for alert

        Returns:
            True if alert sent, False if rate-limited
        """
        # Rate limiting
        alert_key = f"{alert_type}:{severity}"
        now = datetime.now()

        if alert_key in self.last_alert_time:
            time_since_last = (now - self.last_alert_time[alert_key]).total_seconds() / 60
            if time_since_last < self.rate_limit_minutes:
                logger.debug(f"Alert rate-limited: {alert_key} (last: {time_since_last:.1f}m ago)")
                return False

        # Log alert
        alert_event = {
            "event": "alert_sent",
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": now.isoformat()
        }

        with open(self.alerts_log, "a") as f:
            f.write(json.dumps(alert_event) + "\n")

        logger.warning(f"ALERT [{severity.upper()}] {alert_type}: {message}")

        # Update rate limit tracker
        self.last_alert_time[alert_key] = now

        # Send via notification channels
        if severity == "critical":
            self._send_notification(alert_type, severity, message, details)

        return True

    def _send_notification(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]]
    ):
        """
        Send notification via configured channels (email, webhook).

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Alert message
            details: Additional context
        """
        # Email notification (if enabled)
        if self.email_enabled:
            # TODO: Integrate with email service when available
            logger.info(f"Email notification would be sent: {message}")

        # Webhook notification (if configured)
        if self.webhook_url:
            try:
                import httpx
                payload = {
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
                httpx.post(self.webhook_url, json=payload, timeout=10)
                logger.info(f"Webhook notification sent to {self.webhook_url}")
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")

    def check_disk_space(self) -> Optional[str]:
        """
        Check disk space and trigger auto log rotation if needed.

        Returns:
            Alert message if disk space critical, None otherwise
        """
        try:
            disk = psutil.disk_usage(str(self.vault_path))
            free_gb = disk.free / (1024 ** 3)

            if free_gb < self.disk_critical_threshold_gb:
                self.send_alert(
                    alert_type="disk_space",
                    severity="critical",
                    message=f"Disk space critical: {free_gb:.2f} GB free",
                    details={"free_gb": free_gb, "percent": disk.percent}
                )

                # Auto log rotation
                self._rotate_logs()

                return f"Disk space critical: {free_gb:.2f} GB free"

            elif free_gb < self.disk_warning_threshold_gb:
                self.send_alert(
                    alert_type="disk_space",
                    severity="warning",
                    message=f"Disk space low: {free_gb:.2f} GB free",
                    details={"free_gb": free_gb, "percent": disk.percent}
                )

                return f"Disk space low: {free_gb:.2f} GB free"

            return None

        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return None

    def _rotate_logs(self):
        """
        Rotate old log files to free disk space.

        Keeps last 7 days of logs, archives older logs.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=7)

            for log_file in self.logs_dir.glob("*.jsonl"):
                # Check file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if mtime < cutoff_date:
                    archive_path = self.logs_dir / "archive"
                    archive_path.mkdir(exist_ok=True)

                    # Move to archive
                    log_file.rename(archive_path / log_file.name)
                    logger.info(f"Archived old log file: {log_file.name}")

            logger.info("Log rotation completed")

        except Exception as e:
            logger.error(f"Failed to rotate logs: {e}")


class HealthMonitor:
    """
    Health monitoring service with watchdog supervision.

    Monitors system resources, watcher processes, and triggers auto-restart on failures.
    Generates daily/weekly health reports and sends critical alerts.
    """

    def __init__(
        self,
        vault_path: str | Path,
        instance: str = "local",
        check_interval_seconds: int = 60,
        restart_threshold_failures: int = 3,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0
    ):
        """
        Initialize HealthMonitor with thresholds and psutil setup.

        Args:
            vault_path: Path to vault directory
            instance: "cloud" or "local"
            check_interval_seconds: Health check frequency
            restart_threshold_failures: Max failures before restart
            cpu_threshold: CPU usage alert threshold (%)
            memory_threshold: Memory usage alert threshold (%)
            disk_threshold: Disk usage alert threshold (%)
        """
        self.vault_path = Path(vault_path)
        self.instance = instance
        self.check_interval = check_interval_seconds
        self.restart_threshold = restart_threshold_failures

        # Thresholds
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

        # Initialize AlertManager
        self.alert_manager = AlertManager(self.vault_path)

        # Watcher configurations
        self.watchers = {
            "gmail-watcher": {
                "service": "gmail-watcher.service",
                "enabled": True,
                "failures": 0
            },
            "filesystem-watcher": {
                "service": "filesystem-watcher.service",
                "enabled": True,
                "failures": 0
            }
        }

        # WhatsApp watcher only on local
        if instance == "local":
            self.watchers["whatsapp-watcher"] = {
                "service": "whatsapp-watcher.service",
                "enabled": True,
                "failures": 0
            }

        # Health tracking
        self.health_dir = self.vault_path / "Health"
        self.health_dir.mkdir(exist_ok=True)

        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(exist_ok=True)

        self.health_log = self.logs_dir / "health.jsonl"

        # Start time for uptime tracking
        self.start_time = datetime.now()

    def collect_health_snapshot(self) -> HealthStatus:
        """
        Gather current health metrics snapshot.

        Collects resource usage, watcher health, and system state.

        Returns:
            HealthStatus snapshot
        """
        # Collect resource metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.vault_path))
        load_avg = psutil.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0)

        resources = ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            disk_free_gb=disk.free / (1024 ** 3),
            load_average=load_avg
        )

        # Check watcher health
        watchers_health = {}
        for watcher_name, config in self.watchers.items():
            if config["enabled"]:
                watchers_health[watcher_name] = self.check_watcher_health(watcher_name, config)

        # Determine overall status
        alerts = []
        status = "healthy"

        if cpu_percent > self.cpu_threshold:
            alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
            status = "degraded"

        if memory.percent > self.memory_threshold:
            alerts.append(f"High memory usage: {memory.percent:.1f}%")
            status = "degraded"

        if disk.percent > self.disk_threshold:
            alerts.append(f"High disk usage: {disk.percent:.1f}%")
            status = "critical"

        # Check for stopped watchers
        for watcher_name, watcher_health in watchers_health.items():
            if watcher_health.status == "stopped":
                alerts.append(f"Watcher down: {watcher_name}")
                status = "critical" if status != "critical" else "critical"

        # Get last vault sync time
        last_sync = self._get_last_vault_sync()

        # Calculate uptime
        uptime = int((datetime.now() - self.start_time).total_seconds())

        snapshot = HealthStatus(
            instance=self.instance,
            status=status,
            resources=resources,
            watchers=watchers_health,
            alerts=alerts,
            last_vault_sync=last_sync,
            uptime_seconds=uptime
        )

        # Save snapshot
        self._save_health_snapshot(snapshot)

        # Log to health.jsonl
        with open(self.health_log, "a") as f:
            f.write(json.dumps({
                "event": "health_snapshot",
                "instance": self.instance,
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            }) + "\n")

        return snapshot

    def check_watcher_health(self, watcher_name: str, config: Dict[str, Any]) -> WatcherHealth:
        """
        Check health of individual watcher process.

        Args:
            watcher_name: Name of watcher
            config: Watcher configuration

        Returns:
            WatcherHealth status
        """
        service_name = config["service"]

        try:
            # Check systemd service status
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            is_running = result.returncode == 0

            if is_running:
                # Get PID
                pid_result = subprocess.run(
                    ["systemctl", "show", "-p", "MainPID", service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                pid_str = pid_result.stdout.strip().split("=")[1]
                pid = int(pid_str) if pid_str and pid_str != "0" else None

                # Get uptime
                if pid:
                    try:
                        process = psutil.Process(pid)
                        create_time = process.create_time()
                        uptime = int(time.time() - create_time)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        uptime = 0
                else:
                    uptime = 0

                # Reset failure count on successful check
                config["failures"] = 0

                return WatcherHealth(
                    watcher_name=watcher_name,
                    pid=pid,
                    status="running",
                    uptime_seconds=uptime,
                    restart_count=0,  # TODO: Track in persistent state
                    last_restart=None,
                    error_count=0,
                    last_error=None
                )

            else:
                # Watcher stopped
                config["failures"] += 1

                return WatcherHealth(
                    watcher_name=watcher_name,
                    pid=None,
                    status="stopped",
                    uptime_seconds=0,
                    restart_count=0,
                    last_restart=None,
                    error_count=config["failures"],
                    last_error=f"Service {service_name} not active"
                )

        except Exception as e:
            logger.error(f"Failed to check watcher health for {watcher_name}: {e}")
            config["failures"] += 1

            return WatcherHealth(
                watcher_name=watcher_name,
                pid=None,
                status="crashed",
                uptime_seconds=0,
                restart_count=0,
                last_restart=None,
                error_count=config["failures"],
                last_error=str(e)
            )

    def restart_watcher(self, watcher_name: str, config: Dict[str, Any]) -> bool:
        """
        Restart watcher via systemctl restart.

        Args:
            watcher_name: Name of watcher
            config: Watcher configuration

        Returns:
            True if restart successful, False otherwise
        """
        service_name = config["service"]

        try:
            logger.warning(f"Restarting watcher: {watcher_name} ({service_name})")

            # Send alert
            self.alert_manager.send_alert(
                alert_type="watcher_restart",
                severity="warning",
                message=f"Restarting watcher: {watcher_name}",
                details={"service": service_name, "failures": config["failures"]}
            )

            # Restart service
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Successfully restarted {watcher_name}")
                config["failures"] = 0

                # Log restart event
                with open(self.health_log, "a") as f:
                    f.write(json.dumps({
                        "event": "watcher_restarted",
                        "watcher": watcher_name,
                        "service": service_name,
                        "timestamp": datetime.now().isoformat()
                    }) + "\n")

                return True

            else:
                logger.error(f"Failed to restart {watcher_name}: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to restart {watcher_name}: {e}")
            return False

    def start_watchdog(self):
        """
        Start main monitoring loop (blocking).

        Continuously monitors health and restarts failed watchers.
        Sends watchdog notifications to systemd.
        """
        logger.info(f"Starting health watchdog for {self.instance} instance")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Monitoring watchers: {list(self.watchers.keys())}")

        while True:
            try:
                # Collect health snapshot
                snapshot = self.collect_health_snapshot()

                # Check for critical alerts
                if snapshot.status == "critical":
                    self.alert_manager.send_alert(
                        alert_type="system_critical",
                        severity="critical",
                        message=f"System health critical on {self.instance}",
                        details={"alerts": snapshot.alerts}
                    )

                # Check disk space
                self.alert_manager.check_disk_space()

                # Check and restart failed watchers
                for watcher_name, config in self.watchers.items():
                    if config["enabled"]:
                        watcher_health = snapshot.watchers.get(watcher_name)

                        if watcher_health and watcher_health.status in ["stopped", "crashed"]:
                            if config["failures"] >= self.restart_threshold:
                                logger.warning(
                                    f"Watcher {watcher_name} failed {config['failures']} times, "
                                    f"restarting..."
                                )
                                self.restart_watcher(watcher_name, config)

                # Notify systemd watchdog (if available)
                self._notify_watchdog()

                # Sleep until next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Health watchdog stopped by user")
                break

            except Exception as e:
                logger.error(f"Error in watchdog loop: {e}")
                time.sleep(self.check_interval)

    def generate_daily_report(self, date: Optional[str] = None) -> HealthReport:
        """
        Generate daily health report aggregating 24h snapshots.

        Args:
            date: Date to generate report for (YYYY-MM-DD), defaults to yesterday

        Returns:
            HealthReport with aggregated statistics
        """
        if date is None:
            report_date = datetime.now() - timedelta(days=1)
        else:
            report_date = datetime.fromisoformat(date)

        start_time = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        # Collect snapshots for the day
        snapshots = self._load_snapshots_in_range(start_time, end_time)

        if not snapshots:
            logger.warning(f"No health snapshots found for {report_date.date()}")
            return HealthReport(
                instance=self.instance,
                report_type="daily",
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                uptime_percentage=0.0,
                total_restarts=0,
                average_cpu=0.0,
                average_memory=0.0,
                peak_cpu=0.0,
                peak_memory=0.0,
                total_alerts=0,
                alert_breakdown={},
                watcher_statistics={}
            )

        # Aggregate metrics
        total_snapshots = len(snapshots)
        healthy_snapshots = sum(1 for s in snapshots if s["status"] == "healthy")
        uptime_percentage = (healthy_snapshots / total_snapshots) * 100

        cpu_values = [s["resources"]["cpu_percent"] for s in snapshots]
        memory_values = [s["resources"]["memory_percent"] for s in snapshots]

        average_cpu = sum(cpu_values) / len(cpu_values)
        average_memory = sum(memory_values) / len(memory_values)
        peak_cpu = max(cpu_values)
        peak_memory = max(memory_values)

        # Count alerts
        all_alerts = []
        for s in snapshots:
            all_alerts.extend(s.get("alerts", []))

        total_alerts = len(all_alerts)
        alert_breakdown = {}
        for alert in all_alerts:
            alert_type = alert.split(":")[0] if ":" in alert else alert
            alert_breakdown[alert_type] = alert_breakdown.get(alert_type, 0) + 1

        # Watcher statistics
        watcher_statistics = {}
        for watcher_name in self.watchers.keys():
            running_count = sum(
                1 for s in snapshots
                if watcher_name in s.get("watchers", {})
                and s["watchers"][watcher_name]["status"] == "running"
            )
            watcher_statistics[watcher_name] = {
                "uptime_percentage": (running_count / total_snapshots) * 100,
                "total_checks": total_snapshots
            }

        report = HealthReport(
            instance=self.instance,
            report_type="daily",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            uptime_percentage=uptime_percentage,
            total_restarts=0,  # TODO: Count from restart events
            average_cpu=average_cpu,
            average_memory=average_memory,
            peak_cpu=peak_cpu,
            peak_memory=peak_memory,
            total_alerts=total_alerts,
            alert_breakdown=alert_breakdown,
            watcher_statistics=watcher_statistics
        )

        # Save report
        report_file = self.health_dir / f"{self.instance}_daily_{report_date.date()}.report.json"
        with open(report_file, "w") as f:
            json.dump(asdict(report), f, indent=2)

        logger.info(f"Daily report generated: {report_file}")

        return report

    def _save_health_snapshot(self, snapshot: HealthStatus):
        """
        Save health snapshot to vault/Health/{instance}_{timestamp}.health.json.

        Args:
            snapshot: HealthStatus to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.instance}_{timestamp}.health.json"
        filepath = self.health_dir / filename

        # Convert to dict
        snapshot_dict = asdict(snapshot)

        with open(filepath, "w") as f:
            json.dump(snapshot_dict, f, indent=2)

    def _load_snapshots_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Load health snapshots within time range.

        Args:
            start_time: Start of range
            end_time: End of range

        Returns:
            List of snapshot dictionaries
        """
        snapshots = []

        for snapshot_file in self.health_dir.glob(f"{self.instance}_*.health.json"):
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)

                snapshot_time = datetime.fromisoformat(data["timestamp"])

                if start_time <= snapshot_time < end_time:
                    snapshots.append(data)

            except Exception as e:
                logger.error(f"Failed to load snapshot {snapshot_file}: {e}")

        return sorted(snapshots, key=lambda x: x["timestamp"])

    def _get_last_vault_sync(self) -> Optional[str]:
        """
        Get timestamp of last vault sync from sync.jsonl.

        Returns:
            ISO timestamp of last sync, or None if no syncs found
        """
        sync_log = self.logs_dir / "sync.jsonl"

        if not sync_log.exists():
            return None

        try:
            last_sync = None
            with open(sync_log) as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("event") == "sync_completed":
                            last_sync = event.get("timestamp")
                    except json.JSONDecodeError:
                        continue

            return last_sync

        except Exception as e:
            logger.error(f"Failed to read sync log: {e}")
            return None

    def _notify_watchdog(self):
        """
        Send watchdog notification to systemd with sd_notify("WATCHDOG=1").

        Requires systemd Python bindings (systemd-python).
        """
        try:
            # Try to notify systemd watchdog
            # This requires systemd-python package
            subprocess.run(
                ["systemd-notify", "WATCHDOG=1"],
                capture_output=True,
                timeout=5,
                check=False
            )
        except Exception:
            # Watchdog notification not critical, skip silently
            pass


def main():
    """
    CLI interface for HealthMonitor.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Health Monitor for Platinum Tier")
    parser.add_argument(
        "command",
        choices=["start", "snapshot", "report"],
        help="Command to run"
    )
    parser.add_argument(
        "--vault-path",
        default=os.getenv("VAULT_PATH", "."),
        help="Path to vault directory"
    )
    parser.add_argument(
        "--instance",
        choices=["cloud", "local"],
        default=os.getenv("INSTANCE", "local"),
        help="Instance type (cloud or local)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--date",
        help="Date for report generation (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    monitor = HealthMonitor(
        vault_path=args.vault_path,
        instance=args.instance,
        check_interval_seconds=args.interval
    )

    if args.command == "start":
        # Start watchdog (blocking)
        monitor.start_watchdog()

    elif args.command == "snapshot":
        # Take single snapshot
        snapshot = monitor.collect_health_snapshot()
        print(f"Health Status: {snapshot.status}")
        print(f"CPU: {snapshot.resources.cpu_percent:.1f}%")
        print(f"Memory: {snapshot.resources.memory_percent:.1f}%")
        print(f"Disk: {snapshot.resources.disk_percent:.1f}%")
        print(f"Alerts: {len(snapshot.alerts)}")
        for alert in snapshot.alerts:
            print(f"  - {alert}")

    elif args.command == "report":
        # Generate daily report
        report = monitor.generate_daily_report(date=args.date)
        print(f"Daily Report for {args.instance}")
        print(f"Uptime: {report.uptime_percentage:.1f}%")
        print(f"Avg CPU: {report.average_cpu:.1f}%")
        print(f"Peak CPU: {report.peak_cpu:.1f}%")
        print(f"Avg Memory: {report.average_memory:.1f}%")
        print(f"Peak Memory: {report.peak_memory:.1f}%")
        print(f"Total Alerts: {report.total_alerts}")


if __name__ == "__main__":
    main()
