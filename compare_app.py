from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os, time, pandas as pd
from datetime import datetime
import saas_logic
import core

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me')
GUEST_TOKEN = "b2831286e14844faa0782f69d4649825"

def get_effective_token():
    return request.args.get('token') or GUEST_TOKEN

import ops_middleware
ops_middleware.setup_ops(app, core.CSV_FILE)

# ─── Search endpoint (same logic as main app) ──────────────────
@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = core.load_df()
    candidates = []
    for _, r in df.iterrows():
        sym = str(r.get('Symbol', ''))
        sec = str(r.get('Security', ''))
        if q in sym.lower() or q in sec.lower():
            candidates.append({'symbol': sym, 'name': sec})
        if len(candidates) >= 12:
            break
    return jsonify(candidates)

# ─── UI Template ───────────────────────────────────────────────
COMPOSE_HTML = """
<!doctype html><html lang="de"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aktien Vergleich</title>
<style>
  :root { --bg:#091221; --panel:#0f1b2b; --border:rgba(255,255,255,.08); --f:#e9eef6; --muted:#9fb0c7; --acc:#10b981; --acc2:#059669; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
         background:{% if is_embedded %}transparent{% else %}var(--bg){% endif %};
         color:var(--f); min-height:100vh; padding:{% if is_embedded %}12px{% else %}40px 16px{% endif %}; }
  {% if is_embedded %}h1{display:none}{% endif %}
  h1 { text-align:center; font-size:1.8rem; font-weight:700; margin-bottom:28px;
       background:linear-gradient(135deg,#10b981,#3b82f6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .card { background:rgba(255,255,255,.04); border:1px solid var(--border); border-radius:20px; padding:28px; max-width:860px; margin:0 auto; }
  .row { display:flex; flex-wrap:wrap; gap:16px; margin-bottom:16px; }
  .field-wrap { flex:1 1 200px; position:relative; min-width:0; }
  label { display:block; font-size:0.78rem; color:var(--muted); margin-bottom:6px; text-transform:uppercase; letter-spacing:.05em; }
  input[type=text] { width:100%; padding:12px 16px; border-radius:10px; border:1px solid var(--border);
                     background:rgba(255,255,255,.06); color:var(--f); font-size:1rem; outline:none; transition:.2s; }
  input[type=text]:focus { border-color:var(--acc); background:rgba(16,185,129,.08); }
  .suggestions { position:absolute; top:calc(100% + 4px); left:0; right:0; background:#0f1b2b;
                 border:1px solid var(--border); border-radius:10px; z-index:100; max-height:220px;
                 overflow-y:auto; display:none; box-shadow:0 8px 32px rgba(0,0,0,.5); }
  .suggestions li { list-style:none; padding:10px 14px; cursor:pointer; font-size:.92rem; }
  .suggestions li:hover, .suggestions li.active { background:rgba(16,185,129,.15); color:var(--acc); }
  .vs-badge { display:flex; align-items:center; justify-content:center; font-size:1.2rem; font-weight:800;
              color:var(--acc); padding-top:24px; }
  button[type=submit] { width:100%; margin-top:20px; padding:15px; background:linear-gradient(135deg,var(--acc),var(--acc2));
                        border:none; border-radius:12px; color:white; font-size:1rem; font-weight:700;
                        cursor:pointer; letter-spacing:.04em; transition:.2s; }
  button[type=submit]:hover { opacity:.88; transform:translateY(-1px); }
  .hint { text-align:center; margin-top:14px; font-size:.82rem; color:var(--muted); }
  .spinner { display:inline-block; width:16px; height:16px; border:2px solid rgba(255,255,255,.3); border-radius:50%; border-top-color:#fff; animation:spin 1s ease-in-out infinite; vertical-align:middle; margin-left:8px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head><body>
<h1>Aktien Vergleich ⚡</h1>
<div class="card">
  <form action="/generate" method="get" id="cmpForm">
    <input type="hidden" name="embed" value="{{ '1' if is_embedded else '0' }}">
    <div class="row">
      <!-- Ticker A -->
      <div class="field-wrap">
        <label>Aktie A</label>
        <input type="text" id="search1" placeholder="z.B. Apple, AAPL…" autocomplete="off" value="{{ vt1 }}">
        <ul class="suggestions" id="sugg1"></ul>
        <input type="hidden" name="t1" id="t1" value="{{ vt1 }}">
      </div>
      <div class="vs-badge">VS</div>
      <!-- Ticker B -->
      <div class="field-wrap">
        <label>Aktie B</label>
        <input type="text" id="search2" placeholder="z.B. Tesla, TSLA…" autocomplete="off" value="{{ vt2 }}">
        <ul class="suggestions" id="sugg2"></ul>
        <input type="hidden" name="t2" id="t2" value="{{ vt2 }}">
      </div>
    <div class="row" style="margin-top:4px;">
      <div class="field-wrap">
        <label>Metriken</label>
        <select name="metrics_preset" style="width:100%; padding:12px; border-radius:10px; border:1px solid var(--border); background:rgba(255,255,255,.06); color:var(--f); outline:none;" onchange="document.getElementById('custom_metrics').style.display = this.value === 'custom' ? 'block' : 'none'">
          <option value="" {% if not vmetrics %}selected{% endif %}>Standard (KGV, Margen, Wachstum)</option>
          <option value="Dividendenrendite,Ausschüttungsquote,KGV,Forward PE,KBV,Operative Marge,Eigenkapitalrendite" {% if vmetrics == 'Dividendenrendite,Ausschüttungsquote,KGV,Forward PE,KBV,Operative Marge,Eigenkapitalrendite' %}selected{% endif %}>Dividenden & Value</option>
          <option value="Umsatzwachstum 3J (erwartet),PEG-Ratio,Forward PE,Bruttomarge,Operative Marge,ROIC" {% if vmetrics == 'Umsatzwachstum 3J (erwartet),PEG-Ratio,Forward PE,Bruttomarge,Operative Marge,ROIC' %}selected{% endif %}>Wachstum & Tech</option>
          <option value="custom" {% if vmetrics and vmetrics not in ['Dividendenrendite,Ausschüttungsquote,KGV,Forward PE,KBV,Operative Marge,Eigenkapitalrendite','Umsatzwachstum 3J (erwartet),PEG-Ratio,Forward PE,Bruttomarge,Operative Marge,ROIC'] %}selected{% endif %}>Individuell (Kommagetrennt)</option>
        </select>
        <input type="text" name="metrics_custom" id="custom_metrics" placeholder="z.B. Dividendenrendite, KGV..." style="display:{% if vmetrics and vmetrics not in ['Dividendenrendite,Ausschüttungsquote,KGV,Forward PE,KBV,Operative Marge,Eigenkapitalrendite','Umsatzwachstum 3J (erwartet),PEG-Ratio,Forward PE,Bruttomarge,Operative Marge,ROIC'] %}block{% else %}none{% endif %}; margin-top:10px; width:100%; padding:12px; border-radius:10px; border:1px solid var(--border); background:rgba(255,255,255,.06); color:var(--f); outline:none;" value="{% if vmetrics and vmetrics not in ['Dividendenrendite,Ausschüttungsquote,KGV,Forward PE,KBV,Operative Marge,Eigenkapitalrendite','Umsatzwachstum 3J (erwartet),PEG-Ratio,Forward PE,Bruttomarge,Operative Marge,ROIC'] %}{{ vmetrics }}{% endif %}">
      </div>
    </div>
    <div class="row" style="margin-top:4px;">
      <div class="field-wrap">
        <label>Eigenes Hintergrundbild (Optional)</label>
        <input type="file" id="bg_upload" accept="image/png, image/jpeg, image/webp" style="width:100%; padding:12px; border-radius:10px; border:1px solid var(--border); background:rgba(255,255,255,.06); color:var(--f);">
        <input type="hidden" name="bg_path" id="bg_path" value="">
        <div id="bg-preview" style="color:var(--acc); font-size:0.8rem; margin-top:4px; display:none;"></div>
      </div>
    </div>
    <button type="submit">Vergleich erstellen →</button>
  </form>
  <p class="hint">Beide Felder müssen ausgefüllt sein.</p>
</div>

<script>
function setupAutocomplete(searchId, suggId, hiddenId) {
  const inp = document.getElementById(searchId);
  const list = document.getElementById(suggId);
  const hidden = document.getElementById(hiddenId);
  let activeIdx = -1;

  inp.addEventListener('input', async () => {
    const q = inp.value.trim();
    if (!q) { list.style.display = 'none'; return; }
    const res = await fetch('/search?q=' + encodeURIComponent(q));
    const data = res.ok ? await res.json() : [];
    if (!data.length) { list.style.display = 'none'; return; }
    list.innerHTML = data.map(o =>
      `<li data-sym="${o.symbol}">${o.symbol} — ${o.name}</li>`
    ).join('');
    list.style.display = 'block';
    activeIdx = -1;
  });

  list.addEventListener('click', e => {
    const li = e.target.closest('li[data-sym]');
    if (!li) return;
    hidden.value = inp.value = li.dataset.sym;
    list.style.display = 'none';
  });

  inp.addEventListener('keydown', e => {
    const items = list.querySelectorAll('li');
    if (e.key === 'ArrowDown') { activeIdx = Math.min(activeIdx+1, items.length-1); }
    else if (e.key === 'ArrowUp') { activeIdx = Math.max(activeIdx-1, 0); }
    else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      const li = items[activeIdx];
      hidden.value = inp.value = li.dataset.sym;
      list.style.display = 'none';
    } else return;
    items.forEach((li, i) => li.classList.toggle('active', i === activeIdx));
  });

  document.addEventListener('click', e => {
    if (!inp.contains(e.target) && !list.contains(e.target)) list.style.display = 'none';
  });
}

setupAutocomplete('search1', 'sugg1', 't1');
setupAutocomplete('search2', 'sugg2', 't2');

const bgInput = document.getElementById('bg_upload');
if(bgInput) {
  bgInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if(!file) return;
    const fd = new FormData();
    fd.append('bg_file', file);
    const pv = document.getElementById('bg-preview');
    pv.textContent = 'Lädt hoch... ⏳'; pv.style.display = 'block';
    try {
      const res = await fetch('/upload-background', { method: 'POST', body: fd });
      if(res.ok) {
        const data = await res.json();
        document.getElementById('bg_path').value = data.bg_path;
        pv.textContent = 'Hintergrundbild aktiv! ✅';
      } else { pv.textContent = 'Upload fehlerhaft ❌'; }
    } catch(e) { pv.textContent = 'Verbindungsfehler ❌'; }
  });
}

document.getElementById('cmpForm').addEventListener('submit', e => {
  if (!document.getElementById('t1').value || !document.getElementById('t2').value) {
    e.preventDefault();
    alert('Bitte beide Aktien auswählen.');
  } else {
    const btn = e.target.querySelector('button[type="submit"]');
    btn.innerHTML = 'Generiere Grafik... <span class="spinner"></span>';
    btn.style.pointerEvents = 'none';
    btn.style.opacity = '0.8';
  }
});
</script>
{% if is_embedded %}
<script>
  function sendHeight() { window.parent.postMessage({type:'setHeight', height:document.body.scrollHeight}, '*'); }
  window.onload = sendHeight; window.onresize = sendHeight;
</script>
{% endif %}
</body></html>
"""

