#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update schatzsuche40.de homepage (ID 1045 and 191) with a premium design
including dynamic latest Depot-Update stats and 6 tool cards.
"""
import requests
import base64
import os
import pandas as pd

WP_USER = "schatzsuche40"
WP_APP_PASS = "R33G PRPb mqee hBGc pvKJ 51iz"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
}

def get_latest_metrics():
    metrics = {
        "value": "129.565 €",
        "dividends": "154 €",
        "perf": "+0,43%"
    }
    csv_path = 'C:/Users/fhofmann/Dropbox/portfolio/Wertpapier-Performance_(Standard).csv'
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, sep=';')
            sum_row = df[df['Name'] == 'Summe']
            if not sum_row.empty:
                # Marktwert
                raw_val = str(sum_row.iloc[0]['Marktwert']).split(',')[0].replace('.', '')
                val_formatted = f"{int(raw_val):,}".replace(',', '.') + " €"
                metrics["value"] = val_formatted
                
                # Dividends
                raw_div = str(sum_row.iloc[0]['∑Div']).split(',')[0].replace('.', '')
                div_formatted = f"{int(raw_div):,}".replace(',', '.') + " €"
                metrics["dividends"] = div_formatted
        except Exception as e:
            print(f"Error parsing Dropbox CSV: {e}")
    return metrics

def build_homepage_html():
    stats = get_latest_metrics()
    
    html = f"""<!-- wp:html -->
