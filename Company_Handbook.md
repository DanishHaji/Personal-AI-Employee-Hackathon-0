---
# Company Handbook - Personal AI Employee Configuration
# Gold Tier Autonomous AI System

# Trust Rules - Auto-Approval Configuration
# Configure which actions can be auto-approved without manual review
trust_rules: []
  # Example trust rule (uncomment and customize):
  # - rule_id: RULE_email_known_contacts
  #   rule_name: "Email Replies to Known Contacts"
  #   action_type: email_send
  #   trust_level: 1  # 0=Always approve, 1=Auto-approve, 2=Auto+notify, 3=Silent auto
  #   contact_filter: ["@example.com", "Team"]  # Emails or group names
  #   content_pattern: null  # Optional regex pattern for content matching
  #   time_pattern: null  # Optional time-based filter (e.g., "weekdays 9am-5pm")
  #   max_value: null  # Optional maximum financial amount
  #   created_at: "2026-03-01T00:00:00Z"
  #   created_by: user
  #   last_used: null
  #   usage_count: 0
  #   effectiveness_score: 1.0
  #   enabled: true

# Scheduled Tasks - Automated Recurring Actions
scheduled_tasks: []
  # Example scheduled task:
  # - task_id: TASK_weekly_status
  #   task_name: "Weekly Status Report"
  #   schedule: "Friday 5pm"  # Natural language schedule
  #   action_type: document_generate
  #   parameters:
  #     template: weekly-status.md.j2
  #     folder: Documents/Status Reports
  #   enabled: true
  #   last_run: null
  #   next_run: null

# Calendar Preferences - Meeting Scheduling Rules
calendar_preferences:
  work_hours_start: "09:00"
  work_hours_end: "17:00"
  no_meeting_blocks: []
    # - day: Monday
    #   start: "12:00"
    #   end: "13:00"
    #   reason: "Lunch break"
  minimum_gap_minutes: 15  # Minimum gap between meetings
  default_meeting_duration_minutes: 30
  buffer_before_meeting_minutes: 5  # Preparation time

# Budget Allocations - Monthly Expense Budgets
budgets:
  default_currency: USD
  categories:
    software: 500.00
    travel: 1000.00
    office: 200.00
    marketing: 300.00
    meals: 400.00
    transportation: 150.00
    utilities: 100.00
    other: 250.00
  alert_threshold: 0.80  # Alert when 80% of budget used
  alerts_enabled: true

# Proactive Suggestions - AI-Initiated Task Categories
proactive_suggestions:
  enabled: true
  max_per_category_per_day: 3  # Limit suggestion volume
  categories:
    follow_up_reminders:
      enabled: true
      threshold_days: 3  # Suggest follow-up if no reply in 3 days
    incomplete_task_chains:
      enabled: true
    relationship_maintenance:
      enabled: true
      vip_stale_days: 30  # Suggest check-in if no contact in 30 days
    recurring_pattern_detection:
      enabled: false  # Phase 2 feature

# Contact Management - CRM Settings
crm_settings:
  auto_create_contacts: true  # Auto-create contact profiles from interactions
  vip_relationship_threshold: 200  # Relationship strength score for auto-VIP
  encrypt_vip_contacts: true  # Encrypt VIP contact data
  duplicate_detection_threshold: 0.85  # Fuzzy match threshold (0.0-1.0)

# Analytics - Insights & Reporting
analytics:
  weekly_insights_enabled: true
  weekly_insights_day: Friday
  weekly_insights_time: "17:00"
  retention_days: 90  # Keep 90 days of audit logs for analysis
  metrics_to_track:
    - emails_sent
    - emails_received
    - meetings_attended
    - tasks_completed
    - response_time
    - trust_effectiveness
    - budget_utilization

# Security & Privacy
security:
  encrypt_sensitive_data: true  # Encrypt CRM, financial, meeting transcripts
  encryption_key_id: "ai-employee-vault-key"  # OS keychain identifier
  require_recording_consent: true  # Meeting recording consent required
  data_retention_days: 365  # General data retention policy
  export_format: json  # Format for GDPR data export

