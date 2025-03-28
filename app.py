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

    df = df.dropna(subset=numeric_columns)

    row = df[df["Symbol"] == ticker]
    if row.empty:
        return None

    data = {col: row.iloc[0][col] for col in numeric_columns + ["Security"]}

    # Beispielhafte Umrechnungen
    if data["Dividendenrendite"] < 1:
        data["Dividendenrendite"] *= 100
    if data["Ausschüttungsquote"] < 1:
        data["Ausschüttungsquote"] *= 100

    data["Marktkapitalisierung_Mrd"] = data["Marktkapitalisierung"] / 1e9
    data["Gewinnwachstum_5J_pct"] = data["Gewinnwachstum 5J"] * 100
    data["Umsatzwachstum_10J_pct"] = data["Umsatzwachstum 10J"] * 100

    return data

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

    title_text = f"Aktie: {stock_data['Security']} ({ticker})"
    title_bbox = title_font.getbbox(title_text)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_x = (img.width - title_width) // 2
    title_y = 50
    draw.text((title_x, title_y), title_text, fill="black", font=title_font)

    # Logo (unverändert)
    logo_path = f"static/logos/{ticker}.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        orig_w, orig_h = logo.size
        target_height = 200
        scale_factor = target_height / float(orig_h)
        new_width = int(orig_w * scale_factor)
        new_height = target_height
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logo_center_y = int(0.7 * img.height)
        logo_x = (img.width - new_width) // 2
        logo_y = logo_center_y - (new_height // 2)
    else:
        logo_x = img.width // 2
        logo_y = int(0.7 * img.height)

    # Kennzahlen
    text_items = [
        f"Dividendenrendite: {stock_data['Dividendenrendite']:.2f}%",
        f"Ausschüttungsquote: {stock_data['Ausschüttungsquote']:.2f}%",
        f"KUV: {stock_data['KUV']:.2f}",
        f"KGV: {stock_data['KGV']:.2f}",
        f"Gewinn je Aktie: {stock_data['Gewinn je Aktie']:.2f}",
        f"Marktkapitalisierung: {stock_data['Marktkapitalisierung_Mrd']:.2f} Mrd. $",
        f"Gewinnwachstum: {stock_data['Gewinnwachstum_5J_pct']:.2f}%",
        f"Umsatzwachstum: {stock_data['Umsatzwachstum_10J_pct']:.2f}%"
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
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img.paste(logo, (logo_x, logo_y), logo)

    output_filename = f"{ticker}_stock_image.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    img.save(output_path, "PNG")
    return output_path

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
