# TODO

## Research
- [x] Query all Notion databases to discover structure and IDs - **14 database IDs documented in CLAUDE.md**
- [ ] Explore Big Plan Page (2f9ff6d0-ac74-812c-b7c0-e46d2c9f8f38) for vision/goals - **Needs Notion MCP query**
- [x] Research Apple Health integration options (Shortcuts, MCP servers) - **3 MCP servers found + Claude iOS native**
- [ ] Research Apple Shortcuts as a way to get data journal ideas
- [ ] Research Uses of Notion and Claude Code for personal assistants
- [x] Research Bookshelf App export/API capabilities - **SOLVED: bookshelf_to_notion.py exists**
- [x] Evaluate Copilot Money integration options - **Export available, local storage + weekly review analysis**

## Implementation

### Phase 1: Notion Discovery & Documentation (Week 5) ✅ COMPLETE
- [x] Document Personal OKR and schema - **Objectives: `16eff6d0-ac74-811e-83ec-d3bea3ef75f6`, Key Results: `16eff6d0-ac74-81ef-91da-f5867df63ef4`**
- [x] Document Journal database ID and schema - **`17dff6d0-ac74-802c-b641-f867c9cf72c2`**
- [x] Document Tags database ID and schema - **`184ff6d0-ac74-8036-a682-e118c4777421`**
- [x] Document People database ID and schema - **`184ff6d0-ac74-80cb-a533-c7cb2fd690ab`**
- [x] Document Crazy Ideas database ID and schema - **`1a5ff6d0-ac74-80e4-ac05-d10c604c23b3`**
- [x] Document Storyworthy Moments database ID and schema - **`187ff6d0-ac74-80ed-8130-fbb5fabbf307`**
- [x] Document "What I want my life to look like" page structure - **`18bff6d0-ac74-805b-b483-e9e55646a1aa`**
- [x] Document Inbox database ID and schema - **`23eff6d0-ac74-80a2-a283-e8f6f0d58097`**
- [x] Document Common Place Journal ID and schema - **`24cff6d0-ac74-8080-8393-d0f2905e8714`**
- [x] Document Works/Reading Notes database schemas - **Works: `2dfff6d0-ac74-81b5-8338-c6d5264786fa`, Notes: `2dfff6d0-ac74-8135-ac38-fa7e0dcaa207`**
- [x] Update CLAUDE.md with all new database IDs - **14 databases added, organized by category**

### Phase 2.0: Profile Enhancement (Week 5) ✅ COMPLETE
- [ ] Extract goals from Objectives DB - **Pending: Query via Notion MCP**
- [ ] Read Journals to understand values and document - **Pending: Query via Notion MCP**
- [x] Add Life Goals & OKRs section to profile.md - **Added priorities + OKR database links**
- [x] Add Habits to Build section to profile.md - **Journaling, Exercise, Reading/Learning**
- [x] Add Schedule Patterns section to profile.md - **Early Bird (6am-3pm), Sundays review**
- [x] Document Heath's preferences as learned - **Financial, Reading, Health tracking documented**

### Phase 2.5: Informed Interview ✅ COMPLETE
- [x] Interview Heath about his work - **Engineering leadership at ZEISS**
- [x] Interview Heath about his family and relationships
  - Courtney - Wife of 27 years
  - Gage Augustin - Son - 24
  - Soren Basil - Son - 22
  - Pax Athanasius - Son - 20
  - Merit Ambrose - Daughter - 13
- [x] Interview Heath about his church - **Elder 10 years at Redeemer Presbyterian, Temple TX - sabbatical year starting**
- [x] Interview Heath about his hobbies - **Reading/Learning/Conversation, Tech and tinkering**
- [x] Interview Heath about his current daily and weekly routine - **5AM wake, morning routine (Bible/prayer), 5:30-6AM India calls, 8AM office, meetings until noon, project work/1:1s until 3PM, evenings for family/church**

### Phase B: Telegram Bot ✅ COMPLETE (2026-01-31)
- [x] Create Telegram bot via @BotFather - **@Midnighthour**
- [x] Clone claude-code-telegram bot
- [x] Configure with workspace context
- [x] Whitelist Heath's user ID (5639696644)
- [x] Test: /start command working
- [ ] Implement anchor point reminders (future enhancement)

### Phase 3: Journaling System (Week 6)
- [ ] Create journal-agent.md with quick capture capability
- [ ] Create `/journal` slash command for quick thought capture
- [ ] Implement daily journal summary compilation
- [ ] Build weekly review processor for journal entries
- [ ] Document Journal DB structure in CLAUDE.md

### Phase 4: OKR & Goal Tracking (Week 6)
- [ ] Create okr-tracker-agent.md
- [ ] Implement weekly OKR check-in workflow
- [ ] Implement monthly OKR progress report
- [ ] Modify daily-planning to show relevant OKRs
- [ ] Create Four Life Areas dashboard in Notion (or find existing)

### Phase 5: Health Data Integration (Week 7+)
- [ ] Choose health integration approach (API vs manual)
- [ ] Create Health Tracking database in Notion (if not exists)
- [ ] Create health-tracker-agent.md
- [ ] Add daily health summary to daily schedule
- [ ] Add weekly health trends to weekly review

### Phase 6: Financial Integration (Week 7+)
- [ ] Create `copilot_analyzer.py` script to parse Copilot exports
- [ ] Create `/data/financial/` directory for local storage (gitignored)
- [ ] Enhance bill payment reminders (already partially exists)
- [ ] Add financial analysis to weekly review workflow (local analysis → Notion summary)
- [ ] Create quarterly net worth update workflow

### Phase 7: Reading/Learning Integration (Week 8+)
- [ ] Create Learning Tracker database (or find existing)
- [ ] Implement Bookshelf App integration
- [ ] Add weekly reading highlights review
- [ ] Connect learning goals to Career/Growth OKRs

### Phase 8: Weekly Review System (Week 6)
- [ ] Create weekly-review.md command
- [ ] Implement journal processing section
- [ ] Implement OKR progress review section
- [ ] Implement health week summary section
- [ ] Implement task/sprint retrospective section
- [ ] Implement relationship check section
- [ ] Implement financial snapshot section
- [ ] Implement next week planning section
- [ ] Create weekly_review_template.md

### Phase 9: Habit Tracking System (Week 8+)
- [ ] Create Habits database in Notion (if not exists)
- [ ] Add morning habit review to daily routine
- [ ] Add evening habit completion to daily routine
- [ ] Create habit dashboard with streaks

## Verification
- [ ] Test `/journal "test thought"` captures to Notion
- [ ] Test weekly review generates all sections
- [ ] Verify OKRs display in daily schedule
- [ ] Verify health data flows correctly
- [ ] Test habit streaks calculate correctly
- [ ] Confirm all 4 life areas tracked in weekly review

---

## Acceptance Criteria

### Must Have
- [x] All Notion databases documented in CLAUDE.md with IDs - **14 databases added**
- [ ] `/journal` command works for quick thought capture
- [ ] Weekly review command generates comprehensive summary
- [ ] OKRs visible in daily planning
- [ ] Profile.md contains goals, habits, and preferences
- [ ] Habit tracking with streak counts functional

### Nice to Have
- [ ] Health data auto-synced from wearables
- [ ] Financial data pulled from Copilot
- [ ] Reading highlights synced from Bookshelf
- [ ] AI-generated insights from journal patterns
- [ ] Mood/energy correlation analysis

### Out of Scope
- Real-time push notifications
- Mobile app interface
- Automated financial transactions
- Third-party app development
