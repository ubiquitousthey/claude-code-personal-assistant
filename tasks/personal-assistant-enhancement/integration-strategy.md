# Personal Assistant Integration Strategy

## What I've Learned About Heath

### Core Identity
- **Full Name**: Brandon Heath Robinson (goes by Heath)
- **Location**: Bell County, Texas (historical district) - committed to staying local
- **Family**: Married 27 years to Courtney; 4 children (Gage 24, Soren 22, Pax 20, Merit 13)
- **Faith**: Elder at Redeemer Presbyterian Church, Temple TX (10 years) - entering sabbatical year

### Work Context
- **Role**: Head of Software Engineering at ZEISS
- **Challenge**: Feels disconnected - manages international teams (India, Germany) but wants local impact
- **Schedule**: 5AM wake → Bible/prayer → 5:30-6AM India calls → 8AM office → meetings until noon → project work/1:1s until 3PM → evenings for family/church

### Life Vision (from Notion)
**What Heath Wants:**
- Work on something local with creativity and experimentation
- Bring the local community together
- Flourishing relationships with family
- Use his strengths

**What Heath Doesn't Want:**
- Lack of clarity on mission/vision
- Conflicting goals
- Health problems
- Relationship problems

### Current OKRs
1. 🏠 Deepen family relationships through intentional connection
2. 🏋️ Transform health through sustainable weight loss/fitness
3. 📖 Transform reading habits, reduce social media
4. 🎙️ Launch community-focused Christian podcast

### Tools Already in Use
- **Notion** - Primary data store (14+ databases documented)
- **Apple Ecosystem** - Watch, iPhone, Mac
- **Copilot Money** - Financial tracking
- **Bookshelf App** - Reading tracking (syncs to Notion)
- **Claude** - Code, iOS, Mac apps
- **Google** - Calendar, Gmail (work + personal)

---

## Integration Recommendations

### 1. Telegram Bot for Mobile Access (HIGH PRIORITY) ✅ CONFIRMED

**Why Telegram**: Official Bot API (stable, well-documented), most mature Claude integrations, you already have it installed.

**Recommended Solution**: [claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot) or [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)

**Features**:
- Voice messages (driving mode) + text (meeting mode)
- Photo/document capture → instant processing
- Session persistence across conversations
- Real-time tool usage visibility
- Proactive reminders at anchor points

**Security Setup**:
1. Self-host the bot (data stays on your infrastructure)
2. Whitelist only your Telegram user ID
3. Use strong API token management
4. Keep sensitive data in Notion/local, not in chat history

**Setup**:
1. Create Telegram bot via @BotFather → get token
2. Deploy bot connected to this Claude Code workspace
3. Configure CLAUDE.md context to travel with you
4. Set up reminder schedule (see Anchor Points above)

**Daily Use Cases**:
| Time | Mode | Example |
|------|------|---------|
| 5:00 AM | Text | Receive morning brief automatically |
| 7:45 AM | Voice | "What should I prep for before my first meeting?" |
| In meeting | Text | "Add task: follow up with [person] on [topic]" |
| 3:00 PM | Voice | "What's left for today? Anything urgent?" |
| Evening | Text | "Journal: [quick thought capture]" |

---

### 2. Apple Shortcuts Integration (HIGH PRIORITY)

**Why**: Native iOS automation with Siri voice triggers, Apple Watch access, location/time-based automation.

