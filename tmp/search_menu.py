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

def search_menu_item(title):
    r = requests.get(f"{BASE}/menu-items?search={title}", headers=HEADERS)
    if r.status_code == 200:
        items = r.json()
        for i in items:
            print(f"ID: {i['id']}, Title: {i['title']['rendered']}, Link: {i['url']}")
    else:
        print(f"Error: {r.status_code} {r.text}")

if __name__ == "__main__":
    search_menu_item("Buchtipps")
