from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import textwrap
import pandas as pd
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSV_FILE = os.path.join(BASE_DIR, "stock_data.csv")
BACKGROUND_FILE = os.path.join(STATIC_DIR, "default_background.png")
LOGO_DIR = os.path.join(STATIC_DIR, "logos")            # static/logos/<TICKER>.png
FONT_DIR = os.path.join(STATIC_DIR, "fonts")
MONTSERRAT_BOLD = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")
MONTSERRAT_REG = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
GENERATED_DIR = os.path.join(STATIC_DIR, "generated")

os.makedirs(GENERATED_DIR, exist_ok=True)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CSV Cache
# ---------------------------------------------------------------------------
_df_cache: pd.DataFrame | None = None

def load_dataframe() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="utf-8-sig", on_bad_lines="skip")
        df.columns = df.columns.str.replace("\ufeff", "").str.strip()
        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
        df["Security"] = df["Security"].astype(str).str.strip()
        _df_cache = df
    return _df_cache

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_stock_row(ticker: str):
    df = load_dataframe()
    r = df[df["Symbol"] == ticker]
    return r.iloc[0] if not r.empty else None


def _fmt_number(val, dec: int = 2):
    if pd.isna(val):
        return "–"
    if isinstance(val, (int, float)):
        return f"{val:,.{dec}f}".replace(",", ".")
    return str(val)

# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _font(path: str, size: int, fallback):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return fallback

# ---------------------------------------------------------------------------
# Bildgenerierung
# ---------------------------------------------------------------------------

def create_stock_image(bg: str, ticker: str) -> str:
    row = get_stock_row(ticker)
    if row is None:
        raise ValueError("Ticker not found")

    img = Image.open(bg).convert("RGBA")
    draw = ImageDraw.Draw(img)

    fallback = ImageFont.load_default()
    f_title = _font(MONTSERRAT_BOLD, 58, fallback)
    f_label = _font(MONTSERRAT_BOLD, 32, fallback)
    f_small = _font(MONTSERRAT_REG, 22, fallback)

    # ------------------------------ Zentrierter Titel mit Wrap ------------------------------
    max_width = img.width - 160
    title_raw = f"Aktie: {row['Security'].upper()} ({ticker})"
    words = title_raw.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        if draw.textlength(test, font=f_title) > max_width and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = 25
    for l in lines:
        w = draw.textlength(l, font=f_title)
        draw.text(((img.width - w) // 2, y), l, fill="black", font=f_title)
        y += f_title.size + 8

    # ------------------------------ Kennzahlen ----------------------------------
    # Marktkapitalisierung in Milliarden umrechnen
    raw_mcap = row.get('Marktkapitalisierung', row.get('Marktkap.', None))
    mcap_bil = raw_mcap / 1_000_000_000 if pd.notna(raw_mcap) else pd.NA

    metrics = [
        ("Dividendenrendite", f"{_fmt_number(row.get('Dividendenrendite'))}%"),
        ("Ausschüttungsquote", f"{_fmt_number(row.get('Ausschüttungsquote'))}%"),
        ("KUV", _fmt_number(row.get('KUV'))),
        ("KGV", _fmt_number(row.get('KGV'))),
        ("Gewinn je Aktie", _fmt_number(row.get('Gewinn je Aktie'))),
        ("Marktkap.", f"{_fmt_number(mcap_bil)} Mrd. $") ,
        ("Gewinnwachstum", f"{_fmt_number(row.get('Gewinnwachstum'))}%"),
        ("Umsatzwachstum", f"{_fmt_number(row.get('Umsatzwachstum'))}%"),
    ]

    col_x = [100, img.width // 2 + 40]
    y_start = y + 90
    y_cursor = [y_start, y_start]
    line_h = f_label.size + 60  # größerer Zeilenabstand

    for i, (lab, val) in enumerate(metrics):
        col = i % 2
        draw.text((col_x[col], y_cursor[col]), f"{lab}: {val}", fill="black", font=f_label)
        y_cursor[col] += line_h

    # ------------------------------ Logo ---------------------------------------
    logo_path = next((os.path.join(LOGO_DIR, v) for v in (f"{ticker}.png", f"{ticker.lower()}.png", f"{ticker.upper()}.png") if os.path.exists(os.path.join(LOGO_DIR, v))), None)
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        max_w = int(img.width * 0.18)
        scale = min(1, max_w / logo.width)
        logo = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
        y_logo = max(y_cursor) + 40  # Logo leicht höher
        x_logo = (img.width - logo.width) // 2
        img.alpha_composite(logo, (x_logo, y_logo))
        y_footer_start = y_logo + logo.height + 40  # Footer etwas höher
    else:
        y_footer_start = max(y_cursor) + 80

    # ------------------------------ Footer -------------------------------------
    footer = f"Abfragedatum: {datetime.now():%d.%m.%Y}, Datenquelle: Yahoo Finance"
    w = draw.textlength(footer, font=f_small)
    draw.text(((img.width - w) // 2, y_footer_start), footer, fill="black", font=f_small)

    out_path = os.path.join(GENERATED_DIR, f"{ticker}_{int(datetime.now().timestamp())}.png")
    img.save(out_path)
    return out_path

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    df = load_dataframe()
    mask = df['Symbol'].str.contains(q, case=False, na=False) | df['Security'].str.contains(q, case=False, na=False)
    return jsonify([{ 'symbol': s, 'name': n } for s, n in df.loc[mask, ['Symbol', 'Security']].head(20).to_records(index=False)])

@app.route('/generate_image', methods=['POST'])
def generate_image():
    ticker = request.form.get('ticker', '').strip().upper()
    if not ticker:
        return 'Ticker fehlt', 400
    if get_stock_row(ticker) is None:
        return f"Ticker '{ticker}' nicht gefunden", 400
    if not os.path.exists(BACKGROUND_FILE):
        return 'Standard-Hintergrund nicht gefunden', 500
    path = create_stock_image(BACKGROUND_FILE, ticker)
    return redirect(url_for('display_result', filename=os.path.basename(path)))

@app.route('/result/<filename>')
def display_result(filename):
    return render_template('display_result.html', filename=filename)

@app.route('/static/generated/<path:filename>')
def generated_file(filename):
    return send_from_directory(GENERATED_DIR, filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    return send_from_directory(GENERATED_DIR, filename)

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
