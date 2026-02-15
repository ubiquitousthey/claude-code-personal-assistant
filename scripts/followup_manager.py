#!/usr/bin/env python3
"""
Shepherding Follow-up Manager

Manages monthly follow-up distribution for shepherding contacts.
- Distributes one adult per household across the month
- Tracks completion and re-surfaces incomplete follow-ups
- Integrates monthly themes with smart questions
"""

import os
import json
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

from pco_client import PCOClient, Person, Household
from pco_notion_sync import NotionCRM

# Configuration
FOLLOWUP_DATA_FILE = Path("/workspace/data/followup_state.json")
FOLLOWUP_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# Monthly themes configuration
MONTHLY_THEMES = {
    "2026-02": {
        "name": "Spiritual Growth at Home",
        "questions": [
            "How is your family's spiritual rhythm going?",
            "Have you been able to do family worship or devotions?",
            "What's been encouraging in your walk with God lately?",
            "Any prayer requests for your household?"
        ]
    },
    "2026-03": {
        "name": "Community & Relationships",
        "questions": [
            "How connected do you feel to others in the church?",
            "Have you been able to build any new relationships?",
            "Is there anyone you'd like to get to know better?",
            "How can we help you feel more connected?"
        ]
    },
    "2026-04": {
        "name": "Serving & Using Gifts",
        "questions": [
            "How have you been able to serve others recently?",
            "What gifts do you feel God has given you?",
            "Is there a ministry area you'd like to explore?",
            "How can we help you find ways to serve?"
        ]
    }
}


@dataclass
class FollowupAssignment:
    """A follow-up assignment for a person."""
    person_id: str
    person_name: str
    household_id: str
    household_name: str
    phone: Optional[str]
    email: Optional[str]
    assigned_date: str  # ISO format
    completed: bool = False
    completed_date: Optional[str] = None
    last_reminder_date: Optional[str] = None
    notes: str = ""


