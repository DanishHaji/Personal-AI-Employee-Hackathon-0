# Gold Tier Quickstart Guide

**Feature**: 003-gold-tier-upgrade
**Date**: 2026-02-27
**Purpose**: Integration test scenarios and usage examples

---

## Prerequisites

Before testing Gold Tier features, ensure:

1. ✅ **Silver Tier operational**: All Silver processes running (executor, scheduler, whatsapp-watcher)
2. ✅ **30+ days audit log history**: Analytics requires historical data
3. ✅ **Obsidian vault initialized**: All folders present
4. ✅ **Dependencies installed**: `uv sync` with new Gold Tier dependencies

---

## US1: Autonomous Workflows & Trust Levels

**Goal**: Configure trust rules to auto-approve specific actions without manual approval

### Test Scenario 1.1: Create Trust Rule for Email Replies

**Setup**:
1. Open `Company_Handbook.md` in Obsidian
2. Add trust rule to YAML frontmatter:

```yaml
---
trust_rules:
  - rule_id: RULE_email_known_contacts
    rule_name: "Email Replies to Known Contacts"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@yourcompany.com"]
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: 2026-02-27T10:00:00Z
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: true
---
```

3. Save file

**Test**:
1. Receive email from `colleague@yourcompany.com`
2. AI generates reply plan
3. Executor checks trust rules
4. **Expected**: Email auto-approved and sent WITHOUT moving to /Pending_Approval/
5. **Verify**: Check audit log for `"approved_by": "auto"` and `"trust_rule_id": "RULE_email_known_contacts"`

**Success Criteria**:
- ✅ Email sent automatically within 2 minutes
- ✅ Audit log shows `approved_by: auto`
- ✅ Trust rule usage_count incremented
- ✅ No file in /Pending_Approval/

---

## US2: Calendar & Meeting Management

**Goal**: Autonomously schedule meetings with conflict detection and Google Calendar sync

### Test Scenario 2.1: Schedule Meeting with Availability Check

**Setup**:
1. Ensure Google Calendar API credentials configured (`.env` has `GOOGLE_CALENDAR_CREDENTIALS_PATH`)
2. Authenticate: `uv run python -c "from src.services.calendar_service import CalendarService; CalendarService().authenticate()"`

**Test**:
1. Create meeting request file in `/Needs_Action/MEETING_request_q2_planning.md`:

```markdown
---
type: meeting_request
title: "Q2 Planning Meeting"
attendees: ["john@example.com", "jane@example.com"]
duration_minutes: 60
preferred_times: ["2026-03-15T14:00:00-07:00", "2026-03-16T10:00:00-07:00"]
priority: high
---

# Meeting Request: Q2 Planning

Need to schedule Q2 planning meeting with John and Jane.

**Agenda**:
- Review Q1 results
- Define Q2 objectives
- Resource allocation
```

2. Move to `/Approved/`
3. Wait for executor to process

**Expected**:
1. Executor queries Google Calendar for availability
2. Detects conflicts with first preferred time
3. Schedules meeting at second time slot (2026-03-16T10:00:00-07:00)
4. Sends calendar invites to attendees
5. Creates local cache in `/Calendar/events.json`
6. Moves plan to `/Done/` with execution details

**Success Criteria**:
- ✅ Meeting appears in Google Calendar
- ✅ Attendees receive calendar invites
- ✅ No conflicts with existing events
- ✅ Local cache updated with event details

---

## US3: Document Generation & Editing

**Goal**: Auto-generate documents from templates using audit log data

### Test Scenario 3.1: Generate Weekly Status Report

**Setup**:
1. Ensure template exists: `.specify/templates/documents/weekly-status.md.j2`
2. Configure scheduled task in `Company_Handbook.md`:

```yaml
scheduled_tasks:
  - task_id: weekly_status_report
    task_name: "Weekly Status Report"
    task_type: document_generation
    schedule_pattern: "0 17 * * 5"  # Fridays at 5pm
    enabled: true
    parameters:
      template: "weekly-status.md.j2"
      output_folder: "Documents/Status Reports"
```

**Test** (Manual trigger for testing):
1. Run: `uv run python src/services/document_service.py --template weekly-status.md.j2 --output-folder "Documents/Status Reports"`

**Expected**:
1. Document service loads template
2. Queries audit logs for past 7 days
3. Populates template context with:
   - Emails sent count
   - Meetings attended count
   - Tasks completed count
   - Key accomplishments from logs
4. Generates document in `/Documents/Status Reports/Weekly_Status_2026_02_27.md`
5. Document includes frontmatter with metadata

**Success Criteria**:
- ✅ Document created with correct filename
- ✅ Content includes accurate metrics from audit logs
- ✅ Frontmatter has template_used and generation_date
- ✅ Document readable in Obsidian

---

## US4: Advanced Analytics & Insights

