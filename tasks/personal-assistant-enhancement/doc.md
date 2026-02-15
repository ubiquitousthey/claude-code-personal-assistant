# Personal Assistant Enhancement - Technical Document

## Summary
This project enhances Heath's personal assistant from a task/sprint management tool into a comprehensive life management system. It integrates multiple Notion databases, creates new agents for journaling and OKR tracking, and establishes a weekly review workflow that synthesizes progress across career, health, relationships, and financial life areas.

## Key Decisions

### Decision 1: Data Storage Location
- **Options considered**: Local files, Notion, Hybrid approach
- **Chosen**: Notion as primary, local files for session artifacts
- **Rationale**: Notion provides mobile access, Claude iOS can query it, and Heath already uses it extensively. Local files used for daily schedules and session outputs.

### Decision 2: Agent Architecture
- **Options considered**: Single monolithic agent, Multiple specialized agents, Command-based approach
- **Chosen**: Multiple specialized agents with slash commands
- **Rationale**: Separation of concerns allows focused capabilities. Agents: journal-agent, okr-tracker-agent, health-tracker-agent, weekly-review-agent. Commands provide quick access points.

### Decision 3: Health Data Integration
- **Options considered**: Direct API integration, Apple Shortcuts export, Manual entry, Third-party sync service
- **Chosen**: Apple Watch via Apple Shortcuts/HealthKit
- **Rationale**: Heath uses Apple Watch as primary wearable. Apple Health data accessible via Shortcuts automation or third-party sync tools. No Oura integration needed.

### Decision 4: Weekly Review Timing
- **Options considered**: Sunday evening, Monday morning, Flexible user choice
- **Chosen**: Sunday
- **Rationale**: Heath prefers Sunday for weekly review. Allows planning the week ahead before Monday starts.

## Technical Details

### Architecture / Data Flow
```
User Input (Claude Code)
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Claude Code CLI                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ /journal │  │ /weekly- │  │ /daily-      │  │
│  │ command  │  │  review  │  │  routine     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │             │               │          │
│       ▼             ▼               ▼          │
│  ┌──────────────────────────────────────────┐  │
│  │              Agent Layer                  │  │
│  │  journal-agent │ okr-tracker │ health-   │  │
│  │                │   agent     │ tracker   │  │
│  └────────────────────┬─────────────────────┘  │
└───────────────────────┼─────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   ┌──────────┐  ┌───────────┐  ┌───────────┐
   │  Notion  │  │  Google   │  │  Health   │
   │   MCP    │  │ Calendar  │  │   APIs    │
   │          │  │   MCP     │  │ (future)  │
   └──────────┘  └───────────┘  └───────────┘
```

### Notion Database IDs (Discovered)

| Database | ID |
|----------|-----|
| Journal | `17dff6d0-ac74-802c-b641-f867c9cf72c2` |
| Tags | `184ff6d0-ac74-8036-a682-e118c4777421` |
| People | `184ff6d0-ac74-80cb-a533-c7cb2fd690ab` |
| Crazy Ideas | `1a5ff6d0-ac74-80e4-ac05-d10c604c23b3` |
| Storyworthy Moments | `187ff6d0-ac74-80ed-8130-fbb5fabbf307` |
| What I want my life to look like | `18bff6d0-ac74-805b-b483-e9e55646a1aa` |
| Pages | `1b7ff6d0-ac74-8018-8f49-e97875e67ed8` |
| Inbox | `23eff6d0-ac74-80a2-a283-e8f6f0d58097` |
| Common Place Journal | `24cff6d0-ac74-8080-8393-d0f2905e8714` |
| The Convivium Society | `2d7ff6d0-ac74-80c7-a8a9-cc402e94ce89` |
| Works (Bookshelf) | `2dfff6d0-ac74-81b5-8338-c6d5264786fa` |
| Reading Notes (Bookshelf) | `2dfff6d0-ac74-8135-ac38-fa7e0dcaa207` |
| Objectives (OKRs) | `16eff6d0-ac74-811e-83ec-d3bea3ef75f6` |
| Key Results (OKRs) | `16eff6d0-ac74-81ef-91da-f5867df63ef4` |
| Habits | TBD - may need to create |

### Database Schemas (to be queried via Notion MCP)

```
Journal Database (17dff6d0-ac74-802c-b641-f867c9cf72c2)
├── Date (date)
├── Content (rich_text)
├── Mood (select?)
├── Tags (relation to Tags DB)
└── Weekly Review (checkbox)

Objectives Database (16eff6d0-ac74-811e-83ec-d3bea3ef75f6)
├── Objective (title)
├── Key Results (relation to Key Results DB)
├── Life Area (select: Career/Health/Relationships/Financial)
├── Quarter (select)
└── Status (status)

Key Results Database (16eff6d0-ac74-81ef-91da-f5867df63ef4)
├── Key Result (title)
├── Objective (relation to Objectives DB)
├── Score (number 0-1.0)
├── Target (number?)
└── Status (status)

Habits Database (TBD - may need to create)
├── Habit Name (title)
├── Frequency (select: daily/weekly/custom)
├── Streak (number)
├── Last Completed (date)
├── Linked OKR (relation)
└── Active (checkbox)
```

### Files to Create

```
.claude/agents/
├── journal-agent.md
├── okr-tracker-agent.md
├── health-tracker-agent.md
└── weekly-review-agent.md

.claude/commands/
├── journal.md
└── weekly-review.md

templates/
├── weekly_review_template.md
└── journal_entry_template.md
```

### Implementation Notes
- Use Notion MCP `API-post-page` for creating journal entries
- Use Notion MCP `API-patch-page` for updating OKR scores
- Weekly review should query multiple databases and synthesize
- Habit streaks calculated from Last Completed date vs today
- Consider caching frequently accessed data to reduce API calls

## Open Questions
- [x] Which health wearables does Heath actively use? **Apple Watch**
- [x] Preferred day for weekly review? **Sunday**
- [x] Existing Personal OKRs database or need to create? **Exists** (need to find ID via Notion MCP)
- [ ] Existing Habits database or need to create?
- [x] Financial tool integration priority? **Copilot has NO API - manual tracking recommended**
- [x] Bookshelf App export format? **CSV export + existing import script (`bookshelf_to_notion.py`)**

## Research Findings Summary

### Apple Health Integration (RECOMMENDED)
- **neiltron/apple-health-mcp** - npx install, natural language queries
- **Claude iOS** - Native Apple Health integration (Jan 2026)
- Add to `.claude/.mcp.json`:
```json
"apple-health-mcp": {
  "command": "npx",
  "args": ["-y", "@neiltron/apple-health-mcp"]
}
```

### Bookshelf Integration (SOLVED)
- Script exists: `/workspace/bookshelf_to_notion.py`
- Uses CSV export from Bookshelf app
- Already created: Works + Reading Notes databases

### Copilot Money (Export-based)
- No public API, but **export feature available**
- Approach: Python script to parse exports (similar to bookshelf_to_notion.py)
- **Store locally** (not in Notion) for privacy
- Claude analyzes during weekly review
- Update Notion with summary/insights as part of weekly review workflow

## References
- [Notion API Documentation](https://developers.notion.com/)
- [Apple Health MCP (neiltron)](https://github.com/neiltron/apple-health-mcp)
- [Apple Health MCP (LobeHub)](https://lobehub.com/mcp/aferdina-health_mcp)
- [Claude iOS Apple Health](https://www.macrumors.com/2026/01/22/claude-ai-adds-apple-health-connectivity/)
- [GTD Weekly Review methodology](https://gettingthingsdone.com/)
