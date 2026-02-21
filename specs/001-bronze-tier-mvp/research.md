# Research: Bronze Tier MVP - Personal AI Employee

**Feature**: 001-bronze-tier-mvp
**Date**: 2026-02-21
**Phase**: 0 - Research & Technology Selection

## Research Questions

This document consolidates research findings for all technology choices and best practices needed for the Bronze Tier MVP implementation.

---

## 1. Python Package Management with UV

**Decision**: Use UV package manager for all Python dependencies

**Rationale**:
- **Requirement**: FR-021 mandates UV usage, pip NOT permitted
- **Speed**: UV is 10-100x faster than pip for dependency resolution
- **Reliability**: Deterministic builds via uv.lock file
- **Modern**: Uses pyproject.toml (PEP 621 standard)
- **Compatibility**: Works with existing Python ecosystem

**Best Practices**:
```bash
# Initialize UV project
uv init

# Add dependencies
uv add google-auth google-api-python-client watchdog python-dotenv pyyaml

# Install dependencies from lock file
uv sync

# Run scripts with UV
uv run python src/watchers/gmail_watcher.py

# Update dependencies
uv lock --upgrade
```

**pyproject.toml structure**:
```toml
[project]
name = "ai-employee-bronze"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "google-auth>=2.0.0",
    "google-api-python-client>=2.0.0",
    "watchdog>=3.0.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

**Alternatives Considered**:
- pip + requirements.txt: Rejected due to FR-021 mandate
- Poetry: Slower than UV, more complex configuration
- Pipenv: Less active development, slower

---

## 2. Gmail API Integration

**Decision**: Use Google Gmail API with OAuth2 authentication

**Rationale**:
- **Official**: Google's recommended method for Gmail access
- **Secure**: OAuth2 flow, no password storage
- **Feature-rich**: Filter by labels, importance, keywords
- **Rate limits**: 250 quota units/user/second (sufficient for <100 emails/day)
- **Python support**: Well-maintained google-api-python-client library

**Authentication Flow**:
1. Create project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth2 credentials (Desktop app)
4. Download credentials.json
5. First run: User authorizes via browser, token saved to token.json
6. Subsequent runs: Use saved token (refresh automatically)

**Best Practices**:
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)
```

**Query Patterns** (FR-004):
```python
# Get unread important emails
query = 'is:unread is:important'

# Get emails with urgent keywords
query = 'is:unread (subject:urgent OR subject:asap OR subject:invoice)'

# Combine both
query = 'is:unread (is:important OR subject:urgent OR subject:asap)'
```

**Rate Limit Handling** (FR-008):
```python
import time
from googleapiclient.errors import HttpError

def exponential_backoff(func, max_retries=4):
    for attempt in range(max_retries):
        try:
            return func()
        except HttpError as error:
            if error.resp.status == 429:  # Rate limit
                delay = 2 ** attempt  # 1s, 2s, 4s, 8s
                print(f"Rate limited, waiting {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

**Alternatives Considered**:
- IMAP: Less reliable, no official Gmail support, deprecated by Google
- Third-party APIs (Nylas, SendGrid): Overkill for Bronze tier, cost concerns
- Web scraping: Violates Gmail ToS, fragile

---

## 3. File System Monitoring

**Decision**: Use watchdog library for cross-platform file system events

**Rationale**:
- **Cross-platform**: Works on Windows, macOS, Linux
- **Event-driven**: No polling overhead
- **Mature**: Well-maintained since 2010, widely used
- **Pythonic**: Clean observer pattern API
- **Lightweight**: Minimal dependencies

**Best Practices** (FR-009):
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class InboxHandler(FileSystemEventHandler):
    def __init__(self, vault_path):
        self.vault_path = vault_path

    def on_created(self, event):
        if event.is_directory:
            return

        # Process new file
        file_path = event.src_path
        self.process_file(file_path)

    def process_file(self, file_path):
        # Copy to /Needs_Action, create metadata
        pass

# Usage
observer = Observer()
handler = InboxHandler('/path/to/vault')
observer.schedule(handler, '/path/to/vault/Inbox', recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

**File Type Quarantine** (FR-011):
```python
UNSAFE_EXTENSIONS = {'.exe', '.dmg', '.app', '.bat', '.sh', '.cmd', '.msi', '.dll'}

def is_safe_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext not in UNSAFE_EXTENSIONS
```

**Alternatives Considered**:
- Polling (os.listdir in loop): High CPU usage, delayed detection
- inotify (Linux-only): Not cross-platform
- fswatch: External dependency, requires installation

---

## 4. Obsidian Vault File Format

**Decision**: Use Markdown with YAML frontmatter for structured data

**Rationale**:
- **Obsidian native**: Standard format for Obsidian vaults
- **Human-readable**: Easy to inspect and debug
- **Portable**: Plain text, works with any editor
- **Parseable**: pyyaml library for frontmatter extraction
- **Version-controllable**: Git-friendly format

**Email File Format** (FR-005):
```markdown
---
type: email
from: client@example.com
subject: Urgent invoice request
received: 2026-02-21T14:30:00Z
priority: high
status: pending
email_id: ABC123XYZ
---

