#!/usr/bin/env python3
"""
Review Manager

Creates and manages review pages in Notion, linking them to Journal entries.
Supports daily, weekly, and monthly reviews.
"""

import os
import json
import requests
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Notion Configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"

# Database IDs
JOURNAL_DB_ID = "17dff6d0-ac74-802c-b641-f867c9cf72c2"
REVIEWS_DB_ID = os.getenv("NOTION_REVIEWS_DB_ID", "")  # Will be set after creation

# Parent page for Reviews database (same as Journal)
LIFE_MANAGEMENT_PAGE_ID = "4d372276-bb03-414c-8b09-6cee9330bc27"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


@dataclass
class ReviewData:
    """Data for a review page."""
    review_type: str  # Daily, Weekly, Monthly
    date: date
    title: str
    content_blocks: list = field(default_factory=list)
    journal_page_id: Optional[str] = None


class ReviewManager:
    """Manages review pages in Notion."""

    def __init__(self, reviews_db_id: str = None):
        self.reviews_db_id = reviews_db_id or REVIEWS_DB_ID

    def create_reviews_database(self) -> str:
        """Create the Reviews database in Notion."""
        url = "https://api.notion.com/v1/databases"

        payload = {
            "parent": {"type": "page_id", "page_id": LIFE_MANAGEMENT_PAGE_ID},
            "icon": {"type": "emoji", "emoji": "📋"},
            "title": [{"type": "text", "text": {"content": "Reviews"}}],
            "properties": {
                "Name": {"title": {}},
                "Type": {
                    "select": {
                        "options": [
                            {"name": "Daily", "color": "blue"},
                            {"name": "Weekly", "color": "green"},
                            {"name": "Monthly", "color": "purple"}
                        ]
                    }
                },
                "Date": {"date": {}},
                "Completed": {"checkbox": {}},
                "Journal": {
                    "relation": {
                        "database_id": JOURNAL_DB_ID,
                        "single_property": {}
                    }
                }
            }
        }

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            data = response.json()
            db_id = data["id"]
            print(f"✅ Created Reviews database: {db_id}")
            print(f"   URL: {data.get('url', 'N/A')}")
            return db_id
        else:
            print(f"❌ Failed to create database: {response.status_code}")
            print(response.text)
            return ""

    def find_journal_entry(self, target_date: date) -> Optional[str]:
        """Find the journal entry for a specific date."""
        url = f"https://api.notion.com/v1/databases/{JOURNAL_DB_ID}/query"

        # Journal entries are named by date (YYYY-MM-DD)
        date_str = target_date.strftime("%Y-%m-%d")

        payload = {
            "filter": {
                "property": "Name",
                "title": {"equals": date_str}
            }
        }

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
        return None

    def create_journal_entry(self, target_date: date) -> str:
        """Create a journal entry for a specific date if it doesn't exist."""
        existing = self.find_journal_entry(target_date)
        if existing:
            return existing

        url = "https://api.notion.com/v1/pages"
        date_str = target_date.strftime("%Y-%m-%d")

        payload = {
            "parent": {"database_id": JOURNAL_DB_ID},
            "icon": {"type": "emoji", "emoji": "📆"},
            "properties": {
                "Name": {"title": [{"text": {"content": date_str}}]}
            }
        }

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            page_id = response.json()["id"]
            print(f"✅ Created journal entry: {date_str}")
            return page_id
        else:
            print(f"❌ Failed to create journal entry: {response.text}")
            return ""

    def find_existing_review(self, review_type: str, target_date: date) -> Optional[str]:
        """Check if a review already exists for this type and date."""
        if not self.reviews_db_id:
            return None

        url = f"https://api.notion.com/v1/databases/{self.reviews_db_id}/query"

        # Build title to search for
        if review_type == "Daily":
            title = f"Daily Review - {target_date.strftime('%Y-%m-%d')}"
        elif review_type == "Weekly":
            week_num = target_date.isocalendar()[1]
            title = f"Weekly Review - Week {week_num}"
        else:
            title = f"Monthly Review - {target_date.strftime('%B %Y')}"

        payload = {
            "filter": {
                "property": "Name",
                "title": {"equals": title}
            }
        }

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                return results[0]["id"]
        return None

    def create_review_page(self, review_data: ReviewData) -> dict:
        """Create a review page in Notion."""
        if not self.reviews_db_id:
            return {"error": "Reviews database not configured"}

        # Check for existing
        existing = self.find_existing_review(review_data.review_type, review_data.date)
        if existing:
            url = f"https://www.notion.so/{existing.replace('-', '')}"
            return {
                "status": "exists",
                "page_id": existing,
                "url": url,
                "message": f"Review already exists for {review_data.title}"
            }

        # Find or create journal entry
        journal_page_id = self.find_journal_entry(review_data.date)
        if not journal_page_id:
            journal_page_id = self.create_journal_entry(review_data.date)

        url = "https://api.notion.com/v1/pages"

        # Build properties
        properties = {
            "Name": {"title": [{"text": {"content": review_data.title}}]},
            "Type": {"select": {"name": review_data.review_type}},
            "Date": {"date": {"start": review_data.date.isoformat()}},
            "Completed": {"checkbox": False}
        }

        # Add journal relation if we have one
        if journal_page_id:
            properties["Journal"] = {"relation": [{"id": journal_page_id}]}

        payload = {
            "parent": {"database_id": self.reviews_db_id},
            "icon": {"type": "emoji", "emoji": self._get_emoji(review_data.review_type)},
            "properties": properties,
            "children": review_data.content_blocks
        }

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            data = response.json()
            page_id = data["id"]
            page_url = data.get("url", f"https://www.notion.so/{page_id.replace('-', '')}")

            # Add link to journal entry
            if journal_page_id:
                self._add_review_link_to_journal(journal_page_id, review_data.title, page_url)

            return {
                "status": "created",
                "page_id": page_id,
                "url": page_url,
                "journal_linked": bool(journal_page_id)
            }
        else:
            return {"error": response.text}

    def _get_emoji(self, review_type: str) -> str:
        """Get emoji for review type."""
        return {
            "Daily": "📋",
            "Weekly": "📅",
            "Monthly": "📊"
        }.get(review_type, "📋")

    def _add_review_link_to_journal(self, journal_page_id: str, review_title: str, review_url: str):
        """Add a link to the review in the journal entry."""
        url = f"https://api.notion.com/v1/blocks/{journal_page_id}/children"

        # First check if Reviews section already exists
        existing_blocks = requests.get(url, headers=HEADERS).json().get("results", [])

        has_reviews_section = False
        for block in existing_blocks:
            if block.get("type") == "heading_2":
                text = block.get("heading_2", {}).get("rich_text", [])
                if text and "Reviews" in text[0].get("plain_text", ""):
                    has_reviews_section = True
                    break

        blocks_to_add = []

        if not has_reviews_section:
            blocks_to_add.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Reviews"}}]
                }
            })

        # Add link to review
        blocks_to_add.append({
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": review_title,
                        "link": {"url": review_url}
                    }
                }]
            }
        })

        payload = {"children": blocks_to_add}
        requests.patch(url, headers=HEADERS, json=payload)


