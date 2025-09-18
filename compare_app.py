from flask import (
    Flask, request, jsonify, send_from_directory, render_template_string
)
import os, time, math, re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ───────────────────────── Basis / Pfade ─────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUT_DIR    = os.path.join(STATIC_DIR, "generated")
LOGO_DIR   = os.path.join(STATIC_DIR, "logos")
FONT_DIR   = os.path.join(STATIC_DIR, "fonts")
BACKGROUND = os.path.join(STATIC_DIR, "default_background.png")
CSV_FILE   = os.environ.get("STOCK_CSV", os.path.join(BASE_DIR, "stock_data.csv"))

os.makedirs(OUT_DIR, exist_ok=True)

# ───────────────────────── Render- und Layout-Parameter ─────────────────────────
OUTPUT_WIDTH  = 1080
OUTPUT_HEIGHT = 1350
SAFE_MARGIN_X = 0.06          # Seiten-Sicherheitsrand
SAFE_TOP_FRAC = 0.08          # Titel-Safe-Zone
SAFE_BOTTOM_FRAC = 0.18       # etwas mehr Raum für Footer/Branding

# ───────────────────────── Fonts ─────────────────────────
FONT_REG_PATH = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
FONT_BLD_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

def _font(path: str, size: int, backup):
    try:
        f = ImageFont.truetype(path, size)
        f.path = path  # type: ignore[attr-defined]
        f.size = size
        return f
    except OSError:
        try:
            f = ImageFont.truetype('DejaVuSans.ttf', size)
            f.size = size
            return f
        except Exception:
            f = backup
            try:
                f.size = size
            except Exception:
                pass
            return f

# ───────────────────────── Farben/Palette ─────────────────────────
COLOR_TEXT      = (20, 24, 28)
COLOR_BETTER    = (17, 146, 74)
COLOR_WORSE     = (196, 59, 43)
COLOR_MUTED     = (95, 103, 112)

PALETTE = {
    "card_bg": (255, 255, 255, 240),
    "chip_bg": (245, 247, 250, 255),
    "shadow" : (0, 0, 0, 70),
    "zebra"  : (247, 249, 252, 170),
    "bar_hold": (240, 198, 89, 255),
    "bar_bg"  : (236, 242, 248, 255),
}

# ───────────────────────── Daten & Format ─────────────────────────
CURRENCY_SYMBOL = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF",
    "CAD": "C$", "AUD": "A$", "HKD": "HK$", "INR": "₹"
}

PERCENT_KEYS = {
    "Dividendenrendite", "Ausschüttungsquote",
    "Bruttomarge", "Operative Marge", "Nettomarge",
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    "Free Cashflow Yield",
    "Umsatzwachstum", "Gewinnwachstum",
    "Umsatzwachstum 3J (erwartet)", "Umsatzwachstum 10J", "Umsatzwachstum 5J",
    "52Wochen Change", "Insider_Anteil", "Institutioneller_Anteil", "Short Interest"
}

# Bewertung: Was ist "besser"?
BETTER_HIGH = {
    "Dividendenrendite","Bruttomarge","Operative Marge","Nettomarge",
    "Eigenkapitalrendite","Return on Assets","ROIC","Free Cashflow Yield",
    "Umsatzwachstum","Umsatzwachstum 3J (erwartet)","Umsatzwachstum 5J","Umsatzwachstum 10J",
    "52Wochen Change"
}
BETTER_LOW  = {"KGV","Forward PE","KUV","Ausschüttungsquote"}

def _metric_value_for_compare(row: pd.Series, key: str) -> Optional[float]:
    v = numeric_value(key, row)
    return v

def compare_metrics(row_left: pd.Series, row_right: pd.Series, metrics: list[str]) -> dict[str,int]:
    out = {}
    for key in metrics[:6]:
        a = _metric_value_for_compare(row_left, key)
        b = _metric_value_for_compare(row_right, key)
        if a is None or b is None:
            out[key] = 0
            continue
        # niedrig besser?
        if key in BETTER_LOW:
            out[key] = 1 if a < b else (-1 if a > b else 0)
        else:
            # Standard/Prozent: höher ist besser
            out[key] = 1 if a > b else (-1 if a < b else 0)
    return out

SECTOR_METRICS: Dict[str, List[str]] = {
    "communication":            ["KGV","KUV","Nettomarge","Operative Marge","Bruttomarge","Umsatzwachstum 10J"],
    "information technology":   ["KGV","Forward PE","KUV","Eigenkapitalrendite","Free Cashflow Yield","Umsatzwachstum 3J (erwartet)"],
    "consumer discretionary":   ["KGV","Forward PE","KUV","Operative Marge","Eigenkapitalrendite","Umsatzwachstum 3J (erwartet)"],
    "consumer staples":         ["Dividendenrendite","Ausschüttungsquote","KGV","Nettomarge","Eigenkapitalrendite","Umsatzwachstum 3J (erwartet)"],
    "health care":              ["KGV","KUV","Nettomarge","Bruttomarge","Eigenkapitalrendite","Umsatzwachstum 10J"],
    "financials":               ["KGV","KUV","Eigenkapitalrendite","Nettomarge","Dividendenrendite","Umsatzwachstum 10J"],
    "industrials":              ["KGV","KUV","Operative Marge","Eigenkapitalrendite","Free Cashflow Yield","Umsatzwachstum 10J"],
    "materials":                ["KGV","KUV","Operative Marge","Nettomarge","Eigenkapitalrendite","Umsatzwachstum 10J"],
    "energy":                   ["KGV","KUV","Nettomarge","Free Cashflow Yield","Dividendenrendite","Umsatzwachstum 10J"],
    "utilities":                ["Dividendenrendite","Ausschüttungsquote","KGV","Nettomarge","Free Cashflow Yield","Umsatzwachstum 10J"],
    "real estate":              ["Dividendenrendite","Ausschüttungsquote","KGV","KUV","Nettomarge","Umsatzwachstum 10J"],
}

