# Gold Tier Setup Guide

**Personal AI Employee - Gold Tier**
**Version**: 1.0.0
**Last Updated**: 2026-03-02

Complete setup and usage guide for Gold Tier autonomous AI features.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [User Story Setup](#user-story-setup)
   - [US1: Trust Framework](#us1-trust-framework)
   - [US2: Calendar Management](#us2-calendar-management)
   - [US3: Document Generation](#us3-document-generation)
   - [US4: Analytics & Insights](#us4-analytics--insights)
   - [US5: Proactive Suggestions](#us5-proactive-suggestions)
   - [US6: Meeting Attendance](#us6-meeting-attendance)
   - [US7: CRM Integration](#us7-crm-integration)
   - [US8: Financial Tracking](#us8-financial-tracking)
5. [Configuration](#configuration)
6. [Running the System](#running-the-system)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Gold Tier adds 8 advanced autonomous features to your Personal AI Employee:

| Feature | Description | Auto-Approval | Status |
|---------|-------------|---------------|---------|
| **Trust Framework** (US1) | Auto-approve trusted actions | 60% friction reduction | ✅ MVP |
| **Calendar Management** (US2) | Google Calendar sync & conflict resolution | Yes (trusted meetings) | ✅ Implemented |
| **Document Generation** (US3) | Auto-generate status reports, meeting notes | Yes (trusted types) | ✅ Implemented |
| **Analytics & Insights** (US4) | Weekly productivity insights | N/A | ✅ Implemented |
| **Proactive Suggestions** (US5) | AI-initiated follow-ups & reminders | No (suggestions only) | ✅ Implemented |
| **Meeting Attendance** (US6) | Join Zoom, transcribe, extract action items | Yes (if trusted) | ✅ Implemented |
| **CRM Integration** (US7) | Auto-track contacts & relationships | N/A | ✅ Implemented |
| **Financial Tracking** (US8) | OCR receipts, track budgets | Yes (recurring vendors) | ✅ Implemented |

---

## Prerequisites

### System Requirements

- **Python**: 3.13+ (3.12.3+ validated)
- **OS**: Linux, macOS, or WSL2
- **RAM**: 4GB minimum (8GB recommended for OCR)
- **Disk**: 2GB free space
- **Node.js**: 18+ (for PM2 process management)

### Required Accounts & API Keys

#### Core (Bronze/Silver Tier)
- Gmail API credentials (`credentials.json`)
- Obsidian vault directory

#### Gold Tier Optional APIs
- **Google Calendar API** (US2) - Calendar management
- **OpenAI API** (US6) - Whisper transcription
- **Zoom SDK** (US6) - Meeting attendance
- **Google Vision API** (US8) - OCR fallback (optional)

### Python Dependencies

All dependencies are managed via `uv` and defined in `pyproject.toml`:

```bash
# Core Gold Tier dependencies
google-api-python-client  # Calendar & Vision APIs
jinja2                    # Document templating
pandas                    # Analytics
cryptography              # Encryption
openai                    # Whisper API
easyocr                   # Receipt OCR
fuzzywuzzy                # Contact deduplication
zoomus                    # Zoom SDK
keyring                   # Secure key storage
```

---

## Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd personal-ai-employee
git checkout 003-gold-tier-upgrade
```

### Step 2: Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies including Gold Tier
uv sync --all-extras
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimum Required Settings:**
```bash
VAULT_PATH=/path/to/your/obsidian/vault
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json
```

### Step 4: Initialize Vault Structure

```bash
# Create required directories
uv run python scripts/init_vault.py --path "$VAULT_PATH"
```

This creates:
- `/Needs_Action/` - Pending tasks
- `/Approved/` - Approved actions
- `/Done/` - Completed items
- `/Pending_Approval/` - HITL review (Silver Tier)
- `/Expenses/` - Expense entities (Gold Tier)
- `/Budgets/` - Budget JSON files (Gold Tier)
- `/Receipts/` - Receipt attachments (Gold Tier)
- `/Contacts/` - Contact profiles (Gold Tier)
- `/Calendar/` - Calendar cache (Gold Tier)
- `/Insights/` - Analytics reports (Gold Tier)
- `/Meetings/` - Meeting notes (Gold Tier)
- `/Logs/` - Audit logs

---

## User Story Setup

### US1: Trust Framework

**Purpose**: Auto-approve trusted actions without HITL review.

#### Setup

1. **Configure Trust Rules** in `Company_Handbook.md`:

```yaml
trust_rules:
  - rule_id: "TRUST_001"
    action_type: "email_reply"
    contact_filter:
      - "boss@company.com"
      - "@team.company.com"
    auto_approve: true

  - rule_id: "TRUST_002"
    action_type: "calendar_schedule"
    time_pattern: "09:00-17:00 Mon-Fri"
    auto_approve: true
```

2. **Enable Trust Framework**:

```bash
# In .env
TRUST_FRAMEWORK_ENABLED=true
TRUST_EFFECTIVENESS_THRESHOLD=0.80
```

3. **Verify**:

```bash
uv run python -c "from src.services.trust_evaluator import TrustEvaluator; t = TrustEvaluator('$VAULT_PATH'); print(f'Loaded {len(t.rules)} trust rules')"
```

#### Usage

Trust evaluation happens automatically during action execution. See audit logs:

```bash
tail -f Logs/audit_log.jsonl | grep "trust_rule_id"
```

---

### US2: Calendar Management

**Purpose**: Google Calendar integration with conflict detection.

#### Setup

1. **Get Google Calendar API Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create project → Enable Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download as `google_calendar_credentials.json`

2. **Authenticate**:

```bash
# First-time OAuth flow
uv run python -c "from src.services.calendar_service import CalendarService; CalendarService('$VAULT_PATH', './google_calendar_credentials.json', './google_calendar_token.json').authenticate()"
```

3. **Enable in .env**:

```bash
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CREDENTIALS_PATH=./google_calendar_credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=./google_calendar_token.json
CALENDAR_SYNC_INTERVAL=3600
CALENDAR_WATCHER_ENABLED=true
```

4. **Configure Work Hours** in `Company_Handbook.md`:

```yaml
calendar_preferences:
  work_hours:
    start: "09:00"
    end: "17:00"
    timezone: "America/New_York"
  no_meeting_blocks:
    - start: "12:00"
      end: "13:00"
      reason: "Lunch break"
```

#### Usage

```bash
# Start calendar watcher
pm2 start src/watchers/calendar_watcher.py --name calendar-watcher --interpreter python3
```

---

### US3: Document Generation

**Purpose**: Auto-generate weekly status reports and meeting notes.

#### Setup

1. **Configure Templates** in `.specify/templates/documents/`:
   - `weekly-status.md.j2`
   - `meeting-notes.md.j2`
   - `monthly-summary.md.j2`

2. **Enable in .env**:

```bash
DOCUMENT_GENERATION_ENABLED=true
```

3. **Schedule in `Company_Handbook.md`**:

```yaml
scheduled_tasks:
  - task_id: "weekly_status"
    type: "document_generation"
    template: "weekly-status.md.j2"
    schedule: "0 17 * * 5"  # Friday 5pm
    auto_approve: true
```

#### Usage

Documents are auto-generated per schedule. Manual generation:

```bash
uv run python -c "from src.services.document_service import DocumentService; DocumentService('$VAULT_PATH').generate_from_template('weekly-status.md.j2', {'week': '2026-W09'})"
```

---

### US4: Analytics & Insights

**Purpose**: Weekly productivity insights from audit logs.

#### Setup

1. **Enable in .env**:

```bash
ANALYTICS_INSIGHTS_ENABLED=true
ANALYTICS_SCHEDULE=0 17 * * 5  # Friday 5pm
ANALYTICS_MIN_DAYS=30
ANALYTICS_ENGINE_ENABLED=true
```

2. **Ensure Audit Logs Exist**:

```bash
# Check audit log has data
wc -l Logs/audit_log.jsonl
```

#### Usage

Analytics run automatically per schedule. Manual run:

```bash
uv run python -c "from src.services.analytics_service import AnalyticsService; AnalyticsService('$VAULT_PATH').generate_weekly_insights()"
```

Insights saved to: `/Insights/YYYY-MM-DD.json`

---

### US5: Proactive Suggestions

**Purpose**: AI-initiated follow-ups and reminders.

#### Setup

1. **Enable in .env**:

```bash
PROACTIVE_SUGGESTIONS_ENABLED=true
SUGGESTION_CHECK_INTERVAL=3600
MAX_SUGGESTIONS_PER_CATEGORY=3
SUGGESTION_ENGINE_ENABLED=true
```

2. **Configure Categories** in `Company_Handbook.md`:

```yaml
suggestion_preferences:
  enabled_categories:
    - follow_up_email
    - incomplete_task_chain
    - recurring_pattern
  opt_out_categories: []
```

#### Usage

Suggestions run hourly. View suggestions:

```bash
ls -lt Needs_Action/SUGGEST_*.md | head -5
```

---

### US6: Meeting Attendance

**Purpose**: Join Zoom meetings, transcribe with Whisper, extract action items.

#### Setup

1. **Get API Keys**:
   - **OpenAI API**: https://platform.openai.com/api-keys
   - **Zoom SDK**: https://marketplace.zoom.us/

2. **Configure .env**:

```bash
OPENAI_API_KEY=sk-...
ZOOM_API_KEY=your-zoom-api-key
ZOOM_API_SECRET=your-zoom-api-secret
MEETING_ATTENDANCE_ENABLED=true
USE_LOCAL_WHISPER=false
```

3. **Install Zoom SDK**:

```bash
uv add zoomus
```

#### Usage

Meeting attendance is triggered automatically from calendar events with Zoom links.

Manual transcription:

```bash
uv run python -c "from src.services.transcription_service import TranscriptionService; TranscriptionService('$VAULT_PATH').transcribe_audio('/path/to/recording.mp3')"
```

---

### US7: CRM Integration

**Purpose**: Auto-track contacts and relationships.

#### Setup

1. **Enable in .env**:

```bash
CRM_INTEGRATION_ENABLED=true
CRM_WATCHER_ENABLED=true
```

2. **Configure Thresholds** in `Company_Handbook.md`:

```yaml
crm_preferences:
  vip_threshold: 30  # days without contact
  regular_threshold: 60
  auto_promote_score: 200
```

#### Usage

Contacts are auto-created from email/meeting interactions.

Check stale relationships:

```bash
uv run python -c "from src.services.contact_service import ContactService; cs = ContactService('$VAULT_PATH'); print(f'Stale VIPs: {len(cs.find_stale_relationships(vip_only=True))}')"
```

---

### US8: Financial Tracking

**Purpose**: OCR receipts, track budgets, send alerts.

#### Setup

1. **Install OCR Dependencies**:

```bash
# EasyOCR (required)
uv add easyocr pdf2image

# Google Vision API (optional fallback)
uv add google-cloud-vision
```

2. **Configure .env**:

```bash
EXPENSE_TRACKING_ENABLED=true
OCR_VISION_THRESHOLD=0.75
VISION_API_ENABLED=false  # Set to true if using Vision API
DEFAULT_CURRENCY=USD
```

3. **Set Default Budgets** in `Company_Handbook.md`:

```yaml
default_budgets:
  software: 500.00
  travel: 1000.00
  office: 200.00
  marketing: 300.00
  meals: 400.00
  transportation: 250.00
  utilities: 150.00
  other: 200.00
```

#### Usage

Receipts are auto-processed from Gmail attachments.

Manual processing:

```bash
uv run python -c "from src.services.expense_service import ExpenseService; ExpenseService('$VAULT_PATH').create_expense_from_receipt('/path/to/receipt.pdf', '2026-03')"
```

View budget status:

```bash
uv run python -c "from src.services.budget_service import BudgetService; import json; print(json.dumps(BudgetService('$VAULT_PATH').get_budget_report('2026-03'), indent=2))"
```

---

## Configuration

### Company Handbook

The central configuration file: `Company_Handbook.md`

**Key Sections:**
- `trust_rules` - Trust framework rules
- `calendar_preferences` - Work hours, no-meeting blocks
- `scheduled_tasks` - Document generation schedules
- `crm_preferences` - VIP thresholds
- `default_budgets` - Monthly budget allocations
- `suggestion_preferences` - Enabled/disabled categories

### Environment Variables

See `.env.example` for full list. Key Gold Tier variables:

```bash
# Feature Flags
TRUST_FRAMEWORK_ENABLED=true
CALENDAR_MANAGEMENT_ENABLED=false
ANALYTICS_INSIGHTS_ENABLED=true
EXPENSE_TRACKING_ENABLED=false

# API Keys
OPENAI_API_KEY=sk-...
GOOGLE_CALENDAR_CREDENTIALS_PATH=./google_calendar_credentials.json
ZOOM_API_KEY=your-zoom-api-key

# Performance
TRUST_EVAL_MAX_TIME_MS=10
GOOGLE_CALENDAR_DAILY_LIMIT=1000000
WHISPER_API_RATE_LIMIT=50
```

---

## Running the System

### PM2 Process Manager

```bash
# Start all processes
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs

# Restart specific process
pm2 restart calendar-watcher
```

### Individual Processes

```bash
# Gmail Watcher (Bronze Tier)
pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3

# Executor (Silver Tier)
pm2 start src/executor.py --name executor --interpreter python3

# Calendar Watcher (Gold Tier US2)
pm2 start src/watchers/calendar_watcher.py --name calendar-watcher --interpreter python3

# Analytics Engine (Gold Tier US4)
pm2 start src/services/analytics_engine.py --name analytics-engine --interpreter python3

# Suggestion Engine (Gold Tier US5)
pm2 start src/services/suggestion_engine.py --name suggestion-engine --interpreter python3

# CRM Watcher (Gold Tier US7)
pm2 start src/watchers/crm_watcher.py --name crm-watcher --interpreter python3
```

---

## Verification

### Test Each User Story

#### US1: Trust Framework
```bash
# Check trust rules loaded
uv run python -c "from src.services.trust_evaluator import TrustEvaluator; print(TrustEvaluator('$VAULT_PATH').rules)"
```

#### US2: Calendar Management
```bash
# Test calendar connection
uv run python -c "from src.services.calendar_service import CalendarService; cs = CalendarService('$VAULT_PATH', './google_calendar_credentials.json', './google_calendar_token.json'); print(cs.test_connection())"
```

#### US3: Document Generation
```bash
# Generate test document
uv run python -c "from src.services.document_service import DocumentService; DocumentService('$VAULT_PATH').generate_from_template('weekly-status.md.j2', {})"
```

#### US4: Analytics & Insights
```bash
# Check insights
ls -lt Insights/*.json | head -1
```

#### US5: Proactive Suggestions
```bash
# Check suggestion files
ls Needs_Action/SUGGEST_*.md 2>/dev/null | wc -l
```

#### US6: Meeting Attendance
```bash
# Test transcription (requires audio file)
uv run python -c "from src.services.transcription_service import TranscriptionService; print('Transcription service ready')"
```

#### US7: CRM Integration
```bash
# Check contacts
ls Contacts/CONTACT_*.md 2>/dev/null | wc -l
```

#### US8: Financial Tracking
```bash
# Check budgets
ls Budgets/*.json 2>/dev/null
```

### Monitor Logs

```bash
# Watch audit log
tail -f Logs/audit_log.jsonl

# Check PM2 logs
pm2 logs --lines 50

# View specific process
pm2 logs gmail-watcher --lines 100
```

---

## Troubleshooting

See [Gold Tier Troubleshooting Guide](./gold-tier-troubleshooting.md) for detailed solutions.

**Quick Fixes:**

- **Gmail credentials expired**: Delete `token.json`, re-run `gmail_watcher.py`
- **Calendar API quota**: Check daily limit in Google Cloud Console
- **OCR low accuracy**: Enable Vision API fallback or improve image quality
- **Trust rules not loading**: Check YAML syntax in `Company_Handbook.md`
- **PM2 process crashed**: Check logs with `pm2 logs <process-name>`

---

## Next Steps

1. **Enable Features Gradually**: Start with US1 (Trust Framework), then add others
2. **Monitor Performance**: Check audit logs and PM2 metrics
3. **Tune Trust Rules**: Adjust based on effectiveness scores
4. **Review Insights**: Check weekly analytics for optimization opportunities
5. **Backup Encryption Keys**: See [Encryption Backup Guide](./encryption-backup.md)

---

**Support**: See `docs/gold-tier-troubleshooting.md` for detailed troubleshooting
**Version**: Gold Tier 1.0.0
**Last Updated**: 2026-03-02
