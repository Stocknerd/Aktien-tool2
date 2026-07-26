import os

import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = os.environ['SCHATZSUCHE_WP_APP_PASSWORD']
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

def get_menu_item(item_id):
    r = requests.get(f"{BASE}/menu-items/{item_id}", headers=HEADERS)
    print(f"Status: {r.status_code}")
    print(r.text)

if __name__ == "__main__":
    get_menu_item(1732)
