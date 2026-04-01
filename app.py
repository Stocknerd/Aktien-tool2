from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_from_directory, flash, render_template_string
)
import os, pandas as pd, io, time
import saas_logic
import core
import tasks
import ai_logic
from datetime import datetime
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-aktien-tool')

# SaaS Guest Auth
GUEST_TOKEN = "b2831286e14844faa0782f69d4649825" # Standard Guest Token (Premium Tier)

def get_effective_token():
    t = request.form.get('token') or request.args.get('token')
    if not t or t.strip() == "":
        return GUEST_TOKEN
    return t.strip()

import ops_middleware
ops_middleware.setup_ops(app, core.CSV_FILE)

# ─── Navigation Helpers ──────────────────────────────────────
TOP_TICKERS_LIST = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'SAP.DE', 'SIE.DE', 'ALV.DE']

def get_ticker_meta(ticker):
    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if not row.empty:
        # Try different column names for sector
        sector = (row.iloc[0].get('GICS Sector') or 
                  row.iloc[0].get('Sektor') or 
                  row.iloc[0].get('Sector') or 
                  'Aktien')
        return {
            'symbol': ticker,
            'name': str(row.iloc[0].get('Langname', row.iloc[0].get('Security', ticker))),
            'sector': str(sector)
        }
    return None

def get_related_stocks(ticker, limit=6):
    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty: return []
    
    # Try multiple columns for categorization
    sector = row.iloc[0].get('GICS Sector') or row.iloc[0].get('Sektor') or row.iloc[0].get('Branche')
    if not sector: return []
    
    # Check both columns for matches
    related = df[
        ((df['GICS Sector'] == sector) | (df['Sektor'] == sector) | (df['Branche'] == sector)) & 
        (df['Symbol'] != ticker)
    ].head(limit)
    
    res = []
    for _, r in related.iterrows():
        res.append({
            'symbol': r['Symbol'],
            'name': str(r.get('Langname', r.get('Security', r['Symbol'])))
        })
    return res

# ─── Regular Routes ──────────────────────────────────────────

@app.route('/')
def home():
    df = core.load_df()
    keys = core.all_metric_keys(df)
    available = [{
        "key": k,
        "label": core.METRIC_LABELS.get(k, k),
        "desc": core.METRIC_DESC.get(k, "")
    } for k in keys]

    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else time.time()
    last_update_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
    
    show_cta = os.environ.get("SHOW_CTA_BANNER", "false").lower() == "true"
    is_embedded = request.args.get('embed') == '1'

    # Phase 8: Curated Top Stocks
    top_stocks = [get_ticker_meta(t) for t in TOP_TICKERS_LIST]
    top_stocks = [s for s in top_stocks if s]

    return render_template(
        'index.html',
        default_metrics=core.DEFAULT_METRICS,
        available_metrics=available,
        metric_descriptions=core.METRIC_DESC,
        last_update_str=last_update_str,
        is_stale=(time.time() - mtime) / 86400.0 > 1.5,
        show_cta=show_cta,
        is_embedded=is_embedded,
        top_stocks=top_stocks
    )

