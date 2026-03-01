# Analytics & Insights Agent Skill

**Skill ID:** `analytics-insights`
**Category:** Gold Tier US4 - Advanced Analytics & Insights
**Trust Level:** 2-3 (auto-approve weekly insights, review on-demand)

## Overview

The Analytics & Insights skill generates weekly productivity insights from audit log data using pandas DataFrames. It calculates metrics, detects patterns and anomalies, analyzes trust rule effectiveness, and provides actionable recommendations.

## Capabilities

1. **Metrics Calculation**
   - Total actions and actions per day
   - Email volume (sent/received)
   - Meeting statistics (total, hours, average duration)
   - Response times (average and median)
   - Trust rule effectiveness tracking

2. **Pattern Detection**
   - Day-of-week activity clustering
   - Time-of-day patterns
   - Recurring action identification
   - Trend analysis

3. **Anomaly Detection**
   - 3-sigma anomaly detection for unusual activity
   - Low trust effectiveness alerts
   - Slow response time detection

4. **Trust Rule Analysis**
   - Effectiveness scoring by rule
   - High-performing rule identification
   - Low-performing rule warnings

5. **Recommendation Generation**
   - Trust rule optimization suggestions
   - Productivity improvements
   - Scheduling optimizations
   - Priority-based actionable items

## Usage

### Basic Syntax

```
Generate weekly insights
Analyze the past [time_period]
Show analytics for [date_range]
```

### Examples

**Weekly Insights (Automatic):**
```
# Automatically generated every Friday at 5 PM
# Output: /Insights/YYYY-MM-DD.json
```

**On-Demand Analysis:**
```
Generate weekly insights for last week
Analyze productivity for March 2026
Show analytics for the past 30 days
```

**View Existing Insights:**
```
Show me the latest weekly insights
What were the recommendations from last week?
Display high-priority insights
```

## Trust Framework Integration

### Auto-Approval Rules

Analytics generation can be auto-approved based on:
- Time period (recent vs. historical)
- Insight type (weekly vs. custom analysis)
- Data sensitivity (aggregate vs. individual)

### Example Trust Rules

**Auto-approve weekly insights:**
```yaml
rule_id: RULE_auto_weekly_insights
action_type: analytics_generated
trust_level: 3  # Silent auto-approval
content_pattern: ".*weekly.*insight.*"
enabled: true
```

**Review custom analytics:**
```yaml
rule_id: RULE_review_custom_analytics
action_type: analytics_generated
trust_level: 1  # Require approval
content_pattern: ".*custom.*"
enabled: true
```

## Command Reference

### Generate Weekly Insight

**Command:**
```
Generate weekly insights
```

**Parameters:**
- `week_start` (optional): Start date (default: last Monday)

**Output:**
- JSON file saved to: `/Insights/YYYY-MM-DD.json`
- High-priority alerts in: `/Needs_Action/INSIGHT_*.md`

**Example:**
```
Generate weekly insights for March 1, 2026
```

**Output Structure:**
```json
{
  "insight_id": "INSIGHT_2026_03_01",
  "week_start": "2026-02-24T00:00:00Z",
  "week_end": "2026-03-01T23:59:59Z",
  "metrics": {
    "total_actions": 147,
    "actions_per_day": 21,
    "email_volume": {"sent": 32, "received": 48},
    "meeting_stats": {...},
    "response_times": {...},
    "trust_effectiveness": {...}
  },
  "patterns": [...],
  "recommendations": [...],
  "anomalies": [...]
}
```

### View High-Priority Recommendations

**Command:**
```
Show high-priority recommendations
```

**Output:**
- List of high-priority recommendations from latest insight
- Each with rationale and action items

### Analyze Trust Rule Effectiveness

**Command:**
```
Analyze trust rule effectiveness
```

**Output:**
- High-performing rules (effectiveness >= 0.95)
- Low-performing rules (effectiveness < 0.75)
- Suggestions for trust level adjustments

## Metrics Explained

### Total Actions
Count of all logged actions in audit logs during the period.

### Actions Per Day
Average number of actions per day (total_actions / unique_days).

### Email Volume
- **Sent**: Count of `email_send` actions
- **Received**: Count of `email_receive` actions

### Meeting Stats
- **Total Meetings**: Count of meeting/calendar actions
- **Total Hours**: Sum of meeting durations in hours
- **Avg Duration**: Average meeting length in minutes

### Response Times
- **Avg Seconds**: Mean execution time for actions
- **Median Seconds**: Median execution time (50th percentile)

### Trust Effectiveness
- **Auto Approved Count**: Actions auto-approved by trust rules
- **Manual Review Count**: Actions requiring human approval
- **Avg Effectiveness Score**: Mean effectiveness across all rules (0.0-1.0)

## Pattern Types

### Day of Week
Identifies peak activity days (e.g., "Peak activity on Tuesday and Thursday").

**Use case:** Schedule important meetings on peak days, reserve low-activity days for deep work.

### Time of Day
Identifies peak hours (e.g., "Peak activity during afternoon (12pm-6pm)").

**Use case:** Schedule focused work during low-activity hours.

### Recurring Actions
Identifies frequently repeated actions (e.g., "Recurring email_send actions (32 times)").

**Use case:** Create automation workflows for common tasks.

### Anomalies
Detects unusual behavior using 3-sigma detection.

**Types:**
- **high_activity**: Unusually high action volume
- **low_trust_effectiveness**: Trust rules underperforming
- **slow_responses**: Response times exceeding expectations

## Recommendations

Recommendations are categorized and prioritized:

**Priority Levels:**
- **High**: Immediate action recommended (e.g., low trust effectiveness)
- **Medium**: Should address soon (e.g., optimize scheduling)
- **Low**: Nice to have (e.g., batching optimizations)

