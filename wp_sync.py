import requests
import json
import base64

# Configuration
SITE_URL = "https://schatzsuche40.de"
USER = "fhofmann"
PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"

def get_auth_header():
    credentials = f"{USER}:{PASS}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}

def get_page_by_slug(slug):
    url = f"{SITE_URL}/wp-json/wp/v2/pages?slug={slug}"
    headers = get_auth_header()
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            p = data[0]
            print(f"--- {slug} (ID: {p['id']}) ---")
            print(p['content']['rendered'])
        else:
            print(f"Page with slug '{slug}' not found.")
    else:
        print(f"Error fetching page {slug}: {response.status_code}")

if __name__ == "__main__":
    for s in ["aktien-tool", "vergleich", ""]: # Empty slug often represents homepage or front page
        get_page_by_slug(s)
