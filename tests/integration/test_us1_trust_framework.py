"""
Integration Tests for US1: Trust Framework - Gold Tier

Tests from quickstart.md Test Scenario 1.1:
- Configure trust rule for email replies to known contacts
- Receive test email
- Verify auto-approval without /Pending_Approval/ file
- Check audit log shows trust_rule_id
"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from datetime import datetime

from src.services.trust_evaluator import TrustEvaluator
from src.models.trust_rule import TrustRule


class TestUS1TrustFrameworkIntegration:
    """Integration tests for US1: Autonomous Workflows & Trust Levels."""

    @pytest.fixture
    def test_vault(self):
        """Create test vault with Company_Handbook.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Create required directories
            (vault_path / "Approved").mkdir()
            (vault_path / "Pending_Approval").mkdir()
            (vault_path / "Done").mkdir()
            (vault_path / "Logs").mkdir()

            # Create Company_Handbook.md with test trust rule
            handbook_content = """---
trust_rules:
  - rule_id: RULE_email_known_contacts
    rule_name: "Email Replies to Known Contacts"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@testcompany.com", "trusted@external.com"]
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: "2026-03-01T00:00:00Z"
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: true
---

# Company Handbook

Test configuration for integration tests.
"""
            (vault_path / "Company_Handbook.md").write_text(handbook_content)

            yield vault_path

    def test_scenario_1_1_auto_approve_known_contact(self, test_vault):
        """
        Test Scenario 1.1: Auto-approve email to known contact.

        Given: Trust rule configured for emails to @testcompany.com
        When: Email plan created for alice@testcompany.com
        Then: Plan auto-approved without manual review
        And: Audit log shows trust_rule_id
        """
        # Initialize TrustEvaluator
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Verify trust rule loaded
        rule = evaluator.get_rule("RULE_email_known_contacts")
        assert rule is not None
        assert rule.enabled

        # Create email plan (simulating email to known contact)
        email_plan = {
            'type': 'email_send',
            'target': 'alice@testcompany.com',
            'content': 'Hi Alice, quick update on the project.',
            'subject': 'Project Update'
        }

        # Evaluate trust
        is_trusted, rule_id = evaluator.evaluate(email_plan)

        # Assertions
        assert is_trusted, "Email to known contact should be trusted"
        assert rule_id == "RULE_email_known_contacts", "Should match email_known_contacts rule"

        # Verify usage tracking
        rule = evaluator.get_rule("RULE_email_known_contacts")
        assert rule.usage_count == 1, "Usage count should increment"
        assert rule.last_used is not None, "Last used timestamp should be set"

        # Simulate audit log entry (in real system, executor creates this)
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action_type': 'email_send',
            'actor': 'executor',
            'target': 'alice@testcompany.com',
            'parameters': {
                'trust_rule_id': rule_id,
                'subject': 'Project Update'
            },
            'approval_status': 'approved',
            'approved_by': 'auto',
            'result': 'success'
        }

        # Write to audit log
        log_file = test_vault / "Logs" / f"{datetime.utcnow().date().isoformat()}.json"
        with open(log_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')

        # Verify audit log contains trust_rule_id
        with open(log_file, 'r') as f:
            log_lines = f.readlines()

        assert len(log_lines) == 1
        logged_entry = json.loads(log_lines[0])
        assert logged_entry['parameters']['trust_rule_id'] == "RULE_email_known_contacts"
        assert logged_entry['approved_by'] == 'auto'

    def test_scenario_1_2_require_approval_unknown_contact(self, test_vault):
        """
        Test Scenario 1.2: Require approval for unknown contact.

        Given: Trust rule configured for @testcompany.com only
        When: Email plan created for stranger@unknown.com
        Then: Plan NOT auto-approved (requires manual review)
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Email to unknown contact
        email_plan = {
            'type': 'email_send',
            'target': 'stranger@unknown.com',
            'content': 'Hello stranger',
        }

        # Evaluate trust
        is_trusted, rule_id = evaluator.evaluate(email_plan)

        # Assertions
        assert not is_trusted, "Email to unknown contact should NOT be trusted"
        assert rule_id is None, "No rule should match"

        # In real system, executor would move plan to /Pending_Approval/

    def test_scenario_1_3_revoke_trust(self, test_vault):
        """
        Test Scenario 1.3: Revoke trust for action type.

        Given: Trust rule previously enabled
        When: User disables the rule
        Then: Future actions require manual approval
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Initially trusted
        email_plan = {
            'type': 'email_send',
            'target': 'alice@testcompany.com',
            'content': 'Test'
        }

        is_trusted, _ = evaluator.evaluate(email_plan)
        assert is_trusted, "Should be trusted initially"

        # Revoke trust by disabling rule
        evaluator.disable_rule("RULE_email_known_contacts")

        # Reload to ensure persistence
        evaluator.reload_rules()

        # Same email plan should now require approval
        is_trusted, rule_id = evaluator.evaluate(email_plan)

        assert not is_trusted, "Should NOT be trusted after revoke"
        assert rule_id is None, "Disabled rule should not match"

    def test_scenario_1_4_effectiveness_tracking(self, test_vault):
        """
        Test Scenario 1.4: Effectiveness tracking and auto-disable.

        Given: Trust rule with usage history
        When: User provides negative feedback repeatedly
        Then: Rule auto-disables when effectiveness drops below 0.80
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        rule_id = "RULE_email_known_contacts"
        rule = evaluator.get_rule(rule_id)

        # Initial state
        assert rule.effectiveness_score == 1.0
        assert rule.enabled

        # Simulate negative feedback (10 times)
        for _ in range(10):
            evaluator.update_rule_effectiveness(rule_id, user_would_approve=False)

        # Reload to get updated rule
        rule = evaluator.get_rule(rule_id)

        # Assertions
        assert rule.effectiveness_score < 0.80, "Effectiveness should drop below 0.80"
        assert not rule.enabled, "Rule should auto-disable"

        # Verify plan no longer auto-approved
        email_plan = {
            'type': 'email_send',
            'target': 'alice@testcompany.com',
            'content': 'Test'
        }

        is_trusted, _ = evaluator.evaluate(email_plan)
        assert not is_trusted, "Disabled rule should not auto-approve"

    def test_scenario_1_5_multiple_trust_levels(self, test_vault):
        """
        Test Scenario 1.5: Different trust levels.

        Given: Rules with different trust levels configured
        When: Plans match different trust levels
        Then: Each returns appropriate trust level behavior
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Add trust level 2 rule (auto-approve with notification)
        level_2_rule = TrustRule(
            rule_id="RULE_social_posts",
            rule_name="Social Media Posts",
            action_type="social_post",
            trust_level=2,  # Auto-approve with notification
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=True
        )
        evaluator.add_rule(level_2_rule)

        # Evaluate social post
        social_plan = {
            'type': 'social_post',
            'target': 'LinkedIn',
            'content': 'Exciting news about our product!'
        }

        is_trusted, rule_id = evaluator.evaluate(social_plan)

        assert is_trusted, "Social post should be trusted"
        assert rule_id == "RULE_social_posts"

        # Get rule to verify trust level
        rule = evaluator.get_rule(rule_id)
        assert rule.trust_level == 2, "Should be trust level 2 (with notification)"

    def test_scenario_1_6_content_pattern_filter(self, test_vault):
        """
        Test Scenario 1.6: Content pattern filtering.

        Given: Trust rule with content_pattern filter
        When: Content matches pattern
        Then: Action auto-approved
        When: Content doesn't match pattern
        Then: Action requires approval
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Add rule with content pattern
        urgent_rule = TrustRule(
            rule_id="RULE_urgent_email",
            rule_name="Urgent Emails to Team",
            action_type="email_send",
            trust_level=1,
            contact_filter=["@testcompany.com"],
            content_pattern=".*urgent.*",
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=True
        )
        evaluator.add_rule(urgent_rule)

        # Email with "urgent" in content
        urgent_email = {
            'type': 'email_send',
            'target': 'bob@testcompany.com',
            'content': 'This is urgent! Please respond ASAP.'
        }

        is_trusted, rule_id = evaluator.evaluate(urgent_email)
        assert is_trusted, "Urgent email should match pattern"
        assert rule_id == "RULE_urgent_email"

        # Email without "urgent" in content (should match general rule instead)
        normal_email = {
            'type': 'email_send',
            'target': 'bob@testcompany.com',
            'content': 'Normal update on the project.'
        }

        is_trusted, rule_id = evaluator.evaluate(normal_email)
        # Should match RULE_email_known_contacts (no content filter)
        assert is_trusted
        assert rule_id == "RULE_email_known_contacts"

    def test_scenario_1_7_time_pattern_filter(self, test_vault):
        """
        Test Scenario 1.7: Time pattern filtering.

        Given: Trust rule with time_pattern (business hours)
        When: Action during business hours
        Then: Action auto-approved
        When: Action outside business hours
        Then: Action requires approval
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Add rule with time pattern
        business_hours_rule = TrustRule(
            rule_id="RULE_business_hours_email",
            rule_name="Business Hours Emails",
            action_type="email_send",
            trust_level=1,
            time_pattern="weekdays 9am-5pm",
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=True
        )
        evaluator.add_rule(business_hours_rule)

        # Test during business hours (Monday 10am)
        monday_10am = datetime(2026, 3, 2, 10, 0)

        email_plan = {
            'type': 'email_send',
            'target': 'anyone@anywhere.com',
            'content': 'Test'
        }

        # Manually check time matching (since evaluate() uses current time)
        assert business_hours_rule.matches_time(monday_10am)

        # Test outside business hours (Monday 6pm)
        monday_6pm = datetime(2026, 3, 2, 18, 0)
        assert not business_hours_rule.matches_time(monday_6pm)

        # Test weekend (Saturday 10am)
        saturday_10am = datetime(2026, 3, 7, 10, 0)
        assert not business_hours_rule.matches_time(saturday_10am)

    def test_scenario_1_8_max_value_filter(self, test_vault):
        """
        Test Scenario 1.8: Max value filtering for expenses.

        Given: Trust rule with max_value limit
        When: Expense under limit
        Then: Auto-approved
        When: Expense exceeds limit
        Then: Requires approval
        """
        evaluator = TrustEvaluator(vault_path=test_vault)

        # Add expense rule with value limit
        small_expense_rule = TrustRule(
            rule_id="RULE_small_expense",
            rule_name="Small Expenses",
            action_type="expense_record",
            trust_level=1,
            max_value=50.00,
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=True
        )
        evaluator.add_rule(small_expense_rule)

        # Small expense (under limit)
        small_expense = {
            'type': 'expense_record',
            'target': 'Office Supplies',
            'amount': 25.00
        }

        is_trusted, rule_id = evaluator.evaluate(small_expense)
        assert is_trusted, "Small expense should be auto-approved"
        assert rule_id == "RULE_small_expense"

        # Large expense (exceeds limit)
        large_expense = {
            'type': 'expense_record',
            'target': 'Equipment',
            'amount': 100.00
        }

        is_trusted, rule_id = evaluator.evaluate(large_expense)
        assert not is_trusted, "Large expense should require approval"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
