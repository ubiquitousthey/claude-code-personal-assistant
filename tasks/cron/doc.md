# Cron - Technical Document

## Summary

A scheduled review system that creates Notion pages for each review and sends Telegram messages with links. Reviews are logged permanently in Notion for tracking and reflection. Simple action triggers (like "check stocks") still use Apple Reminders. Scheduling is based on productivity research showing peak performance at ~10 AM, trough at ~3 PM, and creative recovery in late afternoon.

## Key Decisions

### Decision 1: Telegram vs Apple Reminders Channel Selection
- **Options considered**:
  A. All Telegram (consistent channel)
  B. All Apple Reminders (simple)
  C. Hybrid based on interactivity needs
- **Chosen**: C - Hybrid approach
- **Rationale**: Telegram best for reviews requiring conversation (planning, reflection, contact logging). Apple Reminders best for simple action triggers where no agent interaction needed. This avoids notification fatigue while ensuring interactive reviews get proper attention.

### Decision 2: Review Timing
- **Options considered**:
  A. Morning-only reviews
  B. End-of-day reviews
  C. Distributed throughout day based on productivity research
- **Chosen**: C - Research-based distribution
- **Rationale**: [Research shows](https://www.todoist.com/inspiration/daily-schedule) cognitive performance varies ~20% based on time of day. Morning peak (10 AM) for planning, avoid 3 PM trough, use recovery period (4-5 PM) for lighter reviews like financial check.

### Decision 3: Weekly Review Day
- **Options considered**:
  A. Friday afternoon (end of work week)
  B. Sunday evening (prep for week)
  C. Monday morning (start fresh)
- **Chosen**: B - Sunday evening
- **Rationale**: [GTD practitioners](https://www.asianefficiency.com/productivity/gtd-weekly-review/) recommend consistency over specific day. Sunday evening allows processing the week while preparing for Monday. Heath's Sunday schedule already includes church context (shepherding list review fits naturally).

### Decision 4: Preventing Duplicate Reminders
- **Options considered**:
  A. Check for existing reminders before creating
  B. Use unique reference IDs in reminder notes
  C. Time-based deduplication (no reminder if one created today)
- **Chosen**: B + C - Reference IDs with time check
- **Rationale**: Reference IDs (like `cron_daily_2026-02-06`) allow checking for duplicates. Time-based check prevents re-triggering if script runs multiple times.

### Decision 5: Review Storage in Notion
- **Options considered**:
  A. Add to existing Journal database
  B. Create new Reviews database
  C. Use Inbox database
- **Chosen**: B - New Reviews database
- **Rationale**: Reviews have different properties (type, completion status, linked data) than journal entries. Separate database allows filtering by review type, tracking completion rates, and keeping journal for freeform reflection. Telegram message includes direct link to the Notion page.

### Decision 6: Link Reviews to Journal
- **Options considered**:
  A. Relation property on Reviews pointing to Journal
  B. Embed review link in Journal page content
  C. Both relation and embedded link
- **Chosen**: C - Both
- **Rationale**: Relation allows querying "what reviews exist for this journal day". Embedded link in journal content makes it visible when reading the journal entry. Journal is the daily anchor; reviews are linked artifacts.

## Technical Details

### Architecture / Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        macOS launchd                             │
│  (scheduled plist files for each review type)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   review_scheduler.py                            │
│  - Determines review type based on time/day                     │
│  - Checks for existing review page (dedup)                      │
│  - Gathers data from sources (PCO, Notion, Calendar, etc.)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Notion Reviews DB                             │
│  - Creates review page with pre-filled content                  │
│  - Properties: Type, Date, Status, Linked Data                  │
│  - Returns page URL                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌───────────────────┐          ┌───────────────────┐
    │  Telegram Bot      │          │  Apple Reminders   │
    │  (interactive)     │          │  (simple trigger)  │
    │                    │          │                    │
    │  - Sends message   │          │  - Creates reminder│
    │  - Includes link   │          │  - No Notion page  │
    │    to Notion page  │          │  - Just action     │
    └───────────────────┘          └───────────────────┘
```

### Reviews Database Schema

```
Database: Reviews (new)
Properties:
  - Name (title): "Daily Review - 2026-02-06" or "Weekly Review - Week 6"
  - Type (select): Daily, Weekly, Monthly
  - Date (date): Review date
  - Status (status): Not Started, In Progress, Completed
  - Journal (relation): Link to Journal entry for that day
  - Follow-ups (relation): Link to People pages contacted
  - OKR Snapshot (relation): Link to Objectives reviewed
  - Notes (rich text): Reflection notes added during review
```

### Journal Integration

After creating a review page, the script will:
1. Find or create today's Journal entry
2. Add a relation from Review → Journal
3. Append a link block to the Journal page content:

```markdown
## Reviews
- [Daily Review - 2026-02-06](notion-link)
```

This keeps the Journal as the daily anchor with reviews as linked artifacts.

### Telegram Message Format

```markdown
📋 **Daily Review Ready**

Your daily review is ready:
[Open in Notion](https://notion.so/page-id)

**Quick Summary:**
- 3 tasks due today
- 1 shepherding follow-up: Gage Robinson
- 2 calendar events

Reply here to discuss or add notes.
```

### Schedule Configuration

```python
# /workspace/config/review_schedule.py

REVIEW_SCHEDULE = {
    "daily_morning": {
        "time": "07:00",
        "days": ["mon", "tue", "wed", "thu", "fri"],  # Weekdays
        "channel": "telegram",
        "template": "daily_morning",
        "description": "Plan your day: tasks, reminders, important dates, shepherding"
    },
    "daily_financial": {
        "time": "16:30",
        "days": ["mon", "tue", "wed", "thu", "fri"],  # Market days
        "channel": "apple_reminder",
        "template": "Check stocks and portfolio",
        "description": "Quick financial check after market close"
    },
    "weekly_data_upload": {
        "time": "19:00",
        "days": ["sun"],
        "channel": "apple_reminder",
        "template": "Upload: Health export, Copilot CSV, Bookshelf data",
        "description": "Trigger data uploads for tracking"
    },
    "weekly_journal_recap": {
        "time": "19:30",
        "days": ["sun"],
        "channel": "telegram",
        "template": "weekly_journal",
        "description": "Review journal entries, identify themes"
    },
    "monthly_reflection": {
        "time": "18:00",
        "days": ["sun"],  # First Sunday only
        "week": 1,  # First week of month
        "channel": "telegram",
        "template": "monthly_reflection",
        "description": "Data trends, theme reflection, next month planning"
    }
}
```

### Review Templates

#### Daily Morning

**Notion Page Content:**
```markdown
# Daily Review - 2026-02-06

## Tasks & Reminders
- [ ] Task 1 from Notion
- [ ] Task 2 from Notion
- [ ] Reminder: Doctor appointment reminder

## Today's Schedule
| Time | Event |
|------|-------|
| 9:00 AM | Team standup |
| 2:00 PM | Customer call |

## Important Dates This Week
- Feb 8: Mom's birthday
- Feb 10: Project deadline

## Shepherding Follow-up
**Gage Robinson** (Robinson Household)
- 📞 (254) 541-1950
- 📧 theanomalyg@gmail.com

**Theme:** Spiritual Growth at Home
**Questions:**
- How has your family been doing spiritually?
- Any prayer requests?

---

## Reflection
{Space for Heath to add notes during/after review}
```

**Telegram Message:**
```
📋 Daily Review Ready

[Open in Notion](https://notion.so/xxx)

Quick look:
• 3 tasks due today
• 2 calendar events
• Follow-up: Gage Robinson 📞

Reply to add notes or discuss.
```

#### Weekly Review

**Notion Page Content:**
```markdown
# Weekly Review - Week 6 (Feb 2-8)

## Get Clear: Process Inboxes
- [ ] Email inbox to zero
- [ ] Notion inbox processed
- [ ] Apple Reminders reviewed

## Get Current: Review Lists
- [ ] Calendar next 2 weeks reviewed
- [ ] Waiting-for items checked
- [ ] Projects list current

## Journal Recap
| Date | Key Theme |
|------|-----------|
| Mon | ... |
| Tue | ... |

**Habits This Week:**
- Bible: 5/7 ✓
- Prayer: 6/7 ✓
- Reading: 3/7

## Storyworthy Moments
- {Pulled from Storyworthy DB}

## Get Creative: What's Next?
{Space for planning}

---

## Data Uploads Needed
- [ ] Apple Health export
- [ ] Copilot CSV
- [ ] Bookshelf sync
```

**Telegram Message:**
```
📅 Weekly Review Ready

[Open in Notion](https://notion.so/xxx)

This week:
• Habits: 14/21 completed
• 2 storyworthy moments captured
• 3 data uploads needed

Ready for your weekly reset?
```

#### Monthly Reflection

**Notion Page Content:**
```markdown
# Monthly Review - February 2026

## Shepherding Theme: Spiritual Growth at Home

### Follow-up Progress
| Household | Status | Notes |
|-----------|--------|-------|
| Dutton | ✅ Completed | ... |
| Robinson | 🔄 Pending | ... |

**Completion Rate:** 8/20 (40%)

## OKR Progress

### 🎙️ Launch Community Podcast
| Key Result | Current | Target | Progress |
|------------|---------|--------|----------|
| Episodes recorded | 2 | 12 | 17% |

### 📖 Transform Reading Habits
| Key Result | Current | Target | Progress |
|------------|---------|--------|----------|
| Books read | 3 | 12 | 25% |

## Health Trends
- Avg steps: 7,234/day
- Workouts: 12 this month
- Weight: ↓ 2 lbs

## Reflection
1. **What worked well?**
   {Space for response}

2. **What could improve?**
   {Space for response}

3. **Next month's focus:**
   {Space for response}
```

**Telegram Message:**
```
📊 Monthly Review Ready

[Open in Notion](https://notion.so/xxx)

February summary:
• Shepherding: 8/20 households (40%)
• OKRs: 2/4 on track
• Health: 7,234 avg steps, ↓2 lbs

Time for monthly reflection!
```

### Launchd Plist Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.heath.review.daily.morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>/workspace/.claude-venv/bin/python</string>
        <string>/workspace/scripts/review_scheduler.py</string>
        <string>daily_morning</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/workspace/logs/review_daily_morning.log</string>
    <key>StandardErrorPath</key>
    <string>/workspace/logs/review_daily_morning.err</string>
</dict>
</plist>
```

### Deduplication Logic

```python
def should_create_reminder(review_type: str, target_date: date) -> bool:
    """Check if reminder already exists for this review/date."""
    reference_id = f"cron_{review_type}_{target_date.isoformat()}"

    # Check Apple Reminders for existing
    existing = mcp_reminders_tasks(
        action="read",
        filterList="Reminders"
    )

    for reminder in existing:
        if reference_id in reminder.get("note", ""):
            return False  # Already exists

    return True
```

## Open Questions

- [ ] Can Telegram bot initiate conversations, or only respond? (Need to verify bot capabilities)
- [ ] Should weekend schedule differ from weekday?
- [ ] How to handle travel/vacation mode (pause reminders)?
- [ ] Should monthly review include spouse for family OKRs?

## References

- [GTD Weekly Review Best Practices](https://gettingthingsdone.com/2025/06/weekly-review-best-practices/)
- [Scientific Daily Schedule - Todoist](https://www.todoist.com/inspiration/daily-schedule)
- [Time of Day Productivity Research](https://www.memtime.com/blog/most-productive-hours-of-the-day)
- [Asian Efficiency GTD Weekly Review](https://www.asianefficiency.com/productivity/gtd-weekly-review/)
- Apple launchd documentation
- Existing PCO integration: `/workspace/scripts/followup_manager.py`
