#!/usr/bin/env python3
"""
Planning Center Online (PCO) API Client

Provides access to PCO People and Services APIs for:
- Shepherding list management
- People/household search
- Service schedules
- Tasks
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv("/workspace/.env")

# Configuration
PCO_APP_ID = os.getenv("PLANNING_CENTER_CLIENT_ID")
PCO_SECRET = os.getenv("PLANNING_CETNER_SECRET_KEY")  # Note: typo in env var
BASE_URL = "https://api.planningcenteronline.com"

# Heath's IDs
HEATH_PERSON_ID = "33065814"
SHEPHERDING_LIST_ID = "3015465"


@dataclass
class PhoneNumber:
    number: str
    location: str  # e.g., "Mobile", "Home"
    primary: bool = False


@dataclass
class Email:
    address: str
    location: str
    primary: bool = False


@dataclass
class Person:
    pco_id: str
    name: str
    first_name: str
    last_name: str
    is_child: bool = False
    membership: str = ""
    phones: list[PhoneNumber] = field(default_factory=list)
    emails: list[Email] = field(default_factory=list)
    household_id: Optional[str] = None
    household_name: Optional[str] = None

    @property
    def primary_phone(self) -> Optional[str]:
        for p in self.phones:
            if p.primary:
                return p.number
        return self.phones[0].number if self.phones else None

    @property
    def primary_email(self) -> Optional[str]:
        for e in self.emails:
            if e.primary:
                return e.address
        return self.emails[0].address if self.emails else None


@dataclass
class Household:
    household_id: str
    name: str
    members: list[Person] = field(default_factory=list)
    primary_contact_id: Optional[str] = None

    @property
    def adults(self) -> list[Person]:
        return [m for m in self.members if not m.is_child]

    @property
    def children(self) -> list[Person]:
        return [m for m in self.members if m.is_child]


@dataclass
class ServiceSchedule:
    schedule_id: str
    plan_id: str
    service_type: str
    team_name: str
    position: str
    plan_date: date
    times: list[str] = field(default_factory=list)
    status: str = ""  # Confirmed, Unconfirmed, Declined


@dataclass
class PCOTask:
    task_id: str
    description: str
    due_date: Optional[date] = None
    completed: bool = False
    service_plan: Optional[str] = None


class PCOClient:
    """Client for Planning Center Online API."""

    def __init__(self):
        if not PCO_APP_ID or not PCO_SECRET:
            raise ValueError("PCO credentials not found in environment")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated GET request to PCO API."""
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            auth=(PCO_APP_ID, PCO_SECRET)
        )
        response.raise_for_status()
        return response.json()

    def _parse_person(self, data: dict, included: list[dict] = None) -> Person:
        """Parse person data from API response."""
        attrs = data["attributes"]
        person = Person(
            pco_id=data["id"],
            name=attrs.get("name", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
            is_child=attrs.get("child", False),
            membership=attrs.get("membership", ""),
        )

        # Parse included phone numbers and emails if provided
        if included:
            relationships = data.get("relationships", {})

            # Get phone numbers
            phone_refs = relationships.get("phone_numbers", {}).get("data", [])
            for ref in phone_refs:
                phone_data = next(
                    (i for i in included if i["type"] == "PhoneNumber" and i["id"] == ref["id"]),
                    None
                )
                if phone_data:
                    pattrs = phone_data["attributes"]
                    person.phones.append(PhoneNumber(
                        number=pattrs.get("number", pattrs.get("e164", "")),
                        location=pattrs.get("location", ""),
                        primary=pattrs.get("primary", False)
                    ))

            # Get emails
            email_refs = relationships.get("emails", {}).get("data", [])
            for ref in email_refs:
                email_data = next(
                    (i for i in included if i["type"] == "Email" and i["id"] == ref["id"]),
                    None
                )
                if email_data:
                    eattrs = email_data["attributes"]
                    person.emails.append(Email(
                        address=eattrs.get("address", ""),
                        location=eattrs.get("location", ""),
                        primary=eattrs.get("primary", False)
                    ))

            # Get household
            hh_refs = relationships.get("households", {}).get("data", [])
            if hh_refs:
                hh_data = next(
                    (i for i in included if i["type"] == "Household" and i["id"] == hh_refs[0]["id"]),
                    None
                )
                if hh_data:
                    person.household_id = hh_data["id"]
                    person.household_name = hh_data["attributes"].get("name", "")

        return person

    def get_shepherding_list(self) -> list[Person]:
        """Fetch all people in the shepherding list with contact info."""
        data = self._get(
            f"/people/v2/lists/{SHEPHERDING_LIST_ID}/people",
            {"include": "emails,phone_numbers,households", "per_page": 100}
        )

        included = data.get("included", [])
        people = []

        for person_data in data.get("data", []):
            person = self._parse_person(person_data, included)
            people.append(person)

        return people

    def search_people(self, query: str, include_family: bool = True) -> list[Person]:
        """
        Search for people by name.

        Supports queries like "Robertson" or "Robertson kids".
        """
        # Check if searching for kids/children specifically
        query_lower = query.lower()
        searching_kids = any(word in query_lower for word in ["kids", "children", "child"])
        if searching_kids:
            # Remove the kids/children word from query
            for word in ["kids", "children", "child"]:
                query_lower = query_lower.replace(word, "").strip()
            query = query_lower

        data = self._get(
            "/people/v2/people",
            {"where[search_name]": query, "include": "emails,phone_numbers,households", "per_page": 25}
        )

        included = data.get("included", [])
        people = []

        for person_data in data.get("data", []):
            person = self._parse_person(person_data, included)
            people.append(person)

        # If searching for kids and we found people, get their household members
        if searching_kids and people and include_family:
            # Get unique household IDs
            household_ids = set(p.household_id for p in people if p.household_id)
            kids = []
            for hh_id in household_ids:
                household = self.get_household(hh_id)
                kids.extend(household.children)
            return kids

        # If include_family, also fetch household members for found people
        if include_family and people:
            household_ids = set(p.household_id for p in people if p.household_id)
            all_people = list(people)
            seen_ids = {p.pco_id for p in people}

            for hh_id in household_ids:
                household = self.get_household(hh_id)
                for member in household.members:
                    if member.pco_id not in seen_ids:
                        all_people.append(member)
                        seen_ids.add(member.pco_id)

            return all_people

        return people

    def get_person_details(self, person_id: str) -> Person:
        """Get detailed info for a specific person."""
        data = self._get(
            f"/people/v2/people/{person_id}",
            {"include": "emails,phone_numbers,households"}
        )
        return self._parse_person(data["data"], data.get("included", []))

    def get_household(self, household_id: str) -> Household:
        """Get all members of a household."""
        # Get household info
        hh_data = self._get(f"/people/v2/households/{household_id}")
        hh_attrs = hh_data["data"]["attributes"]

        household = Household(
            household_id=household_id,
            name=hh_attrs.get("name", ""),
            primary_contact_id=hh_attrs.get("primary_contact_id")
        )

        # Get household members with contact info
        members_data = self._get(
            f"/people/v2/households/{household_id}/people",
            {"include": "emails,phone_numbers"}
        )

        included = members_data.get("included", [])
        for person_data in members_data.get("data", []):
            person = self._parse_person(person_data, included)
            person.household_id = household_id
            person.household_name = household.name
            household.members.append(person)

        return household

    def get_household_for_person(self, person_id: str) -> Optional[Household]:
        """Get the household for a specific person."""
        person = self.get_person_details(person_id)
        if person.household_id:
            return self.get_household(person.household_id)
        return None

    def get_my_schedules(self, days_ahead: int = 60) -> list[ServiceSchedule]:
        """Get Heath's upcoming service schedules."""
        data = self._get(
            f"/services/v2/people/{HEATH_PERSON_ID}/schedules",
            {"filter": "future", "per_page": 25}
        )

        schedules = []
        for sched_data in data.get("data", []):
            attrs = sched_data["attributes"]

            # Parse date
            date_str = attrs.get("sort_date") or attrs.get("plan_dates", "")
            plan_date = None
            if date_str:
                try:
                    plan_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                except ValueError:
                    pass

            schedule = ServiceSchedule(
                schedule_id=sched_data["id"],
                plan_id=attrs.get("plan_id", ""),
                service_type=attrs.get("service_type_name", ""),
                team_name=attrs.get("team_name", ""),
                position=attrs.get("team_position_name", ""),
                plan_date=plan_date,
                status=attrs.get("status", "")
            )

            # Parse times if available
            times = attrs.get("plan_times", [])
            if times:
                schedule.times = [t.get("starts_at", "") for t in times if t.get("starts_at")]

            schedules.append(schedule)

        # Filter by days_ahead
        if days_ahead:
            cutoff = date.today()
            from datetime import timedelta
            cutoff_end = cutoff + timedelta(days=days_ahead)
            schedules = [s for s in schedules if s.plan_date and cutoff <= s.plan_date <= cutoff_end]

        return sorted(schedules, key=lambda s: s.plan_date or date.max)

    def get_my_tasks(self) -> list[PCOTask]:
        """Get Heath's incomplete tasks from PCO Services."""
        # Note: PCO Services tasks are typically checklist items on plans
        # This requires iterating through scheduled plans
        tasks = []

        # Get upcoming schedules first
        schedules = self.get_my_schedules(days_ahead=30)

        for schedule in schedules:
            if not schedule.plan_id:
                continue

            try:
                # Get plan details with needed items
                # Note: This endpoint may vary based on PCO setup
                pass  # Tasks implementation depends on PCO configuration
            except Exception:
                pass

        return tasks


# Convenience functions for CLI usage
def main():
    """CLI interface for PCO client."""
    import sys

    client = PCOClient()

    if len(sys.argv) < 2:
        print("Usage: pco_client.py <command> [args]")
        print("\nCommands:")
        print("  list              - Show shepherding list")
        print("  search <query>    - Search for people")
        print("  household <id>    - Show household members")
        print("  schedules         - Show upcoming schedules")
        print("  person <id>       - Show person details")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        people = client.get_shepherding_list()
        print(f"Shepherding List ({len(people)} people):\n")
        for p in people:
            phone = p.primary_phone or "(no phone)"
            email = p.primary_email or "(no email)"
            hh = f" [{p.household_name}]" if p.household_name else ""
            child = " (child)" if p.is_child else ""
            print(f"  {p.name}{child}{hh}")
            print(f"    Phone: {phone}")
            print(f"    Email: {email}")
            print()

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        people = client.search_people(query)
        print(f"Search results for '{query}' ({len(people)} people):\n")
        for p in people:
            phone = p.primary_phone or "(no phone)"
            hh = f" [{p.household_name}]" if p.household_name else ""
            child = " (child)" if p.is_child else ""
            print(f"  {p.name}{child}{hh} - {phone}")

    elif cmd == "household" and len(sys.argv) > 2:
        hh_id = sys.argv[2]
        household = client.get_household(hh_id)
        print(f"Household: {household.name}\n")
        print("Adults:")
        for p in household.adults:
            print(f"  - {p.name}: {p.primary_phone or '(no phone)'}")
        print("\nChildren:")
        for p in household.children:
            print(f"  - {p.name}")

    elif cmd == "schedules":
        schedules = client.get_my_schedules()
        print(f"Upcoming Schedules ({len(schedules)}):\n")
        for s in schedules:
            print(f"  {s.plan_date}: {s.team_name} - {s.position}")
            print(f"    Status: {s.status}")
            print()

    elif cmd == "person" and len(sys.argv) > 2:
        person_id = sys.argv[2]
        person = client.get_person_details(person_id)
        print(f"Person: {person.name}")
        print(f"  ID: {person.pco_id}")
        print(f"  Membership: {person.membership}")
        print(f"  Phones:")
        for p in person.phones:
            primary = " (primary)" if p.primary else ""
            print(f"    - {p.location}: {p.number}{primary}")
        print(f"  Emails:")
        for e in person.emails:
            primary = " (primary)" if e.primary else ""
            print(f"    - {e.location}: {e.address}{primary}")
        if person.household_name:
            print(f"  Household: {person.household_name}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
