#!/usr/bin/env python3
"""
WhatsApp Watcher - Silver Tier US3

Monitors WhatsApp Business API for incoming messages every 60 seconds.
Creates WhatsAppMessage entities in /Needs_Action/ folder.

Workflow:
1. Poll WhatsApp MCP server for new messages
2. Load priority contacts from Company_Handbook.md
3. Process each new message (create entity)
4. Download media attachments
5. Write heartbeat every 60 seconds

PM2 Configuration:
    pm2 start src/watchers/whatsapp_watcher.py --name whatsapp-watcher --interpreter python3
    pm2 logs whatsapp-watcher
    pm2 stop whatsapp-watcher
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not found. Install with: uv pip install python-dotenv")
    sys.exit(1)

from src.watchers.base_watcher import BaseWatcher
from src.services.whatsapp_service import WhatsAppService
from src.services.mcp_client import MCPClient, MCPErrorType
from src.services.vault_service import VaultService
from src.services.logger_service import AuditLogger, Actor, ActionType, Result


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class WhatsAppWatcher(BaseWatcher):
    """
    WhatsApp Business message watcher.

    Extends BaseWatcher to monitor WhatsApp Business API for incoming messages.
    Implements exponential backoff for MCP connection failures and alert creation
    when API is down for >10 minutes.
    """

    def __init__(
        self,
        vault_path: str,
        whatsapp_mcp_url: str,
        check_interval: int = 60,
        dry_run: bool = False
    ):
        """
        Initialize WhatsAppWatcher.

        Args:
            vault_path: Absolute path to Obsidian vault
            whatsapp_mcp_url: WhatsApp MCP server URL
            check_interval: Polling interval in seconds (default: 60)
            dry_run: If True, simulate polling without actual MCP calls
        """
        super().__init__(
            vault_path=vault_path,
            watcher_name="whatsapp_watcher",
            check_interval=check_interval
        )

        self.whatsapp_mcp_url = whatsapp_mcp_url
        self.dry_run = dry_run

        # Initialize services
        self.vault_service = VaultService(vault_path=self.vault_path)

        self.mcp_client = MCPClient(
            server_url=whatsapp_mcp_url,
            dry_run=dry_run
        )

        # WhatsAppService will be initialized after loading priority contacts
        self.whatsapp_service: Optional[WhatsAppService] = None

        # Error handling state
        self.connection_failures = 0
        self.last_connection_error: Optional[datetime] = None
        self.backoff_delay = 5  # Start with 5 seconds
        self.max_backoff = 120  # Max 2 minutes
        self.alert_created = False  # Track if we've created an alert

        logger.info(
            f"WhatsAppWatcher initialized (MCP: {whatsapp_mcp_url}, "
            f"interval: {check_interval}s, dry_run: {dry_run})"
        )

    def _get_processed_count_key(self) -> str:
        """Override to use WhatsApp-specific key."""
        return "messages_processed_today"

    def _perform_check(self) -> None:
        """
        Perform WhatsApp message polling check.

        Implements BaseWatcher abstract method.
        Handles MCP connection failures with exponential backoff.
        """
        logger.debug("Polling WhatsApp for new messages")

        try:
            # Initialize WhatsAppService on first check
            # (loads priority contacts from handbook)
            if self.whatsapp_service is None:
                self._initialize_service()

            # Poll for new messages
            messages = self.whatsapp_service.poll_messages()

            # Reset error state on successful poll
            if self.connection_failures > 0:
                logger.info("✅ WhatsApp MCP connection restored")
                self.connection_failures = 0
                self.last_connection_error = None
                self.backoff_delay = 5
                self.alert_created = False

            # Process each message
            for message in messages:
                try:
                    # Create entity in /Needs_Action/
                    entity_path = self.whatsapp_service.create_message_entity(message)

                    # Log message detection
                    self.logger.log(
                        action_type=ActionType.WHATSAPP_DETECT,
                        actor=Actor.WHATSAPP_WATCHER,
                        target=str(entity_path.name),
                        parameters={
                            'sender_phone': message.sender_phone,
                            'sender_name': message.sender_name,
                            'priority': message.priority.value,
                            'has_media': message.has_media(),
                            'media_count': message.get_media_count()
                        },
                        result=Result.SUCCESS
                    )

                    # Increment processed count
                    self.increment_processed_count()

                    logger.info(
                        f"✅ Processed message from {message.sender_phone} "
                        f"(priority: {message.priority.value})"
                    )

                except Exception as e:
                    logger.exception(f"Failed to process message {message.message_id}: {e}")
                    self.logger.log_error(
                        actor=Actor.WHATSAPP_WATCHER,
                        error_message=str(e),
                        error_type=type(e).__name__,
                        target=message.message_id
                    )

        except ConnectionError as e:
            # MCP connection failed - handle with exponential backoff
            self._handle_connection_error(e)

        except Exception as e:
            # Other errors - log but continue
            logger.exception(f"Error during WhatsApp check: {e}")
            self.logger.log_error(
                actor=Actor.WHATSAPP_WATCHER,
                error_message=str(e),
                error_type=type(e).__name__,
                target="perform_check"
            )

    def _initialize_service(self):
        """Initialize WhatsAppService with priority contacts from handbook."""
        logger.info("Initializing WhatsAppService...")

        # Create service with empty priority list
        self.whatsapp_service = WhatsAppService(
            mcp_client=self.mcp_client,
            vault_service=self.vault_service,
            priority_contacts=[]
        )

        # Load priority contacts from Company_Handbook.md
        priority_contacts = self.whatsapp_service.load_priority_contacts_from_handbook()

        if priority_contacts:
            logger.info(f"Loaded {len(priority_contacts)} priority contacts from handbook")
        else:
            logger.debug("No priority contacts found in handbook")

    def _handle_connection_error(self, error: Exception):
        """
        Handle MCP connection failure with exponential backoff.

        Implements T064 - Error handling with exponential backoff (5s, 30s, 2m).
        Implements T065 - Alert creation when API is down for >10 minutes.

        Args:
            error: Connection error exception
        """
        self.connection_failures += 1
        self.last_connection_error = datetime.now(timezone.utc)

        # Calculate downtime
        downtime_seconds = 0
        if self.connection_failures > 1:
            # Approximate downtime based on check_interval and failures
            downtime_seconds = (self.connection_failures - 1) * self.check_interval

        logger.error(
            f"❌ WhatsApp MCP connection failed (attempt {self.connection_failures}): {error}"
        )

        # Log connection error
        self.logger.log_error(
            actor=Actor.WHATSAPP_WATCHER,
            error_message=str(error),
            error_type="MCPConnectionError",
            target="whatsapp_mcp_server"
        )

        # Exponential backoff: 5s, 30s, 2m (120s)
        if self.connection_failures == 1:
            self.backoff_delay = 5  # 5 seconds
        elif self.connection_failures == 2:
            self.backoff_delay = 30  # 30 seconds
        elif self.connection_failures >= 3:
            self.backoff_delay = 120  # 2 minutes (max)

        logger.info(f"Backing off for {self.backoff_delay} seconds before retry")
        time.sleep(self.backoff_delay)

        # Create alert if API down for >10 minutes (600 seconds)
        # 10 minutes = 600s / 60s check_interval = 10 consecutive failures
        if downtime_seconds > 600 and not self.alert_created:
            self._create_api_down_alert(downtime_seconds)
            self.alert_created = True

    def _create_api_down_alert(self, downtime_seconds: int):
        """
        Create alert when WhatsApp API is down for >10 minutes.

        Implements T065 - Alert creation for prolonged API downtime.

        Args:
            downtime_seconds: Estimated downtime in seconds
        """
        logger.warning(
            f"⚠️  WhatsApp API down for {downtime_seconds}s "
            f"({downtime_seconds // 60} minutes) - creating alert"
        )

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_filename = f"ALERT_whatsapp_api_down_{timestamp}.md"
            alert_path = self.vault_path / "Needs_Action" / alert_filename

            downtime_minutes = downtime_seconds // 60

            alert_content = f"""---
