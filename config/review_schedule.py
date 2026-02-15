"""
Review Schedule Configuration

Defines when each review type should be triggered.
Based on productivity research:
- Peak cognitive performance: ~10:26 AM
- Trough (avoid): ~2:55 PM
- Creative recovery: Late afternoon/evening
"""

from datetime import time

REVIEW_SCHEDULE = {
    "daily_morning": {
        "time": time(5, 30),
        "days": ["mon", "tue", "wed", "thu", "fri"],  # Weekdays only
        "channel": "telegram",
        "script_args": ["daily_morning"],
        "description": "Plan your day: tasks, reminders, important dates, shepherding"
    },
    "daily_financial": {
        "time": time(16, 0),
        "days": ["mon", "tue", "wed", "thu", "fri"],  # Market days
        "channel": "apple_reminder",
        "script_args": ["daily_financial"],
        "description": "Quick financial check after market close"
    },
    "weekly_upload": {
        "time": time(20, 0),
        "days": ["sun"],
        "channel": "apple_reminder",
        "script_args": ["weekly_upload"],
        "description": "Trigger data uploads: Health, Copilot, Bookshelf"
    },
    "weekly": {
        "time": time(20, 0),
        "days": ["sun"],
        "channel": "telegram",
        "script_args": ["weekly"],
        "description": "Weekly GTD review with journal recap and habits"
    },
    "monthly": {
        "time": time(20, 0),
        "days": ["sun"],
        "week_of_month": 1,  # First Sunday only
        "channel": "telegram",
        "script_args": ["monthly"],
        "description": "Monthly reflection: OKR progress, trends, theme"
    }
}

# Telegram notification settings
TELEGRAM_SETTINGS = {
    "parse_mode": "Markdown",
    "disable_web_page_preview": False
}

# Apple Reminder settings
REMINDER_SETTINGS = {
    "list": "Reminders",
    "due_time_offset_hours": 0  # Same time as trigger
}
