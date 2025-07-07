from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_from_directory
)
import os, pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import List

# ───────────────────────── Konfiguration ─────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSV_FILE   = os.path.join(BASE_DIR, "stock_data.csv")
BACKGROUND = os.path.join(STATIC_DIR, "default_background.png")
LOGO_DIR   = os.path.join(STATIC_DIR, "logos")
FONT_DIR   = os.path.join(STATIC_DIR, "fonts")
MONTS_BOLD = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")
MONTS_REG  = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
OUT_DIR    = os.path.join(STATIC_DIR, "generated")
os.makedirs(OUT_DIR, exist_ok=True)

# Acht Standard-Kennzahlen (vorangekreuzt, max 8 auswählbar)
DEFAULT_METRICS = [
    "Dividendenrendite", "Ausschüttungsquote",
    "KUV", "KGV",
    "Gewinn je Aktie", "Marktkapitalisierung",
    "Forward PE", "KBV",
]

# Beschriftung (Kurzform) fürs fertige Bild
METRIC_LABELS = {
    "Dividendenrendite":    "Dividendenrendite",
    "Ausschüttungsquote":   "Ausschüttungsquote",
    "KUV":                  "KUV",
    "KGV":                  "KGV",
    "Forward PE":           "Forward P/E",
    "KBV":                  "KBV",
    "Gewinn je Aktie":      "Gewinn je Aktie",
    "Marktkapitalisierung": "Marktkap.",
    "Gewinnwachstum":       "Gewinnwachstum",
    "Umsatzwachstum":       "Umsatzwachstum",
}

# ✨ NEU: Kurz­beschreibungen aller Kennzahlen (Popover-Text)
METRIC_DESCRIPTIONS = {
    "Währung": "Handelswährung der Aktie.",
    "Region": "Region/Land des Unternehmenssitzes.",
    "Sektor": "Übergeordneter Wirtschaftssektor.",
    "Branche": "Spezifische Branche innerhalb des Sektors.",
    "Vortagesschlusskurs": "Letzter Schlusskurs (gestern).",
    "Dividendenrendite": "Jährliche Dividende ÷ Aktienkurs, in %.",
    "Ausschüttungsquote": "Anteil des Gewinns, der als Dividende ausgeschüttet wird, in %.",
    "KGV": "Kurs-Gewinn-Verhältnis (Preis ÷ Gewinn je Aktie).",
    "Forward PE": "Prognostiziertes KGV für die nächsten 12 Monate.",
    "KBV": "Kurs-Buchwert-Verhältnis (Preis ÷ Buchwert je Aktie).",
    "KUV": "Kurs-Umsatz-Verhältnis (Marktkap. ÷ Jahresumsatz).",
    "PEG-Ratio": "KGV geteilt durch erwartetes Gewinnwachstum; <1 gilt als günstig.",
    "EV/EBITDA": "Unternehmenswert ÷ EBITDA.",
    "EBIT": "Ergebnis vor Zinsen und Steuern.",
    "Bruttomarge": "Bruttogewinn als % des Umsatzes.",
    "Operative Marge": "Operatives Ergebnis als % des Umsatzes.",
    "Nettomarge": "Jahresüberschuss als % des Umsatzes.",
    "Marktkapitalisierung": "Börsenwert aller ausstehenden Aktien.",
    "Free Cashflow": "Cashflow nach Investitionen (FCF).",
    "Free Cashflow Yield": "FCF ÷ Marktkapitalisierung, in %.",
    "Operativer Cashflow": "Cashflow aus laufender Geschäftstätigkeit.",
    "Eigenkapitalrendite": "Gewinn ÷ Eigenkapital (ROE), in %.",
    "Return on Assets": "Gewinn ÷ Bilanzsumme (ROA), in %.",
    "ROIC": "Return on Invested Capital, in %.",
    "Umsatzwachstum 10J": "Ø jährliche Umsatzsteigerung der letzten 10 Jahre.",
    "Umsatzwachstum 3J (erwartet)": "Erwartete Ø Umsatzsteigerung der nächsten 3 Jahre.",
    "Gewinn je Aktie": "Erwarteter Gewinn je Aktie (EPS) in den nächsten 12 Monaten.",
    "Gewinnwachstum 5J": "Ø jährliche Gewinnsteigerung der letzten 5 Jahre.",
    "Gewinnwachstum": "Jährliche Gewinnsteigerungsrate, in %.",
    "Umsatzwachstum": "Jährliche Umsatzsteigerungsrate, in %.",
    "Verschuldungsgrad": "Fremdkapital ÷ Eigenkapital, in %.",
    "Interest Coverage": "EBIT ÷ Zinsaufwand; höher ist besser.",
    "Current Ratio": "Umlaufvermögen ÷ kurzfristige Verbindlichkeiten.",
    "Quick Ratio": "Liquiditätsgrad II (Cash + Forderungen) ÷ kurzfristige Verbindlichkeiten.",
    "Beta": "Volatilität relativ zum Gesamtmarkt (β > 1 = schwankungsintensiver).",
    "52Wochen Hoch": "Höchster Kurs der letzten 52 Wochen.",
    "52Wochen Tief": "Tiefster Kurs der letzten 52 Wochen.",
    "52Wochen Change": "Kursveränderung in den letzten 52 Wochen, in %.",
    "Analysten_Kursziel": "Durchschnittliches Kursziel laut Analysten.",
    "Empfehlungsdurchschnitt": "Analysten-Rating (1 = Kaufen, 5 = Verkaufen).",
    "Insider_Anteil": "Anteil der Insider-Aktien, in %.",
    "Institutioneller_Anteil": "Anteil institutioneller Investoren, in %.",
    "Short Interest": "Prozentual leerverkaufter Streubesitz.",
}