def build_daily_review_blocks(target_date: date, tasks: list = None, events: list = None,
                              followup: dict = None, dates: list = None) -> list:
    """Build content blocks for a daily review."""
    blocks = []

    # Tasks section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Tasks & Reminders"}}]}
    })

    if tasks:
        for task in tasks:
            blocks.append({
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": task}}],
                    "checked": False
                }
            })
    else:
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "No tasks due today"}}]}
        })

    # Schedule section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Today's Schedule"}}]}
    })

    if events:
        for event in events:
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": event}}]
                }
            })
    else:
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "No scheduled events"}}]}
        })

    # Shepherding follow-up
    if followup:
        blocks.append({
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Shepherding Follow-up"}}]}
        })

        followup_text = f"**{followup.get('person_name', 'N/A')}** ({followup.get('household', 'N/A')})"
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": followup_text}}]}
        })

        if followup.get('phone'):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"📞 {followup['phone']}"}}]
                }
            })

        if followup.get('email'):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"📧 {followup['email']}"}}]
                }
            })

        if followup.get('theme'):
            blocks.append({
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "💡"},
                    "rich_text": [{"type": "text", "text": {"content": f"Theme: {followup['theme']}"}}]
                }
            })

        if followup.get('theme_questions'):
            for q in followup['theme_questions']:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": q}}]
                    }
                })

    # Important dates
    if dates:
        blocks.append({
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Important Dates This Week"}}]}
        })
        for d in dates:
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": d}}]
                }
            })

    # Reflection section
    blocks.append({
        "type": "divider",
        "divider": {}
    })
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Reflection"}}]}
    })
    blocks.append({
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}
    })

    return blocks


