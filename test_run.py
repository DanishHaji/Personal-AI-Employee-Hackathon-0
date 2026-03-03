#!/usr/bin/env python3
"""
Personal AI Employee - Test Mode Runner

Runs the AI Employee system in test mode without Gmail API.

Usage:
    python test_run.py

This will:
1. Create test vault structure
2. Start mock Gmail watcher (reads from Mock_Inbox/)
3. Start file system watcher (watches Inbox/)
4. Generate sample data for testing

NO GOOGLE CLOUD VERIFICATION REQUIRED!
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_vault_structure(vault_path: Path):
    """Create complete vault folder structure."""
    logger.info(f"Creating vault structure at: {vault_path}")

    folders = [
        "Inbox",           # Bronze: File drop
        "Mock_Inbox",      # Test: Mock emails
        "Needs_Action",    # Bronze: Detected items
        "Plans",           # Bronze: AI plans
        "Pending_Approval", # Silver: Awaiting approval
        "Approved",        # Silver: Approved actions
        "Done",            # All: Completed items
        "Logs",            # All: Audit logs
        "Quarantine",      # Bronze: Unsafe files
        "Contacts",        # Gold: CRM contacts
        "Expenses",        # Gold: Expense tracking
        "Budgets",         # Gold: Monthly budgets
        "Receipts",        # Gold: Receipt images
        "Meetings",        # Gold: Meeting notes
        "Calendar",        # Gold: Calendar sync
        "Insights",        # Gold: Analytics
        "Documents",       # Gold: Generated docs
    ]

    for folder in folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ Created {len(folders)} folders")


def create_company_handbook(vault_path: Path):
    """Create Company_Handbook.md with basic trust rules."""
    handbook_path = vault_path / "Company_Handbook.md"

    if handbook_path.exists():
        logger.info("Company_Handbook.md already exists")
        return

    content = """---
trust_rules:
  - rule_id: RULE_test_auto_approve
    rule_name: "Test Auto-Approve"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@example.com"]
    enabled: true
    effectiveness_score: 1.0
---

# Company Handbook

## Trust Rules

This handbook contains AI behavior rules and trust policies.

In TEST MODE, all actions from @example.com are auto-approved.

## Usage

1. Drop files in `/Inbox/` for file processing
2. Drop email files in `/Mock_Inbox/` for email simulation
3. Check `/Needs_Action/` for detected items
4. Review `/Plans/` for AI-generated action plans

## Test Mode

Currently running in TEST MODE (no Gmail API required).
"""

    handbook_path.write_text(content)
    logger.info("✅ Created Company_Handbook.md")


def create_dashboard(vault_path: Path):
    """Create Dashboard.md."""
    dashboard_path = vault_path / "Dashboard.md"

    content = f"""# AI Employee Dashboard

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Status

🟢 **RUNNING IN TEST MODE** (No Gmail API required)

## Quick Stats

- **Mode**: Test Mode (Mock Gmail)
- **Vault**: `{vault_path}`
- **Items Needing Action**: Check `/Needs_Action/` folder

## Recent Activity

Check `/Logs/audit_log.jsonl` for detailed activity.

## How to Test

### 1. Test Email Processing (Bronze Tier)
Drop a `.txt` file in `/Mock_Inbox/` with this format:
```
FROM: test@example.com
SUBJECT: Test Email
DATE: {datetime.now().isoformat()}

This is a test email body.
```

### 2. Test File Processing (Bronze Tier)
Drop any file in `/Inbox/` folder.

### 3. Test Expense Tracking (Gold Tier)
Create a file in `/Mock_Inbox/`:
```
FROM: receipts@adobe.com
SUBJECT: Receipt - Software Purchase
DATE: {datetime.now().isoformat()}

Amount: $45.99
Vendor: Adobe Creative Cloud
Category: software
```

### 4. Check Results
- New items appear in `/Needs_Action/`
- Plans generated in `/Plans/`
- Audit logs in `/Logs/audit_log.jsonl`

---

**Test Mode**: No Google Cloud verification needed!
"""

    dashboard_path.write_text(content)
    logger.info("✅ Created Dashboard.md")


def create_sample_files(vault_path: Path):
    """Create sample files for testing."""
    logger.info("Creating sample test files...")

    # Sample email
    email_sample = vault_path / "Mock_Inbox" / "sample_email_meeting.txt"
    email_sample.write_text("""FROM: colleague@example.com
