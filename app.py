from flask import (
    Flask, render_template, request, jsonify, Response,
    redirect, url_for, send_from_directory, flash, render_template_string, session
)
import os, pandas as pd, io, time, threading
import saas_logic
import core
import tasks
import ai_logic
from datetime import datetime
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-aktien-tool'


MAIN_DOMAIN_EQUIVALENTS = {
    '/': 'https://schatzsuche40.de/aktien-tool/',
    '/screener': 'https://schatzsuche40.de/screener/',
    '/dividenden-kalender': 'https://schatzsuche40.de/dividenden-kalender/',
    '/dividend-rechner': 'https://schatzsuche40.de/dividend-rechner/',
    '/p2p': 'https://schatzsuche40.de/p2p-dashboard/',
    '/compare': 'https://schatzsuche40.de/aktien-vergleichstool/',
}


def compute_canonical_url():
    host = request.host.split(':', 1)[0].lower()
    is_emb = request.args.get('embed') == '1' or request.form.get('is_embedded') == '1'
    path = request.path or '/'

    if host == 'compare.schatzsuche40.de' and path in ('/', '/compare'):
        return 'https://schatzsuche40.de/aktien-vergleichstool/' if is_emb else 'https://compare.schatzsuche40.de/'

    if is_emb and path in MAIN_DOMAIN_EQUIVALENTS and not request.args.get('ticker'):
        return MAIN_DOMAIN_EQUIVALENTS[path]

    if request.endpoint in ('stock_landing', 'display_result'):
        sym = ((request.view_args or {}).get('ticker') or request.args.get('ticker') or '').upper().strip()
        if not sym and request.endpoint == 'display_result':
            fname = os.path.basename((request.view_args or {}).get('filename', ''))
            if fname.startswith('cache_'):
                parts = fname[len('cache_'):].rsplit('_', 1)
                if parts:
                    sym = parts[0].upper().strip()
            elif '_' in fname:
                sym = fname.split('_', 1)[0].upper().strip()
        if sym:
            return f'https://tool.schatzsuche40.de/analyse/{sym}'

    return request.base_url


@app.context_processor
def inject_tracking_config():
    premium_cta_url = os.environ.get('PREMIUM_CTA_URL', '').strip() or os.environ.get('NEWSLETTER_URL', '').strip() or 'https://schatzsuche40.de/newsletter/'
    newsletter_url = os.environ.get('NEWSLETTER_URL', '').strip() or premium_cta_url
    return {
        'analytics_measurement_id': os.environ.get('GA_MEASUREMENT_ID', '').strip(),
        'analytics_container_id': os.environ.get('GTM_CONTAINER_ID', '').strip(),
        'consent_storage_key': os.environ.get('ANALYTICS_CONSENT_KEY', 'qc_cookie_consent').strip() or 'qc_cookie_consent',
        'premium_cta_url': premium_cta_url,
        'newsletter_url': newsletter_url,
        'show_monetization_cta': os.environ.get('SHOW_CTA_BANNER', 'false').lower() == 'true',
        'canonical_url': compute_canonical_url(),
    }

# SaaS Guest Auth. Ensure runtime guest token is always initialized in SQLite.
GUEST_TOKEN = os.environ.get("SCHATZSUCHE_GUEST_TOKEN", "b2831286e14844faa0782f69d4649825").strip() or "b2831286e14844faa0782f69d4649825"
os.environ.setdefault("SCHATZSUCHE_GUEST_TOKEN", GUEST_TOKEN)
saas_logic.init_db()


def build_analysis_title(company_name, ticker, max_length=60):
    """Build a bounded SEO title while preserving company, ticker and search intent."""
    ticker = " ".join(str(ticker or "").split()).upper()
    company_name = " ".join(str(company_name or ticker or "Aktie").split())
    analysis_suffix = f" ({ticker}) - Aktienanalyse" if ticker else " - Aktienanalyse"
    brand_suffix = " | Schatzsuche 4.0"
    branded_title = f"{company_name}{analysis_suffix}{brand_suffix}"
    if len(branded_title) <= max_length:
        return branded_title

    available_company_length = max_length - len(analysis_suffix)
    if available_company_length < 2:
        fallback = f"{ticker} - Aktienanalyse" if ticker else "Aktienanalyse"
        return fallback[:max_length]
    if len(company_name) > available_company_length:
        company_name = company_name[: available_company_length - 1].rstrip(" .,-_") + "…"
    return f"{company_name}{analysis_suffix}"


_TRACKED_COMPLETION_EVENTS = frozenset({'analysis_completed', 'comparison_completed'})


def mark_pending_completion(event_name, result_id):
    """Bind one completion event to the result created in this browser session."""
    if event_name not in _TRACKED_COMPLETION_EVENTS:
        raise ValueError(f"Unsupported completion event: {event_name}")
    key = f's40_pending_{event_name}'
    result_id = os.path.basename(str(result_id))
    raw_pending = session.get(key, [])
    pending = [raw_pending] if isinstance(raw_pending, str) else list(raw_pending)
    pending = [os.path.basename(str(item)) for item in pending if item]
    if result_id and result_id not in pending:
        pending.append(result_id)
    session[key] = pending[-8:]