# ─── Result page template ───────────────────────────────────────
RESULT_HTML = """
<!doctype html><html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vergleich {{ t1 }} vs {{ t2 }}</title>
<style>
  body{margin:0;background:#091221;color:#e9eef6;font-family:ui-sans-serif,system-ui;display:flex;flex-direction:column;align-items:center;min-height:100vh;padding:32px 16px;}
  img{max-width:100%;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,.6);}
  .actions{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap;justify-content:center;}
  a.btn, button.btn{padding:12px 28px;border-radius:10px;font-weight:700;text-decoration:none;font-size:.95rem;font-family:inherit;border:none;cursor:pointer;}
  .dl{background:#10b981;color:#fff;}
  .share{background:rgba(255,255,255,.07);color:#fff;border:1px solid rgba(255,255,255,.15);transition:.2s;}
  .share:hover{background:rgba(255,255,255,.15);}
  .back{background:rgba(255,255,255,.07);color:#e9eef6;border:1px solid rgba(255,255,255,.12);}
</style>
</head><body>
<img src="/static/generated/{{ fname }}">
<div class="actions">
  <a class="btn dl" href="/download/{{ fname }}" download>⬇ PNG herunterladen</a>
  <button class="btn share" onclick="copyShare()">🔗 Link teilen</button>
  <a class="btn back" href="/">← Neuer Vergleich</a>
</div>
<script>
function copyShare() {
  let url = window.location.origin + "/?t1={{ t1 }}&t2={{ t2 }}";
  {% if m_param %}url += "&metrics={{ m_param }}";{% endif %}
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.querySelector('.share');
    btn.innerText = '✅ Kopiert!';
    setTimeout(() => btn.innerText = '🔗 Link teilen', 2000);
  });
}
</script>
</body></html>
"""