def build_weekly_review_blocks(target_date: date, habits: dict = None,
                               journal_entries: list = None) -> list:
    """Build content blocks for a weekly review."""
    blocks = []

    # Get Clear section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Get Clear: Process Inboxes"}}]}
    })

    for item in ["Email inbox to zero", "Notion inbox processed", "Apple Reminders reviewed"]:
        blocks.append({
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
                "checked": False
            }
        })

    # Get Current section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Get Current: Review Lists"}}]}
    })

    for item in ["Calendar next 2 weeks reviewed", "Waiting-for items checked", "Projects list current"]:
        blocks.append({
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
                "checked": False
            }
        })

    # Habits section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Habits This Week"}}]}
    })

    if habits:
        for habit, count in habits.items():
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"{habit}: {count}/7"}}]
                }
            })

    # Data uploads
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Data Uploads"}}]}
    })

    for item in ["Apple Health export", "Copilot CSV", "Bookshelf sync"]:
        blocks.append({
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": item}}],
                "checked": False
            }
        })

    # Get Creative section
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Get Creative: What's Next?"}}]}
    })
    blocks.append({
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}
    })

    return blocks


def build_monthly_review_blocks(target_date: date, followup_stats: dict = None,
                                okr_progress: list = None, health_trends: dict = None,
                                theme: str = None) -> list:
    """Build content blocks for a monthly review."""
    blocks = []
    month_name = target_date.strftime("%B %Y")

    # Theme section
    if theme:
        blocks.append({
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "🎯"},
                "rich_text": [{"type": "text", "text": {"content": f"Shepherding Theme: {theme}"}}]
            }
        })

    # Follow-up progress
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Shepherding Follow-up Progress"}}]}
    })

    if followup_stats:
        completed = followup_stats.get("completed", 0)
        total = followup_stats.get("total", 0)
        rate = (completed / total * 100) if total > 0 else 0
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Completed: {completed}/{total} ({rate:.0f}%)"}}]
            }
        })

    # OKR Progress
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "OKR Progress"}}]}
    })

    if okr_progress:
        for okr in okr_progress:
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"{okr['name']}: {okr['progress']}%"}}]
                }
            })
    else:
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "OKR data not available"}}]}
        })

    # Health Trends
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Health Trends"}}]}
    })

    if health_trends:
        for metric, value in health_trends.items():
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"{metric}: {value}"}}]
                }
            })

    # Reflection questions
    blocks.append({
        "type": "divider",
        "divider": {}
    })
    blocks.append({
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Reflection"}}]}
    })

    for q in ["What worked well this month?", "What could improve?", "What's the focus for next month?"]:
        blocks.append({
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"type": "text", "text": {"content": q}}]
            }
        })
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}
        })

    return blocks


