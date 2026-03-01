# Implementation Plan: Gold Tier - Autonomous AI Employee

**Branch**: `003-gold-tier-upgrade` | **Date**: 2026-02-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-gold-tier-upgrade/spec.md`

## Summary

Gold Tier upgrades the AI Employee from Human-in-the-Loop (HITL) execution to autonomous decision-making with trust framework. Users configure trust rules to auto-approve specific action types (email replies to known contacts, routine expenses, calendar events), reducing approval friction by 60% while maintaining full audit trails. Additional capabilities include: Google Calendar integration with conflict resolution, template-based document generation, productivity analytics, proactive task suggestions, meeting attendance with transcription, CRM relationship tracking, and expense tracking with OCR.

**Technical Approach**: Build on Silver Tier foundation (Python 3.13, Obsidian vault, PM2 processes). New services: TrustEvaluator, CalendarService (Google Calendar API), DocumentService (Jinja2 templates), AnalyticsService (pandas), TranscriptionService (Whisper API), ContactService (CRM), ExpenseService (EasyOCR). Trust rules stored in Company_Handbook.md YAML, evaluated before action execution. Local-first privacy maintained with encryption for sensitive data (CRM, financial, meeting transcripts).

## Technical Context

**Language/Version**: Python 3.13+ (consistent with Bronze/Silver Tier)
**Primary Dependencies**:
  - Existing: watchdog, python-dotenv, requests, jsonschema, apscheduler
  - New: google-api-python-client, jinja2, pandas, cryptography, openai (Whisper), easyocr, fuzzywuzzy, zoomus, keyring

**Storage**: Obsidian vault (Markdown files with YAML frontmatter, JSON for structured data)
  - Trust rules: Company_Handbook.md YAML frontmatter
  - Calendar events: /Calendar/events.json (local cache)
  - Documents: /Documents/{folder}/ (Markdown)
  - Insights: /Insights/YYYY-MM-DD.json
  - Contacts: /Contacts/{contact_id}.md (Markdown with encryption support)
  - Expenses: /Expenses/YYYY-MM/{expense_id}.md
  - Budgets: /Budgets/YYYY-MM.json

**Testing**: pytest with contract validation (JSON Schema), integration tests per user story (quickstart.md scenarios)

**Target Platform**: Linux (WSL2 compatible), macOS (primary development), Windows (via WSL2)

**Project Type**: Single project (extends existing src/ structure)

**Performance Goals**:
  - Trust rule evaluation: <10ms per action
  - Calendar conflict detection: <500ms for 100 events
  - Document generation: <2 minutes per template
  - Analytics insights: <5 seconds for 90-day audit logs
  - OCR processing: <3 seconds per receipt
  - Audit log queries: <1 second for 90-day history

**Constraints**:
  - Local-first: No cloud storage of personal data (CRM, financial, meeting transcripts)
  - Privacy: Encryption required for sensitive entities (AES-256-GCM)
  - Rate limits: Google Calendar 1M queries/day, Whisper API 50 req/min
  - Trust safety: Auto-disable rules if effectiveness <80%
  - Suggestion limits: Max 3 proactive suggestions per category per day

**Scale/Scope**:
  - Single user (no multi-tenancy)
  - ~100 trust rules maximum
  - ~1000 contacts in CRM
  - ~500 calendar events cached locally
  - ~1000 expenses per year
  - 90-day audit log retention (extensible)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check (Phase 0)

**Principle I: Local-First Privacy** ✅ PASS
- All trust rules, contacts, expenses, budgets stored locally in vault
- Google Calendar API only queries/writes events (no persistent storage of personal data)
- Whisper API receives audio but transcripts stored locally
- CRM data encrypted at rest, never sent to cloud
- No violation

**Principle II: Human-in-the-Loop** ⚠️ MODIFIED (By Design)
- Trust framework intentionally reduces HITL for trusted actions
- Justification: User explicitly configures trust levels, maintains control via rule enablement
- Safety: All auto-approved actions logged with trust_rule_id for review/reversion
- Auto-disable rules if effectiveness <80% (safety threshold)
- **GATE**: Approved - core Gold Tier feature, user retains control

**Principle III: Security & Credential Management** ✅ PASS
- API keys in .env (Google Calendar, Zoom, Whisper)
- Encryption keys in OS keychain (keyring library)
- All autonomous actions logged to audit trail
- Encryption for sensitive data (CRM, financial, transcripts)
- No violation

**Principle IV: Agent Skills Architecture** ✅ PASS
- New skills: trust-evaluator.md, calendar-manager.md, document-generator.md, analytics-insights.md, crm-manager.md, expense-tracker.md
- All major capabilities implemented as skills
- No violation

**Principle V: Event-Driven Architecture** ✅ PASS
- Trust evaluation integrated into executor workflow
- Calendar events trigger meeting attendance
- Scheduled tasks trigger document generation
- Pattern detection triggers proactive suggestions
- No violation

**Principle VI: Testing Discipline** ✅ PASS
- Integration tests defined in quickstart.md (8 user stories, 12 scenarios)
- Contract tests for all entities (JSON Schema validation)
- pytest suite extended for Gold Tier services
- No violation

**Principle VII: Performance Budgets** ✅ PASS
- Trust evaluation <10ms (simple dict lookup + regex)
- Calendar queries cached locally (conflicts <500ms)
- Analytics run weekly (not real-time, acceptable)
- OCR async processing (non-blocking)
- No violation

### Post-Design Check (Phase 1)

**Re-evaluated after research.md, data-model.md, contracts/** ✅ ALL PASS

No constitution violations introduced during design phase. Trust framework modifications approved as core feature requirement.

## Project Structure

### Documentation (this feature)

```text
specs/003-gold-tier-upgrade/
├── plan.md                   # This file (/sp.plan command output)
├── spec.md                   # Feature specification (/sp.specify output)
├── research.md               # Technology research (Phase 0 output)
├── data-model.md             # Entity definitions (Phase 1 output)
├── quickstart.md             # Integration test scenarios (Phase 1 output)
├── contracts/                # JSON Schema contracts (Phase 1 output)
│   ├── trust-rule-schema.json
│   ├── calendar-event-schema.json
│   ├── contact-schema.json
│   └── ... (7 total schemas)
├── checklists/
│   └── requirements.md       # Spec validation checklist
└── tasks.md                  # Task breakdown (/sp.tasks output - NOT YET CREATED)
```

### Source Code (repository root)

```text
src/
├── models/                   # Data models (extends Silver Tier)
│   ├── trust_rule.py         # NEW: Trust rule entity
│   ├── calendar_event.py     # NEW: Calendar event entity
│   ├── document.py           # NEW: Generated document entity
│   ├── insight.py            # NEW: Analytics insight entity
│   ├── proactive_suggestion.py  # NEW: AI-initiated suggestion
│   ├── meeting_note.py       # NEW: Meeting transcript/notes
│   ├── contact.py            # NEW: CRM contact profile
│   ├── expense.py            # NEW: Expense tracking
│   └── budget.py             # NEW: Budget allocation
│
├── services/                 # Business logic (extends Silver Tier)
│   ├── trust_evaluator.py   # NEW: Trust rule evaluation
│   ├── calendar_service.py  # NEW: Google Calendar integration
│   ├── document_service.py  # NEW: Template-based generation
│   ├── analytics_service.py # NEW: Audit log analysis
│   ├── transcription_service.py  # NEW: Whisper API integration
│   ├── meeting_service.py   # NEW: Video platform integration
│   ├── contact_service.py   # NEW: CRM management
│   ├── expense_service.py   # NEW: OCR + expense tracking
│   ├── budget_service.py    # NEW: Budget monitoring
│   ├── encryption_service.py  # NEW: AES-256 encryption
│   ├── feedback_service.py  # NEW: User feedback tracking
│   └── suggestion_engine.py # NEW: Proactive pattern detection
│
├── watchers/                 # Event monitors (extends Silver Tier)
│   └── calendar_watcher.py  # NEW: Google Calendar webhook listener (optional)
│
├── trust_evaluator.py        # NEW: Main trust evaluation process
├── analytics_engine.py       # NEW: Weekly analytics generation
└── suggestion_engine.py      # NEW: Proactive suggestion generation