LABELS = {
    "Dividendenrendite": "Div.-Rendite",
    "Ausschüttungsquote": "Ausschüttg.",
    "Marktkapitalisierung": "Marktkap.",
    "Operative Marge": "Oper. Marge",
    "Operativer Cashflow": "Oper. CF",
    "Umsatzwachstum 3J (erwartet)": "Umsatzw. 3J",
    "Umsatzwachstum 10J": "Umsatzw. 10J",
}

COLUMN_ALIASES: Dict[str, List[str]] = {
    "Nettomarge": ["Nettomarge","Net Margin","Net Profit Margin","Profit Margin","profitMargins","netProfitMargin","netMargin"],
    "Operative Marge": ["Operative Marge","Operating Margin","operatingMargins"],
    "Bruttomarge": ["Bruttomarge","Gross Margin","grossMargins"],
    "Marktkapitalisierung": ["Marktkapitalisierung","Market Cap","marketCap","MarketCap"],
    "Dividendenrendite": ["Dividendenrendite","Dividend Yield","dividendYield"],
    "Eigenkapitalrendite": ["Eigenkapitalrendite","Return on Equity","ROE","returnOnEquity"],
    "KGV": ["KGV","PE","trailingPE"],
    "Forward PE": ["Forward PE","forwardPE"],
    "KUV": ["KUV","Price to Sales","priceToSalesTrailing12Months"],
    "Free Cashflow Yield": ["Free Cashflow Yield","freeCashflowYield","fcfYield"],
    "Analysten_Kursziel": ["Analysten_Kursziel","Target Mean Price","targetMeanPrice"],
    "Preis": ["Preis","Close","Last","Vortagesschlusskurs"],
    "Umsatzwachstum 10J": ["Umsatzwachstum 10J","Revenue Growth 10Y","revenueGrowth10Y"],
    "Umsatzwachstum 3J (erwartet)": ["Umsatzwachstum 3J (erwartet)","Revenue Growth 3Y (fwd)","revenueGrowth3YForward"],
}

# ───────────────────────── CSV laden ─────────────────────────
_df: Optional[pd.DataFrame] = None
_df_mtime: Optional[float] = None

def load_df() -> pd.DataFrame:
    global _df, _df_mtime
    cur_mtime = os.path.getmtime(CSV_FILE) if os.path.exists(CSV_FILE) else None
    if _df is None or _df_mtime != cur_mtime:
        last_err = None
        for _ in range(3):
            try:
                df = pd.read_csv(CSV_FILE, encoding="utf-8-sig", on_bad_lines="skip")
                _df = df
                _df_mtime = cur_mtime
                return _df
            except Exception as e:
                last_err = e
                time.sleep(0.25)
        raise last_err
    return _df

# ───────────────────────── Formatierung ─────────────────────────

