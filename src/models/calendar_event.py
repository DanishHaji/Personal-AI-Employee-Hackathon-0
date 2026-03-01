"""
CalendarEvent Model - Gold Tier US2

Represents a Google Calendar event with conflict tracking and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from src.models.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class Attendee:
    """Represents an event attendee."""
    email: str
    name: Optional[str] = None
    response_status: str = "needsAction"  # accepted, declined, tentative, needsAction

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"email": self.email}
        if self.name:
            result["name"] = self.name
        result["response_status"] = self.response_status
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attendee":
        """Create from dictionary."""
        return cls(
            email=data["email"],
            name=data.get("name"),
            response_status=data.get("response_status", "needsAction")
        )


@dataclass
class CalendarEvent(BaseModel):
    """
    Google Calendar event with conflict tracking.

    Attributes:
        event_id: Google Calendar event ID (CAL_xxx format)
        title: Event summary/title
        start_time: Event start (ISO 8601 with timezone)
        end_time: Event end (ISO 8601 with timezone)
        attendees: List of attendees
        location: Physical location
        video_link: Video conference URL
        agenda: Meeting agenda/description
        recurring_pattern: RRULE for recurring events
        recurrence_id: Parent event ID for recurring series
        priority: Event priority (high, medium, low)
        conflicts: List of conflicting event IDs
        created_by: Creator (ai or user)
        created_at: Creation timestamp
        last_modified: Last modification timestamp
        status: Event status (confirmed, tentative, cancelled)
    """

    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    priority: str = "medium"
    created_by: str = "ai"
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    status: str = "confirmed"

    # Optional fields
    attendees: Optional[List[Attendee]] = None
    location: Optional[str] = None
    video_link: Optional[str] = None
    agenda: Optional[str] = None
    recurring_pattern: Optional[str] = None
    recurrence_id: Optional[str] = None
    conflicts: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize timestamps and validate."""
        # Set type identifier
        object.__setattr__(self, 'type', 'calendar_event')

        # Set timestamps if not provided
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None))
        if self.last_modified is None:
            object.__setattr__(self, 'last_modified', self.created_at)

        # Ensure start_time is before end_time
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")

        # Validate priority
        if self.priority not in ["high", "medium", "low"]:
            raise ValueError("priority must be high, medium, or low")

        # Validate status
        if self.status not in ["confirmed", "tentative", "cancelled"]:
            raise ValueError("status must be confirmed, tentative, or cancelled")

        # Validate created_by
        if self.created_by not in ["ai", "user"]:
            raise ValueError("created_by must be ai or user")

    @classmethod
    def get_schema_name(cls) -> Optional[str]:
        """Return JSON Schema filename for validation."""
        return "calendar-event-schema.json"

    def has_conflict_with(self, other: "CalendarEvent") -> bool:
        """
        Check if this event overlaps with another event.

        Args:
            other: Another CalendarEvent

        Returns:
            bool: True if events overlap
        """
        # Skip if either event is cancelled
        if self.status == "cancelled" or other.status == "cancelled":
            return False

        # Check for time overlap
        # Events overlap if: self.start < other.end AND self.end > other.start
        return self.start_time < other.end_time and self.end_time > other.start_time

    def add_conflict(self, event_id: str) -> None:
        """
        Add a conflicting event ID.

        Args:
            event_id: ID of conflicting event
        """
        if event_id not in self.conflicts:
            self.conflicts.append(event_id)
            self.last_modified = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

    def remove_conflict(self, event_id: str) -> None:
        """
        Remove a conflicting event ID.

        Args:
            event_id: ID of event to remove
        """
        if event_id in self.conflicts:
            self.conflicts.remove(event_id)
            self.last_modified = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

    def duration_minutes(self) -> int:
        """
        Calculate event duration in minutes.

        Returns:
            int: Duration in minutes
        """
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    def to_frontmatter(self) -> Dict[str, Any]:
        """
        Convert to YAML frontmatter dictionary.

        Returns:
            Dict with event data
        """
        data = super().to_frontmatter()

        # Convert datetime objects to ISO strings
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.last_modified:
            data["last_modified"] = self.last_modified.isoformat()

        # Convert attendees to dicts
        if self.attendees:
            data["attendees"] = [att.to_dict() for att in self.attendees]

        return data

    @classmethod
    def from_frontmatter(cls, data: Dict[str, Any]) -> "CalendarEvent":
        """
        Create CalendarEvent from frontmatter dictionary.

        Args:
            data: Dictionary from YAML frontmatter

        Returns:
            CalendarEvent instance
        """
        # Parse datetime strings
        if isinstance(data.get("start_time"), str):
            data["start_time"] = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
        if isinstance(data.get("end_time"), str):
            data["end_time"] = datetime.fromisoformat(data["end_time"].replace('Z', '+00:00'))
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        if isinstance(data.get("last_modified"), str):
            data["last_modified"] = datetime.fromisoformat(data["last_modified"].replace('Z', '+00:00'))

        # Parse attendees
        if data.get("attendees"):
            data["attendees"] = [Attendee.from_dict(att) for att in data["attendees"]]

        # Remove BaseModel fields before creating instance
        data.pop("ENCRYPTED_FIELDS", None)
        data.pop("type", None)

        return cls(**data)

    def to_google_calendar_format(self) -> Dict[str, Any]:
        """
        Convert to Google Calendar API format.

        Returns:
            Dict compatible with Google Calendar API
        """
        event = {
            "summary": self.title,
            "start": {
                "dateTime": self.start_time.isoformat(),
                "timeZone": str(self.start_time.tzinfo) if self.start_time.tzinfo else "UTC"
            },
            "end": {
                "dateTime": self.end_time.isoformat(),
                "timeZone": str(self.end_time.tzinfo) if self.end_time.tzinfo else "UTC"
            },
            "status": self.status
        }

        if self.attendees:
            event["attendees"] = [{"email": att.email} for att in self.attendees]

        if self.location:
            event["location"] = self.location

        if self.video_link:
            event["conferenceData"] = {
                "entryPoints": [{
                    "entryPointType": "video",
                    "uri": self.video_link
                }]
            }

        if self.agenda:
            event["description"] = self.agenda

        if self.recurring_pattern:
            event["recurrence"] = [self.recurring_pattern]

        return event

    @classmethod
    def from_google_calendar(cls, gcal_event: Dict[str, Any]) -> "CalendarEvent":
        """
        Create CalendarEvent from Google Calendar API response.

        Args:
            gcal_event: Event dict from Google Calendar API

        Returns:
            CalendarEvent instance
        """
        # Extract start/end times
        start_str = gcal_event["start"].get("dateTime") or gcal_event["start"].get("date")
        end_str = gcal_event["end"].get("dateTime") or gcal_event["end"].get("date")

        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

        # Extract attendees
        attendees = None
        if gcal_event.get("attendees"):
            attendees = [
                Attendee(
                    email=att["email"],
                    name=att.get("displayName"),
                    response_status=att.get("responseStatus", "needsAction")
                )
                for att in gcal_event["attendees"]
            ]

        # Extract video link
        video_link = None
        if gcal_event.get("conferenceData"):
            for entry in gcal_event["conferenceData"].get("entryPoints", []):
                if entry.get("entryPointType") == "video":
                    video_link = entry.get("uri")
                    break

        # Extract recurring pattern
        recurring_pattern = None
        if gcal_event.get("recurrence"):
            recurring_pattern = gcal_event["recurrence"][0]

        return cls(
            event_id=f"CAL_{gcal_event['id']}",
            title=gcal_event.get("summary", "Untitled Event"),
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            location=gcal_event.get("location"),
            video_link=video_link,
            agenda=gcal_event.get("description"),
            recurring_pattern=recurring_pattern,
            recurrence_id=gcal_event.get("recurringEventId"),
            priority="medium",  # Google Calendar doesn't have priority
            status=gcal_event.get("status", "confirmed"),
            created_by="user",  # Assume user created unless we know otherwise
            created_at=datetime.fromisoformat(gcal_event["created"].replace('Z', '+00:00')),
            last_modified=datetime.fromisoformat(gcal_event["updated"].replace('Z', '+00:00'))
        )