## Email Content

Hi, can you send me the invoice for January? Need it ASAP for accounting.

Thanks,
Client

## Suggested Actions

- [ ] Identify client account
- [ ] Calculate January charges
- [ ] Generate invoice
- [ ] Get approval for sending
- [ ] Send invoice to client@example.com
```

**File Drop Metadata Format** (FR-010):
```markdown
---
type: file_drop
original_name: contract.pdf
size: 524288
file_type: .pdf
received: 2026-02-21T14:35:00Z
status: pending
quarantined: false
---

## File Information

A new file was dropped into the Inbox for processing.

**Location**: `/Needs_Action/contract.pdf`
**Size**: 512.00 KB
**Type**: PDF Document
```

**Dashboard.md Format** (FR-002):
```markdown
# AI Employee Dashboard

**Last Updated**: 2026-02-21 14:40:00

## Status Overview

- **Pending Actions**: 3 items
- **Pending Approvals**: 1 item
- **System Health**: ✅ Healthy

## Recent Activity

1. [14:35] File dropped: contract.pdf → /Needs_Action
2. [14:30] Email detected: Urgent invoice request → /Needs_Action/EMAIL_ABC123.md
3. [14:15] Plan created: Invoice for January → /Plans/PLAN_001.md
4. [14:10] Email processed: Meeting request → /Done/EMAIL_XYZ789.md
5. [14:00] System started: All watchers running

## Watchers Status

- **Gmail Watcher**: ✅ Running (last check: 14:39)
- **File System Watcher**: ✅ Running (last heartbeat: 14:40)
- **Orchestrator**: ✅ Running
```

**Frontmatter Parsing**:
```python
import yaml
import re

def parse_frontmatter(content):
    # Extract YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if match:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    return {}, content
```

**Alternatives Considered**:
- JSON files: Less human-readable, not Obsidian-native
- SQLite database: Violates Local-First Privacy principle (not portable markdown)
- CSV: Poor structure for variable fields

---

## 5. Process Management with PM2

**Decision**: Use PM2 for running Python watchers as background processes

**Rationale**:
- **Cross-platform**: Works on Windows, macOS, Linux
- **Auto-restart**: Recovers from crashes automatically
- **Logging**: Built-in log management
- **Process monitoring**: CPU, memory usage tracking
- **Easy setup**: Single command to start/stop/restart
- **Startup scripts**: Auto-start on system boot

**Best Practices** (FR-019):
```bash
# Install PM2 globally
npm install -g pm2

# Start watchers
pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3
pm2 start src/watchers/filesystem_watcher.py --name fs-watcher --interpreter python3
pm2 start src/orchestrator.py --name orchestrator --interpreter python3

# Enable startup on boot
pm2 startup
pm2 save

# Monitor processes
pm2 status
pm2 monit

# View logs
pm2 logs gmail-watcher
pm2 logs --lines 100

# Restart on code changes
pm2 restart all
```

**ecosystem.config.js** (optional advanced config):
```javascript
module.exports = {
  apps: [
    {
      name: 'gmail-watcher',
      script: 'src/watchers/gmail_watcher.py',
      interpreter: 'python3',
      restart_delay: 5000,
      max_restarts: 10,
      env: {
        VAULT_PATH: process.env.VAULT_PATH
      }
    },
    {
      name: 'fs-watcher',
      script: 'src/watchers/filesystem_watcher.py',
      interpreter: 'python3'
    },
    {
      name: 'orchestrator',
      script: 'src/orchestrator.py',
      interpreter: 'python3'
    }
  ]
};
```

**Health Check Integration** (FR-020):
```python
import json
from datetime import datetime
from pathlib import Path

def write_heartbeat(vault_path):
    heartbeat_file = Path(vault_path) / 'Logs' / 'heartbeat.json'
    heartbeat_data = {
        'timestamp': datetime.now().isoformat(),
        'process': 'gmail-watcher',
        'status': 'running'
    }
    heartbeat_file.write_text(json.dumps(heartbeat_data, indent=2))

# In watcher main loop
while True:
    write_heartbeat(vault_path)
    # ... watcher logic
    time.sleep(60)
