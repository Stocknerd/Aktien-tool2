from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import threading, time, os, math
import pandas as pd

app = Flask(__name__)

# --- Konfiguration ---------------------------------------------------------
UPLOAD_FOLDER      = 'uploads'
OUTPUT_FOLDER      = 'output'
LOG_FOLDER         = 'logs'
CSV_FILE           = 'stock_data.csv'
FONT_PATH          = 'static/fonts/Montserrat-Bold.ttf'
DEFAULT_BACKGROUND = 'static/default_background.png'

# Globale Liste aller Kennzahlen
NUMERIC_COLUMNS = [
    # Basis-Daten
    "Dividendenrendite", "Ausschüttungsquote", "KUV", "KGV", "Gewinn je Aktie", "Marktkapitalisierung",
    # Wachstum
    "Gewinnwachstum 5J", "Umsatzwachstum 10J",
    # Bewertungskennzahlen
    "Forward PE", "KBV", "PEG-Ratio", "EV/EBITDA",
    # Margen
    "Bruttomarge", "Operative Marge", "Nettomarge",
    # Cashflow
    "Free Cashflow", "Free Cashflow Yield", "Operativer Cashflow",
    # Rentabilität
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    # Liquidität & Verschuldung
    "Verschuldungsgrad", "Interest Coverage", "Current Ratio", "Quick Ratio",
    # Risiko & Markt
    "Beta", "52Wochen Hoch", "52Wochen Tief", "52Wochen Change",
    # Analysten
    "Analysten_Kursziel", "Empfehlungsdurchschnitt",
    # Ownership
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest"
]

# Formatierungs-Maps
SUFFIX_MAP = {
    **{k: '%' for k in [
        "Dividendenrendite","Ausschüttungsquote","Gewinnwachstum 5J","Umsatzwachstum 10J",
        "Bruttomarge","Operative Marge","Nettomarge",
        "Eigenkapitalrendite","Return on Assets","ROIC",
        "52Wochen Change","Insider_Anteil","Institutioneller_Anteil","Short Interest"
    ]},
    "Marktkapitalisierung": " Mrd. $",
    **{k: '' for k in NUMERIC_COLUMNS if k not in [
        "Dividendenrendite","Ausschüttungsquote","Gewinnwachstum 5J","Umsatzwachstum 10J",
        "Bruttomarge","Operative Marge","Nettomarge",
        "Eigenkapitalrendite","Return on Assets","ROIC",
        "52Wochen Change","Insider_Anteil","Institutioneller_Anteil","Short Interest",
        "Marktkapitalisierung"
    ]}
}
PRECISION_MAP = {k: 2 for k in NUMERIC_COLUMNS}

# Verzeichnisse anlegen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
LOG_FILE = os.path.join(LOG_FOLDER, "ticker_log.csv")


def log_ticker_usage(ticker):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts},{ticker}\n")