def consume_pending_completion(event_name, result_id):
    """Consume a matching completion marker exactly once."""
    if event_name not in _TRACKED_COMPLETION_EVENTS:
        return ''
    key = f's40_pending_{event_name}'
    expected = os.path.basename(str(result_id))
    raw_pending = session.get(key, [])
    pending = [raw_pending] if isinstance(raw_pending, str) else list(raw_pending)
    pending = [os.path.basename(str(item)) for item in pending if item]
    if not expected or expected not in pending:
        return ''
    pending.remove(expected)
    if pending:
        session[key] = pending
    else:
        session.pop(key, None)
    return expected


def get_effective_token():
    t = (request.form.get('token') or request.args.get('token') or '').strip()
    if not t or not saas_logic.get_token_info(t):
        return GUEST_TOKEN
    return t

import ops_middleware
ops_middleware.setup_ops(app, core.CSV_FILE)

COMPARE_HOST = 'compare.schatzsuche40.de'


def current_host():
    return request.host.split(':', 1)[0].lower()


@app.before_request
def enforce_compare_host_boundary():
    """Keep analysis tools off the dedicated comparison hostname."""
    if current_host() != COMPARE_HOST:
        return None

    path = request.path
    if request.method in {'GET', 'HEAD'}:
        if path == '/compare':
            return redirect('https://compare.schatzsuche40.de/', code=301)
        if path in {
            '/', '/robots.txt', '/sitemap.xml', '/llms.txt', '/api/search-all', '/search', '/googlef3be5002fc1d35b1.html'
        } or path.startswith(
            ('/compare/result/', '/output/', '/static/', '/download/')
        ):
            return None
        target = f"https://tool.schatzsuche40.de{path}"
        if request.query_string:
            target = f"{target}?{request.query_string.decode('utf-8', errors='ignore')}"
        return redirect(target, code=301)

    if request.method == 'POST' and path == '/compare/generate':
        return None
    return jsonify({'error': 'Not found'}), 404


# ─── API Cost Shield & Thread-Safe IP Rate Limiting ──────────
RATE_LIMIT_ERROR_MSG = "Bitte warte einen kurzen Moment – zu viele Anfragen in kurzer Zeit."
_RATE_LIMIT_BUCKETS = {}
_rate_limit_lock = threading.Lock()


def reset_rate_limits():
    with _rate_limit_lock:
        _RATE_LIMIT_BUCKETS.clear()


def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    xri = request.headers.get('X-Real-IP', '')
    if xri:
        return xri.strip()
    return request.remote_addr or '127.0.0.1'


def _check_and_record_rate_limit(bucket_key, windows):
    """
    windows: list of (window_seconds, max_requests) tuples.
    Returns True if allowed (and records timestamp), False if rate limit exceeded.
    """
    now = time.time()
    max_window = max(w for w, _ in windows)
    with _rate_limit_lock:
        timestamps = _RATE_LIMIT_BUCKETS.get(bucket_key, [])
        timestamps = [t for t in timestamps if (now - t) < max_window]
        for win_sec, max_req in windows:
            recent_count = sum(1 for t in timestamps if (now - t) < win_sec)
            if recent_count >= max_req:
                _RATE_LIMIT_BUCKETS[bucket_key] = timestamps
                return False
        timestamps.append(now)
        _RATE_LIMIT_BUCKETS[bucket_key] = timestamps
        return True


@app.after_request
def apply_seo_and_embed_headers(response):
    if request.args.get('embed') == '1' or request.path.startswith(('/result/', '/compare/result/')):
        response.headers['X-Robots-Tag'] = 'noindex, follow'
    return response


@app.before_request
def enforce_expensive_endpoint_rate_limits():
    """Rate-limit only expensive AI & manual POST generation endpoints; never throttle normal GET crawls."""
    if app.config.get('TESTING') and not app.config.get('ENABLE_RATE_LIMIT_IN_TESTS'):
        return None

    path = request.path or '/'
    ip = get_client_ip()

    # 1. AI Analysis endpoints: max 6 req/min and 25 req/hour per IP
    if path in ('/api/ai-analysis', '/ai_analysis'):
        if not _check_and_record_rate_limit(f"ai:{ip}", [(60, 6), (3600, 25)]):
            return jsonify({
                "status": "error",
                "error": RATE_LIMIT_ERROR_MSG,
                "message": RATE_LIMIT_ERROR_MSG,
            }), 429
        return None

    # 2. Manual POST generation endpoints: max 15 POST req/min per IP
    if request.method == 'POST' and path in ('/', '/generate_image', '/compare/generate', '/api/add-ticker', '/api/v1/render'):
        if request.form.get('ai_insight') == '1':
            if not _check_and_record_rate_limit(f"ai:{ip}", [(60, 6), (3600, 25)]):
                return jsonify({
                    "status": "error",
                    "error": RATE_LIMIT_ERROR_MSG,
                    "message": RATE_LIMIT_ERROR_MSG,
                }), 429
        if not _check_and_record_rate_limit(f"post:{ip}", [(60, 15)]):
            return jsonify({
                "status": "error",
                "error": RATE_LIMIT_ERROR_MSG,
                "message": RATE_LIMIT_ERROR_MSG,
            }), 429
        return None

    return None

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
    if row.empty:
        return []
    
    # Try multiple columns for categorization safely
    sector = None
    for col in ('GICS Sector', 'Sektor', 'Branche', 'Sector'):
        if col in row.columns:
            val = row.iloc[0].get(col)
            if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'nan':
                sector = val
                break

    other_df = df[df['Symbol'] != ticker]
    if sector:
        mask = pd.Series(False, index=other_df.index)
        for col in ('GICS Sector', 'Sektor', 'Branche', 'Sector'):
            if col in other_df.columns:
                mask = mask | (other_df[col] == sector)
        related = other_df[mask].head(limit)
        if len(related) < 4:
            extra = other_df[~mask].head(limit - len(related))
            related = pd.concat([related, extra]).head(limit)
    else:
        related = other_df.head(limit)
    
    res = []
    for _, r in related.iterrows():
        # Get formatted values safely
        kgv_disp = core.display_value('KGV', r)
        div_yield_disp = core.display_value('Dividendenrendite', r)
        marge_disp = core.display_value('Nettomarge', r) if pd.notna(r.get('Nettomarge')) else core.display_value('Operative Marge', r)

        res.append({
            'symbol': r['Symbol'],
            'name': core.get_clean_name(r),
            'kgv': kgv_disp,
            'div_yield': div_yield_disp,
            'margin': marge_disp
        })
    return res

