from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_from_directory
)
import os, pandas as pd, io, time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any

# ───────────────────────── Konfiguration ─────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))

# Zielgröße für Social (1080x1350, Portrait)
OUTPUT_WIDTH  = 1080
OUTPUT_HEIGHT = 1350
OUTPUT_SIZE   = (OUTPUT_WIDTH, OUTPUT_HEIGHT)
# Layout-Sicherheitsränder & Abstände
SAFE_MARGIN_X       = 0.06   # links/rechts
SAFE_TOP_FRAC       = 0.09   # Abstand nach oben
SAFE_BOTTOM_FRAC    = 0.22   # Footer deutlich höher platzieren
LINE_SPACING_MULT   = 2.10   # größerer Zeilenabstand für Werte
METRICS_TOP_EXTRA_FRAC = 0.03  # zusätzlicher Abstand unter dem Titel
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSV_FILE   = os.path.join(BASE_DIR, "stock_data.csv")
BACKGROUND = os.path.join(STATIC_DIR, "default_background.png")
LOGO_DIR   = os.path.join(STATIC_DIR, "logos")
FONT_DIR   = os.path.join(STATIC_DIR, "fonts")
OUT_DIR    = os.path.join(STATIC_DIR, "generated")

os.makedirs(OUT_DIR, exist_ok=True)

# Fonts (Fallback auf PIL Default, falls nicht vorhanden)
FONT_REG_PATH = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
FONT_BLD_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

# Maximal 8 Kennzahlen gleichzeitig
MAX_METRICS = 8

# Spalten, die NIEMALS als Kennzahl angezeigt werden sollen
EXCLUDE_COLS = {
    "Symbol", "Security", "Abfragedatum", "Datenquelle",
    "valid_yahoo_ticker", "resolved_name", "resolved_exchange", "resolved_score",
    "GICS Sector", "GICS Sector Name"
}

# Einheitliche Prozentinterpretation
PERCENT_KEYS = {
    "Dividendenrendite", "Ausschüttungsquote",
    "Bruttomarge", "Operative Marge", "Nettomarge",
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    "Free Cashflow Yield",
    "Umsatzwachstum", "Gewinnwachstum",
    "Umsatzwachstum 3J (erwartet)",
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest",
    "52Wochen Change"
}

# Mapping Währung → Label
CURRENCY_SYMBOL = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF",
    "CAD": "C$", "AUD": "A$", "HKD": "HK$", "INR": "₹"
}

# Anzeigelabels + Kurzbeschreibungen (Tooltip)
METRIC_LABELS: Dict[str, str] = {
    "Dividendenrendite": "Div.-Rendite",
    "Ausschüttungsquote": "Ausschüttg.",
    "KGV": "KGV",
    "Forward PE": "Forward PE",
    "KBV": "KBV",
    "KUV": "KUV",
    "PEG-Ratio": "PEG-Ratio",
    "EV/EBITDA": "EV/EBITDA",
    "EBIT": "EBIT",
    "Bruttomarge": "Bruttomarge",
    "Operative Marge": "Oper. Marge",
    "Nettomarge": "Nettomarge",
    "Marktkapitalisierung": "Marktkap.",
    "Free Cashflow": "Free Cashflow",
    "Free Cashflow Yield": "FCF-Yield",
    "Operativer Cashflow": "Oper. Cashflow",
    "Eigenkapitalrendite": "ROE",
    "Return on Assets": "ROA",
    "ROIC": "ROIC",
    "Umsatzwachstum 3J (erwartet)": "Umsatzw. 3J (exp.)",
    "Gewinn je Aktie": "EPS",
    "Gewinnwachstum 5J": "Gewinnw. 5J",
    "Verschuldungsgrad": "Debt/Equity",
    "Interest Coverage": "Zinsdeck.",
    "Current Ratio": "Current Ratio",
    "Quick Ratio": "Quick Ratio",
    "Beta": "Beta",
    "52Wochen Hoch": "52W Hoch",
    "52Wochen Tief": "52W Tief",
    "52Wochen Change": "52W Change",
    "Analysten_Kursziel": "Kursziel (Ø)",
    "Empfehlungsdurchschnitt": "Empfehlung (Ø)",
    "Insider_Anteil": "Insider %",
    "Institutioneller_Anteil": "Institutionell %",
    "Short Interest": "Short Interest %",
}

