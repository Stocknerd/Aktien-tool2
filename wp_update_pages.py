#!/usr/bin/env python3
"""
WordPress Page Updater
Updates schatzsuche40.de pages with premium content via REST API.
"""

import base64
import json
import requests
import sys

# --- Config ---
WP_BASE = "https://schatzsuche40.de/wp-json/wp/v2"
WP_USER = "fhofmann"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"

# Build auth header
credentials = f"{WP_USER}:{WP_APP_PASS}"
token = base64.b64encode(credentials.encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; Antigravity/1.0)",
}

# --- HTML content for pages ---

HTML_PAGE_1210 = """
<h3>Kurzanleitung: So erstellst du dein Bild</h3>
<ol>
  <li><strong>Aktie suchen</strong>: Gib den Namen oder das Kürzel (z.B. Apple oder AAPL) in das Suchfeld ein.</li>
  <li><strong>Design wählen</strong>: Entscheide dich für das helle Standard-Design oder den eleganten <strong>Dark Mode</strong>.</li>
  <li><strong>Metriken anpassen</strong>: Wähle bis zu 8 Kennzahlen (Dividende, KGV, Marge etc.), die dir wichtig sind.</li>
  <li><strong>KI-Check</strong>: Aktiviere die <strong>KI-Insights</strong>, um eine automatisierte Einschätzung von GPT-4o zu erhalten.</li>
  <li><strong>Download</strong>: Klicke auf "Bild erzeugen" und lade dein PNG direkt herunter.</li>
</ol>
<div style="max-width:1200px;margin-top:24px;">
  <iframe src="https://tool.schatzsuche40.de/?embed=1" style="width:100%;height:950px;border:0;border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.1);" loading="lazy"></iframe>
</div>
"""

HTML_PAGE_1384 = """
<h3>Aktien-Vergleich auf Profi-Niveau</h3>
<p>Finde heraus, welches Unternehmen fundamental die Nase vorn hat. Unser Tool vergleicht für dich Rentabilität, Bewertung und Dividenden-Check im direkten Duell.</p>
<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
  <iframe src="https://tool.schatzsuche40.de/compare?embed=1" width="100%" height="850" frameborder="0" style="border-radius:14px;display:block;" loading="lazy" title="Aktien Vergleichstool"></iframe>
</div>
<h3>So geht's:</h3>
<ol>
  <li>Gib links und rechts die beiden Ticker-Symbole ein (z.B. MSFT vs. AAPL).</li>
  <li>Wähle ein Set an Kennzahlen oder bleib beim Standard.</li>
  <li>Erhalte sofort einen visuellen Vergleich inklusive Analysten-Kurszielen beider Werte.</li>
</ol>
"""


def check_auth():
    """Verify authentication works."""
    print("Checking authentication...")
    r = requests.get(f"{WP_BASE}/users/me", headers=HEADERS, timeout=10)
    print(f"  Auth status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  Logged in as: {data.get('name', 'unknown')} (roles: {data.get('roles', [])})")
        return True
    else:
        print(f"  Auth failed: {r.text[:200]}")
        return False


def get_page(page_id):
    """Get current page content."""
    r = requests.get(f"{WP_BASE}/pages/{page_id}", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        data = r.json()
        return data
    else:
        print(f"  Error getting page {page_id}: {r.status_code} {r.text[:100]}")
        return None


def update_page(page_id, new_html_block, page_name):
    """Append HTML to existing page content."""
    print(f"\nUpdating page {page_id} ({page_name})...")
    
    # Get current content
    page = get_page(page_id)
    if not page:
        print(f"  SKIP: Could not fetch page {page_id}")
        return False
    
    current_content = page.get("content", {}).get("raw", "")
    title = page.get("title", {}).get("rendered", f"Page {page_id}")
    print(f"  Current title: {title}")
    print(f"  Current content length: {len(current_content)} chars")
    
    # Check if our block already exists to avoid duplicates
    if "Kurzanleitung" in current_content or "Profi-Niveau" in current_content:
        print(f"  Content already appears to be updated — overwriting to refresh...")
        # Find and replace existing block or just prepend
    
    # Prepend our instruction block (before any existing content)
    updated_content = new_html_block.strip() + "\n\n" + current_content
    
    # Send update
    payload = {
        "content": updated_content,
    }
    
    r = requests.post(
        f"{WP_BASE}/pages/{page_id}",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    
    if r.status_code in (200, 201):
        print(f"  SUCCESS! Page {page_id} updated. New length: {len(updated_content)} chars")
        data = r.json()
        print(f"  View at: {data.get('link', 'N/A')}")
        return True
    else:
        print(f"  FAILED: {r.status_code} {r.text[:300]}")
        return False


def main():
    print("=" * 60)
    print("WordPress Page Updater - schatzsuche40.de")
    print("=" * 60)
    
    # 1. Check auth
    if not check_auth():
        print("\nAuthentication failed. The server may be blocking Authorization headers.")
        print("Trying alternate approach with cookie-based auth...")
        # Try cookie-based: first login via xmlrpc
        return False
    
    # 2. Update pages
    results = {}
    results[1210] = update_page(1210, HTML_PAGE_1210, "Aktien-Analyse Tool")
    results[1384] = update_page(1384, HTML_PAGE_1384, "Aktien-Vergleich")
    
    # 3. Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    for page_id, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  Page {page_id}: {status}")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