# Thread-safe in-memory cache definitions
import threading
import json
import re

_STOCK_LANDING_CACHE = {}
_stock_landing_cache_lock = threading.Lock()


def get_broker_recommendation(ticker, stock_name, currency='EUR'):
    """Return contextual primary & secondary partner broker recommendations for a given stock."""
    t_up = (ticker or '').upper().strip()
    name = (stock_name or t_up or 'diese Aktie').strip()
    curr = (currency or '').upper().strip()

    is_de_sparplan = t_up.endswith('.DE') or t_up.endswith('.F') or (curr == 'EUR' and '.' in t_up)

    if is_de_sparplan:
        primary = {
            'name': 'Scalable Capital',
            'role_badge': '⭐ Sparplan-Favorit (DE & Europa)',
            'headline': f'0 € Sparplan für {name}',
            'description': 'Kostenlose Depotführung, Aktien-Sparpläne ab 1 € Ausführungsrate und Top-Zinsen auf dein Guthaben.',
            'button_text': 'Depot eröffnen & Sparplan starten *',
            'url': 'https://www.financeads.net/tc.php?t=47128C142835927T',
            'btn_class': 'btn-primary',
            'border_color': 'rgba(16, 185, 129, 0.45)',
            'bg_color': 'rgba(16, 185, 129, 0.08)',
        }
        secondary = {
            'name': 'Consorsbank',
            'role_badge': '💡 Vollbank & Dividenden-Favorit',
            'headline': f'Dividenden von {name} automatisch reinvestieren',
            'description': 'Umfassendes Direktbank-Depot mit automatischer Dividenden-Wiederanlage und attraktiver Neukundenprämie.',
            'button_text': '50 € Prämie & Sparplan-Angebot *',
            'url': 'https://www.financeads.net/tc.php?t=47128C15212339T',
            'btn_class': 'btn-outline-info',
            'border_color': 'rgba(56, 189, 248, 0.35)',
            'bg_color': 'rgba(15, 23, 42, 0.55)',
        }
    else:
        primary = {
            'name': 'CapTrader',
            'role_badge': '🌎 Profi-Trader & US-Börsen-Favorit',
            'headline': f'Günstig weltweit & US-Optionen für {name} handeln',
            'description': 'Direkter Börsenzugang an über 150 Handelsplätzen weltweit (NYSE, NASDAQ, Asien) zu minimalen Ordergebühren.',
            'button_text': 'Zu CapTrader *',
            'url': 'https://www.financeads.net/tc.php?t=47128C46917042T',
            'btn_class': 'btn-success',
            'border_color': 'rgba(16, 185, 129, 0.45)',
            'bg_color': 'rgba(16, 185, 129, 0.08)',
        }
        secondary = {
            'name': 'Scalable Capital',
            'role_badge': '⭐ Sparplan-Favorit ab 1 €',
            'headline': f'0 € Sparplan für {name}',
            'description': 'Investiere bequem per monatlichem Aktien-Sparplan ab 1 € oder handle Einzelorders ab 0,99 € im Prime-Broker.',
            'button_text': 'Depot eröffnen & Sparplan starten *',
            'url': 'https://www.financeads.net/tc.php?t=47128C142835927T',
            'btn_class': 'btn-outline-primary',
            'border_color': 'rgba(59, 130, 246, 0.35)',
            'bg_color': 'rgba(15, 23, 42, 0.55)',
        }

    return {'primary': primary, 'secondary': secondary}


