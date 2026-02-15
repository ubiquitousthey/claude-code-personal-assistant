#!/bin/bash
# Docker initialization script for Claude Code
# Merges project defaults with persisted user config

CLAUDE_DIR="/home/claude/.claude"
DEFAULTS_DIR="/home/claude/.claude-defaults"

# Ensure .claude directory exists
mkdir -p "$CLAUDE_DIR"

# Function to copy directory contents without overwriting
copy_defaults() {
    local src_dir="$1"
    local dest_dir="$2"
    local label="$3"

    if [ -d "$src_dir" ]; then
        mkdir -p "$dest_dir"
        for file in "$src_dir"/*; do
            if [ -f "$file" ]; then
                basename=$(basename "$file")
                if [ ! -f "$dest_dir/$basename" ]; then
                    cp "$file" "$dest_dir/$basename"
                    echo "Copied default $label: $basename"
                fi
            fi
        done
    fi
}

# Copy default commands, agents, and hooks if not already present
copy_defaults "$DEFAULTS_DIR/commands" "$CLAUDE_DIR/commands" "command"
copy_defaults "$DEFAULTS_DIR/agents" "$CLAUDE_DIR/agents" "agent"
copy_defaults "$DEFAULTS_DIR/hooks" "$CLAUDE_DIR/hooks" "hook"

# Copy default settings.json if none exists
if [ -f "$DEFAULTS_DIR/settings.json" ] && [ ! -f "$CLAUDE_DIR/settings.json" ]; then
    cp "$DEFAULTS_DIR/settings.json" "$CLAUDE_DIR/settings.json"
    echo "Copied default settings.json"
fi

# Copy default settings.local.json if none exists
if [ -f "$DEFAULTS_DIR/settings.local.json" ] && [ ! -f "$CLAUDE_DIR/settings.local.json" ]; then
    cp "$DEFAULTS_DIR/settings.local.json" "$CLAUDE_DIR/settings.local.json"
    echo "Copied default settings.local.json"
fi

# Copy MCP configuration files if not present
for mcp_file in ".mcp.json" "mcp-servers.json"; do
    if [ -f "$DEFAULTS_DIR/$mcp_file" ] && [ ! -f "$CLAUDE_DIR/$mcp_file" ]; then
        cp "$DEFAULTS_DIR/$mcp_file" "$CLAUDE_DIR/$mcp_file"
        echo "Copied MCP config: $mcp_file"
    fi
done

echo "Claude Code initialization complete"

# Execute the passed command (or default to bash)
exec "$@"