@app.route('/analyse/<ticker>')
@app.route('/<ticker>')
def stock_landing(ticker):
    # Normalize ticker
    ticker = ticker.upper().strip()
    # Skip common static paths or API routes if they hit here accidentally
    if ticker in ["SEARCH", "HEALTH", "API", "STATIC", "DOWNLOAD", "FAVICON.ICO"]:
        return redirect(url_for('home'))
        
    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        # Try to find by name if not found by exact symbol
        match = df[df['Langname'].str.contains(ticker, case=False, na=False)]
        if not match.empty:
            return redirect(url_for('stock_landing', ticker=match.iloc[0]['Symbol']))
        return redirect(url_for('home'))
    
    # Set a flag to trigger auto-analysis in index.html
    from flask import g
    g.is_landing_page = True
    
    keys = core.all_metric_keys(df)
    available = [{"key": k, "label": core.METRIC_LABELS.get(k, k), "desc": core.METRIC_DESC.get(k, "")} for k in keys]
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else time.time()
    last_update_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
    
    is_embedded = request.args.get('embed') == '1'
    company_name = str(row.iloc[0].get('Langname', ticker)) # Use Langname for SEO title

    return render_template(
        'index.html',
        ticker=ticker,
        company_name=company_name,
        default_metrics=core.DEFAULT_METRICS,
        available_metrics=available,
        metric_descriptions=core.METRIC_DESC,
        last_update_str=last_update_str,
        is_stale=(time.time() - mtime) / 86400.0 > 1.5,
        show_cta=False,
        is_embedded=is_embedded,
        is_landing=True
    )

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = core.load_df()
    if not q: return jsonify([])
    candidates = []
    
    # Fuzzy search: map dash/dot/space to uniform space
    def normalize(s):
        return str(s).lower().replace('-', ' ').replace('.', ' ').strip()
        
    q_norm = normalize(q)
    
    for _, row in df.iterrows():
        sym = normalize(row.get('Symbol') or '')
        sec = normalize(row.get('Security') or '')
        lng = normalize(row.get('Langname') or '')
        
        if q_norm in sym or q_norm in sec or q_norm in lng:
            candidates.append({
                'symbol': str(row.get('Symbol', '')), 
                'name': str(row.get('Security', ''))
            })
        if len(candidates) >= 15: break
    return jsonify(candidates)

@app.route('/generate_image', methods=['POST'])
def generate_image():
    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok:
        flash(msg, "danger")
        return redirect(url_for('home'))

    ticker = (request.form.get('ticker') or '').strip().upper().replace(' ', '')
    if not ticker:
        flash("Bitte einen Ticker eingeben.", "warning")
        return redirect(url_for('home'))

    selected = request.form.getlist('metrics') or core.DEFAULT_METRICS
    layout_mode = (request.form.get('layout') or 'default').lower()
    watermark = (request.form.get('watermark') or '').strip()

    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        flash(f"Ticker '{ticker}' nicht gefunden.", "danger")
        return redirect(url_for('home'))

    # Background override validation
    bg_path = None
    session_bg = request.form.get('bg_path') or ''
    if session_bg and os.path.exists(session_bg):
        safe_bg_dir = os.path.abspath(os.path.join(core.STATIC_DIR, 'user_backgrounds'))
        if os.path.abspath(session_bg).startswith(safe_bg_dir):
            bg_path = session_bg

    # AI Verdict Generation
    ai_verdict = ""
    if request.form.get('ai_insight') == '1':
        # Prepare data for AI
        fin_data = {}
        for m in selected:
            fin_data[m] = core.display_value(m, row.iloc[0])
        ai_verdict = ai_logic.get_ai_verdict(ticker, row.iloc[0].get('Langname', ticker), fin_data)

    img = core.render_stock_card(row.iloc[0], selected, layout_mode, watermark, bg_path=bg_path, ai_verdict=ai_verdict)
    
    filename = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(core.OUT_DIR, filename)
    img.convert('RGB').save(path, format='PNG')
    
    saas_logic.log_usage(token, "render")

    is_embedded_form = request.form.get('is_embedded') == '1'
    embed_param = "?embed=1" if is_embedded_form or request.args.get('embed') == '1' else ""
    return redirect(url_for('display_result', filename=filename, ticker=ticker) + embed_param)

