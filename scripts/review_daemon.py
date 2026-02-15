#!/usr/bin/env python3
"""
Review Scheduler Daemon

Runs in the background and triggers reviews at scheduled times.
Uses the Python 'schedule' library instead of system cron.

Usage:
  python scripts/review_daemon.py start   # Start daemon in background
  python scripts/review_daemon.py stop    # Stop daemon
  python scripts/review_daemon.py status  # Check if running
  python scripts/review_daemon.py run     # Run in foreground (for testing)
"""

import os
import sys
import time
import signal
import schedule
from datetime import datetime, date
from pathlib import Path

# Add scripts to path
sys.path.insert(0, "/workspace/scripts")

PID_FILE = "/workspace/data/review_daemon.pid"
LOG_FILE = "/workspace/logs/review_daemon.log"


def log(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)

    # Also write to log file
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")


def run_review(review_type: str):
    """Run a review via the scheduler script."""
    log(f"Running {review_type} review...")

    try:
        from review_scheduler import (
            run_daily_morning, run_daily_financial,
            run_weekly, run_weekly_data_upload, run_monthly
        )

        if review_type == "daily_morning":
            run_daily_morning()
        elif review_type == "daily_financial":
            run_daily_financial()
        elif review_type == "weekly":
            run_weekly()
        elif review_type == "weekly_upload":
            run_weekly_data_upload()
        elif review_type == "monthly":
            run_monthly()

        log(f"Completed {review_type} review")
    except Exception as e:
        log(f"Error running {review_type}: {e}")


def sync_calendars():
    """Sync calendars from ICS feeds."""
    log("Syncing calendars...")
    try:
        from calendar_sync import sync_calendars as do_sync
        do_sync()
        log("Calendar sync complete")
    except Exception as e:
        log(f"Calendar sync error: {e}")


def setup_schedule():
    """Set up the review schedule."""
    # Calendar sync: Every hour
    schedule.every().hour.do(sync_calendars)

    # Daily morning review: 5:30 AM weekdays
    schedule.every().monday.at("05:30").do(run_review, "daily_morning")
    schedule.every().tuesday.at("05:30").do(run_review, "daily_morning")
    schedule.every().wednesday.at("05:30").do(run_review, "daily_morning")
    schedule.every().thursday.at("05:30").do(run_review, "daily_morning")
    schedule.every().friday.at("05:30").do(run_review, "daily_morning")

    # Daily financial: 4:00 PM weekdays
    schedule.every().monday.at("16:00").do(run_review, "daily_financial")
    schedule.every().tuesday.at("16:00").do(run_review, "daily_financial")
    schedule.every().wednesday.at("16:00").do(run_review, "daily_financial")
    schedule.every().thursday.at("16:00").do(run_review, "daily_financial")
    schedule.every().friday.at("16:00").do(run_review, "daily_financial")

    # Weekly reviews: Sunday 8:00 PM
    schedule.every().sunday.at("20:00").do(run_review, "weekly_upload")
    schedule.every().sunday.at("20:00").do(run_review, "weekly")
    schedule.every().sunday.at("20:00").do(run_review, "monthly")  # Will skip if not first Sunday

    log("Schedule configured:")
    log("  - Calendar sync: Every hour")
    log("  - Daily morning: 5:30 AM (Mon-Fri)")
    log("  - Daily financial: 4:00 PM (Mon-Fri)")
    log("  - Weekly/Monthly: 8:00 PM (Sunday)")

    # Run initial calendar sync
    sync_calendars()


def run_daemon():
    """Run the scheduler loop."""
    setup_schedule()
    log("Review daemon started")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def start_daemon():
    """Start the daemon in background."""
    # Check if already running
    if Path(PID_FILE).exists():
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)  # Check if process exists
            print(f"Daemon already running (PID {pid})")
            return
        except ProcessLookupError:
            pass  # Process doesn't exist, continue

    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Parent process
        print(f"Started review daemon (PID {pid})")
        print(f"Log file: {LOG_FILE}")
        return

    # Child process - become daemon
    os.setsid()

    # Write PID file
    Path(PID_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    # Run the daemon
    try:
        run_daemon()
    except KeyboardInterrupt:
        log("Daemon stopped by user")
    finally:
        Path(PID_FILE).unlink(missing_ok=True)


def stop_daemon():
    """Stop the daemon."""
    if not Path(PID_FILE).exists():
        print("Daemon not running")
        return

    with open(PID_FILE) as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped daemon (PID {pid})")
    except ProcessLookupError:
        print("Daemon was not running")

    Path(PID_FILE).unlink(missing_ok=True)


def daemon_status():
    """Check daemon status."""
    if not Path(PID_FILE).exists():
        print("Daemon not running")
        return False

    with open(PID_FILE) as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, 0)
        print(f"Daemon running (PID {pid})")

        # Show next scheduled jobs
        print("\nNext scheduled runs:")
        for job in schedule.get_jobs()[:5]:
            print(f"  {job}")

        return True
    except ProcessLookupError:
        print("Daemon not running (stale PID file)")
        Path(PID_FILE).unlink(missing_ok=True)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: review_daemon.py {start|stop|status|run}")
        print("\nCommands:")
        print("  start   - Start daemon in background")
        print("  stop    - Stop daemon")
        print("  status  - Check if daemon is running")
        print("  run     - Run in foreground (Ctrl+C to stop)")
        return

    cmd = sys.argv[1]

    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "status":
        daemon_status()
    elif cmd == "run":
        try:
            run_daemon()
        except KeyboardInterrupt:
            log("Daemon stopped")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
