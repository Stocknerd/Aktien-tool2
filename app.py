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
            'name': core.get_clean_name(row.iloc[0]),
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
            'name': core.get_clean_name(r)
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
        top_stocks=top_stocks,
        ticker=request.args.get('ticker')
    )

@app.route('/dividenden-kalender')
def dividend_calendar_page():
    is_embedded = request.args.get('embed') == '1'
    return render_template('dividend_calendar.html', is_embedded=is_embedded)

@app.route('/api/dividenden-kalender')
def api_dividend_calendar():
    df = core.load_df()
    
    # Helper to safely convert to float (must reject inf/nan for JSON)
    import math
    def safe_float(val, default=0):
        try:
            if pd.notna(val):
                v = float(str(val).replace(',', '.'))
                if math.isfinite(v):
                    return round(v, 2)
        except:
            pass
        return default
    
    # Show ALL dividend-paying stocks (yield > 0), not just those with ex-date
    dy_col = pd.to_numeric(df.get('Dividendenrendite', pd.Series(dtype=float)), errors='coerce')
    df_div = df[dy_col > 0].copy()
    
    # Sort: stocks with upcoming ex-dates first, then by yield
    has_ex = df_div['Ex-Dividenden-Datum'].notna() if 'Ex-Dividenden-Datum' in df_div.columns else pd.Series(False, index=df_div.index)
    df_div['_sort_key'] = (~has_ex).astype(int)
    df_div = df_div.sort_values(['_sort_key', 'Ex-Dividenden-Datum'], ascending=[True, True])
    
    results = []
    for _, r in df_div.iterrows():
        dy = safe_float(r.get('Dividendenrendite'))
        if dy <= 0:
            continue
        
        amt = safe_float(r.get('Dividenden-Betrag'))
        kgv = safe_float(r.get('KGV'), None)
        kuv = safe_float(r.get('KUV'), None)
        mcap = safe_float(r.get('Marktkapitalisierung'), None)
        
        ex_date = ''
        ex_month = 0
        if 'Ex-Dividenden-Datum' in r.index and pd.notna(r.get('Ex-Dividenden-Datum')):
            ex_raw = str(r['Ex-Dividenden-Datum'])
            if len(ex_raw) >= 10 and ex_raw[4] == '-':
                ex_date = ex_raw
                try:
                    ex_month = int(ex_raw[5:7])
                except:
                    pass
        
        # Normalize sector names
        sector = str(r.get('Sektor', '')) if pd.notna(r.get('Sektor')) else ''
        
        results.append({
            'symbol': str(r['Symbol']),
            'name': core.get_clean_name(r),
            'ex_date': ex_date,
            'ex_month': ex_month,
            'div_yield': dy,
            'amount': amt,
            'currency': str(r.get('Währung', 'EUR')) if pd.notna(r.get('Währung')) else 'USD',
            'sector': sector,
            'region': str(r.get('Region', '')) if pd.notna(r.get('Region')) else '',
            'kgv': kgv,
            'kuv': kuv,
            'mcap': mcap,
        })
    
    # Deduplicate sectors and sort
    all_sectors = sorted(set(s for s in df[df['Sektor'].notna()]['Sektor'].unique() if s))
    
    return jsonify({'stocks': results, 'sectors': all_sectors, 'total': len(results)})

@app.route('/api/search-all')
def api_search_all():
    index = core.get_search_index()
    results = [{
        'symbol': item['symbol'],
        'name': item['name'],
        'div_yield': item.get('div_yield', 0.0),
        'sector': item.get('sector', '')
    } for item in index]
    return jsonify({'stocks': results})

# ─── Aktien-Screener ─────────────────────────────────────────
@app.route('/screener')
def screener_page():
    is_embedded = request.args.get('embed') == '1'
    return render_template('screener.html', is_embedded=is_embedded)

@app.route('/watchlist')
def watchlist_page():
    is_embedded = request.args.get('embed') == '1'
    return render_template('watchlist.html', is_embedded=is_embedded)


