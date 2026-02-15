#!/usr/bin/env python3
"""
Journal Helper - Quick journal operations using Notion API directly.

Usage:
    python scripts/journal_helper.py add "Your thought here"
    python scripts/journal_helper.py habit read_bible
    python scripts/journal_helper.py habit prayed
    python scripts/journal_helper.py show

Habits: read_bible, prayed, journaled, read_book, flipped_switch
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional

import requests

NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
JOURNAL_DATABASE_ID = "17dff6d0-ac74-802c-b641-f867c9cf72c2"
JOURNAL_DATA_SOURCE_ID = "95459472-1827-410a-973e-2f3a8ecdb3df"

HABIT_PROPERTIES = {
    "read_bible": "Read Bible?",
    "prayed": "Prayed?",
    "journaled": "Journaled?",
    "read_book": "Read a book?",
    "flipped_switch": "Flipped the Switch?",
}


class NotionJournalClient:
    """Simple Notion client for journal operations."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def find_today_entry(self) -> Optional[dict]:
        """Find today's journal entry."""
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/databases/{JOURNAL_DATABASE_ID}/query"
        payload = {
            "filter": {
                "property": "Name",
                "title": {"equals": today}
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0] if results else None

    def create_today_entry(self) -> dict:
        """Create today's journal entry."""
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/pages"
        payload = {
            "parent": {"database_id": JOURNAL_DATABASE_ID},
            "icon": {"type": "emoji", "emoji": "📆"},
            "properties": {
                "Name": {"title": [{"text": {"content": today}}]},
                "Journaled?": {"checkbox": True}
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def append_thought(self, page_id: str, thought: str) -> dict:
        """Append a timestamped thought to a journal entry."""
        timestamp = datetime.now().strftime("%H:%M")
        url = f"{self.base_url}/blocks/{page_id}/children"
        payload = {
            "children": [{
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"**{timestamp}** {thought}"}
                    }]
                }
            }]
        }
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def update_habit(self, page_id: str, habit_key: str, value: bool = True) -> dict:
        """Update a habit checkbox."""
        if habit_key not in HABIT_PROPERTIES:
            raise ValueError(f"Unknown habit: {habit_key}. Valid: {list(HABIT_PROPERTIES.keys())}")

        property_name = HABIT_PROPERTIES[habit_key]
        url = f"{self.base_url}/pages/{page_id}"
        payload = {
            "properties": {
                property_name: {"checkbox": value}
            }
        }
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_habit_status(self, page: dict) -> dict:
        """Get habit completion status from a page."""
        props = page.get("properties", {})
        return {
            habit_key: props.get(prop_name, {}).get("checkbox", False)
            for habit_key, prop_name in HABIT_PROPERTIES.items()
        }

    def get_page_content(self, page_id: str) -> list:
        """Get the content blocks of a page."""
        url = f"{self.base_url}/blocks/{page_id}/children"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("results", [])


def format_habits(habits: dict) -> str:
    """Format habit status for display."""
    lines = []
    for habit_key, completed in habits.items():
        status = "[x]" if completed else "[ ]"
        label = HABIT_PROPERTIES[habit_key]
        lines.append(f"  {status} {label}")
    return "\n".join(lines)


def main():
    if not NOTION_API_KEY:
        print("Error: NOTION_API_KEY or NOTION_TOKEN not set")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    client = NotionJournalClient(NOTION_API_KEY)
    command = sys.argv[1].lower()

    # Find or create today's entry
    entry = client.find_today_entry()

    if command == "add":
        if len(sys.argv) < 3:
            print("Usage: python journal_helper.py add 'Your thought here'")
            sys.exit(1)

        thought = " ".join(sys.argv[2:])

        if not entry:
            print("Creating today's journal entry...")
            entry = client.create_today_entry()

        page_id = entry["id"]
        client.append_thought(page_id, thought)
        client.update_habit(page_id, "journaled", True)

        print(f"Added at {datetime.now().strftime('%H:%M')}: {thought}")
        print(f"Entry: {entry.get('url', 'https://www.notion.so/' + page_id.replace('-', ''))}")
        print("\nToday's habits:")

        # Refresh entry to get updated habits
        entry = client.find_today_entry()
        habits = client.get_habit_status(entry)
        print(format_habits(habits))

    elif command == "habit":
        if len(sys.argv) < 3:
            print(f"Usage: python journal_helper.py habit <habit_name>")
            print(f"Valid habits: {', '.join(HABIT_PROPERTIES.keys())}")
            sys.exit(1)

        habit_key = sys.argv[2].lower().replace(" ", "_")

        if not entry:
            print("Creating today's journal entry...")
            entry = client.create_today_entry()

        page_id = entry["id"]
        client.update_habit(page_id, habit_key, True)

        print(f"Updated: {HABIT_PROPERTIES.get(habit_key, habit_key)} = True")
        print(f"Entry: {entry.get('url', 'https://www.notion.so/' + page_id.replace('-', ''))}")
        print("\nToday's habits:")

        # Refresh entry
        entry = client.find_today_entry()
        habits = client.get_habit_status(entry)
        print(format_habits(habits))

    elif command == "show":
        if not entry:
            print("No journal entry for today yet.")
            print("Use: python journal_helper.py add 'Your first thought'")
            sys.exit(0)

        page_id = entry["id"]
        url = entry.get("url", f"https://www.notion.so/{page_id.replace('-', '')}")

        print(f"Today's Journal ({datetime.now().strftime('%Y-%m-%d')})")
        print(f"Link: {url}")
        print("-" * 40)

        # Get habits
        habits = client.get_habit_status(entry)
        print("Habits:")
        print(format_habits(habits))
        print("-" * 40)

        # Get content
        blocks = client.get_page_content(page_id)
        if blocks:
            print("Content:")
            for block in blocks:
                if block.get("type") == "paragraph":
                    texts = block.get("paragraph", {}).get("rich_text", [])
                    content = "".join(t.get("plain_text", "") for t in texts)
                    if content:
                        print(f"  {content}")
        else:
            print("No content yet.")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
