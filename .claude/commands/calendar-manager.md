# Calendar Manager Agent Skill

**Purpose**: Autonomous Google Calendar management with conflict detection, meeting scheduling, and availability checking.

**Gold Tier US2**: Calendar & Meeting Management

## Capabilities

This agent skill provides autonomous calendar management capabilities:

1. **Sync Events**: Sync events from Google Calendar to local cache
2. **Check Availability**: Check if time slots are available
3. **Schedule Meetings**: Create calendar events with conflict detection
4. **Detect Conflicts**: Find overlapping events and suggest alternatives
5. **Manage Events**: Update, cancel, or reschedule events
6. **Calendar Preferences**: View and update work hours, no-meeting blocks

## Usage

### Sync Calendar Events

```
Sync the next 30 days of calendar events from Google Calendar.
```

**What it does**:
- Connects to Google Calendar API
- Downloads events from the specified time range
- Updates local cache in `/Calendar/events.json`
- Reports number of events synced

### Check Availability

```
Check if I'm available tomorrow at 2pm for a 1-hour meeting.
```

**What it does**:
- Queries local calendar cache
- Checks for conflicts in the specified time slot
- Returns availability status and any conflicting events

### Schedule Meeting

```
Schedule a meeting titled "Q2 Planning" for next Monday at 10am for 1 hour with alice@company.com and bob@company.com.
```

**What it does**:
- Creates CalendarEvent with specified details
- Checks for conflicts
- If available: Creates event and syncs to Google Calendar
- If conflicts: Suggests 3 alternative times
- Sends calendar invites to attendees

### Find Alternative Times

```
I need to schedule a 30-minute meeting with the team. Suggest 3 available times this week.
```

**What it does**:
- Analyzes calendar availability
- Respects work hours preferences (9am-5pm weekdays by default)
- Suggests 3 available time slots
- Considers minimum meeting gap (15 minutes default)

### Detect Conflicts

```
Check my calendar for any scheduling conflicts this week.
```

**What it does**:
- Scans all events in the time range
- Detects overlapping events
- Reports conflicts with event details
- Suggests resolutions (cancel, reschedule, or accept double-booking)

### Cancel Meeting

```
Cancel the "Q2 Planning" meeting scheduled for Monday.
```

**What it does**:
- Finds the event by title or ID
- Marks event as cancelled
- Syncs cancellation to Google Calendar
- Sends cancellation notices to attendees

### View Calendar Preferences

```
Show my calendar preferences.
```

**What it does**:
- Loads preferences from Company_Handbook.md
- Displays work hours, work days, no-meeting blocks
- Shows minimum meeting gap and default meeting duration

## Calendar Preferences Configuration

Edit `Company_Handbook.md` YAML frontmatter to configure calendar preferences:

```yaml
calendar_preferences:
  work_hours:
    start: "09:00"
    end: "17:00"
    timezone: "America/Los_Angeles"
  work_days: [0, 1, 2, 3, 4]  # Monday=0, Sunday=6
  no_meeting_blocks:
    - day: 2  # Wednesday
      start: "14:00"
      end: "16:00"
      reason: "Focus time"
  minimum_meeting_gap_minutes: 15
  default_meeting_duration_minutes: 30
```

## Trust Framework Integration

Calendar operations can be auto-approved based on trust rules:

**Example Trust Rules**:

```yaml
trust_rules:
  - rule_id: RULE_auto_schedule_team_sync
    rule_name: "Auto-schedule Team Sync Meetings"
    action_type: calendar_create
    trust_level: 1  # Auto-approve
    contact_filter: ["@company.com"]
    content_pattern: "Team Sync|Standup|Daily Meeting"
    enabled: true

  - rule_id: RULE_small_meetings
    rule_name: "Small Internal Meetings"
    action_type: calendar_create
    trust_level: 1
    contact_filter: ["@company.com"]
    max_value: 4  # Max 4 attendees (using max_value as attendee count)
    enabled: true
```

**Auto-Approval Criteria**:
- Meeting title matches `content_pattern` (if specified)
- All attendees match `contact_filter` (if specified)
- Attendee count ≤ `max_value` (if specified)
- No conflicts with existing high-priority meetings

**When Trust Rule Matches**:
- Event created automatically without HITL approval
- Calendar invite sent immediately
- Action logged in audit trail with `trust_rule_id`

**When Trust Rule Doesn't Match**:
- Event plan created in `/Pending_Approval/`
- User reviews event details before creation
- User can approve, modify, or reject

## Examples

### Example 1: Schedule with Conflict Detection

**User**: "Schedule a 1-hour meeting with Alice tomorrow at 2pm to discuss the Q2 budget."

**Agent Actions**:
1. Check availability for tomorrow 2pm-3pm
2. Find conflict: "Team Meeting" already scheduled 2pm-3pm
3. Suggest alternatives:
   - Tomorrow 3:30pm-4:30pm (Available)
   - Tomorrow 4pm-5pm (Available)
   - Day after tomorrow 2pm-3pm (Available)
