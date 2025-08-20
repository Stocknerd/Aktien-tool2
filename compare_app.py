from flask import (
    Flask, request, jsonify, send_from_directory, render_template_string
)
import os, time, math
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
SAFE_MARGIN_X = 0.06
SAFE_TOP_FRAC = 0.08
SAFE_BOTTOM_FRAC = 0.22

# ───────────────────────── Fonts ─────────────────────────
FONT_REG_PATH = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
FONT_BLD_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

def _font(path: str, size: int, backup):
    try:
        f = ImageFont.truetype(path, size)
        f.path = path  # type: ignore[attr-defined]
        return f
    except OSError:
        return backup

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

# ───────────────────────── Utils: CSV laden ─────────────────────────
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

# ───────────────────────── Utils: Formatierung ─────────────────────────
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

def fmt_percent_for(key: str, val: Any, dec: int = 2) -> str:
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

def fcur(x: float, sym: str) -> str:
    return f"{sym}{_fmt_locale(x,2)}" if sym in {"$","€","£","¥"} else f"{_fmt_locale(x,2)}{sym}"

# ───────────────────────── Utils: Column-Resolve ─────────────────────────
def resolve_col(row_or_df, key: str) -> Optional[str]:
    cols = row_or_df.index if isinstance(row_or_df, pd.Series) else row_or_df.columns
    if key in cols:
        return key
    for alt in COLUMN_ALIASES.get(key, []):
        if alt in cols:
            return alt
    return None

# ───────────────────────── Utils: Zahlenzugriff ─────────────────────────
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
        return fmt_number(val, 2)
    if key in {"Operativer Cashflow","Free Cashflow"}:
        v = _to_float(val)
        if v is None:
            return "–"
        num = v / 1e9
        return _fmt_locale(num, 1) + f" {currency_label(row)}"
    return fmt_number(val, 2)

# ───────────────────────── Bild-/Layout-Helfer ─────────────────────────
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

# ───────────────────────── Cards / Zusatz-Widgets ─────────────────────────
def draw_company_card(
    img: Image.Image, draw: ImageDraw.ImageDraw, rect: Tuple[int,int,int,int],
    row: pd.Series, symbol: str, name: str, metrics: List[str],
    chip_widths: Dict[str,int],
    f_title, f_lbl, f_val
):
    x1, y1, x2, y2 = rect
    _drop_shadow(img, rect, radius=20, blur=18, color=(0,0,0,70))
    _rounded_rect(img, rect, radius=18, fill=PALETTE["card_bg"])

    pad = int(img.width * 0.035)
    gy = y1 + pad

    # Header: Logo + zweizeiliger Name
    logo = _load_logo(symbol)
    logo = _fit_logo(logo, target_h=int(f_title.size*1.2), max_w=int((x2-x1)*0.55)) if logo else None

    pref_name = str(row.get("resolved_name") or row.get("Security") or symbol)
    name_max_w = (x2 - x1) - pad*2 - (logo.width + 12 if logo else 0)
    f_title_fit, _ = shrink_to_fit(draw, pref_name, f_title, name_max_w, min_px=max(20, f_title.size-14), font_path=FONT_BLD_PATH)
    name_draw = ellipsize_to_fit(draw, pref_name, f_title_fit, name_max_w)

    if logo:
        img.alpha_composite(logo, (x1 + pad, gy))
        lx = x1 + pad + logo.width + 12
        name1, name2 = split_two_lines(draw, name_draw, f_title_fit, (x2 - lx - pad))
        draw.text((lx, gy), name1, fill=COLOR_TEXT, font=f_title_fit)
        gy += f_title_fit.size + int(f_title_fit.size*0.10)
        if name2:
            draw.text((lx, gy), name2, fill=COLOR_TEXT, font=f_title_fit)
            gy += f_title_fit.size + int(f_title_fit.size*0.20)
        gy = max(gy, y1 + pad + logo.height) + int(f_title_fit.size*0.15)
    else:
        name1, name2 = split_two_lines(draw, name_draw, f_title_fit, (x2 - (x1 + pad) - pad))
        draw.text((x1 + pad, gy), name1, fill=COLOR_TEXT, font=f_title_fit)
        gy += f_title_fit.size + int(f_title_fit.size*0.10)
        if name2:
            draw.text((x1 + pad, gy), name2, fill=COLOR_TEXT, font=f_title_fit)
            gy += f_title_fit.size + int(f_title_fit.size*0.20)

    # Tabellenbereich
    line_h = int(max(f_lbl.size, f_val.size) * 1.5)
    for i, key in enumerate(metrics[:6]):
        y = gy + i*line_h
        if i % 2 == 1:
            _rounded_rect(img, (x1 + pad - 8, y - int(line_h*0.15), x2 - pad + 8, y + int(line_h*0.95)), radius=10, fill=PALETTE["zebra"])

        label = LABELS.get(key, key) + ":"
        max_label_w = (x2 - x1) - pad*2 - int(f_val.size * 6.2)
        label_fit = ellipsize_to_fit(draw, label, f_lbl, max_label_w)
        draw.text((x1 + pad, y), label_fit, fill=COLOR_TEXT, font=f_lbl)

        val_txt = display_value(key, row)
        nx = numeric_value(key, row)
        is_pct = key in PERCENT_KEYS
        has_val = (val_txt is not None) and (val_txt.strip() != "–")

        if has_val:
            color = (COLOR_BETTER if (is_pct and nx is not None and nx >= 0)
                     else COLOR_WORSE if (is_pct and nx is not None and nx < 0)
                     else COLOR_TEXT)
            pad_x, pad_y = 12, 6
            tw = int(draw.textlength(val_txt, font=f_val))
            base_w = tw + pad_x*2
            chip_w = max(base_w, chip_widths.get(key, base_w))
            chip_h = f_val.size + pad_y*2
            vx = x2 - pad - chip_w
            vy = y - int((chip_h - f_val.size)/2)
            _rounded_rect(img, (vx, vy, vx + chip_w, vy + chip_h), radius=10, fill=PALETTE["chip_bg"])
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

