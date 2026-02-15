#!/usr/bin/env python3
"""Find a person's ID in Planning Center."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

PCO_APP_ID = os.getenv("PLANNING_CENTER_CLIENT_ID")
PCO_SECRET = os.getenv("PLANNING_CETNER_SECRET_KEY")  # Note: typo in env var name

BASE_URL = "https://api.planningcenteronline.com"

def search_people(query: str):
    """Search for people by name."""
    url = f"{BASE_URL}/people/v2/people"
    params = {"where[search_name]": query}

    response = requests.get(url, params=params, auth=(PCO_APP_ID, PCO_SECRET))
    response.raise_for_status()

    data = response.json()
    people = data.get("data", [])

    print(f"Found {len(people)} results for '{query}':\n")
    for person in people[:10]:  # Limit to 10 results
        pid = person["id"]
        attrs = person["attributes"]
        name = attrs.get("name", "Unknown")
        email = attrs.get("primary_email") or "(no email)"
        membership = attrs.get("membership", "")
        print(f"  ID: {pid}")
        print(f"  Name: {name}")
        print(f"  Email: {email}")
        print(f"  Membership: {membership}")
        print()

    return people

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Heath"
    search_people(query)