type: alert
category: whatsapp_api_down
severity: high
created: {datetime.now(timezone.utc).isoformat()}
status: needs_attention
downtime_minutes: {downtime_minutes}
connection_failures: {self.connection_failures}
---

# ⚠️ WhatsApp Business API Unreachable

## Problem

The WhatsApp Business API has been unreachable for **{downtime_minutes} minutes**.

**MCP Server URL**: `{self.whatsapp_mcp_url}`

**Last Error**: {self.last_connection_error.strftime("%Y-%m-%d %H:%M:%S") if self.last_connection_error else "Unknown"}

**Consecutive Failures**: {self.connection_failures}

## Impact

- ❌ New WhatsApp messages are **not being detected**
- ❌ Incoming messages may be **missed**
- ⚠️  Messages sent during downtime will be processed once API is restored

## Possible Causes

1. **MCP Server Down**: WhatsApp MCP server process not running
2. **Network Issues**: Network connectivity problems
3. **WhatsApp API Outage**: WhatsApp Business API experiencing issues
4. **Authentication Failure**: API credentials expired or invalid
5. **Rate Limiting**: WhatsApp API rate limits exceeded

## Solution

### Step 1: Check MCP Server Status

```bash
pm2 status
```

Expected: `whatsapp-mcp-server` should be "online"