def _fmt_locale(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if "," in s and dec > 0:
        s = s.rstrip("0").rstrip(",")
    return s

def fmt_number(val: Any, dec: int = 2) -> str:
    if pd.isna(val):
        return "–"
    try:
        num = float(str(val).replace(",", "."))
    except ValueError:
        return str(val)
    return _fmt_locale(num, dec)

def fmt_percent_for(key: str, val: Any, dec: int = 1):  # 1 Nachkommastelle reicht optisch
    if pd.isna(val):
        return "–"
    s_raw = str(val).strip().replace("%", "")
    try:
        x = float(s_raw.replace(",", "."))
    except ValueError:
        return str(val)
    if abs(x) <= 1.5:
        x *= 100.0
    return _fmt_locale(x, dec) + "%"

def currency_label(row: pd.Series) -> str:
    cur = str(row.get("Währung") or "").upper()
    sym = CURRENCY_SYMBOL.get(cur, cur or "$")
    return f"Mrd {sym}"

def fcur(x: float, sym: str, dec: int = 0) -> str:  # Werte in Pills ohne Nachkommastellen
    return f"{sym}{_fmt_locale(x,dec)}" if sym in {"$","€","£","¥"} else f"{_fmt_locale(x,dec)}{sym}"

# ───────────────────────── Column-Resolve & Value-Checks ─────────────────────────

def resolve_col(row_or_df, key: str) -> Optional[str]:
    cols = row_or_df.index if isinstance(row_or_df, pd.Series) else row_or_df.columns
    if key in cols:
        return key
    for alt in COLUMN_ALIASES.get(key, []):
        if alt in cols:
            return alt
    return None

def _to_float(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    try:
        return float(str(x).replace("%", "").replace(",", ".").replace(" ", ""))
    except Exception:
        return None

def _get_val(row: pd.Series, key: str) -> Any:
    col = resolve_col(row, key)
    if col:
        return row.get(col)
    return None

def has_value(row: pd.Series, key: str) -> bool:
    col = resolve_col(row, key)
    if not col:
        return False
    v = row.get(col)
    if pd.isna(v):
        return False
    s = str(v).strip()
    if not s or s == "–":
        return False
    if key in {"KGV","Forward PE","KUV","Marktkapitalisierung","Operativer Cashflow","Free Cashflow"} or key in PERCENT_KEYS:
        return _to_float(v) is not None
    return True

def numeric_value(key: str, row: pd.Series) -> Optional[float]:
    val = _get_val(row, key)
    return _to_float(val)

def display_value(key: str, row: pd.Series) -> str:
    val = _get_val(row, key)
    if key in PERCENT_KEYS:
        return fmt_percent_for(key, val)
    if key == "Marktkapitalisierung":
        v = _to_float(val)
        if v is None:
            return "–"
        num = v / 1e9
        return _fmt_locale(num, 1) + f" {currency_label(row)}"
    if key in {"KGV","Forward PE","KUV"}:
        v = _to_float(val)
        if v is None:
            return "–"
        dec = 0 if abs(v) >= 100 else 2
        return fmt_number(v, dec)
    if key in {"Operativer Cashflow","Free Cashflow"}:
        v = _to_float(val)
        if v is None:
            return "–"
        num = v / 1e9
        return _fmt_locale(num, 1) + f" {currency_label(row)}"
    return fmt_number(val, 2)

# ───────────────────────── Layout-Helpers ─────────────────────────

def resize_cover(im: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = im.size
    scale = max(target_w / w, target_h / h)
    nw, nh = int(w * scale), int(h * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = (nw - target_w) // 2
    y = (nh - target_h) // 2
    return im.crop((x, y, x + target_w, y + target_h))

def _rounded_rect(img: Image.Image, xy, radius: int, fill, outline=None, outline_width=1):
    x1, y1, x2, y2 = xy
    w, h = x2 - x1, y2 - y1
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w-1, h-1), radius=radius, fill=255)
    layer = Image.new("RGBA", (w, h), fill)
    img.paste(layer, (x1, y1), mask)
    if outline:
        omask = Image.new("L", (w, h), 0)
        od = ImageDraw.Draw(omask)
        od.rounded_rectangle((0, 0, w-1, h-1), radius=radius, outline=255, width=outline_width)
        ol = Image.new("RGBA", (w, h), outline)
        img.paste(ol, (x1, y1), omask)

def _drop_shadow(img: Image.Image, xy, radius=20, offset=(0, 10), blur=18, color=PALETTE["shadow"]):
    x1, y1, x2, y2 = xy
    w, h = x2 - x1, y2 - y1
    pad = blur
    shadow = Image.new("RGBA", (w + pad*2, h + pad*2), (0,0,0,0))
    shape = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(shape)
    sd.rounded_rectangle((0, 0, w-1, h-1), radius=radius, fill=255)
    block = Image.new("RGBA", (w, h), color)
    shadow.paste(block, (pad, pad), shape)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    img.paste(shadow, (x1 - pad + offset[0], y1 - pad + offset[1]), shadow)

def _load_logo(sym: str) -> Optional[Image.Image]:
    p = os.path.join(LOGO_DIR, f"{sym}.png")
    if os.path.exists(p):
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            return None
    return None

def _fit_logo(img_in: Optional[Image.Image], target_h: int, max_w: int) -> Optional[Image.Image]:
    if img_in is None: return None
    w, h = img_in.size
    if h == 0: return None
    scale = target_h / h
    nw, nh = int(w*scale), int(h*scale)
    if nw > max_w:
        scale = max_w / w
        nw, nh = int(w*scale), int(h*scale)
    return img_in.resize((nw, nh), Image.LANCZOS)

def shrink_to_fit(draw, text, font, max_width, min_px=18, font_path=None):
    size = getattr(font, "size", 26)
    path = font_path or getattr(font, "path", FONT_REG_PATH)
    while size > min_px and draw.textlength(text, font=font) > max_width:
        size -= 1
        font = _font(path, size, ImageFont.load_default())
    return font, text

def ellipsize_to_fit(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    s = text
    while s and draw.textlength(s + "…", font=font) > max_width:
        s = s[:-1]
    return s + "…"

def split_two_lines(draw, text, font, max_w):
    if draw.textlength(text, font=font) <= max_w:
        return (text, None)
    best = None
    for i in range(len(text)-1, 0, -1):
        if text[i].isspace() and draw.textlength(text[:i], font=font) <= max_w:
            best = i
            break
    if best:
        return (text[:best].rstrip(), text[best:].strip())
    s = text
    while s and draw.textlength(s + "…", font=font) > max_w:
        s = s[:-1]
    return (s + "…", None)

def trim_numeric_text_to_fit(draw, text, font, max_width):
    """
    Kürzt Dezimalstellen (z. B. '28,33' -> '28,3' -> '28'),
    bevor Ellipsen gesetzt werden. Prozent/Einheiten bleiben erhalten.
    """
    if draw.textlength(text, font=font) <= max_width:
        return text
    s = text
    while draw.textlength(s, font=font) > max_width:
        m = list(re.finditer(r"(\d+),(\d+)(?=[^0-9%]|$|%)", s))
        if not m:
            break
        i = m[-1].start(2)
        grp = m[-1].group(2)
        if len(grp) > 1:
            s = s[:i] + grp[:-1] + s[i+len(grp):]
        else:
            s = s[:m[-1].start(1)+len(m[-1].group(1))] + s[m[-1].end(2):]
    if draw.textlength(s, font=font) <= max_width:
        return s
    return ellipsize_to_fit(draw, s, font, max_width)

# ───────────────────────── Kürzere Label-Fallbacks & Card-Parameter ─────────────────────────
CHIP_MAX_FRAC   = 0.40   # maximale Chipbreite (Anteil am Inhaltsbereich)
LABEL_MIN_FRAC  = 0.50   # mindestens so viel Platz für Label

ALT_LABELS2 = {
    "Eigenkapitalrendite": ["EK-Rendite", "ROE"],
    "Free Cashflow Yield": ["FCF-Yield", "FCF%"],
    "Operative Marge": ["Oper. Marge", "Op.-Marge"],
    "Nettomarge": ["Nettomarge", "Net-Marge"],
    "Bruttomarge": ["Bruttomarge", "Gross-Marge"],
    "Umsatzwachstum 3J (erwartet)": ["Umsatzw. 3J", "Rev. 3J"],
    "Marktkapitalisierung": ["Marktkap.", "Mkt Cap"],
}

def shrink_label_to_fit_for_key(draw, key, base_label_with_colon, font, max_w):
    if draw.textlength(base_label_with_colon, font=font) <= max_w:
        return font, base_label_with_colon
    size = font.size
    min_px = max(14, int(size * 0.82))
    path = getattr(font, "path", FONT_REG_PATH)
    f = font
    while size > min_px and draw.textlength(base_label_with_colon, font=f) > max_w:
        size -= 1
        f = ImageFont.truetype(path, size)
    if draw.textlength(base_label_with_colon, font=f) <= max_w:
        return f, base_label_with_colon
    for alt in ALT_LABELS2.get(key, []):
        cand = alt + (":" if base_label_with_colon.endswith(":") else "")
        if draw.textlength(cand, font=f) <= max_w:
            return f, cand
    return f, ellipsize_to_fit(draw, base_label_with_colon, f, max_w)

# ───────────────────────── Zeichnen: Cards, Pills, Bar ─────────────────────────

def draw_company_card(img, draw, rect, row, symbol, metrics, chip_widths, f_lbl, f_val, ticker_font):
    """Card-Header: **zentriertes Logo** + **Ticker-Badge**, KEIN Firmenname mehr (der steht jetzt oben im Titel).
    Danach 6 Kennzahlenzeilen.
    """
    x1, y1, x2, y2 = rect
    _drop_shadow(img, rect, radius=20, blur=18, color=(0,0,0,70))
    _rounded_rect(img, rect, radius=18, fill=PALETTE["card_bg"])

    pad = int(img.width * 0.035)
    gy = y1 + pad

    # Logo mittig (horizontal) in der Karte
    logo = _load_logo(symbol)
    if logo:
        logo = _fit_logo(logo, target_h=int(ticker_font.size * 2.0), max_w=(x2 - x1) - 2*pad)
        if logo:
            lx = x1 + ((x2 - x1) - logo.width)//2
            img.alpha_composite(logo, (lx, gy))
            gy += logo.height + int(ticker_font.size * 0.25)

    # Ticker-Badge mittig
    ticker_txt = symbol
    badge_w = int(draw.textlength(ticker_txt, font=ticker_font)) + 20
    badge_h = ticker_font.size + 10
    bx = x1 + ((x2 - x1) - badge_w)//2
    by = gy
    _rounded_rect(img, (bx, by, bx + badge_w, by + badge_h), radius=999, fill=(235,240,246,255))
    draw.text((bx + 10, by + 5), ticker_txt, fill=COLOR_MUTED, font=ticker_font)
    gy += badge_h + int(ticker_font.size * 0.4)

    # Tabellenbereich
    content_w   = (x2 - x1) - 2*pad
    max_chip_w  = int(content_w * CHIP_MAX_FRAC)
    min_label_w = int(content_w * LABEL_MIN_FRAC)
    line_h      = int(max(f_lbl.size, f_val.size) * 1.5)

    for i, key in enumerate(metrics[:6]):
        y = gy + i * line_h
        if i % 2 == 1:
            _rounded_rect(img, (x1 + pad - 8, y - int(line_h*0.15), x2 - pad + 8, y + int(line_h*0.95)),
                          radius=10, fill=PALETTE["zebra"])

        val_txt = display_value(key, row)
        has_val = (val_txt is not None) and (val_txt.strip() != "–")
        chip_w  = 0
        chip_h  = f_val.size + 12
        if has_val:
            base_w = int(draw.textlength(val_txt, font=f_val)) + 24
            suggested = max(base_w, chip_widths.get(key, base_w))
            chip_w = min(suggested, max_chip_w)
            if content_w - chip_w - 16 < min_label_w:
                chip_w = max( int(content_w * 0.30), content_w - 16 - min_label_w )
            val_txt = trim_numeric_text_to_fit(draw, val_txt, f_val, chip_w - 20)

        raw_label = LABELS.get(key, key)
        label_txt = raw_label + ":"
        max_label_w = content_w - (chip_w if has_val else int(f_val.size*2.5)) - 16
        f_lbl_fit, label_fit = shrink_label_to_fit_for_key(draw, key, label_txt, f_lbl, max_label_w)
        draw.text((x1 + pad, y), label_fit, fill=COLOR_TEXT, font=f_lbl_fit)

        if has_val:
            nx = numeric_value(key, row)
            is_pct = key in PERCENT_KEYS
            color = (COLOR_BETTER if (is_pct and nx is not None and nx >= 0)
                     else COLOR_WORSE if (is_pct and nx is not None and nx < 0)
                     else COLOR_TEXT)
            vx = x2 - pad - chip_w
            vy = y - int((chip_h - f_val.size)/2)
            _rounded_rect(img, (vx, vy, vx + chip_w, vy + chip_h), radius=10, fill=PALETTE["chip_bg"])
            tw = int(draw.textlength(val_txt, font=f_val))
            draw.text((vx + (chip_w - tw)//2, y), val_txt, fill=color, font=f_val)
        else:
            vw = int(draw.textlength("–", font=f_val))
            vx = x2 - pad - vw
            draw.text((vx, y), "–", fill=COLOR_MUTED, font=f_val)


def _price_target_data(row: pd.Series) -> Optional[Tuple[float,float,str]]:
    p = _to_float(row.get("Vortagesschlusskurs"))
    t = _to_float(row.get("Analysten_Kursziel"))
    cur = str(row.get("Währung") or "").upper()
    if p is None or t is None or p <= 0:
        return None
    return p, t, cur

def _currency_sym(cur: str) -> str:
    return CURRENCY_SYMBOL.get(cur, cur or "$")


def draw_winner_badge_below_cards(img: Image.Image, draw: ImageDraw.ImageDraw, card_a, card_b, text: str, color):
    """Plaziert eine runde Badge mittig UNTER den Cards."""
    cx = (card_a[2] + card_b[0]) // 2
    try:
        f = ImageFont.truetype(FONT_BLD_PATH, max(20, int(img.width*0.030)))
    except Exception:
        f = ImageFont.load_default()
    try:
        f.size = getattr(f, 'size', max(20, int(img.width*0.030)))
    except Exception:
        pass
    tw = int(draw.textlength(text, font=f))
    bw = tw + 32
    bh = f.size + 14
    x1 = cx - bw//2
    cards_bottom = max(card_a[3], card_b[3])
    y1 = cards_bottom + int(img.height * 0.010)
    x2 = x1 + bw
    y2 = y1 + bh
    _rounded_rect(img, (x1, y1, x2, y2), radius=bh//2, fill=(255,255,255,235))
    try:
        bd = Image.new("RGBA", (bw, bh), (0,0,0,0))
        gd = ImageDraw.Draw(bd)
        gd.rounded_rectangle((0,0,bw-1,bh-1), radius=bh//2, outline=color, width=2)
        img.paste(bd, (x1, y1), bd)
    except Exception:
        pass
    draw.text((x1 + (bw - tw)//2, y1 + (bh - f.size)//2 - 1), text, fill=color, font=f)


def draw_stat_pills(img, draw, center_x, y, row, f_lbl, f_val, card_w=None):
    info = _price_target_data(row)
    if not info:
        return y
    price, target, cur = info
    sym = _currency_sym(cur)
    pot = (target/price - 1.0) * 100.0
    arrow = "▲" if pot >= 0 else "▼"

    items = [
        ("Kurs", fcur(price, sym, 0)),
        ("Ziel", fcur(target, sym, 0)),
        ("Pot.", f"{arrow} {_fmt_locale(pot,1)}%"),
    ]

    avail = int((card_w or img.width//2) * 0.92)
    gap = int(img.width * 0.012)
    n = 3
    w = (avail - gap*(n-1)) // n
    start_x = center_x - (w*n + gap*(n-1))//2

    pill_h = f_val.size*2 + 10
    for i, (lab, val) in enumerate(items):
        x1 = start_x + i*(w+gap); x2 = x1 + w
        _rounded_rect(img, (x1, y, x2, y + pill_h), radius=14, fill=PALETTE["chip_bg"])
        lw = int(draw.textlength(lab, font=f_lbl))
        draw.text((x1 + (w - lw)//2, y + 4), lab, fill=COLOR_MUTED, font=f_lbl)
        vfit = trim_numeric_text_to_fit(draw, val, f_val, w - 20)
        vw = int(draw.textlength(vfit, font=f_val))
        draw.text((x1 + (w - vw)//2, y + 4 + f_lbl.size + 4), vfit, fill=COLOR_TEXT, font=f_val)
    return y + pill_h


def draw_analyst_bar(img, draw, center_x, y, width, row, f_lbl, f_val):
    mean = _to_float(row.get("Empfehlungsdurchschnitt"))
    if mean is None or not (0.5 <= mean <= 5.5):
        return y

    buy_frac = max(0.0, min(1.0, (5.0 - float(mean)) / 4.0))
    buy_pct  = int(round(buy_frac * 100))
    hold_pct = 100 - buy_pct

    x1 = center_x - width // 2
    x2 = center_x + width // 2
    bar_h = max(14, int(f_val.size * 0.50))

    # Hintergrund + Kaufanteil
    _rounded_rect(img, (x1, y, x2, y + bar_h), radius=bar_h // 2, fill=PALETTE["bar_hold"])
    gx2 = x1 + int(width * buy_frac)
    if gx2 > x1:
        _rounded_rect(img, (x1, y, gx2, y + bar_h), radius=bar_h // 2, fill=COLOR_BETTER)

    # Prozentwerte **nur innerhalb** der Bar – keine doppelten Labels darüber
    bp = f"{buy_pct}%"; hp = f"{hold_pct}%"
    draw.text((x1 + 8, y + (bar_h - f_val.size)//2), bp, fill=(255,255,255), font=f_val)
    tw_h = int(draw.textlength(hp, font=f_val))
    draw.text((x2 - tw_h - 8, y + (bar_h - f_val.size)//2), hp, fill=(30,30,30), font=f_val)

    # Zweizeilige Unterzeile: Zeile 1 = Ø-Rating, Zeile 2 = Erklärung
    sub1 = f"Ø-Rating {fmt_number(mean,2)} (1–5)"
    sub1 = ellipsize_to_fit(draw, sub1, f_lbl, width)
    w1 = int(draw.textlength(sub1, font=f_lbl))
    y_sub1 = y + bar_h + 4
    draw.text((center_x - w1//2, y_sub1), sub1, fill=COLOR_MUTED, font=f_lbl)

    # Kürzere Erklärung + kleinere Schrift, falls nötig automatisch schrumpfen
    sub2 = "1=K • 3=H • 5=V"
    f_small = _font(FONT_REG_PATH, max(12, int(f_lbl.size * 0.90)), ImageFont.load_default())
    # notfalls weiter schrumpfen bis es passt
    while int(draw.textlength(sub2, font=f_small)) > width and f_small.size > 10:
        f_small = _font(FONT_REG_PATH, f_small.size - 1, ImageFont.load_default())
    w2 = int(draw.textlength(sub2, font=f_small))
    y_sub2 = y_sub1 + f_lbl.size + 0
    draw.text((center_x - w2//2, y_sub2), sub2, fill=COLOR_MUTED, font=f_small)

    return y_sub2 + f_small.size + 2

# ───────────────────────── Auswahl-Logik für Kennzahlen ─────────────────────────

def select_metrics(rows: List[pd.Series], req_metrics: List[str], sec_key: Optional[str]) -> List[str]:
    if req_metrics:
        base = [m for m in req_metrics if isinstance(m, str) and m.strip()]
    else:
        base = SECTOR_METRICS.get(sec_key, ["KGV","Forward PE","KUV","Nettomarge","Eigenkapitalrendite","Umsatzwachstum 3J (erwartet)"])
    fallback = ["KGV","Forward PE","KUV","Nettomarge","Operative Marge","Bruttomarge",
                "Eigenkapitalrendite","Free Cashflow Yield","Marktkapitalisierung",
                "Umsatzwachstum 3J (erwartet)","Umsatzwachstum 10J","Dividendenrendite"]

    order: List[str] = []
    for key in base + [k for k in fallback if k not in base]:
        if key not in order and (resolve_col(rows[0], key) or resolve_col(rows[1], key)):
            order.append(key)

    both, either = [], []
    for key in order:
        a = has_value(rows[0], key)
        b = has_value(rows[1], key)
        if a and b:
            both.append(key)
        elif a or b:
            either.append(key)

    sel = (both + either)[:6]
    if len(sel) < 3:
        sel = [k for k in order if k not in sel][:6]
    return sel

# ───────────────────────── Datum aus CSV im deutschen Format ─────────────────────────

def fmt_de_date_from_row(row: pd.Series) -> Optional[str]:
    val = row.get("Abfragedatum")
    if pd.isna(val):
        return None
    try:
        dt = pd.to_datetime(val)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return None

# ───────────────────────── Render ─────────────────────────

def render_compare(rows: List[pd.Series], metrics: List[str]) -> Image.Image:
    if os.path.exists(BACKGROUND):
        bg = Image.open(BACKGROUND).convert('RGBA')
    else:
        bg = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (19, 33, 54, 255))
        g = ImageDraw.Draw(bg)
        g.ellipse((-200, -150, OUTPUT_WIDTH+200, OUTPUT_HEIGHT+300), fill=(14, 22, 36, 255))
    bg = resize_cover(bg, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    img = bg.copy()
    draw = ImageDraw.Draw(img)

    base_w = img.width
    TITLE_SZ = max(42, int(base_w * 0.058))           # Titel etwas kleiner (weil jetzt Firmennamen)
    LABEL_SZ = max(26, int(base_w * 0.034))
    VAL_SZ   = max(28, int(base_w * 0.036))
    TICKER_SZ= max(22, int(base_w * 0.028))
    FOOT_SZ  = max(20, int(base_w * 0.026))

    f_title = _font(FONT_BLD_PATH, TITLE_SZ, ImageFont.load_default())
    f_lbl   = _font(FONT_REG_PATH, LABEL_SZ, ImageFont.load_default())
    f_val   = _font(FONT_REG_PATH, VAL_SZ,   ImageFont.load_default())
    f_tick  = _font(FONT_BLD_PATH, TICKER_SZ,ImageFont.load_default())
    f_foot  = _font(FONT_REG_PATH, FOOT_SZ,  ImageFont.load_default())

    # kleine Fonts für den unteren Bereich
    f_lbl_small = _font(FONT_REG_PATH, max(18, int(LABEL_SZ * 0.84)), ImageFont.load_default())
    f_val_small = _font(FONT_REG_PATH, max(18, int(VAL_SZ   * 0.84)), ImageFont.load_default())

    sym_a = str(rows[0].get('Symbol') or '')
    sym_b = str(rows[1].get('Symbol') or '')

    # Titel: Firmennamen statt Ticker
    name_a = str(rows[0].get('resolved_name') or rows[0].get('Security') or sym_a)
    name_b = str(rows[1].get('resolved_name') or rows[1].get('Security') or sym_b)
    title = f"{name_a}   vs   {name_b}"
    f_title, _ = shrink_to_fit(draw, title, f_title, int(img.width*0.92), min_px=int(TITLE_SZ*0.60), font_path=FONT_BLD_PATH)
    tw = draw.textlength(title, font=f_title)
    draw.text(((img.width - tw)//2, int(img.height * SAFE_TOP_FRAC)), title, fill=COLOR_TEXT, font=f_title)

    # Sektor-Key & smarte Auswahl
    sec_raw = str(rows[0].get("GICS Sector") or rows[0].get("Sektor") or "").strip().lower()
    sec_key = next((k for k in SECTOR_METRICS if k in sec_raw), None)
    metrics = select_metrics(rows, metrics, sec_key)

    # Karten-Bereich
    top = int(img.height * (SAFE_TOP_FRAC + 0.075))
    margin_x = int(img.width * SAFE_MARGIN_X)
    gap = int(img.width * 0.04)
    card_w = (img.width - margin_x*2 - gap) // 2
    card_h = int(img.height * 0.42)

    card_a = (margin_x, top, margin_x + card_w, top + card_h)
    card_b = (margin_x + card_w + gap, top, margin_x + card_w*2 + gap, top + card_h)

    # Notbremse: Bei knapper Cardhöhe auf 5 Zeilen reduzieren
    max_lines = 6
    if card_h < int(img.height * 0.41):
        max_lines = 5
    metrics = metrics[:max_lines]

    # Gleichbreite Chips je Kennzahl (max über beide Cards; finale Clamp pro Card)
    chip_widths: Dict[str,int] = {}
    for key in metrics[:6]:
        t1 = display_value(key, rows[0]); t2 = display_value(key, rows[1])
        tw1 = int(draw.textlength(t1, font=f_val)) if t1 and t1.strip() != "–" else 0
        tw2 = int(draw.textlength(t2, font=f_val)) if t2 and t2.strip() != "–" else 0
        mx = max(tw1, tw2)
        if mx > 0:
            chip_widths[key] = mx + 24

    
    # Vergleich + Punkte für Sieger-Badge
    _cmp = compare_metrics(rows[0], rows[1], metrics)
    left_pts = right_pts = 0.0
    for k, sign in _cmp.items():
        if sign > 0: left_pts += 1.0
        elif sign < 0: right_pts += 1.0
        else: left_pts += 0.5; right_pts += 0.5
# Cards
    draw_company_card(img, draw, card_a, rows[0], sym_a, metrics, chip_widths, f_lbl, f_val, f_tick)
    draw_company_card(img, draw, card_b, rows[1], sym_b, metrics, chip_widths, f_lbl, f_val, f_tick)

    # Sieger-Badge mittig zwischen den Cards
    if abs(left_pts - right_pts) < 1e-6:
        badge_text = f"Unentschieden {int(left_pts)} : {int(right_pts)}"
        bcol = COLOR_MUTED
    elif left_pts > right_pts:
        badge_text = f"{name_a} gewinnt {int(left_pts)} : {int(right_pts)}"
        bcol = COLOR_BETTER
    else:
        badge_text = f"{name_b} gewinnt {int(right_pts)} : {int(left_pts)}"
        bcol = COLOR_BETTER
    draw_winner_badge_below_cards(img, draw, card_a, card_b, badge_text, bcol)

    # Vorab-Layout für unteren Bereich (Bottom-Clamp)
    est_pill_h = f_val_small.size*2 + 10
    est_bar_h  = max(14, int(f_val_small.size * 0.50)) + 4 + f_lbl_small.size + 2
    y_pills = max(card_a[3], card_b[3]) + int(img.height * 0.012)

    # verfügbare Unterkante (oberhalb der Fußzone)
    safe_bottom = img.height - int(img.height * SAFE_BOTTOM_FRAC) - 12

    # Platzbedarf berechnen
    need_bottom = y_pills + est_pill_h + int(img.height * 0.014) + est_bar_h
    extra = safe_bottom - need_bottom

    if extra < 0:
        # Zu wenig Platz → nach oben schieben
        y_pills += extra  # extra ist negativ
        y_pills = max(max(card_a[3], card_b[3]) + 2, y_pills)
    else:
        # Luft vorhanden → Mindestpolster zum Footer (~1 %) behalten
        y_pills += max(0, extra - int(img.height * 0.01))

    # pauschal etwas anheben (1.5% Höhe), um Abschneiden ganz zu vermeiden
    y_pills -= int(img.height * 0.015)

    # Pills
    center_a = (card_a[0] + card_a[2]) // 2
    center_b = (card_b[0] + card_b[2]) // 2
    y_after_a = draw_stat_pills(img, draw, center_a, y_pills, rows[0], f_lbl_small, f_val_small, card_w=card_w)
    y_after_b = draw_stat_pills(img, draw, center_b, y_pills, rows[1], f_lbl_small, f_val_small, card_w=card_w)

    # Analysten-Bar
    bar_w = int(card_w * 0.84)
    y_bar = max(y_after_a, y_after_b) + int(img.height * 0.012)
    y_bar_a = draw_analyst_bar(img, draw, center_a, y_bar, bar_w, rows[0], f_lbl_small, f_val_small)
    y_bar_b = draw_analyst_bar(img, draw, center_b, y_bar, bar_w, rows[1], f_lbl_small, f_val_small)

    # Footer – mit CSV-Abfragedatum je Aktie
    date_a = fmt_de_date_from_row(rows[0])
    date_b = fmt_de_date_from_row(rows[1])
    if not date_a and not date_b:
        foot = f"Stand: {datetime.today().strftime('%d.%m.%Y')}  •  Quelle: Yahoo Finance"
    else:
        part_a = f"{sym_a} {date_a or '-'}"
        part_b = f"{sym_b} {date_b or '-'}"
        foot = f"Stand: {part_a}  •  {part_b}  •  Quelle: Yahoo Finance"
    fw = draw.textlength(foot, font=f_foot)
    fx = (img.width - int(fw)) // 2
    fy = max(max(y_bar_a, y_bar_b) + int(img.height * 0.020), img.height - int(img.height * SAFE_BOTTOM_FRAC * 0.96))
    draw.text((fx, fy), foot, fill=(30, 34, 38), font=f_foot)

    return img

# ───────────────────────── Flask ─────────────────────────
# ── Optional WordPress-SSO/Newsletter Bridge ───────────────────────────────
try:
    from flask_wp_sso_bridge_v2 import gate_wp_modes, is_premium  # type: ignore
except Exception:
    # Fallback: keine Gate-Checks, alles durchlassen
    def gate_wp_modes():
        return {}
    def is_premium(user):
        return False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me')

@app.route("/")
def compare_home():
    guard = gate_wp_modes()
    if guard is not None and not isinstance(guard, dict):
        return guard
    return render_template_string(COMPOSE_HTML)

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = load_df()
    if not q:
        return jsonify([])
    # nur eindeutige Symbole zurückgeben
    mask = df['Symbol'].astype(str).str.lower().str.contains(q) | df['Security'].astype(str).str.lower().str.contains(q)
    sub = df.loc[mask, ['Symbol','Security']].drop_duplicates('Symbol').head(20)
    out = [{'symbol': r.Symbol, 'name': r.Security} for _, r in sub.iterrows()]
    return jsonify(out)

@app.route('/api/peers')
def peers():
    ticker = (request.args.get('ticker') or '').upper().strip()
    df = load_df()
    row = df[df['Symbol'] == ticker].head(1)
    if row.empty:
        return jsonify([])
    sector = str(row.iloc[0].get('GICS Sector') or '')
    peers_df = df[(df['GICS Sector'] == sector) & (df['Symbol'] != ticker)][['Symbol','Security']].drop_duplicates('Symbol')
    out = [{'symbol': r['Symbol'], 'name': r['Security']} for _, r in peers_df.head(40).iterrows()]
    return jsonify(out)

@app.route('/api/default_metrics')
def api_default_metrics():
    ticker = (request.args.get('ticker') or '').upper().strip()
    df = load_df()
    row = df[df['Symbol'] == ticker].head(1)
    if row.empty:
        return jsonify([])
    r = row.iloc[0]
    sec_raw = str(r.get("GICS Sector") or r.get("Sektor") or "").strip().lower()
    sec_key = next((k for k in SECTOR_METRICS if k in sec_raw), None)
    defaults = SECTOR_METRICS.get(sec_key, ["KGV","Forward PE","KUV","Nettomarge","Eigenkapitalrendite","Umsatzwachstum 3J (erwartet)"])[:6]
    available = [m for m in defaults if resolve_col(r, m)]
    return jsonify(available)

@app.route('/generate')
def generate_compare():
    guard = gate_wp_modes()
    if guard is not None and not isinstance(guard, dict):
        return guard
    ticker_a = (request.args.get('ticker_a') or '').upper().strip()
    ticker_b = (request.args.get('ticker_b') or '').upper().strip()
    metrics = request.args.getlist('metrics') or []

    if not ticker_a or not ticker_b:
        return "ticker_a und ticker_b sind Pflichtparameter", 400

    df = load_df()
    rows_a = df[df['Symbol'] == ticker_a]
    rows_b = df[df['Symbol'] == ticker_b]
    if rows_a.empty or rows_b.empty:
        return "Ticker nicht in CSV gefunden", 404

    row_a = rows_a.iloc[0]
    row_b = rows_b.iloc[0]

    img = render_compare([row_a, row_b], metrics)
    fname = f"COMPARE_{ticker_a}_{ticker_b}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    out_path = os.path.join(OUT_DIR, fname)
    img.save(out_path, format="PNG")

    rel = f"/static/generated/{fname}"
    return render_template_string(
        """<!doctype html><html><head><meta charset=\"utf-8\"><title>Vergleich</title>
        <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial;margin:24px}
        .wrap{max-width:1120px;margin:auto;text-align:center}
        img{max-width:100%;height:auto;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.25)}
        a.btn{display:inline-block;margin-top:14px;padding:10px 16px;border-radius:10px;background:#111;color:#fff;text-decoration:none}
        </style></head><body><div class=\"wrap\">
        <h1>Bild erzeugt</h1>
        <p><a class=\"btn\" href=\"{{ rel }}\" download>PNG herunterladen</a></p>
        <img src=\"{{ rel }}\" alt=\"Compare\">
        </div></body></html>""",
        rel=rel
    )

@app.route('/static/generated/<path:filename>')
def serve_generated(filename):
    return send_from_directory(OUT_DIR, filename)

# ───────────────────────── Minimaler Composer ─────────────────────────
COMPOSE_HTML = r"""
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>Aktien-Vergleich</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root{ --bg:#0f1b2b; --panel:#0c1624; --f:#e9eef6; --muted:#9fb0c7; --acc:#10b981; }
*{box-sizing:border-box}
body{margin:0;font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Inter,Arial;background:radial-gradient(1000px 600px at 50% -100px,#13243d 0%,#0b1625 60%,#091221 100%);color:var(--f)}
.container{max-width:980px;margin:32px auto;padding:0 16px}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:16px}
h1{font-size:28px;margin:0 0 16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label{display:block;font-weight:600;margin:8px 0 6px}
input,select{width:100%;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:#0e1a2a;color:#eaf2ff}
button{padding:12px 16px;border:none;border-radius:10px;background:#10b981;color:#02100a;font-weight:700;cursor:pointer}
.small{font-size:12px;color:var(--muted)}
.metrics{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.metric{display:flex;gap:6px;align-items:center;background:#0c1729;border:1px solid rgba(255,255,255,.1);padding:6px 10px;border-radius:999px}
.badge{background:#0c1729;border:1px solid rgba(255,255,255,.1);padding:6px 10px;border-radius:999px}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
hr{border:none;border-top:1px solid rgba(255,255,255,.1);margin:16px 0}
</style>
</head>
<body>
  <div class="container">
    <h1>Aktien-Vergleich (2-Card Layout)</h1>
    <form action="/generate" method="get" class="card" id="frm">
      <div class="grid">
        <div>
          <label>Aktie A</label>
          <input id="a" name="ticker_a" placeholder="z. B. META" list="a_list" autocomplete="off" />
          <datalist id="a_list"></datalist>
        </div>
        <div>
          <label>Aktie B (gleicher Sektor)</label>
          <select id="b" name="ticker_b"></select>
        </div>
      </div>
      <hr/>
      <label>Bis zu 6 Kennzahlen</label>
      <div id="metrics" class="metrics"></div>
      <div class="row">
        <input id="addMetric" list="allMetrics" placeholder="Kennzahl suchen & hinzufügen" />
        <datalist id="allMetrics"></datalist>
        <button type="button" id="addBtn">Hinzufügen</button>
        <span class="badge"><span id="count">0</span>/6 ausgewählt</span>
      </div>
      <p class="small">Ohne Auswahl werden sinnvolle Sektor-Defaults genommen.</p>
      <div class="row"><button id="submit" disabled>Vergleich erzeugen</button></div>
    </form>
  </div>
<script>
const a = document.getElementById('a');
const aList = document.getElementById('a_list');
const b = document.getElementById('b');
const metricsBox = document.getElementById('metrics');
const submitBtn = document.getElementById('submit');
const addMetric = document.getElementById('addMetric');
const addBtn = document.getElementById('addBtn');
const count = document.getElementById('count');

const available = [
  "KGV","Forward PE","KUV","Nettomarge","Operative Marge","Bruttomarge",
  "Eigenkapitalrendite","Free Cashflow Yield","Umsatzwachstum 3J (erwartet)",
  "Dividendenrendite","Ausschüttungsquote","Marktkapitalisierung",
  "Umsatzwachstum 10J","52Wochen Change"
].map(k => ({key:k,label:k}));

document.getElementById('allMetrics').innerHTML =
  available.map(x=>`<option value="${x.key}">${x.label}</option>`).join('');

function updateCount(){
  const checked = [...metricsBox.querySelectorAll('input[type=checkbox]:checked')];
  count.textContent = checked.length;
  submitBtn.disabled = !a.value || !b.value;
}
metricsBox.addEventListener('change', updateCount);

function addMetricChip(key,label){
  if([...metricsBox.querySelectorAll('input')].some(i => i.value===key)) return;
  if(metricsBox.querySelectorAll('input').length>=6) return;
  const el = document.createElement('label');
  el.className='metric';
  el.innerHTML = `<input type="checkbox" name="metrics" value="${key}" checked /> ${label}`;
  metricsBox.appendChild(el);
}

function setDefaultMetrics(keys){
  if(metricsBox.querySelectorAll('input').length>0) return;
  metricsBox.innerHTML = '';
  keys.forEach(k=>{
    const label = (available.find(m=>m.key===k)?.label) || k;
    addMetricChip(k,label);
  });
  updateCount();
}

addBtn.addEventListener('click', ()=>{
  const key = addMetric.value.trim();
  if(!key) return;
  const label = (available.find(m=>m.key===key)?.label) || key;
  addMetricChip(key,label);
  addMetric.value='';
  updateCount();
});

a.addEventListener('input', async (e)=>{
  const q = a.value.trim();
  if(!q){ aList.innerHTML=''; return; }
  const r = await fetch('/search?q='+encodeURIComponent(q));
  const data = await r.json();
  aList.innerHTML = data.map(d=>`<option value="${d.symbol}">${d.name}</option>`).join('');
});

a.addEventListener('change', async ()=>{
  const sym = a.value.trim();
  if(!sym){ return; }

  const r = await fetch('/api/peers?ticker='+encodeURIComponent(sym));
  const peers = await r.json();
  b.innerHTML = peers.map(p=>`<option value="${p.symbol}">${p.symbol} — ${p.name}</option>`).join('');
  submitBtn.disabled = !a.value || !b.value;

  metricsBox.innerHTML = '';
  try{
    const r2 = await fetch('/api/default_metrics?ticker='+encodeURIComponent(sym));
    const keys = await r2.json();
    setDefaultMetrics(keys);
  }catch(e){}
});

b.addEventListener('change', updateCount);
</script>
</body>
</html>
"""

# ───────────────────────── Run ─────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
