# Research Findings

## 1. Notion Database IDs (Extracted from Enhancement Plan URLs)

| Database | ID | Status |
|----------|-----|--------|
| Journal | `17dff6d0-ac74-802c-b641-f867c9cf72c2` | Discovered |
| Tags | `184ff6d0-ac74-8036-a682-e118c4777421` | Discovered |
| People | `184ff6d0-ac74-80cb-a533-c7cb2fd690ab` | Discovered |
| Crazy Ideas | `1a5ff6d0-ac74-80e4-ac05-d10c604c23b3` | Discovered |
| Storyworthy Moments | `187ff6d0-ac74-80ed-8130-fbb5fabbf307` | Discovered |
| What I want my life to look like | `18bff6d0-ac74-805b-b483-e9e55646a1aa` | Discovered (Page) |
| Pages | `1b7ff6d0-ac74-8018-8f49-e97875e67ed8` | Discovered |
| Inbox | `23eff6d0-ac74-80a2-a283-e8f6f0d58097` | Discovered |
| Common Place Journal | `24cff6d0-ac74-8080-8393-d0f2905e8714` | Discovered |
| The Convivium Society | `2d7ff6d0-ac74-80c7-a8a9-cc402e94ce89` | Discovered |
| Works (Bookshelf Import) | `2dfff6d0-ac74-81b5-8338-c6d5264786fa` | Discovered |
| Reading Notes (Bookshelf Import) | `2dfff6d0-ac74-8135-ac38-fa7e0dcaa207` | Discovered |
| Objectives (OKRs) | `16eff6d0-ac74-811e-83ec-d3bea3ef75f6` | Discovered |
| Key Results (OKRs) | `16eff6d0-ac74-81ef-91da-f5867df63ef4` | Discovered |

**Note**: Database schemas need to be queried via Notion MCP to document properties.

---

## 2. Apple Health Integration Options

### Recommended: Apple Health MCP Servers

Several MCP servers are available for Apple Health integration:

1. **[Apple Health MCP Server (LobeHub)](https://lobehub.com/mcp/aferdina-health_mcp)**
   - PostgreSQL backend with automatic import
   - File system watching for automatic updates
   - Comprehensive health data: heart rate, sleep, steps, workouts
   - iOS Shortcuts integration for easy data export
   - Privacy-first: all data stays local

2. **[The Momentum's Apple Health MCP](https://github.com/the-momentum/apple-health-mcp-server)**
   - Natural language querying with DuckDB
   - Personalized insights
   - Docker support for easy deployment

3. **[Neiltron's Apple Health MCP](https://github.com/neiltron/apple-health-mcp)**
   - Natural language + SQL querying
   - Automated reports
   - No installation required (npx via Claude Desktop)

### Alternative: Native Claude iOS Integration
- **[Claude iOS now supports Apple Health](https://www.macrumors.com/2026/01/22/claude-ai-adds-apple-health-connectivity/)** (Jan 2026)
- Direct access to health data from Claude iOS app
- Rolling out in US

### Recommendation
Use **neiltron/apple-health-mcp** for Claude Code (easiest setup with npx) combined with **Claude iOS** for mobile health queries.

---

## 3. Bookshelf App Integration

### Current Status: SOLVED
A working import script already exists: `/workspace/bookshelf_to_notion.py`

### How It Works
1. **Export from Bookshelf App**: CSV export (Books + Cards/Notes)
2. **Run import script**: Creates two Notion databases:
   - Works (Bookshelf Import) - Book information
   - Reading Notes (Bookshelf Import) - Highlights and notes linked to books

### CSV Export Files Expected
- `Bookshelf-Books-YYYY-MM-DD-HH-MM-SS.csv`
- `Bookshelf-Cards-YYYY-MM-DD-HH-MM-SS.csv`

### Database Schema (from script)
**Works Database:**
- Title, Author, ISBN-10, ISBN-13, ASIN, Publisher
- Year Published, Page Count, Category, Format
- Ownership Status, Reading Status, Date Added
- Is Favorite, Book Source, Start Date, End Date, Rating

**Notes Database:**
- Title, Work (relation), Type (Quote/Note/Flash Card/Definition)
- Date Added, Study Level, Card ID

### Usage
```bash
export NOTION_API_KEY='your_key'
export NOTION_PAGE_ID='parent_page_id'
python bookshelf_to_notion.py
```

---

## 4. Copilot Money Integration

### Finding: NO PUBLIC API

Copilot Money does **not** offer a public API for third-party integration.

### How Copilot Works Internally
- Uses **Plaid** for bank account aggregation (10,000+ institutions)
- AI auto-categorizes transactions
- Natural language search within app
- Data stays within Apple ecosystem (iOS/Mac only)

### Limitations
- No external API access
- Cannot export data programmatically
- Cannot create automation workflows
- Must contact support to modify categorization rules

### Alternatives for Financial Integration
1. **Tiller Money** - Exports to Google Sheets/Excel, scriptable
2. **Monarch Money** - Has some automation features
3. **Manual CSV export** - Most apps support this
4. **Plaid direct integration** - Would require building custom solution

### Recommendation (Updated)
For financial tracking in the assistant:
- Use **Copilot export feature** to get transaction/financial data
- Write **Python script** (similar to bookshelf_to_notion.py) to parse exports
- **Store data locally** (not in Notion) for privacy/security
- Claude **analyzes locally** during weekly review
- Update Notion with **summary/insights only** as part of weekly review
- Keep bill payment reminders (already working)

### Implementation Plan
1. Create `copilot_analyzer.py` script to parse Copilot exports
2. Store exports in `/data/financial/` (gitignored)
3. Add financial analysis to weekly review workflow
4. Summary metrics go to Notion, raw data stays local

---

## 5. MCP Configuration (Current)

From `/workspace/.claude/.mcp.json`:
- **notion-mcp**: Configured via `@notionhq/notion-mcp-server`
- **mcp-gsuite**: Configured for Gmail/Calendar integration

### To Add for Health Integration
```json
"apple-health-mcp": {
  "command": "npx",
  "args": ["-y", "@neiltron/apple-health-mcp"]
}
```

---

## Summary & Recommendations

| Integration | Status | Recommendation |
|-------------|--------|----------------|
| Notion | Ready | Use existing MCP, query for OKRs database ID |
| Apple Health | Ready to implement | Add neiltron/apple-health-mcp to config |
| Bookshelf | Already solved | Use existing bookshelf_to_notion.py |
| Copilot Money | No API | Manual tracking, CSV exports |

### Next Steps
1. Query Notion MCP for Personal OKRs database ID
2. Document database schemas via API queries
3. Add Apple Health MCP to configuration
4. Update CLAUDE.md with all database IDs
