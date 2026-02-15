#!/usr/bin/env python3
"""
Calendar Sync

Fetches ICS calendar feeds and caches them locally for quick access.
Parses events and provides agenda views.
"""

import os
import json
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from zoneinfo import ZoneInfo
from icalendar import Calendar
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Local timezone (Heath is in Central Time)
LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TIMEZONE", "America/Chicago"))

# Calendar URLs
WORK_CALENDAR_URL = os.getenv(
    "WORK_CALENDAR_ICS",
    "https://outlook.office365.com/owa/calendar/2aae6d2a45e54b0b837b48325aedbc35@zeiss.com/e90e4d4c4bc64bf3933d2d60d7cbf61015883374241815795953/calendar.ics"
)
PERSONAL_CALENDAR_URL = os.getenv("PERSONAL_CALENDAR_ICS", "")

# Cache location
CACHE_DIR = Path("/workspace/cache/calendar")
WORK_CACHE = CACHE_DIR / "work_calendar.json"
PERSONAL_CACHE = CACHE_DIR / "personal_calendar.json"
LAST_SYNC_FILE = CACHE_DIR / "last_sync.json"


@dataclass
class CalendarEvent:
    """Parsed calendar event."""
    title: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    all_day: bool = False
    calendar: str = "work"
    uid: str = ""


def fetch_ics_calendar(url: str) -> Optional[str]:
    """Fetch ICS content from URL."""
    if not url:
        return None

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch calendar: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return None


def parse_ics_events(ics_content: str, calendar_name: str = "work") -> list[CalendarEvent]:
    """Parse ICS content into event objects."""
    events = []

    try:
        cal = Calendar.from_ical(ics_content)

        for component in cal.walk():
            if component.name == "VEVENT":
                # Get start/end times
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")

                if not dtstart:
                    continue

                start_dt = dtstart.dt
                end_dt = dtend.dt if dtend else start_dt

                # Check if all-day event
                all_day = not isinstance(start_dt, datetime)

                # Convert date to datetime if needed
                if all_day:
                    start_dt = datetime.combine(start_dt, datetime.min.time())
                    end_dt = datetime.combine(end_dt, datetime.min.time())

                # Convert to local timezone, then make naive for JSON serialization
                if hasattr(start_dt, 'tzinfo') and start_dt.tzinfo:
                    start_dt = start_dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
                if hasattr(end_dt, 'tzinfo') and end_dt.tzinfo:
                    end_dt = end_dt.astimezone(LOCAL_TZ).replace(tzinfo=None)

                events.append(CalendarEvent(
                    title=str(component.get("summary", "No Title")),
                    start=start_dt,
                    end=end_dt,
                    location=str(component.get("location", "")) or None,
                    description=str(component.get("description", ""))[:500] or None,
                    all_day=all_day,
                    calendar=calendar_name,
                    uid=str(component.get("uid", ""))
                ))

    except Exception as e:
        print(f"Error parsing ICS: {e}")

    return events


def save_events_cache(events: list[CalendarEvent], cache_file: Path):
    """Save events to cache file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to JSON-serializable format
    data = []
    for event in events:
        d = asdict(event)
        d["start"] = event.start.isoformat()
        d["end"] = event.end.isoformat()
        data.append(d)

    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2)


def load_events_cache(cache_file: Path) -> list[CalendarEvent]:
    """Load events from cache file."""
    if not cache_file.exists():
        return []

    with open(cache_file) as f:
        data = json.load(f)

    events = []
    for d in data:
        d["start"] = datetime.fromisoformat(d["start"])
        d["end"] = datetime.fromisoformat(d["end"])
        events.append(CalendarEvent(**d))

    return events


def sync_calendars():
    """Sync all configured calendars."""
    print(f"🔄 Syncing calendars at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Work calendar
    if WORK_CALENDAR_URL:
        print("  Fetching work calendar...")
        ics = fetch_ics_calendar(WORK_CALENDAR_URL)
        if ics:
            events = parse_ics_events(ics, "work")
            save_events_cache(events, WORK_CACHE)
            print(f"  ✅ Work calendar: {len(events)} events cached")

    # Personal calendar
    if PERSONAL_CALENDAR_URL:
        print("  Fetching personal calendar...")
        ics = fetch_ics_calendar(PERSONAL_CALENDAR_URL)
        if ics:
            events = parse_ics_events(ics, "personal")
            save_events_cache(events, PERSONAL_CACHE)
            print(f"  ✅ Personal calendar: {len(events)} events cached")

    # Update last sync time
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LAST_SYNC_FILE, "w") as f:
        json.dump({"last_sync": datetime.now().isoformat()}, f)


def get_events_for_date(target_date: date) -> list[CalendarEvent]:
    """Get all events for a specific date."""
    events = []

    # Load from cache
    events.extend(load_events_cache(WORK_CACHE))
    events.extend(load_events_cache(PERSONAL_CACHE))

    # Filter to target date
    target_start = datetime.combine(target_date, datetime.min.time())
    target_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    filtered = [
        e for e in events
        if e.start < target_end and e.end > target_start
    ]

    # Sort by start time
    filtered.sort(key=lambda e: e.start)

    return filtered


def get_agenda(days: int = 7) -> dict:
    """Get agenda for the next N days."""
    agenda = {}
    today = date.today()

    for i in range(days):
        target = today + timedelta(days=i)
        events = get_events_for_date(target)
        if events:
            agenda[target.isoformat()] = [
                {
                    "time": e.start.strftime("%H:%M") if not e.all_day else "All Day",
                    "title": e.title,
                    "location": e.location,
                    "calendar": e.calendar
                }
                for e in events
            ]

    return agenda


def format_today_agenda() -> str:
    """Format today's agenda for display."""
    events = get_events_for_date(date.today())

    if not events:
        return "No events scheduled for today."

    lines = [f"📅 Today's Agenda ({date.today().strftime('%A, %B %d')}):\n"]

    for e in events:
        time_str = e.start.strftime("%H:%M") if not e.all_day else "All Day"
        cal_icon = "💼" if e.calendar == "work" else "🏠"
        lines.append(f"  {cal_icon} {time_str} - {e.title}")
        if e.location:
            lines.append(f"      📍 {e.location}")

    return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Calendar Sync")
        print("\nUsage: calendar_sync.py <command>")
        print("\nCommands:")
        print("  sync     - Fetch and cache calendars")
        print("  today    - Show today's agenda")
        print("  week     - Show week agenda")
        print("  status   - Show sync status")
        return

    cmd = sys.argv[1]

    if cmd == "sync":
        sync_calendars()

    elif cmd == "today":
        print(format_today_agenda())

    elif cmd == "week":
        agenda = get_agenda(7)
        if not agenda:
            print("No events in the next 7 days.")
        else:
            for day, events in agenda.items():
                day_date = date.fromisoformat(day)
                print(f"\n{day_date.strftime('%A, %B %d')}:")
                for e in events:
                    cal_icon = "💼" if e["calendar"] == "work" else "🏠"
                    print(f"  {cal_icon} {e['time']} - {e['title']}")

    elif cmd == "status":
        if LAST_SYNC_FILE.exists():
            with open(LAST_SYNC_FILE) as f:
                data = json.load(f)
            last_sync = datetime.fromisoformat(data["last_sync"])
            print(f"Last sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")

            work_events = load_events_cache(WORK_CACHE)
            personal_events = load_events_cache(PERSONAL_CACHE)
            print(f"Work events cached: {len(work_events)}")
            print(f"Personal events cached: {len(personal_events)}")
        else:
            print("Calendar not synced yet. Run: calendar_sync.py sync")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
