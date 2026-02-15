#!/usr/bin/env python3
"""
Notion Cache Sync - Sync Notion databases to local markdown files for fast Claude access.

Usage:
    python scripts/notion_cache_sync.py [--full]

Options:
    --full    Full sync of all databases (default: just active/open items)

This script syncs key Notion databases to local markdown files in /workspace/cache/notion/
so Claude Code can quickly read context without API calls.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# Configuration from CLAUDE.md
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
CACHE_DIR = Path("/workspace/cache/notion")
DB_PATH = CACHE_DIR / "notion_cache.db"

# Database IDs from CLAUDE.md
DATABASES = {
    "work_tasks": "2f9ff6d0-ac74-8109-bd55-c2e0a10dc807",
    "personal_tasks": "2f9ff6d0-ac74-816f-9c57-f8cd7c850208",
    "sprints": "2f9ff6d0-ac74-8121-a6f8-f0df1bf3e57c",
    "objectives": "16eff6d0-ac74-811e-83ec-d3bea3ef75f6",
    "key_results": "16eff6d0-ac74-81ef-91da-f5867df63ef4",
    "journal": "17dff6d0-ac74-802c-b641-f867c9cf72c2",
    "people": "184ff6d0-ac74-80cb-a533-c7cb2fd690ab",
    "inbox": "23eff6d0-ac74-80a2-a283-e8f6f0d58097",
}

# Current sprint info
CURRENT_SPRINT = {
    "name": "Week 5",
    "id": "2f9ff6d0-ac74-8151-bf73-e185b8b0a0ea",
    "start": "2026-01-27",
    "end": "2026-02-02",
}

HEATH_USER_ID = "38065d15-3eb5-4850-b9be-ea0ac658da58"


class NotionClient:
    """Simple Notion API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def query_database(
        self, database_id: str, filter_obj: Optional[dict] = None, sorts: Optional[list] = None
    ) -> list:
        """Query a Notion database."""
        url = f"{self.base_url}/databases/{database_id}/query"
        payload = {}
        if filter_obj:
            payload["filter"] = filter_obj
        if sorts:
            payload["sorts"] = sorts

        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

            all_results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        return all_results

    def get_page(self, page_id: str) -> dict:
        """Get a single page."""
        url = f"{self.base_url}/pages/{page_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


def extract_title(properties: dict) -> str:
    """Extract title from Notion properties."""
    for key in ["Name", "Title", "title"]:
        if key in properties:
            title_prop = properties[key]
            if title_prop.get("type") == "title":
                title_list = title_prop.get("title", [])
                if title_list:
                    return title_list[0].get("plain_text", "Untitled")
    return "Untitled"


def extract_text(prop: dict) -> str:
    """Extract text from various property types."""
    prop_type = prop.get("type")

    if prop_type == "rich_text":
        texts = prop.get("rich_text", [])
        return " ".join(t.get("plain_text", "") for t in texts)
    elif prop_type == "title":
        titles = prop.get("title", [])
        return " ".join(t.get("plain_text", "") for t in titles)
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif prop_type == "multi_select":
        return ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
    elif prop_type == "checkbox":
        return "Yes" if prop.get("checkbox") else "No"
    elif prop_type == "date":
        date_obj = prop.get("date")
        if date_obj:
            return date_obj.get("start", "")
        return ""
    elif prop_type == "number":
        return str(prop.get("number", ""))
    elif prop_type == "status":
        status = prop.get("status")
        return status.get("name", "") if status else ""
    elif prop_type == "people":
        people = prop.get("people", [])
        return ", ".join(p.get("name", "") for p in people)
    elif prop_type == "relation":
        relations = prop.get("relation", [])
        return f"[{len(relations)} linked]"

    return ""