def _compute_stock_seo_data(ticker, row):
    stock_name = core.get_clean_name(row) or ticker
    kgv_disp = core.display_value('KGV', row)
    div_yield_disp = core.display_value('Dividendenrendite', row)
    op_marge_disp = core.display_value('Operative Marge', row)
    netto_marge_disp = core.display_value('Nettomarge', row)
    margin_disp = netto_marge_disp if pd.notna(row.get('Nettomarge')) else op_marge_disp
    price_disp = core.display_value('Current Price', row) if pd.notna(row.get('Current Price')) else core.display_value('Vortagesschlusskurs', row)
    target_disp = core.display_value('Analyst Mean Target', row)
    fpe_disp = core.display_value('Forward PE', row)
    roe_disp = core.display_value('Eigenkapitalrendite', row)

    raw_curr = row.get('Währung')
    currency = str(raw_curr).strip() if pd.notna(raw_curr) and str(raw_curr).strip() not in ('', 'nan', 'None') else 'EUR'

    sector = 'Aktienmarkt'
    for col in ('Sektor', 'GICS Sector', 'Branche', 'Sector'):
        val = row.get(col)
        if pd.notna(val) and str(val).strip() and str(val).strip().lower() not in ('nan', 'none'):
            sector = str(val).strip()
            break

    seo_title = f"{stock_name} ({ticker}) Aktie: Analyse, KGV, Dividende & Kursziel | Schatzsuche 4.0"

    metric_snippets = []
    if kgv_disp not in ('–', 'N/A', '', 'nan'):
        metric_snippets.append(f"KGV: {kgv_disp}")
    if div_yield_disp not in ('–', 'N/A', '', 'nan'):
        metric_snippets.append(f"Dividendenrendite: {div_yield_disp}")
    if metric_snippets:
        metrics_str = ", ".join(metric_snippets)
        seo_description = (
            f"Aktuelle Fundamentalanalyse zur {stock_name} ({ticker}) Aktie ({metrics_str}): "
            f"KGV, Dividendenrendite, Margen, Analysten-Kursziel & kostenlose Infografik auf einen Blick."
        )
    else:
        seo_description = (
            f"Aktuelle Fundamentalanalyse zur {stock_name} ({ticker}) Aktie: "
            f"KGV, Dividendenrendite, Margen, Analysten-Kursziel & kostenlose Infografik auf einen Blick."
        )

    if price_disp not in ('–', 'N/A', '', 'nan'):
        s1 = f"Die {stock_name} Aktie (Ticker: {ticker}) ist im Sektor {sector} tätig und notiert aktuell bei einem Kurs von {price_disp} {currency}."
    else:
        s1 = f"Die {stock_name} Aktie (Ticker: {ticker}) ist ein börsennotiertes Unternehmen aus dem Sektor {sector}."

    marge_for_text = op_marge_disp if op_marge_disp not in ('–', 'N/A', '', 'nan') else margin_disp
    s2 = (
        f"In der aktuellen Fundamentalanalyse weist {stock_name} ein Kurs-Gewinn-Verhältnis (KGV) von {kgv_disp}, "
        f"eine Dividendenrendite von {div_yield_disp} sowie eine operative Marge von {marge_for_text} auf."
    )
    if target_disp not in ('–', 'N/A', '', 'nan'):
        s3 = f"Das durchschnittliche Analysten-Kursziel liegt derzeit bei {target_disp} {currency} (erwartetes KGV: {fpe_disp}, Eigenkapitalrendite: {roe_disp})."
    else:
        s3 = f"Ergänzende Bewertungskennzahlen zeigen ein erwartetes KGV von {fpe_disp} sowie eine Eigenkapitalrendite (ROE) von {roe_disp}."
    seo_summary_text = f"{s1} {s2} {s3}"

    ordered_keys = list(core.DEFAULT_METRICS) + [k for k in core.METRIC_LABELS.keys() if k not in core.DEFAULT_METRICS]
    fundamental_metrics = []
    for k in ordered_keys:
        val_str = core.display_value(k, row)
        if k in core.DEFAULT_METRICS or (k in row and pd.notna(row.get(k)) and val_str not in ('–', 'N/A', '', 'nan')):
            fundamental_metrics.append({
                'key': k,
                'label': core.METRIC_LABELS.get(k, k),
                'value': val_str,
                'desc': core.METRIC_DESC.get(k, '')
            })

    stock_data = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
    stock_data['kgv_disp'] = kgv_disp
    stock_data['div_yield_disp'] = div_yield_disp
    stock_data['margin_disp'] = margin_disp
    stock_data['op_marge_disp'] = op_marge_disp
    stock_data['price_disp'] = price_disp
    stock_data['target_disp'] = target_disp
    stock_data['sector_disp'] = sector
    stock_data['currency_disp'] = currency

    related_stocks = get_related_stocks(ticker, limit=6)
    broker_recommendations = get_broker_recommendation(ticker, stock_name, currency)

    return {
        'stock_name': stock_name,
        'company_name': stock_name,
        'seo_title': seo_title,
        'seo_description': seo_description,
        'seo_summary_text': seo_summary_text,
        'fundamental_metrics': fundamental_metrics,
        'related_stocks': related_stocks,
        'stock_data': stock_data,
        'broker_recommendations': broker_recommendations,
    }


