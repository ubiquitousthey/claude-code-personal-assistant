#!/usr/bin/env python3
"""
Streaks Habit Tracker Sync

Parses Streaks CSV exports and syncs habit data to:
- Journal entries (daily habit checkboxes)
- Weekly review summaries
- OKR tracking

Usage:
  streaks_sync.py import <csv_file>  - Import/update from CSV export
  streaks_sync.py today              - Show today's habits
  streaks_sync.py week               - Show this week's habits
  streaks_sync.py summary            - Show habit statistics
"""

import os
import sys
import csv
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Cache location
CACHE_DIR = Path("/workspace/cache/habits")
HABITS_CACHE = CACHE_DIR / "streaks_data.json"
LAST_IMPORT = CACHE_DIR / "last_import.json"


@dataclass
class HabitEntry:
    """A single habit entry."""
    task_id: str
    title: str
    entry_type: str  # completed_manually, missed_auto, skipped_auto
    entry_date: date
    completed: bool


def parse_streaks_csv(csv_path: str) -> list[HabitEntry]:
    """Parse Streaks CSV export."""
    entries = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Parse date (format: YYYYMMDD)
                date_str = row.get('entry_date', '')
                if not date_str or len(date_str) != 8:
                    continue

                entry_date = date(
                    int(date_str[:4]),
                    int(date_str[4:6]),
                    int(date_str[6:8])
                )

                entry_type = row.get('entry_type', '')
                completed = entry_type == 'completed_manually'

                # Clean title (remove quotes and time suffixes)
                title = row.get('title', '').strip('"')
                if ', ' in title and title.split(', ')[-1].replace(':', '').isdigit():
                    title = title.split(', ')[0]

                entries.append(HabitEntry(
                    task_id=row.get('task_id', ''),
                    title=title,
                    entry_type=entry_type,
                    entry_date=entry_date,
                    completed=completed
                ))
            except Exception as e:
                continue

    return entries


