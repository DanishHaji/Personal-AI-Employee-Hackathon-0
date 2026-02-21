---
name: email-triage
description: Analyze email content and determine priority and appropriate response strategy
---

# Email Triage Skill

This skill provides email-specific analysis to help determine:
- Priority level (high/medium/low)
- Response urgency
- Suggested action steps
- Whether approval is needed

This is a helper skill used by vault-manager when processing Email entities.

## Usage

```
Use email-triage skill to analyze email from client@example.com with subject "Urgent invoice request"
```

Or with full context:

```
Analyze email:
From: client@example.com
Subject: Urgent invoice request
Content: Hi, can you send me the invoice for January? Need it ASAP for accounting.
```

## Analysis Process

When invoked, this skill should:

1. **Analyze Subject Line**:
   - Check for urgent keywords: urgent, asap, important, critical, immediate
   - Check for financial keywords: invoice, payment, bill, refund
   - Check for meeting keywords: meeting, call, schedule, calendar
   - Identify request type: information, action, acknowledgment

2. **Analyze Content**:
   - Extract main request or question
   - Identify any deadlines mentioned
   - Check for financial amounts
   - Identify stakeholders (who is involved)
   - Detect sentiment (positive, neutral, negative, frustrated)

3. **Determine Priority**:
   - **High Priority**:
     - Contains urgent keywords
     - Mentions payment/invoice
     - From known client/important contact
     - Has imminent deadline (< 24 hours)
     - Expresses frustration or complaints
   - **Medium Priority**:
     - Standard business communication
     - No immediate deadline
     - Routine questions
   - **Low Priority**:
     - FYI emails
     - Newsletters
     - Marketing content

4. **Suggest Response Strategy**:
   - **Immediate** (< 2 hours): High priority, urgent requests
   - **Same day** (< 24 hours): Medium priority, standard requests
   - **Within 2-3 days**: Low priority, informational

5. **Generate Action Steps**:
   Based on email type, suggest specific steps:
   - **Invoice requests**: Verify details → Calculate amount → Generate invoice → Get approval → Send
   - **Meeting requests**: Check calendar → Propose times → Confirm
   - **Questions**: Research answer → Draft response → Send
   - **Complaints**: Acknowledge → Investigate → Propose solution → Escalate if needed

## Example Output

```
Email Analysis:
- Priority: HIGH
- Type: Invoice Request
- Urgency: Immediate (ASAP mentioned)
- Financial: Yes (invoice for January)
- Response Strategy: Same day response required
- Approval Needed: Yes (payment/financial matter)

Suggested Action Steps:
1. Review email and clarify which invoice is needed
2. Verify client account details
3. Calculate January charges
4. Generate invoice PDF
5. Get approval for sending (financial matter >$100)
6. Send invoice to client
7. Verify delivery and move to /Done/

Risk Factors:
- Uses "ASAP" - client needs this urgently
- Financial matter - requires approval per Company Handbook
- External stakeholder - client relationship important
```

## Priority Classification Rules

### High Priority Indicators
- Keywords: urgent, asap, critical, immediate, emergency, help
- From: clients, boss, key stakeholders
- Content: complaints, payment issues, system down, deadline today
- Sentiment: frustrated, angry, demanding

### Medium Priority Indicators
- Keywords: please, when possible, at your convenience
- From: colleagues, vendors, partners
- Content: routine requests, questions, updates
- Sentiment: neutral, polite

### Low Priority Indicators
- Keywords: FYI, no rush, whenever
- From: newsletters, automated emails, marketing
- Content: informational, announcements, promotions
- Sentiment: N/A (automated)

## Response Time Guidelines

Based on Company_Handbook.md default rules:
- **Client emails**: Within 24 hours (high priority: same day)
- **Internal emails**: Within 2-3 days
- **Urgent issues**: Within 2 hours
- **Financial matters**: Same day after approval

## Approval Detection

Suggest approval needed if email involves:
- Payment requests over $100
- Sending emails to new contacts not in handbook
- Irreversible actions (refunds, deletions, cancellations)
- Sensitive information disclosure
- Commitments (contracts, agreements, proposals)

## Integration with vault-manager

This skill feeds into the vault-manager plan action to:
- Set correct priority levels
- Generate context-appropriate steps
- Determine if approval workflow needed
- Provide business context for planning

## Error Handling

- If email content is unclear: Suggest "Request clarification" as first step
- If sender is unknown: Mark as medium priority, suggest verification
- If subject is empty: Analyze content only
- If content is very long: Summarize key points first
