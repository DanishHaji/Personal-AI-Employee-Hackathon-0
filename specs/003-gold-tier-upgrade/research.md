# Gold Tier Technology Research

**Feature**: 003-gold-tier-upgrade
**Date**: 2026-02-27
**Purpose**: Technology decisions for autonomous AI employee capabilities

---

## 1. Trust Framework & Rule Engine

**Decision**: Simple dictionary-based rule matching with YAML storage in Company_Handbook.md

**Rationale**:
- Trust rules are simple conditional logic (action type + contact filter + content pattern)
- No need for complex rule engine overhead (Drools, python-rules-engine)
- YAML in Company_Handbook.md keeps configuration accessible to users
- Pattern matching with Python's `re` module is sufficient for content filtering
- Maintains consistency with existing Silver Tier configuration approach

**Alternatives Considered**:
- **python-rules-engine**: Too heavyweight for simple if/then logic
- **Separate JSON rule files**: Fragments configuration, harder for users to manage
- **SQLite rule storage**: Adds database dependency, overkill for <100 rules

**Integration Approach**:
- Extend Company_Handbook.md YAML frontmatter with `trust_rules:` section
- Executor service loads rules on startup, caches in memory
- Rule evaluation happens before plan execution (check trust level → auto-approve or wait)

**Dependencies**: None (uses standard library `re`, `yaml` already installed)

---

## 2. Google Calendar API

**Decision**: google-api-python-client (official library) with google-auth-oauthlib

**Rationale**:
- Official Google library with comprehensive Calendar API v3 support
- Well-maintained, widely used, extensive documentation
- Handles OAuth 2.0 flow, token refresh automatically
- Supports all Calendar features (events, recurring, conflict detection, invites)
- Rate limits: 1M queries/day per project (sufficient for single-user)

**Alternatives Considered**:
- **google-calendar-simple-api**: Simpler but lacks advanced features (recurring events, conflict detection)
- **icalendar + CalDAV**: Standards-based but Google Calendar doesn't expose CalDAV
- **Direct REST API calls**: Reinventing the wheel, OAuth handling complex

**Integration Approach**:
- New `CalendarService` in `src/services/calendar_service.py`
- OAuth credentials stored in `.env` (GOOGLE_CALENDAR_CREDENTIALS_PATH)
- Token refresh handled automatically by library
- Calendar events cached locally in vault (`/Calendar/events.json`) for offline conflict detection

**Dependencies**:
```toml
google-api-python-client = "^2.100.0"
google-auth-oauthlib = "^1.2.0"
google-auth-httplib2 = "^0.2.0"
```

**OAuth Scopes Needed**:
- `https://www.googleapis.com/auth/calendar` (read/write calendar events)
- `https://www.googleapis.com/auth/calendar.events` (create/modify events)

---

## 3. Document Generation & Templates

**Decision**: Jinja2 template engine with Python-Markdown for rendering

**Rationale**:
- Jinja2 is industry-standard Python templating (Django, Flask use it)
- Powerful variable substitution, loops, conditionals
- Template inheritance for complex document structures
- Python-Markdown for final rendering if needed (optional)
- Simple {{variable}} syntax accessible to non-technical users

**Alternatives Considered**:
- **string.Template**: Too simple, lacks loops/conditionals
- **Mako**: Powerful but overkill, allows arbitrary Python execution (security risk)
- **Mustache/Handlebars**: Cross-language but less powerful than Jinja2

**Integration Approach**:
- Templates stored in `.specify/templates/documents/` (e.g., `weekly-status.md.j2`, `meeting-notes.md.j2`)
- New `DocumentService` in `src/services/document_service.py`
- Template context populated from audit logs, meeting notes, user data
- Generated documents saved to `/Documents/` with version metadata in frontmatter
- Version control via frontmatter (version number, generation date, template used)

**Dependencies**:
```toml
jinja2 = "^3.1.0"
markdown = "^3.5.0"  # Optional for rendering
```

---

## 4. Analytics & Pattern Recognition

