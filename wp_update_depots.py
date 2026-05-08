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

DEPOTS_HTML = """<!-- wp:html -->
<style>
.depot-comparison {
  margin: 40px 0;
  font-family: 'Inter', sans-serif;
}
.depot-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 30px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 30px;
  transition: transform 0.2s;
}
.depot-card:hover {
  transform: translateY(-4px);
  border-color: #6366f1;
}
.depot-logo {
  width: 120px;
  height: 120px;
  background: #fff;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px;
  flex-shrink: 0;
}
.depot-logo img {
  max-width: 100%;
  height: auto;
}
.depot-content {
  flex: 1;
}
.depot-tag {
  display: inline-block;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  padding: 4px 12px;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: 700;
  margin-bottom: 12px;
}
.depot-title {
  font-size: 1.4rem;
  font-weight: 800;
  color: #fff !important;
  margin-bottom: 8px;
}
.depot-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}
.depot-feature {
  font-size: 0.9rem;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 8px;
}
.depot-feature::before {
  content: '✓';
  color: #10b981;
  font-weight: bold;
}
.depot-cta {
  background: #6366f1;
  color: #fff !important;
  padding: 14px 28px;
  border-radius: 10px;
  font-weight: 700;
  text-decoration: none !important;
  display: inline-block;
}
.depot-badge {
  background: #f59e0b;
  color: #000;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
  vertical-align: middle;
  margin-left: 10px;
}
@media (max-width: 768px) {
  .depot-card { flex-direction: column; text-align: center; }
  .depot-features { grid-template-columns: 1fr; }
}
</style>

<div class="depot-comparison">
  <!-- Traders Place -->
  <div class="depot-card">
    <div class="depot-logo">
      <img src="https://schatzsuche40.de/wp-content/uploads/2026/01/tradersplace_logo.png" alt="Traders Place">
    </div>
    <div class="depot-content">
      <span class="depot-tag">Top-Empfehlung 2026</span>
      <div class="depot-title">Traders Place <span class="depot-badge">NEU</span></div>
      <div class="depot-features">
        <div class="depot-feature">0€ Ordergebühr über Gettex</div>
        <div class="depot-feature">Handel an 40+ Börsen weltweit</div>
        <div class="depot-feature">Gratis Sparpläne</div>
        <div class="depot-feature">Web & App verfügbar</div>
      </div>
      <a href="https://www.financeads.net/tc.php?t=47128C274449894T" class="depot-cta" target="_blank">Konto eröffnen & Bonus sichern*</a>
    </div>
  </div>

  <!-- C24 Bank -->
  <div class="depot-card">
    <div class="depot-logo">
      <img src="https://schatzsuche40.de/wp-content/uploads/2026/01/c24_logo.png" alt="C24 Bank">
    </div>
    <div class="depot-content">
      <span class="depot-tag">Bestes Girokonto</span>
      <div class="depot-title">C24 Bank (Check24 Gruppe)</div>
      <div class="depot-features">
        <div class="depot-feature">Kostenlose Kontoführung</div>
        <div class="depot-feature">Zinsen auf das laufende Konto</div>
        <div class="depot-feature">Echtzeit-Überweisungen</div>
        <div class="depot-feature">Kostenlose Mastercard</div>
      </div>
      <a href="https://a.check24.net/misc/click.php?pid=109920&aid=18&deep=c24bank&cat=14" class="depot-cta" target="_blank">Jetzt Girokonto eröffnen*</a>
    </div>
  </div>

  <!-- Scalable Capital -->
  <div class="depot-card">
    <div class="depot-logo">
      <img src="https://schatzsuche40.de/wp-content/uploads/2026/01/scalable_logo.png" alt="Scalable Capital">
    </div>
    <div class="depot-content">
      <span class="depot-tag">Platzhirsch</span>
      <div class="depot-title">Scalable Capital</div>
      <div class="depot-features">
        <div class="depot-feature">Prime-Flatrate für Vieltrader</div>
        <div class="depot-feature">Über 7.000 Aktien & 1.700 ETFs</div>
        <div class="depot-feature">Top Zinsen auf Guthaben</div>
        <div class="depot-feature">Sehr intuitive App</div>
      </div>
      <a href="https://www.financeads.net/tc.php?t=42020C274449894T" class="depot-cta" target="_blank">Depot bei Scalable eröffnen*</a>
    </div>
  </div>
</div>

<p style="font-size: 0.8rem; opacity: 0.6; text-align: center; margin-top: 20px;">
  *Affiliate Links: Bei Kontoeröffnung erhalten wir ggf. eine kleine Provision. Für dich entstehen keine Kosten. Investieren birgt Risiken.
</p>
<!-- /wp:html -->"""

def update_depots():
    payload = {
        "content": DEPOTS_HTML,
    }
    r = requests.post(f"{BASE}/pages/114", headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print(f"SUCCESS! 'Meine Depots' page updated.")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    update_depots()
