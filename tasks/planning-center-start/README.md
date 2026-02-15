# Planning Center Integration

## Background

Heath has church responsibilities that require regular coordination through Planning Center (PCO):
- A shepherding list of people he needs to follow up with regularly
- Service schedules where he may be assigned roles
- Tasks assigned to him through the PCO system

Currently, this information lives only in Planning Center and requires manual checking. Integrating PCO with the personal assistant system will surface this information during daily planning, create automatic reminders, and enable CRM-like contact management synced to Notion.

## Goals

- Enable natural language people search via Telegram/Claude Code (e.g., "What are the Robertson's kids' names?")
- Sync shepherding contacts to Notion People database as a personal CRM
- Record and retrieve contact notes with smart follow-up question suggestions
- Distribute monthly follow-ups across daily planning (one adult per household per month)
- Support monthly follow-up themes with relevant conversation starters
- Create reminders for upcoming service assignments
- Sync PCO tasks to Apple Reminders

## Key Use Cases

### 1. People Search (Telegram/Agent)
**Example:** "What are the names of the Robertson's kids?"
- Search PCO by family name
- Return household members with relationships
- Include contact info (phone, email)

### 2. Contact Notes as CRM
**Example:** "Log note for John Smith: discussed job transition, praying for interview Friday"
- Sync PCO contacts → Notion People DB
- Append timestamped notes to Notion page
- Generate smart follow-up questions based on last interaction
- Follow-up reminder: "Ask John how the interview went"

### 3. Monthly Follow-up Themes
**Example:** Theme for February: "How is your family doing spiritually?"
- Configure monthly theme
- Include theme-based questions in follow-up reminders
- Suggested questions adapt to theme + person context

### 4. Distributed Monthly Follow-ups
**Workflow:**
- Each month, contact one adult from each household on shepherding list
- Distribute follow-ups across days in daily planning
- If no contact logged within 7 days, re-surface the reminder
- Track completion to avoid duplicate outreach

## Scope

### In Scope
- Read-only access to PCO People API (shepherding list, people search, households)
- Read-only access to PCO Services API (schedules, tasks)
- Sync shepherding contacts to Notion People database
- Contact note recording with timestamps
- Smart follow-up question generation (based on notes + theme)
- Monthly follow-up distribution algorithm
- Creating Apple Reminders from PCO data
- MCP server for agent tool access (Telegram + Claude Code)
- Integration with daily planning workflow

### Out of Scope
- Two-way sync (marking PCO tasks complete from reminders)
- Calendar conflict detection
- PCO Check-ins API integration
- PCO Giving API integration
- Automated SMS/email sending

## Dependencies

- [x] Planning Center API credentials (stored in .env)
- [x] Shepherding list ID: `3015465`
- [x] Heath's PCO person ID: `33065814`
- [x] Apple Reminders MCP (already available)
- [x] Notion People Database: `184ff6d0-ac74-80cb-a533-c7cb2fd690ab`
- [ ] Python PCO client library or requests-based implementation
- [ ] Monthly theme configuration (where to store?)

## Resources

- [Planning Center API Docs](https://developer.planning.center/docs/)
- [People API](https://developer.planning.center/docs/#/apps/people)
- [Services API](https://developer.planning.center/docs/#/apps/services)
- Original spec: `/workspace/specs/planning_center_integration.md`
- Notion People DB: `184ff6d0-ac74-80cb-a533-c7cb2fd690ab`
