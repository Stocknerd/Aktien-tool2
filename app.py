from flask import Flask, request, send_file, render_template, redirect, url_for, send_from_directory
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import threading
import time
import pandas as pd
import os
import math

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# Log-Verzeichnis
os.makedirs("logs", exist_ok=True)
LOG_FILE = os.path.join("logs", "ticker_log.csv")

def log_ticker_usage(ticker):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp},{ticker}\n")
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)


CSV_FILE = 'stock_data.csv'
FONT_PATH = 'static/fonts/Montserrat-Bold.ttf'

# NEU: Standard-Hintergrund festlegen
DEFAULT_BACKGROUND = 'static/default_background.png'  # Pfad zu deinem Default-Bild

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate_image', methods=['POST'])
def generate_image():
    ticker = request.form.get('ticker', '').upper()
    if not ticker:
        return "Bitte einen Ticker angeben!", 400

    stock_data = get_stock_data(ticker)
    if not stock_data:
        return f"Keine Daten für Ticker '{ticker}' gefunden.", 400
    log_ticker_usage(ticker)

    # Ab hier ENTFERNT: kein Upload mehr nötig
    # ----------------------------------------------------------
    # if 'background' not in request.files:
    #     return "Bitte ein Hintergrundbild hochladen!", 400
    # background_file = request.files['background']
    # if background_file.filename == '':
    #     return "Ungültiger Dateiname.", 400
    # background_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    # background_file.save(background_path)
    # ----------------------------------------------------------

    # STATT DESSEN: Immer das Default-Hintergrundbild verwenden
    background_path = DEFAULT_BACKGROUND

    output_path = create_stock_image(background_path, stock_data, ticker)
    filename = os.path.basename(output_path)

    return redirect(url_for('display_result', filename=filename))

