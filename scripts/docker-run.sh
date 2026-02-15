#!/bin/bash
# Run Claude Code in Docker container
# Usage: ./scripts/docker-run.sh [claude args...]
#
# Examples:
#   ./scripts/docker-run.sh              # Interactive bash shell
#   ./scripts/docker-run.sh claude       # Start Claude Code CLI
#   ./scripts/docker-run.sh claude -p "help me with tasks"

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for Claude credentials
CLAUDE_CREDS="$HOME/.claude/.credentials.json"
if [ ! -f "$CLAUDE_CREDS" ]; then
    echo "Error: Claude credentials not found at $CLAUDE_CREDS"
    echo "Run 'claude' on your host machine first to authenticate."
    exit 1
fi

# Build and run
docker compose run --rm claude "$@"
