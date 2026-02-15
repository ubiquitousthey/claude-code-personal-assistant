#!/usr/bin/env python3
"""
Health Analyzer - Comprehensive health analysis with historical tracking.

Features:
- SQLite database for historical health data
- Trend analysis comparing current to previous periods
- Comprehensive health reports
- Notion integration for reports and daily tracking
- Journal integration with links

Usage:
    from scripts.health_analyzer import HealthAnalyzer
    analyzer = HealthAnalyzer()
    report = analyzer.analyze_and_report(xml_path, days=30)
"""

import os
import sqlite3
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"
HEALTH_DB_ID = os.environ.get("NOTION_HEALTH_DB_ID", "2faff6d0-ac74-8179-a4f3-fdebbd4fd06a")
HEALTH_REPORTS_DB_ID = os.environ.get("NOTION_HEALTH_REPORTS_DB_ID")  # Will create if not set
JOURNAL_DB_ID = "17dff6d0-ac74-802c-b641-f867c9cf72c2"
BIG_PLAN_PAGE_ID = "2f9ff6d0-ac74-812c-b7c0-e46d2c9f8f38"

# Health metrics configuration
METRICS_CONFIG = {
    "HKQuantityTypeIdentifierStepCount": {
        "name": "steps",
        "unit": "steps",
        "aggregation": "sum",
        "goal": 8000,
        "direction": "higher_better",
    },
    "HKQuantityTypeIdentifierDistanceWalkingRunning": {
        "name": "distance_miles",
        "unit": "miles",
        "aggregation": "sum",
        "convert": lambda x: x * 0.000621371,  # meters to miles
        "direction": "higher_better",
    },
    "HKQuantityTypeIdentifierActiveEnergyBurned": {
        "name": "active_calories",
        "unit": "kcal",
        "aggregation": "sum",
        "goal": 500,
        "direction": "higher_better",
    },
    "HKQuantityTypeIdentifierBodyMass": {
        "name": "weight_lbs",
        "unit": "lbs",
        "aggregation": "last",
        "convert": lambda x: x * 2.20462,  # kg to lbs
        "direction": "lower_better",  # Assuming weight loss goal
    },
    "HKQuantityTypeIdentifierHeartRate": {
        "name": "avg_heart_rate",
        "unit": "bpm",
        "aggregation": "avg",
        "direction": "neutral",
    },
    "HKQuantityTypeIdentifierRestingHeartRate": {
        "name": "resting_heart_rate",
        "unit": "bpm",
        "aggregation": "avg",
        "goal": 60,
        "direction": "lower_better",
    },
    "HKCategoryTypeIdentifierSleepAnalysis": {
        "name": "sleep_hours",
        "unit": "hours",
        "aggregation": "sum",
        "is_category": True,
        "goal": 7,
        "direction": "higher_better",
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


@dataclass
class HealthReport:
    """Health report data structure."""
    report_date: str
    period_start: str
    period_end: str
    days_analyzed: int

    # Current period metrics
    current_metrics: Dict[str, float]

    # Previous period comparison
    previous_metrics: Dict[str, float]
    changes: Dict[str, Dict[str, Any]]  # metric -> {change, pct, direction}

    # Analysis
    highlights: List[str]
    concerns: List[str]
    streaks: Dict[str, int]
    personal_records: List[str]

    # Goal progress
    goal_progress: Dict[str, Dict[str, Any]]

    # Workouts
    workout_count: int
    workout_types: Dict[str, int]

    # Notion page ID (after creation)
    notion_page_id: Optional[str] = None
    notion_url: Optional[str] = None


class HealthAnalyzer:
    """Comprehensive health analyzer with SQLite history tracking."""

    def __init__(self, db_path: str = "/workspace/data/health_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_API_VERSION,
        }

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Daily health metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                steps INTEGER,
                distance_miles REAL,
                active_calories INTEGER,
                weight_lbs REAL,
                avg_heart_rate INTEGER,
                resting_heart_rate INTEGER,
                sleep_hours REAL,
                workout_count INTEGER,
                workout_types TEXT,
                import_date TEXT,
                notion_synced INTEGER DEFAULT 0
            )
        """)

        # Import history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_date TEXT,
                xml_file TEXT,
                days_imported INTEGER,
                records_processed INTEGER,
                report_notion_id TEXT
            )
        """)

        # Personal records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_records (
                metric TEXT,
                value REAL,
                date TEXT,
                PRIMARY KEY (metric)
            )
        """)

        conn.commit()
        conn.close()

    def parse_health_export(self, xml_path: str, days: int = 30) -> Dict[str, Dict]:
        """Parse Apple Health export XML and extract daily metrics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        daily_data = defaultdict(lambda: defaultdict(list))
        workouts_by_day = defaultdict(list)

        # Parse XML iteratively for large files
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

                            metric_name = METRICS_CONFIG[record_type]["name"]
                            daily_data[date_key][metric_name].append(value)
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

        # Aggregate daily data
        aggregated = {}

        for date_key, metrics in daily_data.items():
            day_data = {"date": date_key, "workouts": workouts_by_day.get(date_key, [])}

            for metric_name, values in metrics.items():
                # Find aggregation method
                agg = "sum"
                for config in METRICS_CONFIG.values():
                    if config["name"] == metric_name:
                        agg = config["aggregation"]
                        break

                if agg == "sum":
                    day_data[metric_name] = sum(values)
                elif agg == "avg":
                    day_data[metric_name] = mean(values) if values else 0
                elif agg == "last":
                    day_data[metric_name] = values[-1] if values else None

            aggregated[date_key] = day_data

        return aggregated, record_count, workout_count

    def store_health_data(self, health_data: Dict[str, Dict]):
        """Store parsed health data in SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        import_date = datetime.now().isoformat()

        for date_key, data in health_data.items():
            workouts = data.get("workouts", [])
            workout_types = ", ".join([w["type"] for w in workouts]) if workouts else ""

            cursor.execute("""
                INSERT OR REPLACE INTO daily_metrics
                (date, steps, distance_miles, active_calories, weight_lbs,
                 avg_heart_rate, resting_heart_rate, sleep_hours,
                 workout_count, workout_types, import_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_key,
                data.get("steps"),
                data.get("distance_miles"),
                data.get("active_calories"),
                data.get("weight_lbs"),
                data.get("avg_heart_rate"),
                data.get("resting_heart_rate"),
                data.get("sleep_hours"),
                len(workouts),
                workout_types,
                import_date,
            ))

        conn.commit()
        conn.close()

    def get_previous_period_data(self, days: int = 30) -> Dict[str, float]:
        """Get aggregated data from the previous period for comparison."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Previous period is days*2 ago to days ago
        end_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days*2)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT
                AVG(steps) as avg_steps,
                AVG(distance_miles) as avg_distance,
                AVG(active_calories) as avg_calories,
                AVG(weight_lbs) as avg_weight,
                AVG(avg_heart_rate) as avg_hr,
                AVG(resting_heart_rate) as avg_rhr,
                AVG(sleep_hours) as avg_sleep,
                SUM(workout_count) as total_workouts,
                COUNT(*) as days_count
            FROM daily_metrics
            WHERE date >= ? AND date < ?
        """, (start_date, end_date))

        row = cursor.fetchone()
        conn.close()

        if row and row[8]:  # days_count > 0
            return {
                "steps": row[0] or 0,
                "distance_miles": row[1] or 0,
                "active_calories": row[2] or 0,
                "weight_lbs": row[3],
                "avg_heart_rate": row[4] or 0,
                "resting_heart_rate": row[5] or 0,
                "sleep_hours": row[6] or 0,
                "workout_count": row[7] or 0,
                "days_count": row[8],
            }
        return {}

    def get_personal_records(self) -> Dict[str, Tuple[float, str]]:
        """Get all personal records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT metric, value, date FROM personal_records")
        records = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        conn.close()
        return records

    def update_personal_records(self, health_data: Dict[str, Dict]) -> List[str]:
        """Check and update personal records, return list of new PRs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_prs = []

        # Check each metric for potential PRs
        pr_metrics = {
            "steps": ("max", "🏃 Steps"),
            "distance_miles": ("max", "📏 Distance"),
            "active_calories": ("max", "🔥 Calories"),
            "sleep_hours": ("max", "😴 Sleep"),
        }

        for metric, (direction, label) in pr_metrics.items():
            # Get current record
            cursor.execute(
                "SELECT value, date FROM personal_records WHERE metric = ?",
                (metric,)
            )
            current = cursor.fetchone()
            current_value = current[0] if current else 0

            # Find best value in new data
            values = [
                (d.get(metric, 0), date)
                for date, d in health_data.items()
                if d.get(metric)
            ]

            if values:
                if direction == "max":
                    best_value, best_date = max(values, key=lambda x: x[0])
                    is_new_pr = best_value > current_value
                else:
                    best_value, best_date = min(values, key=lambda x: x[0])
                    is_new_pr = best_value < current_value

                if is_new_pr and best_value > 0:
                    cursor.execute("""
                        INSERT OR REPLACE INTO personal_records (metric, value, date)
                        VALUES (?, ?, ?)
                    """, (metric, best_value, best_date))

                    if metric == "steps":
                        new_prs.append(f"{label}: {best_value:,.0f} on {best_date}")
                    elif metric == "distance_miles":
                        new_prs.append(f"{label}: {best_value:.2f} mi on {best_date}")
                    elif metric == "sleep_hours":
                        new_prs.append(f"{label}: {best_value:.1f} hrs on {best_date}")
                    else:
                        new_prs.append(f"{label}: {best_value:.0f} on {best_date}")

        conn.commit()
        conn.close()
        return new_prs

    def calculate_streaks(self, health_data: Dict[str, Dict]) -> Dict[str, int]:
        """Calculate current streaks for various goals."""
        sorted_dates = sorted(health_data.keys(), reverse=True)

        streaks = {
            "steps_8k": 0,
            "workout": 0,
            "sleep_7h": 0,
        }

        # Steps streak
        for date in sorted_dates:
            if health_data[date].get("steps", 0) >= 8000:
                streaks["steps_8k"] += 1
            else:
                break

        # Workout streak (any workout in a day)
        for date in sorted_dates:
            if health_data[date].get("workouts"):
                streaks["workout"] += 1
            else:
                break

        # Sleep streak
        for date in sorted_dates:
            if health_data[date].get("sleep_hours", 0) >= 7:
                streaks["sleep_7h"] += 1
            else:
                break

        return streaks

    def analyze(self, health_data: Dict[str, Dict], days: int = 30) -> HealthReport:
        """Perform comprehensive health analysis."""
        sorted_dates = sorted(health_data.keys())
        if not sorted_dates:
            raise ValueError("No health data to analyze")

        # Calculate current period averages
        current_metrics = {}
        metrics_lists = defaultdict(list)

        for data in health_data.values():
            for metric in ["steps", "distance_miles", "active_calories", "weight_lbs",
                          "avg_heart_rate", "resting_heart_rate", "sleep_hours"]:
                if data.get(metric) is not None:
                    metrics_lists[metric].append(data[metric])

        for metric, values in metrics_lists.items():
            if values:
                current_metrics[metric] = mean(values)

        # Workout stats
        total_workouts = sum(len(d.get("workouts", [])) for d in health_data.values())
        workout_types = defaultdict(int)
        for data in health_data.values():
            for w in data.get("workouts", []):
                workout_types[w["type"]] += 1

        current_metrics["workout_count"] = total_workouts

        # Get previous period for comparison
        previous_metrics = self.get_previous_period_data(days)

        # Calculate changes
        changes = {}
        for metric, current_val in current_metrics.items():
            if metric in previous_metrics and previous_metrics[metric]:
                prev_val = previous_metrics[metric]
                change = current_val - prev_val
                pct = (change / prev_val * 100) if prev_val != 0 else 0

                # Determine if change is good/bad based on metric
                direction_config = None
                for config in METRICS_CONFIG.values():
                    if config["name"] == metric:
                        direction_config = config.get("direction", "neutral")
                        break

                if direction_config == "higher_better":
                    is_good = change > 0
                elif direction_config == "lower_better":
                    is_good = change < 0
                else:
                    is_good = None

                changes[metric] = {
                    "change": change,
                    "pct": pct,
                    "direction": "↑" if change > 0 else "↓" if change < 0 else "→",
                    "is_good": is_good,
                }

        # Calculate goal progress
        goal_progress = {}

        # Steps goal: 8K/day
        steps_goal_days = sum(1 for d in health_data.values() if d.get("steps", 0) >= 8000)
        goal_progress["steps"] = {
            "target": "8,000 steps/day",
            "achieved": steps_goal_days,
            "total": len(health_data),
            "pct": steps_goal_days / len(health_data) * 100 if health_data else 0,
        }

        # Workout goal: 4/week
        weeks = max(1, len(health_data) // 7)
        workouts_per_week = total_workouts / weeks
        goal_progress["workouts"] = {
            "target": "4 workouts/week",
            "achieved": total_workouts,
            "weeks": weeks,
            "per_week": workouts_per_week,
            "pct": min(100, workouts_per_week / 4 * 100),
        }

        # Sleep goal: 7hrs/night
        sleep_goal_days = sum(1 for d in health_data.values() if d.get("sleep_hours", 0) >= 7)
        goal_progress["sleep"] = {
            "target": "7+ hours sleep",
            "achieved": sleep_goal_days,
            "total": len(health_data),
            "pct": sleep_goal_days / len(health_data) * 100 if health_data else 0,
        }

        # Calculate streaks
        streaks = self.calculate_streaks(health_data)

        # Check for personal records
        personal_records = self.update_personal_records(health_data)

        # Generate highlights
        highlights = []
        if streaks["steps_8k"] >= 3:
            highlights.append(f"🔥 {streaks['steps_8k']}-day steps streak!")
        if streaks["workout"] >= 3:
            highlights.append(f"💪 {streaks['workout']}-day workout streak!")
        if goal_progress["steps"]["pct"] >= 80:
            highlights.append(f"🎯 Hit step goal {goal_progress['steps']['pct']:.0f}% of days")
        if workouts_per_week >= 4:
            highlights.append(f"🏆 Averaging {workouts_per_week:.1f} workouts/week")
        if personal_records:
            highlights.extend([f"🏅 NEW PR: {pr}" for pr in personal_records])

        # Generate concerns
        concerns = []
        if current_metrics.get("sleep_hours", 7) < 6.5:
            concerns.append(f"😴 Low sleep average: {current_metrics['sleep_hours']:.1f} hrs")
        if goal_progress["steps"]["pct"] < 50:
            concerns.append(f"📉 Step goal only {goal_progress['steps']['pct']:.0f}% of days")
        if workouts_per_week < 2:
            concerns.append(f"⚠️ Low workout frequency: {workouts_per_week:.1f}/week")

        # Weight trend concern
        if "weight_lbs" in changes and changes["weight_lbs"]["change"] > 2:
            concerns.append(f"⚖️ Weight up {changes['weight_lbs']['change']:.1f} lbs")

        return HealthReport(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            period_start=sorted_dates[0],
            period_end=sorted_dates[-1],
            days_analyzed=len(health_data),
            current_metrics=current_metrics,
            previous_metrics=previous_metrics,
            changes=changes,
            highlights=highlights,
            concerns=concerns,
            streaks=streaks,
            personal_records=personal_records,
            goal_progress=goal_progress,
            workout_count=total_workouts,
            workout_types=dict(workout_types),
        )

    def create_notion_report(self, report: HealthReport) -> Tuple[str, str]:
        """Create a health report page in Notion and return (page_id, url)."""
        # Create page in Health database with report content
        url = "https://api.notion.com/v1/pages"

        title = f"Health Report {report.period_start} to {report.period_end}"

        # Build page content blocks
        blocks = []

        # Header
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📊 Summary"}}]
            }
        })

        # Metrics table as text
        metrics_text = f"""**Period:** {report.period_start} to {report.period_end} ({report.days_analyzed} days)

**Key Metrics:**
• Steps: {report.current_metrics.get('steps', 0):,.0f}/day avg"""

        if "steps" in report.changes:
            c = report.changes["steps"]
            metrics_text += f" ({c['direction']}{abs(c['pct']):.0f}%)"

        metrics_text += f"""
• Sleep: {report.current_metrics.get('sleep_hours', 0):.1f} hrs/night avg"""

        if "sleep_hours" in report.changes:
            c = report.changes["sleep_hours"]
            metrics_text += f" ({c['direction']}{abs(c['pct']):.0f}%)"

        metrics_text += f"""
• Workouts: {report.workout_count} total ({report.workout_count / max(1, report.days_analyzed // 7):.1f}/week)"""

        if report.current_metrics.get("weight_lbs"):
            metrics_text += f"""
• Weight: {report.current_metrics['weight_lbs']:.1f} lbs"""
            if "weight_lbs" in report.changes:
                c = report.changes["weight_lbs"]
                metrics_text += f" ({c['direction']}{abs(c['change']):.1f} lbs)"

        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": metrics_text}}]
            }
        })

        # Highlights
        if report.highlights:
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "✨ Highlights"}}]
                }
            })
            for highlight in report.highlights:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": highlight}}]
                    }
                })

        # Concerns
        if report.concerns:
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "⚠️ Areas to Improve"}}]
                }
            })
            for concern in report.concerns:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": concern}}]
                    }
                })

        # Goal Progress
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 Goal Progress"}}]
            }
        })

        goals_text = ""
        for goal_name, progress in report.goal_progress.items():
            pct = progress["pct"]
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))

            if goal_name == "steps":
                goals_text += f"Steps (8K/day): {bar} {pct:.0f}% ({progress['achieved']}/{progress['total']} days)\n"
            elif goal_name == "workouts":
                goals_text += f"Workouts (4/wk): {bar} {pct:.0f}% ({progress['per_week']:.1f}/week)\n"
            elif goal_name == "sleep":
                goals_text += f"Sleep (7+ hrs): {bar} {pct:.0f}% ({progress['achieved']}/{progress['total']} nights)\n"

        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": goals_text}}]
            }
        })

        # Workout breakdown
        if report.workout_types:
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🏋️ Workouts"}}]
                }
            })
            workout_text = "\n".join([
                f"{wtype}: {count}" for wtype, count in
                sorted(report.workout_types.items(), key=lambda x: x[1], reverse=True)
            ])
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": workout_text}}]
                }
            })

        # Create the page
        data = {
            "parent": {"database_id": HEALTH_DB_ID},
            "icon": {"emoji": "📊"},
            "properties": {
                "Date": {"title": [{"text": {"content": title}}]},
            },
            "children": blocks,
        }

        response = requests.post(url, headers=self.headers, json=data, timeout=30)

        if response.status_code == 200:
            page = response.json()
            return page["id"], page.get("url", f"https://notion.so/{page['id'].replace('-', '')}")
        else:
            raise Exception(f"Failed to create Notion report: {response.text}")

    def sync_daily_data_to_notion(self, health_data: Dict[str, Dict]):
        """Sync daily health data to Notion Health database."""
        # Get existing dates
        existing = self._get_existing_notion_dates()

        created = 0
        updated = 0

        for date_key in sorted(health_data.keys()):
            data = health_data[date_key]

            properties = {
                "Date": {"title": [{"text": {"content": date_key}}]},
            }

            if data.get("steps"):
                properties["Steps"] = {"number": int(data["steps"])}
                properties["Steps Goal Met"] = {"checkbox": data["steps"] >= 8000}

            if data.get("distance_miles"):
                properties["Distance (mi)"] = {"number": round(data["distance_miles"], 2)}

            if data.get("active_calories"):
                properties["Active Calories"] = {"number": int(data["active_calories"])}

            if data.get("weight_lbs"):
                properties["Weight (lbs)"] = {"number": round(data["weight_lbs"], 1)}

            if data.get("resting_heart_rate"):
                properties["Resting HR"] = {"number": int(data["resting_heart_rate"])}

            if data.get("avg_heart_rate"):
                properties["Avg HR"] = {"number": int(data["avg_heart_rate"])}

            if data.get("sleep_hours"):
                properties["Sleep (hrs)"] = {"number": round(data["sleep_hours"], 1)}

            workouts = data.get("workouts", [])
            if workouts:
                properties["Workouts"] = {"number": len(workouts)}
                workout_types = ", ".join([w["type"] for w in workouts])
                properties["Workout Types"] = {
                    "rich_text": [{"text": {"content": workout_types[:2000]}}]
                }

            if date_key in existing:
                # Update
                response = requests.patch(
                    f"https://api.notion.com/v1/pages/{existing[date_key]}",
                    headers=self.headers,
                    json={"properties": properties},
                    timeout=30,
                )
                if response.status_code == 200:
                    updated += 1
            else:
                # Create
                response = requests.post(
                    "https://api.notion.com/v1/pages",
                    headers=self.headers,
                    json={"parent": {"database_id": HEALTH_DB_ID}, "properties": properties},
                    timeout=30,
                )
                if response.status_code == 200:
                    created += 1

        return created, updated

    def _get_existing_notion_dates(self) -> Dict[str, str]:
        """Get existing date entries from Notion database."""
        url = f"https://api.notion.com/v1/databases/{HEALTH_DB_ID}/query"

        existing = {}
        has_more = True
        start_cursor = None

        while has_more:
            payload = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()

                for page in data.get("results", []):
                    title_prop = page["properties"].get("Date", {})
                    title_list = title_prop.get("title", [])
                    if title_list:
                        date_str = title_list[0].get("plain_text", "")
                        # Only include actual dates (YYYY-MM-DD format)
                        if len(date_str) == 10 and date_str[4] == "-":
                            existing[date_str] = page["id"]

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            else:
                break

        return existing

    def add_to_journal(self, report: HealthReport):
        """Add health report summary to today's journal with link."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Find or create today's journal entry
        entry = self._find_journal_entry(today)
        if not entry:
            entry = self._create_journal_entry(today)

        if not entry:
            return False

        page_id = entry["id"]

        # Build journal content
        summary = f"💪 Health Report ({report.days_analyzed} days): "
        summary += f"{report.current_metrics.get('steps', 0):,.0f} steps/day avg, "
        summary += f"{report.workout_count} workouts"

        if report.highlights:
            summary += f" | {report.highlights[0]}"

        # Add to journal with link
        rich_text = [
            {"type": "text", "text": {"content": summary}}
        ]

        if report.notion_url:
            rich_text.append({"type": "text", "text": {"content": " - "}})
            rich_text.append({
                "type": "text",
                "text": {"content": "View Report", "link": {"url": report.notion_url}},
                "annotations": {"color": "blue"}
            })

        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        payload = {
            "children": [{
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text}
            }]
        }

        response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
        return response.status_code == 200

    def _find_journal_entry(self, date_str: str) -> Optional[Dict]:
        """Find journal entry for a specific date."""
        url = f"https://api.notion.com/v1/databases/{JOURNAL_DB_ID}/query"
        payload = {
            "filter": {
                "property": "Name",
                "title": {"equals": date_str}
            }
        }

        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return results[0] if results else None
        return None

    def _create_journal_entry(self, date_str: str) -> Optional[Dict]:
        """Create journal entry for a specific date."""
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": JOURNAL_DB_ID},
            "icon": {"type": "emoji", "emoji": "📆"},
            "properties": {
                "Name": {"title": [{"text": {"content": date_str}}]},
                "Journaled?": {"checkbox": True}
            }
        }

        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None

    def analyze_and_report(self, xml_path: str, days: int = 30) -> HealthReport:
        """Complete analysis workflow: parse, store, analyze, report, journal."""
        # Parse health data
        health_data, record_count, workout_count = self.parse_health_export(xml_path, days)

        if not health_data:
            raise ValueError("No health data found in export")

        # Store in SQLite
        self.store_health_data(health_data)

        # Sync daily data to Notion
        created, updated = self.sync_daily_data_to_notion(health_data)

        # Analyze
        report = self.analyze(health_data, days)

        # Create Notion report page
        page_id, page_url = self.create_notion_report(report)
        report.notion_page_id = page_id
        report.notion_url = page_url

        # Add to journal
        self.add_to_journal(report)

        # Record import
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO import_history (import_date, xml_file, days_imported, records_processed, report_notion_id)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), xml_path, days, record_count, page_id))
        conn.commit()
        conn.close()

        return report

    def format_telegram_report(self, report: HealthReport) -> str:
        """Format report for Telegram message."""
        lines = []

        lines.append(f"💪 HEALTH REPORT ({report.days_analyzed} days)")
        lines.append(f"📅 {report.period_start} to {report.period_end}")
        lines.append("")

        # Key metrics
        lines.append("📊 KEY METRICS")
        lines.append(f"   Steps: {report.current_metrics.get('steps', 0):,.0f}/day avg")
        if "steps" in report.changes:
            c = report.changes["steps"]
            emoji = "✅" if c.get("is_good") else "❌" if c.get("is_good") is False else "➡️"
            lines[-1] += f" {emoji} {c['direction']}{abs(c['pct']):.0f}%"

        lines.append(f"   Sleep: {report.current_metrics.get('sleep_hours', 0):.1f} hrs/night")
        if "sleep_hours" in report.changes:
            c = report.changes["sleep_hours"]
            emoji = "✅" if c.get("is_good") else "❌" if c.get("is_good") is False else "➡️"
            lines[-1] += f" {emoji} {c['direction']}{abs(c['pct']):.0f}%"

        lines.append(f"   Workouts: {report.workout_count} ({report.workout_count / max(1, report.days_analyzed // 7):.1f}/week)")

        if report.current_metrics.get("weight_lbs"):
            lines.append(f"   Weight: {report.current_metrics['weight_lbs']:.1f} lbs")
            if "weight_lbs" in report.changes:
                c = report.changes["weight_lbs"]
                emoji = "✅" if c.get("is_good") else "❌" if c.get("is_good") is False else "➡️"
                lines[-1] += f" {emoji} {c['direction']}{abs(c['change']):.1f} lbs"

        lines.append("")

        # Goal progress
        lines.append("🎯 GOAL PROGRESS")
        for goal_name, progress in report.goal_progress.items():
            pct = progress["pct"]
            bar = "█" * int(pct / 12.5) + "░" * (8 - int(pct / 12.5))

            if goal_name == "steps":
                lines.append(f"   Steps 8K: {bar} {pct:.0f}%")
            elif goal_name == "workouts":
                lines.append(f"   4/week:   {bar} {pct:.0f}%")
            elif goal_name == "sleep":
                lines.append(f"   Sleep 7h: {bar} {pct:.0f}%")

        lines.append("")

        # Highlights
        if report.highlights:
            lines.append("✨ HIGHLIGHTS")
            for h in report.highlights[:3]:
                lines.append(f"   {h}")
            lines.append("")

        # Concerns
        if report.concerns:
            lines.append("⚠️ AREAS TO IMPROVE")
            for c in report.concerns[:3]:
                lines.append(f"   {c}")
            lines.append("")

        # Link to full report
        if report.notion_url:
            lines.append(f"📋 Full report: {report.notion_url}")

        return "\n".join(lines)


def main():
    """CLI for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Health Analyzer")
    parser.add_argument("xml_path", nargs="?", help="Path to export.xml")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")

    args = parser.parse_args()

    if not args.xml_path:
        print("Usage: python health_analyzer.py <export.xml> [--days N]")
        return

    analyzer = HealthAnalyzer()
    report = analyzer.analyze_and_report(args.xml_path, args.days)
    print(analyzer.format_telegram_report(report))


if __name__ == "__main__":
    main()
