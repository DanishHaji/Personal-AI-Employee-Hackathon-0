"""
Unit Tests for Meeting Service - Gold Tier US6

Tests meeting note generation, transcription, action item extraction, and task creation.
"""

import pytest
import tempfile
import wave
import struct
from pathlib import Path
from datetime import datetime

from src.models.meeting_note import MeetingNote, save_meeting_notes
from src.services.meeting_service import MeetingService


class TestMeetingNote:
    """Test MeetingNote model validation and methods."""

    def test_meeting_note_creation(self):
        """Test basic MeetingNote creation and validation."""
        note = MeetingNote(
            note_id="MEETING_2026_03_01_abc",
            meeting_id="CAL_abc123",
            meeting_date=datetime.now(),
            attendees=[
                {"name": "John Smith", "email": "john@example.com", "role": "PM"}
            ],
            duration_minutes=60,
            transcript="This is a test meeting transcript.",
            summary="Test meeting summary",
            key_points=["Point 1", "Point 2"],
            recording_consent=True,
            confidence=0.92
        )

        assert note.note_id == "MEETING_2026_03_01_abc"
        assert note.get_attendee_count() == 1
        assert note.confidence == 0.92
        assert note.recording_consent

    def test_confidence_validation(self):
        """Test confidence score must be 0.0-1.0."""
        # Valid confidence
        note = MeetingNote(
            note_id="MEETING_test",
            meeting_id="CAL_test",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.85
        )
        assert note.confidence == 0.85

        # Invalid confidence (too high)
        with pytest.raises(ValueError, match="confidence must be between"):
            MeetingNote(
                note_id="MEETING_test",
                meeting_id="CAL_test",
                meeting_date=datetime.now(),
                attendees=[{"name": "Test", "email": "test@example.com"}],
                duration_minutes=30,
                transcript="Test",
                summary="Test",
                key_points=["Test"],
                recording_consent=True,
                confidence=1.5
            )

    def test_attendee_validation(self):
        """Test at least one attendee is required."""
        # Valid with attendees
        note = MeetingNote(
            note_id="MEETING_test",
            meeting_id="CAL_test",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90
        )
        assert note.get_attendee_count() == 1

        # Invalid without attendees
        with pytest.raises(ValueError, match="at least one attendee"):
            MeetingNote(
                note_id="MEETING_test",
                meeting_id="CAL_test",
                meeting_date=datetime.now(),
                attendees=[],
                duration_minutes=30,
                transcript="Test",
                summary="Test",
                key_points=["Test"],
                recording_consent=True,
                confidence=0.90
            )

    def test_add_action_item(self):
        """Test adding action items to meeting notes."""
        note = MeetingNote(
            note_id="MEETING_test",
            meeting_id="CAL_test",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90
        )

        assert note.get_action_item_count() == 0

        note.add_action_item(
            task="Send project update",
            assignee="John",
            deadline="2026-03-05"
        )

        assert note.get_action_item_count() == 1
        assert note.action_items[0]["task"] == "Send project update"
        assert note.action_items[0]["assignee"] == "John"

    def test_add_highlight(self):
        """Test adding highlights to meeting notes."""
        note = MeetingNote(
            note_id="MEETING_test",
            meeting_id="CAL_test",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90
        )

        note.add_highlight(
            timestamp="00:15:30",
            content="This is an important point",
            speaker="John"
        )

        assert len(note.highlights) == 1
        assert note.highlights[0]["timestamp"] == "00:15:30"
        assert note.highlights[0]["speaker"] == "John"

    def test_generate_body(self):
        """Test markdown body generation."""
        note = MeetingNote(
            note_id="MEETING_2026_03_01_abc",
            meeting_id="CAL_abc123",
            meeting_date=datetime(2026, 3, 1, 14, 0, 0),
            attendees=[
                {"name": "John Smith", "email": "john@example.com", "role": "PM"},
                {"name": "Jane Doe", "email": "jane@example.com", "role": "Engineer"}
            ],
            duration_minutes=60,
            transcript="Full meeting transcript here...",
            summary="Discussed Q2 roadmap and resource allocation",
            key_points=["MVP scope", "Timeline", "Resources"],
            recording_consent=True,
            confidence=0.92,
            decisions_made=["Focus on MVP features", "6-week timeline"],
            action_items=[
                {"task": "Send roadmap", "assignee": "John", "deadline": "2026-03-05"}
            ]
        )

        body = note.generate_body()

        # Check key sections are present
        assert "# Meeting Notes:" in body
        assert "March 01, 2026" in body
        assert "John Smith (PM)" in body
        assert "Jane Doe (Engineer)" in body
        assert "Discussed Q2 roadmap" in body
        assert "MVP scope" in body
        assert "Focus on MVP features" in body
        assert "**John**: Send roadmap" in body

    def test_generate_id(self):
        """Test meeting note ID generation."""
        meeting_date = datetime(2026, 3, 1, 14, 0, 0)

        # With meeting ID
        note_id = MeetingNote.generate_id(meeting_date, "CAL_abc123xyz")
        assert note_id.startswith("MEETING_2026_03_01_")
        assert "abc123xy" in note_id

        # Without meeting ID (random)
        note_id2 = MeetingNote.generate_id(meeting_date)
        assert note_id2.startswith("MEETING_2026_03_01_")
        assert len(note_id2) > 20

    def test_get_filename(self):
        """Test filename generation."""
        note = MeetingNote(
            note_id="MEETING_2026_03_01_abc",
            meeting_id="CAL_abc123",
            meeting_date=datetime(2026, 3, 1, 14, 0, 0),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=60,
            transcript="Test",
            summary="Test",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90
        )

        # With title
        filename = note.get_filename("Q2 Planning Meeting")
        assert filename == "2026-03-01_Q2_Planning_Meeting.md"

        # Without title
        filename2 = note.get_filename()
        assert filename2.startswith("2026-03-01_")