**Goal**: Generate weekly insights from audit log analysis

### Test Scenario 4.1: Run Analytics and Review Insights

**Setup**:
1. Ensure 30+ days of audit log history exists in `/Logs/`

**Test**:
1. Run analytics: `uv run python src/services/analytics_service.py --generate-insights --output /Insights/2026-02-27.json`

**Expected**:
1. Analytics service loads last 30 days of audit logs into pandas DataFrame
2. Calculates metrics:
   - Total actions per day average
   - Email volume by day of week
   - Meeting attendance patterns
   - Trust rule effectiveness scores
   - Response time trends
3. Detects patterns and anomalies (e.g., "40% of emails sent on Mondays")
4. Generates recommendations
5. Outputs insights JSON to `/Insights/2026-02-27.json`

**Success Criteria**:
- ✅ Insights file created with valid JSON
- ✅ Contains at least 3 insights
- ✅ Each insight has metrics, recommendations, confidence score
- ✅ Patterns make sense (verifiable against audit logs)

---

## US5: Proactive Task Suggestions

**Goal**: AI detects patterns and proactively suggests follow-up actions

### Test Scenario 5.1: Follow-up Email Suggestion

**Setup**:
1. Send important email 3+ days ago with no reply
2. Mark email as important in frontmatter: `priority: high`

**Test**:
1. Wait for proactive suggestion engine to run (scheduled hourly)
2. Check `/Needs_Action/` for suggestion files

**Expected**:
1. Suggestion engine detects:
   - Email sent 3+ days ago
   - No reply received
   - Email marked as important
2. Creates suggestion file: `/Needs_Action/SUGGEST_followup_2026_02_27.md`
3. Suggestion includes:
   - Context about original email
   - Draft follow-up message
   - Link to original email entity
   - Confidence score

**Success Criteria**:
- ✅ Suggestion file created in /Needs_Action/
- ✅ Draft message is polite and contextually relevant
- ✅ Confidence score > 0.7
- ✅ Related email ID correctly referenced

---

## US6: Meeting Attendance & Notes

**Goal**: AI joins Zoom meeting, records audio, generates transcript and structured notes

### Test Scenario 6.1: Attend and Transcribe Meeting

**Setup**:
1. Configure Zoom OAuth credentials in `.env`
2. Create calendar event with Zoom link
3. Mark AI as attendee in event

**Test**:
1. Join test Zoom meeting as human
2. AI bot joins 1 minute after meeting starts
3. AI announces: "AI Assistant joining to take notes. Recording will begin with your consent."
4. Give verbal consent
5. Have 5-minute test conversation
6. End meeting

**Expected**:
1. AI downloads meeting audio
2. Uploads to Whisper API for transcription
3. Receives transcript JSON
4. Generates structured meeting notes in `/Meetings/2026-02-27_test_meeting.md`
5. Extracts any action items mentioned
6. Creates tasks in /Needs_Action/ for action items

**Success Criteria**:
- ✅ Meeting notes file created
- ✅ Transcript accuracy > 85% (manually verify)
- ✅ Attendees list matches actual participants
- ✅ Action items extracted correctly (if any mentioned)
- ✅ Recording link works

---

## US7: CRM Integration

**Goal**: Track contacts across all interactions and detect relationship staleness

### Test Scenario 7.1: Auto-Create Contact Profile

**Setup**:
1. Ensure no existing contact for `newcontact@example.com`

**Test**:
1. Receive email from `newcontact@example.com` with name "Alice Johnson"
2. AI processes email

**Expected**:
1. ContactService detects new email address
2. Creates contact file: `/Contacts/CONTACT_alice_johnson.md`
3. Populates frontmatter:
   - name: "Alice Johnson" (extracted from email)
   - email: "newcontact@example.com"
   - first_contact_date: today
   - last_contact_date: today
   - interaction_count: 1
   - relationship_strength: 10
4. Body includes conversation history with first email

**Success Criteria**:
- ✅ Contact file created with correct name
- ✅ Email address matches
- ✅ Interaction count = 1
- ✅ Conversation history shows first email

### Test Scenario 7.2: Stale Relationship Detection

**Setup**:
1. Create VIP contact with last_contact_date 31 days ago

**Test**:
1. Wait for CRM monitoring to run (scheduled daily)

**Expected**:
1. CRM service detects VIP contact with 30+ days no contact
2. Creates proactive suggestion in `/Needs_Action/SUGGEST_relationship_alice.md`
3. Suggestion includes:
   - Previous conversation context
   - Recommended check-in message
   - Relationship history summary

**Success Criteria**:
- ✅ Suggestion created for stale relationship
- ✅ Context references previous interactions
- ✅ Draft message is personalized

---

## US8: Financial Tracking

**Goal**: Extract expense details from receipts and track against budgets

### Test Scenario 8.1: Process Receipt Email with OCR