If stopped:
```bash
pm2 restart whatsapp-mcp-server
pm2 logs whatsapp-mcp-server
```

### Step 2: Test MCP Server Connection

```bash
curl {self.whatsapp_mcp_url}/health
```

Expected: `{{"status": "healthy"}}`

### Step 3: Check WhatsApp API Status

Visit: https://status.whatsapp.com (if available)

Or check WhatsApp Business API dashboard for alerts.

### Step 4: Verify Credentials

Check `.env` file for correct WhatsApp API credentials:

```bash
# WHATSAPP_PHONE_NUMBER_ID
# WHATSAPP_ACCESS_TOKEN
# WHATSAPP_BUSINESS_ACCOUNT_ID
```

### Step 5: Restart Watcher

Once MCP server is healthy:

```bash
pm2 restart whatsapp-watcher
pm2 logs whatsapp-watcher
```

Watcher will resume polling and process any missed messages.

## Data Safety

- **No message loss**: WhatsApp stores unread messages
- **Automatic recovery**: Watcher will process backlog once API is restored
- **Heartbeat monitoring**: Dashboard shows watcher status

**Recommendation**: Investigate MCP server logs for root cause.

---

**This alert was automatically generated by whatsapp_watcher**

**Created**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

            alert_path.write_text(alert_content, encoding='utf-8')
            logger.info(f"✅ Created API down alert: {alert_filename}")

            # Log alert creation
            self.logger.log(
                action_type=ActionType.SYSTEM_START,  # Reuse for alert
                actor=Actor.WHATSAPP_WATCHER,
                target=alert_filename,
                parameters={
                    'alert_type': 'whatsapp_api_down',
                    'downtime_minutes': downtime_minutes,
                    'connection_failures': self.connection_failures
                },
                result=Result.SUCCESS
            )

        except Exception as e:
            logger.error(f"Failed to create API down alert: {e}")


def main():
    """Main entry point for WhatsApp watcher process."""
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

    # Get WhatsApp MCP URL
    whatsapp_mcp_url = os.getenv(
        "WHATSAPP_MCP_URL",
        "http://localhost:3005/whatsapp"
    )

    # Get check interval (default: 60 seconds)
    check_interval = int(os.getenv("WHATSAPP_CHECK_INTERVAL", "60"))

    # Get dry run mode
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    # Create and start watcher
    try:
        watcher = WhatsAppWatcher(
            vault_path=str(vault_path),
            whatsapp_mcp_url=whatsapp_mcp_url,
            check_interval=check_interval,
            dry_run=dry_run
        )
        watcher.run()

    except KeyboardInterrupt:
        logger.info("WhatsApp watcher interrupted")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Failed to start WhatsApp watcher: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
