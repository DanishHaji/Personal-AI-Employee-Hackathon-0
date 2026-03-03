#!/usr/bin/env python3
"""
Mock Gmail Watcher (Test Mode)

Simulates Gmail monitoring without requiring Google Cloud verification.
Reads mock emails from test-vault/Mock_Inbox/ folder instead of Gmail API.

Usage:
    python src/watchers/mock_gmail_watcher.py
"""

import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockGmailWatcher:
    """
    Mock Gmail watcher that reads emails from local files.

    Simulates Bronze Tier Gmail monitoring without API access.
    """

    def __init__(self, vault_path: str):
        """
        Initialize mock Gmail watcher.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.mock_inbox = self.vault_path / "Mock_Inbox"
        self.needs_action = self.vault_path / "Needs_Action"
        self.processed_file = self.vault_path / "Logs" / "processed_emails.json"

        # Create directories
        self.mock_inbox.mkdir(exist_ok=True)
        self.needs_action.mkdir(exist_ok=True)
        (self.vault_path / "Logs").mkdir(exist_ok=True)

        # Load processed emails
        self.processed_emails = self._load_processed()

        logger.info(f"Mock Gmail Watcher initialized")
        logger.info(f"Watching: {self.mock_inbox}")
        logger.info(f"Output: {self.needs_action}")

    def _load_processed(self) -> set:
        """Load list of already processed email files."""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed', []))
            except:
                return set()
        return set()

    def _save_processed(self):
        """Save list of processed email files."""
        try:
            with open(self.processed_file, 'w') as f:
                json.dump({'processed': list(self.processed_emails)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save processed list: {e}")

    def create_sample_emails(self):
        """Create sample email files for testing."""
        logger.info("Creating sample emails...")

        samples = [
            {
                'filename': 'email_meeting_request.txt',
                'from': 'colleague@example.com',
                'subject': 'Meeting Request: Q2 Planning',
                'body': '''Hi,

Can we schedule a meeting to discuss Q2 planning?

I'm available:
- Tomorrow 2pm
- Thursday 10am

Let me know what works for you.

Thanks,
John'''
            },
            {
                'filename': 'email_expense_receipt.txt',
                'from': 'receipts@adobe.com',
                'subject': 'Receipt - Adobe Creative Cloud',
                'body': '''Your receipt for Adobe Creative Cloud subscription

Amount: $45.99
Date: 2026-03-03
Category: Software

Thank you for your business!'''
            },
            {
                'filename': 'email_contact_intro.txt',
                'from': 'alice.johnson@startup.com',
                'subject': 'Introduction - Partnership Opportunity',
                'body': '''Hi,

I'm Alice Johnson from TechStartup Inc.

I wanted to reach out regarding a potential partnership opportunity.

Would you be interested in a quick call next week?

Best regards,
Alice Johnson
CEO, TechStartup Inc.'''
            }
        ]

        for sample in samples:
            file_path = self.mock_inbox / sample['filename']
            if not file_path.exists():
                content = f"""FROM: {sample['from']}
SUBJECT: {sample['subject']}
DATE: {datetime.now().isoformat()}