SUBJECT: Meeting Request - Q2 Planning
DATE: 2026-03-03T10:00:00

Hi,

Can we schedule a meeting to discuss Q2 planning?

I'm available:
- Tomorrow 2pm
- Thursday 10am

Let me know what works.

Thanks,
John
""")

    # Sample file
    inbox_sample = vault_path / "Inbox" / "project_proposal.txt"
    inbox_sample.write_text("""Project Proposal: AI Integration

Overview:
We propose to integrate AI capabilities into our existing platform.

Budget: $50,000
Timeline: 3 months
Team: 5 engineers

Next Steps:
1. Review proposal
2. Schedule kickoff meeting
3. Assign resources
""")

    logger.info("✅ Created sample files")
    logger.info(f"   - {email_sample.name}")
    logger.info(f"   - {inbox_sample.name}")


def check_dependencies():
    """Check if required Python packages are installed."""
    logger.info("Checking dependencies...")

    required = [
        'watchdog',  # File system monitoring
        'pyyaml',    # YAML parsing
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        logger.warning(f"Missing packages: {', '.join(missing)}")
        logger.info("Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing)

    logger.info("✅ Dependencies OK")


def main():
    """Run test mode."""
    print("="*70)
    print("PERSONAL AI EMPLOYEE - TEST MODE")
    print("="*70)
    print()
    print("🧪 NO GMAIL API REQUIRED")
    print("🧪 NO GOOGLE CLOUD VERIFICATION NEEDED")
    print()

    # Get vault path
    vault_path = Path(os.getenv('VAULT_PATH', './test-vault'))
    vault_path = vault_path.resolve()

    print(f"Vault: {vault_path}")
    print()

    # Setup
    logger.info("Setting up test environment...")

    # Check dependencies
    check_dependencies()

    # Create vault structure
    create_vault_structure(vault_path)
    create_company_handbook(vault_path)
    create_dashboard(vault_path)
    create_sample_files(vault_path)

    print()
    print("="*70)
    print("SETUP COMPLETE")
    print("="*70)
    print()
    print("✅ Vault structure created")
    print("✅ Sample files created")
    print("✅ Test mode configured")
    print()

    # Instructions
    print("📋 NEXT STEPS:")
    print()
    print("1️⃣  Start Mock Gmail Watcher:")
    print(f"   python src/watchers/mock_gmail_watcher.py")
    print()
    print("2️⃣  Start File System Watcher:")
    print(f"   python src/watchers/filesystem_watcher.py")
    print()
    print("3️⃣  Test Email Processing:")
    print(f"   - Drop .txt files in: {vault_path}/Mock_Inbox/")
    print(f"   - Sample files already created!")
    print()
    print("4️⃣  Test File Processing:")
    print(f"   - Drop any files in: {vault_path}/Inbox/")
    print(f"   - Sample file already created!")
    print()
    print("5️⃣  Check Results:")
    print(f"   - Needs Action: {vault_path}/Needs_Action/")
    print(f"   - Plans: {vault_path}/Plans/")
    print(f"   - Audit Logs: {vault_path}/Logs/audit_log.jsonl")
    print()
    print("="*70)
    print()

    # Ask if user wants to start watchers
    response = input("Start watchers now? (y/n): ").lower().strip()

    if response == 'y':
        print()
        logger.info("Starting watchers...")
        print()

        # Export vault path
        os.environ['VAULT_PATH'] = str(vault_path)
        os.environ['TEST_MODE'] = 'true'

        try:
            # Start mock gmail watcher in background
            logger.info("Starting Mock Gmail Watcher...")
            gmail_process = subprocess.Popen(
                [sys.executable, 'src/watchers/mock_gmail_watcher.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            time.sleep(2)

            # Start filesystem watcher
            logger.info("Starting File System Watcher...")
            fs_process = subprocess.Popen(
                [sys.executable, 'src/watchers/filesystem_watcher.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            print()
            print("✅ Watchers started!")
            print()
            print("🎉 SYSTEM IS RUNNING IN TEST MODE")
            print()
            print("📧 Drop email files (.txt) in Mock_Inbox/")
            print("📁 Drop any files in Inbox/")
            print()
            print("Press Ctrl+C to stop...")
            print()

            # Keep running
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print()
            logger.info("Stopping watchers...")
            gmail_process.terminate()
            fs_process.terminate()
            print()
            print("✅ Stopped")

    else:
        print()
        print("👍 Run the commands above manually when ready!")
        print()


if __name__ == "__main__":
    main()
