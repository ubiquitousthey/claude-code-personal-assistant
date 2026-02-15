---
description: Quick thought capture to Heath's Notion journal
allowed-tools: Task, Bash(date:*), Read, mcp__notion-mcp__*
---

# Quick Log

Capture a thought or update to Heath's Notion journal. This command handles:
- Adding timestamped thoughts to today's journal entry
- Creating a new daily entry if one doesn't exist
- Updating habit checkboxes
- Viewing today's journal content

## Current Context

- Today's date: !`date +"%Y-%m-%d"`
- Current time: !`date +"%H:%M"`

## Usage Patterns

### Quick Thought Capture
```
/log Just had a great conversation with [person] about [topic]
/log Feeling grateful for [thing]
/log Idea: [description]
```

### Habit Updates
```
/log read bible
/log prayed
/log read book
/log flipped switch
```

### View Today's Journal
```
/log show
/log view
```

### Full Journaling Session
```
/log start
```

## Process

### 1. Parse Input
- Determine if this is a thought capture, habit update, or view request
- Extract the content to journal

### 2. Find or Create Today's Entry
Query the Journal database for today's date:
```javascript
mcp__notion-mcp__API-query-data-source({
  data_source_id: "95459472-1827-410a-973e-2f3a8ecdb3df",
  filter: {
    property: "Name",
    title: { equals: "YYYY-MM-DD" }
  }
})
```

### 3. Execute Action

**For Thought Capture**:
- If entry exists: Append paragraph block with timestamp
- If no entry: Create new page with initial content
- Always mark "Journaled?" checkbox as true

**For Habit Updates**:
- Find today's entry
- Update the corresponding checkbox property
- Confirm the update

**For View Requests**:
- Retrieve the page
- Get all block children
- Display content summary

## Database Reference

- **Journal Database**: `17dff6d0-ac74-802c-b641-f867c9cf72c2`
- **Data Source ID**: `95459472-1827-410a-973e-2f3a8ecdb3df`

## Habit Property Mapping

| Command | Property | Value |
|---------|----------|-------|
| read bible, bible | Read Bible? | true |
| prayed, prayer | Prayed? | true |
| read book, reading | Read a book? | true |
| flipped switch, switch | Flipped the Switch? | true |

## Output

After capturing:
1. Confirm the thought was added with timestamp
2. Show Notion link to the entry
3. Display current habit completion status
4. Suggest "Mark any habits complete?" if habits are unchecked

## Examples

**Input**: `/log Grateful for the team's progress on the demo today`
**Output**:
```
Added to journal at 14:32
Entry: https://www.notion.so/...

Today's habits:
- [ ] Read Bible
- [x] Prayed
- [x] Journaled
- [ ] Read a book
- [ ] Flipped the Switch
```

**Input**: `/log read bible`
**Output**:
```
Updated habit: Read Bible? = true

Today's habits:
- [x] Read Bible
- [x] Prayed
- [x] Journaled
- [ ] Read a book
- [ ] Flipped the Switch
```
