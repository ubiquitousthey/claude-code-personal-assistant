#!/usr/bin/env python3
"""
PCO Reminder Sync

Syncs Planning Center data to Apple Reminders:
- Service schedules (day-before alerts)
- Shepherding follow-ups with smart questions
"""

import os
import json
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import Optional

from pco_client import PCOClient
from followup_manager import FollowupManager

# Configuration
REMINDER_LIST = "Reminders"  # Target Apple Reminders list


@dataclass
class ReminderData:
    """Data for creating a reminder."""
    title: str
    due_date: str  # Format: YYYY-MM-DD HH:mm:ss
    note: str
    list_name: str = REMINDER_LIST
    pco_reference: str = ""  # For deduplication


class ReminderSync:
    """Generates reminder data from PCO sources."""

    def __init__(self):
        self.pco_client = PCOClient()
        self.followup_manager = FollowupManager()

    def generate_service_reminders(self, days_ahead: int = 30) -> list[ReminderData]:
        """
        Generate reminders for upcoming service schedules.

        Creates reminder for day before each service.
        """
        schedules = self.pco_client.get_my_schedules(days_ahead=days_ahead)
        reminders = []

        for schedule in schedules:
            if not schedule.plan_date:
                continue

            # Create reminder for day before
            reminder_date = schedule.plan_date - timedelta(days=1)

            # Skip if reminder date is in the past
            if reminder_date < date.today():
                continue

            # Format time (remind at 7 PM day before)
            due_datetime = f"{reminder_date.isoformat()} 19:00:00"

            note = f"""Service: {schedule.service_type}
Team: {schedule.team_name}
Position: {schedule.position}
Date: {schedule.plan_date}
Status: {schedule.status}

PCO Reference: schedule_{schedule.schedule_id}"""

            reminders.append(ReminderData(
                title=f"⛪ Service Tomorrow: {schedule.team_name} - {schedule.position}",
                due_date=due_datetime,
                note=note,
                pco_reference=f"schedule_{schedule.schedule_id}"
            ))

        return reminders

    def generate_followup_reminders(self) -> list[ReminderData]:
        """
        Generate reminders for today's follow-up contacts.

        Includes smart questions based on history and theme.
        """
        followups = self.followup_manager.get_todays_followups()
        reminders = []

        for f in followups:
            # Format due time (remind at 9 AM)
            due_datetime = f"{date.today().isoformat()} 09:00:00"

            # Build note with all the context
            note_lines = [
                f"Household: {f['household']}",
                f"Phone: {f['phone'] or 'N/A'}",
                f"Email: {f['email'] or 'N/A'}",
                "",
                f"Theme: {f['theme']}",
            ]

            if f['theme_questions']:
                note_lines.append("\nTheme Questions:")
                for q in f['theme_questions']:
                    note_lines.append(f"  • {q}")

            if f['history_questions']:
                note_lines.append("\nFrom Previous Contact:")
                for q in f['history_questions']:
                    note_lines.append(f"  • {q}")

            if f['is_overdue']:
                note_lines.insert(0, f"⚠️ OVERDUE by {f['days_overdue']} days\n")

            note_lines.append(f"\nPCO Reference: followup_{f['person_name'].replace(' ', '_')}_{f['assigned_date']}")

            title_prefix = "⚠️ " if f['is_overdue'] else "📞 "
            reminders.append(ReminderData(
                title=f"{title_prefix}Follow up: {f['person_name']}",
                due_date=due_datetime,
                note="\n".join(note_lines),
                pco_reference=f"followup_{f['person_name'].replace(' ', '_')}_{f['assigned_date']}"
            ))

        return reminders

    def generate_all_reminders(self) -> dict:
        """Generate all reminders and return structured data."""
        service_reminders = self.generate_service_reminders()
        followup_reminders = self.generate_followup_reminders()

        return {
            "service_reminders": [
                {
                    "title": r.title,
                    "due_date": r.due_date,
                    "note": r.note,
                    "list": r.list_name,
                    "reference": r.pco_reference
                }
                for r in service_reminders
            ],
            "followup_reminders": [
                {
                    "title": r.title,
                    "due_date": r.due_date,
                    "note": r.note,
                    "list": r.list_name,
                    "reference": r.pco_reference
                }
                for r in followup_reminders
            ],
            "summary": {
                "service_count": len(service_reminders),
                "followup_count": len(followup_reminders),
                "total": len(service_reminders) + len(followup_reminders)
            }
        }

    def format_for_display(self) -> str:
        """Format reminders for display."""
        data = self.generate_all_reminders()
        lines = []

        lines.append(f"=== Reminder Sync Summary ===")
        lines.append(f"Service Reminders: {data['summary']['service_count']}")
        lines.append(f"Follow-up Reminders: {data['summary']['followup_count']}")
        lines.append("")

        if data['service_reminders']:
            lines.append("📅 SERVICE REMINDERS:")
            for r in data['service_reminders']:
                lines.append(f"  • {r['title']}")
                lines.append(f"    Due: {r['due_date']}")
            lines.append("")

        if data['followup_reminders']:
            lines.append("📞 FOLLOW-UP REMINDERS:")
            for r in data['followup_reminders']:
                lines.append(f"  • {r['title']}")
                lines.append(f"    Due: {r['due_date']}")

        return "\n".join(lines)


def main():
    """CLI interface for reminder sync."""
    import sys

    sync = ReminderSync()

    if len(sys.argv) < 2:
        print("Usage: pco_sync_reminders.py <command>")
        print("\nCommands:")
        print("  preview    - Preview reminders that would be created")
        print("  json       - Output reminder data as JSON")
        print("  services   - Preview service reminders only")
        print("  followups  - Preview follow-up reminders only")
        return

    cmd = sys.argv[1]

    if cmd == "preview":
        print(sync.format_for_display())

    elif cmd == "json":
        data = sync.generate_all_reminders()
        print(json.dumps(data, indent=2))

    elif cmd == "services":
        reminders = sync.generate_service_reminders()
        print(f"Service Reminders ({len(reminders)}):\n")
        for r in reminders:
            print(f"Title: {r.title}")
            print(f"Due: {r.due_date}")
            print(f"Note:\n{r.note}")
            print("\n" + "=" * 40 + "\n")

    elif cmd == "followups":
        reminders = sync.generate_followup_reminders()
        print(f"Follow-up Reminders ({len(reminders)}):\n")
        for r in reminders:
            print(f"Title: {r.title}")
            print(f"Due: {r.due_date}")
            print(f"Note:\n{r.note}")
            print("\n" + "=" * 40 + "\n")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