def sync_work_tasks(client: NotionClient, full_sync: bool = False) -> str:
    """Sync work tasks to markdown."""
    print("Syncing work tasks...")

    # Query open tasks (not checked)
    filter_obj = {"property": "Checkbox", "checkbox": {"equals": False}}
    if not full_sync:
        # Only current sprint tasks
        filter_obj = {
            "and": [
                {"property": "Checkbox", "checkbox": {"equals": False}},
            ]
        }

    tasks = client.query_database(
        DATABASES["work_tasks"],
        filter_obj=filter_obj,
        sorts=[{"property": "Due Date", "direction": "ascending"}]
    )

    # Group by tag
    by_tag = {}
    no_tag = []

    for task in tasks:
        props = task.get("properties", {})
        title = extract_title(props)
        tags = props.get("Tags", {}).get("multi_select", [])
        due = extract_text(props.get("Due Date", {}))
        person = extract_text(props.get("Person", {}))
        sprint_rel = props.get("Sprint", {}).get("relation", [])

        task_info = {
            "id": task["id"],
            "title": title,
            "due": due,
            "person": person,
            "sprint_count": len(sprint_rel),
            "url": task.get("url", ""),
        }

        if tags:
            for tag in tags:
                tag_name = tag.get("name", "Other")
                if tag_name not in by_tag:
                    by_tag[tag_name] = []
                by_tag[tag_name].append(task_info)
        else:
            no_tag.append(task_info)

    # Generate markdown
    md = f"""# Work Tasks (Open)

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Total open tasks: {len(tasks)}*

"""

    # Priority order for tags
    tag_order = ["Build", "Serve", "Sell", "Raise", "Admin", "META", "Learn", "Measure", "Maintain", "Backlog"]

    for tag in tag_order:
        if tag in by_tag:
            md += f"\n## {tag}\n\n"
            for t in by_tag[tag]:
                due_str = f" (Due: {t['due']})" if t['due'] else ""
                md += f"- [ ] **{t['title']}**{due_str}\n"
            del by_tag[tag]

    # Any remaining tags
    for tag, task_list in by_tag.items():
        md += f"\n## {tag}\n\n"
        for t in task_list:
            due_str = f" (Due: {t['due']})" if t['due'] else ""
            md += f"- [ ] **{t['title']}**{due_str}\n"

    if no_tag:
        md += "\n## Untagged\n\n"
        for t in no_tag:
            due_str = f" (Due: {t['due']})" if t['due'] else ""
            md += f"- [ ] **{t['title']}**{due_str}\n"

    # Write to file
    output_path = CACHE_DIR / "tasks" / "work_tasks.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def sync_personal_tasks(client: NotionClient, full_sync: bool = False) -> str:
    """Sync personal tasks to markdown."""
    print("Syncing personal tasks...")

    # Query all tasks then filter locally (Status filter can be tricky)
    tasks = client.query_database(
        DATABASES["personal_tasks"],
        sorts=[
            {"property": "Priority", "direction": "ascending"},
        ]
    )

    # Filter out completed tasks locally
    tasks = [t for t in tasks if extract_text(t.get("properties", {}).get("Status", {})) != "Done"]

    # Group by priority
    by_priority = {"High": [], "Medium": [], "Low": [], "None": []}

    for task in tasks:
        props = task.get("properties", {})
        title = extract_title(props)
        priority = extract_text(props.get("Priority", {})) or "None"
        due = extract_text(props.get("Due date", {}))
        status = extract_text(props.get("Status", {}))
        task_type = extract_text(props.get("Task type", {}))

        task_info = {
            "title": title,
            "due": due,
            "status": status,
            "type": task_type,
        }

        if priority in by_priority:
            by_priority[priority].append(task_info)
        else:
            by_priority["None"].append(task_info)

    # Generate markdown
    md = f"""# Personal Tasks (Open)

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Total open tasks: {len(tasks)}*

"""

    for priority in ["High", "Medium", "Low", "None"]:
        task_list = by_priority[priority]
        if task_list:
            emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "None": "⚪"}.get(priority, "")
            md += f"\n## {emoji} {priority} Priority\n\n"
            for t in task_list:
                due_str = f" (Due: {t['due']})" if t['due'] else ""
                status_str = f" [{t['status']}]" if t['status'] and t['status'] != "Not started" else ""
                type_str = f" `{t['type']}`" if t['type'] else ""
                md += f"- [ ] **{t['title']}**{type_str}{due_str}{status_str}\n"

    # Write to file
    output_path = CACHE_DIR / "tasks" / "personal_tasks.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def sync_current_sprint(client: NotionClient) -> str:
    """Sync current sprint summary."""
    print("Syncing current sprint...")

    # Get sprint tasks
    filter_obj = {
        "and": [
            {"property": "Sprint", "relation": {"contains": CURRENT_SPRINT["id"]}},
        ]
    }

    tasks = client.query_database(
        DATABASES["work_tasks"],
        filter_obj=filter_obj,
        sorts=[{"property": "Tags", "direction": "ascending"}]
    )

    completed = []
    in_progress = []

    for task in tasks:
        props = task.get("properties", {})
        title = extract_title(props)
        done = props.get("Checkbox", {}).get("checkbox", False)
        tags = extract_text(props.get("Tags", {}))
        due = extract_text(props.get("Due Date", {}))
        person = extract_text(props.get("Person", {}))

        task_info = {
            "title": title,
            "tags": tags,
            "due": due,
            "person": person,
        }

        if done:
            completed.append(task_info)
        else:
            in_progress.append(task_info)

    total = len(tasks)
    done_count = len(completed)
    progress_pct = (done_count / total * 100) if total > 0 else 0

    md = f"""# Current Sprint: {CURRENT_SPRINT['name']}

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

## Overview
- **Sprint**: {CURRENT_SPRINT['name']}
- **Dates**: {CURRENT_SPRINT['start']} to {CURRENT_SPRINT['end']}
- **Progress**: {done_count}/{total} tasks ({progress_pct:.0f}%)

## Open Tasks ({len(in_progress)})

"""

    for t in in_progress:
        tags_str = f" `{t['tags']}`" if t['tags'] else ""
        due_str = f" (Due: {t['due']})" if t['due'] else ""
        md += f"- [ ] **{t['title']}**{tags_str}{due_str}\n"

    md += f"\n## Completed ({len(completed)})\n\n"

    for t in completed:
        md += f"- [x] ~~{t['title']}~~\n"

    # Write to file
    output_path = CACHE_DIR / "sprint" / "current_sprint.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def sync_okrs(client: NotionClient) -> str:
    """Sync OKRs (Objectives and Key Results)."""
    print("Syncing OKRs...")

    # Get objectives
    objectives = client.query_database(DATABASES["objectives"])

    # Get key results
    key_results = client.query_database(DATABASES["key_results"])

    # Build objective -> key results mapping
    obj_map = {}
    for obj in objectives:
        obj_id = obj["id"]
        props = obj.get("properties", {})
        title = extract_title(props)

        obj_map[obj_id] = {
            "title": title,
            "key_results": [],
        }

    # Add key results to objectives
    for kr in key_results:
        props = kr.get("properties", {})
        title = extract_title(props)
        progress = extract_text(props.get("Progress", {})) or "0"
        obj_rel = props.get("Objective", {}).get("relation", [])

        kr_info = {
            "title": title,
            "progress": progress,
        }

        for rel in obj_rel:
            obj_id = rel.get("id")
            if obj_id in obj_map:
                obj_map[obj_id]["key_results"].append(kr_info)

    md = f"""# Objectives & Key Results (OKRs)

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

"""

    for obj_id, obj in obj_map.items():
        md += f"\n## 🎯 {obj['title']}\n\n"

        if obj["key_results"]:
            for kr in obj["key_results"]:
                progress = kr["progress"]
                md += f"- **{kr['title']}** - Progress: {progress}\n"
        else:
            md += "*No key results defined*\n"

    # Write to file
    output_path = CACHE_DIR / "okrs" / "objectives.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def sync_recent_journal(client: NotionClient, days: int = 7) -> str:
    """Sync recent journal entries."""
    print(f"Syncing journal entries (last {days} days)...")

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    filter_obj = {
        "property": "Date",
        "date": {"on_or_after": cutoff}
    }

    entries = client.query_database(
        DATABASES["journal"],
        filter_obj=filter_obj,
        sorts=[{"property": "Date", "direction": "descending"}]
    )

    md = f"""# Recent Journal Entries

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Showing last {days} days*

"""

    for entry in entries:
        props = entry.get("properties", {})
        title = extract_title(props)
        date = extract_text(props.get("Date", {}))

        md += f"\n## {date}: {title}\n\n"

    if not entries:
        md += "*No journal entries in this period*\n"

    # Write to file
    output_path = CACHE_DIR / "journal" / "recent.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def sync_inbox(client: NotionClient) -> str:
    """Sync inbox items for quick capture review."""
    print("Syncing inbox...")

    # Get all inbox items, sorted by creation date (newest first)
    items = client.query_database(
        DATABASES["inbox"],
        sorts=[{"timestamp": "created_time", "direction": "descending"}]
    )

    md = f"""# Inbox

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Total items: {len(items)}*

Quick capture items awaiting processing. Review and move to appropriate database.

"""

    if items:
        for item in items:
            props = item.get("properties", {})
            title = extract_title(props)
            created = item.get("created_time", "")[:10]  # Just the date part

            # Try to get any notes/description
            notes = ""
            for key in ["Notes", "Description", "Content", "Text"]:
                if key in props:
                    notes = extract_text(props[key])
                    if notes:
                        break

            md += f"- **{title}**"
            if created:
                md += f" *(added {created})*"
            md += "\n"
            if notes:
                md += f"  - {notes[:200]}{'...' if len(notes) > 200 else ''}\n"
    else:
        md += "*Inbox is empty - great job!*\n"

    # Write to file
    output_path = CACHE_DIR / "inbox" / "inbox.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def create_summary(client: NotionClient) -> str:
    """Create a quick summary file for Claude."""
    print("Creating summary...")

    # Count open tasks
    work_open = len(client.query_database(
        DATABASES["work_tasks"],
        filter_obj={"property": "Checkbox", "checkbox": {"equals": False}}
    ))

    personal_tasks = client.query_database(DATABASES["personal_tasks"])
    personal_open = len([t for t in personal_tasks if extract_text(t.get("properties", {}).get("Status", {})) != "Done"])

    # Count inbox items
    inbox_items = len(client.query_database(DATABASES["inbox"]))

    md = f"""# Notion Cache Summary

*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

## Quick Stats
- **Open Work Tasks**: {work_open}
- **Open Personal Tasks**: {personal_open}
- **Inbox Items**: {inbox_items}
- **Current Sprint**: {CURRENT_SPRINT['name']} ({CURRENT_SPRINT['start']} to {CURRENT_SPRINT['end']})

## Cache Files
- `tasks/work_tasks.md` - All open work tasks by tag
- `tasks/personal_tasks.md` - All open personal tasks by priority
- `sprint/current_sprint.md` - Current sprint tasks and progress
- `okrs/objectives.md` - Active OKRs with key results
- `journal/recent.md` - Journal entries from last 7 days
- `inbox/inbox.md` - Quick capture items awaiting processing

## How to Use
Claude can read these files directly with the Read tool for fast context.
Run `python scripts/notion_cache_sync.py` to refresh the cache.

## Database Reference
| Database | ID |
|----------|---|
| Work Tasks | `{DATABASES['work_tasks']}` |
| Personal Tasks | `{DATABASES['personal_tasks']}` |
| Sprints | `{DATABASES['sprints']}` |
| Objectives | `{DATABASES['objectives']}` |
| Key Results | `{DATABASES['key_results']}` |
| Journal | `{DATABASES['journal']}` |
| Inbox | `{DATABASES['inbox']}` |
"""

    output_path = CACHE_DIR / "SUMMARY.md"
    output_path.write_text(md)
    print(f"  Written to {output_path}")

    return md


