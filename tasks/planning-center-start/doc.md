# Planning Center Integration - Technical Document

## Summary

This integration connects Planning Center's People and Services APIs to Heath's personal assistant system. It enables:
- Natural language people/family search via Telegram or Claude Code
- CRM-like contact management with notes synced to Notion People DB
- Smart follow-up question generation based on interaction history and monthly themes
- Distributed monthly follow-ups (one adult per household) surfaced in daily planning
- Automatic reminders for service schedules and PCO tasks

## Key Decisions

### Decision 1: MCP Server vs Python Scripts
- **Options considered**:
  A) MCP server only (tools for agent)
  B) Python scripts only (for automation)
  C) Both - Python client + MCP server wrapper
- **Chosen**: C - Both
- **Rationale**: Python scripts can run in daily automation workflows, while MCP server enables interactive agent queries via Telegram and Claude Code.

### Decision 2: Contact Notes Storage
- **Options considered**:
  A) Store in Notion People database (existing)
  B) Store in local JSON file
  C) Use PCO notes/custom fields
- **Chosen**: A - Notion People Database
- **Rationale**: Leverages existing People DB (`184ff6d0-ac74-80cb-a533-c7cb2fd690ab`), provides rich text support, accessible via Notion MCP, and integrates with broader life management system.

### Decision 3: Follow-up Tracking
- **Options considered**:
  A) Separate Notion database for follow-up tracking
  B) Properties on Notion People pages
  C) Local JSON file with follow-up state
- **Chosen**: B - Properties on Notion People pages
- **Rationale**: Keeps all contact info in one place, allows querying via Notion API, and visible in Notion UI for manual review.

### Decision 4: Monthly Theme Storage
- **Options considered**:
  A) Add to CLAUDE.md
  B) Separate config file
  C) Notion page/database
- **Chosen**: A - CLAUDE.md
- **Rationale**: Simple, agent always has access, easy to update. Can include theme and suggested questions.

### Decision 5: Reminder Deduplication
- **Options considered**:
  A) Check reminder title before creating
  B) Store mapping of PCO ID → Reminder ID locally
  C) Use reminder notes field for PCO reference
- **Chosen**: C - Notes field
- **Rationale**: Apple Reminders MCP can search by notes, allowing lookup of existing reminders by PCO ID

## Technical Details

### Architecture / Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Planning Center │────▶│  pco_client.py   │────▶│ Apple Reminders │
│     APIs        │     │  (Python core)   │     │     (MCP)       │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
           ┌──────────────────┐     ┌──────────────────┐
           │  Notion People   │     │   MCP Server     │
           │  DB (CRM)        │     │  (Agent Tools)   │
           └──────────────────┘     └──────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 ▼
                        ┌──────────────────┐
                        │  Daily Routine   │
                        │  + Telegram Bot  │
                        └──────────────────┘
```

### API Authentication

```python
import os
import requests

PCO_APP_ID = os.getenv("PLANNING_CENTER_CLIENT_ID")
PCO_SECRET = os.getenv("PLANNING_CETNER_SECRET_KEY")  # Note typo in env
BASE_URL = "https://api.planningcenteronline.com"

def pco_get(endpoint, params=None):
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        auth=(PCO_APP_ID, PCO_SECRET)
    )
    response.raise_for_status()
    return response.json()
```

### Key Endpoints

| Function | Endpoint | Notes |
|----------|----------|-------|
| Shepherding list | `GET /people/v2/lists/3015465/people` | Include phone_numbers, emails, households |
| Search people | `GET /people/v2/people?where[search_name]=...` | |
| Person details | `GET /people/v2/people/{id}?include=phone_numbers,emails,households` | |
| Household members | `GET /people/v2/households/{id}/people` | Get all family members |
| My schedules | `GET /services/v2/people/33065814/schedules?filter=future` | |
| My tasks | `GET /services/v2/people/33065814/assigned_tasks?filter=incomplete` | |

### Data Structures

```python
@dataclass
class ShepherdingContact:
    pco_id: str
    name: str
    phone: str | None
    email: str | None
    household_id: str | None
    household_name: str | None
    is_adult: bool  # For monthly follow-up targeting
    notion_page_id: str | None  # Link to Notion People DB

@dataclass
class Household:
    household_id: str
    name: str  # e.g., "Robertson"
    members: list[HouseholdMember]

@dataclass
class HouseholdMember:
    pco_id: str
    name: str
    relationship: str  # e.g., "Primary Contact", "Child", "Spouse"
    age_bracket: str | None  # "adult", "child", "youth"

@dataclass
class ContactNote:
    timestamp: datetime
    note: str
    suggested_followups: list[str]  # AI-generated questions

@dataclass
class MonthlyFollowup:
    household_id: str
    target_person_id: str  # Adult to contact
    target_person_name: str
    assigned_date: date
    completed: bool
    last_reminder_date: date | None
