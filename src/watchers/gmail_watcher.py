#!/usr/bin/env python3
"""
Gmail Watcher for Personal AI Employee - Bronze Tier MVP

Monitors Gmail inbox every 2 minutes for important/urgent emails.
Creates Email entity files in /Needs_Action/ folder.

Implements:
- FR-004 to FR-008: Gmail monitoring and email detection
- Contract 1: Email entity file creation
- FR-020: Heartbeat mechanism

Features:
- Polls Gmail API every 2 minutes (configurable via CHECK_INTERVAL)
- Filters by IMPORTANT label or urgent keywords
- Duplicate detection via .watcher_state.json
- Exponential backoff for rate limits
- Structured audit logging

Usage:
    # First-time authentication
    python src/watchers/gmail_watcher.py --auth-only

    # Run watcher
    python src/watchers/gmail_watcher.py

    # Run with PM2
    pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from src.watchers.base_watcher import BaseWatcher
from src.services.gmail_service import GmailService, authenticate_gmail_cli
from src.services.vault_service import VaultService
from src.models.email import Email, create_email_filename
from src.services.logger_service import Result


class GmailWatcher(BaseWatcher):
    """Watcher that monitors Gmail inbox for important/urgent emails."""

    def __init__(
        self,
        vault_path: str | Path,
        credentials_path: str | Path,
        token_path: str | Path,
        check_interval: int = 120,  # 2 minutes default (FR-004)
        urgent_keywords: List[str] = None
    ):
        """
        Initialize Gmail Watcher.

        Args:
            vault_path: Path to Obsidian vault
            credentials_path: Path to Gmail credentials.json
            token_path: Path to Gmail token.json
            check_interval: Check interval in seconds (default: 120 = 2 minutes)
            urgent_keywords: List of urgent keywords for priority detection
        """
        super().__init__(
            vault_path=vault_path,
            watcher_name="gmail_watcher",
            check_interval=check_interval
        )

        # Initialize Gmail service
        self.gmail_service = GmailService(credentials_path, token_path)

        # Initialize Vault service
        self.vault_service = VaultService(vault_path)

        # Urgent keywords for priority detection (FR-004)
        self.urgent_keywords = urgent_keywords or [
            "urgent", "asap", "invoice", "payment", "help"
        ]

        # State file for duplicate detection (FR-007)
        self.state_file = Path(".watcher_state.json")
        self.processed_email_ids: Set[str] = self._load_state()

        print(f"[GmailWatcher] Initialized")
        print(f"  - Vault: {vault_path}")
        print(f"  - Check interval: {check_interval}s")
        print(f"  - Urgent keywords: {', '.join(self.urgent_keywords)}")
        print(f"  - Processed emails: {len(self.processed_email_ids)}")

    def _perform_check(self) -> None:
        """
        Perform Gmail inbox check for important/urgent emails.

        Implements:
        - FR-004: Query Gmail API for important emails
        - FR-005: Create Email entity files
        - FR-006: Extract email snippets
        - FR-007: Duplicate detection
        - FR-008: Rate limit handling (in GmailService)
        """
        try:
            # Query important/urgent emails (T016)
            emails = self.gmail_service.query_important_emails(
                urgent_keywords=self.urgent_keywords,
                max_results=50  # Check up to 50 recent emails
            )

            if not emails:
                # No new emails found
                return

            print(f"[GmailWatcher] Found {len(emails)} important/urgent emails")

            # Process each email
            new_emails_count = 0
            for email_data in emails:
                email_id = email_data['id']

                # Check for duplicates (FR-007, T018)
                if email_id in self.processed_email_ids:
                    continue  # Skip already processed

                # Create Email entity (T017)
                email_created = self._create_email_entity(email_data)

                if email_created:
                    # Mark as processed
                    self.processed_email_ids.add(email_id)
                    new_emails_count += 1
                    self.increment_processed_count()

                    # Log to audit (T021)
                    self.logger.log_email_detected(
                        email_id=email_id,
                        from_addr=email_data['from'],
                        subject=email_data['subject'],
                        priority="high" if email_data['has_important'] else "medium",
                        result=Result.SUCCESS
                    )

            # Save state after processing
            if new_emails_count > 0:
                self._save_state()
                print(f"[GmailWatcher] Created {new_emails_count} new email entities")

        except HttpError as e:
            # Handle Gmail API credential expiration (T053 - Edge Case)
            if e.resp.status == 401:  # Unauthorized
                self._handle_credential_expiration(e)
                # Don't re-raise - allow watcher to continue with next check
                return
            else:
                # Log other HTTP errors
                self.logger.log_error(
                    actor="gmail_watcher",
                    error_message=str(e),
                    error_type="HttpError",
                    target="inbox_check"
                )
                print(f"[GmailWatcher] HTTP Error during check: {e}", file=sys.stderr)
                # Re-raise to trigger retry in BaseWatcher
                raise

        except Exception as e:
            # Log error (T021)
            self.logger.log_error(
                actor="gmail_watcher",
                error_message=str(e),
                error_type=type(e).__name__,
                target="inbox_check"
            )
            print(f"[GmailWatcher] Error during check: {e}", file=sys.stderr)
            raise  # Re-raise to trigger retry in BaseWatcher

    def _create_email_entity(self, email_data: Dict[str, Any]) -> bool:
        """
        Create Email entity file in /Needs_Action/ folder.

        Implements FR-005, FR-006, Contract 1.

        Args:
            email_data: Email metadata from GmailService

        Returns:
            bool: True if entity created successfully
        """
        try:
            # Determine priority (T016)
            priority = self._determine_priority(email_data)

            # Extract sender email from "Name <email@domain.com>" format
            from_addr = self._extract_email_address(email_data['from'])

            # Truncate snippet to 200 chars (FR-006)
            snippet = email_data['snippet'][:200]

            # Create Email model instance
            email = Email(
                email_id=email_data['id'],
                from_addr=from_addr,
                subject=email_data['subject'],
                received=email_data['date'],
                priority=priority,
                status="pending",
                snippet=snippet
            )

            # Validate email
            email.validate()

            # Generate markdown content
            markdown_content = email.to_markdown()

            # Write to /Needs_Action/ folder
            filename = create_email_filename(email_data['id'])
            file_path = Path("Needs_Action") / filename

            self.vault_service.write_markdown(file_path, markdown_content)

            print(f"[GmailWatcher] Created: {filename}")
            return True

        except Exception as e:
            print(f"[GmailWatcher] Failed to create email entity: {e}", file=sys.stderr)
            self.logger.log_error(
                actor="gmail_watcher",
                error_message=str(e),
                error_type=type(e).__name__,
                target=email_data.get('id', 'unknown')
            )
            return False

    def _determine_priority(self, email_data: Dict[str, Any]) -> str:
        """
        Determine email priority based on labels and keywords.

        Logic (T016):
        - priority="high" if Gmail "important" label OR urgent keyword in subject
        - priority="medium" otherwise

        Args:
            email_data: Email metadata

        Returns:
            str: "high" or "medium"
        """
        # Check IMPORTANT label
        if email_data.get('has_important', False):
            return "high"

        # Check for urgent keywords in subject
        subject_lower = email_data['subject'].lower()
        for keyword in self.urgent_keywords:
            if keyword.lower() in subject_lower:
                return "high"

        return "medium"

    def _extract_email_address(self, from_field: str) -> str:
        """
        Extract email address from "Name <email@domain.com>" format.

        Args:
            from_field: From header value

        Returns:
            str: Email address
        """
        # Try to extract email from angle brackets
        if '<' in from_field and '>' in from_field:
            start = from_field.index('<') + 1
            end = from_field.index('>')
            return from_field[start:end]

        # Return as-is if no angle brackets (already just email)
        return from_field

    def _handle_credential_expiration(self, error: HttpError) -> None:
        """
        Handle Gmail API credential expiration error (T053 - Edge Case).

        Creates an alert file in /Needs_Action/ to notify user.

        Args:
            error: HttpError with 401 status
        """
        try:
            # Create alert filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_filename = f"ALERT_gmail_credentials_expired_{timestamp}.md"
            alert_path = self.vault_path / "Needs_Action" / alert_filename

            # Create alert content
            alert_content = f"""---
