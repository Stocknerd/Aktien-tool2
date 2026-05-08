import requests

BASE = "https://schatzsuche40.de/wp-json/wp/v2"

def find_homepage():
    r = requests.get(f"{BASE}/pages?per_page=50")
    if r.status_code == 200:
        pages = r.json()
        for p in pages:
            print(f"ID: {p['id']}, Link: {p['link']}, Title: {p['title']['rendered']}")
    else:
        print(f"Error: {r.status_code}")

if __name__ == "__main__":
    find_homepage()
