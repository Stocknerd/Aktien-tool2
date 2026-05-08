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

def search_iframes():
    page = 1
    while True:
        r = requests.get(f"{BASE}/pages?per_page=50&page={page}", headers=HEADERS)
        if r.status_code != 200: break
        pages = r.json()
        if not pages: break
        for p in pages:
            content = p.get('content', {}).get('rendered', '')
            if 'iframe' in content:
                print(f"ID: {p['id']}, Link: {p['link']}, Title: {p['title']['rendered']}")
                # Check for dividend-rechner in iframe
                if 'dividend-rechner' in content or 'dividend' in content:
                     print(f"  --> FOUND DIVIDEND IN IFRAME on page {p['id']}")
        page += 1

if __name__ == "__main__":
    search_iframes()