# System Configuration
system:
  version: "0.4.0"  # Platinum Tier
  tier: platinum
  instance: local  # "cloud" or "local" - identifies which work zone this instance operates in
  timezone: "America/Los_Angeles"
  date_format: "YYYY-MM-DD"
  time_format: "24h"
  log_level: INFO

# Platinum Tier - Work Zone Specialization
# Defines capabilities and restrictions for Cloud and Local work zones
work_zones:
  cloud:
    enabled: true
    capabilities:
      - email_triage          # Detect and categorize incoming emails
      - draft_responses       # Draft email replies (not send)
      - schedule_monitoring   # Monitor calendar for conflicts
      - document_analysis     # Analyze documents and generate summaries
      - social_media_drafts   # Draft social media posts
    restrictions:
      - no_whatsapp_access    # Cannot access WhatsApp sessions
      - no_banking_credentials  # Cannot access banking credentials
      - no_final_execution    # Cannot execute final actions (send emails, make payments)

  local:
    enabled: true
    capabilities:
      - approve_cloud_drafts  # Review and approve Cloud-drafted content
      - whatsapp_send         # Send WhatsApp messages
      - banking_transactions  # Execute banking transactions
      - email_send            # Send emails (after approval)
      - final_execution       # Execute all final actions
    exclusive_secrets:
      - whatsapp_session      # WhatsApp Web session data
      - banking_credentials   # Banking API credentials
      - oauth_tokens_sensitive  # Sensitive OAuth tokens

# Platinum Tier - Routing Rules
# Determines which work zone handles each action type
routing_rules:
  - pattern: "EMAIL_*"
    action: "reply_draft"
    zone: "cloud"             # Cloud drafts email replies
    requires_approval: true   # Local must approve before sending

  - pattern: "EMAIL_*"
    action: "send"
    zone: "local"             # Only Local can send emails
    requires_approval: false  # Already approved by moving to /Approved/

  - pattern: "WHATSAPP_*"
    action: "send_message"
    zone: "local"             # WhatsApp only on Local (secrets)
    requires_approval: false

  - pattern: "SOCIAL_*"
    action: "draft_post"
    zone: "cloud"             # Cloud drafts social media posts
    requires_approval: true

  - pattern: "SOCIAL_*"
    action: "publish"
    zone: "local"             # Local publishes after approval
    requires_approval: false

  - pattern: "DOCUMENT_*"
    action: "generate"
    zone: "cloud"             # Cloud can generate documents
    requires_approval: true

  - pattern: "CALENDAR_*"
    action: "schedule"
    zone: "cloud"             # Cloud can schedule meetings
    requires_approval: true

  - pattern: "PAYMENT_*"
    action: "execute"
    zone: "local"             # All payments Local-only (secrets)
    requires_approval: true

  - pattern: "EXPENSE_*"
    action: "record"
    zone: "cloud"             # Cloud can record expenses
    requires_approval: false  # Auto-approved for recording only
---

# Company Handbook

Welcome to your Personal AI Employee system! This handbook configures how your AI Employee operates autonomously.

## Trust Framework

The trust framework allows you to configure which actions can be auto-approved without manual review. This reduces approval friction while maintaining full audit trails.

### Trust Levels

- **Level 0**: Always require manual approval
- **Level 1**: Auto-approve and execute immediately
- **Level 2**: Auto-approve with notification sent
- **Level 3**: Silent auto-approve (no notification)

### Creating Trust Rules

1. Edit the `trust_rules:` section in the frontmatter above
2. Add a new rule with appropriate filters
3. Test with a few examples before enabling widely
4. Monitor effectiveness score (should stay above 0.80)

### Example Trust Rules

**Email Replies to Team Members**:
```yaml
- rule_id: RULE_email_team
  rule_name: "Email Replies to Team"
  action_type: email_send
  trust_level: 1
  contact_filter: ["@mycompany.com"]
  enabled: true
```

**Expense Tracking Under $50**:
```yaml
- rule_id: RULE_small_expenses
  rule_name: "Small Expense Auto-Approval"
  action_type: expense_record
  trust_level: 1
  max_value: 50.00
  enabled: true
```