4. Create plan in `/Pending_Approval/` with suggested times
5. Wait for user selection

### Example 2: Auto-Schedule Trusted Meeting

**User**: "Schedule our weekly team sync for next Monday 10am."

**Trust Rule Match**: RULE_auto_schedule_team_sync
- Title contains "team sync"
- Duration: 30 minutes (default)
- No conflicts detected

**Agent Actions**:
1. Evaluate trust: RULE_auto_schedule_team_sync matches
2. Create calendar event immediately (no approval needed)
3. Send Google Calendar invites
4. Log action with `trust_rule_id: RULE_auto_schedule_team_sync`
5. Notify user: "✅ Team sync scheduled for Monday 10am"

### Example 3: Resolve Double-Booking

**User**: "I have two meetings at 3pm today. What should I do?"

**Agent Actions**:
1. Detect conflict between "Client Call" (high priority) and "Internal Review" (medium priority)
2. Recommend: Reschedule "Internal Review" (lower priority)
3. Suggest 3 alternative times for "Internal Review"
4. Create plan: Cancel or reschedule the lower-priority meeting
5. Wait for approval

## Google Calendar Setup

**Prerequisites**:
1. Google Cloud Project with Calendar API enabled
2. OAuth 2.0 credentials downloaded
3. Environment variable: `GOOGLE_CALENDAR_CREDENTIALS_PATH=/path/to/credentials.json`

**First-Time Setup**:
1. Run calendar sync command
2. Browser opens for Google OAuth consent
3. Grant calendar access permissions
4. Token saved to `token.json` for future use
5. Events synced to local cache

## Performance

- **Conflict Detection**: <500ms for 100 events (optimized sorting algorithm)
- **Availability Check**: <50ms (local cache query)
- **Event Creation**: ~1-2 seconds (includes Google Calendar API call)
- **Cache Sync**: ~2-5 seconds for 30 days of events

## Error Handling

**Google Calendar API Unavailable**:
- Falls back to local cache for queries
- Event creation queued for later sync
- Warning logged, user notified

**OAuth Token Expired**:
- Automatic token refresh attempted
- If refresh fails, user prompted to re-authenticate
- Cached events remain available

**Scheduling Conflict**:
- Never auto-approve if conflicts exist
- Always surface conflicts to user
- Provide alternative time suggestions

## Audit Trail

All calendar operations are logged:
- Event creation, modification, cancellation
- Trust rule matches (auto-approved actions)
- Conflict detections and resolutions
- Sync operations and API calls

**Audit Log Fields**:
```json
{
  "timestamp": "2026-03-01T14:30:00Z",
  "action_type": "calendar_create",
  "event_id": "CAL_20260301143000",
  "event_title": "Team Sync",
  "start_time": "2026-03-03T10:00:00-07:00",
  "end_time": "2026-03-03T10:30:00-07:00",
  "attendees": ["alice@company.com", "bob@company.com"],
  "conflicts": [],
  "trust_rule_id": "RULE_auto_schedule_team_sync",
  "approved_by": "trust_rule",
  "synced_to_google": true
}
```

## Troubleshooting

**"Google Calendar credentials not configured"**:
- Set `GOOGLE_CALENDAR_CREDENTIALS_PATH` environment variable
- Download OAuth credentials from Google Cloud Console

**"No events found in cache"**:
- Run calendar sync first: "Sync my calendar events"
- Check Google Calendar has events in the date range

**"Conflict detection slow"**:
- Cache has >500 events, consider reducing sync range
- Run conflict detection during off-peak hours

**"Trust rule not matching expected events"**:
- Check `contact_filter` includes all attendee domains
- Verify `content_pattern` regex matches event title
- Review trust rule in Company_Handbook.md

## Best Practices

1. **Sync Regularly**: Run hourly background sync to keep cache current
2. **Set Preferences**: Configure work hours to avoid scheduling outside working time
3. **Use Trust Rules**: Auto-approve routine meetings to reduce approval friction
4. **Review Conflicts**: Weekly conflict scan prevents double-booking issues
5. **Monitor Audit Logs**: Review auto-approved events for trust rule accuracy

## Related Skills

- `/trust-evaluator` - Manage trust rules for auto-approval
- `/document-generator` - Generate meeting agendas from templates
- `/analytics-insights` - Analyze meeting patterns and time usage

## Files

- `src/services/calendar_service.py` - Calendar service implementation
- `src/models/calendar_event.py` - CalendarEvent model
- `/Calendar/events.json` - Local event cache
- `Company_Handbook.md` - Calendar preferences configuration
- `.env` - Google Calendar credentials path

## API Reference

See `src/services/calendar_service.py` for full API documentation.
