# Trust Evaluator - Trust Framework Management

**Agent Skill for Gold Tier US1: Autonomous Workflows & Trust Levels**

## Purpose

Manage trust rules that define which actions can be auto-approved without manual HITL review. Trust rules reduce approval friction by allowing the AI Employee to execute trusted actions autonomously while maintaining full audit trails.

## Capabilities

1. **List Trust Rules**: View all configured trust rules with effectiveness scores
2. **Create Trust Rule**: Add new auto-approval rules for specific action types
3. **Enable/Disable Rules**: Toggle rules on/off
4. **Update Effectiveness**: Adjust rule effectiveness based on user feedback
5. **View Rule Details**: See detailed information about a specific rule
6. **Remove Rules**: Delete rules that are no longer needed
7. **View Summary**: Get overview statistics about trust framework performance

## Trust Levels

- **Level 0**: Always require manual approval (most conservative)
- **Level 1**: Auto-approve and execute immediately
- **Level 2**: Auto-approve with notification sent to user
- **Level 3**: Silent auto-approve (no notification, highest automation)

## Action Types

Trust rules can be configured for these action types:
- `email_send`: Email sending
- `social_post`: Social media posts
- `calendar_create`: Calendar event creation
- `expense_record`: Expense tracking
- `document_generate`: Document generation
- `whatsapp_send`: WhatsApp messages
- `task_complete`: Task completion

## Common Use Cases

### 1. Auto-Approve Email Replies to Team

```yaml
rule_id: RULE_email_team
rule_name: "Email Replies to Team"
action_type: email_send
trust_level: 1
contact_filter: ["@mycompany.com"]
```

**Effect**: All emails to @mycompany.com addresses auto-approved.

### 2. Small Expense Auto-Approval

```yaml
rule_id: RULE_small_expenses
rule_name: "Small Expenses Under $50"
action_type: expense_record
trust_level: 1
max_value: 50.00
```

**Effect**: Expenses under $50 auto-approved without review.

### 3. Routine Calendar Events During Business Hours

```yaml
rule_id: RULE_routine_calendar
rule_name: "Routine Calendar Events"
action_type: calendar_create
trust_level: 2
time_pattern: "weekdays 9am-5pm"
```

**Effect**: Calendar events during work hours auto-approved with notification.

## Effectiveness Tracking

Each trust rule tracks its effectiveness based on user feedback:
- **effectiveness_score**: 0.0-1.0 (1.0 = always correct, 0.0 = never correct)
- **usage_count**: Number of times rule has auto-approved actions
- **Auto-disable**: Rules automatically disabled if effectiveness drops below 0.80

**Feedback Loop**:
1. Rule auto-approves action
2. User reviews action in audit log
3. User provides feedback (thumbs up/down)
4. Effectiveness score updates
5. Rule auto-disables if score < 0.80

## Safety Features

- **Conservative Defaults**: New rules start disabled (must explicitly enable)
- **Auto-Disable**: Low-performing rules (< 80% effectiveness) auto-disable
- **Full Audit Trail**: All auto-approved actions logged with trust_rule_id
- **User Override**: Users can always review and revert auto-approved actions
- **Manual Control**: Users can enable/disable any rule at any time

## Example Workflow

**User**: "I want to auto-approve emails to my team members"

**Claude Code**:
1. Creates trust rule with contact_filter for team domain
2. Sets rule to disabled by default
3. Asks user to test with a few emails
4. User enables rule after testing
5. System auto-approves matching emails
6. Tracks effectiveness based on user feedback

## Commands

### List All Trust Rules

```
List all trust rules with their effectiveness scores
```

**Output**: Table of all rules with status, usage count, and effectiveness.

### Create New Trust Rule

```
Create a trust rule to auto-approve emails to @example.com
```

**Process**:
1. Determines action type (email_send)
2. Sets contact_filter to ["@example.com"]
3. Generates rule_id (RULE_email_example)
4. Sets trust_level to 1 (auto-approve)
5. Creates rule in Company_Handbook.md
6. Sets enabled=false for user testing

### Enable a Trust Rule

```
Enable trust rule RULE_email_team
```

**Effect**: Rule becomes active and will start auto-approving matching actions.

### View Trust Framework Summary

```
Show me trust framework performance summary
```

**Output**:
- Total rules: enabled vs disabled
- Average effectiveness score
- Total auto-approvals
- Rules by action type
- Auto-disabled rules (needing attention)

### Update Rule Effectiveness (Internal)

```python
# Called automatically when user provides feedback
trust_evaluator.update_rule_effectiveness(
    rule_id="RULE_email_team",
    user_would_approve=True  # or False
)
```

## Technical Details

**Storage**: Trust rules stored in `Company_Handbook.md` YAML frontmatter under `trust_rules:` section.

**Service**: `src/services/trust_evaluator.py` - TrustEvaluator class

**Model**: `src/models/trust_rule.py` - TrustRule dataclass

**Integration**: Executor checks trust rules before executing plans in `/Approved/` folder.

**Workflow**:
1. Plan file created in `/Approved/`
2. Executor reads plan frontmatter
3. TrustEvaluator.evaluate(plan) checks trust rules
4. If trusted: Execute immediately (log trust_rule_id)
5. If not trusted: Move to `/Pending_Approval/` for manual review

## Best Practices

1. **Start Conservative**: Begin with trust_level=0 or disabled rules
2. **Test First**: Enable rule, test with a few examples, review audit logs
3. **Monitor Effectiveness**: Check effectiveness scores weekly
4. **Adjust Filters**: Narrow contact_filter if getting false positives
5. **Use Time Patterns**: Restrict to business hours for safety
6. **Review Auto-Disabled**: Investigate rules that auto-disable (effectiveness < 80%)
7. **Regular Audits**: Monthly review of all auto-approved actions

## Configuration Location

**File**: `Company_Handbook.md`

**Section**: YAML frontmatter, `trust_rules:` array

**Edit**: Users can manually edit rules in Company Handbook or use this skill via Claude Code.

**Reload**: TrustEvaluator automatically reloads after changes.

## Audit Trail

All auto-approved actions logged to `/Logs/YYYY-MM-DD.json` with:
- `approval_status: approved`
- `approved_by: auto` or `approved_by: trust_rule`
- `parameters.trust_rule_id: RULE_xxx`

**Query Auto-Approved Actions**:
```python
from src.services.audit_service import AuditService

audit = AuditService(vault_path="/path/to/vault")
auto_approved = audit.query_by_parameter("trust_rule_id", "RULE_email_team", days=30)
```

## Related Documentation

- Trust Framework Spec: `/specs/003-gold-tier-upgrade/spec.md` (User Story 1)
- TrustRule JSON Schema: `/specs/003-gold-tier-upgrade/contracts/trust-rule-schema.json`
- Data Model: `/specs/003-gold-tier-upgrade/data-model.md` (Section 1)
- Analytics: Effectiveness tracked in weekly insights (`/Insights/`)

---

**Gold Tier Feature** | Trust Framework Auto-Approval | User Story 1