METRIC_DESC: Dict[str, str] = {
    "Dividendenrendite": "Dividende / Kurs (in %).",
    "Ausschüttungsquote": "Dividende / Gewinn (in %).",
    "KGV": "Preis ÷ Gewinn je Aktie.",
    "Forward PE": "Prognostiziertes KGV nächste 12M.",
    "KBV": "Preis ÷ Buchwert je Aktie.",
    "KUV": "Marktkap. ÷ Jahresumsatz.",
    "PEG-Ratio": "KGV / erwartetes Gewinnwachstum.",
    "EV/EBITDA": "Unternehmenswert ÷ EBITDA.",
    "EBIT": "Ergebnis vor Zinsen und Steuern.",
    "Bruttomarge": "Bruttogewinn in % des Umsatzes.",
    "Operative Marge": "Operatives Ergebnis in % des Umsatzes.",
    "Nettomarge": "Jahresüberschuss in % des Umsatzes.",
    "Marktkapitalisierung": "Börsenwert aller Aktien.",
    "Free Cashflow": "Cashflow nach Investitionen.",
    "Free Cashflow Yield": "FCF ÷ Market Cap (in %).",
    "Operativer Cashflow": "Cashflow aus Geschäftstätigkeit.",
    "Eigenkapitalrendite": "ROE (in %).",
    "Return on Assets": "ROA (in %).",
    "ROIC": "Return on Invested Capital (in %).",
    "Umsatzwachstum 3J (erwartet)": "Schätzung (in %).",
    "Gewinn je Aktie": "EPS (Forward).",
    "Gewinnwachstum 5J": "Heuristisch, ggf. ungenau.",
    "Verschuldungsgrad": "Debt/Equity.",
    "Interest Coverage": "Zinsdeckungsgrad.",
    "Current Ratio": "Umlaufvermögen / kurzfristige Verbindl.",
    "Quick Ratio": "(UV−Vorräte)/kurzfr. Verbindl.",
    "Beta": "Marktrisiko (1≈Markt).",
    "52Wochen Hoch": "52‑W‑Hoch.",
    "52Wochen Tief": "52‑W‑Tief.",
    "52Wochen Change": "Kursänderung 52‑W (in %).",
    "Analysten_Kursziel": "Durchschnitt Kursziel.",
    "Empfehlungsdurchschnitt": "1=StrongBuy … 5=Sell.",
    "Insider_Anteil": "Insideranteil (in %).",
    "Institutioneller_Anteil": "Institutionsanteil (in %).",
    "Short Interest": "Short Float (in %).",
}

# Default-Kennzahlen (8 Stück)
DEFAULT_METRICS = [
    "Dividendenrendite", "Ausschüttungsquote",
    "KGV", "Forward PE", "KBV", "KUV",
    "Free Cashflow Yield", "Marktkapitalisierung",
]

# CSV Cache
_df = None
_df_mtime = None

app = Flask(__name__)

# ───────────────────────── Utils ─────────────────────────

def _font(path: str, size: int, backup):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return backup

def _fmt_locale(num: float, dec: int = 2) -> str:
    # Lokales Format: Tausendertrenner = normales Leerzeichen, Dezimaltrennzeichen = Komma
    # (vorher: schmale NBSP U+202F → führte bei manchen Fonts zu "Tofu"-Rechteck)
    s = f"{num:,.{dec}f}"  # z. B. 4,466.83
    s = s.replace(",", " ").replace(".", ",")  # 4 466,83
    return s

def fmt_number(val: Any, dec: int = 2) -> str:
    if pd.isna(val):
        return "–"
    try:
        num = float(str(val).replace(",", "."))
    except ValueError:
        return str(val)
    return _fmt_locale(num, dec)

