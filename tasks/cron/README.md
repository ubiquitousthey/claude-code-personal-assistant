# Cron - Scheduled Review System

## Background

Heath needs a systematic reminder system for daily, weekly, and monthly reviews. Currently, reminders are ad-hoc and reviews are inconsistent. Research shows that [the Weekly Review is "the critical success factor" in making GTD stick](https://gettingthingsdone.com/2025/06/weekly-review-best-practices/) - those who abandon productivity systems typically fail at reviewing, not capturing.

The system must choose between Telegram (interactive, conversation-based) and Apple Reminders (simple notification) for each type of review, avoiding simultaneous competing reminders.

## Goals

- Establish consistent daily, weekly, and monthly review cadence
- Choose optimal reminder channel (Telegram vs Apple Reminders) for each review type
- Time reminders based on productivity research (peak hours, energy cycles)
- Integrate with existing Planning Center follow-ups and OKR tracking
- Make reviews stick by keeping them achievable (<30 min daily, <1.5 hr weekly)

## Scope

### In Scope
- Telegram bot-initiated conversations for interactive reviews
- Apple Reminders for simple action triggers
- Cron job scheduling on Heath's system
- Review templates/checklists for each cadence
- Integration with existing systems (PCO, Notion, Health, Copilot)

### Out of Scope
- Building new tracking databases
- Automated data analysis (manual review is intentional)
- Push notifications to phone (using Telegram/Reminders instead)
- Multiple competing reminders for same review

## Dependencies

- [ ] Telegram bot can initiate conversations (existing capability)
- [ ] Apple Reminders MCP tools working (confirmed)
- [ ] Cron jobs can run scripts on Heath's machine
- [ ] PCO follow-up system operational (confirmed)

## Resources

- [GTD Weekly Review Best Practices](https://gettingthingsdone.com/2025/06/weekly-review-best-practices/)
- [Todoist Weekly Review Guide](https://www.todoist.com/productivity-methods/weekly-review)
- [Daily Review Timing Research](https://www.memtime.com/blog/most-productive-hours-of-the-day)
- [Scientific Daily Schedule](https://www.todoist.com/inspiration/daily-schedule)
- Planning Center Integration: `/workspace/tasks/planning-center-start/`
- Existing CLAUDE.md workflow documentation
