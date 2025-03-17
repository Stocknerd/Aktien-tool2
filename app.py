from flask import Flask, request, send_file, render_template
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os

app = Flask(__name__)

# CSV-Datei mit den Aktienwerten
CSV_FILE = os.path.join(os.path.dirname(__file__), "stock_data.csv")

# Pfad zur Schriftart für bessere Lesbarkeit (ändern, falls nötig)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Linux/macOS
# Falls du Windows nutzt:
# FONT_PATH = "C:/Windows/Fonts/Arial.ttf"

# Sicherstellen, dass alle benötigten Ordner existieren
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)

# 📌 Route für die Startseite
@app.route('/')
def home():
    return render_template("index.html")

# 📌 Aktien-Kennzahlen aus CSV abrufen
def get_stock_data(ticker):
    try:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()  # Spaltennamen bereinigen
    except Exception as e:
        print(f"Fehler beim Einlesen der CSV: {e}")
        return None

    # Spalten bereinigen
    df["Symbol"] = df["Symbol"].str.strip().str.upper()  # Ticker bereinigen
    df["Dividendenrendite"] = pd.to_numeric(df["Dividendenrendite"], errors='coerce')
    df["KGV"] = pd.to_numeric(df["KGV"], errors='coerce')
    df["KUV"] = pd.to_numeric(df["KUV"], errors='coerce')

    # NaN-Werte entfernen
    df = df.dropna(subset=["Dividendenrendite", "KGV", "KUV"])

    # Zeile mit dem gesuchten Ticker finden
    row = df[df["Symbol"] == ticker]
    if row.empty:
        available_tickers = df["Symbol"].unique()[:10]  # Zeige 10 verfügbare Ticker zur Hilfe
        print(f"Ticker {ticker} nicht gefunden. Verfügbare Ticker: {available_tickers}")
        return None

    return {
        "Dividendenrendite": row.iloc[0]["Dividendenrendite"],
        "KGV": row.iloc[0]["KGV"],
        "KUV": row.iloc[0]["KUV"]
    }

# 📌 Bild generieren mit Kennzahlen & Logo
def create_stock_image(background_path, stock_data, ticker):
    img = Image.open(background_path)
    draw = ImageDraw.Draw(img)

    # Schriftart laden
    try:
        font = ImageFont.truetype(FONT_PATH, 40)
    except:
        font = ImageFont.load_default()

    # Aktien-Daten auf das Bild schreiben
    draw.text((50, 50), f"Aktie: {ticker}", fill="black", font=font)
    draw.text((50, 120), f"Dividendenrendite: {stock_data['Dividendenrendite']}%", fill="black", font=font)
    draw.text((50, 190), f"KGV: {stock_data['KGV']}", fill="black", font=font)
    draw.text((50, 260), f"KUV: {stock_data['KUV']}", fill="black", font=font)

    # 📌 Unternehmenslogo einfügen (falls vorhanden)
    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo = logo.resize((100, 100))  # Logo verkleinern
        img.paste(logo, (img.width - 120, 20), logo)

    # Generiertes Bild speichern
    output_path = f"output/{ticker}_stock_image.png"
    img.save(output_path)
    return output_path

# 📌 API-Route zum Generieren des Bildes
@app.route('/generate', methods=['POST'])
def generate():
    if 'background' not in request.files or 'ticker' not in request.form:
        return "Fehlende Daten", 400

    background = request.files['background']
    ticker = request.form['ticker'].upper()

    stock_data = get_stock_data(ticker)
    if stock_data is None:
        return "Ticker nicht gefunden", 404

    # Speichere das hochgeladene Bild temporär
    background_path = f"uploads/{ticker}_bg.png"
    background.save(background_path)

    output_path = create_stock_image(background_path, stock_data, ticker)

    return send_file(output_path, mimetype='image/png', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)