def fmt_percent_for(key: str, val: Any, dec: int = 2) -> str:
    if pd.isna(val):
        return "–"

    s_raw = str(val).strip().replace("%", "")
    try:
        x = float(s_raw.replace(",", "."))
    except ValueError:
        return str(val)

    def _count_decimals(s: str) -> int:
        # zählt Ziffern nach Dezimaltrennzeichen
        if "," in s:
            part = s.split(",", 1)[1]
        elif "." in s:
            part = s.split(".", 1)[1]
        else:
            return 0
        # entferne evtl. Exponent
        part = part.split("e")[0].split("E")[0]
        return sum(1 for ch in part if ch.isdigit())

    # Feldspezifische Normalisierung
    if key in {"Dividendenrendite", "Free Cashflow Yield"}:
        decs = _count_decimals(s_raw)
        ax = abs(x)
        # Heuristik:
        # - Wenn x < 1.5 und Dezimalstellen >= 3 → wahrscheinlich Bruch → *100
        # - Wenn x < 1.5 und Dezimalstellen <= 2 → wahrscheinlich bereits % (z. B. 0.45) → kein *100
        # - Wenn 1.5 <= x < 100 → % beibehalten
        if ax < 1.5:
            if decs >= 3:
                x *= 100.0
        # sonst: x wie vorhanden (bereits Prozent)
    else:
        # Standardfelder: Brüche in % umwandeln
        if abs(x) <= 1.5:
            x *= 100.0

    return _fmt_locale(x, dec) + "%"

def currency_label(row: pd.Series) -> str:
    cur = str(row.get("Währung") or "").upper()
    sym = CURRENCY_SYMBOL.get(cur, cur or "$")
    return f"Mrd {sym}"

