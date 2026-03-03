# Gold Tier Troubleshooting Guide

**Personal AI Employee - Gold Tier**
**Version**: 1.0.0
**Last Updated**: 2026-03-02

Comprehensive troubleshooting for all Gold Tier features.

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [US1: Trust Framework](#us1-trust-framework)
3. [US2: Calendar Management](#us2-calendar-management)
4. [US3: Document Generation](#us3-document-generation)
5. [US4: Analytics & Insights](#us4-analytics--insights)
6. [US5: Proactive Suggestions](#us5-proactive-suggestions)
7. [US6: Meeting Attendance](#us6-meeting-attendance)
8. [US7: CRM Integration](#us7-crm-integration)
9. [US8: Financial Tracking](#us8-financial-tracking)
10. [Performance Issues](#performance-issues)
11. [Data Recovery](#data-recovery)

---

## Common Issues

### PM2 Process Crashed

**Symptom**: Process shows "errored" or "stopped" in `pm2 status`

**Solution**:
```bash
# Check error logs
pm2 logs <process-name> --err --lines 50

# Restart process
pm2 restart <process-name>

# If continues crashing, delete and recreate
pm2 delete <process-name>
pm2 start src/<path>/<file>.py --name <process-name> --interpreter python3
```

**Common Causes**:
- Missing API credentials
- Invalid .env configuration
- Vault path not accessible
- Dependency not installed

---

### Vault Path Not Found

**Symptom**: `ERROR: Vault path does not exist`

**Solution**:
```bash
# Check VAULT_PATH in .env
cat .env | grep VAULT_PATH

# Verify path exists
ls -la "$VAULT_PATH"

# Create if missing
mkdir -p "$VAULT_PATH"
uv run python scripts/init_vault.py --path "$VAULT_PATH"
```

---

### Audit Log Missing

**Symptom**: `FileNotFoundError: Logs/audit_log.jsonl`

**Solution**:
```bash
# Create logs directory
mkdir -p "$VAULT_PATH/Logs"
touch "$VAULT_PATH/Logs/audit_log.jsonl"

# Initialize audit service
uv run python -c "from src.services.audit_service import AuditService; AuditService('$VAULT_PATH').log_action('system_init', 'Audit log initialized')"
```

---

### Encryption Key Not Found

**Symptom**: `keyring.errors.KeyringError: No recommended backend`

**Solution**:
```bash
# Check keyring backend
uv run python -c "import keyring; print(keyring.get_keyring())"

# Set system keyring (Linux)
sudo apt-get install gnome-keyring

# Set file-based fallback
export KEYRING_BACKEND=file
```

See [Encryption Backup Guide](./encryption-backup.md) for key recovery.

---

## US1: Trust Framework

### Trust Rules Not Loading

**Symptom**: Trust evaluation always returns "no match"

**Diagnosis**:
```bash
# Check rules loaded
uv run python -c "from src.services.trust_evaluator import TrustEvaluator; te = TrustEvaluator('$VAULT_PATH'); print(f'Loaded {len(te.rules)} rules'); print(te.rules)"
```

**Solutions**:

1. **Check YAML Syntax** in `Company_Handbook.md`:
```yaml
# Correct format
trust_rules:
  - rule_id: "TRUST_001"
    action_type: "email_reply"
    auto_approve: true

# Incorrect (missing dash)
trust_rules:
  rule_id: "TRUST_001"  # ❌ Missing dash before rule_id
```

2. **Verify Rule IDs are Unique**:
```bash
# Check for duplicates
grep "rule_id:" Company_Handbook.md | sort | uniq -d
```

3. **Test Rule Matching**:
```bash
uv run python -c "
from src.services.trust_evaluator import TrustEvaluator
from src.models.action_plan import ActionPlan

te = TrustEvaluator('$VAULT_PATH')
plan = ActionPlan(action_plan_id='TEST_001', action_type='email_reply', ...)
result = te.evaluate(plan)
print(f'Match: {result}')
"
```

---

### Trust Rule Auto-Disabled

**Symptom**: Rule stopped auto-approving, `enabled: false` in audit log

**Cause**: Effectiveness score dropped below 0.80

**Solution**:
```bash
# Check effectiveness scores
grep "effectiveness_score" Logs/audit_log.jsonl | tail -10

# Review recent actions
grep "TRUST_001" Logs/audit_log.jsonl | tail -20

# Re-enable after fixing issues
# Edit Company_Handbook.md and set enabled: true
```

**Prevention**:
- Review trust rule patterns regularly
- Adjust `contact_filter` or `content_pattern` if too broad
- Lower `TRUST_EFFECTIVENESS_THRESHOLD` in .env (default: 0.80)

---

## US2: Calendar Management

### Google Calendar API Quota Exceeded

**Symptom**: `HttpError 429: Rate limit exceeded`

**Check Quota**:
- Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Quotas
- Calendar API: 1M queries/day default

**Solutions**:

1. **Reduce Sync Frequency**:
```bash
# In .env
CALENDAR_SYNC_INTERVAL=7200  # Increase from 3600 to 2 hours
```

2. **Request Quota Increase**:
   - Google Cloud Console → Quotas → Calendar API → Request Increase

3. **Enable Caching**:
   - Calendar events cached in `/Calendar/events.json`
   - Check cache hit rate:
```bash
grep "cache_hit" Logs/audit_log.jsonl | wc -l
```

---

### Calendar Credentials Expired

**Symptom**: `google.auth.exceptions.RefreshError: invalid_grant`

**Solution**:
```bash
# Delete expired token
rm google_calendar_token.json

# Re-authenticate
uv run python -c "from src.services.calendar_service import CalendarService; CalendarService('$VAULT_PATH', './google_calendar_credentials.json', './google_calendar_token.json').authenticate()"

# Restart calendar watcher
pm2 restart calendar-watcher
```

---

### Conflict Detection Not Working

**Symptom**: Overlapping meetings scheduled

**Diagnosis**:
```bash
# Check conflict detection logic
uv run python -c "
from src.services.calendar_service import CalendarService
from datetime import datetime, timedelta

cs = CalendarService('$VAULT_PATH', './google_calendar_credentials.json', './google_calendar_token.json')
now = datetime.now()
conflicts = cs.check_availability(now, now + timedelta(hours=1))
print(f'Conflicts: {conflicts}')
"
```

**Solutions**:
- Verify `work_hours` in `Company_Handbook.md` are correct timezone
- Check calendar permissions (must have edit access)
- Ensure recurring events are parsed correctly

---

## US3: Document Generation

### Template Not Found

**Symptom**: `FileNotFoundError: weekly-status.md.j2`

**Solution**:
```bash
# Check template directory
ls -la .specify/templates/documents/

# Create if missing
mkdir -p .specify/templates/documents/

# Copy default templates
cp .specify/templates/phr-template.prompt.md .specify/templates/documents/
```

---

### Template Variables Missing

**Symptom**: `jinja2.exceptions.UndefinedError: 'week' is undefined`

**Solution**:
```bash
# Check template context
uv run python -c "
from src.services.document_service import DocumentService
ds = DocumentService('$VAULT_PATH')
context = ds._build_template_context()
print(context.keys())
"
```

**Fix**: Provide required variables when generating:
```python
service.generate_from_template('weekly-status.md.j2', {'week': '2026-W09'})
```

---

### Generated Document Missing Data

**Symptom**: Document created but sections are empty

**Cause**: Insufficient audit log data

**Solution**:
```bash
# Check audit log has data
wc -l Logs/audit_log.jsonl

# Verify date range
head -1 Logs/audit_log.jsonl
tail -1 Logs/audit_log.jsonl
```

**Fix**: Wait for more audit log entries or manually add test data.

---

## US4: Analytics & Insights

### No Insights Generated

**Symptom**: `/Insights/` directory empty

**Diagnosis**:
```bash
# Check analytics engine running
pm2 status | grep analytics-engine

# Check minimum days requirement
uv run python -c "
from src.services.analytics_service import AnalyticsService
import pandas as pd
from datetime import datetime, timedelta

as_svc = AnalyticsService('$VAULT_PATH')
df = as_svc._load_audit_logs(datetime.now() - timedelta(days=30), datetime.now())
print(f'Audit log entries: {len(df)}')
"
```

**Solutions**:

1. **Not Enough Data**: Wait for 30+ days of audit logs
2. **Schedule Not Run**: Check cron schedule in `Company_Handbook.md`
3. **Manual Generation**:
```bash
uv run python -c "from src.services.analytics_service import AnalyticsService; AnalyticsService('$VAULT_PATH').generate_weekly_insights()"
```

---

### Pattern Detection Incorrect

**Symptom**: Patterns detected don't match actual behavior

**Diagnosis**:
```bash
# Check pattern detection logic
grep "pattern_detected" Logs/audit_log.jsonl | tail -20
```

**Tuning**:
- Adjust anomaly detection threshold (default: 3 sigma)
- Increase sample size (wait for more data)
- Review day-of-week clustering parameters

---

## US5: Proactive Suggestions

### Too Many Suggestions

**Symptom**: `/Needs_Action/` flooded with `SUGGEST_*` files

**Solution**:
```bash
# Reduce suggestion frequency
# In .env
MAX_SUGGESTIONS_PER_CATEGORY=1  # Reduce from 3

# Opt out of categories in Company_Handbook.md
suggestion_preferences:
  opt_out_categories:
    - recurring_pattern  # Disable if too noisy
```

---

### No Suggestions Generated

**Symptom**: No `SUGGEST_*` files created

**Diagnosis**:
```bash
# Check suggestion engine running
pm2 status | grep suggestion-engine

# Test suggestion logic
uv run python -c "
from src.services.suggestion_engine import SuggestionEngine
se = SuggestionEngine('$VAULT_PATH')
suggestions = se.detect_follow_ups()
print(f'Follow-ups detected: {len(suggestions)}')
"
```

**Solutions**:
- Wait for patterns to emerge (3+ days of similar behavior)
- Check `enabled_categories` in `Company_Handbook.md`
- Verify suggestion engine enabled in .env

---

### Suggestions Not Relevant

**Symptom**: Suggestions don't match user needs

**Solution**:
- Dismiss irrelevant suggestions (feedback tracked)
- Adjust detection thresholds in `suggestion_engine.py`
- Opt out of specific categories

---

## US6: Meeting Attendance

### Zoom SDK Authentication Failed

**Symptom**: `ZoomError: Invalid API key`

**Solution**:
```bash
# Verify API credentials
echo $ZOOM_API_KEY
echo $ZOOM_API_SECRET

# Test authentication
uv run python -c "
from src.services.meeting_service import MeetingService
ms = MeetingService('$VAULT_PATH')
print('Zoom auth successful')
"
```

**Get New Keys**: https://marketplace.zoom.us/ → Develop → Create App

---

### Whisper API Quota Exceeded

**Symptom**: `OpenAIError: Rate limit exceeded (50 req/min)`

**Solutions**:

1. **Use Local Whisper**:
```bash
# In .env
USE_LOCAL_WHISPER=true

# Install local Whisper
uv add whisper
```

2. **Reduce Meeting Attendance**: Only join critical meetings

3. **Batch Processing**: Process recordings in off-peak hours

---

### Transcription Accuracy Low

**Symptom**: Transcript contains many errors

**Solutions**:
- Ensure audio quality is good (not echo/background noise)
- Use larger Whisper model: `whisper-1` → `whisper-large-v3`
- Manually review and correct transcripts

---

## US7: CRM Integration

### Duplicate Contacts Created

**Symptom**: Multiple `CONTACT_*` files for same person

**Diagnosis**:
```bash
# Check fuzzy matching threshold
grep "duplicate_detected" Logs/audit_log.jsonl
```

**Solution**:
```bash
# Manually merge duplicates
uv run python -c "
from src.services.contact_service import ContactService
cs = ContactService('$VAULT_PATH')
cs.merge_contacts('CONTACT_john_smith_001', 'CONTACT_john_smith_002')
"
```

**Prevention**: Adjust fuzzywuzzy matching threshold in `contact_service.py`

---

### Relationship Score Incorrect

**Symptom**: VIP contacts show low relationship strength

**Formula**: `interaction_count * 10 - days_since_last_contact`

**Diagnosis**:
```bash
# Check interaction tracking
grep "contact_interaction" Logs/audit_log.jsonl | grep "john@example.com"
```

**Solution**: Ensure all interactions (email, meetings, calls) are logged to audit log.

---

## US8: Financial Tracking

### OCR Accuracy Low (<75%)

**Symptom**: Expenses created with wrong amounts/vendors

**Solutions**:

1. **Enable Vision API Fallback**:
```bash
# In .env
VISION_API_ENABLED=true
GOOGLE_APPLICATION_CREDENTIALS=./google_vision_credentials.json
OCR_VISION_THRESHOLD=0.75
```

2. **Improve Receipt Quality**:
   - Use PDF receipts instead of photos
   - Ensure good lighting and focus
   - Avoid crumpled or faded receipts

3. **Manual Review**: Check flagged expenses in `/Expenses/`

---

### Budget Alerts Not Sent

**Symptom**: Spending exceeded 80% but no alert in `/Needs_Action/`

**Diagnosis**:
```bash
# Check budget thresholds
uv run python -c "
from src.services.budget_service import BudgetService
bs = BudgetService('$VAULT_PATH')
report = bs.get_budget_report('2026-03')
print(report)
"
```

**Solutions**:
- Verify `alerts_enabled: true` in budget JSON
- Check `alert_sent: false` (alerts only sent once)
- Reset alert: Edit budget JSON, set `alert_sent: false`

---

### Receipt Not Detected

**Symptom**: Receipt email arrived but no expense created

**Diagnosis**:
```bash
# Check Gmail watcher logs
pm2 logs gmail-watcher | grep -i receipt

# Test receipt detection
uv run python -c "
from src.watchers.gmail_watcher import GmailWatcher
gw = GmailWatcher('$VAULT_PATH', './credentials.json', './token.json')
email_data = {'subject': 'Receipt from Adobe', 'snippet': 'Thank you for your purchase'}
print(f'Is receipt: {gw._is_receipt_email(email_data)}')
"
```

**Solutions**:
- Ensure receipt keywords in subject/body: "receipt", "invoice", "bill"
- Check attachment is PDF or image format
- Manually process: Copy to `/Receipts/`, run `expense_service.py`

---

## Performance Issues

### Trust Evaluation Slow (>10ms)

**Target**: <10ms per evaluation

**Diagnosis**:
```bash
# Check performance metrics
grep "trust_eval_time_ms" Logs/audit_log.jsonl | tail -20
```

**Solutions**:
- Reduce number of trust rules (< 20 recommended)
- Simplify `contact_filter` regex patterns
- Enable performance monitoring in .env

---

### Calendar Sync Slow

**Symptom**: Calendar events take >500ms to query

**Solutions**:
- Enable local caching (already implemented)
- Reduce `max_results` in calendar queries
- Increase `CALENDAR_SYNC_INTERVAL`

---

### OCR Processing Slow (>30s)

**Solutions**:
- Use GPU acceleration for EasyOCR:
```python
reader = easyocr.Reader(['en'], gpu=True)
```
- Reduce image resolution before OCR
- Process receipts in background queue

---

## Data Recovery

### Encryption Key Lost

**⚠️ CRITICAL**: Cannot decrypt VIP contacts or sensitive receipts

**Recovery**:
See [Encryption Backup Guide](./encryption-backup.md)

If no backup:
- Encrypted data is permanently inaccessible
- Non-encrypted data is still usable
- Re-create affected entities manually

---

### Audit Log Corrupted

**Symptom**: `JSONDecodeError` when reading audit log

**Recovery**:
```bash
# Backup corrupted log
cp Logs/audit_log.jsonl Logs/audit_log.jsonl.backup

# Find last valid line
tail -100 Logs/audit_log.jsonl | python -c "
import sys, json
for i, line in enumerate(sys.stdin):
    try:
        json.loads(line)
    except:
        print(f'Error at line {i+1}')
"

# Remove corrupted lines
head -n <valid_line_count> Logs/audit_log.jsonl.backup > Logs/audit_log.jsonl
```

---

### Budget File Missing

**Symptom**: `FileNotFoundError: Budgets/2026-03.json`

**Recovery**:
```bash
# Initialize default budgets
uv run python -c "
from src.services.budget_service import BudgetService
bs = BudgetService('$VAULT_PATH')
bs.initialize_month_budgets('2026-03')
"
```

---

## Getting Help

**Debug Checklist**:
1. Check PM2 logs: `pm2 logs <process-name>`
2. Check audit log: `tail -f Logs/audit_log.jsonl`
3. Verify .env configuration
4. Test individual components
5. Review recent git commits

**Common Log Locations**:
- PM2 logs: `~/.pm2/logs/`
- Audit log: `$VAULT_PATH/Logs/audit_log.jsonl`
- Error logs: `$VAULT_PATH/Logs/error_log.jsonl`

**Resources**:
- Setup Guide: `docs/gold-tier-setup.md`
- API Documentation: `specs/003-gold-tier-upgrade/contracts/`
- Test Scenarios: `specs/003-gold-tier-upgrade/quickstart.md`

---

**Version**: Gold Tier 1.0.0
**Last Updated**: 2026-03-02