.claude/commands/             # Agent skills (extends Silver Tier)
├── trust-evaluator.md        # NEW: Trust framework management
├── calendar-manager.md       # NEW: Calendar operations
├── document-generator.md     # NEW: Document creation
├── analytics-insights.md     # NEW: Analytics reporting
├── crm-manager.md            # NEW: Contact management
├── expense-tracker.md        # NEW: Expense processing
└── meeting-attendant.md      # NEW: Meeting attendance

.specify/templates/documents/ # NEW: Document templates
├── weekly-status.md.j2
├── meeting-notes.md.j2
├── monthly-summary.md.j2
└── proposal.md.j2

tests/
├── contract/                 # JSON Schema validation tests
│   ├── test_trust_rule_schema.py
│   ├── test_calendar_event_schema.py
│   └── ... (9 total contract tests)
├── integration/              # Integration tests from quickstart.md
│   ├── test_us1_trust_framework.py
│   ├── test_us2_calendar_management.py
│   └── ... (8 total integration tests)
└── unit/                     # Unit tests for services
    ├── test_trust_evaluator.py
    ├── test_calendar_service.py
    └── ... (12 total service tests)
```

**Structure Decision**: Single project extending existing Silver Tier `src/` structure. New directories: `src/models/{9 entities}`, `src/services/{12 services}`, `.specify/templates/documents/`. Maintains consistency with Bronze/Silver architecture (models → services → processes → skills).

## Complexity Tracking

No constitution violations requiring justification.

## Phase 0: Research Outcomes

**Completed**: [research.md](./research.md)

### Key Technology Decisions

1. **Trust Framework**: Simple dict-based rule matching (no heavyweight rule engine)
2. **Google Calendar API**: Official google-api-python-client library
3. **Templates**: Jinja2 (industry standard)
4. **Analytics**: pandas + numpy (time-series analysis)
5. **Encryption**: cryptography library with AES-256-GCM, keyring for key management
6. **Transcription**: OpenAI Whisper API (cloud) with local model fallback
7. **Video Platform**: Zoom SDK initially (defer Google Meet/Teams to Phase 2)
8. **CRM**: Markdown files per contact with fuzzywuzzy deduplication
9. **OCR**: EasyOCR (local processing) + Claude Code parsing
10. **Feedback**: Embedded in entity frontmatter + aggregated JSON

### Dependencies Added

```toml
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