def get_stock_data(ticker):
    """Liest die CSV ein, filtert nach Symbol und liefert ein Dict."""
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        # Spaltenumbenennung für korrekte Zeichencodierung
        df.rename(columns={"AusschÃ¼ttungsquote": "Ausschüttungsquote"}, inplace=True)
    except Exception as e:
        print(f"CSV-Fehler: {e}")
        return None

    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    # Numerische Spalten konvertieren
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    row = df[df["Symbol"] == ticker]
    if row.empty:
        return None
    row = row.iloc[0]

    data = {"Security": row.get("Security", "-")}
    # Werte sammeln
    for col in NUMERIC_COLUMNS:
        data[col] = None if pd.isna(row.get(col)) else row.get(col)

    # Datum und Quelle
    orig = row.get("Abfragedatum")
    if orig:
        try:
            parsed = datetime.strptime(orig, "%Y-%m-%d")
            data["Abfragedatum"] = parsed.strftime("%d.%m.%Y")
        except:
            data["Abfragedatum"] = orig
    else:
        data["Abfragedatum"] = "-"
    data["Datenquelle"] = row.get("Datenquelle", "-")

    return data


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current = words[0]
    for w in words[1:]:
        test = f"{current} {w}"
        width = font.getbbox(test)[2] - font.getbbox(test)[0]
        if width <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def create_stock_image(bg_path, stock_data, ticker, metrics):
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    # Fonts
    try:
        title_font = ImageFont.truetype(FONT_PATH, 50)
        body_font  = ImageFont.truetype(FONT_PATH, 30)
        foot_font  = ImageFont.truetype(FONT_PATH, 20)
    except:
        title_font = body_font = foot_font = ImageFont.load_default()

    # Titel
    title = f"Aktie: {stock_data['Security']} ({ticker})"
    lines = wrap_text(title, title_font, img.width - 100)
    y = 50
    for line in lines:
        bbox = title_font.getbbox(line)
        x = (img.width - (bbox[2]-bbox[0])) // 2
        draw.text((x, y), line, fill="black", font=title_font)
        y += (bbox[3]-bbox[1]) + 10
    title_h = y - 50 - 10

    # Logo
    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        ow, oh = logo.size
        th = 200
        sf = th / oh
        nw, nh = int(ow*sf), th
        max_w = img.width - 200
        if nw > max_w:
            sf = max_w / ow
            nw, nh = max_w, int(oh*sf)
        logo = logo.resize((nw, nh), Image.Resampling.LANCZOS)
        logo_x = (img.width - nw)//2
        logo_y = int(0.7*img.height) - nh//2
    else:
        logo = None
        logo_x = img.width//2
        logo_y = int(0.7*img.height)

    # Kennzahlen formatieren
    def fmt(val, suffix, prec):
        if val is None:
            return '-'
        if suffix == '%': val *= 100
        if suffix == ' Mrd. $': val /= 1e9
        return f"{val:.{prec}f}{suffix}"

    items = []
    for key in metrics:
        raw = stock_data.get(key)
        text = fmt(raw, SUFFIX_MAP.get(key,''), PRECISION_MAP.get(key,2))
        items.append(f"{key}: {text}")

    # Grid-Layout
    cols = 2
    rows = math.ceil(len(items)/cols)
    top = 50 + title_h + 100
    bottom = (logo_y - 30) if logo else (img.height - 200)
    avail_h = max(1, bottom - top)
    row_h = max(avail_h//rows, 50)
    left, right = 100, img.width-100
    col_w = (right-left)//cols
    for i, txt in enumerate(items):
        r, c = divmod(i, cols)
        x = left + c*col_w + 10
        y = top + r*row_h
        draw.text((x, y), txt, fill="black", font=body_font)

    # Logo einfügen
    if logo:
        img.paste(logo, (logo_x, logo_y), logo)
        foot_y = logo_y + logo.size[1] + 20
    else:
        foot_y = int(0.7*img.height) + 20

    # Fußnote
    foot = f"Abfragedatum: {stock_data.get('Abfragedatum','-')}, Datenquelle: {stock_data.get('Datenquelle','-')}"
    fb = foot_font.getbbox(foot)
    fx = (img.width - (fb[2]-fb[0]))//2
    draw.text((fx, foot_y), foot, fill="black", font=foot_font)

    # Speichern
    out_fn = f"{ticker}_stock_image.png"
    out_fp = os.path.join(OUTPUT_FOLDER, out_fn)
    img.save(out_fp, "PNG")
    return out_fp

# --- Flask-Routes ---------------------------------------------------------

@app.route('/')
def home():
    return render_template("index.html", metrics_options=NUMERIC_COLUMNS)

@app.route('/generate_image', methods=['POST'])
def generate_image():
    ticker   = request.form.get('ticker','').upper().strip()
    selected = request.form.getlist('metrics')
    # Validierung
    if not ticker:
        return render_template("index.html", metrics_options=NUMERIC_COLUMNS, error="Bitte einen Ticker angeben!"), 400
    if not selected:
        return render_template("index.html", metrics_options=NUMERIC_COLUMNS, error="Bitte mindestens eine Kennzahl wählen!"), 400
    if len(selected) > 8:
        return render_template("index.html", metrics_options=NUMERIC_COLUMNS, error="Maximal 8 Kennzahlen erlaubt!"), 400
    data = get_stock_data(ticker)
    if not data:
        return render_template("index.html", metrics_options=NUMERIC_COLUMNS, error=f"Keine Daten für Ticker '{ticker}' gefunden."), 400
    log_ticker_usage(ticker)
    out_fp = create_stock_image(DEFAULT_BACKGROUND, data, ticker, selected)
    return redirect(url_for('display_result', filename=os.path.basename(out_fp)))

@app.route('/display_result/<filename>')
def display_result(filename):
    return render_template("display_result.html", filename=filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('q','').strip().lower()
    if not q:
        return {"results":[]}, 200
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df.rename(columns={"AusschÃ¼ttungsquote": "Ausschüttungsquote"}, inplace=True)
    except Exception as e:
        return {"error":f"CSV-Fehler: {e}"}, 500
    df['sec_low'] = df['Security'].str.lower()
    res = df[df['sec_low'].str.contains(q)]
    out = res[['Symbol','Security']].head(10).to_dict(orient='records')
    return {"results":out}, 200

# --- Cleanup-Thread -------------------------------------------------------

def cleanup_old_images(interval=300, max_age=1800):
    while True:
        now = time.time()
        for fn in os.listdir(OUTPUT_FOLDER):
            fp = os.path.join(OUTPUT_FOLDER, fn)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age:
                os.remove(fp)
        time.sleep(interval)

threading.Thread(target=cleanup_old_images, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