EXCLUDE_COLS = {"Symbol", "Security", "Abfragedatum", "Datenquelle"}

app = Flask(__name__)

# ───────────────────────── CSV-Cache ─────────────────────────
_df: pd.DataFrame | None = None           # zwischengespeicherter DataFrame
_df_mtime: float | None = None            # gemerkter "modified time" der CSV

def load_df() -> pd.DataFrame:
    """
    Gibt immer die aktuelle CSV zurück.
    Lädt neu, falls die Datei seit dem letzten Zugriff verändert wurde.
    """
    global _df, _df_mtime

    cur_mtime = os.path.getmtime(CSV_FILE)  # Zeitstempel der Datei abfragen

    # Erstes Laden ODER Datei hat sich geändert → neu einlesen
    if _df is None or _df_mtime is None or cur_mtime != _df_mtime:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="utf-8-sig", on_bad_lines="skip")
        df.columns  = df.columns.str.replace("\ufeff", "").str.strip()
        df["Symbol"]   = df["Symbol"].astype(str).str.strip().str.upper()
        df["Security"] = df["Security"].astype(str).str.strip()

        _df, _df_mtime = df, cur_mtime       # Cache + Zeitstempel aktualisieren

    return _df


def all_metric_keys() -> List[str]:
    """Alle Spalten außer Meta-Spalten zurückgeben."""
    return [c for c in load_df().columns if c not in EXCLUDE_COLS]

# ───────────────────────── Helper ─────────────────────────
def get_row(tkr: str):
    df = load_df()
    r  = df[df["Symbol"] == tkr]
    return r.iloc[0] if not r.empty else None

def fmt(val, dec: int = 2):
    """
    Formatiert Zahlen sauber mit Tausendertrennzeichen und Punkt als Dezimaltrenner.
    Nicht-numerische oder NaN-Werte werden als Gedankenstrich ausgegeben.
    """
    if pd.isna(val):
        return "–"

    # Numerisch?
    try:
        num = float(str(val).replace(",", "."))
    except ValueError:
        return str(val)

    # Normale Formatierung
    return f"{num:,.{dec}f}".replace(",", ".")

def _font(path: str, size: int, backup):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return backup

