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

CALENDAR_HTML = """<!-- wp:html -->
<div id="calendar-wrapper" style="width: 100%; min-height: 800px;">
    <iframe id="div-calendar-iframe" 
            src="https://compare.schatzsuche40.de/dividenden-kalender?embed=1" 
            style="width: 100%; border: none; overflow: hidden;" 
            scrolling="no">
    </iframe>
</div>

<script>
window.addEventListener('message', function(e) {
    if (e.data.type === 'setHeight') {
        document.getElementById('div-calendar-iframe').style.height = e.data.height + 'px';
    }
}, false);
</script>
<!-- /wp:html -->"""

def create_page():
    print("Creating/Updating Dividend Calendar Page...")
    # Check if page exists
    r = requests.get(f"{BASE}/pages?search=Dividenden-Kalender", headers=HEADERS)
    pages = r.json()
    
    payload = {
        "title": "Dividenden-Kalender 2026",
        "content": CALENDAR_HTML,
        "status": "publish",
        "slug": "dividenden-kalender"
    }
    
    if pages:
        page_id = pages[0]['id']
        print(f"Updating existing page ID: {page_id}")
        r = requests.post(f"{BASE}/pages/{page_id}", headers=HEADERS, json=payload)
    else:
        print("Creating new page...")
        r = requests.post(f"{BASE}/pages", headers=HEADERS, json=payload)
    
    if r.status_code in (200, 201):
        print(f"SUCCESS! Calendar live at: {r.json().get('link')}")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    create_page()
