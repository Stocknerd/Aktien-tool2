import requests
import json
import base64

SITE_URL = "https://schatzsuche40.de"
USER = "schatzsuche40"
PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"

def get_auth_header():
    credentials = f"{USER}:{PASS}"
    token = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

# The premium updated HTML for "Wo Aktien kaufen?"
NEW_HTML = """<!-- wp:paragraph -->
<p>Um Aktien, ETFs oder Anleihen kaufen zu können, benötigt man ein Depot und einen Broker. Der Broker ist die Bank, bei der ihr euer Depot eröffnet (oder ein Kooperationspartner).</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Ich habe zur Zeit drei verschiedene Wertpapierdepots bei drei verschiedenen Banken: mein Hauptdepot bei <strong>Scalable Capital</strong> (für unschlagbar günstige Orders und Sparpläne), mein Dividenden-Depot bei der <strong>Consorsbank</strong> (ideal für die automatische Dividenden-Wiederanlage) und ein Zukunftsdepot bei <strong>Traders Place</strong>. Die Gebühren und Leistungen bei diesen Anbietern sind hervorragend und bieten ein erstklassiges Preis-Leistungs-Verhältnis.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Es gibt aber noch einige weitere Möglichkeiten. Man könnte auch über seine Hausbank (Filialbank) Aktien kaufen. Hier sind die Gebühren jedoch oft so hoch, dass sämtliche Gewinne einfach aufgefressen würden. Außerdem sind auch nur selten Sparpläne möglich. Hierzu würde ich pauschal nicht raten.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Man kann aber mit seinem Depot zu einem sogenannten Discountbroker oder Neobroker gehen. Das sind modernere Anbieter, sogenannte <a href="https://de.wikipedia.org/wiki/Finanztechnologie" target="_blank" rel="noreferrer noopener">Fintechs</a>, die mit Kampfpreisen auf den Markt kommen. Oft sind Sparpläne und Depotführung völlig kostenlos. Die Ordergebühren für Einzelkäufe sind ebenfalls extrem günstig. Beispiele hierfür sind <a href="https://www.financeads.net/tc.php?t=47128C142835927T" target="_blank" rel="noopener">Scalable Capital</a>* und Trade Republic. Letzterer bietet auch einen guten Sparplan-Standard, während Scalable zusätzlich überragende Zinsen auf Guthaben bietet.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>In der folgenden Tabelle habe ich mal die wichtigsten Daten der Anbieter aufgelistet:</p>
<!-- /wp:paragraph -->

<!-- wp:shortcode -->
[table id=1 /]
<!-- /wp:shortcode -->

<!-- wp:paragraph -->
<p>Bei den moderneren Discount-Brokern fallen sowohl sehr günstige Preise und Gebühren auf, als auch eine riesige Auswahl an Aktien und ETFs.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Ich habe mich entschieden, meine Käufe vor allem bei modernen Online-Brokern und spezialisierten Direktbanken zu tätigen. Der Grund ist eine Kombination aus modernster Technik, unschlagbaren Konditionen und gutem Service. Wenn etwas mal nicht funktioniert, bekommt man bei Partnern wie der Consorsbank immer direkt kompetente Hilfe. Aber auch die neuen Neobroker haben sich extrem weiterentwickelt und bieten mittlerweile einen hervorragenden Standard.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":4} -->
<h4>Fazit und Empfehlung</h4>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Meine Empfehlung, wenn ihr starten wollt, ist <strong>Scalable Capital</strong> oder die <strong>Consorsbank</strong>.</p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<div class="broker-recommendation-box" style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 30px; margin: 30px 0; font-family: 'Inter', sans-serif;">
  <h4 style="color: #10b981; font-weight: 800; font-size: 1.3rem; margin-top: 0; margin-bottom: 15px;">🌟 Meine aktuelle Top-Empfehlung</h4>
  <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; margin-bottom: 25px;">
    Für Einsteiger und fortgeschrittene Anleger empfehle ich aktuell <strong>Scalable Capital</strong> als modernsten und günstigsten Broker für Aktien und ETFs, sowie die <strong>Consorsbank</strong> für Anleger, die großen Wert auf exzellenten Service und automatische Dividenden-Wiederanlage legen.
  </p>
  <div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <a href="https://www.financeads.net/tc.php?t=47128C142835927T" target="_blank" style="flex: 1; min-width: 250px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff !important; text-align: center; padding: 15px; border-radius: 12px; font-weight: 800; text-decoration: none !important; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: transform 0.2s; display: inline-block;">
      🚀 Scalable Capital Depot eröffnen*
    </a>
    <a href="https://www.financeads.net/tc.php?t=47128C15212339T" target="_blank" style="flex: 1; min-width: 250px; background: rgba(255, 255, 255, 0.05); color: #fff !important; text-align: center; padding: 15px; border-radius: 12px; font-weight: 800; text-decoration: none !important; border: 1px solid rgba(255, 255, 255, 0.15); transition: transform 0.2s; display: inline-block;">
      🎯 Consorsbank Depot eröffnen*
    </a>
  </div>
</div>
<!-- /wp:html -->

<!-- wp:paragraph -->
<p>Hier gibt es eine riesige Auswahl an kostenlosen Sparplänen zu extrem günstigen Gebühren. Die Bedienung der Apps und Web-Oberflächen ist einfach und intuitiv. Zusätzlich gibt es viele weitere tolle Services wie zum Beispiel ETF-Finder oder automatische Wiederanlagen für Zinseszins-Optimierung. Beide Partner bieten hervorragendes, regulatorisch geschütztes Banking in Deutschland.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Eine Übersicht über meine Depots findet ihr auf dieser <a href="https://schatzsuche40.de/meine-depots/" target="_blank" rel="noreferrer noopener">Seite</a>.</p>
<!-- /wp:paragraph -->"""

def update_page_69():
    url = f"{SITE_URL}/wp-json/wp/v2/pages/69"
    headers = get_auth_header()
    payload = {
        "content": NEW_HTML
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        print("SUCCESS! Page 69 (Wo Aktien kaufen) updated successfully.")
        print(f"View page at: {response.json().get('link')}")
    else:
        print(f"FAILED: {response.status_code} - {response.text}")

if __name__ == "__main__":
    update_page_69()