**Decision**: pandas for time-series analysis with numpy for calculations

**Rationale**:
- pandas is standard for structured data analysis in Python
- Efficiently handles time-series operations (groupby date, rolling windows)
- Audit logs are already JSON lines format → easy to load into DataFrame
- numpy for statistical calculations (percentiles, averages, anomaly detection)
- No ML models needed initially (simple rule-based pattern detection)

**Alternatives Considered**:
- **Raw Python loops**: Slower, more code, harder to maintain
- **SQLite with SQL queries**: Requires data import, less flexible for ad-hoc analysis
- **scikit-learn**: Overkill for simple statistics, adds ML complexity

**Integration Approach**:
- New `AnalyticsService` in `src/services/analytics_service.py`
- Load audit logs into pandas DataFrame on-demand
- Calculate metrics: actions/day, time saved, top contacts, bottlenecks
- Pattern detection: anomaly identification (3-sigma rule), trend analysis
- Output weekly insights to `/Insights/` folder as Markdown reports

**Dependencies**:
```toml
pandas = "^2.1.0"
numpy = "^1.26.0"
```

---

## 5. Encryption (Sensitive Data Protection)

**Decision**: cryptography library with AES-256-GCM, OS keychain for key management

**Rationale**:
- cryptography is the standard Python encryption library (maintained by PyCA)
- AES-256-GCM provides authenticated encryption (confidentiality + integrity)
- OS keychain integration (keyring library) for secure key storage
- No keys stored in vault or .env files (uses OS-level secrets)
- Fernet (high-level cryptography API) provides simple encrypt/decrypt

**Alternatives Considered**:
- **PyNaCl (libsodium)**: Good but cryptography is more widely used
- **PyCrypto**: Deprecated, unmaintained
- **Manual AES with pycryptodome**: Cryptography's Fernet is simpler and safer

**Integration Approach**:
- Encryption key stored in OS keychain (macOS Keychain, Windows Credential Manager, Linux keyring)
- `EncryptionService` in `src/services/encryption_service.py`
- Encrypt sensitive Markdown files on write (CRM contacts, financial data, meeting transcripts)
- Encrypted files have `.encrypted` extension, decrypted on read
- Frontmatter indicates encryption status: `encrypted: true`

**Dependencies**:
```toml
cryptography = "^41.0.0"
keyring = "^24.3.0"  # OS keychain integration
```

**Key Management**:
- First-time setup generates master key, stores in OS keychain
- Key identified by `ai-employee-vault-key`
- Rotation: Generate new key, re-encrypt all files (manual process)

---

## 6. Audio Transcription (Meeting Notes)

**Decision**: OpenAI Whisper API (cloud) for MVP, local Whisper model as fallback

**Rationale**:
- Whisper API provides excellent accuracy (state-of-the-art)
- Simple REST API, no local GPU needed
- Cost: $0.006/minute (~$0.36 for 1-hour meeting)
- Fallback to local Whisper (openai-whisper library) if privacy required or offline
- Speaker diarization via pyannote.audio (optional Phase 2 enhancement)

**Alternatives Considered**:
- **Local Whisper only**: Requires GPU, slower processing, but better privacy
- **Google Speech-to-Text**: More expensive ($0.016/minute), less accurate
- **AssemblyAI**: Good API but $0.0125/minute (2x Whisper cost)

**Integration Approach**:
- `TranscriptionService` in `src/services/transcription_service.py`
- Audio files downloaded from video platform APIs
- Upload to Whisper API, receive transcript JSON
- Parse transcript into structured meeting notes
- Local Whisper as fallback when `USE_LOCAL_WHISPER=true` in .env

**Dependencies**:
```toml
openai = "^1.10.0"  # For Whisper API
pydub = "^0.25.0"  # Audio format conversion
openai-whisper = "^20231117"  # Local model (optional)
```

**Configuration**:
- `.env` vars: `OPENAI_API_KEY`, `USE_LOCAL_WHISPER=false`
- Rate limit: 50 requests/minute (sufficient for async processing)