type: alert
category: credential_expiration
service: gmail_api
severity: high
created: {datetime.now().isoformat()}
status: needs_attention
---

# 🔴 Gmail API Credentials Expired

## Problem

The Gmail Watcher cannot access your Gmail inbox because the API credentials have expired.

**Error**: `{str(error)}`

**Time**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Impact

- ❌ Gmail inbox monitoring is **paused**
- ❌ New important emails will **not** be detected
- ❌ Dashboard may show **outdated** status

## Solution

Follow these steps to re-authenticate:

### Step 1: Delete Expired Token

```bash
cd {Path.cwd()}
rm token.json
```

### Step 2: Re-authenticate

```bash
uv run python src/watchers/gmail_watcher.py
```

This will:
1. Open browser for Google OAuth2 flow
2. Ask you to sign in and grant permissions
3. Create new `token.json` file

### Step 3: Restart Gmail Watcher

```bash
pm2 restart gmail-watcher
```

### Step 4: Verify Status

```bash
pm2 logs gmail-watcher --lines 20
```

Expected output:
```
[GmailWatcher] Started at ...
[GmailWatcher] Watching Gmail inbox every 120 seconds
```

## Prevention

Gmail tokens expire after ~7 days of inactivity or when:
- You change your Google password
- You revoke app permissions
- Google detects suspicious activity