# ─── P2P Dashboard ───────────────────────────────────────────
@app.route('/p2p')
def p2p_dashboard():
    is_embedded = request.args.get('embed') == '1'
    
    # Static data for P2P platforms (could later be fetched from a CSV or API)
    platforms = [
        {
            "id": "mintos", "name": "Mintos", "yield": 11.5, "bonus": "50€ Startbonus",
            "logo": "https://assets.mintos.com/webapp/img/mintos-logo-dark-bg.31e96f8.webp",
            "desc": "Der europäische Marktführer. Riesiges Angebot an Krediten und automatisiertes Investieren.",
            "features": ["Marktführer", "Autoinvest", "Sekundärmarkt"],
            "url": "https://www.mintos.com/de/"
        },
        {
            "id": "bondora", "name": "Bondora (Go & Grow)", "yield": 6.75, "bonus": "5€ Startbonus",
            "logo": "https://bondora.group/wp-content/uploads/2023/11/bondora_logo_black_txt.png",
            "desc": "Die einfachste P2P-Plattform. Tägliche Zinsgutschrift und hohe Liquidität.",
            "features": ["Tägliche Zinsen", "Hohe Liquidität", "Sehr einfach"],
            "url": "https://www.bondora.com/de/"
        },
        {
            "id": "robocash", "name": "Robocash", "yield": 11.0, "bonus": "1% Cashback (30 Tage)",
            "logo": "https://robo.cash/images/logos/logo.svg",
            "desc": "Vollautomatisiert. Fokus auf kurzlaufende Konsumkredite mit Buyback-Garantie.",
            "features": ["100% Autoinvest", "Buyback-Garantie", "Kurze Laufzeiten"],
            "url": "https://robo.cash/"
        },
        {
            "id": "twino", "name": "Twino", "yield": 10.0, "bonus": "20€ Startbonus",
            "logo": "https://cdn.brandfetch.io/idvBItVqiS/theme/dark/logo.svg?c=1bxid64Mup7aczewSAYMX&t=1758849062557",
            "desc": "Etablierter Anbieter aus Lettland mit Fokus auf besicherte Immobilien- und Geschäftskredite.",
            "features": ["Reguliert", "Immobilien", "Buyback-Garantie"],
            "url": "https://www.twino.eu/"
        }
    ]
    
    return render_template('p2p.html', platforms=platforms, is_embedded=is_embedded)

