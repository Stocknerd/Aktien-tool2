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

def cleanup_and_update():
    # Delete the duplicate
    requests.delete(f"{BASE}/pages/1878", headers=HEADERS)
    print("Deleted duplicate page 1878")
    
    # Content from wp_create_buchtipps.py
    with open("wp_create_buchtipps.py", "r") as f:
        content = f.read()
        import re
        html_match = re.search(r'BUCHTIPPS_HTML = """(.*?)"""', content, re.DOTALL)
        if html_match:
            html = html_match.group(1)
            requests.post(f"{BASE}/pages/1872", headers=HEADERS, json={"content": html})
            print("Updated page 1872 with new Amazon links")

if __name__ == "__main__":
    cleanup_and_update()