@app.route('/upload-background', methods=['POST'])
def upload_background():
    """Accept a background image upload, save to static/user_backgrounds/, return its path."""
    if 'bg_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['bg_file']
    if not f or not f.filename:
        return jsonify({'error': 'Empty file'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.webp'):
        return jsonify({'error': 'Unsupported format'}), 400
    bg_dir = os.path.join(core.STATIC_DIR, 'user_backgrounds')
    os.makedirs(bg_dir, exist_ok=True)
    import uuid
    saved = os.path.join(bg_dir, f'{uuid.uuid4().hex}{ext}')
    f.save(saved)
    return jsonify({'bg_path': saved, 'url': f'/static/user_backgrounds/{os.path.basename(saved)}'})

@app.route('/result/<path:filename>')
def display_result(filename):
    is_embedded = request.args.get('embed') == '1'
    ticker = request.args.get('ticker', '').upper()
    company_name = ""
    related_stocks = []
    if ticker:
        df = core.load_df()
        row = df[df['Symbol'] == ticker]
        if not row.empty:
            company_name = str(row.iloc[0].get('Langname', row.iloc[0].get('Security', ticker)))
            related_stocks = get_related_stocks(ticker)
            
    return render_template(
        'display_result.html', 
        filename=filename, 
        is_embedded=is_embedded,
        ticker=ticker,
        company_name=company_name,
        related_stocks=related_stocks
    )

@app.route('/download/<path:filename>')
def download_image(filename):
    return send_from_directory(core.OUT_DIR, filename, as_attachment=True)

# ─── SaaS API v1 ──────────────────────────────────────────

@app.route('/api/v1/task/<task_id>')
def get_task_status(task_id):
    task = saas_logic.get_task(task_id)
    if not task: return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route('/api/v1/render', methods=['POST'])
def api_render():
    token = request.headers.get('Authorization') or request.args.get('token')
    if token and token.startswith('Bearer '): token = token[7:]
    if not token: return jsonify({"error": "Unauthorized"}), 401
    ok, msg = saas_logic.check_quota(token)
    if not ok: return jsonify({"error": msg}), 429
    data = request.json or {}
    ticker = data.get('ticker', '').upper().strip()
    if not ticker: return jsonify({"error": "Ticker required"}), 400
    return jsonify({"task_id": tasks.enqueue_task(token, "render", data), "status": "pending"})

# ─── Static Files ──────────────────────────────────────────

@app.route('/static/generated/<path:filename>')
@app.route('/output/<path:filename>')
def generated_file(filename):
    return send_from_directory(core.OUT_DIR, filename)

# ─── Comparison Tool Routes ───────────────────────────────

@app.route('/compare')
def compare_home():
    is_embedded = request.args.get('embed') == '1'
    t1 = request.args.get('t1', '').upper()
    t2 = request.args.get('t2', '').upper()
    m_param = request.args.get('metrics', '')
    
    # Explicitly render the comparison tool template
    return render_template('compare.html', is_embedded=is_embedded, vt1=t1, vt2=t2, vmetrics=m_param)

@app.route('/compare/generate', methods=['POST'])
def generate_compare():
    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok:
        flash(msg, "danger")
        return redirect(url_for('compare_home'))

    t1 = request.form.get('t1', '').upper().strip()
    t2 = request.form.get('t2', '').upper().strip()
    if not t1 or not t2:
        flash("Bitte beide Ticker angeben.", "warning")
        return redirect(url_for('compare_home'))

    df = core.load_df()
    row1 = df[df['Symbol'] == t1]
    row2 = df[df['Symbol'] == t2]

    if row1.empty or row2.empty:
        missing = t1 if row1.empty else t2
        flash(f"Ticker '{missing}' nicht gefunden.", "danger")
        return redirect(url_for('compare_home'))

    m_param = request.form.get('metrics_preset', '')
    if m_param == 'custom':
        m_param = request.form.get('metrics_custom', '')
    elif not m_param:
        m_param = request.form.get('metrics', '')

    if m_param:
        selected_metrics = [m.strip() for m in m_param.split(',') if m.strip()]
    else:
        selected_metrics = core.DEFAULT_METRICS

    bg_path = None
    session_bg = request.form.get('bg_path') or ''
    if session_bg and os.path.exists(session_bg):
        safe_bg_dir = os.path.abspath(os.path.join(core.STATIC_DIR, 'user_backgrounds'))
        if os.path.abspath(session_bg).startswith(safe_bg_dir):
            bg_path = session_bg

    img = core.render_compare([row1.iloc[0], row2.iloc[0]], selected_metrics, fetch_analyst=True, bg_path=bg_path)

    m_hash = "C" if m_param else "S"
    fname = f"COMPARE_{t1}_{t2}_{m_hash}_{int(time.time())}.png"
    path = os.path.join(core.OUT_DIR, fname)
    img.convert('RGB').save(path, format="PNG")

    saas_logic.log_usage(token, "compare")

    is_embedded = request.form.get('embed') == '1'
    embed_param = "&embed=1" if is_embedded or request.args.get('embed') == '1' else ""
    return redirect(url_for('compare_result', filename=fname, t1=t1, t2=t2, m_param=m_param) + embed_param)

@app.route('/compare/result/<path:filename>')
def compare_result(filename):
    is_embedded = request.args.get('embed') == '1'
    t1 = request.args.get('t1', '')
    t2 = request.args.get('t2', '')
    m_param = request.args.get('m_param', '')
    return render_template('compare_result.html', fname=filename, t1=t1, t2=t2, m_param=m_param, is_embedded=is_embedded)

# ─── Health Endpoints (Phase 1D) ───────────────────────────
@app.route('/health/data')
def app_health_data():
    import time as _time
    status = "ok"
    details = {}
    try:
        df = core.load_df()
        mtime = os.path.getmtime(core.CSV_FILE)
        age_h = (_time.time() - mtime) / 3600
        details["csv_rows"] = len(df)
        details["csv_age_hours"] = round(age_h, 1)
        details["csv_stale"] = age_h > 48
        if age_h > 48:
            status = "degraded"
    except Exception as e:
        status = "error"
        details["error"] = str(e)
    logo_count = len([f for f in os.listdir(core.LOGO_DIR) if f.endswith('.png')]) if os.path.exists(core.LOGO_DIR) else 0
    details["logos_cached"] = logo_count
    return jsonify({"status": status, **details}), 200 if status != "error" else 500

@app.route('/report-bug', methods=['POST'])
def report_bug():
    try:
        data = request.json
        ticker = data.get('ticker', 'Unknown')
        error = data.get('error', 'No description')
        email = data.get('email', '-')
        browser = request.headers.get('User-Agent', 'Unknown')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bugs.csv")
        file_exists = os.path.isfile(csv_path)
        
        with open(csv_path, mode='a', encoding='utf-8') as f:
            if not file_exists:
                f.write("Timestamp,Ticker,Error,Email,Browser\n")
            f.write(f'"{timestamp}","{ticker}","{error}","{email}","{browser}"\n')
            
        return jsonify({"status": "success", "message": "Bug reported successfully."})
    except Exception as e:
        print(f"Error reporting bug: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/bugs')
def admin_bugs():
    token = request.args.get('token')
    if token != GUEST_TOKEN:
        return "Access Denied: Invalid Token", 403
    
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bugs.csv")
    if not os.path.exists(csv_path):
        return "<h1>No Bug Reports found</h1><p>The file bugs.csv does not exist yet.</p>"
        
    try:
        df = pd.read_csv(csv_path)
        # Convert to HTML table with some basic styling
        table_html = df.to_html(classes='table table-striped table-hover', index=False)
        return f"""
        <html>
        <head>
            <title>Bug Dashboard</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>body{{padding:20px; background:#f8fafc;}} .container{{background:white; padding:30px; border-radius:15px; box-shadow:0 10px 30px rgba(0,0,0,0.05);}}</style>
        </head>
        <body>
            <div class="container">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1>🐛 Bug Reports</h1>
                    <span class="badge bg-primary">{len(df)} Einträge</span>
                </div>
                <div class="table-responsive">
                    {table_html}
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error reading bugs: {e}", 500

if __name__ == '__main__':
    saas_logic.init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