def save_habits_cache(entries: list[HabitEntry]):
    """Save habits to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Group by date and habit
    data = defaultdict(dict)
    habits_set = set()

    for entry in entries:
        date_str = entry.entry_date.isoformat()
        data[date_str][entry.title] = {
            "completed": entry.completed,
            "type": entry.entry_type
        }
        habits_set.add(entry.title)

    cache = {
        "habits": sorted(habits_set),
        "entries": dict(data),
        "last_updated": datetime.now().isoformat()
    }

    with open(HABITS_CACHE, 'w') as f:
        json.dump(cache, f, indent=2)

    # Update last import
    with open(LAST_IMPORT, 'w') as f:
        json.dump({
            "imported_at": datetime.now().isoformat(),
            "total_entries": len(entries),
            "habits_count": len(habits_set)
        }, f)


def load_habits_cache() -> dict:
    """Load habits from cache."""
    if not HABITS_CACHE.exists():
        return {"habits": [], "entries": {}}

    with open(HABITS_CACHE) as f:
        return json.load(f)


def get_habits_for_date(target_date: date) -> dict:
    """Get all habits for a specific date."""
    cache = load_habits_cache()
    date_str = target_date.isoformat()
    return cache.get("entries", {}).get(date_str, {})


def get_habits_for_week(start_date: date = None) -> dict:
    """Get habits for a week starting from start_date (defaults to this week's Monday)."""
    if start_date is None:
        today = date.today()
        start_date = today - timedelta(days=today.weekday())

    cache = load_habits_cache()
    week_data = {}

    for i in range(7):
        day = start_date + timedelta(days=i)
        date_str = day.isoformat()
        week_data[date_str] = cache.get("entries", {}).get(date_str, {})

    return week_data


def calculate_habit_stats(days: int = 30) -> dict:
    """Calculate habit statistics for the last N days."""
    cache = load_habits_cache()
    habits = cache.get("habits", [])
    entries = cache.get("entries", {})

    today = date.today()
    start = today - timedelta(days=days)

    stats = {}
    for habit in habits:
        completed = 0
        total = 0

        for i in range(days + 1):
            day = start + timedelta(days=i)
            date_str = day.isoformat()

            if date_str in entries and habit in entries[date_str]:
                total += 1
                if entries[date_str][habit].get("completed"):
                    completed += 1

        if total > 0:
            stats[habit] = {
                "completed": completed,
                "total": total,
                "rate": round(completed / total * 100, 1)
            }

    return stats


def format_today_habits() -> str:
    """Format today's habits for display."""
    today = date.today()
    habits = get_habits_for_date(today)

    if not habits:
        return f"No habit data for today ({today}). Run: streaks_sync.py import <csv>"

    lines = [f"📊 Habits for {today.strftime('%A, %B %d')}:\n"]

    for habit, data in sorted(habits.items()):
        status = "✅" if data.get("completed") else "❌"
        lines.append(f"  {status} {habit}")

    # Calculate completion
    completed = sum(1 for h in habits.values() if h.get("completed"))
    total = len(habits)
    lines.append(f"\n  Completed: {completed}/{total}")

    return "\n".join(lines)


def format_week_habits() -> str:
    """Format this week's habits for display."""
    week = get_habits_for_week()
    cache = load_habits_cache()
    habits = cache.get("habits", [])

    if not habits:
        return "No habit data. Run: streaks_sync.py import <csv>"

    # Calculate per-habit weekly totals
    habit_counts = defaultdict(int)
    habit_totals = defaultdict(int)

    for date_str, day_habits in week.items():
        for habit in habits:
            if habit in day_habits:
                habit_totals[habit] += 1
                if day_habits[habit].get("completed"):
                    habit_counts[habit] += 1

    # Sort habits by those tracked this week
    active_habits = [(h, habit_counts[h], habit_totals[h])
                     for h in habits if habit_totals[h] > 0]

    if not active_habits:
        return "No habits tracked this week."

    lines = ["📊 This Week's Habits:\n"]

    for habit, completed, total in sorted(active_habits, key=lambda x: -x[1]):
        bar = "●" * completed + "○" * (total - completed)
        lines.append(f"  {habit}: {bar} ({completed}/{total})")

    return "\n".join(lines)


def format_summary(days: int = 30) -> str:
    """Format habit statistics summary."""
    stats = calculate_habit_stats(days)

    if not stats:
        return f"No habit data for last {days} days."

    lines = [f"📈 Habit Stats (Last {days} Days):\n"]

    # Sort by completion rate
    sorted_habits = sorted(stats.items(), key=lambda x: -x[1]["rate"])

    for habit, data in sorted_habits:
        rate = data["rate"]
        bar_filled = int(rate / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        lines.append(f"  {habit}")
        lines.append(f"    {bar} {rate}% ({data['completed']}/{data['total']})")

    return "\n".join(lines)


def import_csv(csv_path: str):
    """Import habits from CSV."""
    print(f"📥 Importing from {csv_path}...")

    entries = parse_streaks_csv(csv_path)
    print(f"   Parsed {len(entries)} entries")

    save_habits_cache(entries)

    # Get unique habits
    habits = set(e.title for e in entries)
    print(f"   Found {len(habits)} unique habits:")
    for h in sorted(habits):
        print(f"     - {h}")

    # Show recent summary
    print(f"\n{format_today_habits()}")


def get_journal_habit_mapping() -> dict:
    """Map Streaks habits to Journal database properties."""
    return {
        "Scripture": "Read Bible?",
        "Pray": "Prayed?",
        "Write In Journal": "Journaled?",
        "Read a Book": "Read a book?",
    }


def get_weekly_habit_data() -> dict:
    """Get habit data formatted for weekly review."""
    week = get_habits_for_week()
    cache = load_habits_cache()

    # Focus on key habits
    key_habits = ["Scripture", "Pray", "Read a Book", "DMS", "Write In Journal"]

    result = {}
    for habit in key_habits:
        completed = 0
        total = 0
        for date_str, day_habits in week.items():
            if habit in day_habits:
                total += 1
                if day_habits[habit].get("completed"):
                    completed += 1
        if total > 0:
            result[habit] = {"completed": completed, "total": total}

    return result


def main():
    if len(sys.argv) < 2:
        print("Streaks Habit Sync")
        print("\nUsage: streaks_sync.py <command>")
        print("\nCommands:")
        print("  import <csv>  - Import from Streaks CSV export")
        print("  today         - Show today's habits")
        print("  week          - Show this week's habits")
        print("  summary       - Show habit statistics (30 days)")
        print("  summary <N>   - Show habit statistics for N days")
        print("  json          - Output week data as JSON (for integrations)")
        return

    cmd = sys.argv[1]

    if cmd == "import" and len(sys.argv) > 2:
        import_csv(sys.argv[2])

    elif cmd == "today":
        print(format_today_habits())

    elif cmd == "week":
        print(format_week_habits())

    elif cmd == "summary":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(format_summary(days))

    elif cmd == "json":
        data = get_weekly_habit_data()
        print(json.dumps(data, indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
