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

def fix_amazon_links():
    # Page 1872: Buchtipps
    page_id = 1872
    r = requests.get(f"{BASE}/pages/{page_id}?context=edit", headers=HEADERS)
    if r.status_code != 200:
        print(f"Error fetching page: {r.status_code}")
        return

    content = r.json().get('content', {}).get('raw', '')
    
    # Old broken link: https://www.amazon.de/dp/3548359544?tag=schatzsuch0c4-21
    # New working link: https://www.amazon.de/dp/3548375909?tag=schatzsuch0c4-21
    
    new_content = content.replace("3548359544", "3548375909")
    
    if content == new_content:
        print("No changes needed or link not found.")
        return

    payload = {"content": new_content}
    r = requests.post(f"{BASE}/pages/{page_id}", headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print("SUCCESS: Amazon link for Kostolany fixed.")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    fix_amazon_links()
