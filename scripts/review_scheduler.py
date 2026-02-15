#!/usr/bin/env python3
"""
Review Scheduler

Scheduled script that creates review pages in Notion and sends
Telegram notifications with links. Called by cron/launchd.

Usage:
  review_scheduler.py daily_morning
  review_scheduler.py daily_financial
  review_scheduler.py weekly
  review_scheduler.py monthly
"""

import os
import sys
import re
import csv
import json
import subprocess
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Import local modules
sys.path.insert(0, "/workspace/scripts")
from review_manager import (
    ReviewManager, ReviewData,
    build_daily_review_blocks, build_weekly_review_blocks, build_monthly_review_blocks
)
from followup_manager import FollowupManager

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Reviews Database
REVIEWS_DB_ID = os.getenv("NOTION_REVIEWS_DB_ID", "")


def send_telegram_message(message: str) -> bool:
    """Send a message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram not configured] Would send:\n{message}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram message sent")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


def get_tasks_due_today() -> list:
    """Get tasks due today from Notion cache files.

    Reads personal_tasks.md and work_tasks.md, parses task lines,
    and returns tasks that are overdue, due today, or due within 2 days.
    """
    today = date.today()
    upcoming_cutoff = today + timedelta(days=2)

    # Pattern: - [ ] **Title** `emoji Category` (Due: YYYY-MM-DD)
    task_pattern = re.compile(
        r'^- \[ \] \*\*(.+?)\*\*\s*`([^`]*)`(?:\s*\(Due:\s*(\d{4}-\d{2}-\d{2})\))?'
    )

    tasks = []

    cache_files = [
        ("/workspace/cache/notion/tasks/personal_tasks.md", "Personal"),
        ("/workspace/cache/notion/tasks/work_tasks.md", "Work"),
    ]

    for filepath, source in cache_files:
        path = Path(filepath)
        if not path.exists():
            continue

        try:
            content = path.read_text()
        except Exception:
            continue

        current_priority = ""
        for line in content.splitlines():
            # Track priority section headers
            if line.startswith("## "):
                current_priority = line.strip("# ").strip()

            match = task_pattern.match(line.strip())
            if not match:
                continue

            title = match.group(1)
            category = match.group(2)
            due_str = match.group(3)

            if not due_str:
                # No due date — include if high priority
                if "High" in current_priority:
                    tasks.append(f"[NO DATE] {title} ({source}/{category})")
                continue

            try:
                due = date.fromisoformat(due_str)
            except ValueError:
                continue

            if due < today:
                tasks.append(f"[OVERDUE] {title} ({source}/{category}) - was due {due_str}")
            elif due == today:
                tasks.append(f"[TODAY] {title} ({source}/{category})")
            elif due <= upcoming_cutoff:
                tasks.append(f"[UPCOMING] {title} ({source}/{category}) - due {due_str}")

    return tasks


def get_calendar_events_today() -> list:
    """Get today's calendar events from calendar_sync cache.

    Auto-syncs calendars if cache is older than 6 hours.
    Returns formatted event strings with time, title, calendar, and location.
    """
    try:
        from calendar_sync import get_events_for_date, sync_calendars

        # Check cache freshness and sync if stale
        last_sync_file = Path("/workspace/cache/calendar/last_sync.json")
        try:
            if last_sync_file.exists():
                with open(last_sync_file) as f:
                    sync_info = json.load(f)
                last_sync = datetime.fromisoformat(sync_info.get("last_sync", "2000-01-01"))
                if (datetime.now() - last_sync).total_seconds() > 6 * 3600:
                    print("  Calendar cache stale, syncing...")
                    sync_calendars()
            else:
                sync_calendars()
        except Exception as e:
            print(f"  (Calendar sync skipped: {e})")

        events = get_events_for_date(date.today())
        formatted = []
        for ev in events:
            cal_label = "Work" if ev.calendar == "work" else "Personal"
            if ev.all_day:
                time_str = "All day"
            else:
                time_str = ev.start.strftime("%I:%M %p").lstrip("0")

            line = f"{time_str} - {ev.title} [{cal_label}]"
            if ev.location:
                line += f" @ {ev.location}"
            formatted.append(line)
        return formatted
    except ImportError:
        print("  (calendar_sync module not available)")
        return []
    except Exception as e:
        print(f"  (Calendar events error: {e})")
        return []


def get_important_dates() -> list:
    """Get important upcoming dates (birthdays, anniversaries, etc.)."""
    # Would integrate with a dates database or calendar
    return []


def get_financial_summary() -> dict | None:
    """Read Copilot transactions CSV and produce a 30-day financial summary.

    Returns dict with total_spent, income, net, top_categories,
    large_transactions, and pending_bills (from personal tasks cache).
    Returns None if no data is available.
    """
    csv_path = Path("/workspace/copilot-transactions-latest.csv")
    cutoff = date.today() - timedelta(days=30)

    transactions = []
    if csv_path.exists():
        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        txn_date = date.fromisoformat(row["date"])
                    except (ValueError, KeyError):
                        continue
                    if txn_date < cutoff:
                        continue
                    try:
                        amount = float(row.get("amount", 0))
                    except ValueError:
                        continue
                    transactions.append({
                        "date": row["date"],
                        "name": row.get("name", ""),
                        "amount": amount,
                        "category": row.get("category", "Other"),
                        "account": row.get("account", ""),
                    })
        except Exception as e:
            print(f"  (Error reading Copilot CSV: {e})")

    # Scan personal tasks cache for bill-related tasks
    pending_bills = []
    bills_path = Path("/workspace/cache/notion/tasks/personal_tasks.md")
    if bills_path.exists():
        try:
            content = bills_path.read_text()
            bill_pattern = re.compile(
                r'^- \[ \] \*\*(.*(?:Pay|Bill|bill|payment|Credit Card|card).*?)\*\*.*?\(Due:\s*(\d{4}-\d{2}-\d{2})\)',
                re.IGNORECASE
            )
            for line in content.splitlines():
                m = bill_pattern.match(line.strip())
                if m:
                    pending_bills.append({"title": m.group(1), "due": m.group(2)})
        except Exception:
            pass

    if not transactions and not pending_bills:
        return None

    # Calculate summary from transactions
    total_spent = sum(t["amount"] for t in transactions if t["amount"] > 0)
    income = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)
    net = income - total_spent

    # Top spending categories
    cat_totals: dict[str, float] = {}
    for t in transactions:
        if t["amount"] > 0:
            cat_totals[t["category"]] = cat_totals.get(t["category"], 0) + t["amount"]
    top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:3]

    # Large transactions (>$100)
    large = [t for t in transactions if t["amount"] > 100]
    large.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "total_spent": total_spent,
        "income": income,
        "net": net,
        "top_categories": top_categories,
        "large_transactions": large[:5],
        "pending_bills": pending_bills,
        "txn_count": len(transactions),
    }


def ensure_caches_fresh(max_age_hours: int = 12):
    """Refresh Notion caches if older than max_age_hours."""
    summary_path = Path("/workspace/cache/notion/SUMMARY.md")
    if not summary_path.exists():
        print("  Cache missing, refreshing...")
    else:
        try:
            content = summary_path.read_text()
            # Parse "Last synced: YYYY-MM-DD HH:MM" from summary
            match = re.search(r'Last synced:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', content)
            if match:
                last_sync = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
                age_hours = (datetime.now() - last_sync).total_seconds() / 3600
                if age_hours < max_age_hours:
                    print(f"  Notion cache is {age_hours:.1f}h old (fresh enough)")
                    return
                print(f"  Notion cache is {age_hours:.1f}h old, refreshing...")
            else:
                print("  Could not parse cache timestamp, refreshing...")
        except Exception as e:
            print(f"  Error checking cache age: {e}")

    try:
        result = subprocess.run(
            [sys.executable, "/workspace/scripts/notion_cache_sync.py"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print("  Notion cache refreshed")
        else:
            print(f"  Cache refresh failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("  Cache refresh timed out (using stale cache)")
    except Exception as e:
        print(f"  Cache refresh error: {e}")


def run_daily_morning():
    """Create and send daily morning review."""
    print(f"📋 Running daily morning review for {date.today()}")

    # Refresh caches if stale
    ensure_caches_fresh()

    manager = ReviewManager(REVIEWS_DB_ID)
    fm = FollowupManager()

    # Gather real data
    tasks = get_tasks_due_today()
    print(f"  Tasks found: {len(tasks)}")
    if not tasks:
        tasks = ["No tasks found in cache — run notion_cache_sync.py to refresh"]

    events = get_calendar_events_today()
    print(f"  Calendar events found: {len(events)}")

    dates = get_important_dates()

    # Get today's shepherding follow-up (with fallback)
    followups = fm.get_todays_followups()
    followup = followups[0] if followups else None
    print(f"  Followups found: {len(followups)}, selected: {followup['person_name'] if followup else 'None'}")
    if not followup:
        try:
            followup = fm.get_next_followup()
            print(f"  Fallback followup: {followup['person_name'] if followup else 'None'}")
        except Exception as e:
            print(f"  (Followup fallback error: {e})")

    # Get financial snapshot
    financial = get_financial_summary()
    print(f"  Financial data: {'yes' if financial else 'none'}")

    # Build review content
    blocks = build_daily_review_blocks(
        date.today(),
        tasks=tasks,
        events=events,
        followup=followup,
        dates=dates
    )

    # Inject financial snapshot section into blocks if data exists
    if financial:
        fin_lines = ["💰 Financial Snapshot (30 days)"]
        if financial["txn_count"] > 0:
            fin_lines.append(
                f"Spent: ${financial['total_spent']:,.2f} | "
                f"Income: ${financial['income']:,.2f} | "
                f"Net: ${financial['net']:+,.2f}"
            )
            if financial["top_categories"]:
                cats = ", ".join(f"{c}: ${a:,.0f}" for c, a in financial["top_categories"])
                fin_lines.append(f"Top categories: {cats}")
            if financial["large_transactions"]:
                fin_lines.append("Large transactions:")
                for t in financial["large_transactions"][:3]:
                    fin_lines.append(f"  • {t['name']} ${t['amount']:,.2f} ({t['date']})")
        if financial["pending_bills"]:
            fin_lines.append("Pending bills:")
            for b in financial["pending_bills"]:
                fin_lines.append(f"  • {b['title']} (due {b['due']})")
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "\n".join(fin_lines)}}]
            }
        })

    review = ReviewData(
        review_type="Daily",
        date=date.today(),
        title=f"Daily Review - {date.today().strftime('%Y-%m-%d')}",
        content_blocks=blocks
    )

    # Create Notion page
    result = manager.create_review_page(review)
    print(f"  Notion result: {result.get('status', 'unknown')} - {result.get('url', 'no url')}")

    if result.get("status") in ["created", "exists"]:
        # Build enriched Telegram message
        overdue_count = sum(1 for t in tasks if "[OVERDUE]" in t)
        today_count = sum(1 for t in tasks if "[TODAY]" in t)

        followup_line = ""
        if followup:
            overdue_tag = " ⚠️ OVERDUE" if followup.get("is_overdue") else ""
            followup_line = f"• Follow-up: {followup['person_name']}{overdue_tag} 📞\n"

        event_line = ""
        if events:
            event_line = f"• {len(events)} calendar event{'s' if len(events) != 1 else ''}\n"

        fin_line = ""
        if financial and financial["txn_count"] > 0:
            fin_line = f"• 30d spending: ${financial['total_spent']:,.0f}\n"

        task_summary = f"• {len(tasks)} tasks ({overdue_count} overdue, {today_count} today)"

        message = f"""📋 *Daily Review Ready*

