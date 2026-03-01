"""
Unit Tests for Suggestion Engine - Gold Tier US5

Tests proactive suggestion detection, pattern matching, volume limits, and feedback learning.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta

from src.models.proactive_suggestion import (
    ProactiveSuggestion,
    load_suggestions_from_directory,
    get_pending_suggestions,
    expire_old_suggestions
)
from src.services.suggestion_engine import SuggestionEngine


class TestProactiveSuggestion:
    """Test ProactiveSuggestion model validation and factory methods."""

    def test_suggestion_creation(self):
        """Test basic ProactiveSuggestion creation and validation."""
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_followup_2026_03_01",
            category="follow_up",
            reason="No reply received within 3 days",
            confidence_score=0.85,
            context="Email sent to john@example.com about Q2 project",
            suggested_action="Send follow-up email",
            related_entities=["EMAIL_abc123"],
            created_at=datetime.now(),
            priority="high"
        )

        assert suggestion.suggestion_id == "SUGGEST_followup_2026_03_01"
        assert suggestion.category == "follow_up"
        assert suggestion.confidence_score == 0.85
        assert suggestion.priority == "high"
        assert suggestion.user_response is None

    def test_confidence_score_validation(self):
        """Test confidence score must be 0.0-1.0."""
        # Valid confidence
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_test_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.75,
            context="Test context",
            suggested_action="Test action",
            related_entities=[],
            created_at=datetime.now(),
            priority="medium"
        )
        assert suggestion.confidence_score == 0.75

        # Invalid confidence (too high)
        with pytest.raises(ValueError, match="confidence_score must be between"):
            ProactiveSuggestion(
                suggestion_id="SUGGEST_test_002",
                category="follow_up",
                reason="Test",
                confidence_score=1.5,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="medium"
            )

        # Invalid confidence (negative)
        with pytest.raises(ValueError, match="confidence_score must be between"):
            ProactiveSuggestion(
                suggestion_id="SUGGEST_test_003",
                category="follow_up",
                reason="Test",
                confidence_score=-0.1,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="medium"
            )

    def test_category_validation(self):
        """Test category must be one of allowed values."""
        valid_categories = ["follow_up", "reminder", "relationship_maintenance", "task_chain"]

        # Valid categories
        for category in valid_categories:
            suggestion = ProactiveSuggestion(
                suggestion_id=f"SUGGEST_{category}_001",
                category=category,
                reason="Test",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="medium"
            )
            assert suggestion.category == category

        # Invalid category
        with pytest.raises(ValueError, match="category must be one of"):
            ProactiveSuggestion(
                suggestion_id="SUGGEST_invalid_001",
                category="invalid_category",
                reason="Test",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="medium"
            )

    def test_priority_validation(self):
        """Test priority must be high/medium/low."""
        valid_priorities = ["high", "medium", "low"]

        for priority in valid_priorities:
            suggestion = ProactiveSuggestion(
                suggestion_id=f"SUGGEST_priority_{priority}",
                category="follow_up",
                reason="Test",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority=priority
            )
            assert suggestion.priority == priority

        # Invalid priority
        with pytest.raises(ValueError, match="priority must be one of"):
            ProactiveSuggestion(
                suggestion_id="SUGGEST_invalid_priority",
                category="follow_up",
                reason="Test",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="critical"
            )

    def test_expiration_validation(self):
        """Test expires_at must be after created_at."""
        now = datetime.now()

        # Valid expiration
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_expiry_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=now,
            expires_at=now + timedelta(days=7),
            priority="medium"
        )
        assert suggestion.expires_at > suggestion.created_at

        # Invalid expiration (before creation)
        with pytest.raises(ValueError, match="expires_at .* must be after created_at"):
            ProactiveSuggestion(
                suggestion_id="SUGGEST_expiry_002",
                category="follow_up",
                reason="Test",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=now,
                expires_at=now - timedelta(days=1),
                priority="medium"
            )

    def test_is_expired(self):
        """Test expiration check."""
        now = datetime.now()

        # Not expired
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_exp_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=now,
            expires_at=now + timedelta(days=1),
            priority="medium"
        )
        assert not suggestion.is_expired()

        # Expired
        suggestion_expired = ProactiveSuggestion(
            suggestion_id="SUGGEST_exp_002",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),
            priority="medium"
        )
        assert suggestion_expired.is_expired()

    def test_mark_accepted(self):
        """Test marking suggestion as accepted."""
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_accept_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=datetime.now(),
            priority="medium"
        )

        suggestion.mark_accepted("This was helpful!")

        assert suggestion.user_response == "accepted"
        assert suggestion.user_feedback == "This was helpful!"

    def test_mark_rejected(self):
        """Test marking suggestion as rejected."""
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_reject_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=datetime.now(),
            priority="medium"
        )

        suggestion.mark_rejected("Not relevant")

        assert suggestion.user_response == "rejected"
        assert suggestion.user_feedback == "Not relevant"

    def test_create_follow_up_factory(self):
        """Test follow-up factory method."""
        suggestion = ProactiveSuggestion.create_follow_up(
            email_id="EMAIL_abc123",
            contact_email="john@example.com",
            original_subject="Q2 Project Timeline",
            days_since_sent=5,
            draft_message="Hi John, following up on Q2 timeline..."
        )

        assert suggestion.category == "follow_up"
        assert suggestion.priority == "high"  # 5 days = high priority
        assert suggestion.confidence_score >= 0.60
        assert "EMAIL_abc123" in suggestion.related_entities
        assert suggestion.draft_content is not None

    def test_create_reminder_factory(self):
        """Test reminder factory method."""
        due_date = datetime.now() + timedelta(days=2)

        suggestion = ProactiveSuggestion.create_reminder(
            task_name="Monthly Expense Report",
            due_date=due_date,
            related_entities=["BUDGET_monthly"],
            context="Monthly expense report is due on the 5th"
        )

        assert suggestion.category == "reminder"
        # 2 days can be high or medium depending on exact timing
        assert suggestion.priority in ["high", "medium"]
        assert "BUDGET_monthly" in suggestion.related_entities

    def test_create_relationship_maintenance_factory(self):
        """Test relationship maintenance factory method."""
        suggestion = ProactiveSuggestion.create_relationship_maintenance(
            contact_id="CONTACT_john_smith",
            contact_name="John Smith",
            days_since_contact=45,
            last_conversation_topic="Q1 project status"
        )

        assert suggestion.category == "relationship_maintenance"
        assert suggestion.priority == "high"  # 45 days >= 45 = high priority
        assert "CONTACT_john_smith" in suggestion.related_entities
        assert "Q1 project status" in suggestion.context

    def test_create_task_chain_factory(self):
        """Test task chain factory method."""
        suggestion = ProactiveSuggestion.create_task_chain(
            incomplete_task="Create meeting agenda",
            blocking_task="Prepare for Q2 planning meeting",
            related_entities=["CAL_meeting_001"],
            context="Meeting scheduled but no agenda set"
        )

        assert suggestion.category == "task_chain"
        assert suggestion.priority == "medium"
        assert "CAL_meeting_001" in suggestion.related_entities


class TestSuggestionEngine:
    """Test SuggestionEngine service with temporary vault."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Create directory structure
            (vault_path / "Needs_Action").mkdir(parents=True, exist_ok=True)
            (vault_path / "Contacts").mkdir(parents=True, exist_ok=True)
            (vault_path / "Calendar").mkdir(parents=True, exist_ok=True)
            (vault_path / "Logs").mkdir(parents=True, exist_ok=True)
            (vault_path / "Insights").mkdir(parents=True, exist_ok=True)

            # Create Company_Handbook.md with suggestion preferences
            handbook_content = """---
suggestion_preferences:
  enabled_categories:
    - follow_up
    - reminder
    - relationship_maintenance
    - task_chain
  follow_up_threshold_days: 3
  vip_contact_threshold_days: 30
  max_suggestions_per_category: 3
---

# Company Handbook

Test handbook content.
"""
            (vault_path / "Company_Handbook.md").write_text(handbook_content)

            # Create test audit logs
            log_date = datetime.now().date()
            log_file = vault_path / "Logs" / f"{log_date.isoformat()}.json"

            # Sent email (3 days ago, no reply)
            sent_time = datetime.now() - timedelta(days=3)
            log_entries = [
                json.dumps({
                    "id": "EMAIL_abc123",
                    "timestamp": sent_time.isoformat(),
                    "action_type": "email_send",
                    "target": "john@example.com",
                    "result": "success",
                    "parameters": {
                        "subject": "Q2 Project Timeline",
                        "important": True
                    }
                })
            ]
            log_file.write_text("\n".join(log_entries))

            # Create test contact (VIP, stale)
            contact_content = """---
contact_id: CONTACT_john_smith
name: John Smith
email: john@example.com
vip: true
last_contact_date: """ + (datetime.now() - timedelta(days=35)).isoformat() + """
---

# John Smith

## Conversation History

### 2026-01-15 - Q1 Project Discussion
- Topics: Q1 project status, timeline
"""
            (vault_path / "Contacts" / "CONTACT_john_smith.md").write_text(contact_content)

            # Create test calendar events
            event_time = datetime.now() + timedelta(hours=24)
            calendar_data = {
                "events": [
                    {
                        "event_id": "CAL_meeting_001",
                        "title": "Q2 Planning Meeting",
                        "start_time": event_time.isoformat(),
                        "end_time": (event_time + timedelta(hours=1)).isoformat(),
                        "agenda": "",  # Empty agenda
                        "created_by": "ai"
                    }
                ]
            }
            (vault_path / "Calendar" / "events.json").write_text(json.dumps(calendar_data, indent=2))

            yield vault_path

    def test_engine_initialization(self, temp_vault):
        """Test SuggestionEngine loads preferences from handbook."""
        engine = SuggestionEngine(vault_path=temp_vault)

        assert engine.config['follow_up_threshold_days'] == 3
        assert engine.config['vip_contact_threshold_days'] == 30
        assert engine.config['max_suggestions_per_category'] == 3
        assert "follow_up" in engine.config['enabled_categories']

    def test_detect_follow_ups(self, temp_vault):
        """Test follow-up detection for unanswered emails."""
        engine = SuggestionEngine(vault_path=temp_vault)

        suggestions = engine.detect_follow_ups()

        # Should detect the 3-day old email with no reply
        assert len(suggestions) >= 1

        follow_up = suggestions[0]
        assert follow_up.category == "follow_up"
        assert "EMAIL_abc123" in follow_up.related_entities
        assert "john@example.com" in follow_up.context

    def test_detect_incomplete_task_chains(self, temp_vault):
        """Test incomplete task chain detection (meeting with no agenda)."""
        engine = SuggestionEngine(vault_path=temp_vault)

        suggestions = engine.detect_incomplete_task_chains()

        # Should detect meeting with empty agenda
        assert len(suggestions) >= 1

        task_chain = suggestions[0]
        assert task_chain.category == "task_chain"
        assert "CAL_meeting_001" in task_chain.related_entities
        assert "agenda" in task_chain.context.lower()

    def test_detect_stale_relationships(self, temp_vault):
        """Test stale VIP relationship detection."""
        engine = SuggestionEngine(vault_path=temp_vault)

        suggestions = engine.detect_stale_relationships()

        # Should detect John Smith (VIP, 35 days since contact)
        assert len(suggestions) >= 1

        relationship = suggestions[0]
        assert relationship.category == "relationship_maintenance"
        assert "CONTACT_john_smith" in relationship.related_entities
        assert "John Smith" in relationship.context

    def test_volume_limit(self, temp_vault):
        """Test suggestion volume limits per category."""
        engine = SuggestionEngine(vault_path=temp_vault)

        # Create 3 suggestions for follow_up category
        for i in range(3):
            suggestion = ProactiveSuggestion(
                suggestion_id=f"SUGGEST_followup_test_{i}",
                category="follow_up",
                reason=f"Test {i}",
                confidence_score=0.80,
                context="Test",
                suggested_action="Test",
                related_entities=[],
                created_at=datetime.now(),
                priority="medium"
            )
            engine.create_suggestion(suggestion)

        # Check volume limit (should be reached after 3)
        assert not engine._check_volume_limit("follow_up")

        # Other categories should still be under limit
        assert engine._check_volume_limit("reminder")

    def test_category_opt_out(self, temp_vault):
        """Test category opt-in/opt-out via handbook."""
        # Modify handbook to disable follow_up
        handbook_path = temp_vault / "Company_Handbook.md"
        content = handbook_path.read_text()

        # Update preferences to remove follow_up
        content = content.replace(
            "- follow_up\n    - reminder",
            "- reminder"
        )
        handbook_path.write_text(content)

        # Create new engine (loads updated preferences)
        engine = SuggestionEngine(vault_path=temp_vault)

        # follow_up should be disabled
        assert not engine._is_category_enabled("follow_up")
        assert engine._is_category_enabled("reminder")

        # Detect follow-ups should return empty
        suggestions = engine.detect_follow_ups()
        assert len(suggestions) == 0

    def test_feedback_learning(self, temp_vault):
        """Test feedback processing and learning."""
        engine = SuggestionEngine(vault_path=temp_vault)

        # Create and save a suggestion
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_feedback_test",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="urgent project deadline meeting",
            suggested_action="Test",
            related_entities=["EMAIL_test"],
            created_at=datetime.now(),
            priority="medium"
        )
        engine.create_suggestion(suggestion)

        # Process rejection feedback
        engine.process_feedback(
            suggestion_id="SUGGEST_feedback_test",
            response="rejected",
            feedback="Not relevant"
        )

        # Check feedback was recorded
        assert "follow_up" in engine.feedback_history
        assert len(engine.feedback_history["follow_up"]) > 0

        feedback_entry = engine.feedback_history["follow_up"][-1]
        assert feedback_entry["response"] == "rejected"
        assert feedback_entry["feedback_text"] == "Not relevant"

    def test_run_detection(self, temp_vault):
        """Test running all detection methods."""
        engine = SuggestionEngine(vault_path=temp_vault)

        suggestions = engine.run_detection()

        # Should detect at least: follow-up, task chain, relationship maintenance
        assert len(suggestions) >= 3

        categories = {s.category for s in suggestions}
        assert "follow_up" in categories
        assert "task_chain" in categories
        assert "relationship_maintenance" in categories

    def test_create_suggestion_file(self, temp_vault):
        """Test creating suggestion file in /Needs_Action/."""
        engine = SuggestionEngine(vault_path=temp_vault)

        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_file_test",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test context",
            suggested_action="Test action",
            related_entities=["EMAIL_test"],
            created_at=datetime.now(),
            priority="high"
        )

        file_path = engine.create_suggestion(suggestion)

        # Check file was created
        assert file_path.exists()
        assert file_path.name == "SUGGEST_file_test.md"

        # Check content
        content = file_path.read_text()
        assert "# Proactive Suggestion: Follow Up" in content
        assert "Test context" in content
        assert "Test action" in content

    def test_expire_old_suggestions(self, temp_vault):
        """Test expiring old suggestions."""
        needs_action_dir = temp_vault / "Needs_Action"

        # Create expired suggestion
        expired_suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_expired_test",
            category="follow_up",
            reason="Test",
            confidence_score=0.80,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=datetime.now() - timedelta(days=10),
            expires_at=datetime.now() - timedelta(days=3),
            priority="medium"
        )

        file_path = needs_action_dir / expired_suggestion.get_filename()
        expired_suggestion.save_to_file(file_path, body=expired_suggestion.to_markdown_body())

        # Expire old suggestions
        expired_count = expire_old_suggestions(needs_action_dir)

        assert expired_count == 1

        # Check suggestion was marked as expired
        suggestion, _ = ProactiveSuggestion.load_from_file(file_path)
        assert suggestion.user_response == "expired"

    def test_get_pending_suggestions(self, temp_vault):
        """Test getting pending suggestions (not responded to)."""
        needs_action_dir = temp_vault / "Needs_Action"

        # Create pending suggestion
        pending = ProactiveSuggestion(
            suggestion_id="SUGGEST_pending_001",
            category="follow_up",
            reason="Test",
            confidence_score=0.90,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=datetime.now(),
            priority="high"
        )
        pending.save_to_file(needs_action_dir / pending.get_filename(), body=pending.to_markdown_body())

        # Create accepted suggestion
        accepted = ProactiveSuggestion(
            suggestion_id="SUGGEST_accepted_001",
            category="reminder",
            reason="Test",
            confidence_score=0.85,
            context="Test",
            suggested_action="Test",
            related_entities=[],
            created_at=datetime.now(),
            priority="medium"
        )
        accepted.mark_accepted()
        accepted.save_to_file(needs_action_dir / accepted.get_filename(), body=accepted.to_markdown_body())

        # Get pending
        pending_suggestions = get_pending_suggestions(needs_action_dir)

        # Should only include pending, sorted by priority then confidence
        assert len(pending_suggestions) == 1
        assert pending_suggestions[0].suggestion_id == "SUGGEST_pending_001"

    def test_learned_confidence_adjustment(self, temp_vault):
        """Test confidence adjustment based on past feedback."""
        engine = SuggestionEngine(vault_path=temp_vault)

        # Add mock feedback history
        engine.feedback_history["follow_up"] = [
            {
                "response": "accepted",
                "context_keywords": ["project", "timeline", "urgent"]
            },
            {
                "response": "accepted",
                "context_keywords": ["project", "deadline"]
            },
            {
                "response": "rejected",
                "context_keywords": ["invoice", "payment"]
            }
        ]

        # Test confidence for similar context (project-related)
        adjustment = engine._calculate_learned_confidence(
            "follow_up",
            ["project", "timeline", "deadline"]
        )

        # Should boost confidence (high acceptance rate for project-related)
        assert adjustment > 1.0

        # Test confidence for different context (invoice-related)
        adjustment_invoice = engine._calculate_learned_confidence(
            "follow_up",
            ["invoice", "payment", "vendor"]
        )

        # Should reduce confidence (rejected for invoice-related)
        assert adjustment_invoice < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
