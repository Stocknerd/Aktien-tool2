import os

import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = os.environ['SCHATZSUCHE_WP_APP_PASSWORD']
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
}

def update_email(new_email):
    payload = {
        "email": new_email
    }
    r = requests.post(f"https://schatzsuche40.de/wp-json/wp/v2/settings", headers=HEADERS, json=payload)
    if r.status_code == 200:
        print(f"SUCCESS! Site email updated to {new_email}")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    update_email("info@schatzsuche40.de")