@app.route('/api/screener')
def api_screener():
    df = core.load_df()
    
    import math
    def safe_float(val, default=None):
        try:
            if pd.notna(val):
                v = float(str(val).replace(',', '.'))
                if math.isfinite(v):
                    return round(v, 2)
        except:
            pass
        return default

    def safe_float_pct(val, default=None):
        try:
            if pd.notna(val):
                v = float(str(val).replace(',', '.'))
                if math.isfinite(v):
                    return round(v * 100.0, 2)
        except:
            pass
        return default

    EXCHANGE_RATES_TO_USD = {
        'USD': 1.0,
        'EUR': 1.08,
        'CHF': 1.10,
        'GBP': 1.27,
        'JPY': 0.0064,
        'CAD': 0.73,
        'AUD': 0.66,
        'HKD': 0.128,
        'INR': 0.012,
        'SEK': 0.095,
        'DKK': 0.145,
        'NOK': 0.093,
        'BRL': 0.19,
        'CNY': 0.14,
        'TWD': 0.031,
        'KRW': 0.00073,
        'SGD': 0.74,
        'MXN': 0.059,
        'ZAR': 0.054
    }

    results = []
    # Using specific columns to keep payload small
    for _, r in df.iterrows():
        # Only include stocks that have at least a Symbol
        if pd.isna(r.get('Symbol')):
            continue
            
        sector = str(r.get('Sektor', '')) if pd.notna(r.get('Sektor')) else ''
        region = str(r.get('Region', '')) if pd.notna(r.get('Region')) else ''
        
        mcap = safe_float(r.get('Marktkapitalisierung'))
        # Support both German/English column naming variations for Währung
        currency = str(r.get('Währung') or r.get('W\u00e4hrung') or 'USD').strip().upper()
        if not currency or currency == 'NAN':
            currency = 'USD'
            
        mcap_usd = None
        if mcap is not None:
            rate = EXCHANGE_RATES_TO_USD.get(currency, 1.0)
            mcap_usd = round(mcap * rate, 2)
        
        results.append({
            'symbol': str(r['Symbol']),
            'name': core.get_clean_name(r),
            'sector': sector,
            'region': region,
            'kgv': safe_float(r.get('KGV')),
            'div_yield': safe_float(r.get('Dividendenrendite')),
            'umsatz_wachstum': safe_float_pct(r.get('Umsatzwachstum 3J (erwartet)')),
            'netto_marge': safe_float_pct(r.get('Nettomarge')) if pd.notna(r.get('Nettomarge')) else safe_float_pct(r.get('Operative Marge')),
            'op_marge': safe_float_pct(r.get('Operative Marge')),
            'roe': safe_float_pct(r.get('Eigenkapitalrendite')),
            'kbv': safe_float(r.get('KBV')),
            'mcap': mcap,
            'mcap_usd': mcap_usd,
            'currency': currency,
            'rating': str(r.get('Recommendation Key', '')) if pd.notna(r.get('Recommendation Key')) else ''
        })
        
    all_sectors = sorted(set(s for s in df[df['Sektor'].notna()]['Sektor'].unique() if s))
    
    return jsonify({'stocks': results, 'sectors': all_sectors, 'total': len(results)})

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
        name_col = 'resolved_name' if 'resolved_name' in df.columns else ('Security' if 'Security' in df.columns else '')
        if name_col:
            match = df[df[name_col].str.contains(ticker, case=False, na=False)]
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
    company_name = core.get_clean_name(row.iloc[0]) # Use clean name for SEO title

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
    if not q: return jsonify([])
    candidates = []
    def normalize(s):
        return str(s).lower().replace('-', ' ').replace('.', ' ').strip()
    q_norm = normalize(q)
    index = core.get_search_index()
    for item in index:
        if q_norm in item['norm_sym'] or q_norm in item['norm_name'] or q_norm in item['norm_lng']:
            candidates.append({
                'symbol': item['symbol'], 
                'name': item['name'],
                'div_yield': item.get('div_yield', 0.0),
                'sector': item.get('sector', '')
            })
        if len(candidates) >= 15: break
    return jsonify(candidates)

# ─── Dividend Calculator ────────────────────────────────────────
@app.route('/dividend-rechner')
def dividend_rechner():
    is_embedded = request.args.get('embed') == '1'
    return render_template('dividend_calc.html', is_embedded=is_embedded)

@app.route('/api/calculate-dividend')
def calculate_dividend():
    ticker = request.args.get('ticker')
    amount_str = request.args.get('amount', '0')
    shares_str = request.args.get('shares', '0')
    
    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        return jsonify({'error': 'Ticker not found'}), 404
    
    row = row.iloc[0]
    
    # Parse Yield
    div_yield_str = str(row.get('Dividendenrendite', '0'))
    div_yield = 0.0
    try:
        div_yield = float(div_yield_str.replace('%', '').replace(',', '.').strip())
    except: pass
    
    # Parse Price
    price_val = row.get('Vortagesschlusskurs', 0)
    try:
        if isinstance(price_val, str):
            price = float(price_val.replace(',', '.').strip())
        else:
            price = float(price_val)
    except:
        price = 0.0
        
    amount = 0.0
    shares = 0.0
    
    try:
        if shares_str and float(shares_str) > 0:
            shares = float(shares_str)
            amount = shares * price
        else:
            amount = float(amount_str)
            shares = amount / price if price > 0 else 0
    except:
        pass

    annual = amount * (div_yield / 100)
        
    return jsonify({
        'symbol': ticker,
        'yield': round(div_yield, 2),
        'price': round(price, 2),
        'shares': round(shares, 2),
        'amount': round(amount, 2),
        'annual': round(annual, 2),
        'monthly': round(annual / 12, 2)
    })

