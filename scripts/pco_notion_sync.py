#!/usr/bin/env python3
"""
PCO to Notion CRM Sync

Syncs Planning Center contacts to Notion People database and manages contact notes.
"""

import os
import json
import re
from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Import PCO client
from pco_client import PCOClient, Person

# Notion configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PEOPLE_DB_ID = "184ff6d0-ac74-80cb-a533-c7cb2fd690ab"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


@dataclass
class NotionPerson:
    """Represents a person in the Notion People database."""
    page_id: str
    name: str
    pco_id: Optional[str] = None
    last_contact: Optional[date] = None
    notes: list[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


class NotionCRM:
    """Manages contact data in Notion People database."""

    def __init__(self):
        if not NOTION_API_KEY:
            raise ValueError("NOTION_API_KEY not found in environment")
        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION
        }
        self.pco_client = PCOClient()

    def _notion_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Notion API."""
        url = f"{NOTION_API_BASE}{endpoint}"
        response = requests.request(
            method, url, headers=self.headers, json=data
        )
        response.raise_for_status()
        return response.json()

    def _format_name_for_notion(self, name: str) -> str:
        """Format name for Notion (e.g., 'John Smith' -> '@JohnSmith')."""
        # Remove spaces and add @ prefix
        parts = name.split()
        return "@" + "".join(parts)

    def _parse_name_from_notion(self, notion_name: str) -> str:
        """Parse name from Notion format (e.g., '@JohnSmith' -> 'John Smith')."""
        # Remove @ and try to split camelCase
        name = notion_name.lstrip("@")
        # Insert space before capital letters
        result = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return result

    def search_notion_person(self, name: str) -> Optional[NotionPerson]:
        """Search for a person in Notion by name."""
        # Try both formats
        search_names = [
            self._format_name_for_notion(name),
            name,
            "@" + name.replace(" ", "")
        ]

        for search_name in search_names:
            try:
                data = self._notion_request("POST", "/search", {
                    "query": search_name,
                    "filter": {"property": "object", "value": "page"}
                })

                for result in data.get("results", []):
                    if result.get("parent", {}).get("database_id", "").replace("-", "") == NOTION_PEOPLE_DB_ID.replace("-", ""):
                        title_prop = result.get("properties", {}).get("Name", {})
                        titles = title_prop.get("title", [])
                        if titles:
                            page_name = titles[0].get("plain_text", "")
                            if search_name.lower() in page_name.lower() or page_name.lower() in search_name.lower():
                                return NotionPerson(
                                    page_id=result["id"],
                                    name=self._parse_name_from_notion(page_name)
                                )
            except Exception:
                continue

        return None

    def get_or_create_notion_person(self, pco_person: Person) -> NotionPerson:
        """Get existing Notion person or create a new one from PCO data."""
        # Try to find existing person
        existing = self.search_notion_person(pco_person.name)
        if existing:
            return existing

        # Create new person
        notion_name = self._format_name_for_notion(pco_person.name)

        page_data = {
            "parent": {"database_id": NOTION_PEOPLE_DB_ID},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": notion_name}}]
                }
            }
        }

        result = self._notion_request("POST", "/pages", page_data)

        new_person = NotionPerson(
            page_id=result["id"],
            name=pco_person.name,
            pco_id=pco_person.pco_id
        )

        # Add initial metadata as page content
        self._add_metadata_block(new_person.page_id, pco_person)

        return new_person

    def _add_metadata_block(self, page_id: str, pco_person: Person):
        """Add PCO metadata as a callout block at the top of the page."""
        phone = pco_person.primary_phone or "N/A"
        email = pco_person.primary_email or "N/A"
        household = pco_person.household_name or "N/A"

        metadata_text = f"PCO ID: {pco_person.pco_id} | Phone: {phone} | Email: {email} | Household: {household}"

        self._notion_request("PATCH", f"/blocks/{page_id}/children", {
            "children": [
                {
                    "type": "callout",
                    "callout": {
                        "icon": {"emoji": "📋"},
                        "rich_text": [{"type": "text", "text": {"content": metadata_text}}]
                    }
                },
                {
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "Contact Notes"}}]
                    }
                },
                {
                    "type": "divider",
                    "divider": {}
                }
            ]
        })

    def log_contact_note(self, person_name: str, note: str, contact_method: str = "call") -> dict:
        """
        Log a contact note for a person.

        Args:
            person_name: Name of the person (will search PCO and Notion)
            note: The note content
            contact_method: How contact was made (call, text, in-person, email)

        Returns:
            dict with status and follow-up suggestions
        """
        # Find person in PCO first
        pco_people = self.pco_client.search_people(person_name, include_family=False)

        if not pco_people:
            return {"status": "error", "message": f"Could not find '{person_name}' in Planning Center"}

        # Use first match (could improve with fuzzy matching)
        pco_person = pco_people[0]

        # Get or create Notion page
        notion_person = self.get_or_create_notion_person(pco_person)

        # Format the note with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        method_emoji = {
            "call": "📞",
            "text": "💬",
            "in-person": "🤝",
            "email": "📧"
        }.get(contact_method.lower(), "📝")

        formatted_note = f"{method_emoji} [{timestamp}] {note}"

        # Add note as a new block
        self._notion_request("PATCH", f"/blocks/{notion_person.page_id}/children", {
            "children": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": formatted_note}}]
                    }
                }
            ]
        })

        # Generate follow-up suggestions based on the note
        follow_ups = self._generate_followup_questions(note)

        return {
            "status": "success",
            "person": pco_person.name,
            "notion_page_id": notion_person.page_id,
            "follow_up_questions": follow_ups
        }

    def _generate_followup_questions(self, note: str) -> list[str]:
        """Generate follow-up questions based on note content."""
        questions = []
        note_lower = note.lower()

        # Look for keywords and generate relevant follow-ups
        if any(word in note_lower for word in ["job", "work", "interview", "career", "promotion"]):
            questions.append("How is the job situation going?")
            if "interview" in note_lower:
                questions.append("How did the interview go?")

        if any(word in note_lower for word in ["sick", "health", "doctor", "surgery", "hospital"]):
            questions.append("How are you feeling now?")
            questions.append("Is there anything I can help with?")

        if any(word in note_lower for word in ["baby", "pregnant", "expecting", "child", "kid"]):
            questions.append("How is the family doing?")

        if any(word in note_lower for word in ["move", "moving", "house", "home", "apartment"]):
            questions.append("How is the new place?")
            questions.append("Have you settled in?")

        if any(word in note_lower for word in ["pray", "prayer", "praying"]):
            questions.append("How can I continue to pray for you?")

        if any(word in note_lower for word in ["struggle", "difficult", "hard", "challenge"]):
            questions.append("How are things going now?")
            questions.append("Is there anything I can do to help?")

        if any(word in note_lower for word in ["church", "small group", "bible study"]):
            questions.append("How is your involvement at church going?")

        # Always include a general follow-up
        if not questions:
            questions.append("How have things been since we last talked?")

        return questions[:3]  # Limit to 3 suggestions

    def get_contact_history(self, person_name: str) -> dict:
        """Get contact history for a person from their Notion page."""
        notion_person = self.search_notion_person(person_name)

        if not notion_person:
            return {"status": "error", "message": f"Could not find '{person_name}' in Notion"}

        # Get page blocks (content)
        try:
            blocks = self._notion_request("GET", f"/blocks/{notion_person.page_id}/children")

            notes = []
            for block in blocks.get("results", []):
                if block.get("type") == "paragraph":
                    texts = block.get("paragraph", {}).get("rich_text", [])
                    if texts:
                        note_text = texts[0].get("plain_text", "")
                        # Look for our formatted notes (with emoji and timestamp)
                        if note_text.startswith(("📞", "💬", "🤝", "📧", "📝")):
                            notes.append(note_text)

            return {
                "status": "success",
                "person": notion_person.name,
                "page_id": notion_person.page_id,
                "notes": notes,
                "total_contacts": len(notes)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync_shepherding_list_to_notion(self, dry_run: bool = True) -> dict:
        """
        Sync all shepherding list contacts to Notion.

        Args:
            dry_run: If True, only report what would be done without making changes

        Returns:
            Summary of sync operation
        """
        people = self.pco_client.get_shepherding_list()

        # Filter to adults only
        adults = [p for p in people if not p.is_child]

        results = {
            "total": len(adults),
            "existing": 0,
            "created": 0,
            "errors": 0,
            "details": []
        }

        for person in adults:
            existing = self.search_notion_person(person.name)

            if existing:
                results["existing"] += 1
                results["details"].append(f"EXISTS: {person.name}")
            else:
                if dry_run:
                    results["details"].append(f"WOULD CREATE: {person.name}")
                else:
                    try:
                        self.get_or_create_notion_person(person)
                        results["created"] += 1
                        results["details"].append(f"CREATED: {person.name}")
                    except Exception as e:
                        results["errors"] += 1
                        results["details"].append(f"ERROR: {person.name} - {e}")

        return results


def main():
    """CLI interface for Notion CRM."""
    import sys

    crm = NotionCRM()

    if len(sys.argv) < 2:
        print("Usage: pco_notion_sync.py <command> [args]")
        print("\nCommands:")
        print("  log <name> <note>      - Log a contact note")
        print("  history <name>         - Get contact history")
        print("  sync [--execute]       - Sync shepherding list to Notion")
        print("  search <name>          - Search for person in Notion")
        return

    cmd = sys.argv[1]

    if cmd == "log" and len(sys.argv) >= 4:
        name = sys.argv[2]
        note = " ".join(sys.argv[3:])
        result = crm.log_contact_note(name, note)
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"Logged note for: {result['person']}")
            print("\nSuggested follow-up questions:")
            for q in result.get('follow_up_questions', []):
                print(f"  - {q}")
        else:
            print(f"Error: {result.get('message')}")

    elif cmd == "history" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        result = crm.get_contact_history(name)
        if result['status'] == 'success':
            print(f"Contact history for {result['person']}:")
            print(f"Total contacts: {result['total_contacts']}\n")
            for note in result['notes']:
                print(f"  {note}")
        else:
            print(f"Error: {result.get('message')}")

    elif cmd == "sync":
        dry_run = "--execute" not in sys.argv
        if dry_run:
            print("DRY RUN - No changes will be made. Use --execute to sync.\n")
        result = crm.sync_shepherding_list_to_notion(dry_run=dry_run)
        print(f"Shepherding List Sync Results:")
        print(f"  Total adults: {result['total']}")
        print(f"  Already in Notion: {result['existing']}")
        print(f"  {'Would create' if dry_run else 'Created'}: {result['total'] - result['existing'] - result['errors']}")
        if result['errors']:
            print(f"  Errors: {result['errors']}")
        print("\nDetails:")
        for detail in result['details'][:20]:  # Limit output
            print(f"  {detail}")
        if len(result['details']) > 20:
            print(f"  ... and {len(result['details']) - 20} more")

    elif cmd == "search" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        result = crm.search_notion_person(name)
        if result:
            print(f"Found: {result.name}")
            print(f"Page ID: {result.page_id}")
        else:
            print(f"No match found for '{name}'")

    else:
        print(f"Unknown command or missing arguments: {cmd}")


if __name__ == "__main__":
    main()