# ───────────────────────── Bildgenerator ─────────────────────────
def create_stock_image(bg: str, ticker: str, keys: List[str]) -> str:
    """Generiert das PNG für eine Aktie und gibt den Dateipfad zurück."""
    row = get_row(ticker)
    if row is None:
        raise ValueError("Ticker not found")

    img  = Image.open(bg).convert("RGBA")
    draw = ImageDraw.Draw(img)

    f_def = ImageFont.load_default()
    f_ttl = _font(MONTS_BOLD, 58, f_def)
    f_lbl = _font(MONTS_BOLD, 32, f_def)
    f_sml = _font(MONTS_REG , 22, f_def)

    # ─── Titel (mehrzeilig, zentriert) ──────────────────────────
    max_w = img.width - 160
    raw   = f"Aktie: {row['Security'].upper()} ({ticker})"
    lines, cur = [], ""
    for w in raw.split():
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=f_ttl) > max_w and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    lines.append(cur)
    y = 25
    for l in lines:
        draw.text(((img.width - draw.textlength(l, font=f_ttl)) // 2, y), l, fill="black", font=f_ttl)
        y += f_ttl.size + 8

    # ─── Kennzahlen (max 8) ─────────────────────────────────────
    def val(k):
        if k == "Marktkapitalisierung":
            raw_val = row.get("Marktkapitalisierung", row.get("Marktkap.", None))
            return f"{fmt(raw_val / 1_000_000_000)} Mrd $" if pd.notna(raw_val) else "–"
        if k == "Ausschüttungsquote":
            v = row.get(k)
            if pd.notna(v):
                v = v * 100 if v < 1 else v
            return f"{fmt(v)} %"
        if k in {"Dividendenrendite", "Gewinnwachstum", "Umsatzwachstum"}:
            return f"{fmt(row.get(k))} %"
        return fmt(row.get(k))

    metrics = [(METRIC_LABELS.get(k, k), val(k)) for k in keys]
    col_x   = [100, img.width // 2 + 40]
    y_cur   = [y + 90, y + 90]
    line_h  = f_lbl.size + 60
    for i, (lab, v) in enumerate(metrics):
        col = i % 2
        draw.text((col_x[col], y_cur[col]), f"{lab}: {v}", fill="black", font=f_lbl)
        y_cur[col] += line_h

    # ─── Logo (optional) ────────────────────────────────────────
    logo_path = next(
        (p for p in (f"{ticker}.png", f"{ticker.lower()}.png", f"{ticker.upper()}.png")
         if os.path.exists(os.path.join(LOGO_DIR, p))), None)
    if logo_path:
        logo = Image.open(os.path.join(LOGO_DIR, logo_path)).convert("RGBA")
        max_w = img.width * 0.18
        scale = min(1, max_w / logo.width)
        logo  = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
        y_logo = max(y_cur) + 40
        img.alpha_composite(logo, ((img.width - logo.width) // 2, y_logo))
        y_footer = y_logo + logo.height + 40
    else:
        y_footer = max(y_cur) + 80

    # ─── Footer (Datum & Quelle) ────────────────────────────────
    raw_date = row.get("Abfragedatum")
    if pd.notna(raw_date):
        try:
            date_str = pd.to_datetime(raw_date).strftime("%d.%m.%Y")
        except Exception:
            date_str = str(raw_date)
    else:
        date_str = datetime.now().strftime("%d.%m.%Y")

    source_str = row.get("Datenquelle") or "Yahoo Finance"
    footer = f"Abfragedatum: {date_str}, Datenquelle: {source_str}"
    draw.text(
        ((img.width - draw.textlength(footer, font=f_sml)) // 2, y_footer),
        footer,
        fill="black",
        font=f_sml,
    )

    out = os.path.join(OUT_DIR, f"{ticker}_{int(datetime.now().timestamp())}.png")
    img.save(out)
    return out

# ───────────────────────── Routes ─────────────────────────
@app.route('/')
def home():
    return render_template(
        'index.html',
        available_metrics=[{"key": k, "label": METRIC_LABELS.get(k, k)} for k in all_metric_keys()],
        default_metrics=DEFAULT_METRICS,
        metric_descriptions=METRIC_DESCRIPTIONS   # ← neu
    )

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    df = load_df()
    m = df['Symbol'].str.contains(q, case=False, na=False) | df['Security'].str.contains(q, case=False, na=False)
    return jsonify([
        {"symbol": s, "name": n}
        for s, n in df.loc[m, ['Symbol', 'Security']].head(20).to_records(index=False)
    ])

@app.route('/generate_image', methods=['POST'])
def generate_image():
    ticker  = request.form.get('ticker', '').strip().upper()
    metrics = request.form.getlist('metrics')[:8] or DEFAULT_METRICS
    if not ticker:
        return 'Ticker fehlt', 400
    if get_row(ticker) is None:
        return f"Ticker '{ticker}' nicht gefunden", 400

    path = create_stock_image(BACKGROUND, ticker, metrics)
    return redirect(url_for('display_result', filename=os.path.basename(path)))

@app.route('/result/<filename>')
def display_result(filename):
    return render_template('display_result.html', filename=filename)

@app.route('/static/generated/<path:filename>')
def generated_file(filename):
    return send_from_directory(OUT_DIR, filename)

@app.route('/output/<path:filename>')
def output_file(filename):
    return send_from_directory(OUT_DIR, filename)

# ───────────────────────── Main ─────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
