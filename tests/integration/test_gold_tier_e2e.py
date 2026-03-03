#!/usr/bin/env python3
"""
Gold Tier End-to-End Integration Tests (T127)

Tests the complete autonomous workflow from email receipt to follow-up:
1. Auto-reply via trust rules
2. Meeting scheduling with calendar integration
3. Meeting attendance and transcription
4. Document generation
5. Proactive follow-up suggestions

These tests validate the full integration of all 8 Gold Tier user stories.
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from src.services.trust_evaluator import TrustEvaluator
from src.services.calendar_service import CalendarService
from src.services.meeting_service import MeetingService
from src.services.document_service import DocumentService
from src.services.expense_service import ExpenseService
from src.services.contact_service import ContactService
from src.services.analytics_service import AnalyticsService
from src.services.suggestion_engine import SuggestionEngine
from src.models.action_plan import ActionPlan, Step
from src.models.trust_rule import TrustRule
from src.models.contact import Contact


class TestEndToEndWorkflow:
    """Test complete autonomous workflow (T127)."""

    @pytest.fixture
    def vault_path(self, tmp_path):
        """Create temporary vault structure."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create all required folders
        folders = [
            "Needs_Action", "Plans", "Pending_Approval", "Approved",
            "Done", "Logs", "Contacts", "Expenses", "Budgets",
            "Receipts", "Meetings", "Calendar", "Insights"
        ]
        for folder in folders:
            (vault / folder).mkdir()

        # Create Company_Handbook.md with trust rules
        handbook = vault / "Company_Handbook.md"
        handbook.write_text("""---
trust_rules:
  - rule_id: RULE_email_known_contacts
    rule_name: "Email Replies to Known Contacts"
    action_type: email_send
    trust_level: 1
    contact_filter: ["@example.com"]
    content_pattern: null
    time_pattern: null
    max_value: null
    created_at: 2026-02-27T10:00:00Z
    created_by: user
    last_used: null
    usage_count: 0
    effectiveness_score: 1.0
    enabled: true
---

# Company Handbook

Trust rules configured for autonomous operation.
""")

        return vault

    @pytest.fixture
    def mock_apis(self):
        """Mock all external APIs."""
        mocks = {
            'gmail': Mock(),
            'calendar': Mock(),
            'zoom': Mock(),
            'whisper': Mock(),
            'vision': Mock()
        }
        return mocks

    def test_scenario_1_trust_rule_auto_approval(self, vault_path):
        """
        Test Scenario 1: Trust Rule Auto-Approval

        Given a trust rule for known contacts,
        When an email arrives from known contact,
        Then it should auto-approve without manual intervention.
        """
        # Setup
        evaluator = TrustEvaluator(vault_path=vault_path)

        action_plan = {
            "action_type": "email_send",
            "recipient": "colleague@example.com",
            "subject": "Re: Meeting Request",
            "body": "Sounds good! I'm available tomorrow at 2pm."
        }

        # Execute
        approved, rule_id = evaluator.evaluate(action_plan)

        # Assert
        assert approved is True, "Trust rule should auto-approve known contact email"
        assert rule_id == "RULE_email_known_contacts"

        # Verify audit trail
        # (In real implementation, would check audit log)
        print(f"✅ Test 1 passed: Auto-approved via rule {rule_id}")

    @patch('src.services.calendar_service.build')
    def test_scenario_2_calendar_scheduling(self, mock_build, vault_path, mock_apis):
        """
        Test Scenario 2: Calendar Integration

        Given a meeting request,
        When checking calendar availability,
        Then schedule at first available slot and send invites.
        """
        # Setup mock Google Calendar API
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock calendar events (simulate conflict at first time)
        mock_service.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'existing_event',
                    'start': {'dateTime': '2026-03-15T14:00:00-07:00'},
                    'end': {'dateTime': '2026-03-15T15:00:00-07:00'}
                }
            ]
        }

        # Mock successful insert
        mock_service.events().insert().execute.return_value = {
            'id': 'new_meeting_id',
            'htmlLink': 'https://calendar.google.com/event?eid=...'
        }

        calendar_service = CalendarService(vault_path=vault_path)

        # Execute
        meeting_request = {
            'title': 'Q2 Planning Meeting',
            'attendees': ['john@example.com', 'jane@example.com'],
            'duration_minutes': 60,
            'preferred_times': [
                '2026-03-15T14:00:00-07:00',  # Conflict
                '2026-03-16T10:00:00-07:00'   # Available
            ],
            'priority': 'high'
        }

        result = calendar_service.schedule_meeting(meeting_request)

        # Assert
        assert result['success'] is True
        assert result['scheduled_time'] == '2026-03-16T10:00:00-07:00'
        assert result['event_id'] == 'new_meeting_id'

        print("✅ Test 2 passed: Meeting scheduled at available slot")

    @patch('src.services.transcription_service.OpenAI')
    def test_scenario_3_meeting_transcription(self, mock_openai, vault_path):
        """
        Test Scenario 3: Meeting Attendance & Transcription

        Given a Zoom meeting,
        When AI joins and records,
        Then generate transcript and extract action items.
        """
        # Setup mock Whisper API
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_transcription = Mock()
        mock_transcription.text = """
        Alice: Welcome everyone to Q2 planning meeting.
        Bob: Thanks Alice. I'd like to discuss budget allocation.
        Alice: Good point. Action item: Bob will send budget proposal by Friday.
        Charlie: I'll review the proposal and provide feedback by Monday.
        """
        mock_client.audio.transcriptions.create.return_value = mock_transcription

        meeting_service = MeetingService(vault_path=vault_path)

        # Execute
        meeting_data = {
            'meeting_id': 'zoom_123456',
            'title': 'Q2 Planning Meeting',
            'start_time': '2026-03-16T10:00:00-07:00',
            'audio_file': '/tmp/test_recording.mp3'
        }

        result = meeting_service.process_meeting(meeting_data)

        # Assert
        assert result['success'] is True
        assert 'transcript' in result
        assert len(result['action_items']) == 2
        assert any('budget proposal' in item.lower() for item in result['action_items'])

        print(f"✅ Test 3 passed: Extracted {len(result['action_items'])} action items from transcript")

    def test_scenario_4_document_generation(self, vault_path):
        """
        Test Scenario 4: Document Generation

        Given a template and audit log data,
        When generating weekly status report,
        Then populate template with accurate metrics.
        """
        # Setup mock audit logs
        logs_dir = vault_path / "Logs"
        today = datetime.now()

        # Create 7 days of mock audit logs
        for i in range(7):
            date = today - timedelta(days=i)
            log_file = logs_dir / f"audit_log_{date.strftime('%Y%m%d')}.jsonl"

            with open(log_file, 'w') as f:
                # Mock actions for the day
                for action_num in range(5):
                    log_entry = {
                        'timestamp': date.isoformat(),
                        'action_type': 'email_send',
                        'status': 'completed'
                    }
                    f.write(json.dumps(log_entry) + '\n')

        doc_service = DocumentService(vault_path=vault_path)

        # Execute
        result = doc_service.generate_from_template(
            template_name='weekly-status.md.j2',
            output_folder='Documents/Status Reports'
        )

        # Assert
        assert result['success'] is True
        assert 'document_path' in result
        assert result['metrics']['emails_sent'] == 35  # 7 days * 5 emails

        print(f"✅ Test 4 passed: Generated document with {result['metrics']['emails_sent']} emails logged")

    def test_scenario_5_expense_ocr_processing(self, vault_path):
        """
        Test Scenario 5: Financial Tracking with OCR

        Given a receipt image,
        When processing with OCR,
        Then extract expense details and update budget.
        """
        # Setup budget
        budgets_dir = vault_path / "Budgets"
        budget_file = budgets_dir / "2026-02.json"

        budget_data = {
            "month": "2026-02",
            "budgets": [{
                "budget_id": "BUDGET_software_2026_02",
                "category": "software",
                "monthly_limit": 500.00,
                "current_spend": 250.00,
                "alert_threshold": 0.80,
                "currency": "USD"
            }]
        }

        with open(budget_file, 'w') as f:
            json.dump(budget_data, f)

        # Mock OCR result
        with patch('src.services.expense_service.easyocr.Reader') as mock_reader:
            mock_reader_instance = Mock()
            mock_reader.return_value = mock_reader_instance

            # Mock OCR detection
            mock_reader_instance.readtext.return_value = [
                ([(0, 0), (100, 0), (100, 20), (0, 20)], 'Adobe Creative Cloud', 0.95),
                ([(0, 30), (100, 30), (100, 50), (0, 50)], 'Amount: $45.99', 0.92),
                ([(0, 60), (100, 60), (100, 80), (0, 80)], 'Date: 2026-02-27', 0.89)
            ]

            expense_service = ExpenseService(vault_path=vault_path)

            # Execute
            result = expense_service.create_expense_from_receipt(
                receipt_path='/tmp/test_receipt.jpg',
                month='2026-02'
            )

        # Assert
        assert result['success'] is True
        assert result['expense']['amount'] == Decimal('45.99')
        assert result['expense']['vendor'] == 'Adobe Creative Cloud'
        assert result['expense']['category'] == 'software'
        assert result['ocr_confidence'] > 0.85

        # Verify budget updated
        updated_budget = json.loads(budget_file.read_text())
        assert updated_budget['budgets'][0]['current_spend'] == 295.99
        assert updated_budget['budgets'][0]['current_spend'] < 400  # Under 80% threshold

        print(f"✅ Test 5 passed: Processed expense of ${result['expense']['amount']}")

    def test_scenario_6_contact_management(self, vault_path):
        """
        Test Scenario 6: CRM Contact Creation

        Given an email from new contact,
        When processing email,
        Then create contact profile with interaction history.
        """
        contact_service = ContactService(vault_path=vault_path)

        # Execute
        email_data = {
            'from': 'alice.johnson@example.com',
            'from_name': 'Alice Johnson',
            'subject': 'Introduction',
            'body': 'Hi, I wanted to reach out regarding...',
            'timestamp': datetime.now().isoformat()
        }

        contact = contact_service.create_or_update_contact(email_data)

        # Assert
        assert contact is not None
        assert contact.name == 'Alice Johnson'
        assert contact.email == 'alice.johnson@example.com'
        assert contact.interaction_count == 1
        assert contact.relationship_strength == 10  # Initial score

        # Verify contact file created
        contact_files = list((vault_path / "Contacts").glob("CONTACT_*.md"))
        assert len(contact_files) == 1

        print(f"✅ Test 6 passed: Created contact {contact.name}")

    def test_scenario_7_analytics_insights(self, vault_path):
        """
        Test Scenario 7: Analytics & Insights Generation

        Given 30 days of audit logs,
        When generating weekly insights,
        Then provide actionable recommendations.
        """
        # Setup mock audit logs with patterns
        logs_dir = vault_path / "Logs"
        today = datetime.now()

        # Create 30 days of logs with Monday email pattern
        for i in range(30):
            date = today - timedelta(days=i)
            log_file = logs_dir / f"audit_log_{date.strftime('%Y%m%d')}.jsonl"

            # More emails on Mondays
            email_count = 15 if date.weekday() == 0 else 5

            with open(log_file, 'w') as f:
                for _ in range(email_count):
                    f.write(json.dumps({
                        'timestamp': date.isoformat(),
                        'action_type': 'email_send',
                        'day_of_week': date.strftime('%A')
                    }) + '\n')

        analytics_service = AnalyticsService(vault_path=vault_path)

        # Execute
        insights = analytics_service.generate_weekly_insights()

        # Assert
        assert insights is not None
        assert 'patterns' in insights
        assert 'recommendations' in insights

        # Should detect Monday email pattern
        monday_pattern = next(
            (p for p in insights['patterns'] if 'monday' in p['description'].lower()),
            None
        )
        assert monday_pattern is not None
        assert monday_pattern['confidence'] > 0.7

        print(f"✅ Test 7 passed: Generated {len(insights['recommendations'])} recommendations")

    def test_scenario_8_proactive_suggestions(self, vault_path):
        """
        Test Scenario 8: Proactive Follow-up Suggestions

        Given an unanswered important email from 3+ days ago,
        When suggestion engine runs,
        Then create follow-up suggestion.
        """
        # Setup: Create old email without reply
        emails_dir = vault_path / "Done"
        old_email_date = datetime.now() - timedelta(days=4)

        email_file = emails_dir / "EMAIL_important_001.md"
        email_file.write_text(f"""---
email_id: EMAIL_001
from: boss@example.com
subject: Urgent: Budget Approval Needed
priority: high
date: {old_email_date.isoformat()}
replied: false
---

Need your approval on Q2 budget ASAP.
""")

        suggestion_engine = SuggestionEngine(vault_path=vault_path)

        # Execute
        suggestions = suggestion_engine.detect_follow_ups()

        # Assert
        assert len(suggestions) > 0

        follow_up = suggestions[0]
        assert follow_up['type'] == 'follow_up'
        assert follow_up['confidence'] > 0.7
        assert 'boss@example.com' in follow_up['context']
        assert 'draft_message' in follow_up

        print(f"✅ Test 8 passed: Generated {len(suggestions)} follow-up suggestions")

    def test_full_e2e_workflow(self, vault_path, mock_apis):
        """
        Test Complete End-to-End Workflow (T127)

        Simulates the full autonomous workflow:
        1. Email arrives → auto-reply via trust rule
        2. Meeting request detected → schedule on calendar
        3. Meeting attended → transcript generated
        4. Meeting notes → action items extracted
        5. Follow-up reminder → proactive suggestion
        """
        print("\n" + "="*70)
        print("RUNNING FULL END-TO-END INTEGRATION TEST")
        print("="*70)

        # Step 1: Email arrives and auto-replies
        print("\n📧 Step 1: Processing incoming email...")
        evaluator = TrustEvaluator(vault_path=vault_path)

        email_action = {
            "action_type": "email_send",
            "recipient": "colleague@example.com",
            "subject": "Re: Let's schedule Q2 planning",
            "body": "Sure! I'm available next week."
        }

        approved, rule_id = evaluator.evaluate(email_action)
        assert approved, "Step 1 failed: Email should be auto-approved"
        print(f"   ✅ Email auto-approved via {rule_id}")

        # Step 2: Meeting scheduled
        print("\n📅 Step 2: Scheduling meeting...")
        with patch('src.services.calendar_service.build') as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            mock_service.events().list().execute.return_value = {'items': []}
            mock_service.events().insert().execute.return_value = {
                'id': 'meeting_123',
                'htmlLink': 'https://calendar.google.com/...'
            }

            calendar_service = CalendarService(vault_path=vault_path)
            meeting_result = calendar_service.schedule_meeting({
                'title': 'Q2 Planning',
                'attendees': ['colleague@example.com'],
                'duration_minutes': 60,
                'preferred_times': ['2026-03-20T14:00:00-07:00']
            })

            assert meeting_result['success'], "Step 2 failed: Meeting not scheduled"
            print(f"   ✅ Meeting scheduled: {meeting_result['event_id']}")

        # Step 3: Meeting transcribed
        print("\n🎙️  Step 3: Processing meeting transcript...")
        with patch('src.services.transcription_service.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_transcription = Mock()
            mock_transcription.text = "Action item: Follow up on budget by Friday."
            mock_client.audio.transcriptions.create.return_value = mock_transcription

            meeting_service = MeetingService(vault_path=vault_path)
            transcript_result = meeting_service.process_meeting({
                'meeting_id': 'meeting_123',
                'title': 'Q2 Planning',
                'start_time': '2026-03-20T14:00:00-07:00',
                'audio_file': '/tmp/recording.mp3'
            })

            assert transcript_result['success'], "Step 3 failed: Transcription failed"
            assert len(transcript_result['action_items']) > 0, "No action items extracted"
            print(f"   ✅ Transcript generated with {len(transcript_result['action_items'])} action items")

        # Step 4: Document generated
        print("\n📝 Step 4: Generating meeting notes...")
        doc_service = DocumentService(vault_path=vault_path)
        # Create mock audit log for document generation
        logs_dir = vault_path / "Logs"
        log_file = logs_dir / f"audit_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'w') as f:
            f.write(json.dumps({'action_type': 'meeting_attended'}) + '\n')

        doc_result = doc_service.generate_from_template(
            template_name='meeting-notes.md.j2',
            output_folder='Meetings'
        )

        assert doc_result['success'], "Step 4 failed: Document not generated"
        print(f"   ✅ Meeting notes saved to {doc_result['document_path']}")

        # Step 5: Proactive follow-up
        print("\n💡 Step 5: Generating proactive follow-up...")
        # Simulate 3 days passing with no action on item
        suggestion_engine = SuggestionEngine(vault_path=vault_path)

        # Create action item that's overdue
        action_item_file = vault_path / "Needs_Action" / "ACTION_budget_followup.md"
        old_date = datetime.now() - timedelta(days=4)
        action_item_file.write_text(f"""---
type: action_item
from_meeting: meeting_123
created: {old_date.isoformat()}
status: pending
---

Follow up on budget by Friday
""")

        suggestions = suggestion_engine.detect_follow_ups()
        assert len(suggestions) > 0, "Step 5 failed: No follow-up suggestion generated"
        print(f"   ✅ Generated {len(suggestions)} follow-up suggestions")

        # Final verification
        print("\n" + "="*70)
        print("✅ FULL END-TO-END TEST PASSED")
        print("="*70)
        print("\nWorkflow Summary:")
        print("  1. Email auto-approved and sent")
        print("  2. Meeting scheduled on calendar")
        print("  3. Meeting transcribed with AI")
        print("  4. Meeting notes generated")
        print("  5. Follow-up suggestion created")
        print("\n🎉 All Gold Tier features working together!")


def test_performance_trust_evaluation(vault_path):
    """
    Test trust evaluation performance target (<10ms).

    Validates T123: Performance monitoring requirement.
    """
    import time

    evaluator = TrustEvaluator(vault_path=vault_path)

    action_plan = {
        "action_type": "email_send",
        "recipient": "test@example.com"
    }

    # Measure evaluation time
    start = time.perf_counter()
    evaluator.evaluate(action_plan)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 10, f"Trust evaluation took {elapsed_ms:.2f}ms (target: <10ms)"
    print(f"✅ Trust evaluation: {elapsed_ms:.2f}ms (under 10ms target)")


if __name__ == "__main__":
    """Run integration tests with pytest."""
    import sys

    # Run tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-s"  # Show print statements
    ])
