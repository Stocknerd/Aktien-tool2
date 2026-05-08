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

OLD_ID = "schatzsuche0c-21"
NEW_ID = "schatzsuch0c4-21"

def update_amazon_links():
    # 1. Update Posts
    page = 1
    while True:
        r = requests.get(f"{BASE}/posts?per_page=100&page={page}&context=edit", headers=HEADERS)
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
            
        for p in posts:
            content = p.get('content', {}).get('raw', '')
            if OLD_ID in content:
                print(f"Updating Post: {p['id']} - {p['title']['rendered']}")
                new_content = content.replace(OLD_ID, NEW_ID)
                requests.post(f"{BASE}/posts/{p['id']}", headers=HEADERS, json={"content": new_content})
        
        page += 1

    # 2. Update Pages
    page = 1
    while True:
        r = requests.get(f"{BASE}/pages?per_page=100&page={page}&context=edit", headers=HEADERS)
        if r.status_code != 200:
            break
        pages = r.json()
        if not pages:
            break
            
        for p in pages:
            content = p.get('content', {}).get('raw', '')
            if OLD_ID in content:
                print(f"Updating Page: {p['id']} - {p['title']['rendered']}")
                new_content = content.replace(OLD_ID, NEW_ID)
                requests.post(f"{BASE}/pages/{p['id']}", headers=HEADERS, json={"content": new_content})
        
        page += 1

if __name__ == "__main__":
    update_amazon_links()