[Open in Notion]({result['url']})

Quick look:
{task_summary}
{event_line}{followup_line}{fin_line}
Reply to add notes or discuss."""

        send_telegram_message(message)
        print(f"✅ Review created: {result['url']}")
    else:
        print(f"❌ Error: {result}")


PENDING_REMINDERS_FILE = "/workspace/data/pending_reminders.json"


def queue_apple_reminder(title: str, note: str, due_date: str, list_name: str = "Reminders") -> bool:
    """Queue an Apple Reminder for MCP processing."""
    import json
    from pathlib import Path

    # Load existing queue
    queue_file = Path(PENDING_REMINDERS_FILE)
    if queue_file.exists():
        with open(queue_file) as f:
            queue = json.load(f)
    else:
        queue = []

    # Check for existing reminder with same reference
    reference = note.split("Reference: ")[-1].strip() if "Reference:" in note else ""

    for item in queue:
        if item.get("reference") == reference:
            print(f"⏭️ Reminder already queued: {reference}")
            return False

    # Add to queue
    queue.append({
        "title": title,
        "note": note,
        "due_date": due_date,
        "list_name": list_name,
        "reference": reference,
        "created_at": datetime.now().isoformat()
    })

    # Save queue
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)

    print(f"📝 Queued reminder: {title}")
    print(f"   (Process with: python scripts/review_scheduler.py process_reminders)")
    return True


def get_pending_reminders() -> list:
    """Get list of pending reminders for MCP processing."""
    from pathlib import Path

    queue_file = Path(PENDING_REMINDERS_FILE)
    if queue_file.exists():
        with open(queue_file) as f:
            return json.load(f)
    return []


def clear_pending_reminders():
    """Clear the pending reminders queue."""
    from pathlib import Path

    queue_file = Path(PENDING_REMINDERS_FILE)
    if queue_file.exists():
        queue_file.unlink()
        print("✅ Cleared pending reminders queue")


def run_daily_financial():
    """Send financial summary via Telegram, or fall back to Apple Reminder."""
    print(f"💰 Running daily financial review")

    financial = get_financial_summary()

    if financial and (financial["txn_count"] > 0 or financial["pending_bills"]):
        lines = [f"💰 *Daily Financial Summary* ({date.today().strftime('%b %d')})"]

        if financial["txn_count"] > 0:
            lines.append("")
            lines.append(
                f"*30-day totals:*\n"
                f"  Spent: ${financial['total_spent']:,.2f}\n"
                f"  Income: ${financial['income']:,.2f}\n"
                f"  Net: ${financial['net']:+,.2f}"
            )

            if financial["top_categories"]:
                lines.append("\n*Top categories:*")
                for cat, amount in financial["top_categories"]:
                    lines.append(f"  • {cat}: ${amount:,.2f}")

            if financial["large_transactions"]:
                lines.append("\n*Large transactions:*")
                for t in financial["large_transactions"][:5]:
                    lines.append(f"  • {t['name']} — ${t['amount']:,.2f} ({t['date']})")

        if financial["pending_bills"]:
            lines.append("\n*Pending bills:*")
            for b in financial["pending_bills"]:
                lines.append(f"  • {b['title']} (due {b['due']})")

        lines.append("\n_Check stocks & portfolio after market close_")

        send_telegram_message("\n".join(lines))
    else:
        # Fall back to Apple Reminder if no financial data available
        print("  No financial data available, queuing reminder instead")
        target_date = date.today()
        due_str = f"{target_date.isoformat()} 16:00:00"
        queue_apple_reminder(
            "Check stocks and portfolio",
            f"Quick financial check after market close.\n\nReference: cron_financial_{target_date.isoformat()}",
            due_str
        )


def run_weekly():
    """Create and send weekly review."""
    target_date = date.today()
    week_num = target_date.isocalendar()[1]

    print(f"📅 Running weekly review for Week {week_num}")

    manager = ReviewManager(REVIEWS_DB_ID)

    # Get habit tracking data from Streaks
    try:
        from streaks_sync import get_weekly_habit_data
        streaks_data = get_weekly_habit_data()
        habits = {
            "Bible": streaks_data.get("Scripture", {}).get("completed", 0),
            "Prayer": streaks_data.get("Pray", {}).get("completed", 0),
            "Reading": streaks_data.get("Read a Book", {}).get("completed", 0),
        }
    except Exception as e:
        print(f"  (Streaks data not available: {e})")
        habits = {"Bible": 0, "Prayer": 0, "Reading": 0}

    blocks = build_weekly_review_blocks(
        target_date,
        habits=habits
    )

    review = ReviewData(
        review_type="Weekly",
        date=target_date,
        title=f"Weekly Review - Week {week_num}",
        content_blocks=blocks
    )

    result = manager.create_review_page(review)

    if result.get("status") in ["created", "exists"]:
        total_habits = sum(habits.values())
        message = f"""📅 *Weekly Review Ready*

