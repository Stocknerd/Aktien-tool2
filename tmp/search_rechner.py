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

def search_text(query):
    page = 1
    while True:
        r = requests.get(f"{BASE}/pages?per_page=50&page={page}", headers=HEADERS)
        if r.status_code != 200: break
        pages = r.json()
        if not pages: break
        for p in pages:
            content = p.get('content', {}).get('raw', '')
            if query.lower() in content.lower():
                print(f"ID: {p['id']}, Link: {p['link']}, Title: {p['title']['rendered']}")
        page += 1

if __name__ == "__main__":
    search_text("Rechner")
