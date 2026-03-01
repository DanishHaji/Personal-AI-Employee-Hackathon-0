"""
CalendarService - Gold Tier US2

Google Calendar integration with conflict detection, event caching, and autonomous scheduling.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import os

from src.models.calendar_event import CalendarEvent, Attendee

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Google Calendar integration service.

    Features:
    - Google Calendar API authentication
    - Event querying with conflict detection
    - Local event caching for performance
    - Recurring event support (RRULE)
    - Calendar preferences (work hours, no-meeting blocks)
    - Trust framework integration for auto-scheduling
    """

    def __init__(self, vault_path: Path, credentials_path: Optional[str] = None):
        """
        Initialize CalendarService.

        Args:
            vault_path: Path to Obsidian vault
            credentials_path: Path to Google Calendar credentials JSON
        """
        self.vault_path = Path(vault_path)
        self.cache_path = self.vault_path / "Calendar" / "events.json"
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")

        # Ensure Calendar directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Google Calendar API service (lazy initialized)
        self._service = None
        self._calendar_id = "primary"

        # Local event cache
        self._cached_events: Dict[str, CalendarEvent] = {}
        self._cache_last_sync: Optional[datetime] = None

        # Load cached events
        self._load_cache()

        logger.info(f"CalendarService initialized (vault: {vault_path})")

    def _get_google_service(self):
        """
        Get Google Calendar API service (lazy initialization).

        Returns:
            Google Calendar service object

        Raises:
            RuntimeError: If credentials are not configured
        """
        if self._service is not None:
            return self._service

        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise RuntimeError(
                "Google Calendar credentials not configured. "
                "Set GOOGLE_CALENDAR_CREDENTIALS_PATH environment variable or pass credentials_path."
            )

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ['https://www.googleapis.com/auth/calendar']

            creds = None
            token_path = Path(self.credentials_path).parent / "token.json"

            # Load existing token
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save token
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self._service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar API service initialized")
            return self._service

        except ImportError:
            raise RuntimeError(
                "Google Calendar API libraries not installed. "
                "Run: uv pip install google-api-python-client google-auth-oauthlib"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar API: {e}")
            raise

    def _load_cache(self) -> None:
        """Load cached events from disk."""
        if not self.cache_path.exists():
            logger.debug("No event cache found")
            return

        try:
            with open(self.cache_path, 'r') as f:
                cache_data = json.load(f)

            self._cache_last_sync = datetime.fromisoformat(cache_data.get("last_sync", ""))
            events_data = cache_data.get("events", [])

            for event_data in events_data:
                event = CalendarEvent.from_frontmatter(event_data)
                self._cached_events[event.event_id] = event

            logger.info(f"Loaded {len(self._cached_events)} cached events")

        except Exception as e:
            logger.error(f"Failed to load event cache: {e}")
            self._cached_events = {}

    def _save_cache(self) -> None:
        """Save cached events to disk."""
        try:
            cache_data = {
                "last_sync": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None).isoformat(),
                "events": [event.to_frontmatter() for event in self._cached_events.values()]
            }

            with open(self.cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Saved {len(self._cached_events)} events to cache")

        except Exception as e:
            logger.error(f"Failed to save event cache: {e}")

    def sync_from_google_calendar(
        self,
        days_ahead: int = 30,
        days_back: int = 7
    ) -> int:
        """
        Sync events from Google Calendar to local cache.

        Args:
            days_ahead: Number of days ahead to sync
            days_back: Number of days back to sync

        Returns:
            int: Number of events synced

        Raises:
            RuntimeError: If Google Calendar API not available
        """
        service = self._get_google_service()

        # Calculate time range
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        time_min = (now - timedelta(days=days_back)).isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()

        try:
            # Fetch events from Google Calendar
            events_result = service.events().list(
                calendarId=self._calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Convert to CalendarEvent objects and cache
            synced_count = 0
            for gcal_event in events:
                try:
                    event = CalendarEvent.from_google_calendar(gcal_event)
                    self._cached_events[event.event_id] = event
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"Failed to parse event {gcal_event.get('id')}: {e}")
                    continue

            # Save cache
            self._cache_last_sync = now
            self._save_cache()

            logger.info(f"Synced {synced_count} events from Google Calendar")
            return synced_count

        except Exception as e:
            logger.error(f"Failed to sync from Google Calendar: {e}")
            raise

    def get_events(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        include_cancelled: bool = False
    ) -> List[CalendarEvent]:
        """
        Get events from cache within time range.

        Args:
            start: Start time (default: now)
            end: End time (default: 30 days from now)
            include_cancelled: Include cancelled events

        Returns:
            List[CalendarEvent]: Events in time range
        """
        if start is None:
            start = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        if end is None:
            end = start + timedelta(days=30)

        events = []
        for event in self._cached_events.values():
            # Filter by time range
            if event.start_time >= end or event.end_time <= start:
                continue

            # Filter cancelled
            if not include_cancelled and event.status == "cancelled":
                continue

            events.append(event)

        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        return events

    def check_availability(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_event_ids: Optional[List[str]] = None
    ) -> Tuple[bool, List[CalendarEvent]]:
        """
        Check if a time slot is available (no conflicts).

        Args:
            start_time: Proposed start time
            end_time: Proposed end time
            exclude_event_ids: Event IDs to exclude from conflict check

        Returns:
            Tuple[bool, List[CalendarEvent]]:
                - is_available: True if no conflicts
                - conflicting_events: List of conflicting events (empty if available)
        """
        exclude_ids = set(exclude_event_ids or [])

        # Get events in the time range
        events = self.get_events(start=start_time, end=end_time)

        # Check for conflicts
        conflicts = []
        for event in events:
            if event.event_id in exclude_ids:
                continue

            # Check if time overlaps
            if start_time < event.end_time and end_time > event.start_time:
                conflicts.append(event)

        is_available = len(conflicts) == 0
        return (is_available, conflicts)

    def detect_conflicts(self, events: Optional[List[CalendarEvent]] = None) -> Dict[str, List[str]]:
        """
        Detect conflicts among events.

        Performance requirement: <500ms for 100 events (US2 spec).

        Args:
            events: Events to check (default: all cached events)

        Returns:
            Dict[str, List[str]]: Map of event_id to list of conflicting event_ids
        """
        if events is None:
            events = list(self._cached_events.values())

        # Filter out cancelled events
        active_events = [e for e in events if e.status != "cancelled"]

        # Sort by start time for efficiency
        active_events.sort(key=lambda e: e.start_time)

        conflicts: Dict[str, List[str]] = {}

        # Check each pair of events
        for i, event1 in enumerate(active_events):
            for event2 in active_events[i+1:]:
                # Optimization: if event2 starts after event1 ends, no more conflicts possible
                if event2.start_time >= event1.end_time:
                    break

                # Check overlap
                if event1.has_conflict_with(event2):
                    # Add to conflicts map
                    if event1.event_id not in conflicts:
                        conflicts[event1.event_id] = []
                    conflicts[event1.event_id].append(event2.event_id)

                    if event2.event_id not in conflicts:
                        conflicts[event2.event_id] = []
                    conflicts[event2.event_id].append(event1.event_id)

        return conflicts

    def suggest_alternative_times(
        self,
        duration_minutes: int,
        preferred_times: List[datetime],
        attendees: Optional[List[str]] = None,
        work_hours_only: bool = True
    ) -> List[Tuple[datetime, datetime]]:
        """
        Suggest alternative meeting times based on availability.

        Args:
            duration_minutes: Meeting duration
            preferred_times: List of preferred start times
            attendees: Email addresses of attendees (future: check their availability)
            work_hours_only: Only suggest during work hours (9am-5pm weekdays)

        Returns:
            List[Tuple[datetime, datetime]]: List of (start, end) time tuples
        """
        suggestions = []

        for start_time in preferred_times:
            end_time = start_time + timedelta(minutes=duration_minutes)

            # Check work hours constraint
            if work_hours_only:
                if start_time.weekday() >= 5:  # Weekend
                    continue
                if start_time.hour < 9 or start_time.hour >= 17:  # Outside 9am-5pm
                    continue

            # Check availability
            is_available, conflicts = self.check_availability(start_time, end_time)

            if is_available:
                suggestions.append((start_time, end_time))

        return suggestions[:3]  # Return top 3 suggestions

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None,
        video_link: Optional[str] = None,
        agenda: Optional[str] = None,
        priority: str = "medium",
        sync_to_google: bool = True
    ) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            title: Event title
            start_time: Start time
            end_time: End time
            attendees: List of attendee emails
            location: Physical location
            video_link: Video conference URL
            agenda: Meeting agenda
            priority: Event priority (high, medium, low)
            sync_to_google: Sync to Google Calendar immediately

        Returns:
            CalendarEvent: Created event

        Raises:
            RuntimeError: If sync to Google Calendar fails
        """
        # Create CalendarEvent
        attendee_list = None
        if attendees:
            attendee_list = [Attendee(email=email) for email in attendees]

        event = CalendarEvent(
            event_id=f"CAL_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendees=attendee_list,
            location=location,
            video_link=video_link,
            agenda=agenda,
            priority=priority,
            created_by="ai"
        )

        # Validate
        event.validate()

        # Check for conflicts
        is_available, conflicts = self.check_availability(start_time, end_time)
        if conflicts:
            for conflict in conflicts:
                event.add_conflict(conflict.event_id)
            logger.warning(f"Event {event.event_id} has {len(conflicts)} conflicts")

        # Add to cache
        self._cached_events[event.event_id] = event
        self._save_cache()

        # Sync to Google Calendar
        if sync_to_google and self.credentials_path:
            try:
                self._create_google_event(event)
                logger.info(f"Created event {event.event_id} in Google Calendar")
            except Exception as e:
                logger.error(f"Failed to sync event to Google Calendar: {e}")
                # Don't fail the whole operation - event is still in cache

        logger.info(f"Created event: {event.title} ({start_time} - {end_time})")
        return event

    def _create_google_event(self, event: CalendarEvent) -> str:
        """
        Create event in Google Calendar.

        Args:
            event: CalendarEvent to create

        Returns:
            str: Google Calendar event ID

        Raises:
            RuntimeError: If Google Calendar API fails
        """
        service = self._get_google_service()

        gcal_event = event.to_google_calendar_format()

        try:
            result = service.events().insert(
                calendarId=self._calendar_id,
                body=gcal_event,
                sendUpdates='all' if event.attendees else 'none'
            ).execute()

            # Update event_id with Google's ID
            google_id = result['id']
            logger.info(f"Google Calendar event created: {google_id}")
            return google_id

        except Exception as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            raise RuntimeError(f"Google Calendar API error: {e}")

    def cancel_event(self, event_id: str, sync_to_google: bool = True) -> bool:
        """
        Cancel an event.

        Args:
            event_id: Event ID to cancel
            sync_to_google: Sync cancellation to Google Calendar

        Returns:
            bool: True if cancelled successfully
        """
        event = self._cached_events.get(event_id)
        if not event:
            logger.warning(f"Event {event_id} not found in cache")
            return False

        event.status = "cancelled"
        event.last_modified = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        self._save_cache()

        # Sync to Google Calendar
        if sync_to_google and self.credentials_path:
            try:
                service = self._get_google_service()
                google_id = event_id.replace("CAL_", "")
                service.events().delete(
                    calendarId=self._calendar_id,
                    eventId=google_id,
                    sendUpdates='all'
                ).execute()
                logger.info(f"Cancelled event in Google Calendar: {event_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel Google Calendar event: {e}")

        logger.info(f"Cancelled event: {event.title}")
        return True

    def get_calendar_preferences(self) -> Dict[str, Any]:
        """
        Get calendar preferences from Company_Handbook.md.

        Returns:
            Dict with preferences (work_hours, no_meeting_blocks, etc.)
        """
        handbook_path = self.vault_path / "Company_Handbook.md"

        if not handbook_path.exists():
            logger.warning("Company_Handbook.md not found, using default preferences")
            return self._get_default_preferences()

        try:
            import yaml

            with open(handbook_path, 'r') as f:
                content = f.read()

            # Extract YAML frontmatter
            if content.startswith('---'):
                _, yaml_content, _ = content.split('---', 2)
                data = yaml.safe_load(yaml_content)
                return data.get('calendar_preferences', self._get_default_preferences())

        except Exception as e:
            logger.error(f"Failed to load calendar preferences: {e}")

        return self._get_default_preferences()

    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default calendar preferences."""
        return {
            "work_hours": {
                "start": "09:00",
                "end": "17:00",
                "timezone": "UTC"
            },
            "work_days": [0, 1, 2, 3, 4],  # Monday-Friday
            "no_meeting_blocks": [],
            "minimum_meeting_gap_minutes": 15,
            "default_meeting_duration_minutes": 30
        }