def init_sqlite_db():
    """Initialize SQLite database for detailed caching."""
    print("Initializing SQLite database...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT,
            database TEXT,
            status TEXT,
            priority TEXT,
            tags TEXT,
            due_date TEXT,
            person TEXT,
            sprint_id TEXT,
            created_time TEXT,
            last_edited_time TEXT,
            properties_json TEXT
        )
    """)

    # Sync metadata
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"  Database ready at {DB_PATH}")


def main():
    """Main sync function."""
    full_sync = "--full" in sys.argv

    print("=" * 50)
    print("Notion Cache Sync")
    print("=" * 50)

    if not NOTION_API_KEY:
        print("ERROR: NOTION_API_KEY or NOTION_TOKEN environment variable not set")
        print("Set it with: export NOTION_API_KEY='your_token'")
        sys.exit(1)

    # Ensure cache directories exist
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ["tasks", "sprint", "okrs", "journal", "people", "inbox"]:
        (CACHE_DIR / subdir).mkdir(exist_ok=True)

    # Initialize
    client = NotionClient(NOTION_API_KEY)
    init_sqlite_db()

    # Sync each database
    try:
        sync_work_tasks(client, full_sync)
        sync_personal_tasks(client, full_sync)
        sync_current_sprint(client)
        sync_okrs(client)
        sync_recent_journal(client)
        sync_inbox(client)
        create_summary(client)

        print("\n" + "=" * 50)
        print("Sync complete!")
        print(f"Cache location: {CACHE_DIR}")
        print("=" * 50)

    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Notion API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