**Categories:**
- **productivity**: Task efficiency improvements
- **trust_rules**: Trust framework adjustments
- **scheduling**: Calendar optimization
- **budget**: Spending patterns
- **relationships**: CRM suggestions

### Example Recommendations

**Trust Rule Upgrade:**
```
Priority: High
Category: trust_rules
Recommendation: Consider increasing trust level for RULE_email_team
Rationale: 100% effectiveness over 50 actions with no rejections
Action Items:
  - Review RULE_email_team configuration
  - Consider upgrading from level 1 to level 2
```

**Productivity Optimization:**
```
Priority: Medium
Category: productivity
Recommendation: Consider batching similar tasks for efficiency
Rationale: High action volume (52 actions/day) may benefit from task batching
Action Items:
  - Identify repetitive action patterns
  - Create automation workflows for common tasks
```

## Configuration

### Service Initialization

```python
from src.services.analytics_service import AnalyticsService

service = AnalyticsService(vault_path="/path/to/vault")
```

### Generate Insights

```python
from datetime import datetime, timedelta

# Generate for specific week
week_start = datetime(2026, 3, 1)
insight, file_path = service.generate_weekly_insight(week_start=week_start)

print(f"Generated: {file_path}")
print(f"Recommendations: {len(insight.recommendations)}")
```

### Access Metrics

```python
# Load existing insight
with open("/vault/Insights/2026-03-01.json") as f:
    data = json.load(f)

print(f"Total actions: {data['metrics']['total_actions']}")
print(f"Patterns detected: {len(data['patterns'])}")
```

## Performance

- **DataFrame Loading:** <1 second for 1000 audit logs
- **Metrics Calculation:** <500ms for typical week
- **Pattern Detection:** <300ms with 7 days of data
- **Total Generation Time:** <2 seconds for complete weekly insight

## Scheduled Execution

### Weekly Analytics Engine

The analytics engine runs automatically:
- **Schedule:** Every Friday at 5:00 PM
- **Output:** `/Insights/YYYY-MM-DD.json`
- **Alerts:** High-priority recommendations → `/Needs_Action/`

### Manual Triggering

```python
from src.watchers.analytics_engine import AnalyticsEngine

engine = AnalyticsEngine(vault_path="/path/to/vault")
file_path = engine.generate_now()
print(f"Generated: {file_path}")
```

## Integration Examples

### Dashboard Integration

```python
# Display latest insights on dashboard
import json
from pathlib import Path

insights_dir = Path("/vault/Insights")
latest = sorted(insights_dir.glob("*.json"))[-1]

with open(latest) as f:
    insight = json.load(f)

print(f"Week: {insight['week_start']} to {insight['week_end']}")
print(f"Total Actions: {insight['metrics']['total_actions']}")
print(f"High Priority Recs: {len([r for r in insight['recommendations'] if r['priority'] == 'high'])}")
```

### Email Summary

```python
# Send weekly summary email
from src.services.analytics_service import AnalyticsService

service = AnalyticsService(vault_path="/vault")
insight, _ = service.generate_weekly_insight()

# Build email content
summary = f"""
Weekly Productivity Summary

Total Actions: {insight.metrics['total_actions']}
Success Rate: {insight.metrics['trust_effectiveness']['avg_effectiveness_score'] * 100:.1f}%

High Priority Recommendations: {len(insight.get_high_priority_recommendations())}
"""

# Send email (using email service)
# email_service.send(to="user@example.com", subject="Weekly Insights", body=summary)
```

## Troubleshooting

### No Insights Generated

1. **Check audit logs exist:**
   ```bash
   ls -la /vault/Logs/
   ```

2. **Verify analytics engine is running:**
   ```python
   engine = AnalyticsEngine(vault_path="/vault")
   engine.start()
   ```

3. **Check logs for errors:**
   ```bash
   grep "AnalyticsEngine" /vault/Logs/*.json
   ```

### Low Confidence Patterns

1. **Ensure sufficient data:**
   - Need at least 7 days of audit logs
   - Minimum 50 actions for reliable patterns

2. **Check data quality:**
   - Verify timestamps are correct
   - Ensure action types are consistent

### Missing Recommendations

1. **Check thresholds:**
   - Trust effectiveness < 0.95 for upgrade suggestions
   - Trust effectiveness < 0.75 for warnings
   - Actions per day > 50 for batching suggestions

2. **Review pattern detection:**
   - Patterns require 0.75+ confidence
   - Day-of-week needs > 3 days of data

## Best Practices

1. **Regular Review**
   - Check insights every Friday after 5 PM
   - Action high-priority recommendations within 24 hours
   - Monitor trust rule effectiveness monthly

2. **Data Hygiene**
   - Maintain 90 days of audit logs minimum
   - Archive old insights (keep latest 12 weeks)
   - Clean up actioned recommendations from /Needs_Action/

3. **Trust Rule Tuning**
   - Upgrade high-performing rules (0.95+ effectiveness)
   - Review low-performing rules (< 0.75)
   - Test rule changes with small batches first

4. **Metric Tracking**
   - Track actions_per_day trends over time
   - Monitor response time degradation
   - Watch for anomaly frequency increases

## Related Skills

- **trust-evaluator** - Trust framework management
- **document-generator** - Weekly status reports with insights
- **vault-manager** - Obsidian vault analytics file management

## Support

For issues or feature requests:
1. Check analytics engine logs
2. Review pandas DataFrame processing
3. Verify audit log data quality
4. Consult Company_Handbook.md for analytics configuration

---

*This skill is part of the Gold Tier autonomous capabilities. Version 1.0.0*