---

## 7. Video Platform APIs

**Decision**: Zoom SDK (zoomus library) for Phase 1, defer Google Meet/Teams to Phase 2

**Rationale**:
- Zoom has highest market share for business meetings
- zoomus library provides Python SDK for Zoom APIs
- Zoom SDK supports: Join meetings, record audio, get participant list, download recordings
- Google Meet API limited (no recording via API, requires Google Workspace Enterprise)
- Microsoft Teams Graph API complex, requires Azure AD app registration

**Alternatives Considered**:
- **Google Meet**: Limited API capabilities for recording
- **Microsoft Teams**: Complex setup, Graph API overhead
- **Support all three**: Too much complexity for MVP

**Integration Approach**:
- New `MeetingService` in `src/services/meeting_service.py`
- Zoom bot joins meeting via SDK, records audio
- Meeting metadata from Google Calendar (attendees, agenda)
- Audio file saved locally, transcribed via Whisper
- Structured notes generated and saved to `/Meetings/`

**Dependencies**:
```toml
zoomus = "^1.1.10"  # Zoom SDK
```

**OAuth Setup**:
- Create Zoom OAuth app in Zoom App Marketplace
- Scopes needed: `meeting:read`, `meeting:write`, `recording:read`, `recording:write`
- Store tokens in `.env`: `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`

**Constraints**:
- Zoom SDK requires Pro/Business account for recording
- Meeting join requires bot to be invited or meeting ID + password
- Recording consent announcement required (legal compliance)

---

## 8. CRM & Contact Management

**Decision**: Markdown files per contact with YAML frontmatter, fuzzy matching for deduplication

**Rationale**:
- Consistent with vault-first architecture (no separate database)
- Each contact = one Markdown file in `/Contacts/` folder
- Frontmatter stores structured data (name, email, phone, relationship strength)
- Body stores freeform notes, conversation history
- fuzzywuzzy library for name deduplication (Levenshtein distance)

**Alternatives Considered**:
- **SQLite database**: Adds dependency, violates local-first principle
- **Single contacts.json file**: Hard to edit manually, merge conflicts
- **Embedded in email/meeting entities**: Fragmented data, hard to query

**Integration Approach**:
- `ContactService` in `src/services/contact_service.py`
- Auto-create contact on first interaction (email, meeting, WhatsApp)
- Deduplicate by email (primary key), fuzzy-match names for duplicates
- Relationship strength score: (interaction_count * 10) + (days_since_last_contact * -1)
- Important dates extracted from conversation via Claude Code (optional enhancement)

**Dependencies**:
```toml
fuzzywuzzy = "^0.18.0"
python-Levenshtein = "^0.25.0"  # Speedup for fuzzywuzzy
```

**Contact File Format**:
```markdown
---
contact_id: CONTACT_abc123
name: John Smith
email: john.smith@example.com
phone: +14155551234
organization: Acme Corp
first_contact: 2026-01-15
last_contact: 2026-02-20
interaction_count: 15
relationship_strength: 135
vip: true
important_dates:
  - date: 2026-05-01
    event: Birthday
tags: [client, vip, executive]
---

# Conversation History

## 2026-02-20 - Project Discussion
- Discussed Q2 roadmap priorities
- Action: Send proposal by Friday
...
```

---

## 9. OCR for Expense Receipts

**Decision**: EasyOCR (local processing) with Claude Code for expense parsing

**Rationale**:
- EasyOCR runs locally (no API cost), supports 80+ languages
- GPU optional (faster) but works on CPU
- Claude Code (already available) parses extracted text into expense fields
- Local processing preserves privacy (no receipt images sent to cloud)
- Fallback to Google Vision API if accuracy insufficient

**Alternatives Considered**:
- **pytesseract/Tesseract**: Lower accuracy, requires installation
- **Google Vision API**: Excellent accuracy but costs $1.50/1000 images
- **AWS Textract**: Expensive, overkill for simple receipts

