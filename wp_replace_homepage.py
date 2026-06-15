#!/usr/bin/env python3
"""Replace entire homepage (page 191) with premium design only."""
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

# Full replacement - premium dark design only
NEW_CONTENT = """<!-- wp:html -->
<style>
.s40-hero{background:linear-gradient(135deg,#091719 0%,#0B1E21 50%,#14353a 100%);border-radius:20px;padding:60px 40px;text-align:center;margin-bottom:40px;position:relative;overflow:hidden}
.s40-hero::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(ellipse at center,rgba(201,162,39,0.15) 0%,transparent 60%);pointer-events:none}
.s40-hero h2{color:#F7F7F7!important;font-size:2.2rem;font-weight:800;margin-bottom:16px;letter-spacing:-.5px}
.s40-hero p{color:#A0B0B2;font-size:1.1rem;max-width:600px;margin:0 auto 32px;line-height:1.7}
.s40-badge{display:inline-block;background:rgba(201,162,39,0.15);color:#C9A227;border:1px solid rgba(201,162,39,0.35);border-radius:50px;padding:6px 18px;font-size:.85rem;font-weight:600;margin-bottom:24px;letter-spacing:.5px}
.s40-tools-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;margin:40px 0}
.s40-tool-card{background:rgba(20, 44, 48, 0.45);border:1px solid rgba(201, 162, 39, 0.12);border-radius:16px;padding:32px 28px;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease;position:relative;overflow:hidden;text-decoration:none!important;display:block}
.s40-tool-card:hover{transform:translateY(-4px);box-shadow:0 20px 40px rgba(0,0,0,.3);border-color:rgba(201, 162, 39, 0.5);text-decoration:none!important}
.s40-tool-icon{font-size:2.5rem;margin-bottom:16px;display:block}
.s40-tool-title{color:#F7F7F7!important;font-size:1.25rem;font-weight:700;margin:0 0 10px}
.s40-tool-desc{color:#A0B0B2;font-size:.95rem;line-height:1.6;margin:0 0 20px}
.s40-tool-tag{display:inline-block;background:rgba(26,83,92,0.45);color:#A0B0B2;border-radius:6px;padding:3px 10px;font-size:.78rem;font-weight:600;margin-right:6px;margin-bottom:4px}
.s40-tool-cta{display:inline-block;background:linear-gradient(90deg,#C9A227,#E5BA3B);color:#0B1E21!important;padding:10px 22px;border-radius:8px;font-weight:700;font-size:.9rem;margin-top:16px;text-decoration:none!important;transition:opacity .2s}
.s40-tool-cta:hover{opacity:.9;color:#0B1E21!important;text-decoration:none!important}
.s40-coming-soon .s40-tool-title,.s40-coming-soon .s40-tool-desc{opacity:.6}
.s40-coming-soon .s40-tool-tag{background:rgba(148,163,184,.1);color:#64748b}
.s40-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:40px 0}
.s40-stat{background:rgba(20, 44, 48, 0.2);border:1px solid rgba(201, 162, 39, 0.08);border-radius:12px;padding:24px 16px;text-align:center}
.s40-stat-number{display:block;font-size:2rem;font-weight:800;color:#C9A227;margin-bottom:4px}
.s40-stat-label{font-size:.85rem;color:#A0B0B2}
.s40-wrapper{background:#0B1E21;border-radius:24px;padding:48px 40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
@media(max-width:640px){.s40-hero{padding:40px 20px}.s40-hero h2{font-size:1.6rem}.s40-stats{grid-template-columns:1fr}.s40-wrapper{padding:28px 20px}}
</style>

<div class="s40-wrapper">
  <div class="s40-hero">
    <span class="s40-badge">&#127881; 100% Kostenlos &middot; Keine Anmeldung</span>
    <h2>Professionelle Aktienanalyse &mdash;<br>einfach &amp; schnell.</h2>
    <p>Deine Toolbox f&uuml;r smarte Investitionsentscheidungen. Erstelle Infografiken, vergleiche Aktien und behalte dein Portfolio im Blick.</p>
  </div>

  <div class="s40-stats">
    <div class="s40-stat">
      <span class="s40-stat-number">4.000+</span>
      <span class="s40-stat-label">Aktien weltweit</span>
    </div>
    <div class="s40-stat">
      <span class="s40-stat-number">30+</span>
      <span class="s40-stat-label">Kennzahlen pro Aktie</span>
    </div>
    <div class="s40-stat">
      <span class="s40-stat-number">KI</span>
      <span class="s40-stat-label">GPT-4o Analyse</span>
    </div>
  </div>

  <div class="s40-tools-grid">
    <a href="https://schatzsuche40.de/aktien-tool/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128202;</span>
      <div class="s40-tool-title">Aktien-Bild Generator</div>
      <p class="s40-tool-desc">Erstelle in Sekunden professionelle Infografiken mit &uuml;ber 30 Kennzahlen &ndash; inklusive KI-Bewertung von GPT-4o. Perfekt f&uuml;r Instagram &amp; LinkedIn.</p>
      <span class="s40-tool-tag">&#127381; KI-Analyse</span>
      <span class="s40-tool-tag">&#128444; PNG Export</span>
      <span class="s40-tool-tag">Dark Mode</span>
      <br>
      <span class="s40-tool-cta">Jetzt ausprobieren &rarr;</span>
    </a>

    <a href="https://schatzsuche40.de/vergleich/" class="s40-tool-card">
      <span class="s40-tool-icon">&#9878;&#65039;</span>
      <div class="s40-tool-title">Aktien-Vergleich</div>
      <p class="s40-tool-desc">Vergleiche zwei Unternehmen direkt &mdash; Rentabilit&auml;t, Bewertung, Dividende. Finde heraus, welche Aktie fundamental besser aufgestellt ist.</p>
      <span class="s40-tool-tag">Duell-Vergleich</span>
      <span class="s40-tool-tag">&#128200; Analysten-Ziele</span>
      <span class="s40-tool-tag">Dividenden-Check</span>
      <br>
      <span class="s40-tool-cta">Aktien vergleichen &rarr;</span>
    </a>

    <a href="https://schatzsuche40.de/screener/" class="s40-tool-card">
      <span class="s40-tool-icon">&#127919;</span>
      <div class="s40-tool-title">Aktien-Screener</div>
      <p class="s40-tool-desc">Filtere Tausende von Aktien nach KGV, Dividendenrendite, Wachstum und Margen. Mit unserem High-Speed Multi-Faktor Filter findest du die besten Perlen.</p>
      <span class="s40-tool-tag">High-Speed Filter</span>
      <span class="s40-tool-tag">&#128200; Dividendenrendite</span>
      <span class="s40-tool-tag">Wachstum</span>
      <br>
      <span class="s40-tool-cta">Werte filtern &rarr;</span>
    </a>

    <a href="https://schatzsuche40.de/dividend-rechner/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128181;</span>
      <div class="s40-tool-title">Dividenden-Rechner</div>
      <p class="s40-tool-desc">Behalte deine passiven Einkommensstr&ouml;me im Blick. Berechne deine Dividenden-Zahlungen und analysiere deinen monatlichen Cashflow in Sekunden.</p>
      <span class="s40-tool-tag">&#128200; Cashflow-Check</span>
      <span class="s40-tool-tag">Monats-Vorschau</span>
      <br>
      <span class="s40-tool-cta">Jetzt berechnen &rarr;</span>
    </a>

    <a href="https://schatzsuche40.de/dividenden-kalender/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128197;</span>
      <div class="s40-tool-title">Dividenden-Kalender</div>
      <p class="s40-tool-desc">Verpasse nie wieder einen Ex-Tag oder Zahltag. Unser interaktiver Kalender listet alle Aussch&uuml;ttungstermine f&uuml;r &uuml;ber 4.000 Aktien weltweit.</p>
      <span class="s40-tool-tag">Ex-Termine</span>
      <span class="s40-tool-tag">Zahltage</span>
      <br>
      <span class="s40-tool-cta">Kalender &ouml;ffnen &rarr;</span>
    </a>

    <a href="https://schatzsuche40.de/die-besten-plattformen/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128184;</span>
      <div class="s40-tool-title">P2P-Plattformen</div>
      <p class="s40-tool-desc">Passives Einkommen durch Privatkredite. Wir vergleichen die besten Plattformen wie Mintos und Bondora f&uuml;r dein Portfolio.</p>
      <span class="s40-tool-tag">&#128200; 10%+ Rendite</span>
      <span class="s40-tool-tag">Platform-Check</span>
      <br>
      <span class="s40-tool-cta">Plattformen pr&uuml;fen &rarr;</span>
    </a>
  </div>
</div>
<!-- /wp:html -->"""

r = requests.get(f"{BASE}/pages/191?context=edit", headers=HEADERS, timeout=10)
print(f"Fetching page 191: {r.status_code}")

payload = {"content": NEW_CONTENT}
r2 = requests.post(f"{BASE}/pages/191", headers=HEADERS, json=payload, timeout=20)
print(f"Update result: {r2.status_code}")
if r2.status_code in (200, 201):
    print(f"SUCCESS! View at: {r2.json().get('link')}")
else:
    print(r2.text[:300])
