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

def update_page(page_id, new_content):
    url = f"{SITE_URL}/wp-json/wp/v2/pages/{page_id}"
    headers = get_auth_header()
    data = {"content": new_content}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"Page {page_id} updated successfully.")
    else:
        print(f"Error updating page {page_id}: {response.status_code} - {response.text}")

# 1. Aktien-Analyse Tool (ID 396)
analyse_content = """
<h3>Kurzanleitung: So erstellst du dein Bild</h3>
<ol>
  <li><strong>Aktie suchen</strong>: Gib den Namen oder das Krzel (z.B. Apple oder AAPL) in das Suchfeld ein.</li>
  <li><strong>Design whlen</strong>: Entscheide dich fr das helle Standard-Design oder den eleganten <strong>Dark Mode</strong>.</li>
  <li><strong>Metriken anpassen</strong>: Whle bis zu 8 Kennzahlen (Dividende, KGV, Marge etc.), die dir wichtig sind.</li>
  <li><strong>KI-Check</strong>: Aktiviere die <strong>KI-Insights</strong>, um eine automatisierte Einschtzung von GPT-4o zu erhalten.</li>
  <li><strong>Download</strong>: Klicke auf "Bild erzeugen" und lade dein PNG direkt herunter.</li>
</ol>
<div style="aspect-ratio:16/10;max-width:1200px;margin-top:24px;">
  <iframe src="https://tool.schatzsuche40.de/?embed=1" style="width:100%;height:950px;border:0;border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.1);" loading="lazy"></iframe>
</div>
"""

# 2. Aktien-Vergleich (ID 1661)
vergleich_content = """
<h3>Aktien-Vergleich auf Profi-Niveau</h3>
<p>Finde heraus, welches Unternehmen fundamental die Nase vorn hat. Unser Tool vergleicht fr dich Rentabilitt, Bewertung und Dividenden-Check im direkten Duell.</p>
<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
  <iframe src="https://tool.schatzsuche40.de/compare?embed=1" width="100%" height="850" frameborder="0" style="border-radius:14px;display:block;" loading="lazy" title="Aktien Vergleichstool"></iframe>
</div>
<h3>So geht's:</h3>
<ol>
  <li>Gib links und rechts die beiden Ticker-Symbole ein (z.B. MSFT vs. AAPL).</li>
  <li>Whle ein Set an Kennzahlen oder bleib beim Standard.</li>
  <li>Erhalte sofort einen visuellen Vergleich inklusive Analysten-Kurszielen beider Werte.</li>
</ol>
"""

if __name__ == "__main__":
    update_page(396, analyse_content)
    update_page(1661, vergleich_content)
