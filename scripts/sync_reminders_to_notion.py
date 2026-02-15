#!/usr/bin/env python3
"""Sync Apple Reminders to Notion Personal Tasks database."""

import os
import requests
from datetime import datetime

NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
PERSONAL_TASKS_DB = '2f9ff6d0-ac74-816f-9c57-f8cd7c850208'

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

def create_task(title: str, priority: str, task_type: str, due_date: str, icon: str = None):
    """Create a personal task in Notion."""
    url = 'https://api.notion.com/v1/pages'

    data = {
        'parent': {'database_id': PERSONAL_TASKS_DB},
        'properties': {
            'Name': {'title': [{'text': {'content': title}}]},
            'Priority': {'select': {'name': priority}},
            'Task type': {'multi_select': [{'name': task_type}]},
            'Status': {'select': {'name': 'Not started'}},
            'Due date': {'date': {'start': due_date}}
        }
    }

    if icon:
        data['icon'] = {'emoji': icon}

    response = requests.post(url, headers=HEADERS, json=data)

    if response.status_code == 200:
        page = response.json()
        print(f"✅ Created: {title}")
        print(f"   URL: {page.get('url')}")
        return page
    else:
        print(f"❌ Failed to create: {title}")
        print(f"   Error: {response.text}")
        return None

def main():
    """Sync important reminders to Notion."""
    if not NOTION_API_KEY:
        print("Error: NOTION_API_KEY not set")
        return

    print("Syncing Apple Reminders to Notion Personal Tasks...\n")

    # Reminders to sync (from Apple Reminders)
    reminders = [
        {
            'title': 'Pay property taxes (OVERDUE from Jan 15)',
            'priority': 'High',
            'task_type': '💰 Finance',
            'due_date': '2026-02-03',
            'icon': '🏠'
        },
        {
            'title': 'Check upstairs air conditioner',
            'priority': 'High',
            'task_type': '🏠 Home',
            'due_date': '2026-02-07',
            'icon': '❄️'
        },
        {
            'title': 'Pause Disney+ subscription',
            'priority': 'Medium',
            'task_type': '💰 Finance',
            'due_date': '2026-02-21',
            'icon': '📺'
        },
        {
            'title': 'Temple Civic Theatre - Dear Jack, Dear Louise Audition',
            'priority': 'Medium',
            'task_type': '👥 Social',
            'due_date': '2026-02-15',
            'icon': '🎭'
        },
        {
            'title': 'Plan Courtney\'s Birthday Party (Bon Bon Market theme)',
            'priority': 'Medium',
            'task_type': '👥 Social',
            'due_date': '2026-04-15',
            'icon': '🎂'
        },
        {
            'title': 'Temple Civic Theatre - Oklahoma Audition',
            'priority': 'Low',
            'task_type': '👥 Social',
            'due_date': '2026-04-20',
            'icon': '🎭'
        }
    ]

    created = 0
    for reminder in reminders:
        result = create_task(
            title=reminder['title'],
            priority=reminder['priority'],
            task_type=reminder['task_type'],
            due_date=reminder['due_date'],
            icon=reminder.get('icon')
        )
        if result:
            created += 1

    print(f"\n✅ Synced {created}/{len(reminders)} reminders to Notion")

if __name__ == '__main__':
    main()