def elide(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    # Kürzt Text mit …, wenn zu breit
    if draw.textlength(text, font=font) <= max_w:
        return text
    ell = "…"
    while text and draw.textlength(text + ell, font=font) > max_w:
        text = text[:-1]
    return text + ell

# einfacher Auto-Zeilenumbruch für die Titelzeile
def wrap_title(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        test = (" ".join(cur + [w])).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

# generischer Zeilenumbruch (wrap) – bricht auch zu lange Wörter mit Trennstrich
def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int, *, hyphenate: bool = True) -> List[str]:
    if text is None:
        return ["–"]
    s = str(text)
    if not s:
        return ["–"]
    words = s.split()
    lines: List[str] = []
    cur = ""
    for word in words:
        test = (cur + (" " if cur else "") + word)
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
                cur = ""
            # Wort passt nicht in den verfügbaren Bereich
            w = word
            if not hyphenate:
                # ohne Trennstrich: Wort bleibt ganz, wir kürzen später ggf. bei der Ausgabe
                cur = w
                continue
            # mit Trennstrich umbrechen
            while draw.textlength(w, font=font) > max_w and len(w) > 1:
                lo, hi, pos = 1, len(w), 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    trial = w[:mid] + "-"
                    if draw.textlength(trial, font=font) <= max_w:
                        pos = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1
                lines.append(w[:pos] + "-")
                w = w[pos:]
            cur = w
    if cur:
        lines.append(cur)
    return lines

# Aufräumen alter generierter Bilder
def cleanup_generated(max_age_hours: int = 48):
    now = time.time()
    for fn in os.listdir(OUT_DIR):
        p = os.path.join(OUT_DIR, fn)
        try:
            if os.path.isfile(p) and now - os.path.getmtime(p) > max_age_hours * 3600:
                os.remove(p)
        except Exception:
            pass

# Hintergrund skalieren (Cover = ausfüllen, ggf. mittig beschneiden)
def resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    if w == target_w and h == target_h:
        return img
    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # mittig zuschneiden
    left   = (new_w - target_w) // 2
    top    = (new_h - target_h) // 2
    right  = left + target_w
    bottom = top + target_h
    return img.crop((left, top, right, bottom))

# CSV laden (mit Mtime-Cache)
def load_df() -> pd.DataFrame:
    global _df, _df_mtime
    cur_mtime = os.path.getmtime(CSV_FILE) if os.path.exists(CSV_FILE) else None
    if _df is None or _df_mtime != cur_mtime:
        df = pd.read_csv(CSV_FILE, delimiter=",", encoding="utf-8-sig", on_bad_lines="skip")
        _df = df
        _df_mtime = cur_mtime
    return _df

# Hilfsfunktion: verfügbare Kennzahlen für die UI ermitteln
def all_metric_keys(df: pd.DataFrame) -> List[str]:
    cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    # nur numerische/vernünftige Felder anzeigen (Strings filtern)
    return [c for c in cols if c not in ("Währung", "Region", "Sektor", "Branche")]

# ───────────────────────── Routes ─────────────────────────
@app.route('/')
def home():
    df = load_df()
    # Liste verfügbarer Kennzahlen
    keys = all_metric_keys(df)
    # Metriken mit Label+Desc aufbereiten
    available = [{
        "key": k,
        "label": METRIC_LABELS.get(k, k),
        "desc": METRIC_DESC.get(k, "")
    } for k in keys]

    return render_template(
        'index.html',
        default_metrics=DEFAULT_METRICS,
        available_metrics=available,
        metric_descriptions=METRIC_DESC
    )

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = load_df()
    if not q:
        return jsonify([])

    # Suche in Symbol & Security
    candidates = []
    for _, row in df.iterrows():
        sym = str(row.get('Symbol') or '')
        sec = str(row.get('Security') or '')
        if q in sym.lower() or q in sec.lower():
            candidates.append({
                'symbol': sym,
                'name': sec
            })
        if len(candidates) >= 12:
            break
    return jsonify(candidates)

@app.route('/generate_image', methods=['POST'])
def generate_image():
    cleanup_generated()  # alte Bilder regelmäßig löschen

    ticker = (request.form.get('ticker') or '').strip().upper()
    if not ticker:
        return redirect(url_for('home'))

    selected = request.form.getlist('metrics') or []
    if len(selected) > MAX_METRICS:
        selected = selected[:MAX_METRICS]

    df = load_df()
    row = df[df['Symbol'] == ticker]
    if row.empty:
        # Fallback: Suche per valid_yahoo_ticker
        if 'valid_yahoo_ticker' in df.columns:
            row = df[df['valid_yahoo_ticker'] == ticker]
    if row.empty:
        # letzte Chance: case-insensitive Symbol
        row = df[df['Symbol'].astype(str).str.upper() == ticker]
    if row.empty:
        return redirect(url_for('home'))

    row = row.iloc[0]

    # Hintergrund
    bg_path = BACKGROUND
    if 'background' in request.files and request.files['background'] and request.files['background'].filename:
        try:
            bg_file = request.files['background']
            bg_bytes = bg_file.read()
            bg_img = Image.open(io.BytesIO(bg_bytes)).convert('RGBA')
        except Exception:
            bg_img = Image.open(bg_path).convert('RGBA')
        # auf Zielgröße bringen (1080x1350)
        bg_img = resize_cover(bg_img, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    else:
        bg_img = Image.open(bg_path).convert('RGBA')
        # auf Zielgröße bringen (1080x1350)
        bg_img = resize_cover(bg_img, OUTPUT_WIDTH, OUTPUT_HEIGHT)

    # Arbeitsbild exakt in Zielgröße
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)

    # Fonts (dynamisch skaliert nach Bildbreite)
    base_w = img.width
    TITLE_SZ  = max(42, int(base_w * 0.060))
    LABEL_SZ  = max(28, int(base_w * 0.037))
    REG_SZ    = max(24, int(base_w * 0.033))
    FOOT_SZ   = max(20, int(base_w * 0.026))

    f_reg  = _font(FONT_REG_PATH, REG_SZ,  ImageFont.load_default())
    f_bld  = _font(FONT_BLD_PATH, TITLE_SZ, ImageFont.load_default())
    f_lbl  = _font(FONT_REG_PATH, LABEL_SZ, ImageFont.load_default())
    f_foot = _font(FONT_REG_PATH, FOOT_SZ,  ImageFont.load_default())

    # Titelzeile (Name + Ticker) mit Auto-Wrap
    name = str(row.get('Security') or '')
    symb = str(row.get('Symbol') or '')
    title = f"{name} ({symb})".strip()
    max_w = int(img.width * 0.88)
    lines = wrap_title(draw, title, f_bld, max_w)

    x = int(img.width * SAFE_MARGIN_X)
    y = int(img.height * SAFE_TOP_FRAC)
    line_gap = 8
    for ln in lines:
        tw = draw.textlength(ln, font=f_bld)
        tx = (img.width - int(tw)) // 2  # zentriert
        draw.text((tx, y), ln, fill="black", font=f_bld)
        y += int(f_bld.size * 1.18) + line_gap

    # Logo vorbereiten (erst NACH den Werten platzieren)
    logo_img = None
    logo_size = None
    logo_path_png = os.path.join(LOGO_DIR, f"{symb}.png")
    if os.path.exists(logo_path_png):
        try:
            lg = Image.open(logo_path_png).convert('RGBA')
            # Größer als zuvor (~Faktor 2) und dynamisch, aber begrenzt
            target_h = min(int(f_bld.size * 6.0), int(img.height * 0.45))
            ratio = target_h / lg.height
            new_w  = int(lg.width * ratio)
            # Max. 80% der Bildbreite
            max_w  = int(img.width * 0.80)
            if new_w > max_w:
                ratio = max_w / lg.width
                new_w = max_w
                target_h = int(lg.height * ratio)
            logo_img = lg.resize((new_w, target_h))
            logo_size = (new_w, target_h)
        except Exception:
            logo_img = None
            logo_size = None

    # Kennzahlen in zwei Spalten zeichnen
    # Falls nichts gewählt → Defaults
    metrics = selected or DEFAULT_METRICS

    # Hilfs-Funktion zur Aufbereitung einzelner Werte (inkl. Prozent/Währung)
    def val(key: str) -> str:
        if key == "Marktkapitalisierung":
            raw = row.get("Marktkapitalisierung")
            if pd.notna(raw):
                try:
                    v = float(raw) / 1_000_000_000
                except Exception:
                    return "–"
                return f"{fmt_number(v, 0)} {currency_label(row)}"
            return "–"
        if key in PERCENT_KEYS:
            return fmt_percent_for(key, row.get(key))
        return fmt_number(row.get(key))

    # Layout-Berechnung: 2 Spalten, Label/Value in Spalte getrennt
    avail_w = img.width - 2 * x
    col_gap = int(img.width * 0.05)
    col_w   = (avail_w - col_gap) // 2
    col_x   = [x, x + col_w + col_gap]

    # Dynamische Labelbreite: so breit wie das längste Label, aber gedeckelt
    labels = [METRIC_LABELS.get(m, m) + ":" for m in metrics]
    max_label_px = 0
    for lab in labels:
        max_label_px = max(max_label_px, int(draw.textlength(lab, font=f_lbl)))
    label_w = min(int(col_w * 0.72), max_label_px + 18)
    value_w = col_w - label_w

    # Start-Y (Logo wird später unter die Werte gesetzt)
    safe_top = y + int(img.height * METRICS_TOP_EXTRA_FRAC) + 16

    # Vertikale Fläche für Metriken ermitteln und Schriftgröße ggf. anpassen
    bottom_margin = int(img.height * SAFE_BOTTOM_FRAC)
    footer_room   = f_foot.size + int(f_foot.size * 0.6)
    available_vertical = img.height - bottom_margin - footer_room - safe_top

    max_rows = (len(metrics) + 1) // 2

    # --- Einzeiliges Layout erzwingen: dynamische Schrift-Skalierung, kein Wrap
    MIN_FONT = 22

    def compute_label_value_widths(font_lbl: ImageFont.FreeTypeFont, font_val: ImageFont.FreeTypeFont):
        # Labelbreite anhand längsten Labels bestimmen (mit Puffer)
        labels_local = [METRIC_LABELS.get(m, m) + ":" for m in metrics]
        max_label_px_local = 0
        for lab in labels_local:
            max_label_px_local = max(max_label_px_local, int(draw.textlength(lab, font=font_lbl)))
        _label_w = min(int(col_w * 0.72), max_label_px_local + 18)
        _value_w = col_w - _label_w
        # Längster Wert (px)
        max_val_px = 0
        for m in metrics:
            txt = val(m)
            max_val_px = max(max_val_px, int(draw.textlength(str(txt), font=font_val)))
        return _label_w, _value_w, max_val_px

    f_lbl_cur = f_lbl
    f_val_cur = f_lbl

    while True:
        label_w, value_w, max_val_px = compute_label_value_widths(f_lbl_cur, f_val_cur)
        line_h = int(f_lbl_cur.size * LINE_SPACING_MULT)
        total_h = max_rows * line_h
        fits_height = (total_h <= available_vertical)
        fits_width  = (max_val_px <= value_w)
        if fits_height and fits_width:
            break
        # Priorität: erst Wertefont verkleinern, dann Labelfont, danach beide (Höhe)
        changed = False
        if not fits_width and f_val_cur.size > MIN_FONT:
            f_val_cur = _font(FONT_REG_PATH, f_val_cur.size - 1, ImageFont.load_default())
            changed = True
        elif not fits_width and f_lbl_cur.size > MIN_FONT:
            f_lbl_cur = _font(FONT_REG_PATH, f_lbl_cur.size - 1, ImageFont.load_default())
            changed = True
        elif not fits_height:
            if f_lbl_cur.size > MIN_FONT:
                f_lbl_cur = _font(FONT_REG_PATH, f_lbl_cur.size - 1, ImageFont.load_default())
                changed = True
            if f_val_cur.size > MIN_FONT:
                f_val_cur = _font(FONT_REG_PATH, f_val_cur.size - 1, ImageFont.load_default())
                changed = True
        if not changed:
            break

    # Final: mit den gefundenen Fonts neu berechnen
    f_lbl = f_lbl_cur
    f_val = f_val_cur
    label_w, value_w, _ = compute_label_value_widths(f_lbl, f_val)
    line_h = int(f_lbl.size * LINE_SPACING_MULT)

    # Vertikal möglichst weit oben halten, aber nicht kleben
    total_h = max_rows * line_h
    extra   = max(0, available_vertical - total_h)
    safe_top += int(extra * 0.08)

    # Zeichnen: exakt 1 Zeile pro Metrik
    y_row = safe_top
    for r in range(max_rows):
        # links
        if 2*r < len(metrics):
            m_left = metrics[2*r]
            lab_left = METRIC_LABELS.get(m_left, m_left) + ":"
            val_left = str(val(m_left))
        else:
            lab_left, val_left = "", ""
        # rechts
        if 2*r + 1 < len(metrics):
            m_right = metrics[2*r + 1]
            lab_right = METRIC_LABELS.get(m_right, m_right) + ":"
            val_right = str(val(m_right))
        else:
            lab_right, val_right = "", ""

        # links zeichnen
        cxL = col_x[0]
        draw.text((cxL, y_row), lab_left, fill="black", font=f_lbl)
        vwL = draw.textlength(val_left, font=f_val)
        vxL = cxL + label_w + (value_w - vwL)
        draw.text((vxL, y_row), val_left, fill="black", font=f_val)

        # rechts zeichnen
        cxR = col_x[1]
        draw.text((cxR, y_row), lab_right, fill="black", font=f_lbl)
        vwR = draw.textlength(val_right, font=f_val)
        vxR = cxR + label_w + (value_w - vwR)
        draw.text((vxR, y_row), val_right, fill="black", font=f_val)

        y_row += line_h

    # Unterkante des Werteblocks
    metrics_bottom_y = y_row

    # Footer höher platzieren (helle Fläche) und Logo UNTER den Werten
    abf = str(row.get('Abfragedatum') or '')
    src = str(row.get('Datenquelle') or '') or 'Yahoo Finance'
    try:
        dt = datetime.strptime(abf, "%Y-%m-%d").strftime("%d.%m.%Y") if abf else "—"
    except Exception:
        dt = abf or "—"
    foot = f"Stand: {dt}  •  Quelle: {src}"
    fw = draw.textlength(foot, font=f_foot)
    fx = (img.width - int(fw)) // 2
    fy = img.height - int(img.height * SAFE_BOTTOM_FRAC)

    # Logo jetzt unter den Werten, aber oberhalb des Footers einsetzen
    if logo_img is not None:
        metrics_bottom = metrics_bottom_y
        pad = int(img.height * 0.08)
        ly = metrics_bottom + pad
        lx = (img.width - logo_img.width) // 2
        # Wenn wenig Platz bis zum Footer, Logo ggf. kleiner skalieren oder nach oben schieben
        max_h = fy - pad - ly
        if max_h > 10:
            if logo_img.height > max_h:
                ratio = max_h / logo_img.height
                new_w = max(1, int(logo_img.width * ratio))
                new_h = max(1, int(logo_img.height * ratio))
                logo_img = logo_img.resize((new_w, new_h), Image.LANCZOS)
                lx = (img.width - new_w) // 2
            img.alpha_composite(logo_img, (lx, ly))
        else:
            # Notfalls direkt oberhalb des Footers einklinken
            ly = max(int(fy - pad - logo_img.height), metrics_bottom)
            lx = (img.width - logo_img.width) // 2
            img.alpha_composite(logo_img, (lx, ly))

    # Footer zeichnen
    draw.text((fx, fy), foot, fill="black", font=f_foot)

    # Datei speichern
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symb}_{ts}.png"
    path = os.path.join(OUT_DIR, filename)
    img.convert('RGB').save(path, format='PNG')

    return redirect(url_for('display_result', filename=filename))

@app.route('/result/<path:filename>')
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
    # Für lokalen Testbetrieb
    app.run(debug=True, host='0.0.0.0', port=5000)
