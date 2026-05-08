import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
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
