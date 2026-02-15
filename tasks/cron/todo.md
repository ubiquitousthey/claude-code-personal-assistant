# TODO

## Research
- [x] Research GTD review best practices and timing
- [x] Identify optimal time windows for each review type
- [x] Determine Telegram bot's ability to initiate conversations (yes, via bot token)
- [x] Research cron job setup on Heath's system (macOS launchd vs crontab) → launchd
- [x] Review existing daily-routine.md command structure

## Implementation

### Phase 1: Notion Reviews Database
- [x] Create Reviews database in Notion (`2ffff6d0-ac74-8145-a727-c70ce89fcb06`)
- [x] Add properties: Type, Date, Completed (checkbox), Journal (relation)
- [x] Set up relation between Reviews → Journal databases
- [x] Create daily review template (in review_manager.py)
- [x] Create weekly review template (in review_manager.py)
- [x] Create monthly review template (in review_manager.py)
- [x] Add database ID to CLAUDE.md

### Phase 2: Channel Assignment
Based on research - use Telegram for interactive reviews, Apple Reminders for simple triggers:

| Review | Channel | Reason |
|--------|---------|--------|
| Daily AM (tasks/reminders) | Telegram | Needs conversation to plan day |
| Daily PM (financial check) | Apple Reminder | Simple: "Check stocks" |
| Weekly (data upload) | Apple Reminder | Simple action trigger |
| Weekly (journal recap) | Telegram | Interactive reflection |
| Monthly (trends/theme) | Telegram | Deep interactive review |

- [x] Finalize channel assignments
- [x] Document reasoning in doc.md

### Phase 3: Timing Schedule
Based on [productivity research](https://www.todoist.com/inspiration/daily-schedule):
- Peak cognitive performance: ~10:26 AM
- Trough (avoid): ~2:55 PM
- Creative recovery: Late afternoon/evening

| Review | Time | Rationale |
|--------|------|-----------|
| Daily AM | 7:00 AM | Before work, plan the day |
| Daily PM (stocks) | 4:30 PM | Market close, recovery period |
| Weekly Upload | Sunday 7:00 PM | Before weekly review |
| Weekly | Sunday 7:30 PM | End of week, prepare for Monday |
| Monthly | 1st Sunday 6:00 PM | Before weekly review |

- [x] Create schedule configuration file (`config/review_schedule.py`)
- [x] Get Heath's approval on timing (5:30 AM / 4:00 PM / Sunday 8:00 PM)

### Phase 4: Cron Implementation
- [x] Create Python script for reviews (`scripts/review_scheduler.py`)
- [x] Create launchd plist files (`config/launchd/*.plist`)
- [x] Create setup script (`scripts/setup_review_cron.sh`)
- [x] Test daily_morning, weekly, monthly reviews
- [x] Create review daemon (`scripts/review_daemon.py`) - runs in container
- [x] Create Apple Reminder queue + MCP integration

### Phase 5: Integration
- [x] Integrate shepherding follow-ups from PCO system
- [ ] Integrate OKR progress checks (placeholder data)
- [ ] Connect to health data upload workflow
- [ ] Connect to Copilot export workflow

## Verification
- [x] Daily reviews create Notion page correctly
- [x] Weekly review creates Notion page correctly
- [x] Monthly review only runs on first Sunday
- [x] Reviews linked to Journal entries
- [x] Telegram messages formatted with Notion links
- [x] No duplicate reviews (dedup logic works)
- [x] Apple Reminders created via MCP (queued + processed)
- [x] Review daemon running in container

---

## Acceptance Criteria

### Must Have
- [x] Reviews database created in Notion with Journal relation
- [x] Review pages linked to corresponding day's Journal entry (both relation + embedded link)
- [x] Daily review creates Notion page with tasks, reminders, dates, shepherding follow-ups
- [x] Telegram message includes direct link to Notion review page
- [x] Daily afternoon reminder for financial/stock check (queued → MCP)
- [x] Weekly Sunday reminder for data uploads (queued → MCP)
- [x] Weekly review creates Notion page with journal recap, habits, GTD checklist
- [x] Monthly review creates Notion page with OKR progress, trends, theme reflection
- [x] No duplicate reviews (check for existing page before creating)
- [x] Reviews timed to avoid productivity troughs

### Nice to Have
- [ ] Adaptive timing based on calendar (skip if meetings scheduled)
- [ ] Completion tracking for review habit
- [ ] Snooze/reschedule capability
- [x] Weekend vs weekday schedule variations (weekdays for daily, Sunday for weekly)

### Out of Scope
- Automated report generation (reviews are interactive)
- Integration with work calendar for meeting prep
- SMS/phone call reminders
- Multiple reminder channels for same review