**Setup**:
1. Ensure EasyOCR installed
2. Configure budget in `/Budgets/2026-02.json`:

```json
{
  "month": "2026-02",
  "budgets": [
    {
      "budget_id": "BUDGET_software_2026_02",
      "category": "software",
      "monthly_limit": 500.00,
      "current_spend": 250.00,
      "alert_threshold": 0.80,
      "currency": "USD"
    }
  ]
}
```

**Test**:
1. Send test email to Gmail with receipt attachment (e.g., Adobe invoice PDF)
2. Email subject: "Receipt - Adobe Creative Cloud"
3. Wait for Gmail watcher to detect and process

**Expected**:
1. Email watcher saves receipt to `/Receipts/`
2. ExpenseService detects receipt attachment
3. Runs EasyOCR on receipt image
4. Parses OCR text with Claude Code:
   - amount: $45.99
   - vendor: "Adobe Creative Cloud"
   - date: "2026-02-27"
   - category: "software" (keyword matching)
5. Creates expense entity: `/Expenses/2026-02/EXPENSE_2026_02_27_001.md`
6. Checks budget: current_spend=250 + 45.99 = 295.99 (59% of 500 limit)
7. Auto-approves (under threshold)
8. Updates budget JSON file

**Success Criteria**:
- ✅ Expense file created with correct amount
- ✅ OCR confidence > 0.85
- ✅ Category correctly assigned
- ✅ Budget updated
- ✅ No alert triggered (under 80% threshold)

---

## Integration Test: End-to-End Workflow

**Goal**: Test complete autonomous workflow with trust levels

### Scenario: Auto-Reply → Meeting Schedule → Notes Generation

1. **Email Arrives** (auto-approved via trust rule):
   - Receive email from known contact requesting meeting
   - Trust rule auto-approves AI reply confirming availability
   - Reply sent within 2 minutes

2. **Meeting Scheduled** (calendar automation):
   - AI detects meeting request in email
   - Checks calendar availability
   - Schedules meeting for next available slot
   - Sends calendar invite
   - Creates local event cache

3. **Meeting Attended** (AI joins and records):
   - AI joins Zoom meeting at scheduled time
   - Records audio with consent
   - Transcribes via Whisper API

4. **Notes Generated** (document automation):
   - AI generates meeting notes from transcript
   - Extracts 2 action items
   - Creates tasks in /Needs_Action/

5. **Follow-up Scheduled** (proactive suggestion):
   - After 3 days, AI detects action item not completed
   - Creates reminder suggestion
   - Suggests follow-up with meeting participant

**Success Criteria**:
- ✅ All 5 steps complete autonomously
- ✅ No manual approval required (trust rules active)
- ✅ All entities created correctly (email, calendar event, meeting notes, tasks, suggestion)
- ✅ Audit log shows complete chain of actions
- ✅ Total time from email arrival to follow-up suggestion: < 4 days

---

## Troubleshooting

### Trust Rules Not Auto-Approving

**Symptoms**: Actions still going to /Pending_Approval/ despite trust rule

**Check**:
1. Verify trust rule enabled: `enabled: true`
2. Check action_type matches: `email_send` vs `social_post`
3. Verify contact filter matches sender
4. Check effectiveness_score not below 0.80 (auto-disabled threshold)

**Fix**:
```bash
# Check trust rule configuration
cat vault/Company_Handbook.md | grep -A 15 "trust_rules:"

# Check audit logs for rule evaluation
cat vault/Logs/$(date +%Y-%m-%d).json | grep trust_rule
```

### Calendar API Rate Limit

**Symptoms**: Calendar operations fail with 429 errors

**Check**:
- Google Calendar API quota: 1M queries/day per project
- Current usage in Google Cloud Console

**Fix**:
- Wait for quota reset (midnight Pacific Time)
- Reduce calendar sync frequency
- Cache events locally longer

### OCR Low Accuracy

**Symptoms**: Expense amounts/vendors extracted incorrectly

**Check**:
- Receipt image quality (should be >300 DPI)
- `ocr_confidence` field in expense entity

**Fix**:
- Use higher resolution receipt images
- Enable `USE_GOOGLE_VISION_API=true` in .env for better accuracy (costs $1.50/1000 images)
- Manually correct low-confidence extractions (<0.75)

---

## Next Steps After Quickstart

1. **Review audit logs**: Verify all actions logged correctly
2. **Adjust trust levels**: Based on effectiveness scores, expand or restrict auto-approval
3. **Customize templates**: Modify document templates in `.specify/templates/documents/`
4. **Configure budgets**: Set realistic monthly limits per category
5. **Train on suggestions**: Accept/reject proactive suggestions to improve future relevance
6. **Review insights**: Act on analytics recommendations to optimize workflows

---

**Quickstart Complete** ✅

All Gold Tier features tested and verified!
