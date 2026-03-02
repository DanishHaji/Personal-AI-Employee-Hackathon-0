"""
GDPR Data Export Service - Gold Tier Phase 11 (T126)

Implements data export functionality for GDPR compliance (FR-044).

Exports all personal data in standardized formats for user data portability
and deletion requests.

Usage:
    from src.services.gdpr_export import GDPRExporter

    exporter = GDPRExporter(vault_path="/path/to/vault")

    # Export all data
    export_path = exporter.export_all_data(
        output_dir="/path/to/export",
        user_email="user@example.com"
    )

    # Export specific categories
    exporter.export_contacts(output_dir="/path/to/export")
    exporter.export_emails(output_dir="/path/to/export")
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import zipfile

logger = logging.getLogger(__name__)


class GDPRExporter:
    """
    GDPR-compliant data export service.

    Exports all personal data in machine-readable formats:
    - Contacts (JSON)
    - Emails (JSON)
    - Meetings (JSON + transcripts)
    - Expenses & Receipts (JSON + PDFs)
    - Calendar Events (JSON)
    - Audit Logs (JSONL)
    - Trust Rules (YAML)
    - Insights (JSON)
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize GDPR exporter.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = Path(vault_path).resolve()

        logger.info(f"GDPRExporter initialized for vault: {vault_path}")

    def export_all_data(
        self,
        output_dir: str | Path,
        user_email: Optional[str] = None,
        create_zip: bool = True
    ) -> Path:
        """
        Export all personal data for GDPR compliance.

        Creates complete data export in standardized JSON format.

        Args:
            output_dir: Directory to write export files
            user_email: User's email for filtering (optional)
            create_zip: Whether to create ZIP archive (default: True)

        Returns:
            Path: Path to export directory or ZIP file
        """
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"gdpr_export_{timestamp}"
        export_path = output_dir / export_name

        export_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting GDPR export to {export_path}")

        # Export metadata
        self._export_metadata(export_path, user_email)

        # Export each data category
        self.export_contacts(export_path)
        self.export_emails(export_path)
        self.export_meetings(export_path)
        self.export_expenses(export_path)
        self.export_calendar(export_path)
        self.export_audit_logs(export_path)
        self.export_insights(export_path)
        self.export_trust_rules(export_path)

        # Create manifest
        self._create_manifest(export_path)

        logger.info(f"GDPR export complete: {export_path}")

        # Create ZIP archive
        if create_zip:
            zip_path = self._create_zip_archive(export_path)
            logger.info(f"Created ZIP archive: {zip_path}")
            return zip_path

        return export_path

    def _export_metadata(self, export_path: Path, user_email: Optional[str]):
        """Export metadata about the export."""
        metadata = {
            "export_date": datetime.now().isoformat(),
            "export_type": "GDPR_full_export",
            "user_email": user_email,
            "vault_path": str(self.vault_path),
            "format_version": "1.0"
        }

        with open(export_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

    def export_contacts(self, output_dir: Path) -> Path:
        """Export all contacts."""
        contacts_dir = self.vault_path / "Contacts"
        output_file = output_dir / "contacts.json"

        contacts = []

        if contacts_dir.exists():
            for contact_file in contacts_dir.glob("CONTACT_*.md"):
                try:
                    with open(contact_file, 'r') as f:
                        content = f.read()
                    contacts.append({
                        "file": contact_file.name,
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Error exporting contact {contact_file}: {e}")

        with open(output_file, 'w') as f:
            json.dump(contacts, f, indent=2)

        logger.info(f"Exported {len(contacts)} contacts")
        return output_file

    def export_emails(self, output_dir: Path) -> Path:
        """Export all email entities."""
        needs_action = self.vault_path / "Needs_Action"
        done = self.vault_path / "Done"
        output_file = output_dir / "emails.json"

        emails = []

        for directory in [needs_action, done]:
            if directory.exists():
                for email_file in directory.glob("EMAIL_*.md"):
                    try:
                        with open(email_file, 'r') as f:
                            content = f.read()
                        emails.append({
                            "file": email_file.name,
                            "location": directory.name,
                            "content": content
                        })
                    except Exception as e:
                        logger.error(f"Error exporting email {email_file}: {e}")

        with open(output_file, 'w') as f:
            json.dump(emails, f, indent=2)

        logger.info(f"Exported {len(emails)} emails")
        return output_file

    def export_meetings(self, output_dir: Path) -> Path:
        """Export all meeting notes."""
        meetings_dir = self.vault_path / "Meetings"
        output_file = output_dir / "meetings.json"

        meetings = []

        if meetings_dir.exists():
            for meeting_file in meetings_dir.rglob("*.md"):
                try:
                    with open(meeting_file, 'r') as f:
                        content = f.read()
                    meetings.append({
                        "file": str(meeting_file.relative_to(meetings_dir)),
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Error exporting meeting {meeting_file}: {e}")

        with open(output_file, 'w') as f:
            json.dump(meetings, f, indent=2)

        logger.info(f"Exported {len(meetings)} meetings")
        return output_file

    def export_expenses(self, output_dir: Path) -> Path:
        """Export all expenses and receipts."""
        expenses_dir = self.vault_path / "Expenses"
        receipts_dir = self.vault_path / "Receipts"
        output_file = output_dir / "expenses.json"

        expenses = []

        # Export expense entities
        if expenses_dir.exists():
            for expense_file in expenses_dir.rglob("EXPENSE_*.md"):
                try:
                    with open(expense_file, 'r') as f:
                        content = f.read()
                    expenses.append({
                        "file": str(expense_file.relative_to(expenses_dir)),
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Error exporting expense {expense_file}: {e}")

        # Copy receipts directory
        if receipts_dir.exists():
            receipts_export = output_dir / "receipts"
            try:
                shutil.copytree(receipts_dir, receipts_export)
                logger.info(f"Copied receipts directory to {receipts_export}")
            except Exception as e:
                logger.error(f"Error copying receipts: {e}")

        with open(output_file, 'w') as f:
            json.dump(expenses, f, indent=2)

        logger.info(f"Exported {len(expenses)} expenses")
        return output_file

    def export_calendar(self, output_dir: Path) -> Path:
        """Export calendar events."""
        calendar_dir = self.vault_path / "Calendar"
        output_file = output_dir / "calendar.json"

        events = []

        if calendar_dir.exists():
            events_file = calendar_dir / "events.json"
            if events_file.exists():
                try:
                    with open(events_file, 'r') as f:
                        events = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading calendar events: {e}")

        with open(output_file, 'w') as f:
            json.dump(events, f, indent=2)

        logger.info(f"Exported {len(events)} calendar events")
        return output_file

    def export_audit_logs(self, output_dir: Path) -> Path:
        """Export audit logs."""
        audit_log = self.vault_path / "Logs" / "audit_log.jsonl"
        output_file = output_dir / "audit_log.jsonl"

        if audit_log.exists():
            try:
                shutil.copy(audit_log, output_file)
                logger.info(f"Exported audit log to {output_file}")
            except Exception as e:
                logger.error(f"Error copying audit log: {e}")
        else:
            logger.warning("Audit log not found")

        return output_file

    def export_insights(self, output_dir: Path) -> Path:
        """Export analytics insights."""
        insights_dir = self.vault_path / "Insights"
        output_file = output_dir / "insights.json"

        insights = []

        if insights_dir.exists():
            for insight_file in insights_dir.glob("*.json"):
                try:
                    with open(insight_file, 'r') as f:
                        insight = json.load(f)
                        insight["_file"] = insight_file.name
                        insights.append(insight)
                except Exception as e:
                    logger.error(f"Error loading insight {insight_file}: {e}")

        with open(output_file, 'w') as f:
            json.dump(insights, f, indent=2)

        logger.info(f"Exported {len(insights)} insights")
        return output_file

    def export_trust_rules(self, output_dir: Path) -> Path:
        """Export trust rules from Company_Handbook.md."""
        handbook = self.vault_path / "Company_Handbook.md"
        output_file = output_dir / "trust_rules.yaml"

        if handbook.exists():
            try:
                # Extract YAML frontmatter
                with open(handbook, 'r') as f:
                    content = f.read()

                # Find trust_rules section
                import yaml
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        trust_rules = frontmatter.get('trust_rules', [])

                        with open(output_file, 'w') as f:
                            yaml.dump({"trust_rules": trust_rules}, f, default_flow_style=False)

                        logger.info(f"Exported {len(trust_rules)} trust rules")
            except Exception as e:
                logger.error(f"Error exporting trust rules: {e}")
        else:
            logger.warning("Company_Handbook.md not found")

        return output_file

    def _create_manifest(self, export_path: Path):
        """Create manifest file listing all exported data."""
        manifest = {
            "export_date": datetime.now().isoformat(),
            "files": [str(f.relative_to(export_path)) for f in export_path.rglob("*") if f.is_file()],
            "categories": [
                "contacts",
                "emails",
                "meetings",
                "expenses",
                "calendar",
                "audit_logs",
                "insights",
                "trust_rules"
            ],
            "gdpr_compliance": {
                "right_to_access": True,
                "right_to_portability": True,
                "data_format": "JSON",
                "machine_readable": True
            }
        }

        with open(export_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

    def _create_zip_archive(self, export_path: Path) -> Path:
        """Create ZIP archive of export."""
        zip_path = export_path.with_suffix('.zip')

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in export_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(export_path.parent)
                    zipf.write(file_path, arcname)

        return zip_path


def main():
    """Test GDPR export."""
    import sys
    import os

    logging.basicConfig(level=logging.INFO)

    vault_path = os.getenv('VAULT_PATH', '.')
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]

    exporter = GDPRExporter(vault_path=vault_path)

    output_dir = Path("./gdpr_exports")
    output_dir.mkdir(exist_ok=True)

    export_path = exporter.export_all_data(
        output_dir=output_dir,
        user_email="user@example.com",
        create_zip=True
    )

    print(f"✅ GDPR export complete: {export_path}")


if __name__ == "__main__":
    main()
