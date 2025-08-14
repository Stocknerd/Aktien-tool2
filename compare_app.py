from flask import (
    Flask, request, jsonify, send_from_directory, redirect, url_for, render_template_string
)
import os, io, time, math
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# ───────────────────────── Basis / Pfade ─────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUT_DIR    = os.path.join(STATIC_DIR, "generated")
LOGO_DIR   = os.path.join(STATIC_DIR, "logos")
FONT_DIR   = os.path.join(STATIC_DIR, "fonts")
BACKGROUND = os.path.join(STATIC_DIR, "default_background.png")
CSV_FILE   = os.environ.get("STOCK_CSV", os.path.join(BASE_DIR, "stock_data.csv"))

os.makedirs(OUT_DIR, exist_ok=True)

# ───────────────────────── Render- und Layout-Parameter ─────────────────────────
OUTPUT_WIDTH  = 1080
OUTPUT_HEIGHT = 1350
SAFE_MARGIN_X = 0.06
SAFE_TOP_FRAC = 0.08
SAFE_BOTTOM_FRAC = 0.22
LINE_SPACING_MULT = 1.9

# Logos
LOGO_TARGET_H_FRAC = 0.28
LOGO_MAX_W_EACH_FRAC = 0.34
LOGO_GAP_FRAC = 0.06

# ───────────────────────── Fonts ─────────────────────────
FONT_REG_PATH = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
FONT_BLD_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

def _font(path: str, size: int, backup):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return backup

# ───────────────────────── Daten & Format ─────────────────────────
CURRENCY_SYMBOL = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF",
    "CAD": "C$", "AUD": "A$", "HKD": "HK$", "INR": "₹"
}

PERCENT_KEYS = {
    "Dividendenrendite", "Ausschüttungsquote",
    "Bruttomarge", "Operative Marge", "Nettomarge",
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    "Free Cashflow Yield",
    "Umsatzwachstum", "Gewinnwachstum",
    "Umsatzwachstum 3J (erwartet)",
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest",
    "52Wochen Change"
}

SECTOR_METRICS: Dict[str, List[str]] = {
    "Information Technology": [
        "KGV", "Forward PE", "KUV",
        "Eigenkapitalrendite", "Free Cashflow Yield", "Umsatzwachstum 3J (erwartet)"
    ],
    "Communication Services": [
        "KGV", "Forward PE", "KUV",
        "Nettomarge", "Eigenkapitalrendite", "Umsatzwachstum 3J (erwartet)"
    ],
    "Consumer Staples": [
        "Dividendenrendite", "Ausschüttungsquote", "KGV",
        "Nettomarge", "Eigenkapitalrendite", "Umsatzwachstum 3J (erwartet)"
    ],
    "Consumer Discretionary": [
        "KGV", "Forward PE", "KUV",
        "Operative Marge", "Eigenkapitalrendite", "Umsatzwachstum 3J (erwartet)"
    ],
    "Industrials": [
        "KGV", "EV/EBITDA", "KUV",
        "Operative Marge", "Eigenkapitalrendite", "Verschuldungsgrad"
    ],
    "Financials": [
        "KGV", "KBV", "Eigenkapitalrendite",
        "Nettomarge", "Dividendenrendite", "Beta"
    ],
    "Health Care": [
        "KGV", "Forward PE", "KUV",
        "Bruttomarge", "Nettomarge", "Umsatzwachstum 3J (erwartet)"
    ],
    "Energy": [
        "EV/EBITDA", "KGV", "Free Cashflow Yield",
        "Verschuldungsgrad", "Interest Coverage", "Dividendenrendite"
    ],
    "Utilities": [
        "Dividendenrendite", "Ausschüttungsquote", "KGV",
        "Verschuldungsgrad", "Interest Coverage", "Beta"
    ],
    "Materials": [
        "EV/EBITDA", "KGV", "KUV",
        "Bruttomarge", "Verschuldungsgrad", "Free Cashflow Yield"
    ],
    "Real Estate": [
        "Dividendenrendite", "Ausschüttungsquote", "KGV",
        "KUV", "Verschuldungsgrad", "Beta"
    ],
}

