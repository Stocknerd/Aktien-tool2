from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_from_directory, flash
)
import os, pandas as pd, io, time
import saas_logic
import core
import tasks
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

    return render_template(
        'index.html',
        default_metrics=core.DEFAULT_METRICS,
        available_metrics=available,
        metric_descriptions=core.METRIC_DESC,
        last_update_str=last_update_str,
        is_stale=(time.time() - mtime) / 86400.0 > 1.5,
        show_cta=show_cta,
        is_embedded=is_embedded
    )

@app.route('/<ticker>')
def stock_landing(ticker):
    ticker = ticker.upper().strip()
    # Skip common static paths or API routes if they hit here accidentally
    if ticker in ["SEARCH", "HEALTH", "API", "STATIC", "DOWNLOAD"]:
        return redirect(url_for('home'))
        
    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        return redirect(url_for('home'))
    
    from flask import g
    g.is_landing_page = True
    
    keys = core.all_metric_keys(df)
    available = [{"key": k, "label": core.METRIC_LABELS.get(k, k), "desc": core.METRIC_DESC.get(k, "")} for k in keys]
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else time.time()
    last_update_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
    
    is_embedded = request.args.get('embed') == '1'
    company_name = str(row.iloc[0].get('Security', ticker))

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
    for _, row in df.iterrows():
        sym, sec = str(row.get('Symbol') or ''), str(row.get('Security') or '')
        if q in sym.lower() or q in sec.lower():
            candidates.append({'symbol': sym, 'name': sec})
        if len(candidates) >= 12: break
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

    # Background override
    bg_path = None
    session_bg = request.form.get('bg_path') or ''
    if session_bg and os.path.exists(session_bg):
        bg_path = session_bg

    img = core.render_stock_card(row.iloc[0], selected, layout_mode, watermark, bg_path=bg_path)
    
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
    if ticker:
        df = core.load_df()
        row = df[df['Symbol'] == ticker]
        if not row.empty:
            company_name = str(row.iloc[0].get('Security', ticker))
            
    return render_template(
        'display_result.html', 
        filename=filename, 
        is_embedded=is_embedded,
        ticker=ticker,
        company_name=company_name
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

if __name__ == '__main__':
    saas_logic.init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
