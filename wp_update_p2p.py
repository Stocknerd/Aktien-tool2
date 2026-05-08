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

LOGOS = {
    'mintos': 'https://upload.wikimedia.org/wikipedia/commons/e/e0/Mintos_logo.svg',
    'bondora': 'https://upload.wikimedia.org/wikipedia/commons/d/df/Bondora_logo.svg',
    'twino': 'https://upload.wikimedia.org/wikipedia/commons/b/b3/Twino_logo.svg',
    'robocash': 'https://p2pempire.com/media/images/robocash-logo.png',
}

P2P_HTML = f"""<!-- wp:html -->
<style>
.p2p-container {{ font-family: 'Inter', sans-serif; color: #f1f5f9; max-width: 1000px; margin: 0 auto; }}
.p2p-intro {{ background: rgba(255,255,255,0.03); border-radius: 20px; padding: 40px; margin-bottom: 40px; border: 1px solid rgba(255,255,255,0.05); text-align: center; }}
.p2p-intro h2 {{ color: #10b981 !important; font-size: 2.2rem; font-weight: 800; margin-bottom: 20px; }}
.p2p-intro p {{ font-size: 1.1rem; line-height: 1.8; color: #94a3b8; max-width: 800px; margin: 0 auto; }}

.p2p-comparison {{ margin: 60px 0; }}
.p2p-card {{ background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; padding: 40px; margin-bottom: 30px; display: flex; align-items: center; gap: 40px; transition: all 0.3s ease; }}
.p2p-card:hover {{ transform: translateY(-5px); border-color: #10b981; box-shadow: 0 20px 40px rgba(0,0,0,0.3); background: rgba(30, 41, 59, 0.6); }}
.p2p-logo {{ width: 140px; height: 60px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden; }}
.p2p-logo img {{ width: 100%; height: auto; max-height: 100%; object-fit: contain; }}
.p2p-content {{ flex: 1; }}
.p2p-tag {{ display: inline-block; background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 6px 16px; border-radius: 50px; font-size: 0.85rem; font-weight: 700; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.05em; }}
.p2p-title {{ font-size: 1.8rem; font-weight: 800; color: #fff !important; margin-bottom: 12px; }}
.p2p-desc {{ color: #94a3b8; font-size: 1rem; margin-bottom: 20px; line-height: 1.6; }}
.p2p-features {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 25px; }}
.p2p-feature {{ font-size: 0.95rem; color: #cbd5e1; display: flex; align-items: center; gap: 10px; }}
.p2p-feature::before {{ content: '✓'; color: #10b981; font-weight: 900; }}
.p2p-cta {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff !important; padding: 14px 28px; border-radius: 12px; font-weight: 800; text-decoration: none !important; display: inline-block; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: 0.2s; }}
.p2p-cta:hover {{ transform: scale(1.05); filter: brightness(1.1); }}
.p2p-yield {{ font-size: 1.5rem; font-weight: 900; color: #10b981; text-align: right; min-width: 140px; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px; }}

.p2p-faq {{ margin-top: 80px; }}
.p2p-faq h3 {{ font-size: 2rem; font-weight: 800; color: #fff !important; margin-bottom: 30px; text-align: center; }}
.faq-item {{ margin-bottom: 25px; background: rgba(255,255,255,0.02); padding: 25px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }}
.faq-item h4 {{ color: #10b981 !important; font-weight: 700; margin-top: 0; margin-bottom: 10px; }}
.faq-item p {{ color: #94a3b8; line-height: 1.6; margin-bottom: 0; }}

.p2p-table-container {{ overflow-x: auto; margin: 40px 0; background: rgba(30, 41, 59, 0.3); border-radius: 20px; padding: 20px; }}
.p2p-table {{ width: 100%; border-collapse: collapse; color: #cbd5e1; }}
.p2p-table th {{ text-align: left; padding: 15px; border-bottom: 2px solid rgba(255,255,255,0.1); color: #fff; text-transform: uppercase; font-size: 0.8rem; }}
.p2p-table td {{ padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); }}

@media (max-width: 900px) {{
  .p2p-card {{ flex-direction: column; text-align: center; padding: 30px; }}
  .p2p-yield {{ border-left: none; padding-left: 0; text-align: center; margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px; }}
  .p2p-features {{ grid-template-columns: 1fr; }}
}}
</style>

<div class="p2p-container">
  <div class="p2p-intro">
    <h2>P2P-Plattform Vergleich 2026</h2>
    <p>P2P-Kredite sind eine der spannendsten Möglichkeiten, um einen stetigen Cashflow aufzubauen. In diesem Vergleich erfährst du alles über die Plattformen, die ich selbst nutze, um mein Kapital für mich arbeiten zu lassen.</p>
  </div>

  <div class="p2p-table-container">
    <table class="p2p-table">
      <thead>
        <tr>
          <th>Plattform</th>
          <th>Zielrendite</th>
          <th>Min. Investment</th>
          <th>Sicherheit</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><strong>Mintos</strong></td><td>10-12%</td><td>50 €</td><td>Reguliert (Notes)</td></tr>
        <tr><td><strong>Bondora</strong></td><td>Bis 6,75%</td><td>1 €</td><td>Täglich verfügbar</td></tr>
        <tr><td><strong>Robocash</strong></td><td>10-12%</td><td>10 €</td><td>Buyback Garantie</td></tr>
        <tr><td><strong>Twino</strong></td><td>10-12%</td><td>10 €</td><td>Buyback Garantie</td></tr>
      </tbody>
    </table>
  </div>

  <div class="p2p-comparison">
    <!-- Mintos -->
    <div class="p2p-card">
      <div class="p2p-logo"><img src="{LOGOS['mintos']}" alt="Mintos"></div>
      <div class="p2p-content">
        <span class="p2p-tag">Europas Nr. 1</span>
        <div class="p2p-title">Mintos</div>
        <p class="p2p-desc">Der größte Marktplatz für P2P-Kredite in Europa. Durch die neuen "Mintos Notes" ist das System jetzt voll reguliert und bietet maximale Sicherheit bei hoher Rendite.</p>
        <div class="p2p-features">
          <div class="p2p-feature">Über 500.000 Nutzer weltweit</div>
          <div class="p2p-feature">Investition in Kredite, ETFs & Anleihen</div>
          <div class="p2p-feature">Vollautomatisierter Auto-Invest</div>
          <div class="p2p-feature">Sekundärmarkt für Liquidität</div>
        </div>
        <a href="https://www.mintos.com/de/l/ref/74LECG" class="p2p-cta" target="_blank">Jetzt Mintos Depot eröffnen*</a>
      </div>
      <div class="p2p-yield">10 - 12%<br><small style="font-size:0.75rem; color:#64748b; font-weight:400;">erwartete Rendite</small></div>
    </div>

    <!-- Bondora -->
    <div class="p2p-card">
      <div class="p2p-logo"><img src="{LOGOS['bondora']}" alt="Bondora"></div>
      <div class="p2p-content">
        <span class="p2p-tag">Passiv-König</span>
        <div class="p2p-title">Bondora Go & Grow</div>
        <p class="p2p-desc">Die wohl einfachste Art, in P2P zu investieren. Mit Go & Grow parkst du dein Geld wie auf einem Tagesgeldkonto, erhältst aber deutlich höhere Zinsen.</p>
        <div class="p2p-features">
          <div class="p2p-feature">Tägliche Verfügbarkeit des Kapitals</div>
          <div class="p2p-feature">Tägliche Zinsgutschrift (Zinseszins!)</div>
          <div class="p2p-feature">Keine Auswahl von Einzelkrediten nötig</div>
          <div class="p2p-feature">5€ Bonus für Neukunden</div>
        </div>
        <a href="https://goandgrow.eu/ref/frankh68" class="p2p-cta" target="_blank">5€ Bonus sichern*</a>
      </div>
      <div class="p2p-yield">Bis 6,75%<br><small style="font-size:0.75rem; color:#64748b; font-weight:400;">p.a. Zielzins</small></div>
    </div>

    <!-- Robocash -->
    <div class="p2p-card">
      <div class="p2p-logo"><img src="{LOGOS['robocash']}" alt="Robocash"></div>
      <div class="p2p-content">
        <span class="p2p-tag">Autopilot Pur</span>
        <div class="p2p-title">Robocash</div>
        <p class="p2p-desc">Ein kroatischer P2P-Anbieter, der sich auf vollautomatisierte Kurzzeitkredite spezialisiert hat. Extrem stabil und verlässlich seit Jahren.</p>
        <div class="p2p-features">
          <div class="p2p-feature">Vollständige Rückkaufgarantie</div>
          <div class="p2p-feature">Sehr hohe Auto-Invest Rate</div>
          <div class="p2p-feature">Kurze Laufzeiten (30 - 180 Tage)</div>
          <div class="p2p-feature">Transparente Konzernberichte</div>
        </div>
        <a href="https://robo.cash/ref/akvg" class="p2p-cta" target="_blank">Robocash testen*</a>
      </div>
      <div class="p2p-yield">~ 10-12%<br><small style="font-size:0.75rem; color:#64748b; font-weight:400;">Rendite p.a.</small></div>
    </div>

    <!-- Twino -->
    <div class="p2p-card">
      <div class="p2p-logo"><img src="{LOGOS['twino']}" alt="Twino"></div>
      <div class="p2p-content">
        <span class="p2p-tag">Traditionsmarke</span>
        <div class="p2p-title">Twino</div>
        <p class="p2p-desc">Twino gehört zu den erfahrensten Plattformen am Markt. Sie bieten eine gute Mischung aus Konsumkrediten und Immobilienprojekten.</p>
        <div class="p2p-features">
          <div class="p2p-feature">Umfangreiches Buyback-System</div>
          <div class="p2p-feature">Regulierte Investment-Umgebung</div>
          <div class="p2p-feature">Einfacher Investment-Assistent</div>
          <div class="p2p-feature">Starke Performance in Krisenzeiten</div>
        </div>
        <a href="https://www.twino.eu/de/join-today?refer_friend=168935" class="p2p-cta" target="_blank">Jetzt zu Twino*</a>
      </div>
      <div class="p2p-yield">~ 10%<br><small style="font-size:0.75rem; color:#64748b; font-weight:400;">Zielrendite</small></div>
    </div>
  </div>

  <div class="p2p-faq">
    <h3>Häufige Fragen (FAQ)</h3>
    <div class="faq-item">
      <h4>Was ist eine Rückkaufgarantie (Buyback)?</h4>
      <p>Wenn ein Kreditnehmer mehr als 30 oder 60 Tage in Verzug gerät, kauft der Darlehensanbahner den Kredit inklusive Zinsen vom Investor zurück. Das reduziert das Risiko von Kreditausfällen massiv.</p>
    </div>
    <div class="faq-item">
      <h4>Wie viel Geld sollte ich in P2P investieren?</h4>
      <p>P2P-Kredite gelten als alternative Anlageklasse. Ich persönlich investiere etwa 10-15% meines liquiden Kapitals in P2P, um den Cashflow zu erhöhen, ohne das Gesamtrisiko zu stark zu steigern.</p>
    </div>
    <div class="faq-item">
      <h4>Muss ich P2P-Zinsen versteuern?</h4>
      <p>Ja, in Deutschland unterliegen Zinserträge der Abgeltungssteuer (zzgl. Soli und ggf. Kirchensteuer). Die meisten Plattformen führen die Steuer nicht automatisch ab, daher musst du sie in deiner Steuererklärung angeben.</p>
    </div>
  </div>

  <div class="alert alert-danger mt-5 p-4 rounded-4" style="background: rgba(239, 68, 68, 0.05); border: 1px dashed #ef4444;">
    <h5 class="fw-bold mb-2" style="color: #ef4444;">🚨 Wichtiger Risikohinweis</h5>
    <p class="mb-0 small" style="color: #94a3b8;">P2P-Investments sind mit Risiken verbunden. Es handelt sich um unbesicherte (oder nur durch Garantien besicherte) Kredite. Es besteht das Risiko eines Totalverlustes. Streue dein Kapital daher immer auf verschiedene Plattformen und Tausende Einzelkredite.</p>
  </div>
</div>

<p style="font-size: 0.8rem; opacity: 0.6; text-align: center; margin: 40px 0;">
  *Affiliate Links: Bei Anmeldung über diese Links unterstützen Sie Schatzsuche 4.0. Für Sie entstehen keine Kosten, oft erhalten Sie sogar einen Bonus.
</p>
<!-- /wp:html -->"""

def update_p2p():
    payload = {"content": P2P_HTML, "title": "Beste P2P-Plattformen 2026 im Vergleich"}
    r = requests.post(f"{BASE}/pages/423", headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print("SUCCESS! P2P page updated with Premium Logos and expanded content.")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    update_p2p()