```

### Notion People DB Schema (Additions)

Add these properties to People DB (`184ff6d0-ac74-80cb-a533-c7cb2fd690ab`):

| Property | Type | Purpose |
|----------|------|---------|
| PCO ID | Text | Link to Planning Center person |
| Last Contact | Date | When last contacted |
| Contact Notes | Rich Text | Timestamped interaction notes |
| Follow-up Questions | Rich Text | AI-suggested questions for next contact |
| Household | Text | Family/household name |

### Monthly Follow-up Distribution Algorithm

```python
def distribute_monthly_followups(households: list[Household], month: date) -> dict[date, list[str]]:
    """
    Distribute one adult per household across the month's days.

    Returns: {date: [person_ids to contact that day]}
    """
    # Get working days in month (exclude Sundays)
    working_days = get_working_days(month)

    # Select one adult per household
    targets = []
    for household in households:
        adults = [m for m in household.members if m.age_bracket == "adult"]
        if adults:
            # Rotate which adult to contact (based on last contact)
            targets.append(select_next_adult(adults))

    # Distribute evenly across days
    days_needed = len(targets)
    days_available = len(working_days)

    distribution = {}
    for i, target in enumerate(targets):
        day_index = (i * days_available) // days_needed
        day = working_days[day_index]
        distribution.setdefault(day, []).append(target)

    return distribution

def check_and_resurface(followups: list[MonthlyFollowup], today: date):
    """Re-surface incomplete follow-ups after 7 days."""
    for followup in followups:
        if not followup.completed:
            days_since = (today - followup.assigned_date).days
            days_since_reminder = (today - followup.last_reminder_date).days if followup.last_reminder_date else 999

            if days_since >= 7 and days_since_reminder >= 7:
                create_followup_reminder(followup)
                followup.last_reminder_date = today
```

### Follow-up Reminder Content

```python
def generate_followup_reminder(person: ShepherdingContact, theme: str) -> str:
    """Generate reminder content with smart questions."""

    # Get last contact notes from Notion
    history = get_contact_history(person.notion_page_id)

    # Generate questions based on history
    history_questions = generate_followup_questions(history)

    # Get theme-based questions
    theme_questions = get_theme_questions(theme)

    reminder = f"""
Follow up with {person.name}
📞 {person.phone}
📧 {person.email}

📝 From last conversation:
{chr(10).join(f'- {q}' for q in history_questions[:2])}

🎯 This month's theme ({theme}):
{chr(10).join(f'- {q}' for q in theme_questions[:2])}
"""
    return reminder
```

### MCP Tool Definitions

```json
{
  "tools": [
    {
      "name": "pco_search_people",
      "description": "Search Planning Center people by name. Supports family searches like 'Robertson kids'.",
      "parameters": {
        "query": "string - name or family to search for",
        "include_family": "boolean - whether to include household members (default true)"
      }
    },
    {
      "name": "pco_get_household",
      "description": "Get all members of a household/family",
      "parameters": {
        "household_id": "string - PCO household ID",
        "or_person_id": "string - get household for this person"
      }
    },
    {
      "name": "pco_log_contact",
      "description": "Log a contact note for a person (saves to Notion)",
      "parameters": {
        "person_name": "string - name of person contacted",
        "note": "string - what was discussed",
        "contact_method": "string - call, text, in-person, etc."
      }
    },
    {
      "name": "pco_get_contact_history",
      "description": "Get contact history and notes for a person",
      "parameters": {
        "person_name": "string - name of person"
      }
    },
    {
      "name": "pco_get_shepherding_list",
      "description": "Get Heath's full shepherding list with contact info",
      "parameters": {}
    },
    {
      "name": "pco_get_todays_followups",
      "description": "Get today's scheduled follow-up contacts",
      "parameters": {}
    },
    {
      "name": "pco_get_my_schedule",
      "description": "Get Heath's upcoming service schedule",
      "parameters": {
        "days_ahead": "number - how many days to look ahead (default 30)"
      }
    }
  ]
}
```

### Monthly Theme Configuration (CLAUDE.md addition)

```markdown
### Shepherding Monthly Themes

Current month theme and suggested questions:

**February 2026: "Spiritual Growth at Home"**
- How is your family's spiritual rhythm going?
- Have you been able to do family worship or devotions?
- What's been encouraging in your walk with God lately?
- Any prayer requests for your household?

**March 2026: "Community & Relationships"**
- TBD
```

## Open Questions

- [x] Where to store contact notes? → Notion People DB
- [x] Where to store monthly themes? → CLAUDE.md
- [ ] Which service types to monitor (all or specific ones)?
- [ ] Should follow-up questions be AI-generated each time or templated?
- [ ] How to handle new people added to shepherding list mid-month?

## References

- [PCO API Docs](https://developer.planning.center/docs/)
- [PCO People API](https://developer.planning.center/docs/#/apps/people)
- [PCO Services API](https://developer.planning.center/docs/#/apps/services)
- Existing script: `/workspace/scripts/pco_find_person.py`
- Notion People DB: `184ff6d0-ac74-80cb-a533-c7cb2fd690ab`