[Open in Notion]({result['url']})

This week:
• Habits: {total_habits}/21 completed
• 3 data uploads needed

Ready for your weekly reset?"""

        send_telegram_message(message)
        print(f"✅ Review created: {result['url']}")
    else:
        print(f"❌ Error: {result}")


def is_first_sunday_of_month() -> bool:
    """Check if today is the first Sunday of the month."""
    today = date.today()
    # First Sunday is between day 1-7
    return today.weekday() == 6 and today.day <= 7


def run_monthly():
    """Create and send monthly review."""
    target_date = date.today()
    month_name = target_date.strftime("%B %Y")

    # Only run on first Sunday of month
    if not is_first_sunday_of_month():
        print(f"⏭️ Skipping monthly review - not first Sunday (day {target_date.day})")
        return

    print(f"📊 Running monthly review for {month_name}")

    manager = ReviewManager(REVIEWS_DB_ID)
    fm = FollowupManager()

    # Get followup stats
    stats = fm.get_monthly_summary()
    followup_stats = {
        "completed": stats.get("completed", 0),
        "total": stats.get("total_households", 0)
    }
    theme = stats.get("theme", "")

    # Get OKR progress (placeholder)
    okr_progress = [
        {"name": "🎙️ Launch Podcast", "progress": 17},
        {"name": "📖 Reading Habits", "progress": 25},
        {"name": "🏋️ Fitness", "progress": 40},
        {"name": "🏠 Family Relationships", "progress": 30}
    ]

    blocks = build_monthly_review_blocks(
        target_date,
        followup_stats=followup_stats,
        okr_progress=okr_progress,
        theme=theme
    )

    review = ReviewData(
        review_type="Monthly",
        date=target_date,
        title=f"Monthly Review - {month_name}",
        content_blocks=blocks
    )

    result = manager.create_review_page(review)

    if result.get("status") in ["created", "exists"]:
        completed = followup_stats.get("completed", 0)
        total = followup_stats.get("total", 0)
        rate = int((completed / total * 100) if total > 0 else 0)

        message = f"""📊 *Monthly Review Ready*

