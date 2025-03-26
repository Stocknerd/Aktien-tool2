from flask import Flask, request, send_file, render_template, redirect, url_for, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import math

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CSV_FILE = 'stock_data.csv'
FONT_PATH = 'static/fonts/Montserrat-Bold.ttf'

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

    if 'background' not in request.files:
        return "Bitte ein Hintergrundbild hochladen!", 400
    background_file = request.files['background']
    if background_file.filename == '':
        return "Ungültiger Dateiname.", 400
    background_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    background_file.save(background_path)

    output_path = create_stock_image(background_path, stock_data, ticker)
    filename = os.path.basename(output_path)

    return redirect(url_for('display_result', filename=filename))

@app.route('/display_result/<filename>')
def display_result(filename):
    return render_template("display_result.html", filename=filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

def get_stock_data(ticker):
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"Fehler beim Einlesen der CSV: {e}")
        return None

    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    numeric_columns = [
        "Dividendenrendite",
        "KGV",
        "KUV",
        "Eigenkapitalrendite",
        "ROCE",
        "Renditeerwartung",
        "Bruttomarge",
        "EBITDA-Marge"
    ]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Zeilen entfernen, in denen wichtige Werte fehlen
    df = df.dropna(subset=numeric_columns)

    # Passende Zeile zum Ticker herausfiltern
    row = df[df["Symbol"] == ticker]
    if row.empty:
        return None

    # Dictionary bauen
    data = {col: row.iloc[0][col] for col in numeric_columns + ["Security"]}

    # Hier die Spalten multiplizieren, die in der CSV als Dezimal (z.B. 0.20 statt 20.0) vorliegen
    # (Beispiel: Alle außer Dividendenrendite, KGV, KUV)
    data["Eigenkapitalrendite"] *= 100
    data["ROCE"] *= 100
    data["Renditeerwartung"] *= 100
    data["Bruttomarge"] *= 100
    data["EBITDA-Marge"] *= 100

    return data


def create_stock_image(background_path, stock_data, ticker):
    """
    - Logo (200 px Höhe) im unteren Bildbereich (~70% der Bildhöhe).
    - Kennzahlen (Grid) mit 2 Spalten x 4 Zeilen, kleinerer Schrift.
    - Titel: "Aktie: <Name> (<TICKER>)"
    - Grid noch etwas weiter unten positioniert (z.B. +100 px nach dem Titel).
    """
    from PIL import Image, ImageDraw, ImageFont
    import math

    # Hintergrundbild laden
    img = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Schriftarten
    try:
        font = ImageFont.truetype(FONT_PATH, 30)       # Kennzahlen
        title_font = ImageFont.truetype(FONT_PATH, 50) # Titel
    except:
        font = ImageFont.load_default()
        title_font = font

    # -- Titel oben zentriert --
    # Tickersymbol in Klammern dahinter
    title_text = f"Aktie: {stock_data['Security']} ({ticker})"
    title_bbox = title_font.getbbox(title_text)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    title_x = (img.width - title_width) // 2
    title_y = 50  # 50 px vom oberen Rand
    draw.text((title_x, title_y), title_text, fill="black", font=title_font)

    # -- Logo vorbereiten (200 px Höhe) --
    logo_path = f"static/logos/{ticker}.png"
    new_width = new_height = 0
    logo_x = logo_y = 0

    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        orig_w, orig_h = logo.size

        target_height = 200
        scale_factor = target_height / float(orig_h)
        new_width = int(orig_w * scale_factor)
        new_height = target_height

        # Neuere Pillow-Versionen: Image.Resampling.LANCZOS
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Logo bei ~70% der Bildhöhe zentriert platzieren
        logo_center_y = int(0.7 * img.height)
        logo_x = (img.width - new_width) // 2
        logo_y = logo_center_y - (new_height // 2)
    else:
        # Fallback, falls kein Logo vorhanden
        logo_x = img.width // 2
        logo_y = int(0.7 * img.height)

    # -- Kennzahlen in Grid (2x4) --
    text_items = [
        f"Dividendenrendite: {stock_data['Dividendenrendite']:.2f}%",
        f"KGV: {stock_data['KGV']:.2f}",
        f"KUV: {stock_data['KUV']:.2f}",
        f"Eigenkapitalrendite: {stock_data['Eigenkapitalrendite']:.2f}%",
        f"ROCE: {stock_data['ROCE']:.2f}%",
        f"Renditeerwartung: {stock_data['Renditeerwartung']:.2f}%",
        f"Bruttomarge: {stock_data['Bruttomarge']:.2f}%",
        f"EBITDA-Marge: {stock_data['EBITDA-Marge']:.2f}%"
    ]

    items_per_row = 2
    total_items = len(text_items)
    row_count = (total_items + items_per_row - 1) // items_per_row  # = 4 bei 8 Items

    # Startpunkt für Kennzahlen (etwas weiter unten als bisher: +100 statt +30)
    grid_top = title_y + title_height + 100
    # Untere Grenze für das Grid (etwas über dem Logo)
    grid_bottom = logo_y - 30

    # Höhe für Kennzahlen
    available_height = max(1, grid_bottom - grid_top)

    # Zeilenhöhe: verteile den Platz, Mindesthöhe 50 px
    row_height = available_height // row_count if row_count > 0 else 50
    row_height = max(row_height, 50)

    # Grid-Breite: links und rechts 100 px Rand
    grid_left = 100
    grid_right = img.width - 100
    grid_width = grid_right - grid_left

    # Spaltenbreite
    col_width = grid_width // items_per_row

    for i, text in enumerate(text_items):
        row = i // items_per_row
        col = i % items_per_row

        x_pos = grid_left + col * col_width + 10
        y_pos = grid_top + row * row_height

        draw.text((x_pos, y_pos), text, fill="black", font=font)

    # -- Logo zuletzt einfügen --
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img.paste(logo, (logo_x, logo_y), logo)

    # -- Bild speichern --
    output_filename = f"{ticker}_stock_image.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    img.save(output_path, "PNG")

    return output_path


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
