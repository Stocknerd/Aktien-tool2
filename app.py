from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import threading
import time
import os
import math
import pandas as pd
import logging

# ----------------------------------------
# --- Initiale Konfiguration ------------
# ----------------------------------------
app = Flask(__name__)

# Basis-Pfade & Konstanten
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['LOG_FOLDER'] = 'logs'
app.config['CSV_FILE'] = 'stock_data.csv'
app.config['FONT_PATH'] = 'static/fonts/Montserrat-Bold.ttf'
app.config['DEFAULT_BACKGROUND'] = 'static/default_background.png'
app.config['MAX_METRICS'] = 8

# Default-Kennzahlen (max. 8)
app.config['DEFAULT_METRICS'] = [
    "Dividendenrendite",
    "Ausschüttungsquote",
    "KUV",
    "KGV",
    "Gewinn je Aktie",
    "Marktkapitalisierung",
    "Gewinnwachstum 5J",
    "Umsatzwachstum 10J",
]

# Alle verfügbaren Kennzahlen
app.config['NUMERIC_COLUMNS'] = [
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

# Suffix- und Genauigkeits-Maps (für Formatierung)
app.config['SUFFIX_MAP'] = {
    **{k: '%' for k in [
        "Dividendenrendite","Ausschüttungsquote","Gewinnwachstum 5J","Umsatzwachstum 10J",
        "Bruttomarge","Operative Marge","Nettomarge",
        "Eigenkapitalrendite","Return on Assets","ROIC",
        "52Wochen Change","Insider_Anteil","Institutioneller_Anteil","Short Interest"
    ]},
    "Marktkapitalisierung": " Mrd. $",
    **{k: '' for k in app.config['NUMERIC_COLUMNS'] if k not in [
        "Dividendenrendite","Ausschüttungsquote","Gewinnwachstum 5J","Umsatzwachstum 10J",
        "Bruttomarge","Operative Marge","Nettomarge",
        "Eigenkapitalrendite","Return on Assets","ROIC",
        "52Wochen Change","Insider_Anteil","Institutioneller_Anteil","Short Interest",
        "Marktkapitalisierung"
    ]}
}
app.config['PRECISION_MAP'] = {k: 2 for k in app.config['NUMERIC_COLUMNS']}

# Ordner anlegen (falls noch nicht vorhanden)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)
log_file_path = os.path.join(app.config['LOG_FOLDER'], "ticker_log.csv")

# Globals: DataFrame und letzter MTime-Wert
STOCK_DF = None
LAST_CSV_MTIME = None

# Logger einrichten
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(app.config['LOG_FOLDER'], "app.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ----------------------------------------
# --- Helper-Funktionen -----------------
# ----------------------------------------

def load_stock_dataframe():
    """
    Lädt die CSV-Datei nur neu, wenn sie seit dem letzten Laden verändert wurde.
    Speichert anschließend den neuen MTime-Wert.
    """
    global STOCK_DF, LAST_CSV_MTIME
    csv_path = app.config['CSV_FILE']

    # Versuche, aktuellen MTime der CSV zu ermitteln
    try:
        current_mtime = os.path.getmtime(csv_path)
    except Exception as e:
        logger.error(f"Kann MTime der CSV '{csv_path}' nicht lesen: {e}")
        current_mtime = None

    # Wenn schon geladen und keine Änderung: return
    if LAST_CSV_MTIME is not None and current_mtime == LAST_CSV_MTIME:
        return

    # CSV wurde geändert oder noch nie geladen: neu einlesen
    try:
        df = pd.read_csv(
            csv_path,
            sep=None,
            engine="python",
            encoding="ISO-8859-1",
            on_bad_lines="skip"
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der CSV '{csv_path}': {e}")
        STOCK_DF = pd.DataFrame()
        LAST_CSV_MTIME = current_mtime
        return

    # Spaltennamen bereinigen
    df.columns = df.columns.str.strip()
    if "AusschÃ¼ttungsquote" in df.columns:
        df.rename(columns={"AusschÃ¼ttungsquote": "Ausschüttungsquote"}, inplace=True)

    # Symbol in Großbuchstaben
    if "Symbol" in df.columns:
        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
    else:
        logger.warning("CSV enthält keine Spalte 'Symbol'.")

    # Numerische Spalten forcieren
    for col in app.config['NUMERIC_COLUMNS']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Hilfsfeld für Suche (kleingeschrieben)
    if "Security" in df.columns:
        df["__name_low"] = df["Security"].astype(str).str.lower()
    else:
        df["__name_low"] = ""

    STOCK_DF = df.set_index("Symbol", drop=False)
    LAST_CSV_MTIME = current_mtime
    logger.info(f"Stock DataFrame geladen (Zeilen: {len(STOCK_DF)}), MTime: {LAST_CSV_MTIME}.")


def log_ticker_usage(ticker: str):
    """
    Protokolliert jeden aufgerufenen Ticker in eine CSV (Zeitstempel, Ticker).
    """
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"{ts},{ticker}\n")
    except Exception as e:
        logger.error(f"Konnte Ticker-Log nicht schreiben: {e}")


def get_stock_data(ticker: str) -> dict:
    """
    Liest den Datensatz aus dem globalen DataFrame STOCK_DF.
    Prüft vorher, ob die CSV neu eingelesen werden muss.
    """
    # Prüfe auf CSV-Update
    load_stock_dataframe()

    global STOCK_DF
    if STOCK_DF is None or STOCK_DF.empty:
        logger.error("Stock-DataFrame ist leer. get_stock_data kann keine Ergebnisse liefern.")
        return None

    ticker = ticker.strip().upper()
    try:
        row = STOCK_DF.loc[ticker]
    except KeyError:
        return None

    data = {"Security": row.get("Security", "-")}
    # Kennzahlen übernehmen
    for col in app.config['NUMERIC_COLUMNS']:
        val = row.get(col, None)
        data[col] = None if pd.isna(val) else val

    # Abfragedatum formatieren
    orig = row.get("Abfragedatum", None)
    if isinstance(orig, str):
        try:
            parsed = datetime.strptime(orig, "%Y-%m-%d")
            data["Abfragedatum"] = parsed.strftime("%d.%m.%Y")
        except Exception:
            data["Abfragedatum"] = orig
    else:
        data["Abfragedatum"] = "-"

    data["Datenquelle"] = row.get("Datenquelle", "-")
    return data


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """
    Bricht lange Titelzeilen in mehrere Zeilen um, sodass sie in die Bildbreite passen.
    """
    words = text.split(' ')
    lines: list[str] = []
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


def create_stock_image(bg_path: str, stock_data: dict, ticker: str, metrics: list[str]) -> str:
    """
    Erzeugt aus den Daten und dem Hintergrundbild eine Grafik
    und speichert diese unter OUTPUT_FOLDER.
    """
    # Hintergrundbild laden
    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Fonts laden (Fallback)
    try:
        title_font = ImageFont.truetype(app.config['FONT_PATH'], 50)
        body_font  = ImageFont.truetype(app.config['FONT_PATH'], 30)
        foot_font  = ImageFont.truetype(app.config['FONT_PATH'], 20)
    except Exception:
        title_font = ImageFont.load_default()
        body_font  = ImageFont.load_default()
        foot_font  = ImageFont.load_default()

    # Titel zeichnen
    title = f"Aktie: {stock_data['Security']} ({ticker})"
    lines = wrap_text(title, title_font, img.width - 100)
    y = 50
    for line in lines:
        bbox = title_font.getbbox(line)
        x = (img.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill="black", font=title_font)
        y += (bbox[3] - bbox[1]) + 10
    title_height = y - 50 - 10

    # Logo skalieren und positionieren
    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        ow, oh = logo.size
        target_h = 200
        scale = target_h / oh
        nw, nh = int(ow * scale), target_h
        max_w = img.width - 200
        if nw > max_w:
            scale = max_w / ow
            nw, nh = max_w, int(oh * scale)
        logo = logo.resize((nw, nh), Image.Resampling.LANCZOS)
        logo_x = (img.width - nw) // 2
        logo_y = int(0.7 * img.height) - nh // 2
    else:
        logo = None
        logo_x = img.width // 2
        logo_y = int(0.7 * img.height)

    # Formatierungsfunktion
    def fmt(val, suffix, prec):
        if val is None:
            return '-'
        if suffix == '%':
            val *= 100
        if suffix == ' Mrd. $':
            val /= 1e9
        return f"{val:.{prec}f}{suffix}"

    # Kennzahlen-Text vorbereiten
    items: list[str] = []
    for key in metrics:
        raw = stock_data.get(key)
        text = fmt(raw, app.config['SUFFIX_MAP'].get(key, ''), app.config['PRECISION_MAP'].get(key, 2))
        items.append(f"{key}: {text}")

    # Kennzahlen in zwei Spalten anordnen
    cols = 2
    rows = math.ceil(len(items) / cols)
    top_y = 50 + title_height + 100
    bottom_y = (logo_y - 30) if logo else (img.height - 200)
    avail_h = max(1, bottom_y - top_y)
    row_h = max(avail_h // rows, 50)
    left_x, right_x = 100, img.width - 100
    col_w = (right_x - left_x) // cols

    for idx, txt in enumerate(items):
        r, c = divmod(idx, cols)
        x = left_x + c * col_w + 10
        y = top_y + r * row_h
        draw.text((x, y), txt, fill="black", font=body_font)

    # Logo und Fußzeile
    if logo:
        img.paste(logo, (logo_x, logo_y), logo)
        foot_y = logo_y + logo.size[1] + 20
    else:
        foot_y = int(0.7 * img.height) + 20

    foot_text = f"Abfragedatum: {stock_data.get('Abfragedatum','-')}, Datenquelle: {stock_data.get('Datenquelle','-')}"
    fb = foot_font.getbbox(foot_text)
    fx = (img.width - (fb[2] - fb[0])) // 2
    draw.text((fx, foot_y), foot_text, fill="black", font=foot_font)

    # Datei speichern
    out_fn = f"{ticker}_stock_image.png"
    out_fp = os.path.join(app.config['OUTPUT_FOLDER'], out_fn)
    img.save(out_fp, "PNG")
    return out_fp

# ----------------------------------------
# --- Routen / Endpoints ----------------
# ----------------------------------------

@app.route('/')
def home():
    """
    Startseite mit Formular und Checkboxen.
    """
    return render_template(
        "index.html",
        metrics_options=app.config['NUMERIC_COLUMNS'],
        selected_metrics=app.config['DEFAULT_METRICS']
    )

@app.route('/generate_image', methods=['POST'])
def generate_image():
    """
    Form-Handler: prüft Ticker und Kennzahlen, erzeugt Bild und leitet auf
    die Anzeige-Route weiter.
    """
    ticker = request.form.get('ticker', '').upper().strip()
    selected = request.form.getlist('metrics')

    # Validierungen
    if not ticker:
        return render_template(
            "index.html",
            metrics_options=app.config['NUMERIC_COLUMNS'],
            selected_metrics=app.config['DEFAULT_METRICS'],
            error="Bitte einen Ticker angeben!"
        ), 400

    if not selected:
        return render_template(
            "index.html",
            metrics_options=app.config['NUMERIC_COLUMNS'],
            selected_metrics=app.config['DEFAULT_METRICS'],
            error="Bitte mindestens eine Kennzahl wählen!"
        ), 400

    if len(selected) > app.config['MAX_METRICS']:
        return render_template(
            "index.html",
            metrics_options=app.config['NUMERIC_COLUMNS'],
            selected_metrics=app.config['DEFAULT_METRICS'],
            error=f"Maximal {app.config['MAX_METRICS']} Kennzahlen erlaubt!"
        ), 400

    data = get_stock_data(ticker)
    if not data:
        return render_template(
            "index.html",
            metrics_options=app.config['NUMERIC_COLUMNS'],
            selected_metrics=app.config['DEFAULT_METRICS'],
            error=f"Keine Daten für Ticker '{ticker}' gefunden."
        ), 400

    log_ticker_usage(ticker)
    try:
        out_fp = create_stock_image(app.config['DEFAULT_BACKGROUND'], data, ticker, selected)
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Bildes für {ticker}: {e}")
        return render_template(
            "index.html",
            metrics_options=app.config['NUMERIC_COLUMNS'],
            selected_metrics=app.config['DEFAULT_METRICS'],
            error="Fehler bei der Bilderstellung."
        ), 500

    filename = os.path.basename(out_fp)
    return redirect(url_for('display_result', filename=filename))

@app.route('/display_result/<filename>')
def display_result(filename: str):
    """
    Zeigt das generierte Bild und Download-Link an.
    """
    return render_template("display_result.html", filename=filename)

@app.route('/output/<path:filename>')
def output_file(filename: str):
    """
    Gibt die generierten Bilder aus dem OUTPUT_FOLDER aus.
    """
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/search', methods=['GET'])
def search():
    """
    Rückgabe von Unternehmensergebnissen als JSON für die Autocomplete-Suche.
    Vor Filterung prüfen wir, ob CSV-Update nötig ist.
    """
    q = request.args.get('q', '').strip().lower()
    if len(q) < 2:
        return jsonify(results=[])

    # Bevor wir den DataFrame nutzen, checken wir, ob die CSV neu eingelesen werden muss
    load_stock_dataframe()

    global STOCK_DF
    if STOCK_DF is None or STOCK_DF.empty:
        return jsonify(results=[]), 500

    hits = STOCK_DF[STOCK_DF["__name_low"].str.contains(q, na=False)]
    results = []
    for _, row in hits.head(10).iterrows():
        results.append({
            "Symbol": row["Symbol"],
            "Security": row["Security"]
        })
    return jsonify(results=results)

# ----------------------------------------
# --- Cleanup-Thread --------------------
# ----------------------------------------

def cleanup_old_images(interval: int = 300, max_age: int = 1800):
    """
    Löscht alle Bilder im OUTPUT_FOLDER, die älter als max_age Sekunden sind.
    Läuft daemonisiert im Hintergrund.
    """
    folder = app.config['OUTPUT_FOLDER']
    while True:
        now = time.time()
        for fn in os.listdir(folder):
            fp = os.path.join(folder, fn)
            try:
                if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age:
                    os.remove(fp)
                    logger.info(f"Altes Bild gelöscht: {fn}")
            except Exception as e:
                logger.error(f"Fehler beim Löschen von {fn}: {e}")
        time.sleep(interval)

# ----------------------------------------
# --- Starten (development) -------------
# ----------------------------------------
if __name__ == '__main__':
    # Direkt beim Start CSV laden (und MTime speichern)
    load_stock_dataframe()
    # Cleanup-Thread starten (löscht alte Bilder alle 5 Minuten)
    threading.Thread(target=cleanup_old_images, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=5000)