@app.route('/')
def compare_home():
    is_embedded = request.args.get('embed') == '1'
    t1 = request.args.get('t1', '').upper()
    t2 = request.args.get('t2', '').upper()
    m_param = request.args.get('metrics', '')
    return render_template_string(COMPOSE_HTML, is_embedded=is_embedded, vt1=t1, vt2=t2, vmetrics=m_param)

@app.route('/upload-background', methods=['POST'])
def upload_background():
    if 'bg_file' not in request.files: return jsonify({'error': 'No file'}), 400
    f = request.files['bg_file']
    if not f or not f.filename: return jsonify({'error': 'Empty'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.webp'): return jsonify({'error': 'Invalid format'}), 400
    bg_dir = os.path.join(core.STATIC_DIR, 'user_backgrounds')
    os.makedirs(bg_dir, exist_ok=True)
    import uuid
    saved = os.path.join(bg_dir, f'{uuid.uuid4().hex}{ext}')
    f.save(saved)
    return jsonify({'bg_path': saved})

@app.route('/generate')
def generate_compare():
    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok:
        return f"<p style='color:red;font-family:sans-serif;padding:20px'>{msg}</p>", 429

    t1 = request.args.get('t1', '').upper().strip()
    t2 = request.args.get('t2', '').upper().strip()
    if not t1 or not t2:
        return "Bitte beide Ticker angeben.", 400

    df = core.load_df()
    row1 = df[df['Symbol'] == t1]
    row2 = df[df['Symbol'] == t2]

    if row1.empty or row2.empty:
        missing = t1 if row1.empty else t2
        return f"Ticker '{missing}' nicht gefunden.", 404

    m_param = request.args.get('metrics_preset', '')
    if m_param == 'custom':
        m_param = request.args.get('metrics_custom', '')
    elif not m_param:
        # Fallback if somehow both empty
        m_param = request.args.get('metrics', '')

    if m_param:
        selected_metrics = [m.strip() for m in m_param.split(',') if m.strip()]
    else:
        selected_metrics = core.DEFAULT_METRICS

    bg_path = None
    if request.args.get('bg_path') and os.path.exists(request.args.get('bg_path')):
        bg_path = request.args.get('bg_path')

    img = core.render_compare([row1.iloc[0], row2.iloc[0]], selected_metrics, fetch_analyst=True, bg_path=bg_path)

    m_hash = "C" if m_param else "S"
    fname = f"COMPARE_{t1}_{t2}_{m_hash}_{int(time.time())}.png"
    path = os.path.join(core.OUT_DIR, fname)
    img.convert('RGB').save(path, format="PNG")

    saas_logic.log_usage(token, "compare")

    return render_template_string(RESULT_HTML, fname=fname, t1=t1, t2=t2, m_param=m_param)

@app.route('/download/<path:filename>')
def download_image(filename):
    return send_from_directory(core.OUT_DIR, filename, as_attachment=True)

@app.route('/static/generated/<path:filename>')
def generated_file(filename):
    return send_from_directory(core.OUT_DIR, filename)

if __name__ == '__main__':
    saas_logic.init_db()
    app.run(debug=True, port=5001)
