# Personal Assistant Enhancement

## Background
Heath's current personal assistant system focuses primarily on task/sprint management and calendar coordination. The goal is to transform it into a comprehensive life management system that helps build habits, track goals across all life areas (career, health, relationships, financial), and process thoughts through structured journaling.

Currently, Heath has multiple Notion databases that are not yet integrated:
- Journal, Tags, People, Crazy Ideas, Storyworthy Moments
- What I want my life to look like, Inbox, Common Place Journal
- Works and Reading Notes (Bookshelf Import)

## Goals
- Integrate undocumented Notion databases into CLAUDE.md
- Create a journaling system with quick thought capture and weekly review
- Implement OKR/goal tracking across 4 life areas
- Build weekly review workflow that synthesizes all life areas
- Integrate health data tracking (Apple Health, Oura, etc.)
- Enhance financial tracking beyond bill reminders
- Add reading/learning integration (Bookshelf App, highlights)
- Create habit tracking system linked to OKRs

## Scope

### In Scope
- Notion database discovery and documentation
- Profile.md enhancement with goals, habits, preferences
- Journal agent and quick capture command
- OKR tracker agent with weekly/monthly/quarterly reviews
- Weekly review command synthesizing all life areas
- Health tracking agent (research + basic implementation)
- Habit tracking database and check-ins
- Integration with existing tools (Copilot for money, Bookshelf for reading)

### Out of Scope
- Mobile app development
- Custom UI beyond Claude Code/Notion
- Real-time notifications or push alerts
- Integration with employer systems beyond calendar
- Automated financial transactions

## Dependencies
- [ ] Access to all Notion databases via MCP
- [ ] Google Calendar MCP for both work and personal calendars
- [ ] Gmail MCP for email processing (already working)
- [ ] Health API access (to be researched - Apple Health, Oura)
- [ ] Bookshelf App export capability

## Resources
- [Notion MCP documentation]
- [Existing CLAUDE.md with database IDs](/workspace/CLAUDE.md)
- [Heath's profile](/workspace/profile.md)
- [Current daily-routine command](/.claude/commands/daily-routine.md)
