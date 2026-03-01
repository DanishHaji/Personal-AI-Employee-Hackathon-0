# Document Generator Agent Skill

**Skill ID:** `document-generator`
**Category:** Gold Tier US3 - Document Generation & Editing
**Trust Level:** 1-3 (configurable per document type)

## Overview

The Document Generator skill enables autonomous document creation using Jinja2 templates and audit log data. It can generate weekly status reports, meeting notes, monthly summaries, and custom documents with automatic version tracking.

## Capabilities

1. **Template-Based Generation**
   - Weekly status reports from audit logs
   - Meeting notes with agenda and attendees
   - Monthly summary reports with metrics
   - Custom documents from templates

2. **Automatic Context Building**
   - Extract activities from audit logs
   - Calculate performance metrics
   - Identify decision points
   - Aggregate data by time period

3. **Version Management**
   - Track document versions
   - Preserve history
   - Create new versions with full lineage

4. **Vault Integration**
   - Automatic folder organization
   - YAML frontmatter with metadata
   - Tag-based categorization

## Usage

### Basic Syntax

```
Generate a [document_type] for [time_period]
```

### Examples

**Weekly Status Report:**
```
Generate a weekly status report for last week
Generate a weekly status report for March 1-7, 2026
```

**Meeting Notes:**
```
Generate meeting notes for "Q2 Planning Meeting" on March 15, 2026
Create meeting notes with attendees: john@example.com, jane@example.com
```

**Monthly Summary:**
```
Generate a monthly summary for February 2026
Create a monthly summary report for last month
```

**Custom Documents:**
```
Generate a proposal document using proposal-template.md.j2
Create an analysis document from audit logs for the past 30 days
```

## Trust Framework Integration

### Auto-Approval Rules

Document generation can be auto-approved based on:
- Document type (status reports vs. external proposals)
- Time period (recent vs. historical data)
- Template used (trusted vs. custom templates)
- Content sensitivity (public vs. confidential)

### Example Trust Rules

**Auto-approve weekly status reports:**
```yaml
rule_id: RULE_auto_weekly_status
action_type: document_generation
trust_level: 3
effectiveness_score: 0.95
content_pattern: ".*weekly.*status.*"
auto_approve_conditions:
  - document_type: status_report
  - template: weekly-status.md.j2
```

**Require approval for external documents:**
```yaml
rule_id: RULE_review_external_docs
action_type: document_generation
trust_level: 1
content_pattern: ".*proposal.*|.*memo.*"
auto_approve_conditions: []
```

## Command Reference

### Generate Weekly Status Report

**Command:**
```
Generate weekly status report
```

**Parameters:**
- `week_start` (optional): Start date (default: last Monday)
- `encrypt` (optional): Encrypt sensitive fields (default: false)

**Output:**
- Document saved to: `vault/Documents/Status Reports/Weekly_Status_YYYY_MM_DD.md`
- Tags: `#weekly #status #YYYY-QN`

**Example:**
```
Generate weekly status report for March 1, 2026
```

### Generate Meeting Notes

**Command:**
```
Generate meeting notes for "[title]"
```

**Parameters:**
- `title` (required): Meeting title
- `date` (required): Meeting date
- `attendees` (required): List of attendees
- `agenda` (optional): Meeting agenda

**Output:**
- Document saved to: `vault/Documents/Meetings/Meeting_Title_YYYY_MM_DD.md`
- Tags: `#meeting #YYYY-MM`

**Example:**
```
Generate meeting notes for "Q2 Planning Meeting" on March 15, 2026
Attendees: john@example.com, jane@example.com
Agenda: Discuss Q2 objectives and key results
```

### Generate Monthly Summary

**Command:**
```
Generate monthly summary
```

**Parameters:**
- `month` (optional): Month to summarize (default: last month)
- `encrypt` (optional): Encrypt sensitive fields (default: false)

**Output:**
- Document saved to: `vault/Documents/Summaries/Monthly_Summary_YYYY_MM.md`
- Tags: `#monthly #summary #YYYY-QN`

**Example:**
```
Generate monthly summary for February 2026
```

### Create New Document Version

**Command:**
```
Create new version of document [document_id]
```

**Parameters:**
- `document_id` (required): Existing document ID
- `content` (required): New content

**Output:**
- New document with incremented version
- Previous version preserved in history

**Example:**
```
Create new version of document DOC_weekly_status_2026_03_01
```

## Template Development

### Template Location

Templates are stored in:
- `.specify/templates/documents/`
- `templates/documents/`

### Template Format

Templates use Jinja2 syntax with YAML frontmatter support.

**Example Template:**
```jinja2
# {{ title }}

**Generated:** {{ generated_at | datetime_format("%Y-%m-%d %H:%M UTC") }}

## Summary

{{ summary }}

## Details

{% for item in items %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
```

### Available Filters

- `datetime_format(format_str)` - Format datetime objects
- `date_format(format_str)` - Format dates only
- `duration(seconds)` - Format duration (e.g., "2.5h", "30.0m")

### Context Variables

Templates receive the following context:

**All Templates:**
- `generated_at`: Current timestamp
- `document_type`: Type of document

**Status Reports:**
- `start_date`: Report start date
- `end_date`: Report end date
- `metrics`: Performance metrics dict
- `activities`: List of activity dicts
- `decisions`: List of decision dicts

