from flask import Flask, request, send_file, render_template, redirect, url_for, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import math

app = Flask(__name__)

# Ordner für hochgeladene und generierte Dateien
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Beispiel: CSV-Datei und Font-Pfad
CSV_FILE = 'stock_data.csv'
FONT_PATH = 'static/fonts/Montserrat-Bold.ttf'

@app.route('/')
def home():
    """Startseite mit Formular."""
    return render_template("index.html")

@app.route('/generate_image', methods=['POST'])
def generate_image():
    """Nimmt Ticker + Hintergrund entgegen, erzeugt das Bild und leitet weiter."""
    ticker = request.form.get('ticker', '').upper()
    if not ticker:
        return "Bitte einen Ticker angeben!", 400

    # CSV-Daten auslesen
    stock_data = get_stock_data(ticker)
    if not stock_data:
        return f"Keine Daten für Ticker '{ticker}' gefunden.", 400

    # Hintergrundbild speichern
    if 'background' not in request.files:
        return "Bitte ein Hintergrundbild hochladen!", 400
    background_file = request.files['background']
    if background_file.filename == '':
        return "Ungültiger Dateiname.", 400
    background_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    background_file.save(background_path)

    # Bild erzeugen
    output_path = create_stock_image(background_path, stock_data, ticker)

    # Dateiname extrahieren
    filename = os.path.basename(output_path)

    # Weiterleitung zur Ergebnis-Seite
    return redirect(url_for('display_result', filename=filename))

@app.route('/display_result/<filename>')
def display_result(filename):
    """
    Zeigt das generierte Bild an und bietet Download-Link.
    filename: Name der Bilddatei im Ordner output/
    """
    return render_template("display_result.html", filename=filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    """
    Liefert die generierte Bilddatei aus dem output-Ordner aus.
    """
    return send_from_directory(OUTPUT_FOLDER, filename)

def get_stock_data(ticker):
    """Dein Code zum Auslesen aus der CSV-Datei."""
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"Fehler beim Einlesen der CSV: {e}")
        return None

    # Datenbereinigung
    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    df["Dividendenrendite"] = pd.to_numeric(df["Dividendenrendite"], errors='coerce')
    df["KGV"] = pd.to_numeric(df["KGV"], errors='coerce')
    df["KUV"] = pd.to_numeric(df["KUV"], errors='coerce')
    df = df.dropna(subset=["Dividendenrendite", "KGV", "KUV"])

    row = df[df["Symbol"] == ticker]
    if row.empty:
        return None

    return {
        "Unternehmensname": row.iloc[0]["Security"],
        "Dividendenrendite": row.iloc[0]["Dividendenrendite"],
        "KGV": row.iloc[0]["KGV"],
        "KUV": row.iloc[0]["KUV"]
    }

def create_stock_image(background_path, stock_data, ticker):
    """Erzeugt das Bild und speichert es unter output/."""
    # Hintergrund laden
    img = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Schriften laden
    try:
        font = ImageFont.truetype(FONT_PATH, 40)
        title_font = ImageFont.truetype(FONT_PATH, 60)
    except:
        font = ImageFont.load_default()
        title_font = font

    # Logo einfügen (falls vorhanden)
    logo_path = f"static/logos/{ticker}.png"
    center_x = img.width // 2
    center_y = img.height // 2

    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo_size = 250
        logo = logo.resize((logo_size, logo_size))
        center_x = img.width // 2 - logo_size // 2
        center_y = img.height // 2 - logo_size // 2 + 50
        img.paste(logo, (center_x, center_y), logo)

    # Titel
    title_text = f"Aktie: {stock_data['Unternehmensname']}"
    title_bbox = title_font.getbbox(title_text)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((img.width // 2 - title_width // 2, 50), title_text, fill="black", font=title_font)

    # Kennzahlen kreisförmig
    radius = 250
    text_items = [
        f"Dividendenrendite: {stock_data['Dividendenrendite']:.2f}%",
        f"KGV: {stock_data['KGV']:.2f}",
        f"KUV: {stock_data['KUV']:.2f}"
    ]
    angle_step = 360 / len(text_items)

    # Mittelpunkt für den Kreis = Logo-Mitte
    logo_center_x = center_x + 125  # 125 = Hälfte von logo_size
    logo_center_y = center_y + 125

    for i, text in enumerate(text_items):
        angle = math.radians(i * angle_step)
        text_x = int(logo_center_x + radius * math.cos(angle))
        text_y = int(logo_center_y + radius * math.sin(angle))
        draw.text((text_x, text_y), text, fill="black", font=font, anchor="mm")

    # Bild speichern
    output_filename = f"{ticker}_stock_image.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    img.save(output_path, "PNG")

    return output_path

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