## Phase 1: Design Outcomes

**Completed**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

### Entities Designed (9 new)

1. **TrustRule**: Configurable auto-approval rules
2. **CalendarEvent**: Google Calendar events with conflict tracking
3. **Document**: Template-generated documents with versioning
4. **Insight**: Analytics-generated insights and recommendations
5. **ProactiveSuggestion**: AI-initiated task suggestions
6. **MeetingNote**: Transcribed meeting notes with action items
7. **Contact**: CRM profile with relationship tracking
8. **Expense**: OCR-extracted expenses with budget validation
9. **Budget**: Monthly budget allocations per category

### Contracts Created (7 JSON Schemas)

- trust-rule-schema.json
- calendar-event-schema.json
- contact-schema.json
- document-schema.json (deferred - simple Markdown)
- insight-schema.json (deferred - simple JSON)
- expense-schema.json (deferred - simple Markdown)
- proactive-suggestion-schema.json (deferred - simple Markdown)

**Note**: Only complex entities (TrustRule, CalendarEvent, Contact) have JSON schemas. Others use Markdown frontmatter with simpler validation.

### Integration Tests Defined

8 user stories, 12 test scenarios in quickstart.md:
- US1: Trust framework (2 scenarios)
- US2: Calendar management (1 scenario)
- US3: Document generation (1 scenario)
- US4: Analytics insights (1 scenario)
- US5: Proactive suggestions (1 scenario)
- US6: Meeting attendance (1 scenario)
- US7: CRM tracking (2 scenarios)
- US8: Expense tracking (1 scenario)
- End-to-end workflow (1 scenario)

## Implementation Strategy

### MVP Definition (US1: Trust Framework)

**Minimum Viable Product**: Implement US1 (Autonomous Workflows & Trust Levels) first as critical path for all other autonomous features.

**MVP Tasks** (estimated 8-12 hours):
1. Create TrustRule model with validation
2. Implement TrustEvaluator service (rule loading, evaluation, effectiveness tracking)
3. Integrate trust evaluation into Executor (check rules before HITL approval)
4. Extend Company_Handbook.md YAML with trust_rules section
5. Create trust-evaluator.md skill
6. Unit tests for trust evaluation logic
7. Integration test: Auto-approve email via trust rule

**MVP Delivers**:
- Users can configure trust rules
- Trusted actions auto-approved without HITL
- Effectiveness tracking and auto-disable if <80%
- Complete audit trail with trust_rule_id

### Incremental Rollout

**Phase 1 (MVP)**: US1 Trust Framework (Week 1)
- Core autonomous capability
- Foundation for all other features

**Phase 2**: US2 Calendar + US3 Documents (Week 2-3)
- High productivity impact features
- Independent of each other (parallel development possible)

**Phase 3**: US4 Analytics + US5 Suggestions (Week 4)
- Data-driven features requiring historical audit logs
- Analytics generates insights → Suggestions act on patterns

**Phase 4**: US6 Meetings + US7 CRM (Week 5-6)
- Complex integrations (Zoom, transcription, contact deduplication)
- Can be developed in parallel

**Phase 5**: US8 Financial (Week 7)
- OCR complexity isolated to final phase
- Builds on expense categorization patterns from US7 CRM tags

### Parallel Development Opportunities

