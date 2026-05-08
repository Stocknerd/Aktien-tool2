import requests
import base64
import os

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

FEATURED_IMG_PATH = r"C:\Users\fhofmann\.gemini\antigravity\brain\1b0a5e00-fda2-4600-a917-8361004f0c35\p2p_blog_featured_image_1778214047837.png"

ARTICLE_TITLE = "Meine P2P-Lending Strategie 2026: Passives Einkommen mit System"
ARTICLE_CONTENT = """
<!-- wp:paragraph -->
<p>Geld sollte niemals schlafen. Während die meisten Anleger ihr Kapital ausschließlich in Aktien oder ETFs stecken, nutzen Profis oft eine "Cashflow-Komponente", um monatlich frisches Kapital zu generieren. Für mich sind das <strong>P2P-Kredite</strong>.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Warum P2P-Lending im Jahr 2026?</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Im aktuellen Marktumfeld sind Zinsen wieder ein Thema. Doch während Banken oft nur mickrige Prozente auf das Tagesgeld zahlen, bieten P2P-Plattformen zweistellige Renditen. Der Grund ist simpel: Du agierst als Bank und leihst Privatpersonen oder Unternehmen direkt Geld. Das Risiko ist höher, aber die Belohnung in Form von monatlichen Zinsgutschriften ist unschlagbar.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Meine "Big 4" Plattformen</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Ich habe in den letzten Jahren viel getestet und bin bei vier Plattformen hängengeblieben, die für mich die beste Mischung aus Stabilität, Rendite und Handhabung bieten:</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul>
    <li><strong>Mintos:</strong> Mein "Anker". Hier investiere ich in regulierte Notes. Die Diversifikation über verschiedene Länder und Kreditarten ist hier am höchsten.</li>
    <li><strong>Bondora Go & Grow:</strong> Meine Liquiditätsreserve. Zwar ist die Rendite etwas geringer als bei Einzelkrediten, aber die tägliche Verfügbarkeit macht es zum perfekten Parkplatz für Cash.</li>
    <li><strong>Robocash:</strong> Hier herrscht der pure Autopilot. Einmal eingestellt, laufen die Zinsen fast ohne mein Zutun ein.</li>
    <li><strong>Twino:</strong> Ein Veteran am Markt, der mich besonders durch seine Beständigkeit in Krisenzeiten überzeugt hat.</li>
</ul>
<!-- /wp:list -->

<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons">
    <div class="wp-block-button">
        <a class="wp-block-button__link wp-element-button" href="https://schatzsuche40.de/die-besten-plattformen/" style="border-radius:10px; background-color:#10b981; font-weight:bold;">Zum großen P2P-Plattformvergleich</a>
    </div>
</div>
<!-- /wp:buttons -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Risikomanagement: Die 10% Regel</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Eines muss klar sein: P2P-Kredite sind keine sichere Anlage. Es gibt kein Einlagensicherungssystem wie bei der Bank. Mein persönliches Sicherheitsnetz besteht aus zwei Säulen:</p>
<!-- /wp:paragraph -->

<!-- wp:list {"ordered":true} -->
<ol>
    <li><strong>Kapitalanteil:</strong> Maximal 10-15% meines Gesamtportfolios fließen in P2P.</li>
    <li><strong>Plattform-Split:</strong> Ich verteile mein Geld immer auf mindestens 4 verschiedene Anbieter, um das Plattform-Risiko zu minimieren.</li>
</ol>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Fazit: Lohnt sich der Einstieg?</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Für Anleger, die einen monatlichen Cashflow-Boost suchen, ist P2P-Lending auch 2026 unverzichtbar. Es macht einfach Spaß zu sehen, wie jeden Morgen die Zinsen auf dem Dashboard erscheinen. Wenn du klein anfängst und dich diszipliniert an deine Strategie hältst, ist es eine der besten Ergänzungen für jedes Depot.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><em>Disclaimer: Dies ist keine Anlageberatung. Investitionen in P2P-Kredite bergen das Risiko eines Totalverlustes.</em></p>
<!-- /wp:paragraph -->
"""

def publish_article():
    # 1. Upload featured image
    media_id = None
    print("Uploading featured image...")
    with open(FEATURED_IMG_PATH, 'rb') as f:
        media_headers = HEADERS.copy()
        media_headers["Content-Disposition"] = "attachment; filename=p2p_featured_2026.png"
        media_headers["Content-Type"] = "image/png"
        res = requests.post(f"{BASE}/media", headers=media_headers, data=f)
        if res.status_code in (200, 201):
            media_id = res.json().get('id')
            print(f"Image uploaded, ID: {media_id}")
    
    # 2. Create post
    print("Publishing blog post...")
    payload = {
        "title": ARTICLE_TITLE,
        "content": ARTICLE_CONTENT,
        "status": "publish", # Or "draft" if you want to check it first
        "featured_media": media_id,
        "categories": [1] # Standard category, adjust if needed
    }
    
    r = requests.post(f"{BASE}/posts", headers={"Authorization": f"Basic {creds}", "Content-Type": "application/json"}, json=payload)
    if r.status_code in (200, 201):
        print(f"SUCCESS! Article published: {r.json().get('link')}")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    publish_article()
