import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
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
    update_menu_item(519, "https://schatzsuche40.de/buchtipps/")