{sample['body']}
"""
                file_path.write_text(content)
                logger.info(f"Created sample: {sample['filename']}")

    def parse_email_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse email from text file.

        Format:
        FROM: sender@example.com
        SUBJECT: Email subject
        DATE: 2026-03-03T10:00:00

        Email body here...
        """
        content = file_path.read_text()
        lines = content.split('\n')

        email_data = {
            'from': '',
            'subject': '',
            'date': datetime.now().isoformat(),
            'body': '',
            'filename': file_path.name
        }

        body_lines = []
        in_body = False

        for line in lines:
            if line.startswith('FROM:'):
                email_data['from'] = line.replace('FROM:', '').strip()
            elif line.startswith('SUBJECT:'):
                email_data['subject'] = line.replace('SUBJECT:', '').strip()
            elif line.startswith('DATE:'):
                email_data['date'] = line.replace('DATE:', '').strip()
            elif line.strip() == '' and not in_body:
                in_body = True
            elif in_body:
                body_lines.append(line)

        email_data['body'] = '\n'.join(body_lines).strip()

        return email_data

    def create_email_entity(self, email_data: Dict[str, Any]) -> Path:
        """
        Create email entity in Needs_Action folder.

        Args:
            email_data: Parsed email data

        Returns:
            Path to created email entity file
        """
        # Generate email ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        email_id = f"EMAIL_{timestamp}"

        # Create markdown file
        filename = f"{email_id}_{email_data['subject'][:30].replace(' ', '_')}.md"
        filename = filename.replace('/', '_').replace('\\', '_')
        file_path = self.needs_action / filename

        # Create frontmatter
        frontmatter = f"""---
email_id: {email_id}
type: email
from: {email_data['from']}
subject: {email_data['subject']}
date: {email_data['date']}
priority: normal
status: needs_action
source: mock_gmail
original_file: {email_data['filename']}
---

# Email: {email_data['subject']}

**From**: {email_data['from']}
**Date**: {email_data['date']}

## Body

{email_data['body']}

---

**AI Actions Required**: Review and decide action
"""

        file_path.write_text(frontmatter)

        # Log to audit
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'email_detected',
            'email_id': email_id,
            'from': email_data['from'],
            'subject': email_data['subject'],
            'status': 'moved_to_needs_action'
        }
        self._log_audit(audit_entry)

        return file_path

    def _log_audit(self, entry: Dict[str, Any]):
        """Log to audit log."""
        audit_log = self.vault_path / "Logs" / "audit_log.jsonl"

        try:
            with open(audit_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def process_new_emails(self) -> int:
        """
        Check for new emails in Mock_Inbox and process them.

        Returns:
            Number of new emails processed
        """
        email_files = list(self.mock_inbox.glob("*.txt"))
        new_count = 0

        for email_file in email_files:
            # Skip if already processed
            if email_file.name in self.processed_emails:
                continue

            try:
                logger.info(f"Processing: {email_file.name}")

                # Parse email
                email_data = self.parse_email_file(email_file)

                # Create entity
                entity_path = self.create_email_entity(email_data)

                logger.info(f"Created entity: {entity_path.name}")

                # Mark as processed
                self.processed_emails.add(email_file.name)
                new_count += 1

            except Exception as e:
                logger.error(f"Failed to process {email_file.name}: {e}")

        # Save processed list
        if new_count > 0:
            self._save_processed()

        return new_count

    def run(self, interval: int = 30):
        """
        Run mock Gmail watcher in loop.

        Args:
            interval: Check interval in seconds (default: 30)
        """
        logger.info(f"Starting mock Gmail watcher (check every {interval}s)")
        logger.info(f"Drop email files (.txt) in: {self.mock_inbox}")
        logger.info("Press Ctrl+C to stop")

        # Create sample emails on first run
        if len(list(self.mock_inbox.glob("*.txt"))) == 0:
            self.create_sample_emails()

        try:
            while True:
                new_count = self.process_new_emails()

                if new_count > 0:
                    logger.info(f"✅ Processed {new_count} new emails")

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\nStopping mock Gmail watcher")
            logger.info(f"Total emails processed: {len(self.processed_emails)}")


def main():
    """Run mock Gmail watcher."""
    # Get vault path from environment or use default
    vault_path = os.getenv('VAULT_PATH', './test-vault')

    # Create vault if doesn't exist
    vault = Path(vault_path)
    vault.mkdir(exist_ok=True)

    # Initialize watcher
    watcher = MockGmailWatcher(vault_path)

    # Run
    interval = int(os.getenv('MOCK_EMAIL_INTERVAL', '30'))
    watcher.run(interval=interval)


if __name__ == "__main__":
    main()
