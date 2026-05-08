import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

def list_menus():
    r = requests.get(f"https://schatzsuche40.de/wp-json/wp/v2/menus", headers=HEADERS)
    if r.status_code == 200:
        menus = r.json()
        for m in menus:
            print(f"Menu ID: {m['id']}, Name: {m['name']}")
    else:
        print(f"Error: {r.status_code} {r.text}")

def list_menu_items(menu_id):
    r = requests.get(f"https://schatzsuche40.de/wp-json/wp/v2/menu-items?menus={menu_id}", headers=HEADERS)
    if r.status_code == 200:
        items = r.json()
        for i in items:
            print(f"Item ID: {i['id']}, Title: {i['title']['rendered']}, Link: {i['url']}")
    else:
        print(f"Error: {r.status_code}")

if __name__ == "__main__":
    list_menus()
    # If ID found, list items
    # list_menu_items(...)
