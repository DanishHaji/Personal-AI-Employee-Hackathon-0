---
trust_rules:
  - rule_id: RULE_test_auto_approve
    rule_name: "Test Auto-Approve"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@example.com"]
    enabled: true
    effectiveness_score: 1.0
---

# Company Handbook

## Trust Rules

This handbook contains AI behavior rules and trust policies.

In TEST MODE, all actions from @example.com are auto-approved.

## Usage

1. Drop files in `/Inbox/` for file processing
2. Drop email files in `/Mock_Inbox/` for email simulation
3. Check `/Needs_Action/` for detected items
4. Review `/Plans/` for AI-generated action plans

## Test Mode

Currently running in TEST MODE (no Gmail API required).