@app.route('/generate_image', methods=['POST'])
def generate_image():
    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok:
        flash(msg, "danger")
        return redirect(url_for('home'))

    raw_ticker = (request.form.get('ticker') or '').strip()
    ticker = raw_ticker.upper().replace(' ', '')
    if not ticker:
        flash("Bitte einen Ticker eingeben.", "warning")
        return redirect(url_for('home'))

    selected = request.form.getlist('metrics') or core.DEFAULT_METRICS
    layout_mode = (request.form.get('layout') or 'default').lower()
    watermark = (request.form.get('watermark') or '').strip()

    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        # Try to resolve by name
        resolved = False
        for col in ['resolved_name', 'Security', 'Langname']:
            if col in df.columns:
                match = df[df[col].str.contains(raw_ticker, case=False, na=False)]
                if not match.empty:
                    row = match.iloc[[0]]
                    ticker = row.iloc[0]['Symbol']
                    resolved = True
                    break
        if not resolved:
            flash(f"Ticker '{raw_ticker}' nicht gefunden.", "danger")
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
        from flask import session
        session['ai_verdict'] = ai_verdict
    else:
        from flask import session
        session.pop('ai_verdict', None)

    img = core.render_stock_card(row.iloc[0], selected, layout_mode, watermark, bg_path=bg_path, ai_verdict=ai_verdict)
    
    filename = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(core.OUT_DIR, filename)
    img.convert('RGB').save(path, format='PNG')
    
    saas_logic.log_usage(token, "render")

    is_embedded_form = request.form.get('is_embedded') == '1'
    kwargs = {'filename': filename, 'ticker': ticker}
    if is_embedded_form or request.args.get('embed') == '1':
        kwargs['embed'] = '1'
    return redirect(url_for('display_result', **kwargs))

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
    if not ticker:
        base = os.path.basename(filename)
        if "_" in base:
            ticker = base.split("_")[0].upper()
            
    company_name = ""
    related_stocks = []
    stock_data = {}
    if ticker:
        df = core.load_df()
        row = df[df['Symbol'] == ticker]
        if not row.empty:
            company_name = core.get_clean_name(row.iloc[0])
            related_stocks = get_related_stocks(ticker)
            # Convert row to dict safely, converting pd.NA/NaN to None
            stock_data = {k: (None if pd.isna(v) else v) for k, v in row.iloc[0].to_dict().items()}
            
    from flask import session
    ai_verdict = session.get('ai_verdict', "")
            
    return render_template(
        'display_result.html', 
        filename=filename,
        ticker=ticker,
        company_name=company_name,
        related_stocks=related_stocks,
        ai_verdict=ai_verdict,
        is_embedded=is_embedded,
        stock_data=stock_data
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
    
    # Try resolving t1 if not found by Symbol
    row1 = df[df['Symbol'] == t1]
    if row1.empty:
        for col in ['resolved_name', 'Security', 'Langname']:
            if col in df.columns:
                match = df[df[col].str.contains(t1, case=False, na=False)]
                if not match.empty:
                    row1 = match.iloc[[0]]
                    t1 = row1.iloc[0]['Symbol']
                    break
                    
    # Try resolving t2 if not found by Symbol
    row2 = df[df['Symbol'] == t2]
    if row2.empty:
        for col in ['resolved_name', 'Security', 'Langname']:
            if col in df.columns:
                match = df[df[col].str.contains(t2, case=False, na=False)]
                if not match.empty:
                    row2 = match.iloc[[0]]
                    t2 = row2.iloc[0]['Symbol']
                    break

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
    kwargs = {'filename': fname, 't1': t1, 't2': t2}
    if m_param:
        kwargs['m_param'] = m_param
    if is_embedded or request.args.get('embed') == '1':
        kwargs['embed'] = '1'
    return redirect(url_for('compare_result', **kwargs))

@app.route('/compare/result/<path:filename>')
def compare_result(filename):
    is_embedded = request.args.get('embed') == '1'
    t1 = request.args.get('t1', '')
    t2 = request.args.get('t2', '')
    m_param = request.args.get('m_param', '')
    return render_template('compare_result.html', fname=filename, t1=t1, t2=t2, m_param=m_param, is_embedded=is_embedded)

# ─── SEO Sitemap (Hebel 1) ─────────────────────────────────
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.static_folder, 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')


# ─── Add Ticker Endpoint (Hebel 2) ──────────────────────────
@app.route('/api/add-ticker', methods=['POST'])
def api_add_ticker():
    try:
        data = request.json or {}
        ticker_symbol = data.get('ticker', '').strip().upper()
        if not ticker_symbol:
            return jsonify({"status": "error", "message": "Kein Ticker angegeben."}), 400
            
        import re
        if not re.match(r'^[A-Z0-9.\-]+$', ticker_symbol):
            return jsonify({"status": "error", "message": "Ungültiger Ticker. Erlaubt sind Buchstaben, Zahlen, Punkte und Bindestriche."}), 400
            
        df_existing = core.load_df()
        if not df_existing.empty and ticker_symbol in df_existing['Symbol'].astype(str).str.upper().values:
            row = df_existing[df_existing['Symbol'].astype(str).str.upper() == ticker_symbol].iloc[0]
            
            # Extract div yield safely
            dy = row.get('Dividendenrendite')
            try:
                dy_val = float(str(dy).replace(',', '.')) if pd.notna(dy) else 0.0
            except:
                dy_val = 0.0
                
            return jsonify({
                "status": "success", 
                "message": f"Aktie '{ticker_symbol}' existiert bereits.",
                "stock": {
                    "symbol": str(row.get('Symbol')),
                    "name": core.get_clean_name(row),
                    "div_yield": round(dy_val, 2),
                    "sector": str(row.get('Sektor', '')) if pd.notna(row.get('Sektor')) else ''
                }
            })
            
        from curl_cffi import requests as curl_requests
        import yfinance as yf
        
        session = curl_requests.Session(impersonate="chrome")
        ticker_obj = yf.Ticker(ticker_symbol, session=session)
        info = ticker_obj.info
        
        if not info or not info.get('symbol') or (not info.get('shortName') and not info.get('longName')):
            return jsonify({"status": "error", "message": f"Ticker '{ticker_symbol}' wurde auf Yahoo Finance nicht gefunden."}), 404
            
        resolved_name = info.get('longName') or info.get('shortName') or ticker_symbol
        sector = info.get('sector') or ''
        
        new_row = {
            "Symbol": ticker_symbol,
            "Security": resolved_name,
            "GICS Sector": sector,
            "valid_yahoo_ticker": ticker_symbol,
            "resolved_name": resolved_name,
            "resolved_exchange": info.get("exchange", ""),
            "resolved_score": 1.0,
            "SourceIndex": "MANUAL",
            "Sektor": sector,
            "Währung": info.get("currency", "USD"),
            "Region": info.get("country", ""),
            "Branche": info.get("industry", ""),
            "Vortagesschlusskurs": info.get("previousClose") or info.get("currentPrice"),
            "Dividendenrendite": info.get("dividendYield"),
            "Ausschüttungsquote": info.get("payoutRatio", 0) * 100 if info.get("payoutRatio") else None,
            "KGV": info.get("trailingPE"),
            "Forward PE": info.get("forwardPE"),
            "KBV": info.get("priceToBook"),
            "KUV": info.get("priceToSalesTrailing12Months"),
            "PEG-Ratio": info.get("pegRatio"),
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "EBIT": info.get("ebit") or info.get("ebitda"),
            "Bruttomarge": info.get("grossMargins", 0) * 100 if info.get("grossMargins") else None,
            "Operative Marge": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None,
            "Nettomarge": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None,
            "Marktkapitalisierung": info.get("marketCap"),
            "Free Cashflow": info.get("freeCashflow"),
            "Free Cashflow Yield": (info.get("freeCashflow") / info.get("marketCap")) if info.get("freeCashflow") and info.get("marketCap") else None,
            "Operativer Cashflow": info.get("operatingCashflow"),
            "Eigenkapitalrendite": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
            "Return on Assets": info.get("returnOnAssets", 0) * 100 if info.get("returnOnAssets") else None,
            "ROIC": None,
            "Umsatzwachstum 3J (erwartet)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None,
            "Analyst Mean Target": info.get("targetMeanPrice"),
            "Analyst High Target": info.get("targetHighPrice"),
            "Analyst Low Target": info.get("targetLowPrice"),
            "Current Price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "Recommendation Key": info.get("recommendationKey"),
            "Number of Analysts": info.get("numberOfAnalystOpinions"),
            "Ex-Dividenden-Datum": datetime.fromtimestamp(info.get("exDividendDate")).strftime("%Y-%m-%d") if info.get("exDividendDate") else None,
            "Dividenden-Frequenz": info.get("dividendRate"),
            "Dividenden-Betrag": info.get("dividendRate") or info.get("trailingAnnualDividendRate"),
            "Abfragedatum": datetime.now().strftime("%Y-%m-%d"),
            "Datenquelle": "Yahoo Finance (Manual)",
            "Datenqualität": 1.0,
            "Fehlende_Kennzahlen": 0
        }
        
        # Write to ticker_resolved.csv
        resolved_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ticker_resolved.csv")
        if os.path.exists(resolved_csv_path):
            try:
                df_res = pd.read_csv(resolved_csv_path)
                df_res = df_res[df_res['valid_yahoo_ticker'].astype(str).str.upper() != ticker_symbol]
                new_res = pd.DataFrame([{
                    "Symbol": ticker_symbol,
                    "Security": resolved_name,
                    "GICS Sector": sector,
                    "valid_yahoo_ticker": ticker_symbol,
                    "resolved_name": resolved_name,
                    "resolved_exchange": info.get("exchange", ""),
                    "resolved_score": 1.0,
                    "SourceIndex": "MANUAL",
                    "Sektor": sector
                }])
                df_res = pd.concat([df_res, new_res], ignore_index=True)
                df_res.to_csv(resolved_csv_path, index=False)
            except Exception as e_res:
                print(f"⚠️ [WARN] Error writing to data/ticker_resolved.csv: {e_res}")
                
        # Write to stock_data.csv (core.CSV_FILE)
        df_stock = core.load_df()
        if not df_stock.empty and 'Symbol' in df_stock.columns:
            df_stock = df_stock[df_stock['Symbol'].astype(str).str.upper() != ticker_symbol]
            
        new_stock_df = pd.DataFrame([new_row])
        df_stock = pd.concat([df_stock, new_stock_df], ignore_index=True)
        df_stock.to_csv(core.CSV_FILE, index=False)
        
        # Reset local cache
        with core._df_cache_lock:
            core._CACHED_DF = None
            core._CACHED_MTIME = 0.0
            core._SEARCH_INDEX = None
            
        # Re-generate sitemap
        try:
            from generate_sitemap import generate_sitemap
            generate_sitemap(csv_path=core.CSV_FILE, output_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "sitemap.xml"))
        except Exception as e_sm:
            print(f"⚠️ [WARN] Sitemap generation failed in adder: {e_sm}")
            
        div_yield_val = info.get("dividendYield") or 0.0
        try:
            div_yield_val = float(div_yield_val)
        except:
            div_yield_val = 0.0
            
        return jsonify({
            "status": "success",
            "message": f"Aktie '{ticker_symbol}' erfolgreich hinzugefügt.",
            "stock": {
                "symbol": ticker_symbol,
                "name": resolved_name,
                "div_yield": round(div_yield_val, 2),
                "sector": sector
            }
        })
    except Exception as e:
        print(f"❌ [ERROR] in /api/add-ticker: {e}")
        return jsonify({"status": "error", "message": f"Serverfehler beim Hinzufügen der Aktie: {str(e)}"}), 500

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