def get_or_create_default_stock_image(ticker, row=None):
    """Return (filename, seo_data_dict) for a ticker using a 24h on-disk PNG+JSON cache and in-memory cache."""
    ticker = ticker.upper().strip()
    safe_ticker = re.sub(r'[^A-Z0-9._-]', '_', ticker)
    today_str = datetime.now().strftime('%Y%m%d')
    filename = f"cache_{safe_ticker}_{today_str}.png"
    path = os.path.join(core.OUT_DIR, filename)
    meta_path = os.path.join(core.OUT_DIR, f"cache_{safe_ticker}_{today_str}.json")
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else 0.0
    cache_key = (ticker, today_str, mtime)

    # Fast path 1: PNG < 24h old on disk + in-memory or on-disk JSON metadata (0ms, no DataFrame lookup needed)
    png_fresh = False
    if os.path.exists(path):
        try:
            if (time.time() - os.path.getmtime(path)) < 86400:
                png_fresh = True
        except OSError:
            png_fresh = False

    if png_fresh:
        with _stock_landing_cache_lock:
            seo_ctx = _STOCK_LANDING_CACHE.get(cache_key)
        if seo_ctx is not None:
            if 'broker_recommendations' not in seo_ctx:
                seo_ctx['broker_recommendations'] = get_broker_recommendation(
                    ticker,
                    seo_ctx.get('stock_name', ticker),
                    seo_ctx.get('stock_data', {}).get('currency_disp', 'EUR')
                )
            return filename, seo_ctx
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    cached_json = json.load(f)
                if cached_json.get('_csv_mtime') == mtime:
                    seo_ctx = cached_json['data']
                    if 'broker_recommendations' not in seo_ctx:
                        seo_ctx['broker_recommendations'] = get_broker_recommendation(
                            ticker,
                            seo_ctx.get('stock_name', ticker),
                            seo_ctx.get('stock_data', {}).get('currency_disp', 'EUR')
                        )
                    with _stock_landing_cache_lock:
                        _STOCK_LANDING_CACHE[cache_key] = seo_ctx
                    return filename, seo_ctx
            except Exception:
                pass

    # Slow path (cache miss or stale): load row from DataFrame
    if row is None:
        df = core.load_df()
        match = df[df['Symbol'] == ticker]
        if match.empty:
            return None, None
        row = match.iloc[0]

    if not png_fresh:
        os.makedirs(core.OUT_DIR, exist_ok=True)
        img = core.render_stock_card(row, core.DEFAULT_METRICS, 'default', '', bg_path=None, ai_verdict='')
        img.convert('RGB').save(path, format='PNG')

    with _stock_landing_cache_lock:
        seo_ctx = _STOCK_LANDING_CACHE.get(cache_key)
    if seo_ctx is None:
        seo_ctx = _compute_stock_seo_data(ticker, row)
        with _stock_landing_cache_lock:
            _STOCK_LANDING_CACHE[cache_key] = seo_ctx
        try:
            os.makedirs(core.OUT_DIR, exist_ok=True)
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({'_csv_mtime': mtime, 'data': seo_ctx}, f, ensure_ascii=False, default=str)
        except Exception:
            pass

    return filename, seo_ctx

_DIV_CAL_CACHE_DATA = None
_DIV_CAL_CACHE_MTIME = 0.0
_div_cal_cache_lock = threading.Lock()

_SCREENER_CACHE_DATA = None
_SCREENER_CACHE_MTIME = 0.0
_screener_cache_lock = threading.Lock()

_SEARCH_ALL_CACHE_DATA = None
_SEARCH_ALL_CACHE_MTIME = 0.0
_search_all_cache_lock = threading.Lock()

# ─── Regular Routes ──────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return generate_image()
    if current_host() == COMPARE_HOST:
        return compare_home()

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
    global _DIV_CAL_CACHE_DATA, _DIV_CAL_CACHE_MTIME
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else 0.0
    
    if _DIV_CAL_CACHE_DATA is not None and mtime == _DIV_CAL_CACHE_MTIME:
        return Response(_DIV_CAL_CACHE_DATA, mimetype='application/json')
        
    with _div_cal_cache_lock:
        if _DIV_CAL_CACHE_DATA is not None and mtime == _DIV_CAL_CACHE_MTIME:
            return Response(_DIV_CAL_CACHE_DATA, mimetype='application/json')
            
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
        
        json_payload = json.dumps({'stocks': results, 'sectors': all_sectors, 'total': len(results)})
        _DIV_CAL_CACHE_DATA = json_payload
        _DIV_CAL_CACHE_MTIME = mtime
        
    return Response(json_payload, mimetype='application/json')

@app.route('/api/search-all')
def api_search_all():
    global _SEARCH_ALL_CACHE_DATA, _SEARCH_ALL_CACHE_MTIME
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else 0.0
    
    if _SEARCH_ALL_CACHE_DATA is not None and mtime == _SEARCH_ALL_CACHE_MTIME:
        return Response(_SEARCH_ALL_CACHE_DATA, mimetype='application/json')
        
    with _search_all_cache_lock:
        if _SEARCH_ALL_CACHE_DATA is not None and mtime == _SEARCH_ALL_CACHE_MTIME:
            return Response(_SEARCH_ALL_CACHE_DATA, mimetype='application/json')
            
        index = core.get_search_index()
        results = [{
            'symbol': item['symbol'],
            'name': item['name'],
            'div_yield': item.get('div_yield', 0.0),
            'sector': item.get('sector', '')
        } for item in index]
        
        json_payload = json.dumps({'stocks': results})
        _SEARCH_ALL_CACHE_DATA = json_payload
        _SEARCH_ALL_CACHE_MTIME = mtime
        
    return Response(json_payload, mimetype='application/json')

# ─── Aktien-Screener ─────────────────────────────────────────
def _build_screener_cache():
    global _SCREENER_CACHE_DATA, _SCREENER_CACHE_MTIME
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else 0.0
    if _SCREENER_CACHE_DATA is not None and mtime == _SCREENER_CACHE_MTIME:
        return _SCREENER_CACHE_DATA
    # Trigger population via api_screener logic
    api_screener()
    return _SCREENER_CACHE_DATA