# Kürzere Labels
LABELS = {
    "Dividendenrendite": "Div.-Rendite",
    "Ausschüttungsquote": "Ausschüttg.",
    "Marktkapitalisierung": "Marktkap.",
    "Operative Marge": "Oper. Marge",
    "Operativer Cashflow": "Oper. CF",
    "Umsatzwachstum 3J (erwartet)": "Umsatzw. 3J",
}

# Aliasse für robustes Spalten-Mapping
COLUMN_ALIASES: Dict[str, List[str]] = {
    # Margen
    "Nettomarge": ["Nettomarge","Net Margin","Net Profit Margin","Profit Margin","profitMargins","netProfitMargin","netMargin"],
    "Operative Marge": ["Operative Marge","Operating Margin","operatingMargins"],
    "Bruttomarge": ["Bruttomarge","Gross Margin","grossMargins"],
    # Marktkap
    "Marktkapitalisierung": ["Marktkapitalisierung","Market Cap","marketCap","MarketCap"],
    # Dividendenrendite
    "Dividendenrendite": ["Dividendenrendite","Dividend Yield","dividendYield"],
    # Eigenkapitalrendite
    "Eigenkapitalrendite": ["Eigenkapitalrendite","Return on Equity","ROE","returnOnEquity"],
    # KGV / KUV
    "KGV": ["KGV","PE","trailingPE"],
    "Forward PE": ["Forward PE","forwardPE"],
    "KUV": ["KUV","Price to Sales","priceToSalesTrailing12Months"],
}

# Fallback-Datenquellen für Berechnung Nettomarge
REVENUE_ALIASES = [
    "Umsatz","Revenue","totalRevenue","Total Revenue","Revenue (ttm)","Umsatz (ttm)","revenue"
]
NET_INCOME_ALIASES = [
    "Net Income","Nettoergebnis","netIncome","Net Income Common Stockholders","netIncomeToCommon",
    "Net income applicable to common shares","Net Income (ttm)","net_income"
]

# Highlight-Logik
LOWER_BETTER = {"KGV","Forward PE","PEG-Ratio","KUV","EV/EBITDA","Verschuldungsgrad","Beta"}
HIGHER_BETTER = {
    "Dividendenrendite","Free Cashflow Yield","Bruttomarge","Operative Marge","Nettomarge",
    "Eigenkapitalrendite","Return on Assets","ROIC","Umsatzwachstum 3J (erwartet)","Gewinnwachstum 5J",
    "Interest Coverage","Current Ratio","Quick Ratio","EBIT","Free Cashflow","Operativer Cashflow","52Wochen Change"
}
NEUTRAL_METRICS = {"Marktkapitalisierung"}

COLOR_BETTER  = (14, 122, 63)
COLOR_DEFAULT = (0, 0, 0)

# UI: Kennzahlen-Liste (alle außer offensichtliche Stammdaten)
EXCLUDE_COLS = {
    "Symbol","Security","Abfragedatum","Datenquelle","valid_yahoo_ticker","resolved_name","resolved_exchange","resolved_score",
    "GICS Sector","GICS Sector Name","Sektor","Sector","Branche","Industry","Währung","Region"
}

_df = None
_df_mtime = None

def load_df() -> pd.DataFrame:
    global _df, _df_mtime
    cur_mtime = os.path.getmtime(CSV_FILE) if os.path.exists(CSV_FILE) else None
    if _df is None or _df_mtime != cur_mtime:
        last_err = None
        for _ in range(3):
            try:
                df = pd.read_csv(CSV_FILE, encoding="utf-8-sig", on_bad_lines="skip")
                _df = df
                _df_mtime = cur_mtime
                return _df
            except Exception as e:
                last_err = e
                time.sleep(0.25)
        raise last_err
    return _df

# ---------- Formatierer ----------

def _fmt_locale(num: float, dec: int = 2) -> str:
    s = f"{num:,.{dec}f}"
    s = s.replace(",", " ").replace(".", ",")
    return s

def fmt_number(val: Any, dec: int = 2) -> str:
    if pd.isna(val):
        return "–"
    try:
        num = float(str(val).replace(",", "."))
    except ValueError:
        return str(val)
    return _fmt_locale(num, dec)