#### A. Claude iOS App Integration
[Claude iOS supports Shortcuts](https://support.claude.com/en/articles/10263469-using-claude-app-intents-shortcuts-and-widgets-on-ios):
- **"Ask Claude"** - Siri voice trigger ("Hey Siri, Ask Claude...")
- **Widgets** - Home screen quick access with mic/camera buttons
- **Control Center** - Analyze photos directly

**Quick Wins**:
- "Hey Siri, Ask Claude what's my first meeting today"
- Widget tap → voice journal entry
- Photo of receipt → expense logging

#### B. Notion via Shortcuts
[Native Notion actions](https://notionist.app/notion-apple-shortcuts) are limited but work for:
- Quick task capture to Inbox database
- Journal entry creation

For advanced automation, use [Nautomate app](https://apps.apple.com/ee/app/nautomate/id1608529689) ($):
- Full property support when creating pages
- File uploads to Notion
- Complex database queries

#### C. Health Data Export ✅ METRICS CONFIRMED
[Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id1115567069) ($4.99):

**Focus Metrics** (aligned with Health OKR):
| Metric | Source | Frequency | Action Threshold |
|--------|--------|-----------|------------------|
| **Sleep Duration** | Apple Watch | Daily | < 6 hrs = alert |
| **Sleep Quality** | Apple Watch | Daily | Track trends |
| **Steps/Activity** | Apple Watch | Daily | < 5000 = nudge |
| **Weight** | Manual/Smart Scale | Weekly | Track trend vs goal |

**Recommended Workflow**:
1. Health Auto Export → nightly JSON to `/workspace/data/health/`
2. Morning brief includes last night's sleep
3. Weekly review shows 7-day trends
4. Weight tracked weekly (Sunday weigh-in?)

**NOT Tracking** (reduces noise):
- HRV, heart rate zones, detailed workout metrics
- Can add later if training for specific goal

---

### 3. Local Notion Cache (MEDIUM PRIORITY)

**Why**: Faster queries, offline access, historical analysis, reduced API calls.

**Architecture**:
```
Notion (Source of Truth)
        ↓ (periodic sync)
Local SQLite Cache (/workspace/data/notion_cache.db)
        ↓
Claude Code queries local cache
        ↓
Changes → Notion API (write-through)
```

**Implementation**:
1. Create `notion_sync.py` script
2. Sync key databases nightly (Tasks, Journal, OKRs)
3. Store in SQLite for fast local queries
4. Write changes directly to Notion (cache updates on next sync)

**Benefits**:
- Query historical data without API limits
- Pattern analysis (journal sentiment, task completion trends)
- Works during Notion outages
- Faster daily planning generation

**Databases to Cache**:
- Work Tasks (`2f9ff6d0-ac74-8109-bd55-c2e0a10dc807`)
- Personal Tasks (`2f9ff6d0-ac74-816f-9c57-f8cd7c850208`)
- Journal (`17dff6d0-ac74-802c-b641-f867c9cf72c2`)
- Objectives (`16eff6d0-ac74-811e-83ec-d3bea3ef75f6`)
- Key Results (`16eff6d0-ac74-81ef-91da-f5867df63ef4`)

---

### 4. Apple Watch Integration (MEDIUM PRIORITY)

**Approach**: Watch → iPhone Shortcut → Claude/Notion

**Options**:
1. **Siri on Watch**: "Hey Siri, Ask Claude..." (requires iPhone nearby)
2. **Complications**: Nautomate widget for quick task entry
3. **Health Data**: Automatic via Health Auto Export

**Best Use Cases**:
- Quick task capture during meetings
- Log workout completion
- Check next calendar event
- Start/stop focus timer

---

### 5. Communication Channels Summary

| Channel | Use Case | Setup Effort |
|---------|----------|--------------|
| **Telegram** | Primary mobile interface, voice/photo/text | Medium |
| **Claude iOS** | Quick queries via Siri, widgets | Low (already have) |
| **Apple Shortcuts** | Automation triggers, health data | Medium |
| **Email** | Async triage (already implemented) | Done |
| **Claude Code** | Deep work, planning, code | Done |

---

## Implementation Order (Revised)

### Phase A: Quick Wins (This Week)
1. [ ] Set up Claude iOS widget on home screen
2. [ ] Create "Ask Claude" Siri shortcut for voice queries (driving mode)
3. [ ] Create "Quick Journal" shortcut → Notion Inbox
4. [ ] Test voice input while driving

### Phase B: Telegram Bot (Next Week) - HIGH PRIORITY
1. [ ] Create Telegram bot via @BotFather
2. [ ] Clone [claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot)
3. [ ] Configure with this workspace's CLAUDE.md + profile.md context
4. [ ] Whitelist Heath's Telegram user ID only
5. [ ] Test: voice messages, photo capture, text commands
6. [ ] Implement anchor point reminders (5AM, 7:45AM, 11:45AM, 2:45PM, 8PM)

### Phase C: Health Integration (Week 7)
1. [ ] Install Health Auto Export app ($4.99)
2. [ ] Configure nightly export: sleep, steps, weight → `/workspace/data/health/`
3. [ ] Create `health_analyzer.py` script (daily + weekly summaries)
4. [ ] Add sleep score to morning Telegram brief
5. [ ] Add weekly health trends to Sunday review

### Phase D: Local Notion Cache (Week 8+)
1. [ ] Create `notion_sync.py` with SQLite
2. [ ] Sync key databases nightly: Tasks, Journal, OKRs
3. [ ] Update daily-planning to query local cache first
4. [ ] Add trend analysis: task completion rates, journal patterns

### Phase E: Proactive Assistant Mode (Week 9+)
1. [ ] Implement reminder delivery via Telegram
2. [ ] Add context-aware suggestions ("You have 30 min before next meeting...")
3. [ ] Weekly review auto-generation
4. [ ] Pattern detection alerts (sleep declining, tasks piling up)

---

## Architecture Vision

```
                    ┌─────────────────┐
                    │   Heath's Day   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   Apple Watch          iPhone              Mac/Claude Code
   (Siri/Widgets)    (Telegram Bot)        (Deep Work)
        │               Claude iOS              │
        │                    │                  │
        └────────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Claude Code    │
                    │  (This Workspace)│
                    │  - CLAUDE.md    │
                    │  - profile.md   │
                    │  - Local Cache  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
     Notion              Google              Apple Health
   (Tasks, Journal,    (Calendar,          (Sleep, Steps,
    OKRs, Reading)      Email)              Workouts)
```

---

## Heath's Preferences (Confirmed)

### Messaging Platform: **Telegram** ✅

**Why Telegram over Signal/WhatsApp:**
- **Signal**: No official bot API - only unofficial tools (signal-cli), very limited
- **WhatsApp**: Uses unofficial APIs (Baileys/WhatsApp Web scraping) - Meta can break it anytime
- **Telegram**: Official Bot API, well-documented, most Claude bot implementations exist here

**Security Note**: Telegram is less secure than Signal for person-to-person chat, but for a personal assistant bot where YOU control the server, the data stays on your infrastructure. Use "Secret Chats" for sensitive conversations with humans.

### Health Metrics: Sleep, Activity, Weight

**Tracking Focus** (aligned with Health OKR):
| Metric | Why It Matters | Frequency |
|--------|----------------|-----------|
| **Sleep** | Foundation for everything - affects focus, mood, willpower | Daily |
| **Activity** | Steps/movement - proxy for lifestyle | Daily |
| **Weight** | Direct OKR metric - sustainable weight loss | Weekly |

**What Doesn't Matter** (for now):
- HRV/Recovery scores - useful but adds complexity without clear action
- Heart rate zones - more relevant for athletes
- Detailed workout metrics - unless training for something specific

### Input Mode: Context-Dependent

| Context | Mode | Use Case |
|---------|------|----------|
| **Driving** (7:45-8AM, 3PM+) | Voice | "What's my first meeting?" / "Add task..." |
| **Meetings** | Text | Quick task capture, silent queries |
| **Morning routine** (5-5:30AM) | Either | Depends on family sleep |
| **Evening** | Text | Review tomorrow, journal capture |

### Reminder Strategy: Executive Assistant Style

**Anchor Point Reminders** (proactive, not annoying):

| Time | Trigger | Reminder Type |
|------|---------|---------------|
| **5:00 AM** | Wake | "Good morning. Today: [top 3 priorities]. First meeting: [X] at [time]" |
| **7:45 AM** | Leave for office | "Driving brief: [key meetings], [urgent items]" |
| **11:45 AM** | Pre-lunch | "Before lunch: [any urgent tasks?]. Afternoon: [1:1s, project work]" |
| **2:45 PM** | End of day prep | "Wrapping up: [incomplete high-priority]. Tomorrow: [preview]" |
| **8:00 PM** | Evening wind-down | "Day complete. [Wins]. [Carry-forward items]. Journal prompt?" |
| **Sunday 7PM** | Weekly review | "Weekly review time. [Summary ready]" |

**Reminder Principles**:
- Brief, actionable, not chatty
- Include context (why this matters now)
- Easy to dismiss or act on
- Respect family/church time (no interruptions during dinner, services)

---

## Sources

### Telegram Integration
- [claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot) - Recommended solution
- [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) - Alternative with session persistence
- [How to Use Claude Code From Your Phone](https://medium.com/@amirilovic/how-to-use-claude-code-from-your-phone-with-a-telegram-bot-dde2ac8783d0)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Platform Comparison
- [Bot Development for Messenger Platforms](https://alexasteinbruck.medium.com/bot-development-for-messenger-platforms-whatsapp-telegram-and-signal-2025-guide-50635f49b8c6)
- Signal has no official bot API - [Signal vs Telegram](https://www.safetydetectives.com/blog/signal-vs-telegram/)
- [Clawdbot Security Analysis](https://www.straiker.ai/blog/how-the-clawdbot-moltbot-ai-assistant-becomes-a-backdoor-for-system-takeover) - Security considerations

### Apple Integration
- [Claude iOS Shortcuts Guide](https://support.claude.com/en/articles/10263469-using-claude-app-intents-shortcuts-and-widgets-on-ios)
- [Notion Apple Shortcuts Guide](https://notionist.app/notion-apple-shortcuts)
- [Nautomate App](https://apps.apple.com/ee/app/nautomate/id1608529689)

### Health Data
- [Health Auto Export](https://www.healthyapps.dev/)
- [Health Auto Export REST API Docs](https://github.com/Lybron/health-auto-export)

### Local Caching
- [How Notion Uses SQLite](https://blog.neetcode.io/p/notion-uses-sqlite-caching)
- [Notion Offline Architecture](https://www.notion.com/blog/how-we-made-notion-available-offline)