**Integration Approach**:
- `ExpenseService` in `src/services/expense_service.py`
- Email attachments (PDF/images) saved to `/Receipts/`
- EasyOCR extracts text from receipt images
- Claude Code parses OCR output → (amount, vendor, date, category)
- Expense entity created in `/Expenses/` with receipt link
- Budget tracking checks against monthly limits

**Dependencies**:
```toml
easyocr = "^1.7.0"
Pillow = "^10.2.0"  # Image processing
PyPDF2 = "^3.0.0"  # PDF to image conversion
pdf2image = "^1.17.0"  # Requires poppler binary
```

**Budget Category Defaults**:
- Software, Travel, Office, Marketing, Meals, Transportation, Utilities, Other

---

## 10. Feedback & Learning

**Decision**: JSON feedback storage embedded in entity frontmatter + aggregated analytics

**Rationale**:
- Feedback stored directly in entity files (email, plan, suggestion) for traceability
- Aggregated feedback.json for quick lookup of patterns
- Simple thumbs up/down + optional text feedback
- Learning via confidence scoring (decrease confidence for dismissed suggestions)
- No ML models needed initially (rule-based adjustment)

**Alternatives Considered**:
- **Separate feedback database**: Adds complexity, fragments data
- **Cloud-based learning**: Violates privacy principle
- **Embeddings for similarity**: Overkill for Phase 1, defer to later

**Integration Approach**:
- `FeedbackService` in `src/services/feedback_service.py`
- Entity frontmatter includes `feedback:` section
- User provides feedback via vault-manager skill (thumbs up/down)
- Aggregated analytics:
  - Trust rule effectiveness: approval accuracy per rule
  - Suggestion acceptance rate: per category
  - Document quality: edits required per template
- Confidence adjustment: Rejected suggestions → lower confidence for similar future suggestions

**Dependencies**: None (uses standard library + existing JSON handling)

**Feedback Storage Format**:
```yaml
feedback:
  rating: positive  # positive, negative, neutral
  timestamp: 2026-02-27T14:30:00Z
  feedback_text: "Great summary, saved 20 minutes"
  user_action: accepted  # accepted, rejected, modified
```

**Aggregated Feedback** (`/Logs/feedback_analytics.json`):
```json
{
  "trust_rules": {
    "email_reply_known_contacts": {
      "total_auto_approved": 150,
      "user_would_approve": 142,
      "accuracy": 0.947
    }
  },
  "suggestions": {
    "follow_up_reminders": {
      "total_suggested": 50,
      "accepted": 28,
      "acceptance_rate": 0.56
    }
  }
}
```

---

## Summary of Dependencies

**New pyproject.toml additions**:
```toml
[project.dependencies]
# Already installed from Bronze/Silver:
# - watchdog, python-dotenv, requests, jsonschema, apscheduler

# Google Calendar
google-api-python-client = "^2.100.0"
google-auth-oauthlib = "^1.2.0"
google-auth-httplib2 = "^0.2.0"

# Document Generation
jinja2 = "^3.1.0"
markdown = "^3.5.0"

# Analytics
pandas = "^2.1.0"
numpy = "^1.26.0"

# Encryption
cryptography = "^41.0.0"
keyring = "^24.3.0"

# Audio Transcription
openai = "^1.10.0"
pydub = "^0.25.0"

# Video Platforms
zoomus = "^1.1.10"

# CRM
fuzzywuzzy = "^0.18.0"
python-Levenshtein = "^0.25.0"

# OCR
easyocr = "^1.7.0"
Pillow = "^10.2.0"
PyPDF2 = "^3.0.0"
pdf2image = "^1.17.0"
```

**Optional (local Whisper fallback)**:
```toml
openai-whisper = "^20231117"  # Large download, requires ffmpeg
```

---

## Research Completion

✅ All 10 technology areas researched
✅ Decisions made with rationale
✅ Integration approaches defined
✅ Dependencies documented

**Next Phase**: Data Model Design (data-model.md)