**Recommendation**: Check Dashboard.md daily to catch issues early.

## Documentation

See: [Gmail API Setup Guide](../docs/gmail-api-setup.md#troubleshooting)

---

**This alert was automatically generated by Gmail Watcher**

Once resolved, move this file to `/Done/` folder.
"""

            # Write alert file
            self.vault_service.write_markdown(alert_path, alert_content)

            print(f"[GmailWatcher] ⚠️  CREDENTIAL EXPIRATION ALERT CREATED")
            print(f"[GmailWatcher] Alert file: {alert_filename}")
            print(f"[GmailWatcher] Action required: Delete token.json and re-authenticate")

            # Log to audit
            self.logger.log_error(
                actor="gmail_watcher",
                error_message="Gmail API credentials expired (HTTP 401)",
                error_type="CredentialExpiration",
                target="gmail_authentication"
            )

        except Exception as e:
            print(f"[GmailWatcher] Error creating credential expiration alert: {e}", file=sys.stderr)

    def _load_state(self) -> Set[str]:
        """
        Load processed email IDs from state file.

        Implements FR-007 duplicate detection.

        Returns:
            Set[str]: Set of processed email IDs
        """
        if not self.state_file.exists():
            return set()

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return set(state.get('processed_email_ids', []))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()

    def _save_state(self) -> None:
        """
        Save processed email IDs to state file.

        Implements FR-007 duplicate detection.
        """
        state = {
            'processed_email_ids': list(self.processed_email_ids),
            'last_updated': datetime.now().isoformat()
        }

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[GmailWatcher] Failed to save state: {e}", file=sys.stderr)


def main():
    """Main entry point for Gmail Watcher."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Gmail Watcher for Personal AI Employee"
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Authenticate with Gmail API and exit (first-time setup)"
    )
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get configuration from environment
    vault_path = os.getenv('VAULT_PATH')
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', './credentials.json')
    token_path = os.getenv('GMAIL_TOKEN_PATH', './token.json')
    check_interval = int(os.getenv('CHECK_INTERVAL', '120'))  # 2 minutes default
    urgent_keywords_str = os.getenv('URGENT_KEYWORDS', 'urgent,asap,invoice,payment,help')
    urgent_keywords = [kw.strip() for kw in urgent_keywords_str.split(',')]

    # Validate vault path
    if not vault_path:
        print("ERROR: VAULT_PATH not set in .env file", file=sys.stderr)
        sys.exit(1)

    # Auth-only mode
    if args.auth_only:
        authenticate_gmail_cli(credentials_path, token_path)
        sys.exit(0)

    # Validate vault exists
    if not Path(vault_path).exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        print("Run: python scripts/init_vault.py --path /path/to/vault", file=sys.stderr)
        sys.exit(1)

    # Create and run watcher
    try:
        watcher = GmailWatcher(
            vault_path=vault_path,
            credentials_path=credentials_path,
            token_path=token_path,
            check_interval=check_interval,
            urgent_keywords=urgent_keywords
        )

        # Test Gmail connection
        watcher.gmail_service.test_connection()

        # Run watcher loop
        watcher.run()

    except KeyboardInterrupt:
        print("\n[GmailWatcher] Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[GmailWatcher] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
