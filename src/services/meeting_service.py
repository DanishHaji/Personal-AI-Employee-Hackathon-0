"""
Meeting Service for Personal AI Employee - Gold Tier

Orchestrates meeting attendance, recording, transcription, and note generation.

Features:
- Zoom meeting joining (via Zoom SDK or API)
- Recording consent management
- Audio recording download
- Transcript generation with Whisper
- Action item extraction with AI
- Structured note generation
- Integration with calendar events

Usage:
    service = MeetingService(vault_path="/path/to/vault")

    # Attend a meeting
    notes = service.attend_meeting(
        meeting_id="CAL_abc123",
        zoom_meeting_url="https://zoom.us/j/123456789"
    )

    # Generate notes from existing recording
    notes = service.generate_notes_from_recording(
        recording_path="/path/to/recording.m4a",
        meeting_metadata={"title": "Q2 Planning", ...}
    )
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from src.models.meeting_note import MeetingNote, save_meeting_notes
from src.services.transcription_service import TranscriptionService
from src.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)


class MeetingService:
    """
    Service for attending meetings, recording, and generating structured notes.

    Handles the full meeting lifecycle from joining to note generation.
    """

    def __init__(
        self,
        vault_path: str | Path,
        openai_api_key: Optional[str] = None,
        zoom_api_key: Optional[str] = None,
        zoom_api_secret: Optional[str] = None
    ):
        """
        Initialize MeetingService.

        Args:
            vault_path: Path to Obsidian vault root
            openai_api_key: OpenAI API key for transcription and AI
            zoom_api_key: Zoom API key (optional)
            zoom_api_secret: Zoom API secret (optional)
        """
        self.vault_path = Path(vault_path).resolve()
        self.meetings_dir = self.vault_path / "Meetings"
        self.recordings_dir = self.meetings_dir / "Recordings"
        self.transcripts_dir = self.meetings_dir / "Transcripts"
        self.needs_action_dir = self.vault_path / "Needs_Action"

        # Ensure directories exist
        self.meetings_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.transcription_service = TranscriptionService(api_key=openai_api_key)

        # Initialize encryption service (optional - may not be available in all environments)
        try:
            self.encryption_service = get_encryption_service()
        except Exception as e:
            logger.warning(f"Encryption service unavailable: {e}")
            self.encryption_service = None

        # Zoom credentials (for future Zoom SDK integration)
        self.zoom_api_key = zoom_api_key
        self.zoom_api_secret = zoom_api_secret

        # Track active meetings
        self.active_meetings: Dict[str, Dict[str, Any]] = {}

        logger.info("MeetingService initialized")

    def attend_meeting(
        self,
        meeting_id: str,
        zoom_meeting_url: Optional[str] = None,
        calendar_event: Optional[Dict[str, Any]] = None
    ) -> Optional[MeetingNote]:
        """
        Attend a Zoom meeting (simulated - requires Zoom SDK for real implementation).

        Args:
            meeting_id: Calendar event ID
            zoom_meeting_url: Zoom meeting URL
            calendar_event: Calendar event metadata

        Returns:
            MeetingNote: Generated meeting notes, or None if failed
        """
        logger.info(f"Attempting to attend meeting: {meeting_id}")

        # For MVP: This is a placeholder for Zoom SDK integration
        # Real implementation would use Zoom SDK to join meeting and record
        logger.warning(
            "Direct Zoom meeting joining requires Zoom SDK integration. "
            "Use generate_notes_from_recording() for existing recordings."
        )

        return None

    def generate_notes_from_recording(
        self,
        recording_path: str | Path,
        meeting_metadata: Dict[str, Any],
        encrypt_sensitive: bool = False
    ) -> MeetingNote:
        """
        Generate structured meeting notes from an audio recording.

        Args:
            recording_path: Path to audio recording file
            meeting_metadata: Meeting metadata (title, date, attendees, etc.)
            encrypt_sensitive: Whether to encrypt transcript and recording link

        Returns:
            MeetingNote: Generated meeting notes

        Raises:
            ValueError: If recording file not found or transcription fails
        """
        recording_path = Path(recording_path)

        if not recording_path.exists():
            raise ValueError(f"Recording file not found: {recording_path}")

        logger.info(f"Generating notes from recording: {recording_path}")

        # Step 1: Transcribe audio
        logger.info("Step 1: Transcribing audio...")
        transcript, confidence = self.transcription_service.transcribe_audio(recording_path)

        # Step 2: Parse transcript and extract information
        logger.info("Step 2: Parsing transcript...")
        summary = self._generate_summary(transcript)
        key_points = self._extract_key_points(transcript)
        decisions = self._extract_decisions(transcript)
        action_items = self._extract_action_items(transcript)
        highlights = self._extract_highlights(transcript)

        # Step 3: Create MeetingNote
        logger.info("Step 3: Creating meeting note...")

        meeting_date = meeting_metadata.get("meeting_date", datetime.now())
        if isinstance(meeting_date, str):
            meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))

        # Calculate duration
        try:
            duration_minutes = int(self.transcription_service.get_audio_duration(recording_path) / 60)
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            duration_minutes = meeting_metadata.get("duration_minutes", 60)

        # Generate note ID
        note_id = MeetingNote.generate_id(
            meeting_date=meeting_date,
            meeting_id=meeting_metadata.get("meeting_id")
        )

        # Create meeting note
        note = MeetingNote(
            note_id=note_id,
            meeting_id=meeting_metadata.get("meeting_id", "UNKNOWN"),
            meeting_date=meeting_date,
            attendees=meeting_metadata.get("attendees", []),
            duration_minutes=duration_minutes,
            transcript=transcript,
            summary=summary,
            key_points=key_points,
            recording_consent=meeting_metadata.get("recording_consent", True),
            confidence=confidence,
            decisions_made=decisions,
            action_items=action_items,
            highlights=highlights,
            recording_link=str(recording_path),
            encryption_status=encrypt_sensitive
        )

        # Step 4: Save meeting notes
        logger.info("Step 4: Saving meeting notes...")
        title = meeting_metadata.get("title", "Meeting")
        save_meeting_notes(
            note=note,
            vault_path=self.vault_path,
            title=title,
            encrypt=encrypt_sensitive
        )

        # Step 5: Create action item tasks
        logger.info("Step 5: Creating action item tasks...")
        self._create_action_item_tasks(note)

        logger.info(f"Meeting notes generated successfully: {note.note_id}")

        return note

    def _generate_summary(self, transcript: str) -> str:
        """
        Generate AI summary of meeting transcript.

        Args:
            transcript: Full meeting transcript

        Returns:
            str: Summary text
        """
        # Simple summary generation (would use OpenAI API in production)
        # For MVP: Extract first few sentences as summary
        sentences = re.split(r'[.!?]+', transcript)
        clean_sentences = [s.strip() for s in sentences if s.strip()]

        if len(clean_sentences) > 3:
            summary = ". ".join(clean_sentences[:3]) + "."
        else:
            summary = transcript[:200] + "..."

        # TODO: Replace with AI-generated summary using OpenAI API
        # Example:
        # client = OpenAI()
        # response = client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[{
        #         "role": "user",
        #         "content": f"Summarize this meeting transcript in 2-3 sentences:\n\n{transcript}"
        #     }]
        # )
        # summary = response.choices[0].message.content

        return summary

    def _extract_key_points(self, transcript: str) -> List[str]:
        """
        Extract key discussion points from transcript.

        Args:
            transcript: Full meeting transcript

        Returns:
            List[str]: Key points
        """
        # Simple extraction (would use AI in production)
        # Look for common patterns: "discussed", "talked about", "key point"
        key_points = []

        patterns = [
            r"(?:discussed|talking about|key point|important)\s+(.+?)(?:[.!?]|$)",
            r"(?:we should|need to|must)\s+(.+?)(?:[.!?]|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            for match in matches:
                point = match.group(1).strip()
                if point and len(point) > 10 and len(point) < 150:
                    key_points.append(point)

        # Deduplicate and limit
        key_points = list(dict.fromkeys(key_points))[:5]

        # If no points found, extract sentences with keywords
        if not key_points:
            sentences = re.split(r'[.!?]+', transcript)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in ["important", "key", "main", "focus"]):
                    key_points.append(sentence.strip())
                    if len(key_points) >= 3:
                        break

        return key_points or ["Meeting discussion covered multiple topics"]

    def _extract_decisions(self, transcript: str) -> List[str]:
        """
        Extract decisions made during meeting.

        Args:
            transcript: Full meeting transcript

        Returns:
            List[str]: Decisions
        """
        decisions = []

        # Look for decision patterns
        patterns = [
            r"(?:decided|agreed|concluded)\s+(?:to|that)\s+(.+?)(?:[.!?]|$)",
            r"(?:decision|agreement):\s*(.+?)(?:[.!?]|$)",
            r"(?:we will|we'll)\s+(.+?)(?:[.!?]|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            for match in matches:
                decision = match.group(1).strip()
                if decision and len(decision) > 10 and len(decision) < 200:
                    decisions.append(decision)

        # Deduplicate and limit
        decisions = list(dict.fromkeys(decisions))[:5]

        return decisions

    def _extract_action_items(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract action items from transcript.

        Args:
            transcript: Full meeting transcript

        Returns:
            List[Dict]: Action items with task, assignee, deadline
        """
        action_items = []

        # Look for action item patterns
        patterns = [
            # "[Name] will [action] by [deadline]"
            r"(\w+)\s+will\s+(.+?)\s+by\s+(\w+\s+\d+|\w+day|\w+week)",
            # "[Name] to [action]"
            r"(\w+)\s+to\s+(.+?)(?:[.!?]|$)",
            # "Action item: [action] - [assignee]"
            r"action item:\s*(.+?)\s*-\s*(\w+)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, transcript, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                if len(groups) == 3:
                    assignee, task, deadline = groups
                    action_items.append({
                        "task": task.strip(),
                        "assignee": assignee.strip(),
                        "deadline": deadline.strip()
                    })
                elif len(groups) == 2:
                    if "action item" in pattern:
                        task, assignee = groups
                        action_items.append({
                            "task": task.strip(),
                            "assignee": assignee.strip(),
                            "deadline": None
                        })
                    else:
                        assignee, task = groups
                        action_items.append({
                            "task": task.strip(),
                            "assignee": assignee.strip(),
                            "deadline": None
                        })

        # Deduplicate and limit
        seen = set()
        unique_items = []
        for item in action_items:
            task_key = item["task"].lower()
            if task_key not in seen and len(item["task"]) > 10:
                seen.add(task_key)
                unique_items.append(item)
                if len(unique_items) >= 10:
                    break

        return unique_items

    def _extract_highlights(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract important moments/quotes from transcript.

        Args:
            transcript: Full meeting transcript

        Returns:
            List[Dict]: Highlights with timestamp and content
        """
        highlights = []

        # Look for quoted text or emphasized statements
        # In a real implementation, this would use timestamps from Whisper

        # Pattern for quotes
        quote_pattern = r'"([^"]{20,150})"'
        matches = re.finditer(quote_pattern, transcript)

        for i, match in enumerate(matches):
            if i >= 5:  # Limit to 5 highlights
                break

            quote = match.group(1)

            # Estimate timestamp (simple approach - would use real timestamps in production)
            position = match.start()
            estimated_time = int((position / len(transcript)) * 60)  # Assume 60 min meeting
            timestamp = f"{estimated_time // 60:02d}:{estimated_time % 60:02d}:00"

            highlights.append({
                "timestamp": timestamp,
                "content": quote,
                "speaker": None  # Would extract from context in production
            })

        return highlights

    def _create_action_item_tasks(self, note: MeetingNote):
        """
        Create task files in /Needs_Action/ for each action item.

        Args:
            note: MeetingNote with action items
        """
        if not note.action_items:
            return

        logger.info(f"Creating {len(note.action_items)} action item tasks...")

        for i, item in enumerate(note.action_items):
            task_id = f"ACTION_{note.note_id}_{i+1:02d}"

            # Create task file
            assignee = item.get("assignee", "Unassigned")
            deadline = item.get("deadline", "No deadline")
            task_desc = item["task"]

            content = f"""---
task_id: {task_id}
type: action_item
source: meeting_note
meeting_id: {note.meeting_id}
note_id: {note.note_id}
assignee: {assignee}
deadline: {deadline}
created_at: {datetime.now().isoformat()}
status: pending
---

# Action Item: {task_desc}

**From Meeting**: {note.meeting_date.strftime('%Y-%m-%d')}
**Assigned To**: {assignee}
**Deadline**: {deadline}

## Context

This action item was extracted from the meeting notes.

**Meeting Summary**: {note.summary[:200]}...

## Task

{task_desc}

---

**Next Steps**:
- Review and clarify if needed
- Add to your task management system
- Complete before deadline
- Update status when done
"""

            # Save task file
            task_filename = f"{task_id}.md"
            task_path = self.needs_action_dir / task_filename

            task_path.write_text(content, encoding='utf-8')
            logger.info(f"Created action item task: {task_path}")

    def join_meeting_announcement(self, meeting_title: str) -> str:
        """
        Generate announcement message when AI joins meeting.

        Args:
            meeting_title: Title of the meeting

        Returns:
            str: Announcement text
        """
        return (
            f"Hello everyone! This is the AI Meeting Assistant for {meeting_title}. "
            "I will be recording this meeting and taking notes. "
            "Does everyone consent to being recorded? Please say 'yes' or indicate in the chat."
        )

    def save_recording(
        self,
        audio_data: bytes,
        meeting_id: str,
        format: str = "m4a"
    ) -> Path:
        """
        Save audio recording to vault.

        Args:
            audio_data: Raw audio data
            meeting_id: Meeting identifier
            format: Audio format (m4a, wav, mp3)

        Returns:
            Path: Path to saved recording
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_{meeting_id}.{format}"
        recording_path = self.recordings_dir / filename

        with open(recording_path, 'wb') as f:
            f.write(audio_data)

        logger.info(f"Saved recording: {recording_path}")

        return recording_path

    def get_meeting_notes(self, note_id: str) -> Optional[MeetingNote]:
        """
        Load meeting notes by ID.

        Args:
            note_id: Meeting note ID

        Returns:
            MeetingNote: Loaded notes, or None if not found
        """
        # Search for note file
        for note_file in self.meetings_dir.glob("*.md"):
            try:
                note, _ = MeetingNote.load_from_file(note_file, decrypt=True)
                if note.note_id == note_id:
                    return note
            except Exception as e:
                logger.debug(f"Error loading {note_file}: {e}")
                continue

        logger.warning(f"Meeting notes not found: {note_id}")
        return None

    def list_recent_meetings(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        List recent meetings with notes.

        Args:
            days: Number of days to look back

        Returns:
            List[Dict]: Meeting summaries
        """
        cutoff_date = datetime.now().timestamp() - (days * 86400)
        recent_meetings = []

        for note_file in self.meetings_dir.glob("*.md"):
            if note_file.stat().st_mtime < cutoff_date:
                continue

            try:
                note, _ = MeetingNote.load_from_file(note_file, decrypt=False)

                recent_meetings.append({
                    "note_id": note.note_id,
                    "meeting_id": note.meeting_id,
                    "date": note.meeting_date.isoformat(),
                    "attendees_count": note.get_attendee_count(),
                    "action_items_count": note.get_action_item_count(),
                    "file_path": str(note_file)
                })
            except Exception as e:
                logger.debug(f"Error loading {note_file}: {e}")
                continue

        # Sort by date (newest first)
        recent_meetings.sort(key=lambda x: x["date"], reverse=True)

        return recent_meetings


# Helper functions

def generate_notes_from_audio(
    audio_path: str | Path,
    vault_path: str | Path,
    meeting_metadata: Dict[str, Any]
) -> MeetingNote:
    """
    Helper function to generate meeting notes from audio file.

    Args:
        audio_path: Path to audio recording
        vault_path: Path to vault root
        meeting_metadata: Meeting metadata

    Returns:
        MeetingNote: Generated meeting notes
    """
    service = MeetingService(vault_path=vault_path)
    return service.generate_notes_from_recording(audio_path, meeting_metadata)


if __name__ == "__main__":
    # Test runner
    import sys

    if len(sys.argv) < 3:
        print("Usage: python meeting_service.py <vault_path> <audio_file>")
        sys.exit(1)

    vault_path = sys.argv[1]
    audio_file = sys.argv[2]

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Generate notes
    service = MeetingService(vault_path=vault_path)

    metadata = {
        "title": "Test Meeting",
        "meeting_date": datetime.now(),
        "attendees": [
            {"name": "Test User", "email": "test@example.com", "role": "Participant"}
        ],
        "recording_consent": True
    }

    notes = service.generate_notes_from_recording(audio_file, metadata)

    print(f"\n=== Meeting Notes Generated ===")
    print(f"Note ID: {notes.note_id}")
    print(f"Summary: {notes.summary}")
    print(f"Action Items: {notes.get_action_item_count()}")