[Open in Notion]({result['url']})

{month_name} summary:
• Shepherding: {completed}/{total} households ({rate}%)
• OKRs: 2/4 on track

Time for monthly reflection!"""

        send_telegram_message(message)
        print(f"✅ Review created: {result['url']}")
    else:
        print(f"❌ Error: {result}")


def run_weekly_data_upload():
    """Queue Apple Reminder for data uploads."""
    print(f"📤 Queuing weekly data upload reminder")

    target_date = date.today()
    # Due at 8:00 PM today
    due_str = f"{target_date.isoformat()} 20:00:00"

    title = "Upload weekly data"
    note = f"""Weekly data upload tasks:
• Apple Health export
• Copilot CSV
• Bookshelf sync

Reference: cron_data_upload_{target_date.isoformat()}"""

    queue_apple_reminder(title, note, due_str)


def show_pending():
    """Show pending reminders waiting for MCP processing."""
    reminders = get_pending_reminders()
    if not reminders:
        print("No pending reminders")
        return

    print(f"📋 Pending reminders ({len(reminders)}):\n")
    for r in reminders:
        print(f"  • {r['title']}")
        print(f"    Due: {r['due_date']}")
        print(f"    List: {r['list_name']}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: review_scheduler.py <review_type>")
        print("\nReview types:")
        print("  daily_morning    - Morning review with tasks, schedule, follow-ups")
        print("  daily_financial  - Afternoon financial check reminder")
        print("  weekly           - Sunday weekly review")
        print("  weekly_upload    - Sunday data upload reminder")
        print("  monthly          - First Sunday monthly review")
        print("\nReminder management:")
        print("  pending          - Show pending reminders")
        print("  clear            - Clear pending reminders queue")
        return

    review_type = sys.argv[1]

    if review_type == "daily_morning":
        run_daily_morning()
    elif review_type == "daily_financial":
        run_daily_financial()
    elif review_type == "weekly":
        run_weekly()
    elif review_type == "weekly_upload":
        run_weekly_data_upload()
    elif review_type == "monthly":
        run_monthly()
    elif review_type == "pending":
        show_pending()
    elif review_type == "clear":
        clear_pending_reminders()
    else:
        print(f"Unknown review type: {review_type}")


if __name__ == "__main__":
    main()
