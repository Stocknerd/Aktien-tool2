import requests
import json
import base64

SITE_URL = "https://schatzsuche40.de"
USER = "schatzsuche40"
PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"

def get_auth_header():
    credentials = f"{USER}:{PASS}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}"}

def get_page_by_slug(slug):
    url = f"{SITE_URL}/wp-json/wp/v2/pages?slug={slug}&context=edit"
    headers = get_auth_header()
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            p = data[0]
            print(f"ID: {p['id']}")
            print(f"Title: {p['title']['raw']}")
            print("Content (raw):")
            print(p['content']['raw'])
        else:
            print(f"Page '{slug}' not found.")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    get_page_by_slug("wo-aktien-kaufen")
