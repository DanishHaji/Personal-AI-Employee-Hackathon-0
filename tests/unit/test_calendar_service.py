"""
Unit Tests for CalendarService - Gold Tier US2

Tests calendar event management, conflict detection, and availability checking.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.models.calendar_event import CalendarEvent, Attendee
from src.services.calendar_service import CalendarService


class TestCalendarEvent:
    """Test CalendarEvent model."""

    def test_calendar_event_creation(self):
        """Test basic CalendarEvent creation and validation."""
        start = datetime(2026, 3, 15, 14, 0)
        end = datetime(2026, 3, 15, 15, 0)

        event = CalendarEvent(
            event_id="CAL_test123",
            title="Test Meeting",
            start_time=start,
            end_time=end,
            priority="high",
            created_by="ai"
        )

        assert event.validate()
        assert event.event_id == "CAL_test123"
        assert event.title == "Test Meeting"
        assert event.duration_minutes() == 60
        assert event.status == "confirmed"
        assert event.priority == "high"

    def test_event_validation_start_before_end(self):
        """Test that start_time must be before end_time."""
        start = datetime(2026, 3, 15, 15, 0)
        end = datetime(2026, 3, 15, 14, 0)  # End before start

        with pytest.raises(ValueError, match="start_time must be before end_time"):
            CalendarEvent(
                event_id="CAL_test123",
                title="Invalid Event",
                start_time=start,
                end_time=end
            )

    def test_event_priority_validation(self):
        """Test priority validation."""
        start = datetime(2026, 3, 15, 14, 0)
        end = datetime(2026, 3, 15, 15, 0)

        # Valid priorities
        for priority in ["high", "medium", "low"]:
            event = CalendarEvent(
                event_id=f"CAL_test_{priority}",
                title=f"{priority.capitalize()} Priority",
                start_time=start,
                end_time=end,
                priority=priority
            )
            assert event.validate()

        # Invalid priority
        with pytest.raises(ValueError, match="priority must be"):
            CalendarEvent(
                event_id="CAL_invalid",
                title="Invalid Priority",
                start_time=start,
                end_time=end,
                priority="critical"
            )

    def test_has_conflict_with(self):
        """Test conflict detection between two events."""
        # Event 1: 2pm-3pm
        event1 = CalendarEvent(
            event_id="CAL_event1",
            title="Event 1",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )

        # Event 2: 2:30pm-3:30pm (overlaps)
        event2 = CalendarEvent(
            event_id="CAL_event2",
            title="Event 2",
            start_time=datetime(2026, 3, 15, 14, 30),
            end_time=datetime(2026, 3, 15, 15, 30)
        )

        # Event 3: 3pm-4pm (no overlap, back-to-back)
        event3 = CalendarEvent(
            event_id="CAL_event3",
            title="Event 3",
            start_time=datetime(2026, 3, 15, 15, 0),
            end_time=datetime(2026, 3, 15, 16, 0)
        )

        # Event 4: 4pm-5pm (no overlap)
        event4 = CalendarEvent(
            event_id="CAL_event4",
            title="Event 4",
            start_time=datetime(2026, 3, 15, 16, 0),
            end_time=datetime(2026, 3, 15, 17, 0)
        )

        # Test conflicts
        assert event1.has_conflict_with(event2), "Should detect overlap"
        assert event2.has_conflict_with(event1), "Should detect overlap (symmetric)"
        assert not event1.has_conflict_with(event3), "Back-to-back should not conflict"
        assert not event1.has_conflict_with(event4), "Separate events should not conflict"

    def test_cancelled_events_no_conflict(self):
        """Test that cancelled events don't create conflicts."""
        event1 = CalendarEvent(
            event_id="CAL_event1",
            title="Event 1",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0),
            status="cancelled"
        )

        event2 = CalendarEvent(
            event_id="CAL_event2",
            title="Event 2",
            start_time=datetime(2026, 3, 15, 14, 30),
            end_time=datetime(2026, 3, 15, 15, 30)
        )

        assert not event1.has_conflict_with(event2), "Cancelled event should not conflict"
        assert not event2.has_conflict_with(event1), "Conflict with cancelled should not exist"

    def test_add_remove_conflict(self):
        """Test adding and removing conflict IDs."""
        event = CalendarEvent(
            event_id="CAL_event1",
            title="Event 1",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )

        assert len(event.conflicts) == 0

        # Add conflict
        event.add_conflict("CAL_event2")
        assert "CAL_event2" in event.conflicts
        assert len(event.conflicts) == 1

        # Add same conflict again (should not duplicate)
        event.add_conflict("CAL_event2")
        assert len(event.conflicts) == 1

        # Add another conflict
        event.add_conflict("CAL_event3")
        assert len(event.conflicts) == 2

        # Remove conflict
        event.remove_conflict("CAL_event2")
        assert "CAL_event2" not in event.conflicts
        assert len(event.conflicts) == 1

    def test_attendee_model(self):
        """Test Attendee model."""
        attendee = Attendee(
            email="alice@example.com",
            name="Alice Smith",
            response_status="accepted"
        )

        assert attendee.email == "alice@example.com"
        assert attendee.name == "Alice Smith"
        assert attendee.response_status == "accepted"

        # Test to_dict
        data = attendee.to_dict()
        assert data["email"] == "alice@example.com"
        assert data["name"] == "Alice Smith"
        assert data["response_status"] == "accepted"

        # Test from_dict
        attendee2 = Attendee.from_dict(data)
        assert attendee2.email == attendee.email
        assert attendee2.name == attendee.name


