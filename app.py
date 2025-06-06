from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os
import math

app = Flask(__name__)

# -------------------------------------------------
# Ordner & Pfade
# -------------------------------------------------
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CSV_FILE = "stock_data.csv"
# Passe bei Bedarf an (Windows: C:/Windows/Fonts/Arial.ttf o. Ä.)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# -------------------------------------------------
# Start‑ & Ergebnis‑Seiten
# -------------------------------------------------
@app.route("/")
def home():
    """Startseite mit Upload‑Formular und Live‑Suche."""
    return render_template("index.html")


@app.route("/generate_image", methods=["POST"])
def generate_image():
    """Erzeugt aus Ticker & Background ein Bild und leitet auf die Ergebnis‑Seite um."""
    ticker = request.form.get("ticker", "").strip().upper()
    if not ticker:
        return "Bitte einen Ticker angeben!", 400

    stock_data = get_stock_data(ticker)
    if not stock_data:
        return f"Keine Daten für Ticker '{ticker}' gefunden.", 400

    # ---------- Hintergrundbild verarbeiten ----------
    if "background" not in request.files:
        return "Bitte ein Hintergrundbild hochladen!", 400
    background_file = request.files["background"]
    if background_file.filename == "":
        return "Ungültiger Dateiname.", 400

    background_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    background_file.save(background_path)

    # ---------- Bild erzeugen ----------
    output_path = create_stock_image(background_path, stock_data, ticker)

    return redirect(url_for("display_result", filename=os.path.basename(output_path)))


@app.route("/display_result/<filename>")
def display_result(filename):
    """Zeigt das generierte PNG an."""
    return render_template("display_result.html", filename=filename)


@app.route("/output/<path:filename>")
def output_file(filename):
    """Reicht die Bilddatei aus /output durch."""
    return send_from_directory(OUTPUT_FOLDER, filename)

# -------------------------------------------------
# Live‑Suche‑Endpoint -----------------------------
# -------------------------------------------------
_df_cache = None  # Lazy‑Loaded Global‑Cache

def load_dataframe():
    """Lädt die CSV einmalig in den Speicher (Lazy‑Cache)."""
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="ISO-8859-1", on_bad_lines="skip")
        df.columns = df.columns.str.strip()
        df["Symbol"] = df["Symbol"].str.strip().str.upper()
        df["Security"] = df["Security"].str.strip()
        for col in ["Dividendenrendite", "KGV", "KUV"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["Dividendenrendite", "KGV", "KUV"], inplace=True)
        _df_cache = df
    return _df_cache


@app.get("/search")
def search():
    """Liefert max. 10 Treffer, deren Symbol oder Firmenname mit *q* beginnt (JSON)."""
    q = request.args.get("q", "").strip().upper()
    if not q:
        return jsonify([])

    df = load_dataframe()
    mask = df["Symbol"].str.startswith(q) | df["Security"].str.upper().str.startswith(q)
    results = df.loc[mask, ["Symbol", "Security"]].head(10)
    return jsonify([
        {"symbol": row.Symbol, "name": row.Security} for row in results.itertuples()
    ])

# -------------------------------------------------
# Datenzugriff ------------------------------------
# -------------------------------------------------

def get_stock_data(ticker: str):
    """Gibt ein Dict mit Kennzahlen für *ticker* zurück oder *None*."""
    df = load_dataframe()
    row = df.loc[df["Symbol"] == ticker]
    if row.empty:
        return None
    return {
        "Unternehmensname": row.iloc[0]["Security"],
        "Dividendenrendite": row.iloc[0]["Dividendenrendite"],
        "KGV": row.iloc[0]["KGV"],
        "KUV": row.iloc[0]["KUV"],
    }

# -------------------------------------------------
# Bild‑Generator ----------------------------------
# -------------------------------------------------

def create_stock_image(background_path: str, stock_data: dict, ticker: str) -> str:
    """Erzeugt die PNG‑Grafik mit Kennzahlen im Kreis und optionalem Logo."""
    img = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, 40)
        title_font = ImageFont.truetype(FONT_PATH, 60)
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    # ---------- Logo (falls vorhanden) ----------
    logo_size = 250
    center_x = img.width // 2
    center_y = img.height // 2
    logo_center = (center_x, center_y)

    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA").resize((logo_size, logo_size))
        logo_center = (center_x - logo_size // 2, center_y - logo_size // 2 + 50)
        img.paste(logo, logo_center, logo)

    # ---------- Titel ----------
    title_text = f"Aktie: {stock_data['Unternehmensname']}"
    title_w = title_font.getbbox(title_text)[2]
    draw.text((img.width // 2 - title_w // 2, 50), title_text, fill="black", font=title_font)

    # ---------- Kennzahlen ----------
    radius = 250
    text_items = [
        f"Dividendenrendite: {stock_data['Dividendenrendite']:.2f}%",
        f"KGV: {stock_data['KGV']:.2f}",
        f"KUV: {stock_data['KUV']:.2f}",
    ]
    angle_step = 360 / len(text_items)
    logo_center_x = logo_center[0] + logo_size // 2
    logo_center_y = logo_center[1] + logo_size // 2

    for i, text in enumerate(text_items):
        angle = math.radians(i * angle_step)
        x = int(logo_center_x + radius * math.cos(angle))
        y = int(logo_center_y + radius * math.sin(angle))
        draw.text((x, y), text, fill="black", font=font, anchor="mm")

    # ---------- Speichern ----------
    output_filename = f"{ticker}_stock_image.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    img.save(output_path, "PNG")
    return output_path

# -------------------------------------------------
# Main --------------------------------------------
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