```

**Alternatives Considered**:
- systemd (Linux-only): Not cross-platform
- Windows Services: Not cross-platform, complex setup
- supervisord: Less features than PM2, Python-specific
- nohup/screen: No auto-restart, no monitoring

---

## 6. Claude Code Agent Skills

**Decision**: Implement AI functionality as Agent Skills in .claude/commands/

**Rationale**:
- **Constitutional requirement**: Principle IV mandates Agent Skills
- **Modularity**: Each skill has single responsibility
- **Reusability**: Skills can be invoked from tasks or manually
- **Testability**: Skills can be tested independently
- **Anthropic best practice**: Recommended by Claude Code documentation

**Skill Structure** (vault-manager.md example):
```markdown
---
name: vault-manager
description: Manage Obsidian vault files - read Needs_Action, create Plans, update Dashboard
arguments:
  - name: action
    description: Action to perform (read|plan|update_dashboard)
    required: true
  - name: file_path
    description: Path to file to process (for read/plan actions)
    required: false
---

# Vault Manager Skill

This skill manages Obsidian vault operations for the AI Employee.

## Actions

### read
Read and analyze files from /Needs_Action folder.

**Usage**: `vault-manager read /path/to/vault/Needs_Action/EMAIL_123.md`

### plan
Create a Plan.md file based on email/file content.

**Usage**: `vault-manager plan /path/to/vault/Needs_Action/EMAIL_123.md`

### update_dashboard
Update Dashboard.md with current system state.

**Usage**: `vault-manager update_dashboard`

## Implementation Notes

- Read files using File System tools
- Parse YAML frontmatter to extract metadata
- Generate Plan.md with 3-7 actionable steps
- Include approval step if sensitive action detected
- Update Dashboard.md with counts and recent activity
```

**Required Skills for Bronze Tier**:
1. **vault-manager.md**: Core vault operations (FR-012, FR-013, FR-014)
2. **email-triage.md**: Analyze email priority and categorize
3. **file-processor.md**: Handle file drops and create metadata
4. **dashboard-updater.md**: Aggregate stats and format Dashboard.md

**Best Practices**:
- One skill per file in `.claude/commands/`
- Clear argument definitions
- Usage examples in skill documentation
- Error handling documented
- Skills should be pure (no side effects except specified)

**Alternatives Considered**:
- Inline prompts: Less reusable, harder to test
- Custom MCP servers: Overkill for Bronze tier, deferred to Silver
- Direct Claude Code prompting: No modularity, not constitutional

---

## 7. Audit Logging

**Decision**: Structured JSON logs with daily rotation

**Rationale**:
- **Constitutional requirement**: Principle VII mandates structured logging
- **Queryable**: JSON format enables programmatic analysis
- **Human-readable**: Pretty-printed JSON is still readable
- **Standardized**: ISO 8601 timestamps, consistent schema
- **Retention**: YYYY-MM-DD.json files enable 90-day retention

**Log Format** (FR-018):
```json
{
  "timestamp": "2026-02-21T14:30:00.123Z",
  "action_type": "email_detected",
  "actor": "gmail_watcher",
  "target": "client@example.com",
  "parameters": {
    "subject": "Urgent invoice request",
    "email_id": "ABC123XYZ",
    "priority": "high"
  },
  "approval_status": "pending",
  "approved_by": null,
  "result": "success",
  "duration_ms": 45
}
```

**Logger Service** (src/services/logger_service.py):
```python
import json
from datetime import datetime
from pathlib import Path

class AuditLogger:
    def __init__(self, vault_path):
        self.logs_dir = Path(vault_path) / 'Logs'
        self.logs_dir.mkdir(exist_ok=True)

    def log(self, action_type, actor, target, parameters={},
            approval_status='pending', approved_by=None, result='success'):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'actor': actor,
            'target': target,
            'parameters': parameters,
            'approval_status': approval_status,
            'approved_by': approved_by,
            'result': result
        }

        # Write to daily log file
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        # Append to file (one entry per line for easier processing)
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
```

**Log Rotation**: Automatic via YYYY-MM-DD filename (new file each day)

**Log Retention**: Manual cleanup script (deferred to Silver tier) or OS-level cron

**Alternatives Considered**:
- Plain text logs: Not queryable
- syslog: Not portable across platforms
- Database: Violates Local-First Privacy principle

---

## Summary of Decisions

| Area | Decision | Primary Rationale |
|------|----------|-------------------|
| Package Manager | UV | FR-021 mandate, speed, deterministic builds |
| Gmail Access | Gmail API OAuth2 | Official, secure, feature-rich |
| File Monitoring | watchdog library | Cross-platform, event-driven, mature |
| File Format | Markdown + YAML frontmatter | Obsidian-native, human-readable |
| Process Management | PM2 | Cross-platform, auto-restart, monitoring |
| AI Architecture | Agent Skills | Constitutional requirement (Principle IV) |
| Logging | Structured JSON | Constitutional requirement (Principle VII) |

**All research questions resolved. Proceed to Phase 1: Design & Contracts.**
