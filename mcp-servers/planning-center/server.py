#!/usr/bin/env python3
"""
Planning Center MCP Server

Exposes Planning Center functions as MCP tools for Claude Code agent.
"""

import sys
import json
import asyncio
from typing import Any

# Add scripts directory to path
sys.path.insert(0, "/workspace/scripts")

from pco_client import PCOClient
from pco_notion_sync import NotionCRM
from followup_manager import FollowupManager
from pco_sync_reminders import ReminderSync


class PCOMCPServer:
    """MCP Server for Planning Center integration."""

    def __init__(self):
        self.pco_client = PCOClient()
        self.notion_crm = NotionCRM()
        self.followup_manager = FollowupManager()
        self.reminder_sync = ReminderSync()

    def get_tools(self) -> list[dict]:
        """Return list of available tools."""
        return [
            {
                "name": "pco_search_people",
                "description": "Search Planning Center people by name. Supports family searches like 'Robertson kids'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Name or family to search for (e.g., 'Smith', 'Robertson kids')"
                        },
                        "include_family": {
                            "type": "boolean",
                            "description": "Whether to include household members",
                            "default": True
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "pco_get_household",
                "description": "Get all members of a household/family by person name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "person_name": {
                            "type": "string",
                            "description": "Name of a person to get their household"
                        }
                    },
                    "required": ["person_name"]
                }
            },
            {
                "name": "pco_log_contact",
                "description": "Log a contact note for a person (saves to Notion)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "person_name": {
                            "type": "string",
                            "description": "Name of person contacted"
                        },
                        "note": {
                            "type": "string",
                            "description": "What was discussed"
                        },
                        "contact_method": {
                            "type": "string",
                            "enum": ["call", "text", "in-person", "email"],
                            "description": "How contact was made",
                            "default": "call"
                        }
                    },
                    "required": ["person_name", "note"]
                }
            },
            {
                "name": "pco_get_contact_history",
                "description": "Get contact history and notes for a person",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "person_name": {
                            "type": "string",
                            "description": "Name of person"
                        }
                    },
                    "required": ["person_name"]
                }
            },
            {
                "name": "pco_get_shepherding_list",
                "description": "Get Heath's full shepherding list with contact info",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "adults_only": {
                            "type": "boolean",
                            "description": "Only return adults",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "pco_get_todays_followups",
                "description": "Get today's scheduled follow-up contacts with smart questions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_overdue": {
                            "type": "boolean",
                            "description": "Include overdue follow-ups (7+ days)",
                            "default": True
                        }
                    }
                }
            },
            {
                "name": "pco_get_my_schedule",
                "description": "Get Heath's upcoming service schedule",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "How many days to look ahead",
                            "default": 30
                        }
                    }
                }
            },
            {
                "name": "pco_mark_followup_complete",
                "description": "Mark a follow-up as completed",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "person_name": {
                            "type": "string",
                            "description": "Name of person who was followed up with"
                        }
                    },
                    "required": ["person_name"]
                }
            },
            {
                "name": "pco_get_monthly_summary",
                "description": "Get summary of follow-up progress for the current month",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict) -> Any:
        """Execute a tool and return the result."""
        if name == "pco_search_people":
            return self._search_people(arguments)
        elif name == "pco_get_household":
            return self._get_household(arguments)
        elif name == "pco_log_contact":
            return self._log_contact(arguments)
        elif name == "pco_get_contact_history":
            return self._get_contact_history(arguments)
        elif name == "pco_get_shepherding_list":
            return self._get_shepherding_list(arguments)
        elif name == "pco_get_todays_followups":
            return self._get_todays_followups(arguments)
        elif name == "pco_get_my_schedule":
            return self._get_my_schedule(arguments)
        elif name == "pco_mark_followup_complete":
            return self._mark_followup_complete(arguments)
        elif name == "pco_get_monthly_summary":
            return self._get_monthly_summary(arguments)
        else:
            return {"error": f"Unknown tool: {name}"}

    def _search_people(self, args: dict) -> dict:
        """Search for people in PCO."""
        query = args.get("query", "")
        include_family = args.get("include_family", True)

        people = self.pco_client.search_people(query, include_family=include_family)

        return {
            "count": len(people),
            "people": [
                {
                    "name": p.name,
                    "phone": p.primary_phone,
                    "email": p.primary_email,
                    "household": p.household_name,
                    "is_child": p.is_child,
                    "pco_id": p.pco_id
                }
                for p in people
            ]
        }

    def _get_household(self, args: dict) -> dict:
        """Get household members for a person."""
        person_name = args.get("person_name", "")

        # First find the person
        people = self.pco_client.search_people(person_name, include_family=False)
        if not people:
            return {"error": f"Person not found: {person_name}"}

        person = people[0]
        if not person.household_id:
            return {"error": f"{person.name} has no household"}

        household = self.pco_client.get_household(person.household_id)

        return {
            "household_name": household.name,
            "adults": [
                {"name": p.name, "phone": p.primary_phone, "email": p.primary_email}
                for p in household.adults
            ],
            "children": [
                {"name": p.name}
                for p in household.children
            ]
        }

    def _log_contact(self, args: dict) -> dict:
        """Log a contact note."""
        person_name = args.get("person_name", "")
        note = args.get("note", "")
        contact_method = args.get("contact_method", "call")

        result = self.notion_crm.log_contact_note(person_name, note, contact_method)

        # Also mark follow-up as complete if applicable
        if result.get("status") == "success":
            self.followup_manager.mark_followup_complete(person_name, note)

        return result

    def _get_contact_history(self, args: dict) -> dict:
        """Get contact history for a person."""
        person_name = args.get("person_name", "")
        return self.notion_crm.get_contact_history(person_name)

    def _get_shepherding_list(self, args: dict) -> dict:
        """Get the shepherding list."""
        adults_only = args.get("adults_only", False)

        people = self.pco_client.get_shepherding_list()
        if adults_only:
            people = [p for p in people if not p.is_child]

        # Group by household
        households = {}
        for p in people:
            hh = p.household_name or "Unknown"
            if hh not in households:
                households[hh] = []
            households[hh].append({
                "name": p.name,
                "phone": p.primary_phone,
                "email": p.primary_email,
                "is_child": p.is_child
            })

        return {
            "total_people": len(people),
            "total_households": len(households),
            "households": households
        }

    def _get_todays_followups(self, args: dict) -> dict:
        """Get today's follow-ups."""
        include_overdue = args.get("include_overdue", True)
        followups = self.followup_manager.get_todays_followups(include_overdue=include_overdue)

        return {
            "count": len(followups),
            "followups": followups
        }

    def _get_my_schedule(self, args: dict) -> dict:
        """Get service schedules."""
        days_ahead = args.get("days_ahead", 30)
        schedules = self.pco_client.get_my_schedules(days_ahead=days_ahead)

        return {
            "count": len(schedules),
            "schedules": [
                {
                    "date": s.plan_date.isoformat() if s.plan_date else None,
                    "service_type": s.service_type,
                    "team": s.team_name,
                    "position": s.position,
                    "status": s.status
                }
                for s in schedules
            ]
        }

    def _mark_followup_complete(self, args: dict) -> dict:
        """Mark a follow-up as complete."""
        person_name = args.get("person_name", "")
        success = self.followup_manager.mark_followup_complete(person_name)

        return {
            "success": success,
            "person": person_name
        }

    def _get_monthly_summary(self, args: dict) -> dict:
        """Get monthly follow-up summary."""
        return self.followup_manager.get_monthly_summary()


def main():
    """Run the MCP server or test tools via CLI."""
    import sys

    server = PCOMCPServer()

    if len(sys.argv) < 2:
        print("Planning Center MCP Server")
        print("\nUsage: server.py <command> [args]")
        print("\nCommands:")
        print("  tools                    - List available tools")
        print("  call <tool> <json_args>  - Call a tool")
        print("\nExample:")
        print('  server.py call pco_search_people \'{"query": "Robertson kids"}\'')
        return

    cmd = sys.argv[1]

    if cmd == "tools":
        tools = server.get_tools()
        print(f"Available tools ({len(tools)}):\n")
        for tool in tools:
            print(f"  {tool['name']}")
            print(f"    {tool['description']}")
            print()

    elif cmd == "call" and len(sys.argv) >= 3:
        tool_name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

        result = server.call_tool(tool_name, args)
        print(json.dumps(result, indent=2, default=str))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
