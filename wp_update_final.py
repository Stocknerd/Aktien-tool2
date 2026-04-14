#!/usr/bin/env python3
"""Update WordPress pages 1210 and 1384 with premium content."""
import requests
import base64
import json

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
}

HTML_1210 = """<!-- wp:html -->
<h3>Kurzanleitung: So erstellst du dein Bild</h3>
<ol>
  <li><strong>Aktie suchen</strong>: Gib den Namen oder das Kuerzel (z.B. Apple oder AAPL) in das Suchfeld ein.</li>
  <li><strong>Design waehlen</strong>: Entscheide dich fuer das helle Standard-Design oder den eleganten <strong>Dark Mode</strong>.</li>
  <li><strong>Metriken anpassen</strong>: Waehle bis zu 8 Kennzahlen (Dividende, KGV, Marge etc.), die dir wichtig sind.</li>
  <li><strong>KI-Check</strong>: Aktiviere die <strong>KI-Insights</strong>, um eine automatisierte Einschaetzung von GPT-4o zu erhalten.</li>
  <li><strong>Download</strong>: Klicke auf &quot;Bild erzeugen&quot; und lade dein PNG direkt herunter.</li>
</ol>
<div style="max-width:1200px;margin-top:24px;">
  <iframe src="https://tool.schatzsuche40.de/?embed=1" style="width:100%;height:950px;border:0;border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.1);" loading="lazy"></iframe>
</div>
<!-- /wp:html -->"""

HTML_1384 = """<!-- wp:html -->
<h3>Aktien-Vergleich auf Profi-Niveau</h3>
<p>Finde heraus, welches Unternehmen fundamental die Nase vorn hat. Unser Tool vergleicht fuer dich Rentabilitaet, Bewertung und Dividenden-Check im direkten Duell.</p>
<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
  <iframe src="https://tool.schatzsuche40.de/compare?embed=1" width="100%" height="850" frameborder="0" style="border-radius:14px;display:block;" loading="lazy" title="Aktien Vergleichstool"></iframe>
</div>
<h3>So geht&#8217;s:</h3>
<ol>
  <li>Gib links und rechts die beiden Ticker-Symbole ein (z.B. MSFT vs. AAPL).</li>
  <li>Waehle ein Set an Kennzahlen oder bleib beim Standard.</li>
  <li>Erhalte sofort einen visuellen Vergleich inklusive Analysten-Kurszielen beider Werte.</li>
</ol>
<!-- /wp:html -->"""


def verify_auth():
    r = requests.get(f"{BASE}/users/me", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        d = r.json()
        print(f"Authenticated as: {d.get('name')} | Roles: {d.get('roles')}")
        return True
    else:
        print(f"Auth check failed: {r.status_code} {r.text[:200]}")
        return False


def get_page(page_id):
    r = requests.get(f"{BASE}/pages/{page_id}?context=edit", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        return r.json()
    print(f"  Could not get page {page_id}: {r.status_code}")
    return None


def update_page(page_id, new_content_block, name):
    print(f"\nUpdating page {page_id} ({name})...")
    page = get_page(page_id)
    if not page:
        return False

    current = page.get("content", {}).get("raw", "")
    print(f"  Current content length: {len(current)} chars")

    # Replace or prepend - avoid duplication
    markers = ["Kurzanleitung", "Profi-Niveau", "wp:html"]
    already_updated = any(m in current for m in markers)
    if already_updated:
        print("  Previous content block found - replacing with fresh version")
        new_content = new_content_block
    else:
        new_content = new_content_block + "\n\n" + current

    payload = {"content": new_content}
    r = requests.post(f"{BASE}/pages/{page_id}", headers=HEADERS, json=payload, timeout=20)
    if r.status_code in (200, 201):
        d = r.json()
        print(f"  SUCCESS: {d.get('link', 'N/A')}")
        return True
    else:
        print(f"  FAILED: {r.status_code} {r.text[:400]}")
        return False


print("=" * 60)
print("WordPress Page Updater")
print("=" * 60)

if verify_auth():
    ok1 = update_page(1210, HTML_1210, "Aktien-Analyse Tool")
    ok2 = update_page(1384, HTML_1384, "Aktien-Vergleich")
    print("\n" + "=" * 60)
    print(f"Page 1210: {'SUCCESS' if ok1 else 'FAILED'}")
    print(f"Page 1384: {'SUCCESS' if ok2 else 'FAILED'}")
else:
    print("Authentication failed - cannot proceed.")