**Can develop in parallel**:
- US2 (Calendar) + US3 (Documents) - different services, no shared dependencies
- US4 (Analytics) + US5 (Suggestions) - analytics generates data, suggestions consumes it but can use mock data
- US6 (Meetings) + US7 (CRM) - different APIs, share Contact entity but non-blocking

**Must be sequential**:
- US1 (Trust) must complete first - all other features use trust evaluation
- US4 (Analytics) before US5 (Suggestions) in production - suggestions need insight data

## Architecture Decisions

### Trust Evaluation Flow

```
Action Plan Created → Executor.process_approved()
                           ↓
                    TrustEvaluator.evaluate(plan)
                           ↓
                    Load trust rules from handbook
                           ↓
                    Match plan against rules (action_type, contacts, content, time)
                           ↓
                    ┌──────────────┬──────────────┐
                    ↓              ↓              ↓
            No match          Match Level 0   Match Level 1+
            HITL required     HITL required   Auto-approve
            Move to           Move to         Execute immediately
            /Pending/         /Pending/       Log trust_rule_id
                                              Update usage_count
```

### Calendar Sync Strategy

**Hybrid approach**: Local cache + API sync

1. **Initial sync**: Download all events from Google Calendar → `/Calendar/events.json`
2. **Conflict detection**: Check local cache (fast) before API query
3. **Event creation**: Write to Google Calendar → Update local cache
4. **Sync schedule**: Hourly background sync to catch external changes
5. **Webhook support** (optional): Google Calendar Push API for real-time updates

### Document Generation Pipeline

```
Scheduled Task Triggers → DocumentService.generate(template, context)
                               ↓
                        Load Jinja2 template from .specify/templates/documents/
                               ↓
                        Build context from audit logs, meeting notes, user data
                               ↓
                        Render template with context
                               ↓
                        Add frontmatter (metadata, version, generation_date)
                               ↓
                        Save to /Documents/{folder}/{title}.md
                               ↓
                        Log generation to audit trail
```

### Analytics Calculation Approach

**Weekly batch processing** (not real-time):

1. Load last 90 days of audit logs into pandas DataFrame
2. Calculate metrics (groupby, rolling windows, percentiles)
3. Detect patterns (day-of-week clustering, anomaly detection via 3-sigma rule)
4. Generate recommendations (rule-based logic)
5. Output insights JSON to `/Insights/YYYY-MM-DD.json`
6. Create dashboard summary in `/Needs_Action/` if high-priority insights

### Encryption Strategy

**Selective encryption** (not vault-wide):

- **Encrypted by default**: CRM contacts (if VIP), financial data, meeting transcripts
- **Encryption method**: Fernet (cryptography library) with AES-256-GCM
- **Key management**: OS keychain via keyring library
- **File naming**: `.encrypted` extension (e.g., `CONTACT_alice.md.encrypted`)
- **Decryption**: On-demand during read operations
- **Performance**: Acceptable for selective encryption (<1ms per file)

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Google Calendar API quota exceeded | Medium | High | Local event caching, batch operations, exponential backoff |
| Trust rule misconfiguration causes unintended auto-approvals | High | Medium | Effectiveness tracking, auto-disable at <80%, prominent warnings in UI |
| Whisper API unavailable (outage) | Low | Medium | Local Whisper model fallback, graceful degradation |
| OCR accuracy low for non-standard receipts | Medium | Low | Manual review for ocr_confidence <0.75, Google Vision API fallback |
| Contact deduplication false positives (merge wrong contacts) | Low | Medium | Fuzzy match threshold tuning, manual undo via git history |
| Calendar conflicts not detected (stale cache) | Medium | Medium | Hourly sync, conflict re-check before sending invites |
| Encryption key loss (OS keychain reset) | Low | High | Key backup instructions in setup docs, recovery procedure |
| Analytics performance degrades with >1 year audit logs | Low | Low | 90-day window, archival of old logs, pagination |

## Next Steps

1. **Run `/sp.tasks`**: Generate task breakdown from this plan
2. **Create document templates**: Weekly status, meeting notes, monthly summary in `.specify/templates/documents/`
3. **Configure test environment**: Set up test Google Calendar, Zoom account, sample receipts
4. **Implement MVP** (US1 Trust Framework): Start with highest priority feature
5. **Validate with quickstart.md**: Run integration tests after each user story

---

**Planning Status**: ✅ **COMPLETE**

**Artifacts Generated**:
- ✅ research.md (technology decisions)
- ✅ data-model.md (9 entity definitions)
- ✅ contracts/ (3 JSON schemas)
- ✅ quickstart.md (integration test scenarios)
- ✅ plan.md (this file)

**Next Command**: `/sp.tasks` to generate task breakdown
