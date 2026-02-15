# Personal Assistant Claude Setup Template

This repository contains a template for setting up a personal assistant using Claude with integrations for Notion and Google Workspace. It's designed to be a starting point for creating your own automated personal assistant.

## Prerequisites

Before you begin, ensure you have the following:

-   **Claude Code CLI**: Install via `npm install -g @anthropic-ai/claude-code`
-   **Docker** (recommended): For running Claude Code in an isolated container
-   **[mcp-gsuite-enhanced](https://github.com/ajramos/mcp-gsuite-enhanced)**: For Google Calendar and Gmail integration
-   **[Notion MCP Server](https://github.com/makenotion/notion-mcp-server)**: For Notion integration
-   **Python 3.10+**: For running the analysis scripts (included in Docker setup)
-   **A Notion account and a Google account**

## Setup Instructions

> **Pro-tip**: You can use Claude Code to automate much of this setup. Just ask it to configure the project for you by replacing the placeholders with your information.

### 1. Configure `CLAUDE.md`

This is the core file that defines your assistant's identity, responsibilities, and workflows.

1.  Open `claude-setup/CLAUDE.md`.
2.  Replace all placeholder values (e.g., `[YOUR_NAME]`, `[WORK_EMAIL]`, `[YOUR_WORK_TASK_DATABASE_ID]`) with your actual information.
    -   **Calendars**: Add your work and personal calendar IDs.
    -   **Notion Databases**: Create the necessary databases in Notion (Sprints, Meetings, Work Tasks, Personal Tasks) and get their IDs.
    -   **Notion User ID**: Find your Notion user ID.

### 2. Set Up Notion

1.  Create the databases in Notion that you referenced in `CLAUDE.md`.
2.  Ensure the properties in your Notion databases match the ones used in the scripts and `CLAUDE.md` (e.g., "Tags", "Sprint", "Due Date").

### 3. Configure Scripts

The `scripts/` directory contains Python scripts for task analysis.

1.  Open `claude-setup/scripts/personal_task_analyzer.py` and `claude-setup/scripts/work_task_analyzer.py`.
2.  Replace the placeholder database and user IDs at the top of each file with your Notion IDs.

This template includes customized task analyzer scripts (`personal_task_analyzer.py` and `work_task_analyzer.py`) designed to fetch tasks in bulk from your Notion databases. This approach provides context to the agent more efficiently than querying tasks one by one.

Depending on your specific Notion database structure and properties, you may need to modify these scripts. Alternatively, you can always ask Claude to interact with your Notion databases directly to get task information.

### 4. Set Up Environment Variables

The scripts require a Notion API token.

1.  Create a `.env` file in the root of your project directory.
2.  Add your Notion integration token to the `.env` file:
    ```
    NOTION_TOKEN="your_notion_api_token"
    ```

### 5. Install Dependencies

The Python scripts have dependencies that need to be installed.

1.  It is recommended to use a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You may need to create a `requirements.txt` file if one doesn't exist. Based on the scripts, you will need `python-dotenv` and `notion-client`.)*

### 6. Using the Assistant

With the setup complete, you can now use your personal assistant.

-   **Daily Routine**: Use the `daily-routine.md` command to trigger your assistant's morning workflow.
-   **Task Analysis**: Run the Python scripts to get reports on your work and personal tasks.

## Running in Docker (Recommended)

Running Claude Code in a Docker container provides isolation and security, allowing you to give it more freedom without risk to your system.

### Quick Start

1.  **Authenticate Claude on your host machine first** (if you haven't already):
    ```bash
    claude
    # Follow the OAuth login prompts
    ```

2.  **Build and run the container:**
    ```bash
    # Option A: Using the helper script
    ./scripts/docker-run.sh

    # Option B: Using docker compose directly
    docker compose run --rm claude
    ```

3.  **Inside the container, start Claude:**
    ```bash
    claude
    ```

The container automatically uses your existing Claude credentials from `~/.claude/.credentials.json`.

### What's Mounted

| Host | Container | Purpose |
|------|-----------|---------|
| `.` (project dir) | `/workspace` | Your files (read-write) |
| `~/.claude/.credentials.json` | `/home/claude/.claude/.credentials.json` | OAuth credentials (read-only) |
| Docker volume `claude-config` | `/home/claude/.claude` | All Claude config persists |

### Key Benefits

-   **Files stay on your machine** - The `/workspace` mount means all edits happen to your actual files
-   **Isolation** - Claude runs as non-root user inside the container
-   **Persisted state** - Claude's settings, MCP servers, and customizations survive container rebuilds
-   **Security** - API keys passed via environment variables, not baked into the image

### One-liner to start Claude directly

```bash
docker compose run --rm claude claude
```

### Config Persistence

The Docker setup uses a smart initialization system to persist your Claude configuration across container rebuilds while keeping project defaults in sync.

#### How It Works

1. **Project defaults** (in `.claude/`) are baked into the image at `/home/claude/.claude-defaults/`
2. **User config** lives in a named Docker volume at `/home/claude/.claude/`
3. **On container start**, the init script (`scripts/docker-init.sh`) copies missing defaults to the volume

#### What Gets Persisted

The `claude-config` volume preserves:
- `settings.json` and `settings.local.json`
- MCP server configurations (`.mcp.json`, `mcp-servers.json`)
- Custom commands you add at runtime
- Custom agents and hooks
- Any other Claude configuration

#### Behavior on Rebuild

| Scenario | What Happens |
|----------|--------------|
| Rebuild image | Volume untouched, all your config preserved |
| Add new command to project `.claude/commands/` | Copied to volume on next start (won't overwrite your version) |
| Modify existing project command | Your customized version in volume takes precedence |
| First run (empty volume) | All project defaults copied to volume |

#### Reset Configuration

To start fresh with only project defaults:

```bash
# Remove the config volume
docker volume rm claude-code-personal-assistant_claude-config

# Rebuild and run
docker compose up --build
```

#### Adding MCP Servers in Container

MCP servers installed inside the container persist in the volume:

```bash
# Inside container
claude mcp add my-server -- npx @example/my-mcp-server

# This survives container rebuilds
```

To make an MCP server part of your project defaults (so it's available to anyone who clones the repo), add it to `.claude/.mcp.json` instead.

## Customization

This is a template, so feel free to customize it to your needs.

-   **Modify `CLAUDE.md`**: Adjust the assistant's personality, responsibilities, and workflows.
-   **Update Templates**: Change the templates in the `templates/` directory to match your preferred formats for daily schedules, sprint planning, and standup notes.
-   **Extend Scripts**: Add more functionality to the Python scripts for more in-depth analysis.

## Security Notes

-   The `.env` file contains sensitive API keys and is excluded from git via `.gitignore`
-   Never commit `.env` to version control
-   Use `.env.example` as a template for required environment variables
-   If running in Docker, API keys are passed as environment variables and not stored in the image

---

*This template is provided as-is. You are responsible for managing your own data and API keys securely.*