def main():
    """CLI for review manager."""
    import sys

    manager = ReviewManager()

    if len(sys.argv) < 2:
        print("Review Manager")
        print("\nUsage: review_manager.py <command> [args]")
        print("\nCommands:")
        print("  create-db          - Create the Reviews database in Notion")
        print("  daily [date]       - Create daily review (default: today)")
        print("  weekly [date]      - Create weekly review (default: this week)")
        print("  monthly [date]     - Create monthly review (default: this month)")
        print("  test               - Test with sample data")
        return

    cmd = sys.argv[1]

    if cmd == "create-db":
        db_id = manager.create_reviews_database()
        if db_id:
            print(f"\n📝 Add this to your .env file:")
            print(f"NOTION_REVIEWS_DB_ID={db_id}")

    elif cmd == "daily":
        target_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

        # Fetch real data using review_scheduler functions
        from review_scheduler import (
            get_tasks_due_today, get_calendar_events_today,
            get_financial_summary, get_important_dates, ensure_caches_fresh
        )

        # Refresh caches if stale
        ensure_caches_fresh()

        # Get real tasks from Notion cache
        tasks = get_tasks_due_today()
        if not tasks:
            tasks = ["No tasks found in cache — run notion_cache_sync.py to refresh"]

        # Get real calendar events
        events = get_calendar_events_today()

        # Get important dates
        dates = get_important_dates()

        # Get followup person (today's assignment prioritized over overdue)
        try:
            from followup_manager import FollowupManager
            fm = FollowupManager()
            followups = fm.get_todays_followups()
            followup = followups[0] if followups else None
            if not followup:
                followup = fm.get_next_followup()
        except Exception as e:
            print(f"  (Followup error: {e})")
            followup = None

        # Get financial snapshot
        financial = get_financial_summary()

        blocks = build_daily_review_blocks(
            target_date,
            tasks=tasks,
            events=events,
            followup=followup,
            dates=dates
        )

        # Inject financial snapshot if data exists
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
            date=target_date,
            title=f"Daily Review - {target_date.strftime('%Y-%m-%d')}",
            content_blocks=blocks
        )

        result = manager.create_review_page(review)
        print(json.dumps(result, indent=2))

    elif cmd == "weekly":
        target_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
        week_num = target_date.isocalendar()[1]

        blocks = build_weekly_review_blocks(
            target_date,
            habits={"Bible": 5, "Prayer": 6, "Reading": 3}
        )

        review = ReviewData(
            review_type="Weekly",
            date=target_date,
            title=f"Weekly Review - Week {week_num}",
            content_blocks=blocks
        )

        result = manager.create_review_page(review)
        print(json.dumps(result, indent=2))

    elif cmd == "monthly":
        target_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

        # Get followup stats
        try:
            from followup_manager import FollowupManager
            fm = FollowupManager()
            stats = fm.get_monthly_summary()
            followup_stats = {
                "completed": stats.get("completed", 0),
                "total": stats.get("total", 0)
            }
            theme = stats.get("theme", "")
        except:
            followup_stats = None
            theme = None

        blocks = build_monthly_review_blocks(
            target_date,
            followup_stats=followup_stats,
            theme=theme
        )

        review = ReviewData(
            review_type="Monthly",
            date=target_date,
            title=f"Monthly Review - {target_date.strftime('%B %Y')}",
            content_blocks=blocks
        )

        result = manager.create_review_page(review)
        print(json.dumps(result, indent=2))

    elif cmd == "test":
        print("Testing review creation with sample data...")

        target_date = date.today()

        blocks = build_daily_review_blocks(
            target_date,
            tasks=["Complete project proposal", "Review pull requests", "Call dentist"],
            events=["9:00 AM - Team standup", "2:00 PM - Customer call"],
            followup={
                "person_name": "Gage Robinson",
                "household": "Robinson Household",
                "phone": "(254) 541-1950",
                "email": "theanomalyg@gmail.com",
                "theme": "Spiritual Growth at Home",
                "theme_questions": [
                    "How has your family been growing spiritually?",
                    "What devotional practices work for your household?"
                ]
            },
            dates=["Feb 8 - Mom's birthday", "Feb 14 - Valentine's Day"]
        )

        review = ReviewData(
            review_type="Daily",
            date=target_date,
            title=f"Daily Review - {target_date.strftime('%Y-%m-%d')}",
            content_blocks=blocks
        )

        result = manager.create_review_page(review)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