**Meeting Notes:**
- `meeting_title`: Meeting title
- `meeting_date`: Meeting date/time
- `attendees`: List of attendee names/emails
- `agenda`: Meeting agenda text

## Configuration

### Service Initialization

```python
from src.services.document_service import DocumentService

service = DocumentService(
    vault_path="/path/to/vault",
    template_dir=".specify/templates/documents"
)
```

### Generate Document

```python
from src.services.document_service import DocumentGenerationParams
from datetime import datetime, timedelta

# Generate weekly status
doc, file_path = service.generate_weekly_status(
    week_start=datetime(2026, 3, 1),
    encrypt=False
)

# Generate meeting notes
doc, file_path = service.generate_meeting_notes(
    meeting_title="Q2 Planning Meeting",
    meeting_date=datetime(2026, 3, 15, 14, 0),
    attendees=["john@example.com", "jane@example.com"],
    agenda="Discuss Q2 objectives"
)
```

## Performance

- **Template Rendering:** <100ms for typical documents
- **Context Building:** <500ms for 30-day audit log analysis
- **File Write:** <50ms for typical document size
- **Total Generation Time:** <1 second for most documents

## Security

### Data Privacy

- Audit log data stays local (no cloud uploads)
- Sensitive fields can be encrypted using BaseModel encryption
- Documents inherit encryption status from source data

### Access Control

- Documents stored in user's Obsidian vault
- File permissions follow OS security model
- No external API calls for document generation

## Error Handling

### Template Not Found

```
Error: Template 'custom-template.md.j2' not found
Solution: Create template in .specify/templates/documents/
```

### Missing Context Data

```
Error: No audit logs found for date range
Solution: Verify audit_service is logging activities
```

### Invalid Document Type

```
Error: document_type must be one of [meeting_notes, status_report, ...]
Solution: Use a valid document_type or use "other"
```

## Troubleshooting

### Document Not Generated

1. **Check template exists:**
   ```bash
   ls -la .specify/templates/documents/
   ```

2. **Verify vault path:**
   ```python
   from pathlib import Path
   print(Path("/path/to/vault").exists())
   ```

3. **Check audit logs:**
   ```python
   from src.services.audit_service import AuditService
   service = AuditService()
   logs = service.query_logs(start_time=..., end_time=...)
   print(f"Found {len(logs)} logs")
   ```

### Template Rendering Errors

1. **Check Jinja2 syntax:**
   - Ensure all `{{ }}` and `{% %}` tags are balanced
   - Verify filter names are correct

2. **Verify context data:**
   ```python
   context = service.build_context(document_type, params)
   print(context.keys())
   ```

### Version History Not Working

1. **Check document has version field:**
   ```python
   print(doc.version)  # Should be >= 1
   ```

2. **Verify previous_versions is a list:**
   ```python
   print(doc.previous_versions)  # Should be a list
   ```

## Best Practices

1. **Template Organization**
   - Use descriptive template names (e.g., `weekly-status.md.j2`)
   - Group related templates in subdirectories
   - Version control templates with git

2. **Context Building**
   - Keep context data focused and relevant
   - Filter audit logs by action type when possible
   - Limit activity lists to recent/important items

3. **Version Management**
   - Create new versions for significant changes
   - Preserve original document for reference
   - Use semantic versioning in document IDs

4. **Trust Rules**
   - Start with conservative rules (low trust levels)
   - Increase trust_level as effectiveness improves
   - Monitor effectiveness_score regularly

## Integration Examples

### Scheduled Weekly Reports

```python
from src.watchers.document_watcher import DocumentWatcher

watcher = DocumentWatcher(
    vault_path="/path/to/vault",
    schedule_weekly=True,
    schedule_monthly=True
)
watcher.start()
```

### Manual Document Generation

```python
from src.services.document_service import DocumentService
from datetime import datetime

service = DocumentService(vault_path="/path/to/vault")

# Generate weekly status
doc, path = service.generate_weekly_status()
print(f"Generated: {path}")

# Generate meeting notes
doc, path = service.generate_meeting_notes(
    meeting_title="Sprint Planning",
    meeting_date=datetime.now(),
    attendees=["team@example.com"]
)
print(f"Generated: {path}")
```

### Custom Template Usage

```python
from src.services.document_service import DocumentGenerationParams

# Build custom context
params = DocumentGenerationParams(
    start_date=datetime(2026, 3, 1),
    end_date=datetime(2026, 3, 31),
    include_metrics=True,
    custom_sections={"budget": "$10,000", "roi": "150%"}
)
context = service.build_context("analysis", params)

# Render custom template
doc = service.render_document(
    template_name="custom-analysis.md.j2",
    context=context,
    document_id="DOC_custom_analysis_2026_03",
    title="Q1 Analysis Report",
    document_type="analysis",
    folder="Documents/Analysis",
    tags=["analysis", "Q1", "2026"]
)

# Save document
path = service.save_document(doc)
```

## Related Skills

- **trust-evaluator** - Trust framework management
- **calendar-manager** - Calendar integration for meeting notes
- **vault-manager** - Obsidian vault file management

## Support

For issues or feature requests:
1. Check error logs in audit system
2. Review template syntax with Jinja2 documentation
3. Verify vault permissions and file paths
4. Consult Company_Handbook.md for trust rule examples

---

*This skill is part of the Gold Tier autonomous capabilities. Version 1.0.0*