<style>
/* WordPress Header Fixes */
.entry-content {{ margin-top: 80px !important; }}
@media (max-width: 768px) {{ .entry-content {{ margin-top: 100px !important; }} }}
header, .site-header, #masthead, .navigation-bar, .main-navigation, .sticky-header {{
    background-color: #0B1E21 !important;
    opacity: 1 !important;
    z-index: 9999 !important;
}}
.s40-hero {{
  background: linear-gradient(135deg, #091719 0%, #0B1E21 50%, #14353a 100%);
  border-radius: 20px;
  padding: 60px 40px;
  text-align: center;
  margin-bottom: 40px;
  position: relative;
  overflow: hidden;
}}
.s40-hero::before {{
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(ellipse at center, rgba(201, 162, 39, 0.15) 0%, transparent 60%);
  pointer-events: none;
}}
.s40-hero h2 {{
  color: #F7F7F7 !important;
  font-size: 2.2rem;
  font-weight: 800;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}}
.s40-hero p {{
  color: #A0B0B2;
  font-size: 1.1rem;
  max-width: 600px;
  margin: 0 auto 32px;
  line-height: 1.7;
}}
.s40-badge {{
  display: inline-block;
  background: rgba(201, 162, 39, 0.15);
  color: #C9A227;
  border: 1px solid rgba(201, 162, 39, 0.35);
  border-radius: 50px;
  padding: 6px 18px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 24px;
  letter-spacing: 0.5px;
}}
.s40-tools-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin: 40px 0;
}}
.s40-tool-card {{
  background: rgba(20, 44, 48, 0.45);
  border: 1px solid rgba(201, 162, 39, 0.12);
  border-radius: 16px;
  padding: 32px 28px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  position: relative;
  overflow: hidden;
  text-decoration: none !important;
  display: block;
}}
.s40-tool-card:hover {{
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.3);
  border-color: rgba(201, 162, 39, 0.5);
  text-decoration: none !important;
}}
.s40-tool-icon {{
  font-size: 2.5rem;
  margin-bottom: 16px;
  display: block;
}}
.s40-tool-title {{
  color: #F7F7F7 !important;
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 10px;
}}
.s40-tool-desc {{
  color: #A0B0B2;
  font-size: 0.95rem;
  line-height: 1.6;
  margin: 0 0 20px;
}}
.s40-tool-tag {{
  display: inline-block;
  background: rgba(26, 83, 92, 0.45);
  color: #A0B0B2;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.78rem;
  font-weight: 600;
  margin-right: 6px;
  margin-bottom: 4px;
}}
.s40-tool-cta {{
  display: inline-block;
  background: linear-gradient(90deg, #C9A227, #E5BA3B);
  color: #0B1E21 !important;
  padding: 10px 22px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.9rem;
  margin-top: 16px;
  text-decoration: none !important;
  transition: opacity 0.2s;
}}
.s40-tool-cta:hover {{
  opacity: 0.9;
  color: #0B1E21 !important;
  text-decoration: none !important;
}}
.s40-stats {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 40px 0;
}}
.s40-stat {{
  background: rgba(20, 44, 48, 0.2);
  border: 1px solid rgba(201, 162, 39, 0.08);
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
}}
.s40-stat-number {{
  display: block;
  font-size: 2rem;
  font-weight: 800;
  color: #C9A227;
  margin-bottom: 4px;
}}
.s40-stat-label {{
  font-size: 0.85rem;
  color: #A0B0B2;
}}
.s40-wrapper {{
  background: #0B1E21;
  border-radius: 24px;
  padding: 48px 40px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* Latest Depot Update Banner */
.s40-depot-banner {{
  background: rgba(201, 162, 39, 0.04);
  border: 1px solid rgba(201, 162, 39, 0.18);
  border-radius: 16px;
  padding: 28px;
  margin: 20px 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}}
.s40-depot-info {{
  flex: 2;
  min-width: 280px;
}}
.s40-depot-badge {{
  display: inline-block;
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.72rem;
  font-weight: 700;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
.s40-depot-info h3 {{
  color: #F7F7F7 !important;
  font-size: 1.35rem;
  margin: 0 0 6px;
  font-weight: 700;
}}
.s40-depot-info p {{
  color: #A0B0B2;
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.55;
}}
.s40-depot-stats {{
  display: flex;
  gap: 12px;
  flex: 1.5;
  min-width: 260px;
  justify-content: space-around;
}}
.s40-depot-stat-card {{
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 10px 14px;
  border-radius: 8px;
  min-width: 80px;
}}
.s40-depot-stat-val {{
  display: block;
  color: #C9A227;
  font-size: 1.15rem;
  font-weight: 800;
}}
.s40-depot-stat-lbl {{
  color: #A0B0B2;
  font-size: 0.72rem;
}}
.s40-depot-btn {{
  background: #C9A227;
  color: #0B1E21 !important;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 700;
  text-decoration: none !important;
  font-size: 0.9rem;
  white-space: nowrap;
  transition: opacity 0.2s;
}}
.s40-depot-btn:hover {{
  opacity: 0.9;
  color: #0B1E21 !important;
}}

/* Newsletter Section */
.s40-newsletter {{
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed rgba(201, 162, 39, 0.3);
  border-radius: 20px;
  padding: 40px;
  margin-top: 40px;
  text-align: center;
}}
.s40-newsletter h3 {{
  color: #fff !important;
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 12px;
}}
.s40-newsletter p {{
  color: #A0B0B2;
  font-size: 1rem;
  max-width: 500px;
  margin: 0 auto 24px;
}}
.s40-newsletter-form {{
  display: flex;
  max-width: 450px;
  margin: 0 auto;
  gap: 10px;
}}
.s40-newsletter-form input {{
  flex: 1;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  outline: none;
}}
.s40-newsletter-form input:focus {{
  border-color: #C9A227;
}}
.s40-newsletter-btn {{
  background: #C9A227;
  color: #0B1E21 !important;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}}
.s40-newsletter-btn:hover {{
  opacity: 0.9;
  color: #0B1E21 !important;
}}
@media (max-width: 768px) {{
  .s40-depot-banner {{ flex-direction: column; align-items: stretch; text-align: center; }}
  .s40-depot-stats {{ margin: 12px 0; }}
  .s40-depot-btn {{ text-align: center; }}
}}
@media (max-width: 640px) {{
  .s40-hero {{ padding: 40px 20px; }}
  .s40-hero h2 {{ font-size: 1.6rem; }}
  .s40-stats {{ grid-template-columns: 1fr; }}
  .s40-wrapper {{ padding: 28px 20px; }}
}}
@media (max-width: 500px) {{
  .s40-newsletter-form {{ flex-direction: column; }}
}}
</style>

<div class="s40-wrapper">
  <!-- Hero -->
  <div class="s40-hero">
    <span class="s40-badge">&#127881; 100% Kostenlos &middot; Keine Anmeldung</span>
    <h2>Professionelle Aktienanalyse &mdash;<br>einfach &amp; schnell.</h2>
    <p>Deine Toolbox f&uuml;r smarte Investitionsentscheidungen. Erstelle Infografiken, vergleiche Aktien und behalte dein Portfolio im Blick.</p>
  </div>

  <!-- Latest Depot Update Banner -->
  <div class="s40-depot-banner">
    <div class="s40-depot-info">
      <span class="s40-depot-badge">Aktuelles Depot-Update: Juni 2026</span>
      <h3>Monatsrückblick: Sparraten &amp; Dividendenregen</h3>
      <p>Im Juni haben wir alle Benchmarks mit dem Dividendendepot geschlagen. Erfahre alles über meine Sparraten, Dividenden und die aktuelle Performance.</p>
    </div>
    <div class="s40-depot-stats">
      <div class="s40-depot-stat-card">
        <span class="s40-depot-stat-val">{stats['value']}</span>
        <span class="s40-depot-stat-lbl">Depotwert</span>
      </div>
      <div class="s40-depot-stat-card">
        <span class="s40-depot-stat-val">{stats['perf']}</span>
        <span class="s40-depot-stat-lbl">Performance</span>
      </div>
      <div class="s40-depot-stat-card">
        <span class="s40-depot-stat-val">{stats['dividends']}</span>
        <span class="s40-depot-stat-lbl">Dividenden</span>
      </div>
    </div>
    <a href="https://schatzsuche40.de/depotupdate-juni-2026/" class="s40-depot-btn">Rückblick lesen &rarr;</a>
  </div>

  <!-- Stats -->
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
      <span class="s40-stat-number">KI 5.4</span>
      <span class="s40-stat-label">gpt-5.4-mini Analyse</span>
    </div>
  </div>

  <!-- Tool Cards -->
  <div class="s40-tools-grid">
    <!-- Tool 1: Aktien-Analyse -->
    <a href="https://schatzsuche40.de/aktien-tool/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128202;</span>
      <div class="s40-tool-title">Aktien-Bild Generator</div>
      <p class="s40-tool-desc">Erstelle in Sekunden professionelle Infografiken mit &uuml;ber 30 Kennzahlen &ndash; inklusive KI-Bewertung von 5.4. Perfekt f&uuml;r Instagram, LinkedIn und deinen Blog.</p>
      <span class="s40-tool-tag">&#127381; KI-Analyse</span>
      <span class="s40-tool-tag">&#128444; PNG Export</span>
      <span class="s40-tool-tag">Dark Mode</span>
      <br>
      <span class="s40-tool-cta">Jetzt ausprobieren &rarr;</span>
    </a>

    <!-- Tool 2: Aktien-Vergleich -->
    <a href="https://schatzsuche40.de/aktien-vergleichstool/" class="s40-tool-card">
      <span class="s40-tool-icon">&#9878;&#65039;</span>
      <div class="s40-tool-title">Aktien-Vergleich</div>
      <p class="s40-tool-desc">Vergleiche zwei Unternehmen direkt &mdash; Rentabilit&auml;t, Bewertung, Dividende. Wer hat fundamental die Nase vorn? Finde es in Sekunden heraus.</p>
      <span class="s40-tool-tag">Duell-Vergleich</span>
      <span class="s40-tool-tag">&#128200; Analysten-Ziele</span>
      <span class="s40-tool-tag">Dividenden-Check</span>
      <br>
      <span class="s40-tool-cta">Aktien vergleichen &rarr;</span>
    </a>

    <!-- Tool 3: Aktien-Screener -->
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

    <!-- Tool 4: Dividenden-Rechner -->
    <a href="https://schatzsuche40.de/dividend-rechner/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128181;</span>
      <div class="s40-tool-title">Dividenden-Rechner</div>
      <p class="s40-tool-desc">Behalte deine passiven Einkommensstr&ouml;me im Blick. Berechne deine Dividenden-Zahlungen und analysiere deinen monatlichen Cashflow in Sekunden.</p>
      <span class="s40-tool-tag">&#128200; Cashflow-Check</span>
      <span class="s40-tool-tag">Monats-Vorschau</span>
      <br>
      <span class="s40-tool-cta">Jetzt berechnen &rarr;</span>
    </a>

    <!-- Tool 5: Dividenden-Kalender -->
    <a href="https://schatzsuche40.de/dividenden-kalender/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128197;</span>
      <div class="s40-tool-title">Dividenden-Kalender</div>
      <p class="s40-tool-desc">Verpasse nie wieder einen Ex-Tag oder Zahltag. Unser interaktiver Kalender listet alle Ausschüttungstermine für über 4.000 Aktien weltweit.</p>
      <span class="s40-tool-tag">Ex-Termine</span>
      <span class="s40-tool-tag">Zahltage</span>
      <span class="s40-tool-tag">Interaktiv</span>
      <br>
      <span class="s40-tool-cta">Kalender öffnen &rarr;</span>
    </a>

    <!-- Tool 6: P2P-Vergleich -->
    <a href="https://schatzsuche40.de/die-besten-plattformen/" class="s40-tool-card">
      <span class="s40-tool-icon">&#128184;</span>
      <div class="s40-tool-title">P2P-Plattformen</div>
      <p class="s40-tool-desc">Passives Einkommen durch Privatkredite. Wir vergleichen die besten Plattformen wie Mintos und Bondora für dein Portfolio.</p>
      <span class="s40-tool-tag">&#128200; 10%+ Rendite</span>
      <span class="s40-tool-tag">Platform-Check</span>
      <br>
      <span class="s40-tool-cta">Plattformen prüfen &rarr;</span>
    </a>
  </div>

  <!-- Newsletter / Lead Magnet -->
  <div class="s40-newsletter">
    <h3>&#128216; Gratis: Leitfaden Aktienbewertung</h3>
    <p>Melde dich zum Newsletter an und erhalte sofort unseren exklusiven Leitfaden zur Aktienbewertung f&uuml;r Einsteiger als PDF.</p>
    
    <form class="s40-newsletter-form" action="https://schatzsuche40.de/?na=s" method="post">
        <input type="email" name="ne" placeholder="Deine E-Mail-Adresse" required>
        <button type="submit" class="s40-newsletter-btn">PDF sichern &rarr;</button>
    </form>
    
    <p style="font-size: 0.75rem; margin-top: 15px; opacity: 0.5;">
        Abmeldung jederzeit möglich. Datenschutz wird groß geschrieben.
    </p>
  </div>
</div>
<!-- /wp:html -->"""
    return html

def update_homepage():
    print("=" * 60)
    print("Homepage Redesign - schatzsuche40.de")
    print("=" * 60)

    homepage_html = build_homepage_html()
    target_ids = [1045, 191]
    success = True
    
    for pid in target_ids:
        print(f"\nProcessing page ID {pid}...")
        r = requests.get(f"{BASE}/pages/{pid}?context=edit", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"Could not fetch page {pid}: {r.status_code} {r.text[:200]}")
            success = False
            continue

        page = r.json()
        current = page.get("content", {}).get("raw", "")
        print(f"Current page content length: {len(current)} chars")

        if "s40-wrapper" in current or "s40-hero" in current:
            print("Existing premium block found - replacing...")
            new_content = homepage_html
        else:
            print("Prepending new premium block...")
            new_content = homepage_html + "\n\n" + current

        payload = {"content": new_content}
        r = requests.post(f"{BASE}/pages/{pid}", headers=HEADERS, json=payload, timeout=20)

        if r.status_code in (200, 201):
            d = r.json()
            print(f"SUCCESS! Page {pid} updated.")
            print(f"View: {d.get('link', 'N/A')}")
        else:
            print(f"FAILED for page {pid}: {r.status_code} {r.text[:400]}")
            success = False

    return success

if __name__ == "__main__":
    update_homepage()