@app.route('/screener')
def screener_page():
    is_embedded = request.args.get('embed') == '1'
    initial_stocks = []
    total_stocks = 0
    try:
        raw_json = _build_screener_cache()
        if raw_json:
            parsed = json.loads(raw_json)
            stocks = parsed.get('stocks', [])
            total_stocks = len(stocks)
            initial_stocks = sorted(
                stocks,
                key=lambda x: (x.get('mcap_usd') or x.get('mcap') or 0),
                reverse=True
            )[:20]
    except Exception:
        pass
    return render_template(
        'screener.html',
        is_embedded=is_embedded,
        initial_stocks=initial_stocks,
        total_stocks=total_stocks,
    )

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
    global _SCREENER_CACHE_DATA, _SCREENER_CACHE_MTIME
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else 0.0
    
    if _SCREENER_CACHE_DATA is not None and mtime == _SCREENER_CACHE_MTIME:
        return Response(_SCREENER_CACHE_DATA, mimetype='application/json')
        
    with _screener_cache_lock:
        if _SCREENER_CACHE_DATA is not None and mtime == _SCREENER_CACHE_MTIME:
            return Response(_SCREENER_CACHE_DATA, mimetype='application/json')
            
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
            'GBp': 1.27,     # UK stocks use GBp currency, but market cap numbers are in GBP
            'JPY': 0.0064,
            'CAD': 0.73,
            'AUD': 0.66,
            'HKD': 0.128,
            'INR': 0.012,
            'SEK': 0.095,
            'DKK': 0.145,
            'NOK': 0.094,
            'BRL': 0.18,
            'CNY': 0.138,
            'TWD': 0.031,    # Taiwan Dollar
            'KRW': 0.00073,  # South Korean Won
            'SGD': 0.74,
            'MXN': 0.055,
            'ZAR': 0.054,
            'ZAc': 0.054,    # South African cents (database values are in Rand ZAR)
            'SAR': 0.27,     # Saudi Riyal
            'IDR': 0.000061, # Indonesian Rupiah
            'PLN': 0.25,     # Polish Zloty
            'CLP': 0.0011,   # Chilean Peso
            'KWF': 3.25,     # Kuwaiti Dinar
            'QAR': 0.27,     # Qatari Riyal
            'MYR': 0.21,     # Malaysian Ringgit
            'ILA': 0.27,     # Israeli Agora (database values are in ILS Shekel)
            'ILS': 0.27,     # Israeli Shekel
            'AED': 0.27,     # UAE Dirham
            'HUF': 0.0028,   # Hungarian Forint
            'NZD': 0.61,     # New Zealand Dollar
            'USX': 1.0,      # US cents
            'CZK': 0.043,    # Czech Koruna
            'THB': 0.027,    # Thai Baht
            'ARS': 0.0011,   # Argentine Peso
            'EGP': 0.021,    # Egyptian Pound
            'NGN': 0.00067,  # Nigerian Naira
            'PHP': 0.017,    # Philippine Peso
            'TRY': 0.031,    # Turkish Lira
            'RUB': 0.011,    # Russian Ruble
            'BTC': 60000.0,  # Bitcoin
        }
    
        results = []
        for _, r in df.iterrows():
            if pd.isna(r.get('Symbol')):
                continue
                
            sector = str(r.get('Sektor', '')) if pd.notna(r.get('Sektor')) else ''
            region = str(r.get('Region', '')) if pd.notna(r.get('Region')) else ''
            
            mcap = safe_float(r.get('Marktkapitalisierung'))
            currency = str(r.get('Währung') or r.get('W\u00e4hrung') or 'USD').strip().upper()
            if not currency or currency == 'NAN':
                currency = 'USD'
                
            # Normalize minor/cents currencies to major currencies (e.g. ZAC -> ZAR, ILA -> ILS, USX -> USD)
            if currency == 'ZAC':
                currency = 'ZAR'
            elif currency == 'ILA':
                currency = 'ILS'
            elif currency == 'USX':
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
        
        json_payload = json.dumps({'stocks': results, 'sectors': all_sectors, 'total': len(results)})
        _SCREENER_CACHE_DATA = json_payload
        _SCREENER_CACHE_MTIME = mtime
        
    return Response(json_payload, mimetype='application/json')

