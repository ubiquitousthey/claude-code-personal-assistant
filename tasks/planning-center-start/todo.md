# TODO

## Research
- [ ] Explore PCO People API - list people endpoint, phone/email includes
- [ ] Explore PCO People API - household relationships and family members
- [ ] Explore PCO Services API - schedules and tasks endpoints
- [ ] Test shepherding list endpoint with list ID `3015465`
- [ ] Test schedules endpoint with person ID `33065814`
- [ ] Explore Notion People DB schema (`184ff6d0-ac74-80cb-a533-c7cb2fd690ab`)
- [ ] Determine best approach: MCP server vs Python scripts vs both

## Implementation

### Phase 1: Core Python Client
- [x] Create `scripts/pco_client.py` - base client with auth
- [x] Implement `get_shepherding_list()` - fetch list members with contact info
- [x] Implement `get_household(person_id)` - get family members/relationships
- [x] Implement `search_people(query)` - search by name (supports family search)
- [x] Implement `get_person_details(id)` - phone, email, address
- [x] Implement `get_my_schedules()` - upcoming service assignments
- [ ] Implement `get_my_tasks()` - incomplete tasks assigned to Heath (deferred - depends on PCO config)

### Phase 2: Notion CRM Integration
- [x] Create `scripts/pco_notion_sync.py` - sync contacts to Notion
- [x] Map PCO person → Notion People page (create if not exists)
- [x] Store PCO ID in Notion for linking
- [x] Implement `log_contact_note(person, note)` - append timestamped note to Notion page
- [x] Implement `get_contact_history(person)` - retrieve notes from Notion
- [x] Generate follow-up questions based on last note content

### Phase 3: Monthly Follow-up System
- [x] Design follow-up tracking schema (Notion DB or local JSON?) → Local JSON
- [x] Implement household grouping from shepherding list
- [x] Create monthly distribution algorithm (1 adult per household)
- [x] Implement `get_todays_followups()` - who to contact today
- [x] Implement follow-up reminder creation with smart questions
- [x] Add 7-day re-surface logic for incomplete follow-ups
- [x] Create monthly theme configuration (CLAUDE.md or separate config?) → CLAUDE.md
- [x] Include theme-based questions in follow-up reminders

### Phase 4: Reminder Integration
- [x] Create `scripts/pco_sync_reminders.py` - sync script
- [x] Map service schedules to Apple Reminders (day-before alerts)
- [x] Map PCO tasks to Apple Reminders with due dates
- [x] Create follow-up reminders with:
  - Person name and contact info
  - Smart questions from last interaction
  - Theme-based questions for the month
- [x] Add deduplication logic (don't create duplicate reminders)

### Phase 5: MCP Server (Agent Tools)
- [x] Create `mcp-servers/planning-center/` structure
- [x] Implement `pco_search_people` tool (supports "Robertson's kids" queries)
- [x] Implement `pco_get_household` tool
- [x] Implement `pco_get_shepherding_list` tool
- [x] Implement `pco_log_contact` tool (logs note to Notion)
- [x] Implement `pco_get_contact_history` tool
- [x] Implement `pco_get_my_schedule` tool
- [ ] Register MCP server in Claude Code config (optional - scripts work directly)

### Phase 6: Daily Routine Integration
- [x] Add shepherding follow-ups to daily planning workflow
- [x] Add service schedule check to daily planning
- [x] Surface today's follow-up contacts with suggested questions
- [x] Track and report follow-up completion rate

## Verification
- [x] Shepherding list fetches correctly with contact details
- [x] Household/family queries work (e.g., "Robertson's kids")
- [x] People search returns accurate results
- [x] Contacts sync to Notion People DB correctly
- [x] Contact notes append with timestamps
- [x] Follow-up questions generated from notes
- [x] Monthly distribution spreads contacts across days
- [x] Incomplete follow-ups re-surface after 7 days
- [x] Service schedules show upcoming assignments
- [x] Apple Reminders created correctly from PCO data
- [x] MCP tools accessible from agent (Telegram + Claude Code)

---

## Acceptance Criteria

### Must Have
- [x] Can fetch shepherding list members with names and contact info
- [x] Can search PCO people by name, including family queries
- [x] Can get household members (e.g., "Who are the Robertson's kids?")
- [x] Shepherding contacts sync to Notion People DB
- [x] Can log contact notes via agent command
- [x] Follow-up reminders include smart questions based on last interaction
- [x] Monthly theme questions included in follow-up reminders
- [x] One adult per household contacted each month
- [x] Follow-ups distributed across days in daily planning
- [x] Incomplete follow-ups re-surface after 7 days
- [x] Service assignments create Apple Reminders automatically
- [x] PCO tasks sync to Apple Reminders (N/A - depends on PCO config)

### Nice to Have
- [x] Follow-up completion tracking/reporting
- [ ] Calendar conflict detection for service schedules
- [ ] Suggested contact method based on person preferences

### Out of Scope
- Two-way task completion sync (PCO ← Reminders)
- Check-ins or Giving API integration
- Automated SMS/email sending
- Bulk contact import from other sources
