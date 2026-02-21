#!/usr/bin/env python3
"""
Vault Initialization Script for Personal AI Employee - Bronze Tier MVP

Creates the Obsidian vault structure with required folders and template files.
Implements FR-001, FR-002, FR-003 from spec.md

Usage:
    python scripts/init_vault.py --path /path/to/your/vault
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime


def create_folder_structure(vault_path: Path) -> None:
    """Create all required folders for the Obsidian vault (FR-001)."""
    folders = [
        "Inbox",
        "Needs_Action",
        "Plans",
        "Pending_Approval",
        "Approved",
        "Done",
        "Logs",
        "Quarantine",
    ]

    for folder in folders:
        folder_path = vault_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created folder: {folder}/")


def create_dashboard_template(vault_path: Path) -> None:
    """Create Dashboard.md template (FR-002)."""
    dashboard_content = f"""# AI Employee Dashboard

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Status Overview

- **Pending Actions**: 0 items
- **Pending Approvals**: 0 items
- **System Health**: ⚙️ Not Started

## Recent Activity

1. [{datetime.now().strftime('%H:%M')}] System initialized: Vault structure created
2. No activity yet
3. No activity yet
4. No activity yet
5. No activity yet

## Watchers Status

- **Gmail Watcher**: ⚙️ Not Started (last check: N/A)
- **File System Watcher**: ⚙️ Not Started (last heartbeat: N/A)
- **Orchestrator**: ⚙️ Not Started

---

*This dashboard is automatically updated by the AI Employee system*

## Getting Started

1. Configure Gmail API credentials in `.env` file
2. Start watchers with PM2: `pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3`
3. Drop files into `/Inbox/` folder for processing
4. Check `/Needs_Action/` for detected emails and files
5. Review `/Plans/` for AI-generated action plans

See [README.md](../README.md) for complete setup instructions.
"""

    dashboard_path = vault_path / "Dashboard.md"
    dashboard_path.write_text(dashboard_content, encoding="utf-8")
    print(f"✓ Created: Dashboard.md")


def create_handbook_template(vault_path: Path) -> None:
    """Create Company_Handbook.md template with default rules (FR-003)."""
    handbook_content = """# Company Handbook - AI Employee Rules

**Purpose**: This file defines the rules and guidelines for your AI Employee's behavior.

**Last Updated**: {date}

---

## Email Response Guidelines

- **Politeness**: Always be polite and professional in all communications
- **Response Time**: Respond to client emails within 24 hours
- **Tone**: Maintain a friendly, helpful, and professional tone

## Financial Rules

- **Payment Approval**: Flag any payment request over $100 for approval
- **Invoice Processing**: Verify all invoice details before processing
- **Budget Awareness**: Alert if expenses exceed monthly budget thresholds

## Task Planning Rules

- **Clarity**: Create plans with 3-7 specific, actionable steps
- **First Step**: Always include a step to clarify objectives before taking action
- **Final Step**: Always include a verification/completion step
- **Human-in-the-Loop**: Require approval for:
  - Sending emails to new contacts
  - Financial transactions over $100
  - Irreversible actions (delete, remove, etc.)
  - Social media posts or replies

## File Processing Rules

- **Security**: Quarantine executable files immediately (.exe, .dmg, .app, .bat, .sh, .cmd, .msi, .dll)
- **Large Files**: Alert on files over 50MB
- **Sensitive Data**: Never store passwords, API keys, or tokens in the vault

## Priority Classification

### High Priority (Requires immediate attention)
- Emails from clients marked "important" or containing urgent keywords
- Payment requests or invoices
- Meeting requests from key stakeholders
- Error alerts or system failures

### Medium Priority (Review within 24 hours)
- General client communications
- Internal team updates
- Document review requests
- Non-urgent administrative tasks

### Low Priority (Review when time permits)
- Newsletters and marketing emails
- FYI/informational emails
- Social media notifications

## Communication Preferences

- **Clients**: Professional, concise, always include next steps
- **Team**: Casual but clear, use bullet points
- **Vendors**: Professional, document all agreements

## Custom Rules

Add your own rules below:

---

**Note**: Edit this file to customize your AI Employee's behavior. Changes take effect immediately.
""".format(date=datetime.now().strftime('%Y-%m-%d'))

    handbook_path = vault_path / "Company_Handbook.md"
    handbook_path.write_text(handbook_content, encoding="utf-8")
    print(f"✓ Created: Company_Handbook.md")


def create_readme(vault_path: Path) -> None:
    """Create a README in the vault explaining the structure."""
    readme_content = """# Personal AI Employee Vault

This Obsidian vault is the central workspace for your Personal AI Employee (Bronze Tier MVP).

## Folder Structure

- **Inbox/**: Drop files here for processing (monitored by File System Watcher)
- **Needs_Action/**: Detected emails and files requiring your attention
- **Plans/**: AI-generated action plans for tasks
- **Pending_Approval/**: Items requiring your approval before execution
- **Approved/**: Approved actions (Silver tier feature)
- **Done/**: Completed tasks and processed items
- **Logs/**: System audit logs (JSON format)
- **Quarantine/**: Unsafe files automatically isolated for security

## Key Files

- **Dashboard.md**: Real-time system status and recent activity
- **Company_Handbook.md**: Rules and guidelines for AI behavior

## Usage

1. **Monitor Dashboard**: Open `Dashboard.md` to see pending items and system health
2. **Check Needs_Action**: Review emails and files that need your attention
3. **Review Plans**: Check `/Plans/` for AI-generated task breakdowns
4. **Drop Files**: Add files to `/Inbox/` for automatic processing
5. **Archive**: Move completed items to `/Done/` for record-keeping

## Automation

- **Gmail Watcher**: Checks inbox every 2 minutes for important emails
- **File System Watcher**: Monitors `/Inbox/` folder in real-time
- **Orchestrator**: Triggers Claude Code processing automatically
- **Dashboard Updater**: Refreshes status within 60 seconds of changes

## Privacy & Security

- ✅ All data stored locally (no cloud sync)
- ✅ Credentials stored outside vault (.env file)
- ✅ Audit logs track all actions
- ✅ Executable files automatically quarantined

For setup instructions, see the project README.md in the repository root.
"""

    readme_path = vault_path / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"✓ Created: README.md")


def main():
    """Main entry point for vault initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize Obsidian vault structure for Personal AI Employee"
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Absolute path to the Obsidian vault directory"
    )

    args = parser.parse_args()
    vault_path = Path(args.path).resolve()

    print(f"\n🚀 Initializing Personal AI Employee vault at: {vault_path}\n")

    # Create vault directory if it doesn't exist
    if not vault_path.exists():
        vault_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created vault directory: {vault_path}\n")
    else:
        print(f"✓ Using existing vault directory: {vault_path}\n")

    # Create folder structure
    print("Creating folder structure...")
    create_folder_structure(vault_path)
    print()

    # Create template files
    print("Creating template files...")
    create_dashboard_template(vault_path)
    create_handbook_template(vault_path)
    create_readme(vault_path)
    print()

    print("✅ Vault initialization complete!\n")
    print("Next steps:")
    print("1. Open Obsidian → Open folder as vault → Select:", vault_path)
    print("2. Configure .env file with VAULT_PATH =", vault_path)
    print("3. Set up Gmail API credentials (see README.md)")
    print("4. Start watchers with PM2")
    print()


if __name__ == "__main__":
    main()