class TestMeetingService:
    """Test MeetingService with temporary vault."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            yield vault_path

    @pytest.fixture
    def sample_audio(self, temp_vault):
        """Create a sample audio file for testing."""
        audio_path = temp_vault / "test_audio.wav"

        # Create a simple 1-second WAV file
        sample_rate = 44100
        duration = 1  # seconds
        frequency = 440  # A4 note

        with wave.open(str(audio_path), 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample
            wav_file.setframerate(sample_rate)

            # Generate sine wave
            for i in range(sample_rate * duration):
                value = int(32767 * 0.5 * (i / sample_rate))  # Simple ramp
                wav_file.writeframes(struct.pack('<h', value))

        return audio_path

    def test_service_initialization(self, temp_vault):
        """Test MeetingService initialization."""
        service = MeetingService(vault_path=temp_vault)

        assert service.vault_path == temp_vault
        assert service.meetings_dir.exists()
        assert service.recordings_dir.exists()
        assert service.transcripts_dir.exists()
        assert service.needs_action_dir.exists()

    def test_extract_key_points(self, temp_vault):
        """Test key point extraction from transcript."""
        service = MeetingService(vault_path=temp_vault)

        transcript = """
        We discussed the Q2 roadmap and key priorities. The important thing is to focus on
        the MVP features first. We talked about the 6-week timeline and must complete
        user testing before launch.
        """

        key_points = service._extract_key_points(transcript)

        # Should extract at least some points
        assert len(key_points) >= 1
        # Should have reasonable content
        assert all(len(point) > 5 for point in key_points)

    def test_extract_decisions(self, temp_vault):
        """Test decision extraction from transcript."""
        service = MeetingService(vault_path=temp_vault)

        transcript = """
        After discussion, we decided to focus on the MVP features. We agreed that
        the timeline will be 6 weeks. We concluded that weekly check-ins are necessary.
        """

        decisions = service._extract_decisions(transcript)

        assert len(decisions) > 0
        assert any("mvp" in decision.lower() for decision in decisions)

    def test_extract_action_items(self, temp_vault):
        """Test action item extraction from transcript."""
        service = MeetingService(vault_path=temp_vault)

        transcript = """
        John will send the updated roadmap by Friday. Sarah to review the architecture
        plan. Mike will complete user testing by next week.
        """

        action_items = service._extract_action_items(transcript)

        # Should extract at least one action item
        assert len(action_items) >= 1
        # Check for extracted assignees
        assignees = [item.get("assignee", "").lower() for item in action_items]
        assert any("john" in a or "sarah" in a or "mike" in a for a in assignees)

    def test_extract_highlights(self, temp_vault):
        """Test highlight extraction from transcript."""
        service = MeetingService(vault_path=temp_vault)

        transcript = """
        John said "This is the most important feature we need to build."
        Sarah mentioned "We must validate this with users first."
        """

        highlights = service._extract_highlights(transcript)

        assert len(highlights) > 0
        # Should extract quoted text
        assert any("important" in h["content"].lower() for h in highlights)

    def test_create_action_item_tasks(self, temp_vault):
        """Test action item task creation in /Needs_Action/."""
        service = MeetingService(vault_path=temp_vault)

        note = MeetingNote(
            note_id="MEETING_test_123",
            meeting_id="CAL_test",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test meeting",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90,
            action_items=[
                {"task": "Send project update", "assignee": "John", "deadline": "2026-03-05"},
                {"task": "Review code", "assignee": "Sarah", "deadline": "2026-03-06"}
            ]
        )

        service._create_action_item_tasks(note)

        # Check tasks were created
        action_files = list(service.needs_action_dir.glob("ACTION_*.md"))
        assert len(action_files) == 2

        # Check task content
        task_content = action_files[0].read_text()
        assert "ACTION_MEETING_test_123" in task_content
        assert "action_item" in task_content.lower()

    def test_join_meeting_announcement(self, temp_vault):
        """Test meeting join announcement generation."""
        service = MeetingService(vault_path=temp_vault)

        announcement = service.join_meeting_announcement("Q2 Planning")

        assert "AI Meeting Assistant" in announcement
        assert "Q2 Planning" in announcement
        assert "recording" in announcement.lower()
        assert "consent" in announcement.lower()

    def test_save_recording(self, temp_vault, sample_audio):
        """Test saving audio recording."""
        service = MeetingService(vault_path=temp_vault)

        # Read audio data
        with open(sample_audio, 'rb') as f:
            audio_data = f.read()

        # Save recording
        recording_path = service.save_recording(
            audio_data=audio_data,
            meeting_id="CAL_test",
            format="wav"
        )

        assert recording_path.exists()
        assert recording_path.suffix == ".wav"
        assert "CAL_test" in recording_path.name

    def test_list_recent_meetings(self, temp_vault):
        """Test listing recent meetings."""
        service = MeetingService(vault_path=temp_vault)

        # Create test meeting notes
        note1 = MeetingNote(
            note_id="MEETING_recent_1",
            meeting_id="CAL_001",
            meeting_date=datetime.now(),
            attendees=[{"name": "Test", "email": "test@example.com"}],
            duration_minutes=30,
            transcript="Test",
            summary="Test meeting 1",
            key_points=["Test"],
            recording_consent=True,
            confidence=0.90
        )

        save_meeting_notes(note1, temp_vault, "Test Meeting 1")

        # List recent meetings
        recent = service.list_recent_meetings(days=7)

        assert len(recent) >= 1
        assert recent[0]["note_id"] == "MEETING_recent_1"
        assert "attendees_count" in recent[0]
        assert "action_items_count" in recent[0]

    def test_generate_summary_simple(self, temp_vault):
        """Test simple summary generation."""
        service = MeetingService(vault_path=temp_vault)

        transcript = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."

        summary = service._generate_summary(transcript)

        assert len(summary) > 0
        # Should include first few sentences
        assert "sentence one" in summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
