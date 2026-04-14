#!/usr/bin/env python3
import requests
import base64

creds = base64.b64encode(b"fhofmann:Pm8T ZqbK 8Muk FgkC kBB0 UIN4").decode()
headers = {"Authorization": f"Basic {creds}"}

# Check user info
r = requests.get("https://schatzsuche40.de/wp-json/wp/v2/users/me?context=edit", headers=headers, timeout=10)
print(f"User info status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"Name: {d.get('name')}")
    print(f"Roles: {d.get('roles')}")
    caps = d.get("capabilities", {})
    print(f"edit_pages: {caps.get('edit_pages')}")
    print(f"edit_others_pages: {caps.get('edit_others_pages')}")
    print(f"publish_pages: {caps.get('publish_pages')}")
    print(f"administrator: {caps.get('administrator')}")
else:
    print(r.text[:300])

# List pages I can see
print("\nListing pages...")
r2 = requests.get("https://schatzsuche40.de/wp-json/wp/v2/pages?per_page=20", headers=headers, timeout=10)
print(f"Pages list status: {r2.status_code}")
if r2.status_code == 200:
    for p in r2.json():
        print(f"  ID: {p['id']} | Author: {p.get('author')} | {p['title']['rendered']}")
