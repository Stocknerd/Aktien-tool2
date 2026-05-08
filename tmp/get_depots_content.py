import requests
import base64
import sys

# Set stdout to utf-8
sys.stdout.reconfigure(encoding='utf-8')

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

def get_page_content(page_id):
    r = requests.get(f"{BASE}/pages/{page_id}?context=edit", headers=HEADERS)
    if r.status_code == 200:
        print(r.json().get('content', {}).get('raw'))
    else:
        print(f"Error: {r.status_code} {r.text}")

if __name__ == "__main__":
    get_page_content(114)