class TestCalendarService:
    """Test CalendarService operations."""

    @pytest.fixture
    def test_vault(self):
        """Create test vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            (vault_path / "Calendar").mkdir()
            yield vault_path

    @pytest.fixture
    def calendar_service(self, test_vault):
        """Create CalendarService instance."""
        return CalendarService(vault_path=test_vault)

    def test_service_initialization(self, test_vault):
        """Test CalendarService initialization."""
        service = CalendarService(vault_path=test_vault)

        assert service.vault_path == test_vault
        assert service.cache_path == test_vault / "Calendar" / "events.json"
        assert len(service._cached_events) == 0

    def test_check_availability_empty_calendar(self, calendar_service):
        """Test availability check with empty calendar."""
        start = datetime(2026, 3, 15, 14, 0)
        end = datetime(2026, 3, 15, 15, 0)

        is_available, conflicts = calendar_service.check_availability(start, end)

        assert is_available
        assert len(conflicts) == 0

    def test_check_availability_with_conflict(self, calendar_service):
        """Test availability check with conflicting event."""
        # Add event to cache
        existing_event = CalendarEvent(
            event_id="CAL_existing",
            title="Existing Meeting",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )
        calendar_service._cached_events["CAL_existing"] = existing_event

        # Check overlapping time
        start = datetime(2026, 3, 15, 14, 30)
        end = datetime(2026, 3, 15, 15, 30)

        is_available, conflicts = calendar_service.check_availability(start, end)

        assert not is_available
        assert len(conflicts) == 1
        assert conflicts[0].event_id == "CAL_existing"

    def test_check_availability_exclude_events(self, calendar_service):
        """Test availability check with excluded events."""
        # Add event to cache
        existing_event = CalendarEvent(
            event_id="CAL_existing",
            title="Existing Meeting",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )
        calendar_service._cached_events["CAL_existing"] = existing_event

        # Check same time but exclude the event
        start = datetime(2026, 3, 15, 14, 30)
        end = datetime(2026, 3, 15, 15, 30)

        is_available, conflicts = calendar_service.check_availability(
            start, end, exclude_event_ids=["CAL_existing"]
        )

        assert is_available
        assert len(conflicts) == 0

    def test_detect_conflicts_performance(self, calendar_service):
        """
        Test conflict detection performance.

        Requirement: <500ms for 100 events (US2 spec).
        """
        import time

        # Create 100 events with some overlaps
        events = []
        base_date = datetime(2026, 3, 1, 9, 0)

        for i in range(100):
            # Create events throughout the month
            day_offset = i // 10
            hour_offset = (i % 10)

            start = base_date + timedelta(days=day_offset, hours=hour_offset)
            end = start + timedelta(hours=1)

            event = CalendarEvent(
                event_id=f"CAL_event_{i}",
                title=f"Event {i}",
                start_time=start,
                end_time=end
            )
            events.append(event)
            calendar_service._cached_events[event.event_id] = event

        # Measure conflict detection time
        start_time = time.time()
        conflicts = calendar_service.detect_conflicts()
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Conflict detection for 100 events: {elapsed_ms:.2f}ms")

        # Should complete in <500ms
        assert elapsed_ms < 500, f"Conflict detection too slow: {elapsed_ms}ms"

    def test_detect_conflicts_accuracy(self, calendar_service):
        """Test conflict detection accuracy."""
        # Event 1: 2pm-3pm
        event1 = CalendarEvent(
            event_id="CAL_event1",
            title="Event 1",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )

        # Event 2: 2:30pm-3:30pm (overlaps with event1)
        event2 = CalendarEvent(
            event_id="CAL_event2",
            title="Event 2",
            start_time=datetime(2026, 3, 15, 14, 30),
            end_time=datetime(2026, 3, 15, 15, 30)
        )

        # Event 3: 3:15pm-4:15pm (overlaps with event2)
        event3 = CalendarEvent(
            event_id="CAL_event3",
            title="Event 3",
            start_time=datetime(2026, 3, 15, 15, 15),
            end_time=datetime(2026, 3, 15, 16, 15)
        )

        # Event 4: 2:45pm-3:15pm (overlaps with event1 and event2)
        event4 = CalendarEvent(
            event_id="CAL_event4",
            title="Event 4",
            start_time=datetime(2026, 3, 15, 14, 45),
            end_time=datetime(2026, 3, 15, 15, 15)
        )

        events = [event1, event2, event3, event4]
        for event in events:
            calendar_service._cached_events[event.event_id] = event

        # Detect conflicts
        conflicts = calendar_service.detect_conflicts()

        # Verify conflicts
        assert "CAL_event1" in conflicts
        assert "CAL_event2" in conflicts["CAL_event1"]
        assert "CAL_event4" in conflicts["CAL_event1"]

        assert "CAL_event2" in conflicts
        assert "CAL_event1" in conflicts["CAL_event2"]
        assert "CAL_event4" in conflicts["CAL_event2"]
        assert "CAL_event3" in conflicts["CAL_event2"]  # Event3 overlaps with event2

        assert "CAL_event3" in conflicts
        assert "CAL_event2" in conflicts["CAL_event3"]  # Only conflicts with event2

        assert "CAL_event4" in conflicts
        assert len(conflicts["CAL_event4"]) == 2  # Conflicts with event1 and event2

    def test_create_event(self, calendar_service):
        """Test event creation."""
        event = calendar_service.create_event(
            title="Team Sync",
            start_time=datetime(2026, 3, 15, 10, 0),
            end_time=datetime(2026, 3, 15, 10, 30),
            attendees=["alice@example.com", "bob@example.com"],
            priority="medium",
            sync_to_google=False  # Don't sync to Google in tests
        )

        assert event.title == "Team Sync"
        assert event.created_by == "ai"
        assert len(event.attendees) == 2
        assert event.attendees[0].email == "alice@example.com"

        # Verify event is in cache
        assert event.event_id in calendar_service._cached_events

    def test_create_event_with_conflict(self, calendar_service):
        """Test event creation detects conflicts."""
        # Create first event
        event1 = calendar_service.create_event(
            title="Meeting 1",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0),
            sync_to_google=False
        )

        # Create conflicting event
        event2 = calendar_service.create_event(
            title="Meeting 2",
            start_time=datetime(2026, 3, 15, 14, 30),
            end_time=datetime(2026, 3, 15, 15, 30),
            sync_to_google=False
        )

        # Verify conflict is tracked
        assert len(event2.conflicts) == 1
        assert event1.event_id in event2.conflicts

    def test_cancel_event(self, calendar_service):
        """Test event cancellation."""
        # Create event
        event = calendar_service.create_event(
            title="Meeting to Cancel",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0),
            sync_to_google=False
        )

        # Cancel event
        success = calendar_service.cancel_event(event.event_id, sync_to_google=False)

        assert success
        assert event.status == "cancelled"

    def test_suggest_alternative_times(self, calendar_service):
        """Test alternative time suggestions."""
        # Add existing event: 2pm-3pm
        existing = CalendarEvent(
            event_id="CAL_existing",
            title="Existing Meeting",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )
        calendar_service._cached_events["CAL_existing"] = existing

        # Request suggestions for 1-hour meeting
        # Include some conflicting times and some available times
        preferred_times = [
            datetime(2026, 3, 15, 14, 30),  # Conflicts (overlaps with existing 2pm-3pm event)
            datetime(2026, 3, 15, 15, 0),   # Available (Saturday, outside work hours, will be filtered)
            datetime(2026, 3, 16, 10, 0),   # Available (Monday, within work hours)
            datetime(2026, 3, 16, 11, 0),   # Available (Monday, within work hours)
            datetime(2026, 3, 16, 13, 0),   # Available (Monday, within work hours)
        ]

        suggestions = calendar_service.suggest_alternative_times(
            duration_minutes=60,
            preferred_times=preferred_times,
            work_hours_only=True
        )

        # Should return available times only (max 3)
        assert len(suggestions) <= 3
        assert len(suggestions) >= 2  # At least 2 available times

        # Verify no conflicts in suggestions
        for start, end in suggestions:
            is_available, _ = calendar_service.check_availability(start, end)
            assert is_available

    def test_get_events_time_range(self, calendar_service):
        """Test querying events by time range."""
        # Create events
        event1 = CalendarEvent(
            event_id="CAL_event1",
            title="Event 1",
            start_time=datetime(2026, 3, 15, 10, 0),
            end_time=datetime(2026, 3, 15, 11, 0)
        )

        event2 = CalendarEvent(
            event_id="CAL_event2",
            title="Event 2",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0)
        )

        event3 = CalendarEvent(
            event_id="CAL_event3",
            title="Event 3",
            start_time=datetime(2026, 3, 16, 10, 0),
            end_time=datetime(2026, 3, 16, 11, 0)
        )

        for event in [event1, event2, event3]:
            calendar_service._cached_events[event.event_id] = event

        # Query events on March 15
        events = calendar_service.get_events(
            start=datetime(2026, 3, 15, 0, 0),
            end=datetime(2026, 3, 16, 0, 0)
        )

        # Should get events 1 and 2
        assert len(events) == 2
        assert events[0].event_id == "CAL_event1"
        assert events[1].event_id == "CAL_event2"

    def test_cache_persistence(self, test_vault):
        """Test that event cache persists across service instances."""
        # Create service and add event
        service1 = CalendarService(vault_path=test_vault)
        event = service1.create_event(
            title="Persistent Event",
            start_time=datetime(2026, 3, 15, 14, 0),
            end_time=datetime(2026, 3, 15, 15, 0),
            sync_to_google=False
        )

        # Create new service instance (should load from cache)
        service2 = CalendarService(vault_path=test_vault)

        # Verify event was loaded from cache
        assert event.event_id in service2._cached_events
        cached_event = service2._cached_events[event.event_id]
        assert cached_event.title == "Persistent Event"