def fmt_percent_for(key: str, val: Any, dec: int = 2) -> str:
    if pd.isna(val):
        return "–"
    s_raw = str(val).strip().replace("%", "")
    try:
        x = float(s_raw.replace(",", "."))
    except ValueError:
        return str(val)
    def _count_decimals(s: str) -> int:
        if "," in s:
            part = s.split(",", 1)[1]
        elif "." in s:
            part = s.split(".", 1)[1]
        else:
            return 0
        part = part.split("e")[0].split("E")[0]
        return sum(1 for ch in part if ch.isdigit())
    if key in {"Dividendenrendite","Free Cashflow Yield"}:
        decs = _count_decimals(s_raw)
        if abs(x) < 1.5 and decs >= 3:
            x *= 100.0
    else:
        if abs(x) <= 1.5:
            x *= 100.0
    return _fmt_locale(x, dec) + "%"

def currency_label(row: pd.Series) -> str:
    cur = str(row.get("Währung") or "").upper()
    sym = CURRENCY_SYMBOL.get(cur, cur or "$")
    return f"Mrd {sym}"

# ---------- Aliasse / Zugriff ----------

def resolve_col(row_or_df, key: str) -> Optional[str]:
    cols = row_or_df.index if isinstance(row_or_df, pd.Series) else row_or_df.columns
    if key in cols:
        return key
    for alt in COLUMN_ALIASES.get(key, []):
        if alt in cols:
            return alt
    return None

# ---------- Numeric helpers ----------

