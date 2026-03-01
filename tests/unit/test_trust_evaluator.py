"""
Unit Tests for TrustEvaluator Service - Gold Tier US1

Tests trust rule matching, effectiveness tracking, and auto-disable logic.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from datetime import datetime, timedelta

from src.models.trust_rule import TrustRule, create_default_trust_rules, get_next_rule_id
from src.services.trust_evaluator import TrustEvaluator


class TestTrustRule:
    """Test TrustRule model validation and matching logic."""

    def test_trust_rule_creation(self):
        """Test basic TrustRule creation and validation."""
        rule = TrustRule(
            rule_id="RULE_test_email",
            rule_name="Test Email Rule",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )

        assert rule.validate()
        assert rule.rule_id == "RULE_test_email"
        assert rule.effectiveness_score == 1.0
        assert rule.usage_count == 0
        assert rule.enabled

    def test_rule_id_validation(self):
        """Test rule_id format validation."""
        # Valid rule_id
        rule = TrustRule(
            rule_id="RULE_valid_name",
            rule_name="Valid Rule",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )
        assert rule.validate()

        # Invalid rule_id (no RULE_ prefix)
        with pytest.raises(ValueError, match="does not match"):
            rule = TrustRule(
                rule_id="invalid_name",
                rule_name="Invalid Rule",
                action_type="email_send",
                trust_level=1,
                created_at=datetime.utcnow(),
                created_by="user"
            )
            rule.validate()

        # Invalid rule_id (uppercase after prefix)
        with pytest.raises(ValueError, match="does not match"):
            rule = TrustRule(
                rule_id="RULE_InvalidName",
                rule_name="Invalid Rule",
                action_type="email_send",
                trust_level=1,
                created_at=datetime.utcnow(),
                created_by="user"
            )
            rule.validate()

    def test_trust_level_validation(self):
        """Test trust_level range validation."""
        # Valid trust levels
        for level in [0, 1, 2, 3]:
            rule = TrustRule(
                rule_id=f"RULE_level_{level}",
                rule_name=f"Level {level}",
                action_type="email_send",
                trust_level=level,
                created_at=datetime.utcnow(),
                created_by="user"
            )
            assert rule.validate()

        # Invalid trust level
        with pytest.raises(ValueError, match="greater than the maximum"):
            rule = TrustRule(
                rule_id="RULE_invalid_level",
                rule_name="Invalid Level",
                action_type="email_send",
                trust_level=4,
                created_at=datetime.utcnow(),
                created_by="user"
            )
            rule.validate()

    def test_contact_filter_matching(self):
        """Test contact filter matching logic."""
        rule = TrustRule(
            rule_id="RULE_team_email",
            rule_name="Team Emails",
            action_type="email_send",
            trust_level=1,
            contact_filter=["@example.com", "john@external.com"],
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Domain match
        assert rule.matches_contact("alice@example.com")
        assert rule.matches_contact("bob@example.com")

        # Exact match
        assert rule.matches_contact("john@external.com")

        # No match
        assert not rule.matches_contact("stranger@other.com")

        # No filter means match all
        rule_no_filter = TrustRule(
            rule_id="RULE_all_email",
            rule_name="All Emails",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )
        assert rule_no_filter.matches_contact("anyone@anywhere.com")

    def test_content_pattern_matching(self):
        """Test content pattern regex matching."""
        rule = TrustRule(
            rule_id="RULE_urgent_email",
            rule_name="Urgent Emails",
            action_type="email_send",
            trust_level=1,
            content_pattern=".*urgent.*",
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Pattern matches
        assert rule.matches_content("This is urgent!")
        assert rule.matches_content("URGENT: Please review")
        assert rule.matches_content("Not urgent but important urgently")

        # Pattern doesn't match
        assert not rule.matches_content("Normal email content")

        # No pattern means match all
        rule_no_pattern = TrustRule(
            rule_id="RULE_all_content",
            rule_name="All Content",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )
        assert rule_no_pattern.matches_content("Any content")

    def test_time_pattern_matching(self):
        """Test time pattern matching."""
        rule = TrustRule(
            rule_id="RULE_business_hours",
            rule_name="Business Hours",
            action_type="email_send",
            trust_level=1,
            time_pattern="weekdays 9am-5pm",
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Weekday during business hours (Monday 10am)
        monday_10am = datetime(2026, 3, 2, 10, 0)  # Monday
        assert rule.matches_time(monday_10am)

        # Weekday outside business hours (Monday 6pm)
        monday_6pm = datetime(2026, 3, 2, 18, 0)
        assert not rule.matches_time(monday_6pm)

        # Weekend (Saturday 10am)
        saturday_10am = datetime(2026, 3, 7, 10, 0)  # Saturday
        assert not rule.matches_time(saturday_10am)

        # No pattern means match all times
        rule_no_pattern = TrustRule(
            rule_id="RULE_anytime",
            rule_name="Anytime",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )
        assert rule_no_pattern.matches_time(saturday_10am)

    def test_value_limit_matching(self):
        """Test max_value limit matching."""
        rule = TrustRule(
            rule_id="RULE_small_expense",
            rule_name="Small Expenses",
            action_type="expense_record",
            trust_level=1,
            max_value=50.00,
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Within limit
        assert rule.matches_value(25.00)
        assert rule.matches_value(50.00)

        # Exceeds limit
        assert not rule.matches_value(50.01)
        assert not rule.matches_value(100.00)

        # No value provided
        assert not rule.matches_value(None)

        # No limit means match all values
        rule_no_limit = TrustRule(
            rule_id="RULE_any_expense",
            rule_name="Any Expense",
            action_type="expense_record",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )
        assert rule_no_limit.matches_value(1000000.00)
        assert rule_no_limit.matches_value(None)

    def test_effectiveness_tracking(self):
        """Test effectiveness score updates and auto-disable."""
        rule = TrustRule(
            rule_id="RULE_test_effectiveness",
            rule_name="Test Effectiveness",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Initial state
        assert rule.effectiveness_score == 1.0
        assert rule.enabled

        # Positive feedback (should stay high)
        rule.update_effectiveness(user_would_approve=True)
        assert rule.effectiveness_score >= 0.9
        assert rule.enabled

        # Negative feedback (should decrease)
        for _ in range(10):
            rule.update_effectiveness(user_would_approve=False)

        # Should be auto-disabled now
        assert rule.effectiveness_score < 0.80
        assert not rule.enabled

    def test_usage_tracking(self):
        """Test usage count and last_used tracking."""
        rule = TrustRule(
            rule_id="RULE_test_usage",
            rule_name="Test Usage",
            action_type="email_send",
            trust_level=1,
            created_at=datetime.utcnow(),
            created_by="user"
        )

        assert rule.usage_count == 0
        assert rule.last_used is None

        # Record usage
        rule.record_usage()

        assert rule.usage_count == 1
        assert rule.last_used is not None

        # Record multiple usages
        for _ in range(5):
            rule.record_usage()

        assert rule.usage_count == 6

    def test_default_trust_rules(self):
        """Test creation of default trust rules."""
        default_rules = create_default_trust_rules()

        assert len(default_rules) == 3
        assert all(isinstance(rule, TrustRule) for rule in default_rules)
        assert all(not rule.enabled for rule in default_rules)  # All disabled by default

        # Validate all default rules
        for rule in default_rules:
            assert rule.validate()

    def test_next_rule_id_generation(self):
        """Test unique rule_id generation."""
        existing_rules = [
            TrustRule(
                rule_id="RULE_email_team",
                rule_name="Email Team",
                action_type="email_send",
                trust_level=1,
                created_at=datetime.utcnow(),
                created_by="user"
            )
        ]

        # Generate new ID
        new_id = get_next_rule_id(existing_rules, "Email Team")

        # Should add suffix to avoid collision
        assert new_id == "RULE_email_team_2"

        # Test with clean description
        new_id_2 = get_next_rule_id(existing_rules, "Social Media Posts")
        assert new_id_2 == "RULE_social_media_posts"


class TestTrustEvaluator:
    """Test TrustEvaluator service with temporary vault."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault with Company_Handbook.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Create Company_Handbook.md with trust rules
            handbook_content = """---
trust_rules:
  - rule_id: RULE_email_team
    rule_name: "Email Replies to Team"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@example.com"]
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: "2026-03-01T00:00:00Z"
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: true

  - rule_id: RULE_small_expense
    rule_name: "Small Expenses"
    action_type: expense_record
    trust_level: 1
    contact_filter: null
    content_pattern: null
    time_pattern: null
    max_value: 50.00
    created_at: "2026-03-01T00:00:00Z"
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: true

  - rule_id: RULE_disabled_rule
    rule_name: "Disabled Rule"
    action_type: email_send
    trust_level: 1
    contact_filter: null
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: "2026-03-01T00:00:00Z"
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: false
---

# Company Handbook

Test handbook content.
"""
            handbook_path = vault_path / "Company_Handbook.md"
            handbook_path.write_text(handbook_content)

            yield vault_path

    def test_trust_evaluator_initialization(self, temp_vault):
        """Test TrustEvaluator loads rules from handbook."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Should load 3 rules (2 enabled, 1 disabled)
        all_rules = evaluator.get_all_rules()
        assert len(all_rules) == 3

        enabled_rules = evaluator.get_enabled_rules()
        assert len(enabled_rules) == 2

    def test_evaluate_trusted_email(self, temp_vault):
        """Test evaluation of trusted email action."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Plan matching RULE_email_team
        plan = {
            'type': 'email_send',
            'target': 'alice@example.com',
            'content': 'Test email content'
        }

        is_trusted, rule_id = evaluator.evaluate(plan)

        assert is_trusted
        assert rule_id == "RULE_email_team"

        # Usage should be recorded
        rule = evaluator.get_rule("RULE_email_team")
        assert rule.usage_count == 1
        assert rule.last_used is not None

    def test_evaluate_untrusted_email(self, temp_vault):
        """Test evaluation of untrusted email action."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Plan NOT matching any rules (different domain)
        plan = {
            'type': 'email_send',
            'target': 'stranger@other.com',
            'content': 'Test email content'
        }

        is_trusted, rule_id = evaluator.evaluate(plan)

        assert not is_trusted
        assert rule_id is None

    def test_evaluate_disabled_rule(self, temp_vault):
        """Test that disabled rules don't match."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # RULE_disabled_rule is disabled and has no filters
        # But it shouldn't match because it's disabled
        plan = {
            'type': 'email_send',
            'target': 'anyone@anywhere.com',
            'content': 'Test'
        }

        is_trusted, rule_id = evaluator.evaluate(plan)

        # Should not match disabled rule
        assert not is_trusted

    def test_evaluate_small_expense(self, temp_vault):
        """Test evaluation of small expense."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Plan matching RULE_small_expense
        plan = {
            'type': 'expense_record',
            'target': 'Vendor XYZ',
            'amount': 25.00
        }

        is_trusted, rule_id = evaluator.evaluate(plan)

        assert is_trusted
        assert rule_id == "RULE_small_expense"

    def test_evaluate_large_expense(self, temp_vault):
        """Test evaluation of large expense (exceeds limit)."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Plan NOT matching RULE_small_expense (exceeds max_value)
        plan = {
            'type': 'expense_record',
            'target': 'Vendor XYZ',
            'amount': 100.00
        }

        is_trusted, rule_id = evaluator.evaluate(plan)

        assert not is_trusted
        assert rule_id is None

    def test_update_rule_effectiveness(self, temp_vault):
        """Test updating rule effectiveness via evaluator."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        rule_id = "RULE_email_team"
        rule = evaluator.get_rule(rule_id)

        # Initial effectiveness
        assert rule.effectiveness_score == 1.0
        assert rule.enabled

        # Negative feedback multiple times
        for _ in range(10):
            evaluator.update_rule_effectiveness(rule_id, user_would_approve=False)

        # Should be auto-disabled
        rule = evaluator.get_rule(rule_id)
        assert rule.effectiveness_score < 0.80
        assert not rule.enabled

    def test_add_rule(self, temp_vault):
        """Test adding a new trust rule."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        new_rule = TrustRule(
            rule_id="RULE_social_posts",
            rule_name="Social Media Posts",
            action_type="social_post",
            trust_level=2,
            created_at=datetime.utcnow(),
            created_by="user"
        )

        # Add rule
        evaluator.add_rule(new_rule)

        # Should now have 4 rules
        assert len(evaluator.get_all_rules()) == 4

        # Rule should be retrievable
        retrieved_rule = evaluator.get_rule("RULE_social_posts")
        assert retrieved_rule is not None
        assert retrieved_rule.rule_name == "Social Media Posts"

    def test_remove_rule(self, temp_vault):
        """Test removing a trust rule."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Remove rule
        success = evaluator.remove_rule("RULE_email_team")
        assert success

        # Should now have 2 rules
        assert len(evaluator.get_all_rules()) == 2

        # Rule should not be retrievable
        assert evaluator.get_rule("RULE_email_team") is None

    def test_enable_disable_rule(self, temp_vault):
        """Test enabling and disabling rules."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Disable enabled rule
        success = evaluator.disable_rule("RULE_email_team")
        assert success

        rule = evaluator.get_rule("RULE_email_team")
        assert not rule.enabled

        # Enable disabled rule
        success = evaluator.enable_rule("RULE_disabled_rule")
        assert success

        rule = evaluator.get_rule("RULE_disabled_rule")
        assert rule.enabled

    def test_get_rules_summary(self, temp_vault):
        """Test rules summary statistics."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        summary = evaluator.get_rules_summary()

        assert summary['total_rules'] == 3
        assert summary['enabled_rules'] == 2
        assert summary['disabled_rules'] == 1
        assert 'by_action_type' in summary
        assert 'avg_effectiveness_score' in summary
        assert summary['total_usage_count'] == 0  # No usage yet

    def test_reload_rules(self, temp_vault):
        """Test reloading rules after manual handbook edits."""
        evaluator = TrustEvaluator(vault_path=temp_vault)

        # Initial state
        assert len(evaluator.get_all_rules()) == 3

        # Manually edit handbook to add a rule
        handbook_path = temp_vault / "Company_Handbook.md"
        with open(handbook_path, 'r') as f:
            content = f.read()

        # Parse and modify
        parts = content.split('---', 2)
        frontmatter = yaml.safe_load(parts[1])

        # Add new rule
        frontmatter['trust_rules'].append({
            'rule_id': 'RULE_manual_add',
            'rule_name': 'Manually Added',
            'action_type': 'email_send',
            'trust_level': 1,
            'contact_filter': None,
            'content_pattern': None,
            'time_pattern': None,
            'max_value': None,
            'created_at': '2026-03-01T00:00:00Z',
            'created_by': 'user',
            'last_used': None,
            'usage_count': 0,
            'effectiveness_score': 1.0,
            'enabled': True
        })

        # Write back
        new_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
        new_content = f"---\n{new_yaml}---{parts[2]}"
        handbook_path.write_text(new_content)

        # Reload
        evaluator.reload_rules()

        # Should now have 4 rules
        assert len(evaluator.get_all_rules()) == 4
        assert evaluator.get_rule('RULE_manual_add') is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
