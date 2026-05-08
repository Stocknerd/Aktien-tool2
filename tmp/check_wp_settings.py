import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

def check_settings():
    r = requests.get(f"https://schatzsuche40.de/wp-json/wp/v2/settings", headers=HEADERS)
    if r.status_code == 200:
        settings = r.json()
        print(f"Site Email: {settings.get('email')}")
        print(f"Site Title: {settings.get('title')}")
    else:
        print(f"Error: {r.status_code} {r.text}")

if __name__ == "__main__":
    check_settings()
