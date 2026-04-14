#!/usr/bin/env python3
"""Find the correct WordPress username for the given Application Password."""
import requests
import base64

APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

# Common usernames to try
usernames = [
    "fhofmann",
    "admin",
    "schatzsuche40",
    "schatzsuche",
    "felix",
    "Felix",
    "felix.hofmann",
    "hofmann",
    "user1",
    "editor",
]

print(f"Testing Application Password: {APP_PASS[:8]}...")
print()

found = False
for username in usernames:
    creds = base64.b64encode(f"{username}:{APP_PASS}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}"}
    r = requests.get(f"{BASE}/users/me", headers=headers, timeout=8)
    status = r.status_code
    if status == 200:
        d = r.json()
        print(f"  OK Username: {username}")
        print(f"     Name: {d.get('name')}")
        print(f"     Roles: {d.get('roles')}")
        found = True
        break
    else:
        code = "?"
        try:
            code = r.json().get("code", "?")
        except Exception:
            pass
        print(f"  FAIL {username}: {status} ({code})")

if not found:
    print("None of the tested usernames worked.")

print("\nDone.")
