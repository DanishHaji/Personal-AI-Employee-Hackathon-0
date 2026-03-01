"""
MeetingNote Model for Personal AI Employee - Gold Tier

Transcribed and structured notes from meetings the AI attended.

Entity Definition: specs/003-gold-tier-upgrade/data-model.md#meetingnote
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.models.base_model import SimpleEntity

logger = logging.getLogger(__name__)


@dataclass
class Attendee:
    """Meeting attendee information."""
    name: str
    email: str
    role: Optional[str] = None


@dataclass
class ActionItem:
    """Action item extracted from meeting."""
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    context: Optional[str] = None


@dataclass
class Highlight:
    """Important moment from meeting with timestamp."""
    timestamp: str  # Format: HH:MM:SS or seconds
    content: str
    speaker: Optional[str] = None


@dataclass
class MeetingNote(SimpleEntity):
    """
    Transcribed and structured notes from meetings the AI attended.

    Features:
    - Full meeting transcript (encrypted if sensitive)
    - AI-generated summary and key points
    - Extracted action items and decisions
    - Timestamped highlights
    - Link to audio/video recording

    Storage: /Meetings/YYYY-MM-DD_{title}.md

    Example:
        note = MeetingNote(
            note_id="MEETING_2026_03_01_abc",
            meeting_id="CAL_abc123xyz",
            meeting_date=datetime.now(),
            attendees=[
                {"name": "John Smith", "email": "john@example.com", "role": "PM"},
                {"name": "Jane Doe", "email": "jane@example.com", "role": "Engineer"}
            ],
            duration_minutes=60,
            transcript="[00:00:00] John: Let's start...",
            summary="Discussed Q2 roadmap and resource allocation",
            key_points=["Gold Tier MVP scope", "6-week timeline"],
            recording_consent=True,
            confidence=0.92
        )

        # Save to vault
        note.save_to_file(
            "/vault/Meetings/2026-03-01_Q2_Planning.md",
            body=note.generate_body()
        )
    """

    # Required fields
    note_id: str
    meeting_id: str
    meeting_date: datetime
    attendees: List[Dict[str, Any]]  # List of attendee dicts
    duration_minutes: int
    transcript: str
    summary: str
    key_points: List[str]
    recording_consent: bool
    confidence: float  # Transcript accuracy confidence 0.0-1.0

    # Optional fields
    decisions_made: Optional[List[str]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    highlights: Optional[List[Dict[str, Any]]] = None
    recording_link: Optional[str] = None
    encryption_status: bool = False

    # Type identifier
    type: str = field(default="meeting_note", init=False)

    # Encrypted fields
    ENCRYPTED_FIELDS = ["transcript", "recording_link"]

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_confidence()
        self._validate_duration()
        self._validate_attendees()
        self._validate_recording_consent()

        # Initialize optional fields
        if self.decisions_made is None:
            self.decisions_made = []
        if self.action_items is None:
            self.action_items = []
        if self.highlights is None:
            self.highlights = []

    def _validate_confidence(self):
        """Ensure confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    def _validate_duration(self):
        """Ensure duration is positive."""
        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")

    def _validate_attendees(self):
        """Ensure at least one attendee."""
        if not self.attendees or len(self.attendees) == 0:
            raise ValueError("Meeting must have at least one attendee")

        # Validate attendee structure
        for attendee in self.attendees:
            if "name" not in attendee or "email" not in attendee:
                raise ValueError(f"Attendee must have 'name' and 'email' fields: {attendee}")

    def _validate_recording_consent(self):
        """Ensure recording consent was obtained (legal requirement)."""
        if not self.recording_consent:
            logger.warning(f"Meeting {self.note_id} recorded without consent - legal risk!")

    def get_attendee_count(self) -> int:
        """Get number of attendees."""
        return len(self.attendees)

    def get_action_item_count(self) -> int:
        """Get number of action items."""
        return len(self.action_items) if self.action_items else 0

    def get_decisions_count(self) -> int:
        """Get number of decisions made."""
        return len(self.decisions_made) if self.decisions_made else 0

    def add_action_item(self, task: str, assignee: Optional[str] = None, deadline: Optional[str] = None):
        """
        Add an action item to the meeting notes.

        Args:
            task: Description of the action item
            assignee: Person responsible
            deadline: Due date (ISO format or human-readable)
        """
        if self.action_items is None:
            self.action_items = []

        action_item = {
            "task": task,
            "assignee": assignee,
            "deadline": deadline,
            "context": f"From meeting: {self.note_id}"
        }

        self.action_items.append(action_item)
        logger.info(f"Added action item: {task}")

    def add_highlight(self, timestamp: str, content: str, speaker: Optional[str] = None):
        """
        Add a highlight to the meeting notes.

        Args:
            timestamp: Timestamp in format HH:MM:SS or seconds
            content: Content of the highlight
            speaker: Speaker name
        """
        if self.highlights is None:
            self.highlights = []

        highlight = {
            "timestamp": timestamp,
            "content": content,
            "speaker": speaker
        }

        self.highlights.append(highlight)

    def generate_body(self) -> str:
        """
        Generate markdown body content for meeting notes file.

        Returns:
            str: Formatted markdown body
        """
        # Format meeting date
        date_str = self.meeting_date.strftime("%B %d, %Y")

        # Format attendees
        attendees_list = "\n".join([
            f"- {att['name']} ({att.get('role', 'Attendee')})"
            for att in self.attendees
        ])

        # Format key points
        key_points_list = "\n".join([f"- {point}" for point in self.key_points])

        # Format decisions
        decisions_section = ""
        if self.decisions_made and len(self.decisions_made) > 0:
            decisions_list = "\n".join([f"{i+1}. {decision}" for i, decision in enumerate(self.decisions_made)])
            decisions_section = f"""
## Decisions Made

{decisions_list}
"""

        # Format action items
        action_items_section = ""
        if self.action_items and len(self.action_items) > 0:
            items_list = []
            for item in self.action_items:
                assignee_str = f"**{item['assignee']}**: " if item.get('assignee') else ""
                deadline_str = f" (Due: {item['deadline']})" if item.get('deadline') else ""
                items_list.append(f"- [ ] {assignee_str}{item['task']}{deadline_str}")

            action_items_section = f"""
## Action Items

{chr(10).join(items_list)}
"""

        # Format highlights
        highlights_section = ""
        if self.highlights and len(self.highlights) > 0:
            highlights_list = []
            for highlight in self.highlights:
                speaker_str = f"{highlight.get('speaker', 'Speaker')}: " if highlight.get('speaker') else ""
                highlights_list.append(f"- [{highlight['timestamp']}] {speaker_str}\"{highlight['content']}\"")

            highlights_section = f"""
## Highlights

{chr(10).join(highlights_list)}
"""

        # Format transcript section
        transcript_section = ""
        if self.transcript:
            if self.encryption_status:
                transcript_section = f"""
---

**Full Transcript**: [View encrypted transcript]({self.recording_link or 'transcript.encrypted.txt'})

*Transcript is encrypted for privacy. Decryption key required.*
"""
            else:
                # Show first 500 chars as preview
                transcript_preview = self.transcript[:500] + "..." if len(self.transcript) > 500 else self.transcript
                transcript_section = f"""
---

## Full Transcript

```
{transcript_preview}
```

*Full transcript available in meeting notes file.*
"""

        # Recording link
        recording_section = ""
        if self.recording_link:
            recording_section = f"\n**Recording**: [View recording]({self.recording_link})"

        # Confidence indicator
        confidence_emoji = "🟢" if self.confidence >= 0.90 else "🟡" if self.confidence >= 0.75 else "🔴"
        confidence_section = f"\n**Transcript Accuracy**: {confidence_emoji} {self.confidence:.0%}"

        body = f"""# Meeting Notes: {self.note_id.replace('MEETING_', '').replace('_', ' ').title()}

**Date**: {date_str} | **Duration**: {self.duration_minutes} minutes{recording_section}{confidence_section}

## Attendees

{attendees_list}

## Summary

{self.summary}

## Key Discussion Points

{key_points_list}
{decisions_section}{action_items_section}{highlights_section}{transcript_section}

---

*These notes were automatically generated by the AI Meeting Attendant.*
*Meeting ID: {self.meeting_id}*
"""
        return body.strip()

    @classmethod
    def generate_id(cls, meeting_date: datetime, meeting_id: Optional[str] = None) -> str:
        """
        Generate unique meeting note ID.

        Args:
            meeting_date: Date of the meeting
            meeting_id: Optional calendar meeting ID

        Returns:
            str: Unique ID in format "MEETING_{date}_{short_id}"
        """
        date_str = meeting_date.strftime("%Y_%m_%d")

        if meeting_id:
            # Extract short ID from calendar meeting ID
            short_id = meeting_id.replace("CAL_", "")[:8]
        else:
            # Generate random short ID
            import random
            import string
            short_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        return f"MEETING_{date_str}_{short_id}"

    def get_filename(self, title: Optional[str] = None) -> str:
        """
        Generate standard filename for meeting notes.

        Args:
            title: Optional meeting title (defaults to using note_id)

        Returns:
            str: Filename in format "YYYY-MM-DD_{title}.md"
        """
        date_str = self.meeting_date.strftime("%Y-%m-%d")

        if title:
            # Sanitize title for filename
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
            safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        else:
            safe_title = self.note_id.replace("MEETING_", "")

        return f"{date_str}_{safe_title}.md"

    def extract_action_items_for_tasks(self) -> List[Dict[str, Any]]:
        """
        Extract action items in format suitable for task creation.

        Returns:
            List[Dict]: Action items with task file metadata
        """
        if not self.action_items:
            return []

        tasks = []
        for item in self.action_items:
            task = {
                "title": item["task"],
                "assignee": item.get("assignee", "Unassigned"),
                "deadline": item.get("deadline"),
                "context": f"Action item from meeting on {self.meeting_date.strftime('%Y-%m-%d')}",
                "meeting_id": self.meeting_id,
                "note_id": self.note_id,
                "priority": "medium"  # Default priority
            }
            tasks.append(task)

        return tasks


# Helper functions

def parse_meeting_notes(file_path: Path, decrypt: bool = False) -> tuple[MeetingNote, str]:
    """
    Parse meeting notes from markdown file.

    Args:
        file_path: Path to meeting notes file
        decrypt: Whether to decrypt encrypted fields

    Returns:
        tuple: (MeetingNote instance, body content)
    """
    return MeetingNote.load_from_file(file_path, decrypt=decrypt)


def save_meeting_notes(
    note: MeetingNote,
    vault_path: Path,
    title: Optional[str] = None,
    encrypt: bool = False
) -> Path:
    """
    Save meeting notes to vault.

    Args:
        note: MeetingNote instance
        vault_path: Path to vault root
        title: Optional meeting title for filename
        encrypt: Whether to encrypt sensitive fields

    Returns:
        Path: Path to saved file
    """
    meetings_dir = vault_path / "Meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)

    filename = note.get_filename(title)
    file_path = meetings_dir / filename

    body = note.generate_body()
    note.save_to_file(file_path, body=body, encrypt=encrypt)

    logger.info(f"Saved meeting notes to {file_path}")
    return file_path
