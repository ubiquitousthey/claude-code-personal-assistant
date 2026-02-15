#!/usr/bin/env python3
"""
Apple Health to Notion Sync

Parses Apple Health XML exports and syncs key metrics to Notion.

Usage:
    # First time - create database
    python scripts/apple_health_to_notion.py --create-db

    # Sync health data
    python scripts/apple_health_to_notion.py /path/to/export.xml

    # Sync specific date range
    python scripts/apple_health_to_notion.py /path/to/export.xml --days 30

Export Apple Health data:
    iPhone → Settings → Health → Export All Health Data → Save export.zip
    Extract export.xml from the zip file
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# Configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
BIG_PLAN_PAGE_ID = "2f9ff6d0-ac74-812c-b7c0-e46d2c9f8f38"  # Parent page for new DB
HEALTH_DB_ID = os.environ.get("NOTION_HEALTH_DB_ID")  # Set after creation

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Health metrics to track (Apple Health type identifiers)
METRICS_CONFIG = {
    "HKQuantityTypeIdentifierStepCount": {
        "name": "Steps",
        "unit": "steps",
        "aggregation": "sum",
    },
    "HKQuantityTypeIdentifierDistanceWalkingRunning": {
        "name": "Distance",
        "unit": "miles",
        "aggregation": "sum",
        "convert": lambda x: x * 0.000621371,  # meters to miles
    },
    "HKQuantityTypeIdentifierActiveEnergyBurned": {
        "name": "Active Calories",
        "unit": "kcal",
        "aggregation": "sum",
    },
    "HKQuantityTypeIdentifierBodyMass": {
        "name": "Weight",
        "unit": "lbs",
        "aggregation": "last",
        "convert": lambda x: x * 2.20462,  # kg to lbs
    },
    "HKQuantityTypeIdentifierHeartRate": {
        "name": "Avg Heart Rate",
        "unit": "bpm",
        "aggregation": "avg",
    },
    "HKQuantityTypeIdentifierRestingHeartRate": {
        "name": "Resting Heart Rate",
        "unit": "bpm",
        "aggregation": "avg",
    },
    "HKCategoryTypeIdentifierSleepAnalysis": {
        "name": "Sleep",
        "unit": "hours",
        "aggregation": "sum",
        "is_category": True,
    },
}

WORKOUT_TYPES = {
    "HKWorkoutActivityTypeRunning": "🏃 Running",
    "HKWorkoutActivityTypeWalking": "🚶 Walking",
    "HKWorkoutActivityTypeCycling": "🚴 Cycling",
    "HKWorkoutActivityTypeSwimming": "🏊 Swimming",
    "HKWorkoutActivityTypeYoga": "🧘 Yoga",
    "HKWorkoutActivityTypeFunctionalStrengthTraining": "💪 Strength",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "🔥 HIIT",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "🏋️ Weights",
    "HKWorkoutActivityTypeCoreTraining": "🎯 Core",
    "HKWorkoutActivityTypeElliptical": "⭕ Elliptical",
    "HKWorkoutActivityTypeStairClimbing": "🪜 Stairs",
    "HKWorkoutActivityTypeOther": "🏅 Other",
}


def create_health_database() -> Optional[str]:
    """Create the Health Tracking database in Notion."""
    url = "https://api.notion.com/v1/databases"

    data = {
        "parent": {"page_id": BIG_PLAN_PAGE_ID},
        "icon": {"emoji": "💪"},
        "title": [{"text": {"content": "Health Tracking"}}],
        "properties": {
            "Date": {"title": {}},
            "Steps": {"number": {"format": "number_with_commas"}},
            "Steps Goal Met": {"checkbox": {}},
            "Distance (mi)": {"number": {"format": "number"}},
            "Active Calories": {"number": {"format": "number"}},
            "Weight (lbs)": {"number": {"format": "number"}},
            "Resting HR": {"number": {"format": "number"}},
            "Avg HR": {"number": {"format": "number"}},
            "Sleep (hrs)": {"number": {"format": "number"}},
            "Workouts": {"number": {"format": "number"}},
            "Workout Types": {"rich_text": {}},
        },
    }

    response = requests.post(url, headers=HEADERS, json=data)

    if response.status_code == 200:
        db = response.json()
        db_id = db["id"]
        print(f"✅ Created Health Tracking database")
        print(f"   Database ID: {db_id}")
        print(f"   URL: {db['url']}")
        print(f"\n📝 Add this to your .env file:")
        print(f"   NOTION_HEALTH_DB_ID={db_id}")
        return db_id
    else:
        print(f"❌ Failed to create database: {response.text}")
        return None


def parse_health_export(xml_path: str, days: int = 30) -> dict:
    """Parse Apple Health export XML and extract daily metrics."""
    print(f"📖 Parsing {xml_path}...")

    cutoff_date = datetime.now() - timedelta(days=days)
    daily_data = defaultdict(lambda: defaultdict(list))
    workouts_by_day = defaultdict(list)

    # Parse XML iteratively to handle large files
    context = ET.iterparse(xml_path, events=("end",))
    record_count = 0
    workout_count = 0

    for event, elem in context:
        if elem.tag == "Record":
            record_type = elem.get("type")

            if record_type in METRICS_CONFIG:
                try:
                    start_date = datetime.strptime(
                        elem.get("startDate")[:19], "%Y-%m-%d %H:%M:%S"
                    )

                    if start_date >= cutoff_date:
                        date_key = start_date.strftime("%Y-%m-%d")

                        if METRICS_CONFIG[record_type].get("is_category"):
                            # Sleep analysis - calculate duration
                            end_date = datetime.strptime(
                                elem.get("endDate")[:19], "%Y-%m-%d %H:%M:%S"
                            )
                            value = (end_date - start_date).total_seconds() / 3600
                        else:
                            value = float(elem.get("value", 0))

                        # Apply conversion if needed
                        convert = METRICS_CONFIG[record_type].get("convert")
                        if convert:
                            value = convert(value)

                        daily_data[date_key][record_type].append(value)
                        record_count += 1
                except (ValueError, TypeError):
                    pass

            elem.clear()

        elif elem.tag == "Workout":
            try:
                start_date = datetime.strptime(
                    elem.get("startDate")[:19], "%Y-%m-%d %H:%M:%S"
                )

                if start_date >= cutoff_date:
                    date_key = start_date.strftime("%Y-%m-%d")
                    workout_type = elem.get("workoutActivityType", "Unknown")
                    duration = float(elem.get("duration", 0))

                    workouts_by_day[date_key].append({
                        "type": WORKOUT_TYPES.get(workout_type, "🏅 Other"),
                        "duration": duration,
                    })
                    workout_count += 1
            except (ValueError, TypeError):
                pass

            elem.clear()

    print(f"   Found {record_count} health records")
    print(f"   Found {workout_count} workouts")

    # Aggregate daily data
    aggregated = {}

    for date_key, metrics in daily_data.items():
        day_data = {"date": date_key, "workouts": workouts_by_day.get(date_key, [])}

        for metric_type, values in metrics.items():
            config = METRICS_CONFIG[metric_type]
            name = config["name"]
            agg = config["aggregation"]

            if agg == "sum":
                day_data[name] = sum(values)
            elif agg == "avg":
                day_data[name] = sum(values) / len(values) if values else 0
            elif agg == "last":
                day_data[name] = values[-1] if values else None

        aggregated[date_key] = day_data

    return aggregated


def sync_to_notion(health_data: dict, db_id: str):
    """Sync health data to Notion database."""
    print(f"\n📤 Syncing {len(health_data)} days to Notion...")

    # Get existing entries to avoid duplicates
    existing_dates = get_existing_dates(db_id)

    created = 0
    updated = 0

    for date_key in sorted(health_data.keys()):
        data = health_data[date_key]

        # Prepare properties
        properties = {
            "Date": {"title": [{"text": {"content": date_key}}]},
        }

        # Add metrics
        if "Steps" in data:
            properties["Steps"] = {"number": int(data["Steps"])}
            properties["Steps Goal Met"] = {"checkbox": data["Steps"] >= 8000}

        if "Distance" in data:
            properties["Distance (mi)"] = {"number": round(data["Distance"], 2)}

        if "Active Calories" in data:
            properties["Active Calories"] = {"number": int(data["Active Calories"])}

        if "Weight" in data and data["Weight"]:
            properties["Weight (lbs)"] = {"number": round(data["Weight"], 1)}

        if "Resting Heart Rate" in data:
            properties["Resting HR"] = {"number": int(data["Resting Heart Rate"])}

        if "Avg Heart Rate" in data:
            properties["Avg HR"] = {"number": int(data["Avg Heart Rate"])}

        if "Sleep" in data:
            properties["Sleep (hrs)"] = {"number": round(data["Sleep"], 1)}

        # Workouts
        workouts = data.get("workouts", [])
        if workouts:
            properties["Workouts"] = {"number": len(workouts)}
            workout_types = ", ".join([w["type"] for w in workouts])
            properties["Workout Types"] = {
                "rich_text": [{"text": {"content": workout_types[:2000]}}]
            }

        # Create or update
        if date_key in existing_dates:
            # Update existing
            page_id = existing_dates[date_key]
            response = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=HEADERS,
                json={"properties": properties},
            )
            if response.status_code == 200:
                updated += 1
        else:
            # Create new
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=HEADERS,
                json={"parent": {"database_id": db_id}, "properties": properties},
            )
            if response.status_code == 200:
                created += 1

    print(f"✅ Created {created} new entries")
    print(f"✅ Updated {updated} existing entries")


def get_existing_dates(db_id: str) -> dict:
    """Get existing date entries from the database."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"

    existing = {}
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = requests.post(url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            data = response.json()

            for page in data.get("results", []):
                title_prop = page["properties"].get("Date", {})
                title_list = title_prop.get("title", [])
                if title_list:
                    date_str = title_list[0].get("plain_text", "")
                    existing[date_str] = page["id"]

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        else:
            break

    return existing


def generate_summary(health_data: dict) -> str:
    """Generate a summary of health metrics."""
    if not health_data:
        return "No data to summarize."

    dates = sorted(health_data.keys())

    # Calculate averages
    steps_list = [d.get("Steps", 0) for d in health_data.values() if d.get("Steps")]
    sleep_list = [d.get("Sleep", 0) for d in health_data.values() if d.get("Sleep")]
    workout_count = sum(len(d.get("workouts", [])) for d in health_data.values())

    avg_steps = sum(steps_list) / len(steps_list) if steps_list else 0
    avg_sleep = sum(sleep_list) / len(sleep_list) if sleep_list else 0
    steps_goal_days = sum(1 for s in steps_list if s >= 8000)

    summary = f"""
## Health Summary ({dates[0]} to {dates[-1]})

### Key Metrics
| Metric | Value | Goal Status |
|--------|-------|-------------|
| Avg Daily Steps | {avg_steps:,.0f} | {"✅" if avg_steps >= 8000 else "❌"} 8K goal |
| Days at 8K+ Steps | {steps_goal_days}/{len(steps_list)} | {steps_goal_days/len(steps_list)*100:.0f}% |
| Avg Sleep | {avg_sleep:.1f} hrs | {"✅" if avg_sleep >= 7 else "❌"} 7hr goal |
| Total Workouts | {workout_count} | {"✅" if workout_count >= len(dates)//7*4 else "❌"} 4/week goal |

### OKR Progress
- **8K Steps/Day**: {steps_goal_days}/{len(steps_list)} days ({steps_goal_days/len(steps_list)*100:.0f}%)
- **4 Workouts/Week**: {workout_count} workouts in {len(dates)//7 + 1} weeks
"""
    return summary


def main():
    parser = argparse.ArgumentParser(description="Sync Apple Health data to Notion")
    parser.add_argument("xml_path", nargs="?", help="Path to export.xml file")
    parser.add_argument("--create-db", action="store_true", help="Create Notion database")
    parser.add_argument("--days", type=int, default=30, help="Days of data to sync")
    parser.add_argument("--summary", action="store_true", help="Show summary only")

    args = parser.parse_args()

    if not NOTION_API_KEY:
        print("❌ Error: NOTION_API_KEY or NOTION_TOKEN not set")
        sys.exit(1)

    if args.create_db:
        create_health_database()
        return

    if not args.xml_path:
        parser.print_help()
        return

    if not Path(args.xml_path).exists():
        print(f"❌ Error: File not found: {args.xml_path}")
        sys.exit(1)

    # Parse health data
    health_data = parse_health_export(args.xml_path, args.days)

    if args.summary:
        print(generate_summary(health_data))
        return

    # Sync to Notion
    db_id = HEALTH_DB_ID
    if not db_id:
        print("❌ Error: NOTION_HEALTH_DB_ID not set")
        print("   Run with --create-db first to create the database")
        sys.exit(1)

    sync_to_notion(health_data, db_id)
    print(generate_summary(health_data))


if __name__ == "__main__":
    main()
