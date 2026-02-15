#!/bin/bash
# Setup Review Scheduler Cron Jobs
#
# This script installs the launchd plist files for scheduled reviews.
# Run with: ./setup_review_cron.sh install
# Uninstall with: ./setup_review_cron.sh uninstall

set -e

WORKSPACE="/workspace"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
PLIST_SOURCE="$WORKSPACE/config/launchd"
LOG_DIR="$WORKSPACE/logs"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

install_jobs() {
    echo "📋 Installing review scheduler jobs..."

    # Create LaunchAgents directory if needed
    mkdir -p "$LAUNCHD_DIR"

    # Copy plist files
    for plist in "$PLIST_SOURCE"/*.plist; do
        filename=$(basename "$plist")
        echo "  Installing $filename..."
        cp "$plist" "$LAUNCHD_DIR/"

        # Load the job
        launchctl load "$LAUNCHD_DIR/$filename" 2>/dev/null || true
    done

    echo ""
    echo "✅ Installed review scheduler jobs:"
    echo "   - Daily morning review (7:00 AM weekdays)"
    echo "   - Daily financial check (4:30 PM weekdays)"
    echo "   - Weekly data upload reminder (Sunday 7:00 PM)"
    echo "   - Weekly review (Sunday 7:30 PM)"
    echo "   - Monthly review (First Sunday 6:00 PM)"
    echo ""
    echo "📝 To configure Telegram notifications, add to .env:"
    echo "   TELEGRAM_BOT_TOKEN=your_bot_token"
    echo "   TELEGRAM_CHAT_ID=your_chat_id"
    echo ""
    echo "📂 Logs will be written to: $LOG_DIR"
}

uninstall_jobs() {
    echo "🗑️ Uninstalling review scheduler jobs..."

    for plist in "$LAUNCHD_DIR"/com.heath.review.*.plist; do
        if [ -f "$plist" ]; then
            filename=$(basename "$plist")
            echo "  Unloading $filename..."
            launchctl unload "$plist" 2>/dev/null || true
            rm "$plist"
        fi
    done

    echo "✅ Review scheduler jobs uninstalled"
}

list_jobs() {
    echo "📋 Review scheduler jobs:"
    echo ""
    launchctl list | grep "com.heath.review" || echo "  (no jobs loaded)"
}

test_job() {
    job_type="${1:-daily_morning}"
    echo "🧪 Testing $job_type review..."
    cd "$WORKSPACE"
    source .claude-venv/bin/activate
    python scripts/review_scheduler.py "$job_type"
}

case "${1:-help}" in
    install)
        install_jobs
        ;;
    uninstall)
        uninstall_jobs
        ;;
    list)
        list_jobs
        ;;
    test)
        test_job "$2"
        ;;
    *)
        echo "Usage: $0 {install|uninstall|list|test [type]}"
        echo ""
        echo "Commands:"
        echo "  install    - Install launchd jobs"
        echo "  uninstall  - Remove launchd jobs"
        echo "  list       - List active jobs"
        echo "  test TYPE  - Test a review type (daily_morning, weekly, monthly)"
        ;;
esac