**Auto-Approve Weekly Status Reports**:
```yaml
- rule_id: RULE_auto_weekly_status
  rule_name: "Auto-Approve Weekly Status Reports"
  action_type: document_generation
  trust_level: 3  # Silent auto-approval
  content_pattern: ".*weekly.*status.*"
  enabled: true
```

**Require Review for External Proposals**:
```yaml
- rule_id: RULE_review_proposals
  rule_name: "Review External Proposals"
  action_type: document_generation
  trust_level: 0  # Always require approval
  content_pattern: ".*proposal.*|.*memo.*"
  enabled: true
```

## Scheduled Tasks

Configure recurring tasks that run automatically on a schedule.

**Weekly Status Reports**: Automatically generate weekly status reports every Monday at 9 AM.

**Monthly Summaries**: Generate monthly productivity and financial summaries on the 1st of each month at 10 AM.

## Document Generation

Your AI Employee automatically generates documents using Jinja2 templates and audit log data:

- **Weekly Status Reports**: Generated every Monday at 9 AM with activity summaries, metrics, and decision points
- **Monthly Summaries**: Generated on the 1st of each month with comprehensive analysis of activities and performance
- **Meeting Notes**: Generated on-demand with agenda, attendees, and action items templates
- **Custom Documents**: Create custom templates for proposals, memos, and analysis reports

### Document Features

- **Template-Based**: Uses Jinja2 templates from `.specify/templates/documents/`
- **Version Tracking**: All documents maintain complete version history
- **Automatic Context**: Pulls data from audit logs, calendar, and metrics
- **Vault Integration**: Saved to Obsidian vault with YAML frontmatter
- **Encryption**: Sensitive document fields can be encrypted

### Available Templates

- `weekly-status.md.j2` - Weekly activity and metrics summary
- `meeting-notes.md.j2` - Meeting notes with agenda and action items
- `monthly-summary.md.j2` - Monthly comprehensive analysis

### Trust Integration

Document generation respects trust rules:
- Weekly/monthly reports: Can be auto-approved (trust_level: 2-3)
- Meeting notes: Auto-approve for internal meetings (trust_level: 1-2)
- Proposals/memos: Require review (trust_level: 0-1)

View generated documents in: `/Documents/`

## Calendar Management

Your AI Employee can manage your Google Calendar autonomously:

- Schedule meetings based on availability
- Detect and resolve conflicts
- Send calendar invites
- Respect work hours and no-meeting blocks

Configure your preferences in the `calendar_preferences` section above.

## Budget Tracking

Expenses are automatically tracked against monthly budgets by category. You'll receive alerts when spending approaches 80% of any category budget.

View your budgets in: `/Budgets/YYYY-MM.json`

## Proactive Suggestions

Your AI Employee can proactively suggest actions based on patterns:

- **Follow-up Reminders**: Suggests follow-ups for unanswered emails
- **Incomplete Task Chains**: Detects missing steps (e.g., meeting scheduled but no agenda)
- **Relationship Maintenance**: Suggests check-ins for contacts you haven't engaged recently

Configure suggestion categories in the `proactive_suggestions` section.

## Contact Management (CRM)

All interactions (emails, meetings, WhatsApp) automatically create and update contact profiles.

- VIP contacts have enhanced tracking
- Contact data can be encrypted for privacy
- Duplicate detection prevents profile fragmentation

View contacts in: `/Contacts/`

## Analytics & Insights

Weekly insights are generated every Friday at 5 PM analyzing:

- Productivity patterns (email volume, meeting hours, task completion)
- Trust framework effectiveness
- Budget utilization
- Relationship health

View insights in: `/Insights/YYYY-MM-DD.json`

## Security & Privacy

- **Local-First**: All data stored in your vault (no cloud storage)
- **Encryption**: Sensitive data encrypted with OS keychain
- **Audit Trails**: Every action logged to `/Logs/`
- **GDPR Compliance**: Export or delete your data anytime

## Support

For questions or issues:

1. Check the `/docs/` folder for documentation
2. Review the specification: `/specs/003-gold-tier-upgrade/spec.md`
3. Check audit logs: `/Logs/YYYY-MM-DD.json`

---

**Last Updated**: 2026-03-01 | **Version**: 0.3.0 (Gold Tier)