@dataclass
class MonthlyFollowupState:
    """State for a month's follow-up assignments."""
    month: str  # Format: YYYY-MM
    theme: str
    assignments: list[FollowupAssignment] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class FollowupManager:
    """Manages monthly follow-up assignments and tracking."""

    def __init__(self):
        self.pco_client = PCOClient()
        self.notion_crm = NotionCRM()
        self.state = self._load_state()

    def _load_state(self) -> dict[str, MonthlyFollowupState]:
        """Load follow-up state from file."""
        if FOLLOWUP_DATA_FILE.exists():
            try:
                with open(FOLLOWUP_DATA_FILE) as f:
                    data = json.load(f)
                    return {
                        month: MonthlyFollowupState(
                            month=state["month"],
                            theme=state["theme"],
                            assignments=[FollowupAssignment(**a) for a in state["assignments"]],
                            created_at=state.get("created_at", "")
                        )
                        for month, state in data.items()
                    }
            except Exception as e:
                print(f"Error loading state: {e}")
        return {}

    def _save_state(self):
        """Save follow-up state to file."""
        data = {
            month: {
                "month": state.month,
                "theme": state.theme,
                "assignments": [asdict(a) for a in state.assignments],
                "created_at": state.created_at
            }
            for month, state in self.state.items()
        }
        with open(FOLLOWUP_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _get_working_days(self, year: int, month: int) -> list[date]:
        """Get working days in a month (exclude Sundays)."""
        days = []
        d = date(year, month, 1)
        while d.month == month:
            if d.weekday() != 6:  # Not Sunday
                days.append(d)
            d += timedelta(days=1)
        return days

    def _group_by_household(self, people: list[Person]) -> dict[str, list[Person]]:
        """Group people by household."""
        households = {}
        for person in people:
            if person.household_id:
                if person.household_id not in households:
                    households[person.household_id] = []
                households[person.household_id].append(person)
        return households

    def generate_monthly_assignments(self, year: int, month: int, force: bool = False) -> MonthlyFollowupState:
        """
        Generate follow-up assignments for a month.

        Assigns one adult per household, distributed across the month's days.
        """
        month_key = f"{year:04d}-{month:02d}"

        # Check if already generated
        if month_key in self.state and not force:
            return self.state[month_key]

        # Get shepherding list
        people = self.pco_client.get_shepherding_list()
        adults = [p for p in people if not p.is_child]

        # Group by household
        households = self._group_by_household(adults)

        # Get working days
        working_days = self._get_working_days(year, month)

        # Select one adult per household and distribute across days
        assignments = []
        household_list = list(households.items())

        for i, (hh_id, members) in enumerate(household_list):
            # Select primary adult (first one, or could rotate based on history)
            primary = members[0]

            # Distribute evenly across working days
            day_index = (i * len(working_days)) // len(household_list)
            assigned_date = working_days[day_index]

            assignments.append(FollowupAssignment(
                person_id=primary.pco_id,
                person_name=primary.name,
                household_id=hh_id,
                household_name=primary.household_name or "",
                phone=primary.primary_phone,
                email=primary.primary_email,
                assigned_date=assigned_date.isoformat()
            ))

        # Get theme
        theme_data = MONTHLY_THEMES.get(month_key, {
            "name": "General Check-in",
            "questions": ["How are you doing?", "Any prayer requests?"]
        })

        state = MonthlyFollowupState(
            month=month_key,
            theme=theme_data["name"],
            assignments=assignments
        )

        self.state[month_key] = state
        self._save_state()

        return state

    def get_todays_followups(self, include_overdue: bool = True) -> list[dict]:
        """
        Get follow-up contacts for today.

        Returns list sorted with today's assigned person FIRST, then overdue
        contacts sorted by oldest first.

        Includes:
        - Contacts assigned for today
        - Overdue contacts (assigned 7+ days ago, not completed)
        """
        today = date.today()
        month_key = today.strftime("%Y-%m")

        # Ensure current month is generated
        if month_key not in self.state:
            self.generate_monthly_assignments(today.year, today.month)

        state = self.state.get(month_key)
        if not state:
            return []

        theme_data = MONTHLY_THEMES.get(month_key, {"questions": []})
        followups = []

        for assignment in state.assignments:
            if assignment.completed:
                continue

            assigned = date.fromisoformat(assignment.assigned_date)
            days_overdue = (today - assigned).days

            # Include if assigned today or overdue (7+ days)
            if assigned == today or (include_overdue and days_overdue >= 7):
                # Get contact history for smart questions
                history = self.notion_crm.get_contact_history(assignment.person_name)
                history_questions = []
                if history.get("status") == "success" and history.get("notes"):
                    # Extract questions from last note
                    last_note = history["notes"][-1] if history["notes"] else ""
                    history_questions = self.notion_crm._generate_followup_questions(last_note)

                followups.append({
                    "person_name": assignment.person_name,
                    "household": assignment.household_name,
                    "phone": assignment.phone,
                    "email": assignment.email,
                    "assigned_date": assignment.assigned_date,
                    "days_overdue": days_overdue if days_overdue > 0 else 0,
                    "is_overdue": days_overdue >= 7,
                    "is_today": assigned == today,
                    "theme": state.theme,
                    "theme_questions": theme_data.get("questions", [])[:2],
                    "history_questions": history_questions[:2],
                    "total_previous_contacts": history.get("total_contacts", 0) if history.get("status") == "success" else 0
                })

        # Sort: today's assignment first, then overdue by oldest
        followups.sort(key=lambda f: (
            0 if f["is_today"] else 1,  # Today first
            f["days_overdue"] * -1       # Then oldest overdue
        ))

        return followups

    def get_next_followup(self) -> dict | None:
        """
        Get the next person to follow up with, regardless of exact date.

        Priority order:
        1. Overdue assignments (assigned date passed, not completed)
        2. Today's assignments
        3. Next upcoming assignment

        Always returns someone if any assignments exist for the current month.
        """
        today = date.today()
        month_key = today.strftime("%Y-%m")

        # Ensure current month is generated
        if month_key not in self.state:
            try:
                self.generate_monthly_assignments(today.year, today.month)
            except Exception as e:
                print(f"  (Could not generate assignments: {e})")
                return None

        state = self.state.get(month_key)
        if not state:
            return None

        theme_data = MONTHLY_THEMES.get(month_key, {
            "name": "General Check-in",
            "questions": ["How are you doing?", "Any prayer requests?"]
        })

        incomplete = [a for a in state.assignments if not a.completed]
        if not incomplete:
            return None

        # Sort: overdue first (oldest), then today, then upcoming (soonest)
        def sort_key(a):
            assigned = date.fromisoformat(a.assigned_date)
            if assigned < today:
                return (0, assigned)  # Overdue - oldest first
            elif assigned == today:
                return (1, assigned)  # Today
            else:
                return (2, assigned)  # Upcoming - soonest first

        incomplete.sort(key=sort_key)
        assignment = incomplete[0]

        assigned = date.fromisoformat(assignment.assigned_date)
        days_overdue = (today - assigned).days

        # Try to get contact history, but don't fail if unavailable
        history_questions = []
        total_contacts = 0
        try:
            history = self.notion_crm.get_contact_history(assignment.person_name)
            if history.get("status") == "success":
                total_contacts = history.get("total_contacts", 0)
                if history.get("notes"):
                    last_note = history["notes"][-1]
                    history_questions = self.notion_crm._generate_followup_questions(last_note)[:2]
        except Exception:
            pass

        return {
            "person_name": assignment.person_name,
            "household": assignment.household_name,
            "phone": assignment.phone,
            "email": assignment.email,
            "assigned_date": assignment.assigned_date,
            "days_overdue": days_overdue if days_overdue > 0 else 0,
            "is_overdue": days_overdue > 0,
            "theme": state.theme,
            "theme_questions": theme_data.get("questions", [])[:2],
            "history_questions": history_questions,
            "total_previous_contacts": total_contacts
        }

    def mark_followup_complete(self, person_name: str, notes: str = "") -> bool:
        """Mark a follow-up as completed."""
        today = date.today()
        month_key = today.strftime("%Y-%m")

        if month_key not in self.state:
            return False

        for assignment in self.state[month_key].assignments:
            if assignment.person_name.lower() == person_name.lower():
                assignment.completed = True
                assignment.completed_date = today.isoformat()
                assignment.notes = notes
                self._save_state()
                return True

        return False

    def get_monthly_summary(self, year: int = None, month: int = None) -> dict:
        """Get summary of follow-up progress for a month."""
        if year is None or month is None:
            today = date.today()
            year, month = today.year, today.month

        month_key = f"{year:04d}-{month:02d}"

        if month_key not in self.state:
            return {"status": "error", "message": f"No assignments for {month_key}"}

        state = self.state[month_key]
        completed = sum(1 for a in state.assignments if a.completed)
        total = len(state.assignments)

        return {
            "month": month_key,
            "theme": state.theme,
            "total_households": total,
            "completed": completed,
            "remaining": total - completed,
            "completion_rate": f"{(completed / total * 100):.1f}%" if total > 0 else "0%",
            "assignments": [
                {
                    "person": a.person_name,
                    "household": a.household_name,
                    "assigned": a.assigned_date,
                    "completed": a.completed,
                    "completed_date": a.completed_date
                }
                for a in sorted(state.assignments, key=lambda x: x.assigned_date)
            ]
        }

    def format_followup_reminder(self, followup: dict) -> str:
        """Format a follow-up into a reminder-ready string."""
        lines = [
            f"🧑‍🤝‍🧑 Follow up with {followup['person_name']}",
            f"   Household: {followup['household']}",
        ]

        if followup['phone']:
            lines.append(f"   📞 {followup['phone']}")
        if followup['email']:
            lines.append(f"   📧 {followup['email']}")

        if followup['is_overdue']:
            lines.append(f"   ⚠️ OVERDUE by {followup['days_overdue']} days")

        lines.append(f"\n🎯 This Month's Theme: {followup['theme']}")
        for q in followup['theme_questions']:
            lines.append(f"   • {q}")

        if followup['history_questions']:
            lines.append(f"\n📝 From Previous Contact:")
            for q in followup['history_questions']:
                lines.append(f"   • {q}")

        if followup['total_previous_contacts'] > 0:
            lines.append(f"\n   ({followup['total_previous_contacts']} previous contacts logged)")

        return "\n".join(lines)


def main():
    """CLI interface for follow-up manager."""
    import sys

    manager = FollowupManager()

    if len(sys.argv) < 2:
        print("Usage: followup_manager.py <command> [args]")
        print("\nCommands:")
        print("  generate [YYYY-MM]     - Generate monthly assignments")
        print("  today                  - Show today's follow-ups")
        print("  complete <name>        - Mark follow-up as complete")
        print("  summary [YYYY-MM]      - Show monthly summary")
        print("  themes                 - Show available themes")
        return

    cmd = sys.argv[1]

    if cmd == "generate":
        if len(sys.argv) >= 3:
            year, month = map(int, sys.argv[2].split("-"))
        else:
            today = date.today()
            year, month = today.year, today.month

        state = manager.generate_monthly_assignments(year, month, force="--force" in sys.argv)
        print(f"Generated {len(state.assignments)} assignments for {state.month}")
        print(f"Theme: {state.theme}")
        print("\nFirst 5 assignments:")
        for a in state.assignments[:5]:
            print(f"  {a.assigned_date}: {a.person_name} ({a.household_name})")

    elif cmd == "today":
        followups = manager.get_todays_followups()
        if not followups:
            print("No follow-ups scheduled for today.")
            return

        print(f"Today's Follow-ups ({len(followups)}):\n")
        for f in followups:
            print(manager.format_followup_reminder(f))
            print("\n" + "=" * 50 + "\n")

    elif cmd == "complete" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        if manager.mark_followup_complete(name):
            print(f"Marked follow-up with {name} as complete.")
        else:
            print(f"Could not find follow-up for {name}")

    elif cmd == "summary":
        if len(sys.argv) >= 3:
            year, month = map(int, sys.argv[2].split("-"))
            summary = manager.get_monthly_summary(year, month)
        else:
            summary = manager.get_monthly_summary()

        if summary.get("status") == "error":
            print(summary["message"])
            return

        print(f"Follow-up Summary for {summary['month']}")
        print(f"Theme: {summary['theme']}")
        print(f"\nProgress: {summary['completed']}/{summary['total_households']} ({summary['completion_rate']})")
        print(f"Remaining: {summary['remaining']}")

        print("\nAssignments:")
        for a in summary["assignments"]:
            status = "✓" if a["completed"] else "○"
            print(f"  {status} {a['assigned']}: {a['person']} ({a['household']})")

    elif cmd == "themes":
        print("Available Monthly Themes:\n")
        for month_key, theme in sorted(MONTHLY_THEMES.items()):
            print(f"{month_key}: {theme['name']}")
            for q in theme['questions']:
                print(f"  • {q}")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