def draw_stat_pills(img, draw, center_x, y, row, f_lbl, f_val, card_w=None):
    info = _price_target_data(row)
    if not info:
        return y
    price, target, cur = info
    sym = _currency_sym(cur)
    pot = (target/price - 1.0) * 100.0
    arrow = "▲" if pot >= 0 else "▼"

    items = [
        ("Kurs",      fcur(price, sym)),
        ("Kursziel",  fcur(target, sym)),
        ("Potential", f"{arrow} {_fmt_locale(pot,1)}%"),
    ]

    avail = int((card_w or img.width//2) * 0.92)
    gap = int(img.width * 0.012)
    n = 3
    w = (avail - gap*(n-1)) // n
    start_x = center_x - (w*n + gap*(n-1))//2

    pill_h = f_val.size*2 + 18
    for i, (lab, val) in enumerate(items):
        x1 = start_x + i*(w+gap); x2 = x1 + w
        _rounded_rect(img, (x1, y, x2, y + pill_h), radius=14, fill=PALETTE["chip_bg"])
        lw = int(draw.textlength(lab, font=f_lbl))
        draw.text((x1 + (w - lw)//2, y + 6), lab, fill=COLOR_MUTED, font=f_lbl)
        col = COLOR_BETTER if lab=="Potential" and pot>=0 else (COLOR_WORSE if lab=="Potential" else COLOR_TEXT)
        vw = int(draw.textlength(val, font=f_val))
        draw.text((x1 + (w - vw)//2, y + 6 + f_lbl.size + 6), val, fill=col, font=f_val)
    return y + pill_h

def draw_analyst_bar(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    width: int,
    row: pd.Series,
    f_lbl,
    f_val
):
    mean = _to_float(row.get("Empfehlungsdurchschnitt"))
    if mean is None or not (0.5 <= mean <= 5.5):
        return y

    buy_frac = max(0.0, min(1.0, (5.0 - float(mean)) / 4.0))
    buy_pct  = int(round(buy_frac * 100))
    hold_pct = 100 - buy_pct

    x1 = center_x - width // 2
    x2 = center_x + width // 2
    bar_h = max(14, int(f_val.size * 0.55))
    cap_gap = 6

    _rounded_rect(img, (x1, y, x2, y + bar_h), radius=bar_h // 2, fill=PALETTE["bar_hold"])
    gx2 = x1 + int(width * buy_frac)
    if gx2 > x1:
        _rounded_rect(img, (x1, y, gx2, y + bar_h), radius=bar_h // 2, fill=COLOR_BETTER)

    lbl_y = y - f_lbl.size - 4
    draw.text((x1, lbl_y), "Kaufen", fill=COLOR_TEXT, font=f_lbl)
    rw = int(draw.textlength("Halten", font=f_lbl))
    draw.text((x2 - rw, lbl_y), "Halten", fill=COLOR_TEXT, font=f_lbl)

    bp = f"{buy_pct} %"
    hp = f"{hold_pct} %"
    draw.text((x1 + 8, y + (bar_h - f_val.size)//2), bp, fill=(255,255,255), font=f_val)
    tw_h = int(draw.textlength(hp, font=f_val))
    draw.text((x2 - tw_h - 8, y + (bar_h - f_val.size)//2), hp, fill=(30,30,30), font=f_val)

    sub = f"Einstufung & Empfehlung von Analysten  •  Ø {fmt_number(mean,2)}/5"
    ts = int(draw.textlength(sub, font=f_lbl))
    draw.text((center_x - ts//2, y + bar_h + cap_gap), sub, fill=COLOR_MUTED, font=f_lbl)

    return y + bar_h + cap_gap + f_lbl.size + 4

# ───────────────────────── Haupt-Renderfunktion ─────────────────────────
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
    TITLE_SZ = max(48, int(base_w * 0.062))
    LABEL_SZ = max(26, int(base_w * 0.034))
    VAL_SZ   = max(28, int(base_w * 0.036))
    FOOT_SZ  = max(20, int(base_w * 0.026))

    f_title = _font(FONT_BLD_PATH, TITLE_SZ, ImageFont.load_default())
    f_lbl   = _font(FONT_REG_PATH, LABEL_SZ, ImageFont.load_default())
    f_val   = _font(FONT_REG_PATH, VAL_SZ,   ImageFont.load_default())
    f_foot  = _font(FONT_REG_PATH, FOOT_SZ,  ImageFont.load_default())

    sym_a = str(rows[0].get('Symbol') or '')
    sym_b = str(rows[1].get('Symbol') or '')
    title = f"{sym_a}   vs   {sym_b}"
    tw = draw.textlength(title, font=f_title)
    draw.text(((img.width - tw)//2, int(img.height * SAFE_TOP_FRAC)), title, fill=COLOR_TEXT, font=f_title)

    # Metriken – sektorabhängige Defaults (max. 6), robust
    sec_raw = str(rows[0].get("GICS Sector") or rows[0].get("Sektor") or "").strip().lower()
    sec_key = next((k for k in SECTOR_METRICS if k in sec_raw), None)
    req_metrics = [m for m in (metrics or []) if isinstance(m, str) and m.strip()]
    if not req_metrics:
        defaults = SECTOR_METRICS.get(sec_key, ["KGV","Forward PE","KUV","Nettomarge","Eigenkapitalrendite","Umsatzwachstum 3J (erwartet)"])
        series0 = rows[0]
        metrics = [m for m in defaults if resolve_col(series0, m)]
    else:
        metrics = req_metrics
    metrics = metrics[:6]

    # Karten-Bereich
    top = int(img.height * (SAFE_TOP_FRAC + 0.085))
    margin_x = int(img.width * SAFE_MARGIN_X)
    gap = int(img.width * 0.04)
    card_w = (img.width - margin_x*2 - gap) // 2
    card_h = int(img.height * 0.50)

    card_a = (margin_x, top, margin_x + card_w, top + card_h)
    card_b = (margin_x + card_w + gap, top, margin_x + card_w*2 + gap, top + card_h)

    # Gleichbreite Chips je Kennzahl (max über beide Cards)
    chip_widths: Dict[str,int] = {}
    pad_x_measure = 12
    for key in metrics[:6]:
        t1 = display_value(key, rows[0]); t2 = display_value(key, rows[1])
        tw1 = int(draw.textlength(t1, font=f_val)) if t1 and t1.strip() != "–" else 0
        tw2 = int(draw.textlength(t2, font=f_val)) if t2 and t2.strip() != "–" else 0
        mx = max(tw1, tw2)
        if mx > 0:
            chip_widths[key] = mx + pad_x_measure*2

    # Cards
    draw_company_card(img, draw, card_a, rows[0], sym_a, "", metrics, chip_widths, f_title, f_lbl, f_val)
    draw_company_card(img, draw, card_b, rows[1], sym_b, "", metrics, chip_widths, f_title, f_lbl, f_val)

    # Geplante Höhen für Pills/Bar -> Bottom-Clamp vor dem Zeichnen
    est_pill_h = f_val.size*2 + 18
    est_bar_h  = max(14, int(f_val.size*0.55)) + 6 + f_lbl.size + 4
    y_pills = max(card_a[3], card_b[3]) + int(img.height * 0.012)
    safe_bottom = img.height - int(img.height * SAFE_BOTTOM_FRAC) - 10
    need_bottom = y_pills + est_pill_h + int(img.height * 0.016) + est_bar_h
    overflow = need_bottom - safe_bottom
    if overflow > 0:
        y_pills = max(max(card_a[3], card_b[3]) + 2, y_pills - overflow)

    # Pills zeichnen
    center_a = (card_a[0] + card_a[2]) // 2
    center_b = (card_b[0] + card_b[2]) // 2
    y_after_a = draw_stat_pills(img, draw, center_a, y_pills, rows[0], f_lbl, f_val, card_w=card_w)
    y_after_b = draw_stat_pills(img, draw, center_b, y_pills, rows[1], f_lbl, f_val, card_w=card_w)

    # Analysten-Bar
    bar_w = int(card_w * 0.88)
    y_bar = max(y_after_a, y_after_b) + int(img.height * 0.016)
    y_bar_a = draw_analyst_bar(img, draw, center_a, y_bar, bar_w, rows[0], f_lbl, f_val)
    y_bar_b = draw_analyst_bar(img, draw, center_b, y_bar, bar_w, rows[1], f_lbl, f_val)

    # Footer
    footer_top = max(y_bar_a, y_bar_b) + int(img.height * 0.028)
    foot = f"Stand: {datetime.today().strftime('%d.%m.%Y')}  •  Quelle: Yahoo Finance"
    fw = draw.textlength(foot, font=f_foot)
    fx = (img.width - int(fw)) // 2
    fy = max(footer_top, img.height - int(img.height * SAFE_BOTTOM_FRAC * 0.85))
    draw.text((fx, fy), foot, fill=(30, 34, 38), font=f_foot)

    return img

# ───────────────────────── Flask ─────────────────────────
app = Flask(__name__)

@app.route("/")
def compare_home():
    return render_template_string(COMPOSE_HTML)

@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip().lower()
    df = load_df()
    if not q:
        return jsonify([])
    out = []
    for _, row in df.iterrows():
        sym = str(row.get('Symbol') or '')
        sec = str(row.get('Security') or '')
        if q in sym.lower() or q in sec.lower():
            out.append({'symbol': sym, 'name': sec})
        if len(out) >= 12:
            break
    return jsonify(out)

@app.route('/api/peers')
def peers():
    ticker = (request.args.get('ticker') or '').upper().strip()
    df = load_df()
    row = df[df['Symbol'] == ticker].head(1)
    if row.empty:
        return jsonify([])
    sector = str(row.iloc[0].get('GICS Sector') or '')
    peers_df = df[(df['GICS Sector'] == sector) & (df['Symbol'] != ticker)]
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
        """<!doctype html><html><head><meta charset="utf-8"><title>Vergleich</title>
        <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial;margin:24px}
        .wrap{max-width:1120px;margin:auto;text-align:center}
        img{max-width:100%;height:auto;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.25)}
        a.btn{display:inline-block;margin-top:14px;padding:10px 16px;border-radius:10px;background:#111;color:#fff;text-decoration:none}
        </style></head><body><div class="wrap">
        <h1>Bild erzeugt</h1>
        <p><a class="btn" href="{{ rel }}" download>PNG herunterladen</a></p>
        <img src="{{ rel }}" alt="Compare">
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
:root{
  --bg:#0f1b2b; --panel:#0c1624; --f:#e9eef6; --muted:#9fb0c7; --acc:#10b981;
}
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