@app.route('/display_result/<filename>')
def display_result(filename):
    return render_template("display_result.html", filename=filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip().lower()  # Suchbegriff aus der URL
    if not query:
        return {"results": []}, 200

    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
    except Exception as e:
        return {"error": f"Fehler beim Einlesen der CSV: {e}"}, 500

    # Für case-insensitive Suche
    df['Security_lower'] = df['Security'].str.lower()
    results_df = df[df['Security_lower'].str.contains(query)]
    results = results_df[['Symbol', 'Security']].head(10).to_dict(orient='records')
    return {"results": results}, 200

def get_stock_data(ticker):
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df.rename(columns={"AusschÃ¼ttungsquote": "Ausschüttungsquote"}, inplace=True)
    except Exception as e:
        print(f"Fehler beim Einlesen der CSV: {e}")
        return None

    df["Symbol"] = df["Symbol"].str.strip().str.upper()

    numeric_columns = [
        "Dividendenrendite",
        "Ausschüttungsquote",
        "KUV",
        "KGV",
        "Gewinn je Aktie",
        "Marktkapitalisierung",
        "Gewinnwachstum 5J",
        "Umsatzwachstum 10J"
    ]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    row = df[df["Symbol"] == ticker]
    if row.empty:
        return None

    row = row.iloc[0]
    data = {"Security": row["Security"]}
    for col in numeric_columns:
        value = row[col]
        data[col] = value if not pd.isna(value) else None

    # Neuen Code einfügen: Abfragedatum ins deutsche Format umwandeln
    original_date = row.get("Abfragedatum")
    if original_date:
        try:
            # Hier wird angenommen, dass das Datum im CSV-Format "YYYY-MM-DD" vorliegt.
            parsed_date = datetime.strptime(original_date, "%Y-%m-%d")
            data["Abfragedatum"] = parsed_date.strftime("%d.%m.%Y")
        except Exception as e:
            # Falls das Parsing fehlschlägt, wird der Originalwert beibehalten.
            data["Abfragedatum"] = original_date
    else:
        data["Abfragedatum"] = "-"

    # Übernehme auch die Datenquelle
    data["Datenquelle"] = row.get("Datenquelle", "-")

    # Beispielhafte Umrechnungen


    if data["Ausschüttungsquote"] < 1:
        data["Ausschüttungsquote"] *= 100

    data["Marktkapitalisierung_Mrd"] = (
        data["Marktkapitalisierung"] / 1e9 if data["Marktkapitalisierung"] is not None else None
    )
    data["Gewinnwachstum_5J_pct"] = (
        data["Gewinnwachstum 5J"] * 100 if data["Gewinnwachstum 5J"] is not None else None
    )
    data["Umsatzwachstum_10J_pct"] = (
        data["Umsatzwachstum 10J"] * 100 if data["Umsatzwachstum 10J"] is not None else None
    )

    return data



def wrap_text(text, font, max_width):
    """Zerteilt einen Text in mehrere Zeilen, sodass jede Zeile maximal max_width Pixel breit ist."""
    words = text.split(' ')
    lines = []
    current_line = words[0]

    for word in words[1:]:
        # Prüfe, ob das Hinzufügen des nächsten Wortes die maximale Breite überschreitet
        test_line = current_line + ' ' + word
        line_width = font.getbbox(test_line)[2] - font.getbbox(test_line)[0]
        if line_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines



def create_stock_image(background_path, stock_data, ticker):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, 30)
        title_font = ImageFont.truetype(FONT_PATH, 50)
    except:
        font = ImageFont.load_default()
        title_font = font

    # Neuer Abschnitt: Automatischer Zeilenumbruch für den Titel,
    # wobei title_y und title_height für den späteren Gebrauch berechnet werden.

    title_text = f"Aktie: {stock_data['Security']} ({ticker})"
    max_title_width = img.width - 100  # Maximale Breite mit Rand
    title_lines = wrap_text(title_text, title_font, max_title_width)

    title_y = 50  # Start-Y-Position der Überschrift
    current_y = title_y
    for line in title_lines:
        line_bbox = title_font.getbbox(line)
        line_width = line_bbox[2] - line_bbox[0]
        line_height = line_bbox[3] - line_bbox[1]
        line_x = (img.width - line_width) // 2
        draw.text((line_x, current_y), line, fill="black", font=title_font)
        current_y += line_height + 10  # Abstand zwischen den Zeilen

    # Berechne die Gesamthöhe der Überschrift, ohne den letzten zusätzlichen Abstand
    title_height = current_y - title_y - 10

    # Für den nächsten Bereich (z. B. die Tabelle) wird grid_top so berechnet wie zuvor:
    grid_top = title_y + title_height + 100

    # Logo (unverändert)
    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        orig_w, orig_h = logo.size
        target_height = 200
        # Berechne zuerst die neue Größe basierend auf target_height
        scale_factor = target_height / float(orig_h)
        new_width = int(orig_w * scale_factor)
        new_height = target_height

        # Definiere den maximal verfügbaren Platz (z.B. 100 Pixel Rand auf jeder Seite)
        available_width = img.width - 200
        if new_width > available_width:
            # Berechne neu, wenn das Logo zu breit ist
            scale_factor = available_width / orig_w
            new_width = available_width
            new_height = int(orig_h * scale_factor)

        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logo_center_y = int(0.7 * img.height)
        logo_x = (img.width - new_width) // 2
        logo_y = logo_center_y - (new_height // 2)
    else:
        logo_x = img.width // 2
        logo_y = int(0.7 * img.height)

    def format_value(value, suffix='', precision=2):
        return f"{value:.{precision}f}{suffix}" if value is not None else "-"

    text_items = [
        f"Dividendenrendite: {format_value(stock_data.get('Dividendenrendite'), '%')}",
        f"Ausschüttungsquote: {format_value(stock_data.get('Ausschüttungsquote'), '%')}",
        f"KUV: {format_value(stock_data.get('KUV'))}",
        f"KGV: {format_value(stock_data.get('KGV'))}",
        f"Gewinn je Aktie: {format_value(stock_data.get('Gewinn je Aktie'))}",
        f"Marktkap.: {format_value(stock_data.get('Marktkapitalisierung_Mrd'), ' Mrd. $')}",
        f"Gewinnwachstum: {format_value(stock_data.get('Gewinnwachstum_5J_pct'), '%')}",
        f"Umsatzwachstum: {format_value(stock_data.get('Umsatzwachstum_10J_pct'), '%')}"
    ]

    items_per_row = 2
    total_items = len(text_items)
    row_count = (total_items + items_per_row - 1) // items_per_row

    grid_top = title_y + title_height + 100
    grid_bottom = logo_y - 30
    available_height = max(1, grid_bottom - grid_top)
    row_height = max(available_height // row_count, 50)
    grid_left = 100
    grid_right = img.width - 100
    grid_width = grid_right - grid_left
    col_width = grid_width // items_per_row

    for i, text in enumerate(text_items):
        row_idx = i // items_per_row
        col_idx = i % items_per_row
        x_pos = grid_left + col_idx * col_width + 10
        y_pos = grid_top + row_idx * row_height
        draw.text((x_pos, y_pos), text, fill="black", font=font)

    if os.path.exists(logo_path):
        img.paste(logo, (logo_x, logo_y), logo)

    # Falls das Logo existiert, wird es eingefügt:
    if os.path.exists(logo_path):
        img.paste(logo, (logo_x, logo_y), logo)
        # Bestimme die Position der Fußnote: ein paar Pixel unter dem Logo
        footnote_y = logo_y + new_height + 20
    else:
        # Falls kein Logo vorhanden ist, definiere eine Standardposition
        footnote_y = int(0.7 * img.height) + 20

    # Erstelle einen kleineren Font für die Fußnote
    try:
        footnote_font = ImageFont.truetype(FONT_PATH, 20)
    except:
        footnote_font = ImageFont.load_default()

    # Formatiere den Fußnotentext
    footnote_text = (
        f"Abfragedatum: {stock_data.get('Abfragedatum', '-')}, "
        f"Datenquelle: {stock_data.get('Datenquelle', '-')}"
    )

    # Zentriere den Fußnotentext horizontal
    footnote_bbox = footnote_font.getbbox(footnote_text)
    footnote_width = footnote_bbox[2] - footnote_bbox[0]
    footnote_x = (img.width - footnote_width) // 2

    # Zeichne den Fußnotentext
    draw.text((footnote_x, footnote_y), footnote_text, fill="black", font=footnote_font)

    output_filename = f"{ticker}_stock_image.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    img.save(output_path, "PNG")
    return output_path

def cleanup_old_images(interval=300, max_age=1800):  # alle 5 Min prüfen, 30 Min alt
    while True:
        now = time.time()
        for filename in os.listdir("output"):
            filepath = os.path.join("output", filename)
            if os.path.isfile(filepath):
                if now - os.path.getmtime(filepath) > max_age:
                    os.remove(filepath)
        time.sleep(interval)

# Thread starten
cleanup_thread = threading.Thread(target=cleanup_old_images, daemon=True)
cleanup_thread.start()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