@app.route('/analyse/<ticker>')
@app.route('/<ticker>')
def stock_landing(ticker):
    # Normalize ticker
    ticker = ticker.upper().strip()
    # Skip common static paths or API routes if they hit here accidentally
    if ticker in ["SEARCH", "HEALTH", "API", "STATIC", "DOWNLOAD", "FAVICON.ICO"]:
        return redirect(url_for('home'))

    from flask import g
    g.is_landing_page = True
    is_embedded = request.args.get('embed') == '1'

    # Direkter SSR-Analyse-Modus (Standard, nutzt 24h-Bild- & Metadaten-Cache ohne unnötigen DataFrame-Load)
    if request.args.get('edit') != '1':
        filename, seo_ctx = get_or_create_default_stock_image(ticker)
        if filename and seo_ctx:
            return render_template(
                'display_result.html',
                filename=filename,
                ticker=ticker,
                ai_verdict="",
                is_embedded=is_embedded,
                completion_id="",
                canonical_url=f"https://tool.schatzsuche40.de/analyse/{ticker}",
                **seo_ctx
            )

    df = core.load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        # Try to find by name if not found by exact symbol
        for name_col in ('resolved_name', 'Security', 'Langname'):
            if name_col in df.columns:
                match = df[df[name_col].str.contains(ticker, case=False, na=False, regex=False)]
                if not match.empty:
                    return redirect(url_for('stock_landing', ticker=match.iloc[0]['Symbol']))
        flash(f"Ticker '{ticker}' nicht gefunden.", "warning")
        return redirect(url_for('home'))

    company_name = core.get_clean_name(row.iloc[0])

    # Konfigurator-Modus (?edit=1)
    keys = core.all_metric_keys(df)
    available = [{"key": k, "label": core.METRIC_LABELS.get(k, k), "desc": core.METRIC_DESC.get(k, "")} for k in keys]
    mtime = os.path.getmtime(core.CSV_FILE) if os.path.exists(core.CSV_FILE) else time.time()
    last_update_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')

    return render_template(
        'index.html',
        ticker=ticker,
        company_name=company_name,
        seo_title=build_analysis_title(company_name, ticker),
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

@app.route('/api/ai-analysis', methods=['GET', 'POST'])
@app.route('/ai_analysis', methods=['GET', 'POST'])
def api_ai_analysis():
    payload = request.get_json(silent=True) or {}
    raw_ticker = (
        request.args.get('ticker')
        or request.form.get('ticker')
        or payload.get('ticker')
        or ''
    ).strip().upper()
    if not raw_ticker:
        return jsonify({"status": "error", "error": "Bitte einen Ticker angeben."}), 400

    mode = (
        request.args.get('mode')
        or request.form.get('mode')
        or payload.get('mode')
        or 'verdict'
    ).strip().lower()

    cached_val = ai_logic.get_cached_ai_analysis(raw_ticker, mode=mode)
    if cached_val:
        return jsonify({
            "status": "success",
            "ticker": raw_ticker,
            "mode": mode,
            "analysis": cached_val,
            "verdict": cached_val,
            "cached": True,
        }), 200

    df = core.load_df()
    row = df[df['Symbol'] == raw_ticker]
    company_name = raw_ticker
    fin_data = {}
    if not row.empty:
        r0 = row.iloc[0]
        company_name = core.get_clean_name(r0) or raw_ticker
        for m in core.DEFAULT_METRICS:
            fin_data[m] = core.display_value(m, r0)

    if mode == 'long_analysis':
        result_text = ai_logic.get_ai_long_analysis(raw_ticker, company_name, fin_data, use_cache=True)
    else:
        result_text = ai_logic.get_ai_verdict(raw_ticker, company_name, fin_data, use_cache=True)

    return jsonify({
        "status": "success",
        "ticker": raw_ticker,
        "company_name": company_name,
        "mode": mode,
        "analysis": result_text,
        "verdict": result_text,
        "cached": False,
    }), 200


@app.route('/generate_image', methods=['POST'])
def generate_image():
    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok and token != GUEST_TOKEN:
        token = GUEST_TOKEN
        ok, msg = saas_logic.check_quota(token)
    if not ok and token == GUEST_TOKEN:
        saas_logic.init_db()
        ok, msg = True, "OK"
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
    is_embedded_result = is_embedded_form or request.args.get('embed') == '1'
    if not is_embedded_result:
        mark_pending_completion('analysis_completed', filename)
    kwargs = {'filename': filename, 'ticker': ticker}
    if is_embedded_result:
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
    from flask import make_response
    is_embedded = request.args.get('embed') == '1'
    completion_id = '' if is_embedded else consume_pending_completion('analysis_completed', filename)
    ticker = request.args.get('ticker', '').upper().strip()
    if not ticker:
        base = os.path.basename(filename)
        if base.startswith('cache_'):
            parts = base[len('cache_'):].rsplit('_', 1)
            if parts:
                ticker = parts[0].upper()
        elif "_" in base:
            ticker = base.split("_")[0].upper()
            
    seo_ctx = {
        'stock_name': ticker,
        'company_name': '',
        'seo_title': build_analysis_title('', ticker) if ticker else 'Ergebnis - Aktien Analyse | Schatzsuche 4.0',
        'seo_description': '',
        'seo_summary_text': '',
        'fundamental_metrics': [],
        'related_stocks': [],
        'stock_data': {},
        'broker_recommendations': get_broker_recommendation(ticker, ticker),
    }
    if ticker:
        df = core.load_df()
        row = df[df['Symbol'] == ticker]
        if not row.empty:
            seo_ctx = _compute_stock_seo_data(ticker, row.iloc[0])
            
    from flask import session
    ai_verdict = session.get('ai_verdict', "")
    if not ai_verdict and ticker:
        ai_verdict = ai_logic.get_cached_ai_analysis(ticker, mode='verdict') or ""
            
    resp = make_response(render_template(
        'display_result.html', 
        filename=filename,
        ticker=ticker,
        ai_verdict=ai_verdict,
        is_embedded=is_embedded,
        completion_id=completion_id,
        canonical_url=f"https://tool.schatzsuche40.de/analyse/{ticker}" if ticker else request.base_url,
        **seo_ctx
    ))
    resp.headers['X-Robots-Tag'] = 'noindex, follow'
    return resp


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
    if current_host() != COMPARE_HOST:
        target = f'https://{COMPARE_HOST}/'
        if request.query_string:
            target = f"{target}?{request.query_string.decode('utf-8', errors='ignore')}"
        return redirect(target, code=301)

    is_embedded = request.args.get('embed') == '1'
    t1 = request.args.get('t1', '').upper()
    t2 = request.args.get('t2', '').upper()
    m_param = request.args.get('metrics', '')
    host = current_host()
    if is_embedded:
        canonical_url = 'https://schatzsuche40.de/aktien-vergleichstool/'
    else:
        canonical_url = f'https://{COMPARE_HOST}/' if host == COMPARE_HOST else request.base_url
    
    # Explicitly render the comparison tool template
    return render_template(
        'compare.html',
        is_embedded=is_embedded,
        vt1=t1,
        vt2=t2,
        vmetrics=m_param,
        canonical_url=canonical_url,
    )

@app.route('/compare/generate', methods=['POST'])
def generate_compare():
    if current_host() != COMPARE_HOST:
        return redirect(f'https://{COMPARE_HOST}/compare/generate', code=308)

    token = get_effective_token()
    ok, msg = saas_logic.check_quota(token)
    if not ok and token != GUEST_TOKEN:
        token = GUEST_TOKEN
        ok, msg = saas_logic.check_quota(token)
    if not ok and token == GUEST_TOKEN:
        saas_logic.init_db()
        ok, msg = True, "OK"
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

    is_embedded = request.form.get('embed') == '1' or request.args.get('embed') == '1'
    if not is_embedded:
        mark_pending_completion('comparison_completed', fname)
    kwargs = {'filename': fname, 't1': t1, 't2': t2}
    if m_param:
        kwargs['m_param'] = m_param
    if is_embedded:
        kwargs['embed'] = '1'
    return redirect(url_for('compare_result', **kwargs))

@app.route('/compare/result/<path:filename>')
def compare_result(filename):
    if current_host() != COMPARE_HOST:
        target = f'https://{COMPARE_HOST}{request.path}'
        if request.query_string:
            target = f"{target}?{request.query_string.decode('utf-8', errors='ignore')}"
        return redirect(target, code=301)

    is_embedded = request.args.get('embed') == '1'
    completion_id = '' if is_embedded else consume_pending_completion('comparison_completed', filename)
    t1 = request.args.get('t1', '')
    t2 = request.args.get('t2', '')
    m_param = request.args.get('m_param', '')
    return render_template(
        'compare_result.html',
        fname=filename,
        t1=t1,
        t2=t2,
        m_param=m_param,
        is_embedded=is_embedded,
        completion_id=completion_id,
    )

@app.route('/googlef3be5002fc1d35b1.html')
def google_verification():
    return Response('google-site-verification: googlef3be5002fc1d35b1.html', mimetype='text/html')

@app.route('/llms.txt')
def llms_txt():
    llms_path = os.path.join(app.static_folder, 'llms.txt')
    if os.path.exists(llms_path):
        with open(llms_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, content_type='text/markdown; charset=utf-8')
    return Response('# Schatzsuche 4.0 - Finanztools & Fundamentalanalyse\n', content_type='text/markdown; charset=utf-8')

# ─── SEO Sitemap (Hebel 1) ─────────────────────────────────
@app.route('/sitemap.xml')
def sitemap():
    if current_host() == COMPARE_HOST:
        body = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://compare.schatzsuche40.de/</loc>
    <lastmod>2026-10-22</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
'''
        return Response(body, mimetype='application/xml')
    return send_from_directory(app.static_folder, 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    if current_host() == COMPARE_HOST:
        body = '''# AI Search Engines & LLM Crawlers
User-agent: GPTBot
User-agent: OAI-SearchBot
User-agent: PerplexityBot
User-agent: ClaudeBot
User-agent: Google-Extended
Allow: /
Allow: /llms.txt
Disallow: /compare/result/
Disallow: /*?embed=1

# Standard Bots
User-agent: *
Allow: /
Allow: /llms.txt
Disallow: /compare/result/
Disallow: /*?embed=1

Sitemap: https://compare.schatzsuche40.de/sitemap.xml
Sitemap: https://schatzsuche40.de/sitemap_index.xml
'''
        return Response(body, mimetype='text/plain')
    body = '''# AI Search Engines & LLM Crawlers
User-agent: GPTBot
User-agent: OAI-SearchBot
User-agent: PerplexityBot
User-agent: ClaudeBot
User-agent: Google-Extended
Allow: /
Allow: /llms.txt
Disallow: /result/
Disallow: /*?embed=1

# Standard Bots
User-agent: *
Allow: /
Allow: /llms.txt
Disallow: /result/
Disallow: /*?embed=1

Sitemap: https://tool.schatzsuche40.de/sitemap.xml
Sitemap: https://schatzsuche40.de/sitemap_index.xml
'''
    return Response(body, mimetype='text/plain')


# ─── Add Ticker Endpoint (Hebel 2) ──────────────────────────
@app.route('/api/add-ticker', methods=['POST'])
def api_add_ticker():
    try:
        data = request.json or {}
        ticker_symbol = data.get('ticker', '').strip().upper()
        if not ticker_symbol:
            return jsonify({"status": "error", "message": "Kein Ticker angegeben."}), 400
            
        import re
        if not re.match(r'^[A-Z0-9.\-\s]+$', ticker_symbol):
            return jsonify({"status": "error", "message": "Ungültiger Ticker. Erlaubt sind Buchstaben, Zahlen, Punkte, Bindestriche und Leerzeichen."}), 400
            
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
        
        # If direct lookup fails, try search resolution
        if not info or not info.get('symbol') or (not info.get('shortName') and not info.get('longName')):
            try:
                search = yf.Search(ticker_symbol, max_results=5)
                results = search.quotes
                if results:
                    for res in results:
                        if res.get('quoteType') == 'EQUITY' or res.get('typeDisp') == 'Equity':
                            resolved_symbol = res.get('symbol')
                            if resolved_symbol and resolved_symbol.upper() != ticker_symbol:
                                ticker_symbol = resolved_symbol.upper()
                                # Retry lookup with resolved symbol
                                ticker_obj = yf.Ticker(ticker_symbol, session=session)
                                info = ticker_obj.info
                                break
            except Exception as search_err:
                print(f"Search resolution error for '{ticker_symbol}': {search_err}")
        
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
