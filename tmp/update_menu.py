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

def update_menu_item(item_id, new_url):
    payload = {
        "url": new_url
    }
    r = requests.post(f"{BASE}/menu-items/{item_id}", headers=HEADERS, json=payload)
    if r.status_code == 200:
        print(f"SUCCESS! Menu item {item_id} updated to {new_url}")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    update_menu_item(1732, "https://schatzsuche40.de/buchtipps/")
