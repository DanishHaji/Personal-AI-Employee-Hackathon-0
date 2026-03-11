#!/usr/bin/env python3
"""
Gmail Watcher for Personal AI Employee - Platinum Tier

Monitors Gmail inbox for important/urgent emails with 24/7 operation.
Creates Email entity files in /Needs_Action/ folder.

Implements:
- FR-004 to FR-008: Gmail monitoring and email detection
- Contract 1: Email entity file creation
- FR-020: Heartbeat mechanism
- Platinum Tier US6: 24/7 continuous operation with health monitoring

Features:
- Polls Gmail API (configurable via CHECK_INTERVAL, default: 120s)
- Filters by IMPORTANT label or urgent keywords
- Duplicate detection via .watcher_state.json
- Exponential backoff for Gmail API rate limits (T080)
- Priority detection for urgent/important emails (T085)
- Event counting and error rate tracking (T083-T084)
- PID logging to health.jsonl on startup (T082)
- Structured audit logging

Usage:
    # First-time authentication
    python src/watchers/gmail_watcher.py --auth-only

    # Run watcher (one-shot mode)
    python src/watchers/gmail_watcher.py

    # Run watcher (24/7 continuous mode - Platinum Tier)
    python src/watchers/gmail_watcher.py --mode continuous

    # Run with systemd (recommended for production)
    systemctl start gmail-watcher.service
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

# Gold Tier US8 - Receipt processing
try:
    from src.services.expense_service import ExpenseService
    from src.services.budget_service import BudgetService
    EXPENSE_TRACKING_AVAILABLE = True
except ImportError:
    EXPENSE_TRACKING_AVAILABLE = False


class GmailWatcher(BaseWatcher):
    """Watcher that monitors Gmail inbox for important/urgent emails."""

    def __init__(
        self,
        vault_path: str | Path,
        credentials_path: str | Path,
        token_path: str | Path,
        check_interval: int = 120,  # 2 minutes default (FR-004)
        urgent_keywords: List[str] = None,
        mode: str = "once"  # "once" or "continuous" (Platinum Tier T079)
    ):
        """
        Initialize Gmail Watcher.

        Args:
            vault_path: Path to Obsidian vault
            credentials_path: Path to Gmail credentials.json
            token_path: Path to Gmail token.json
            check_interval: Check interval in seconds (default: 120 = 2 minutes)
            urgent_keywords: List of urgent keywords for priority detection
            mode: Operation mode - "once" (single check) or "continuous" (24/7 loop)
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

        # Platinum Tier US6 - Operation mode (T079)
        self.mode = mode

        # Platinum Tier US6 - Event counting metrics (T083)
        self.total_events_detected = 0
        self.total_events_processed = 0
        self.total_priority_events = 0

        # Platinum Tier US6 - Error rate tracking (T084)
        self.total_errors = 0
        self.consecutive_errors = 0
        self.last_error_time: Optional[datetime] = None

        # Platinum Tier US6 - Exponential backoff for API errors (T080)
        self.backoff_seconds = 1
        self.max_backoff_seconds = 300  # 5 minutes max
        self.backoff_multiplier = 2

        # Gold Tier US8 - Initialize expense tracking services
        self.expense_service = None
        self.budget_service = None
        if EXPENSE_TRACKING_AVAILABLE:
            try:
                self.expense_service = ExpenseService(vault_path=vault_path)
                self.budget_service = BudgetService(vault_path=vault_path)
                print(f"[GmailWatcher] Expense tracking enabled")
            except Exception as e:
                print(f"[GmailWatcher] Warning: Could not initialize expense tracking: {e}")

        # Urgent keywords for priority detection (FR-004)
        self.urgent_keywords = urgent_keywords or [
            "urgent", "asap", "invoice", "payment", "help"
        ]

        # Receipt detection keywords (Gold Tier US8)
        self.receipt_keywords = [
            "receipt", "invoice", "bill", "payment confirmation",
            "order confirmation", "purchase", "transaction"
        ]

        # State file for duplicate detection (FR-007)
        self.state_file = Path(".watcher_state.json")
        self.processed_email_ids: Set[str] = self._load_state()

        # Receipts directory (Gold Tier US8)
        self.receipts_dir = Path(vault_path) / "Receipts"
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

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

            # Platinum Tier US6 - Update event metrics (T083)
            self.total_events_detected += len(emails)

            # Process each email
            new_emails_count = 0
            priority_count = 0
            for email_data in emails:
                email_id = email_data['id']

                # Check for duplicates (FR-007, T018)
                if email_id in self.processed_email_ids:
                    continue  # Skip already processed

                # Platinum Tier US6 - Priority detection (T085)
                is_priority = self._detect_priority(email_data)
                if is_priority:
                    priority_count += 1
                    self.total_priority_events += 1
                    print(f"[GmailWatcher] ⚠️  PRIORITY email: {email_data['subject']}")

                # Create Email entity (T017)
                email_created = self._create_email_entity(email_data)

                if email_created:
                    # Mark as processed
                    self.processed_email_ids.add(email_id)
                    new_emails_count += 1
                    self.increment_processed_count()
                    self.total_events_processed += 1  # Platinum Tier US6 (T083)

                    # Log to audit (T021)
                    self.logger.log_email_detected(
                        email_id=email_id,
                        from_addr=email_data['from'],
                        subject=email_data['subject'],
                        priority="high" if email_data['has_important'] else "medium",
                        result=Result.SUCCESS
                    )

                    # Gold Tier US8 - Check for receipt attachments (T106)
                    if self.expense_service and self._is_receipt_email(email_data):
                        self._process_receipt_attachments(email_data)

            # Save state after processing
            if new_emails_count > 0:
                self._save_state()
                print(f"[GmailWatcher] Created {new_emails_count} new email entities")
                if priority_count > 0:
                    print(f"[GmailWatcher] Including {priority_count} priority emails")

            # Reset backoff on successful check (Platinum Tier US6 - T080)
            self.backoff_seconds = 1
            self.consecutive_errors = 0

        except HttpError as e:
            # Platinum Tier US6 - Error rate tracking (T084)
            self.total_errors += 1
            self.consecutive_errors += 1
            self.last_error_time = datetime.now()

            # Handle Gmail API credential expiration (T053 - Edge Case)
            if e.resp.status == 401:  # Unauthorized
                self._handle_credential_expiration(e)
                # Don't re-raise - allow watcher to continue with next check
                return

            # Platinum Tier US6 - Rate limiting with exponential backoff (T080)
            elif e.resp.status == 429:  # Too Many Requests
                self.logger.log_error(
                    actor="gmail_watcher",
                    error_message=f"Gmail API rate limit hit (429), backing off for {self.backoff_seconds}s",
                    error_type="HttpError",
                    target="inbox_check"
                )
                print(f"[GmailWatcher] ⚠️  Rate limit hit, backing off for {self.backoff_seconds}s", file=sys.stderr)

                # Sleep with exponential backoff
                time.sleep(self.backoff_seconds)

                # Increase backoff for next time
                self.backoff_seconds = min(
                    self.backoff_seconds * self.backoff_multiplier,
                    self.max_backoff_seconds
                )

                # Don't re-raise - continue with next check after backoff
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
            # Platinum Tier US6 - Error rate tracking (T084)
            self.total_errors += 1
            self.consecutive_errors += 1
            self.last_error_time = datetime.now()

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

    def _is_receipt_email(self, email_data: Dict[str, Any]) -> bool:
        """
        Check if email likely contains a receipt.

        Gold Tier US8 - T106: Receipt detection in Gmail watcher

        Args:
            email_data: Email metadata

        Returns:
            bool: True if email likely contains receipt
        """
        # Check subject for receipt keywords
        subject_lower = email_data['subject'].lower()
        for keyword in self.receipt_keywords:
            if keyword in subject_lower:
                return True

        # Check snippet for receipt keywords
        snippet_lower = email_data.get('snippet', '').lower()
        for keyword in self.receipt_keywords:
            if keyword in snippet_lower:
                return True

        return False

    def _process_receipt_attachments(self, email_data: Dict[str, Any]) -> None:
        """
        Process receipt attachments from an email.

        Gold Tier US8 - T106: Receipt detection and processing

        Args:
            email_data: Email metadata
        """
        try:
            email_id = email_data['id']

            # Get full email message with attachments
            message = self.gmail_service.service.users().messages().get(
                userId='me',
                id=email_id
            ).execute()

            # Check for attachments
            if 'parts' not in message.get('payload', {}):
                return

            # Current month for budget allocation
            current_month = datetime.now().strftime("%Y-%m")

            # Process each attachment
            for part in message['payload']['parts']:
                # Check if part is an attachment
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    filename = part['filename']
                    attachment_id = part['body']['attachmentId']

                    # Check if it's a receipt file (PDF or image)
                    if self._is_receipt_attachment(filename):
                        print(f"[GmailWatcher] Found receipt attachment: {filename}")

                        # Download attachment
                        attachment = self.gmail_service.service.users().messages().attachments().get(
                            userId='me',
                            messageId=email_id,
                            id=attachment_id
                        ).execute()

                        # Save to Receipts directory
                        import base64
                        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                        safe_filename = f"{timestamp}_{filename}"
                        receipt_path = self.receipts_dir / safe_filename

                        with open(receipt_path, 'wb') as f:
                            f.write(file_data)

                        print(f"[GmailWatcher] Saved receipt: {receipt_path}")

                        # Process with ExpenseService
                        try:
                            expense = self.expense_service.create_expense_from_receipt(
                                receipt_path=receipt_path,
                                month=current_month,
                                auto_approve=True
                            )

                            # Update budget
                            if self.budget_service:
                                self.budget_service.add_expense_to_budget(
                                    expense=expense,
                                    send_alerts=True
                                )

                            print(
                                f"[GmailWatcher] Created expense: {expense.expense_id} "
                                f"(${expense.amount}, {expense.approval_status.value})"
                            )

                        except Exception as e:
                            print(f"[GmailWatcher] Error processing receipt: {e}", file=sys.stderr)
                            # Log but don't fail - email entity was already created

        except Exception as e:
            print(f"[GmailWatcher] Error processing receipt attachments: {e}", file=sys.stderr)
            # Log but don't fail - email entity was already created
            self.logger.log_error(
                actor="gmail_watcher",
                error_message=str(e),
                error_type=type(e).__name__,
                target=f"receipt_processing_{email_data.get('id', 'unknown')}"
            )

    def _is_receipt_attachment(self, filename: str) -> bool:
        """
        Check if attachment filename indicates a receipt.

        Args:
            filename: Attachment filename

        Returns:
            bool: True if likely a receipt
        """
        filename_lower = filename.lower()

        # Check file extension
        receipt_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif']
        if not any(filename_lower.endswith(ext) for ext in receipt_extensions):
            return False

        # Check filename for receipt keywords
        receipt_filename_keywords = [
            'receipt', 'invoice', 'bill', 'payment', 'order', 'transaction'
        ]

        for keyword in receipt_filename_keywords:
            if keyword in filename_lower:
                return True

        # If it's a PDF or image but no receipt keywords, still consider it
        # (many receipts have generic names like "document.pdf")
        return True

    def _detect_priority(self, email_data: Dict[str, Any]) -> bool:
        """
        Detect if email is high priority.

        Platinum Tier US6 - T085: Priority detection for urgent emails.

        Priority indicators:
        - Has IMPORTANT label (Gmail native)
        - Contains urgent keywords in subject
        - Contains urgent keywords in snippet
        - From known VIP senders (future enhancement)

        Args:
            email_data: Email metadata

        Returns:
            bool: True if email is high priority
        """
        # Check Gmail IMPORTANT label
        if email_data.get('has_important', False):
            return True

        # Check subject for urgent keywords
        subject = email_data.get('subject', '').lower()
        for keyword in self.urgent_keywords:
            if keyword.lower() in subject:
                return True

        # Check snippet for urgent keywords
        snippet = email_data.get('snippet', '').lower()
        for keyword in self.urgent_keywords:
            if keyword.lower() in snippet:
                return True

        # Additional priority indicators
        priority_indicators = [
            'urgent', 'asap', 'important', 'critical',
            'action required', 'time sensitive', 'deadline'
        ]

        for indicator in priority_indicators:
            if indicator in subject or indicator in snippet:
                return True

        return False

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
        description="Gmail Watcher for Personal AI Employee - Platinum Tier"
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Authenticate with Gmail API and exit (first-time setup)"
    )
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="once",
        help="Operation mode: 'once' (single check) or 'continuous' (24/7 loop, Platinum Tier)"
    )
    parser.add_argument(
        "--vault-path",
        help="Path to vault directory (overrides VAULT_PATH env var)"
    )
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get configuration from environment
    vault_path = args.vault_path or os.getenv('VAULT_PATH')
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
            urgent_keywords=urgent_keywords,
            mode=args.mode  # Platinum Tier US6 (T079)
        )

        # Platinum Tier US6 - Log watcher PID to health.jsonl (T082)
        pid = os.getpid()
        health_log = Path(vault_path) / "Logs" / "health.jsonl"
        health_log.parent.mkdir(exist_ok=True)

        health_event = {
            "event": "watcher_started",
            "watcher": "gmail-watcher",
            "pid": pid,
            "mode": args.mode,
            "check_interval": check_interval,
            "timestamp": datetime.now().isoformat()
        }

        with open(health_log, "a") as f:
            f.write(json.dumps(health_event) + "\n")

        print(f"[GmailWatcher] Started (PID: {pid}, mode: {args.mode})")

        # Test Gmail connection
        watcher.gmail_service.test_connection()

        # Run watcher loop
        if args.mode == "continuous":
            # 24/7 continuous operation (Platinum Tier)
            watcher.run()
        else:
            # Single check mode (Bronze/Silver/Gold Tier compatibility)
            watcher.perform_check()

    except KeyboardInterrupt:
        print("\n[GmailWatcher] Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[GmailWatcher] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