def _to_float(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    try:
        return float(str(x).replace("%", "").replace(",", ".").replace(" ", ""))
    except Exception:
        return None

def numeric_value(key: str, row: pd.Series) -> Optional[float]:
    if key == "Marktkapitalisierung":
        col = resolve_col(row, key) or key
        raw = row.get(col)
        try:
            return float(raw) / 1_000_000_000 if pd.notna(raw) else None
        except Exception:
            return None
    col = resolve_col(row, key) or key
    v = row.get(col)
    if key in PERCENT_KEYS:
        if pd.isna(v):
            if key == "Nettomarge":
                rev = next((row.get(c) for c in REVENUE_ALIASES if c in row.index and pd.notna(row.get(c))), None)
                ni  = next((row.get(c) for c in NET_INCOME_ALIASES if c in row.index and pd.notna(row.get(c))), None)
                try:
                    if rev and ni:
                        return float(ni) / float(rev) * 100.0
                except Exception:
                    return None
            return None
        s_raw = str(v).strip().replace("%", "")
        try:
            x = float(s_raw.replace(",", "."))
        except Exception:
            return None
        def _count_decimals(s: str) -> int:
            if "," in s:
                part = s.split(",", 1)[1]
            elif "." in s:
                part = s.split(".", 1)[1]
            else:
                return 0
            part = part.split("e")[0].split("E")[0]
            return sum(1 for ch in part if ch.isdigit())
        if key in {"Dividendenrendite","Free Cashflow Yield"}:
            decs = _count_decimals(s_raw)
            if abs(x) < 1.5 and decs >= 3:
                x *= 100.0
        else:
            if abs(x) <= 1.5:
                x *= 100.0
        return x
    return _to_float(v)

# ---------- Bild-Helfer ----------

def resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    if w == target_w and h == target_h:
        return img
    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left   = (new_w - target_w) // 2
    top    = (new_h - target_h) // 2
    right  = left + target_w
    bottom = top + target_h
    return img.crop((left, top, right, bottom))

# ---------- Wertebereitstellung ----------

def display_value(key: str, row: pd.Series) -> str:
    if key == "Marktkapitalisierung":
        col = resolve_col(row, key) or key
        raw = row.get(col)
        if pd.notna(raw):
            try:
                v = float(raw) / 1_000_000_000
            except Exception:
                return "–"
            return f"{fmt_number(v, 0)} {currency_label(row)}"
        return "–"
    col = resolve_col(row, key) or key
    val = row.get(col)
    if key == "Nettomarge" and (pd.isna(val) or val == ""):
        rev = next((row.get(c) for c in REVENUE_ALIASES if c in row.index and pd.notna(row.get(c))), None)
        ni  = next((row.get(c) for c in NET_INCOME_ALIASES if c in row.index and pd.notna(row.get(c))), None)
        try:
            if rev and ni:
                return fmt_percent_for(key, float(ni) / float(rev) * 100.0)
        except Exception:
            pass
    if key in PERCENT_KEYS:
        return fmt_percent_for(key, val)
    return fmt_number(val)

# ---------- Flask ----------
app = Flask(__name__)

@app.route("/")
def compare_home():
    return render_template_string(
        COMPOSE_HTML,
    )

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = load_df()
    if not q:
        return jsonify([])
    out = []
    for _, row in df.iterrows():
        sym = str(row.get('Symbol') or '')
        sec = str(row.get('Security') or '')
        if q in sym.lower() or q in sec.lower():
            out.append({'symbol': sym, 'name': sec})
        if len(out) >= 12:
            break
    return jsonify(out)

@app.route('/api/peers')
def peers():
    sym = (request.args.get('symbol') or '').strip().upper()
    df  = load_df()
    row = df[df['Symbol'].astype(str).str.upper() == sym]
    if row.empty:
        return jsonify({"sector": None, "peers": [], "defaults": []})
    sector = str(row.iloc[0].get('Sektor') or row.iloc[0].get('Sector') or '')
    peers_df = df[df['Sektor'].astype(str) == sector][['Symbol','Security']].dropna()
    peers = [{"symbol": s, "name": n} for s, n in peers_df.values if str(s).upper()!=sym]
    return jsonify({"sector": sector, "peers": peers, "defaults": SECTOR_METRICS.get(sector, [])[:6]})

@app.route('/metrics')
def metrics():
    """Alle wählbaren Kennzahlen (nicht nur Defaults)."""
    df = load_df()
    cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    # bisschen sortieren: bekannte zuerst
    known = set()
    ordered: List[str] = []
    for arr in SECTOR_METRICS.values():
        for k in arr:
            if k in cols and k not in known:
                ordered.append(k); known.add(k)
    for c in cols:
        if c not in known:
            ordered.append(c)
    data = [{"key": k, "label": LABELS.get(k, k)} for k in ordered]
    return jsonify(data)

@app.route('/generate_compare', methods=['POST'])
def generate_compare():
    a = (request.form.get('ticker_a') or '').strip().upper()
    b = (request.form.get('ticker_b') or '').strip().upper()
    metrics = request.form.getlist('metrics')[:6]

    df = load_df()
    rows = []
    for t in (a,b):
        r = df[df['Symbol'].astype(str).str.upper()==t]
        if r.empty and 'valid_yahoo_ticker' in df.columns:
            r = df[df['valid_yahoo_ticker'].astype(str).str.upper()==t]
        if r.empty:
            return redirect(url_for('compare_home'))
        rows.append(r.iloc[0])

    # Sektor-Prüfung serverseitig
    sec_a = str(rows[0].get('Sektor') or rows[0].get('Sector') or '')
    sec_b = str(rows[1].get('Sektor') or rows[1].get('Sector') or '')
    if sec_a and sec_b and sec_a != sec_b:
        df_peer = df[df['Sektor'].astype(str)==sec_a]
        alt = df_peer[df_peer['Symbol'].astype(str).str.upper()!=a].head(1)
        if not alt.empty:
            rows[1] = alt.iloc[0]
            b = str(rows[1]['Symbol'])

    if not metrics:
        metrics = SECTOR_METRICS.get(sec_a, ["KGV","Forward PE","KUV","Nettomarge","Eigenkapitalrendite","Dividendenrendite"])[:6]

    # ───── Bild vorbereiten
    bg = Image.open(BACKGROUND).convert('RGBA')
    bg = resize_cover(bg, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    img = bg.copy()
    draw = ImageDraw.Draw(img)

    base_w = img.width
    TITLE_SZ  = max(44, int(base_w * 0.060))
    SUB_SZ    = max(30, int(base_w * 0.042))
    LABEL_SZ  = max(28, int(base_w * 0.036))
    VAL_SZ    = max(28, int(base_w * 0.036))
    FOOT_SZ   = max(20, int(base_w * 0.026))

    f_title = _font(FONT_BLD_PATH, TITLE_SZ, ImageFont.load_default())
    f_sub   = _font(FONT_REG_PATH, SUB_SZ,   ImageFont.load_default())
    f_lbl   = _font(FONT_REG_PATH, LABEL_SZ, ImageFont.load_default())
    f_val   = _font(FONT_REG_PATH, VAL_SZ,   ImageFont.load_default())
    f_foot  = _font(FONT_REG_PATH, FOOT_SZ,  ImageFont.load_default())

    # Titel
    name_a, sym_a = str(rows[0].get('Security') or ''), str(rows[0].get('Symbol') or '')
    name_b, sym_b = str(rows[1].get('Security') or ''), str(rows[1].get('Symbol') or '')
    title = f"{sym_a} vs {sym_b}"
    sub   = f"{name_a}  –  {name_b}"

    def draw_centered(text, font, y):
        tw = draw.textlength(text, font=font)
        tx = (img.width - int(tw)) // 2
        draw.text((tx, y), text, fill="black", font=font)
        return y + int(font.size * 1.15)

    y = int(img.height * SAFE_TOP_FRAC)
    y = draw_centered(title, f_title, y)
    y = draw_centered(sub, f_sub, y)

    # Tabelle (symmetrisch): Kennzahl | A | B
    x = int(img.width * SAFE_MARGIN_X)
    avail_w = img.width - 2*x
    col_gap = int(img.width * 0.04)

    labels = [LABELS.get(m, m) for m in metrics]
    max_label_px = max(int(draw.textlength(l+":", font=f_lbl)) for l in labels)
    label_w = min(int(avail_w*0.36), max_label_px + 20)
    remain = avail_w - label_w - col_gap
    val_w   = (remain - col_gap) // 2

    # Spaltenköpfe exakt über dem Spaltenmittelpunkt
    header_y = y + int(f_sub.size * 0.9)
    a_center = x + label_w + col_gap + val_w/2
    b_center = x + label_w + col_gap + val_w + col_gap + val_w/2
    draw.text((a_center - draw.textlength(sym_a, font=f_lbl)/2, header_y), sym_a, fill="black", font=f_lbl)
    draw.text((b_center - draw.textlength(sym_b, font=f_lbl)/2, header_y), sym_b, fill="black", font=f_lbl)

    y = header_y + int(f_lbl.size * 1.4)

    # Werte ggf. schrumpfen, bis längster in val_w passt
    def longest_value_px(font_val):
        px = 0
        for m in metrics:
            av = display_value(m, rows[0])
            bv = display_value(m, rows[1])
            px = max(px, int(draw.textlength(av, font=font_val)), int(draw.textlength(bv, font=font_val)))
        return px

    while (longest_value_px(f_val) > val_w) and f_val.size > 22:
        f_val = _font(FONT_REG_PATH, f_val.size - 1, ImageFont.load_default())

    line_h = int(max(f_lbl.size, f_val.size) * LINE_SPACING_MULT)

    # Zeilen zeichnen + besseres Ergebnis grün einfärben
    for i, m in enumerate(metrics):
        ly = y + i*line_h
        lab = LABELS.get(m, m) + ":"
        draw.text((x, ly), lab, fill="black", font=f_lbl)

        av = display_value(m, rows[0])
        bv = display_value(m, rows[1])
        a_num = numeric_value(m, rows[0])
        b_num = numeric_value(m, rows[1])

        better = None
        if a_num is not None and b_num is not None and m not in NEUTRAL_METRICS:
            if m in LOWER_BETTER:
                better = 'A' if a_num < b_num else ('B' if b_num < a_num else None)
            elif (m in HIGHER_BETTER) or (m in PERCENT_KEYS):
                better = 'A' if a_num > b_num else ('B' if b_num > a_num else None)

        ax = x + label_w + col_gap + (val_w - int(draw.textlength(av, font=f_val)))
        bx = x + label_w + col_gap + val_w + col_gap + (val_w - int(draw.textlength(bv, font=f_val)))
        colA = COLOR_BETTER if better == 'A' else COLOR_DEFAULT
        colB = COLOR_BETTER if better == 'B' else COLOR_DEFAULT
        draw.text((ax, ly), av, fill=colA, font=f_val)
        draw.text((bx, ly), bv, fill=colB, font=f_val)

    # Logos unter der Tabelle, gleich hoch & Baseline
    def load_logo(sym: str):
        p = os.path.join(LOGO_DIR, f"{sym}.png")
        if os.path.exists(p):
            try:
                return Image.open(p).convert('RGBA')
            except Exception:
                return None
        return None

    la = load_logo(sym_a)
    lb = load_logo(sym_b)

    foot = f"Stand: {datetime.today().strftime('%d.%m.%Y')}  •  Quelle: Yahoo Finance"
    fw = draw.textlength(foot, font=f_foot)
    fx = (img.width - int(fw)) // 2
    fy = img.height - int(img.height * SAFE_BOTTOM_FRAC)

    logos_y_top = y + len(metrics)*line_h + int(img.height*0.05)
    logos_max_h = max(10, fy - logos_y_top - int(img.height*0.03))
    target_h = int(min(logos_max_h, img.height*LOGO_TARGET_H_FRAC))

    def fit_logo(img_in: Optional[Image.Image]) -> Optional[Image.Image]:
        if img_in is None:
            return None
        w, h = img_in.size
        if h == 0:
            return None
        scale = target_h / h
        nw, nh = int(w*scale), int(h*scale)
        max_w = int(img.width * LOGO_MAX_W_EACH_FRAC)
        if nw > max_w:
            scale = max_w / w
            nw, nh = int(w*scale), int(h*scale)
        return img_in.resize((nw, nh), Image.LANCZOS)

    la = fit_logo(la)
    lb = fit_logo(lb)

    if la is not None or lb is not None:
        gap = int(img.width * LOGO_GAP_FRAC)
        total_w = (la.width if la else 0) + (lb.width if lb else 0) + (gap if (la and lb) else 0)
        max_total = int(img.width * 0.88)
        if total_w > max_total:
            scale = max_total / total_w
            def rescale(im):
                if im is None: return None
                return im.resize((max(1,int(im.width*scale)), max(1,int(im.height*scale))), Image.LANCZOS)
            la, lb = rescale(la), rescale(lb)
            total_w = (la.width if la else 0) + (lb.width if lb else 0) + (gap if (la and lb) else 0)

        start_x = (img.width - total_w) // 2
        baseline = logos_y_top + (target_h if target_h>0 else 0)
        if la:
            img.alpha_composite(la, (start_x, baseline - la.height))
        if lb:
            x2 = start_x + (la.width + gap if la else 0)
            img.alpha_composite(lb, (x2, baseline - lb.height))

    # Footer
    draw.text((fx, fy), foot, fill="black", font=f_foot)

    # Datei speichern
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"COMPARE_{sym_a}_{sym_b}_{ts}.png"
    path = os.path.join(OUT_DIR, filename)
    img.convert('RGB').save(path, format='PNG')
    return redirect(url_for('result', filename=filename))

@app.route('/static/generated/<path:filename>')
def result_file(filename):
    return send_from_directory(OUT_DIR, filename)

@app.route('/result/<path:filename>')
def result(filename):
    return render_template_string("""
<!doctype html>
<title>Aktienvergleich – Ergebnis</title>
<div style=\"max-width:1080px;margin:24px auto;text-align:center;font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;\">
  <h2>Aktienvergleich – Ergebnis</h2>
  <p><a href=\"/\">Neuen Vergleich starten</a></p>
  <img src=\"{{ url_for('result_file', filename=filename) }}\" style=\"max-width:100%;height:auto;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.12)\" />
  <p style=\"margin-top:12px\"><a download href=\"{{ url_for('result_file', filename=filename) }}\">PNG herunterladen</a></p>
</div>
""", filename=filename)

# ──────────────── Simple UI (keine Templates nötig) ────────────────
COMPOSE_HTML = """
<!doctype html>
<title>Aktienvergleich</title>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<style>
body{font-family:system-ui, Segoe UI, Roboto, Arial, sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#111}
label{display:block;margin:10px 0 4px}
input,select,button{font-size:16px;padding:10px;border:1px solid #ccc;border-radius:8px;width:100%}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}
.metric{display:flex;align-items:center;gap:8px}
button{background:#0a7; color:white; border:none; padding:12px 16px; cursor:pointer}
button:disabled{opacity:.5;cursor:not-allowed}
small{color:#666}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f5f9;font-size:12px;margin-left:8px}
</style>
<h1>Aktienvergleich</h1>
<form id=\"f\" method=\"post\" action=\"/generate_compare\">
  <div class=\"grid\">
    <div>
      <label>Aktie A (Symbol oder Name)</label>
      <input id=\"a\" name=\"ticker_a\" placeholder=\"z.B. NVDA oder NVIDIA\" list=\"a_list\" autocomplete=\"off\" />
      <datalist id=\"a_list\"></datalist>
    </div>
    <div>
      <label>Aktie B (gleicher Sektor)</label>
      <select id=\"b\" name=\"ticker_b\"></select>
    </div>
  </div>
  <div style=\"margin-top:12px\">
    <label>6 Kennzahlen</label>
    <div id=\"metrics\" class=\"metrics\"></div>
    <div style=\"display:flex;gap:8px;align-items:center;margin-top:8px\">
      <input id=\"addMetric\" list=\"allMetrics\" placeholder=\"Kennzahl suchen & hinzufügen\" />
      <datalist id=\"allMetrics\"></datalist>
      <button type=\"button\" id=\"addBtn\">Hinzufügen</button>
      <span class=\"badge\"><span id=\"count\">0</span>/6 ausgewählt</span>
    </div>
    <small>Du kannst beliebig suchen – maximal 6 Kennzahlen werden dargestellt.</small>
  </div>
  <div style=\"margin-top:16px\">
    <button id=\"submit\" disabled>Vergleich erzeugen</button>
  </div>
</form>
<script>
const a = document.getElementById('a');
const aList = document.getElementById('a_list');
const b = document.getElementById('b');
const metricsBox = document.getElementById('metrics');
const submitBtn = document.getElementById('submit');
const addMetric = document.getElementById('addMetric');
const addBtn = document.getElementById('addBtn');
const countEl = document.getElementById('count');

let available = [];
let debounceTimer;

// Lade alle Kennzahlen für den Picker
(async function loadMetrics(){
  const res = await fetch('/metrics');
  available = await res.json();
  const dl = document.getElementById('allMetrics');
  dl.innerHTML = available.map(m=>`<option value="${m.key}">${m.label}</option>`).join('');
})();

a.addEventListener('input', () => {
  submitBtn.disabled = true;
  clearTimeout(debounceTimer);
  const q = a.value.trim();
  if(!q){ aList.innerHTML=''; b.innerHTML=''; metricsBox.innerHTML=''; updateCount(); return; }
  debounceTimer = setTimeout(async () => {
    const res = await fetch('/search?q=' + encodeURIComponent(q));
    const arr = await res.json();
    aList.innerHTML = arr.map(o=>`<option value="${o.symbol}">${o.name}</option>`).join('');
  }, 220);
});

a.addEventListener('change', async () => {
  const sym = a.value.trim();
  if(!sym){ return; }
  const res = await fetch('/api/peers?symbol=' + encodeURIComponent(sym));
  const data = await res.json();
  b.innerHTML = data.peers.map(p=>`<option value="${p.symbol}">${p.symbol} — ${p.name}</option>`).join('');
  const defs = (data.defaults||[]).slice(0,6);
  renderMetrics(defs);
  submitBtn.disabled = !b.value;
});

b.addEventListener('change', () => {
  submitBtn.disabled = !b.value;
});

function currentSelected(){
  return Array.from(metricsBox.querySelectorAll('input[name=metrics]:checked')).map(x=>x.value);
}

function updateCount(){
  countEl.textContent = currentSelected().length;
}

function renderMetrics(keys){
  const cur = keys.slice(0,6);
  metricsBox.innerHTML = cur.map((k,i)=>{
    const label = (available.find(m=>m.key===k)?.label) || k;
    const checked = 'checked';
    return `<label class="metric"><input type="checkbox" name="metrics" value="${k}" ${checked} /> ${label}</label>`;
  }).join('');
  metricsBox.addEventListener('change', () => {
    const on = currentSelected();
    if(on.length>6){
      // letzte Änderung rückgängig machen
      const last = metricsBox.querySelector('input[name=metrics]:checked:last-of-type');
      if(last) last.checked=false;
    }
    updateCount();
  });
  updateCount();
}

addBtn.addEventListener('click', () => {
  const key = addMetric.value.trim();
  if(!key) return;
  const exists = available.some(m=>m.key===key);
  if(!exists) return;
  const selected = currentSelected();
  if(selected.includes(key)) { addMetric.value=''; return; }
  if(selected.length>=6){ alert('Maximal 6 Kennzahlen.'); return; }
  const label = (available.find(m=>m.key===key)?.label) || key;
  const el = document.createElement('label');
  el.className = 'metric';
  el.innerHTML = `<input type="checkbox" name="metrics" value="${key}" checked /> ${label}`;
  metricsBox.appendChild(el);
  addMetric.value='';
  updateCount();
});
</script>
"""

# ───────────────────────── Run ─────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
