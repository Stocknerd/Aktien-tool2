import os
import pandas as pd
import io
import time
import json
import re
import math
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Dict, Any, Optional, Tuple
from version import __version__

# ───────────────────────── Konfiguration ─────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUT_DIR = os.path.join(STATIC_DIR, "generated")
LOGO_DIR = os.path.join(STATIC_DIR, "logos")
FONT_DIR = os.path.join(STATIC_DIR, "fonts")
CSV_FILE = os.environ.get("STOCK_CSV", os.path.join(BASE_DIR, "stock_data.csv"))
BACKGROUND = os.path.join(STATIC_DIR, "default_background.png")

os.makedirs(OUT_DIR, exist_ok=True)

# Layout constants
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1350
SAFE_MARGIN_X = 0.06
SAFE_TOP_FRAC = 0.08
SAFE_BOTTOM_FRAC = 0.22
LINE_SPACING_MULT = 1.85 # Tighter line spacing for more content
METRICS_TOP_EXTRA_FRAC = 0.03

# Colors
COLOR_TEXT   = (255, 255, 255)
COLOR_MUTED  = (210, 220, 240) # Brighter silver for better contrast
COLOR_ACCENT = (16, 185, 129)
COLOR_DARK_BG = (15, 23, 42, 255) # Modern slate/navy
COLOR_CARD_BG = (255, 255, 255, 15) # Transparent glassmorphism

# Fonts
FONT_REG_PATH = os.path.join(FONT_DIR, "Montserrat-Regular.ttf")
FONT_BLD_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

# Metrics Configuration
DEFAULT_METRICS = [
    "KGV", "Forward PE", "KUV", "KBV",
    "Operative Marge", "Eigenkapitalrendite", "Dividendenrendite", "Umsatzwachstum 3J (erwartet)"
]

PERCENT_KEYS = [
    "Nettomarge", "Eigenkapitalrendite", "Umsatzwachstum 3J (erwartet)", "Dividendenrendite", 
    "Ausschüttungsquote", "Operative Marge", "Bruttomarge", "Eigenkapitalquote",
    "Umsatzwachstum 10J", "Gewinnwachstum", "5Y Dividendenrendite", "Wachstum", "Profitabilität", "Dividende"
]

METRIC_LABELS = {
    "KGV": "KGV (aktuell)", "Forward PE": "KGV (erwartet)", "KUV": "KUV", "KBV": "KBV",
    "Nettomarge": "Nettomarge (%)", "Eigenkapitalrendite": "EK-Rendite (%)",
    "Umsatzwachstum 3J (erwartet)": "Umsatz-Wachstum (3J exp)",
    "Nettoschulden/EBITDA": "Verschuldungsgrad", "Dividendenrendite": "Dividende (%)",
    "Operative Marge": "Op. Marge (%)", "Bruttomarge": "Bruttomarge (%)",
    "Marktkapitalisierung": "Börsenwert", "Ausschüttungsquote": "Payout-Ratio (%)",
    "Gewinn je Aktie": "EPS", "ROIC": "ROIC", "PEG-Ratio": "PEG-Ratio"
}

METRIC_DESC = {
    "KGV": "Kurs-Gewinn-Verhältnis (Aktueller Kurs / Gewinn der letzten 12 Monate).",
    "Forward PE": "Erwartetes KGV basierend auf Analysten-Schätzungen.",
    "KUV": "Kurs-Umsatz-Verhältnis.",
    "KBV": "Kurs-Buchwert-Verhältnis.",
    "Nettomarge": "Wie viel Prozent vom Umsatz als Gewinn übrig bleibt.",
    "Eigenkapitalrendite": "Die Verzinsung des eingesetzten Eigenkapitals.",
    "Umsatzwachstum 3J (erwartet)": "Erwartetes durchschnittliches Wachstum p.a.",
    "Nettoschulden/EBITDA": "Verschuldungsgrad.",
    "Dividendenrendite": "Dividende / Kurs (in %).",
    "Ausschüttungsquote": "Dividende / Gewinn (in %).",
    "PEG-Ratio": "KGV / erwartetes Gewinnwachstum.",
    "ROIC": "Return on Invested Capital."
}

# ───────────────────────── Shared Logic ─────────────────────────
_df_cache_lock = threading.Lock()
_CACHED_DF = None
_CACHED_MTIME = 0.0
_SEARCH_INDEX = None

def get_search_index():
    global _SEARCH_INDEX
    if _SEARCH_INDEX is not None:
        return _SEARCH_INDEX
    load_df()
    return _SEARCH_INDEX or []

def load_df():
    global _CACHED_DF, _CACHED_MTIME, _SEARCH_INDEX
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
        
    try:
        mtime = os.path.getmtime(CSV_FILE)
    except OSError:
        mtime = 0.0
        
    # Read lock-free first for speed
    if _CACHED_DF is not None and mtime == _CACHED_MTIME:
        return _CACHED_DF
        
    with _df_cache_lock:
        # Double check inside lock
        if _CACHED_DF is not None and mtime == _CACHED_MTIME:
            return _CACHED_DF
            
        try:
            df = pd.read_csv(CSV_FILE)
            # Normalize column names with encoding anomalies
            rename_map = {}
            for col in df.columns:
                if "hrung" in col:
                    rename_map[col] = "Währung"
                elif "ttungsquote" in col:
                    rename_map[col] = "Ausschüttungsquote"
                elif "qualit" in col or "qualit" in col.lower():
                    rename_map[col] = "Datenqualität"
            if rename_map:
                df = df.rename(columns=rename_map)
            _CACHED_DF = df
            _CACHED_MTIME = mtime
            
            # Rebuild search index (highly optimized)
            new_index = []
            def norm(s):
                return str(s).lower().replace('-', ' ').replace('.', ' ').strip()
                
            records = df.to_dict('records')
            for row in records:
                sym = str(row.get('Symbol') or '').strip()
                if not sym:
                    continue
                
                # Inline fast name resolution
                clean_n = "Aktie"
                for field in ['resolved_name', 'Security', 'Symbol']:
                    val = row.get(field)
                    if pd.notna(val):
                        s = str(val).strip()
                        if s and s.lower() not in ['nan', 'null', 'none', '<na>']:
                            if field == 'Symbol' and '.' in s:
                                clean_n = s.split('.')[0]
                            else:
                                clean_n = s
                            break
                
                lng = str(row.get('Langname') or '').strip()
                dy = row.get('Dividendenrendite')
                try:
                    dy_val = float(str(dy).replace(',', '.')) if pd.notna(dy) else 0.0
                    if not math.isfinite(dy_val):
                        dy_val = 0.0
                except:
                    dy_val = 0.0
                
                sector = str(row.get('Sektor') or '').strip() if pd.notna(row.get('Sektor')) else ''
                
                new_index.append({
                    'symbol': sym,
                    'name': clean_n,
                    'div_yield': round(dy_val, 2),
                    'sector': sector,
                    'norm_sym': norm(sym),
                    'norm_name': norm(clean_n),
                    'norm_lng': norm(lng)
                })
            _SEARCH_INDEX = new_index
            return df
        except Exception:
            if _CACHED_DF is not None:
                return _CACHED_DF
            return pd.DataFrame()

def get_clean_name(row):
    """
    Safely extract a clean company name from a row (Series, dict, or similar)
    prioritizing resolved_name, then Security, then Symbol, and avoiding pandas float 'nan'.
    """
    import pandas as pd
    
    # Try different name fields
    for field in ['resolved_name', 'Security', 'Symbol']:
        val = None
        if hasattr(row, 'get'):
            val = row.get(field)
        else:
            try:
                val = row[field]
            except:
                pass
        
        if pd.notna(val):
            # Check for pandas/numpy nan, or string nan, or empty string
            s = str(val).strip()
            if s and s.lower() not in ['nan', 'null', 'none', '<na>']:
                # Clean up name a bit if needed (e.g. remove ".DE" or similar if it's a symbol)
                if field == 'Symbol' and '.' in s:
                    return s.split('.')[0]
                return s
                
    # Ultimate fallback
    return "Aktie"

def _font(path: str, size: int, backup):
    try:
        f = ImageFont.truetype(path, size)
        f.path = path; f.size = size
        return f
    except Exception: return backup

def shrink_to_fit(draw, text, font, max_w, min_px=14, font_path=None):
    curr_size = getattr(font, 'size', 24)
    while curr_size > min_px:
        tw = draw.textlength(text, font=font)
        if tw <= max_w: return font, int(tw)
        curr_size -= 2
        font = _font(font_path or FONT_REG_PATH, curr_size, font)
    return font, int(draw.textlength(text, font=font))

def resize_cover(img, target_w, target_h):
    w, h = img.size
    target_aspect = target_w / target_h
    img_aspect = w / h
    if img_aspect > target_aspect:
        new_w = int(h * target_aspect)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_aspect)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

def all_metric_keys(df):
    cols = list(df.columns)
    skip = ("Symbol", "Security", "GICS Sector", "GICS Sub-Industry", "Headquarters Location", "Date added", "CIK", "Founded", "valid_yahoo_ticker", "logo_path", "Rating", "Score", "last_update", "Währung", "Region", "Sektor", "Branche")
    return [c for c in cols if c not in skip]

def display_value(key: str, row) -> str:
    val = row.get(key)
    if pd.isna(val) or val == "" or val == "–": return "–"
    try:
        f_val = float(val)
        kl = key.lower()
        # Dividendenrendite is stored as a plain decimal % (e.g. 0.4 = 0.4%)
        # Marge / Rendite / Wachstum / Quote stored as fraction (0.35 = 35%) → multiply
        is_div = "dividende" in kl and "rendite" in kl  # Dividendenrendite only
        is_div_or_yield = is_div or "yield" in kl
        should_be_percent = any(k in kl for k in [
            "rendite", "marge", "wachstum", "quote", "gewinn", "yield"
        ]) or is_div
        if should_be_percent:
            if abs(f_val) < 0.001: return "0.0%"
            if not is_div and abs(f_val) < 5.0 and f_val != 0:
                f_val *= 100  # fraction → percent
            sign = "+" if f_val > 0 and not is_div_or_yield else ""
            return f"{sign}{f_val:.1f}%"
        if abs(f_val) > 1_000_000_000: return f"{f_val/1e9:.1f} Mrd"
        if abs(f_val) > 1_000_000: return f"{f_val/1e6:.1f} Mio"
        if f_val == int(f_val): return str(int(f_val))
        return f"{f_val:.2f}"
    except (ValueError, TypeError): return str(val)

def wrap_title(draw, text, font, max_w):
    words = text.split(' ')
    lines, curr = [], []
    for w in words:
        test = ' '.join(curr + [w])
        tw = draw.textlength(test, font=font)
        if tw <= max_w: curr.append(w)
        else:
            if curr: lines.append(' '.join(curr))
            curr = [w]
    if curr: lines.append(' '.join(curr))
    return lines

# Analyst Data Cache und fetch_analyst_data wurden entfernt, da diese nun in der stock_data.csv vorgehalten werden.

# ─── Rating helpers ───────────────────────────────────────────────────────────
_RATING_MAP = {
    "strong buy":  ("STARKES KAUFEN", (16, 185, 129)),
    "buy":         ("KAUFEN",         (52, 211, 153)),
    "hold":        ("HALTEN",         (251, 191, 36)),
    "underperform":("UNTERGEWICHTEN", (249, 115, 22)),
    "sell":        ("VERKAUFEN",      (239, 68, 68)),
}

def _rating_label_color(key: str) -> Tuple[str, tuple]:
    k = (key or "").lower().strip()
    for kw, (lbl, col) in _RATING_MAP.items():
        if kw in k:
            return lbl, col
    return "KEINE DATEN", (148, 163, 184)

def _draw_watermark(draw, W, H, text="schatzsuche40.de"):
    if not text: return
    # Subtle watermark at the bottom right
    f_water = _font(FONT_REG_PATH, 28, ImageFont.load_default())
    tw = int(draw.textlength(text, font=f_water))
    draw.text((W - tw - 40, H - 70), text, fill=(255, 255, 255, 90), font=f_water)

# ─── Rendering Tools ──────────────────────────────────────────────────────────

def render_stock_card(row, selected: list, layout_mode: str = 'default',
                      watermark: str = "", bg_path: str = None, fetch_analyst: bool = True,
                      ai_verdict: str = ""):
    """Render a premium single-stock Infographic card (1080×1350)."""
    W, H = OUTPUT_WIDTH, OUTPUT_HEIGHT

    # ── 1. Background ─────────────────────────────────────────────
    bg_src = bg_path or BACKGROUND
    try:
        img = resize_cover(Image.open(bg_src).convert("RGBA"), W, H)
    except Exception:
        img = Image.new("RGBA", (W, H), (15, 23, 42, 255))

    # Dark overlay — solid dark wash; fades in bottom 280px so background branding shows
    FADE_H     = 280
    BASE_ALPHA = 195
    MIN_ALPHA  = 65   # alpha at very bottom edge

    # Build grayscale alpha mask: BASE_ALPHA above strip, fading to MIN_ALPHA at bottom
    alpha_mask = Image.new("L", (W, H), BASE_ALPHA)
    mask_draw  = ImageDraw.Draw(alpha_mask)
    for fy in range(H - FADE_H, H):
        t = (fy - (H - FADE_H)) / FADE_H
        v = int(BASE_ALPHA - (BASE_ALPHA - MIN_ALPHA) * t)
        mask_draw.line([(0, fy), (W, fy)], fill=v)

    # Merge dark colour + alpha mask into RGBA overlay
    ov_rgb  = Image.new("RGB", (W, H), (8, 12, 28))
    overlay = Image.merge("RGBA", (*ov_rgb.split(), alpha_mask))

    # Subtle teal glow at top-center
    ov_draw = ImageDraw.Draw(overlay)
    for r_px in range(280, 0, -8):
        a = int(30 * (1 - r_px / 280))
        ov_draw.ellipse([W//2 - r_px, -r_px//3, W//2 + r_px, r_px],
                        fill=(16, 185, 129, a))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    ACCENT   = (16, 185, 129)
    MUTED    = (210, 225, 245) # Improved visibility
    WHITE    = (255, 255, 255)
    CARD_BG  = (8, 14, 35, 210)
    CARD_BDR = (16, 185, 129, 180) # Stronger border contrast

    # ── 2. Fonts ──────────────────────────────────────────────────
    f_title  = _font(FONT_BLD_PATH, 52, ImageFont.load_default())
    f_sym    = _font(FONT_REG_PATH, 30, ImageFont.load_default())
    f_sector = _font(FONT_REG_PATH, 24, ImageFont.load_default())
    f_lbl    = _font(FONT_REG_PATH, 26, ImageFont.load_default())
    f_val    = _font(FONT_BLD_PATH, 42, ImageFont.load_default())
    f_foot   = _font(FONT_REG_PATH, 22, ImageFont.load_default())
    f_anlbl  = _font(FONT_BLD_PATH, 26, ImageFont.load_default())
    f_anval  = _font(FONT_BLD_PATH, 36, ImageFont.load_default())
    f_badge  = _font(FONT_BLD_PATH, 28, ImageFont.load_default())

    MID = W // 2
    PAD = 64

    # ── 3. Logo ───────────────────────────────────────────────────
    symb   = str(row.get('Symbol') or '')
    name   = get_clean_name(row)
    sector = str(row.get('Sektor') or row.get('GICS Sector') or '')
    currency = str(row.get('Währung') or row.get('W\u00e4hrung') or 'USD')

    logo_path = os.path.join(LOGO_DIR, f"{symb}.png")
    if not os.path.exists(logo_path) and '.' in symb:
        base_symb = symb.split('.')[0]
        logo_path = os.path.join(LOGO_DIR, f"{base_symb}.png")
        
    logo_h = 130
    logo_max_w = W - 2 * PAD
    y = 35   # Moved up from 60
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            ratio = logo_h / logo.height
            lw = int(logo.width * ratio)
            if lw > logo_max_w:
                ratio = logo_max_w / lw
                lw = logo_max_w
                lh = int(logo_h * ratio)
            else:
                lh = logo_h
            logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
            img.alpha_composite(logo, ((W - lw) // 2, y))
            y += lh + 2 # Tighter padding
        except Exception:
            pass

    # ── 4. Company Name + Symbol ──────────────────────────────────
    max_nw = W - 2 * PAD
    fn, _ = shrink_to_fit(draw, name.upper(), f_title, max_nw, 28, FONT_BLD_PATH)
    tw = int(draw.textlength(name.upper(), font=fn))
    draw.text(((W - tw) // 2, y), name.upper(), fill=WHITE, font=fn)
    y += getattr(fn, 'size', 52) + 0 # Compressed

    # Symbol pill
    sym_text = f"  {symb}  "
    sw = int(draw.textlength(sym_text, font=f_sym))
    px, py = (W - sw) // 2, y
    draw.rounded_rectangle([px - 4, py - 2, px + sw + 4, py + 34], radius=10, fill=(16, 185, 129, 100))
    draw.text((px, py), sym_text, fill=(255, 255, 255), font=f_sym)
    y += 44

    # Sector label
    if sector:
        sec_tw = int(draw.textlength(sector, font=f_sector))
        draw.text(((W - sec_tw) // 2, y), sector, fill=MUTED, font=f_sector)
        y += 34

    y += 20  # breathing room

    # ── 5. Metric Cards ───────────────────────────────────────────
    metrics = (selected or DEFAULT_METRICS)[:8]
    margin_x = PAD
    col_gap  = 18
    col_w    = (W - 2 * margin_x - col_gap) // 2
    card_h   = 98    # Ultra-compact
    card_gap = 8    # Ultra-compact
    col_x    = [margin_x, margin_x + col_w + col_gap]
    num_rows = math.ceil(len(metrics) / 2)

    for i, m in enumerate(metrics):
        col   = i % 2
        row_i = i // 2
        cx = col_x[col]
        cy = y + row_i * (card_h + card_gap)

        # Glassmorphism card with subtle border
        draw.rounded_rectangle([cx, cy, cx + col_w, cy + card_h], radius=16, fill=CARD_BG)
        draw.rounded_rectangle([cx, cy, cx + col_w, cy + card_h], radius=16, outline=CARD_BDR, width=2)

        lab     = METRIC_LABELS.get(m, m)
        val_str = display_value(m, row)

        # Label top-left — bright grey-white
        draw.text((cx + 16, cy + 12), lab, fill=MUTED, font=f_lbl)

        # Value bottom-right, large and bold — full white
        vw = int(draw.textlength(val_str, font=f_val))
        vx = cx + col_w - 16 - vw
        vy = cy + card_h - 42 - 12
        draw.text((vx, vy), val_str, fill=WHITE, font=f_val)

    last_card_bottom = y + num_rows * (card_h + card_gap)
    y = last_card_bottom + 10 # Drastic reduction from 30

    # ── 6. Analyst Section ────────────────────────────────────────
    if fetch_analyst:
        cur = _safe_float(row.get("Current Price")) or _safe_float(row.get("Vortagesschlusskurs"))
        mean_t = _safe_float(row.get("Analyst Mean Target")) or _safe_float(row.get("Analysten_Kursziel"))
        high_t = _safe_float(row.get("Analyst High Target")) or _safe_float(row.get("Kursziel_Hoch"))
        low_t  = _safe_float(row.get("Analyst Low Target")) or _safe_float(row.get("Kursziel_Tief"))
        rec_key = str(row.get("Recommendation Key") or row.get("Analysten_Empfehlung", ""))
        if rec_key == "nan": rec_key = ""
        n_analysts = _safe_float(row.get("Number of Analysts")) or _safe_float(row.get("Anzahl Analystenmeinungen"))
    else:
        cur, mean_t, high_t, low_t, rec_key, n_analysts = 0, 0, 0, 0, "", 0

    # Only draw if we have enough data
    panel_bottom = y   # will be updated if analyst section drawn
    if cur and mean_t and low_t and high_t:
        PANEL_H = 195 # Squeezed from 225
        panel_x1, panel_x2 = PAD, W - PAD
        panel_w  = panel_x2 - panel_x1
        panel_bottom = y + PANEL_H   # track for footer placement

        # Panel container (drawn first, content on top)
        draw.rounded_rectangle([panel_x1, y, panel_x2, y + PANEL_H], radius=20, fill=(255, 255, 255, 15))
        draw.rounded_rectangle([panel_x1, y, panel_x2, y + PANEL_H], radius=20, outline=(16, 185, 129, 160), width=2)

        if mean_t and cur:
            # Panel header
            header = "ANALYSTENRATING & KURSZIEL"
            hw = int(draw.textlength(header, font=f_sector))
            draw.text(((W - hw) // 2, y + 12), header, fill=(100, 115, 140), font=f_sector)
            
            BAR_Y    = y + 50
            BAR_H    = 20
            BAR_X    = panel_x1 + 60
            BAR_W    = panel_w - 120
            
            f_small = _font(FONT_REG_PATH, 20, ImageFont.load_default())
            lbl_y = BAR_Y + BAR_H + 8
            
            if high_t and low_t:
                # Gradient bar low→high (red→yellow→green)
                for bx in range(BAR_W):
                    t = bx / BAR_W
                    r = int(239 * (1 - t) + 16 * t)
                    g = int(68  * (1 - t) + 185 * t)
                    b = int(68  * (1 - t) + 129 * t)
                    draw.rectangle([BAR_X + bx, BAR_Y, BAR_X + bx + 1, BAR_Y + BAR_H], fill=(r, g, b, 200))

                # Round ends
                draw.ellipse([BAR_X - BAR_H//2, BAR_Y, BAR_X + BAR_H//2, BAR_Y + BAR_H], fill=(239, 68, 68, 200))
                draw.ellipse([BAR_X + BAR_W - BAR_H//2, BAR_Y, BAR_X + BAR_W + BAR_H//2, BAR_Y + BAR_H], fill=(16, 185, 129, 200))

                # Scale: clamp values to bar axis
                price_range = high_t - low_t
                def _to_bar_x(p):
                    if price_range <= 0: return BAR_X + BAR_W // 2
                    frac = min(max((p - low_t) / price_range, 0), 1)
                    return int(BAR_X + frac * BAR_W)

                mx = _to_bar_x(mean_t)
                D = 12
                draw.polygon([(mx, BAR_Y - D), (mx + D, BAR_Y + BAR_H//2), (mx, BAR_Y + BAR_H + D), (mx - D, BAR_Y + BAR_H//2)],
                             fill=(255, 255, 255, 230))

                cpx = _to_bar_x(cur)
                R = 10
                draw.ellipse([cpx - R, BAR_Y + BAR_H//2 - R, cpx + R, BAR_Y + BAR_H//2 + R], fill=(255, 230, 80, 255))
                draw.ellipse([cpx - R, BAR_Y + BAR_H//2 - R, cpx + R, BAR_Y + BAR_H//2 + R], outline=(255, 255, 255, 200), width=2)

                draw.text((BAR_X, lbl_y), f"{currency} {low_t:.0f}", fill=(239, 100, 100), font=f_small)
                high_lbl = f"{currency} {high_t:.0f}"
                hl_w = int(draw.textlength(high_lbl, font=f_small))
                draw.text((BAR_X + BAR_W - hl_w, lbl_y), high_lbl, fill=(52, 211, 153), font=f_small)
            else:
                mx = W // 2
            
            mean_lbl = f"Ø Ziel: {currency} {mean_t:.0f}"
            ml_w = int(draw.textlength(mean_lbl, font=f_small))
            draw.text((MID - ml_w//2, lbl_y), mean_lbl, fill=(140, 150, 170), font=f_small)

            # Current price and upside (below labels)
            upside = ((mean_t - cur) / cur) * 100 if cur else 0
            up_sign = "+" if upside >= 0 else ""
            upside_col = (52, 211, 153) if upside >= 0 else (239, 68, 68)

            cur_lbl = f"Kurs: {currency} {cur:.2f}"
            upside_lbl = f"Kursziel-Potenzial: {up_sign}{upside:.1f}%"
            if n_analysts:
                upside_lbl += f"  ({int(n_analysts)} Analysten)"

            row2_y = lbl_y + 36
            draw.text((BAR_X, row2_y), cur_lbl, fill=WHITE, font=f_anlbl)
            rhs_w = int(draw.textlength(upside_lbl, font=f_anlbl))
            draw.text((panel_x2 - rhs_w, row2_y), upside_lbl, fill=upside_col, font=f_anlbl)

            # Consensus badge
            rec_label, rec_color = _rating_label_color(rec_key)
            badge_text = f"  {rec_label}  "
            bw = int(draw.textlength(badge_text, font=f_badge))
            bx = (W - bw) // 2
            bby = row2_y + 40
            draw.rounded_rectangle([bx - 6, bby - 4, bx + bw + 6, bby + 36], radius=10, fill=(*rec_color, 60))
            draw.rounded_rectangle([bx - 6, bby - 4, bx + bw + 6, bby + 36], radius=10, outline=(*rec_color, 180), width=2)
            draw.text((bx, bby), badge_text, fill=(255, 255, 255), font=f_badge)

            y = bby + 44

        panel_bottom = y

    # ── 7. AI Verdict Section (New for Single Stock Card) ─────────
    if ai_verdict and ai_verdict.strip():
        av_pad = 40
        av_w = W - 2 * PAD
        f_av_bld = _font(FONT_BLD_PATH, 24, ImageFont.load_default())
        
        # Calculate text wrapping
        av_text = ai_verdict.strip()
        av_lines = wrap_title(draw, av_text, f_av_bld, av_w - 60)
        # Dynamic box height: header + lines * line_height + bottom padding
        av_box_h = 65 + len(av_lines) * 28
        
        av_y = panel_bottom + 10
        # Draw AI Branding / Box
        draw.rounded_rectangle([PAD, av_y, W - PAD, av_y + av_box_h], radius=15, fill=(10, 35, 25, 240))
        draw.rounded_rectangle([PAD, av_y, W - PAD, av_y + av_box_h], radius=15, outline=(16, 185, 129, 200), width=3)
        
        # Icon/Label (Centered)
        ai_label = "KI-BEWERTUNG"
        al_w = int(draw.textlength(ai_label, font=f_av_bld))
        draw.text(((W - al_w) // 2, av_y + 12), ai_label, fill=WHITE, font=f_av_bld)
        
        for li, line in enumerate(av_lines):
            lw = int(draw.textlength(line, font=f_av_bld))
            draw.text(((W - lw) // 2, av_y + 50 + li * 28), line, fill=WHITE, font=f_av_bld)
            
        panel_bottom = av_y + av_box_h + 10

    # Place ABOVE the background logo strip (which starts ~280px from bottom)
    abfrage = str(row.get('Abfragedatum') or row.get('last_update') or '')
    try:
        date_str = datetime.strptime(abfrage[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        date_str = datetime.today().strftime('%d.%m.%Y')

    footer_y = panel_bottom + 14   # right below analyst panel, above background branding
    foot1 = f"STAND: {date_str}  •  DATENQUELLE: YAHOO FINANCE  •  v{__version__}"
    if watermark:
        lines = [foot1, watermark.upper()]
    else:
        lines = [foot1]
    for fi, ft in enumerate(lines):
        tw = int(draw.textlength(ft, font=f_foot))
        draw.text(((W - tw) // 2, footer_y + fi * 28), ft, fill=(170, 180, 200), font=f_foot)

    _draw_watermark(draw, W, H)
    return img

def _safe_float(v):
    try:
        return float(v) if v and str(v) not in ('nan', 'None', '') else None
    except Exception:
        return None


def _parse_num(s: str):
    """Extract a float from a display string like '+35.4%' or '33.23'."""
    try:
        m = re.search(r'[-+]?\d*\.?\d+', str(s).replace(',', '.'))
        return float(m.group()) if m else None
    except: return None

def _is_low_better(metric_key: str) -> bool:
    mk = metric_key.upper()
    if any(x in mk for x in ["MARGE", "RENDITE", "GROWTH", "WACHSTUM"]):
        return False
    return any(k in mk for k in ["KGV", "PE", "KUV", "KBV", "SCHULDEN", "PEG", "EV/", "VERSCHULDUNG"])

def _compare_values(n1: float, n2: float, low_better: bool) -> Tuple[bool, bool]:
    """
    Safely compare two numbers.
    For low_better: lower is better.
    For high_better: higher is better.
    """
    if low_better:
        return n1 < n2, n2 < n1
    else:
        return n1 > n2, n2 > n1

def render_compare(rows: List[pd.Series], metrics: List[str] = None, watermark: str = "",
                   bg_path: str = None, fetch_analyst: bool = False, ai_verdict: str = "") -> Image.Image:
    """Render a premium side-by-side stock comparison card (1080×1350)."""
    W, H = OUTPUT_WIDTH, OUTPUT_HEIGHT

    # ── 1. Background — same treatment as single card ──────────────
    bg_src = bg_path or BACKGROUND
    try:
        img = resize_cover(Image.open(bg_src).convert("RGBA"), W, H)
    except Exception:
        img = Image.new("RGBA", (W, H), (15, 23, 42, 255))

    # Dark overlay with bottom fade (identical logic to render_stock_card)
    FADE_H     = 280
    BASE_ALPHA = 210   # slightly darker than single card for busy compare layout
    MIN_ALPHA  = 65

    alpha_mask = Image.new("L", (W, H), BASE_ALPHA)
    mask_draw  = ImageDraw.Draw(alpha_mask)
    for fy in range(H - FADE_H, H):
        t = (fy - (H - FADE_H)) / FADE_H
        v = int(BASE_ALPHA - (BASE_ALPHA - MIN_ALPHA) * t)
        mask_draw.line([(0, fy), (W, fy)], fill=v)

    ov_rgb  = Image.new("RGB", (W, H), (8, 12, 28))
    overlay = Image.merge("RGBA", (*ov_rgb.split(), alpha_mask))

    # Teal glow at top
    ov_draw = ImageDraw.Draw(overlay)
    for r_px in range(320, 0, -8):
        a = int(40 * (1 - r_px / 320))
        ov_draw.ellipse([W//2 - r_px, -r_px//2, W//2 + r_px, r_px],
                        fill=(16, 185, 129, a))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Colours
    ACCENT    = (16, 185, 129)
    ACCENT2   = (96, 165, 250)    # blue for right side
    WIN_COL   = (52, 211, 153)
    LOSE_COL  = (148, 163, 184)
    BAR_LEFT  = (16, 185, 129, 210)
    BAR_RIGHT = (96, 165, 250, 210)
    BAR_BG    = (255, 255, 255, 20)
    MUTED     = (180, 195, 220)
    WHITE     = (255, 255, 255)
    ROW_BG    = (8, 14, 35, 200)   # dark navy — match single card metric cards
    ROW_BDR_L = (16, 185, 129, 120)
    ROW_BDR_R = (96, 165, 250, 120)

    # ── 2. Fonts ───────────────────────────────────────────────────
    f_name  = _font(FONT_BLD_PATH, 44, ImageFont.load_default())
    f_sym   = _font(FONT_REG_PATH, 26, ImageFont.load_default())
    f_lbl   = _font(FONT_REG_PATH, 24, ImageFont.load_default())
    f_val   = _font(FONT_BLD_PATH, 36, ImageFont.load_default())   # bigger values
    f_vs    = _font(FONT_BLD_PATH, 56, ImageFont.load_default())
    f_foot  = _font(FONT_REG_PATH, 20, ImageFont.load_default())
    f_score = _font(FONT_BLD_PATH, 38, ImageFont.load_default())
    f_scap  = _font(FONT_REG_PATH, 22, ImageFont.load_default())

    MID = W // 2
    PAD = 64

    # ── 3. Company Logos ───────────────────────────────────────────
    LOGO_ZONE  = MID - PAD - 40
    MAX_LOGO_H = 90
    for side, row in enumerate(rows):
        sym = str(row.get('Symbol', ''))
        logo_path = os.path.join(LOGO_DIR, f"{sym}.png")
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                ratio = MAX_LOGO_H / logo.height
                lw, lh = int(logo.width * ratio), MAX_LOGO_H
                if lw > LOGO_ZONE:
                    ratio = LOGO_ZONE / lw
                    lw, lh = LOGO_ZONE, int(lh * ratio)
                logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                logo_y = 28 + (MAX_LOGO_H - lh) // 2
                lx = PAD if side == 0 else W - PAD - lw
                img.alpha_composite(logo, (lx, logo_y))
            except Exception:
                pass

    draw = ImageDraw.Draw(img)   # refresh after compositing logos

    # ── 4. VS badge ────────────────────────────────────────────────
    vs_w = int(draw.textlength("VS", font=f_vs))
    draw.text((MID - vs_w // 2, 40), "VS", fill=(255, 255, 255, 200), font=f_vs)

    # ── 5. Company Names + Tickers ────────────────────────────────
    name1 = get_clean_name(rows[0])
    name2 = get_clean_name(rows[1])
    sym1  = str(rows[0].get('Symbol', ''))
    sym2  = str(rows[1].get('Symbol', ''))

    max_nw = int(W * 0.40)
    fn1, _    = shrink_to_fit(draw, name1.upper(), f_name, max_nw, 20, FONT_BLD_PATH)
    fn2, tw2n = shrink_to_fit(draw, name2.upper(), f_name, max_nw, 20, FONT_BLD_PATH)

    draw.text((PAD, 155), name1.upper(), fill=WHITE, font=fn1)
    draw.text((W - PAD - tw2n, 155), name2.upper(), fill=WHITE, font=fn2)

    # Ticker pills
    for ticker, side_col, anchor_x, align in [
        (sym1, ACCENT,  PAD,         "left"),
        (sym2, ACCENT2, W - PAD,     "right"),
    ]:
        txt = f"  {ticker}  "
        tw  = int(draw.textlength(txt, font=f_sym))
        tx  = anchor_x if align == "left" else anchor_x - tw
        ty  = 205
        draw.rounded_rectangle([tx - 4, ty - 2, tx + tw + 4, ty + 30], radius=8,
                                fill=(*side_col, 100))
        draw.text((tx, ty), txt, fill=WHITE, font=f_sym)

    # Vertical divider
    draw.line([(MID, 155), (MID, 255)], fill=(255, 255, 255, 50), width=2)

    # ── 6. Metric Rows ─────────────────────────────────────────────
    if metrics is None:
        metrics = DEFAULT_METRICS
    metrics_clean = [m for m in metrics if m][:8]
    ROW_START = 240
    ROW_H     = 66
    ROW_GAP   = 12
    BAR_H     = 4
    score1, score2 = 0, 0

    for i, m in enumerate(metrics_clean):
        row_y  = ROW_START + i * (ROW_H + ROW_GAP)

        v1_str = display_value(m, rows[0])
        v2_str = display_value(m, rows[1])
        n1 = _parse_num(v1_str)
        n2 = _parse_num(v2_str)

        col1, col2 = WHITE, WHITE
        bar_frac1, bar_frac2 = 0.5, 0.5

        if n1 is not None and n2 is not None and n1 != n2:
            low_better = _is_low_better(m)
            w1, w2 = _compare_values(n1, n2, low_better)
            col1 = WIN_COL if w1 else (LOSE_COL if w2 else WHITE)
            col2 = WIN_COL if w2 else (LOSE_COL if w1 else WHITE)
            if w1:   score1 += 1
            elif w2: score2 += 1

            abs1, abs2 = abs(n1), abs(n2)
            total = abs1 + abs2
            if total > 0:
                bar_frac1 = abs1 / total
                bar_frac2 = abs2 / total
            if low_better:
                bar_frac1, bar_frac2 = bar_frac2, bar_frac1

        # Full-width Single Card per Row
        draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, fill=ROW_BG)
        draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, outline=(255, 255, 255, 20), width=2)

        # Metric label — centered
        label = METRIC_LABELS.get(m, m).upper()
        tw_l  = int(draw.textlength(label, font=f_lbl))
        draw.text((MID - tw_l // 2, row_y + 18), label, fill=MUTED, font=f_lbl)

        # Values
        tw_v2 = int(draw.textlength(v2_str, font=f_val))
        draw.text((PAD + 24, row_y + 14), v1_str, fill=col1, font=f_val)
        draw.text((W - PAD - 24 - tw_v2, row_y + 14), v2_str, fill=col2, font=f_val)

        # Progress bars
        BAR_MAX = int((W - 2 * PAD - tw_l - 80) / 2)
        b_y = row_y + ROW_H - 12
        
        # Left Bar
        draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + BAR_MAX, b_y + BAR_H], radius=2, fill=BAR_BG)
        w1b = int(BAR_MAX * bar_frac1)
        if w1b > 0:
            draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + w1b, b_y + BAR_H], radius=2, fill=BAR_LEFT)
            
        # Right Bar
        draw.rounded_rectangle([W - PAD - 24 - BAR_MAX, b_y, W - PAD - 24, b_y + BAR_H], radius=2, fill=BAR_BG)
        w2b = int(BAR_MAX * bar_frac2)
        if w2b > 0:
            draw.rounded_rectangle([W - PAD - 24 - w2b, b_y, W - PAD - 24, b_y + BAR_H], radius=2, fill=BAR_RIGHT)


    an_y = ROW_START + len(metrics_clean) * (ROW_H + ROW_GAP) + 12
    if fetch_analyst:
        def _get_an(r):
            rk = str(r.get("Recommendation Key") or r.get("Analysten_Empfehlung", ""))
            return {
                "recommendationKey": rk if rk != "nan" else "",
                "targetMeanPrice": _safe_float(r.get("Analyst Mean Target")) or _safe_float(r.get("Analysten_Kursziel")),
                "currentPrice": _safe_float(r.get("Current Price")) or _safe_float(r.get("Vortagesschlusskurs")),
                "numberOfAnalysts": _safe_float(r.get("Number of Analysts")) or _safe_float(r.get("Anzahl Analystenmeinungen"))
            }
        
        a1 = _get_an(rows[0])
        a2 = _get_an(rows[1])
        
        has_a1 = a1 and (a1.get("recommendationKey") or a1.get("targetMeanPrice"))
        has_a2 = a2 and (a2.get("recommendationKey") or a2.get("targetMeanPrice"))
        
        if has_a1 or has_a2:
            AN_H = 100
            draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, fill=(255, 255, 255, 12))
            draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, outline=(255, 255, 255, 40), width=2)
            
            draw.text((MID - draw.textlength("ANALYSTENRATING", font=f_lbl)//2, an_y + 12), "ANALYSTENRATING", fill=MUTED, font=f_lbl)
            
            f_an_val = _font(FONT_BLD_PATH, 22, ImageFont.load_default())
            f_an_lbl = _font(FONT_REG_PATH, 22, ImageFont.load_default())
            f_an_bld = _font(FONT_BLD_PATH, 22, ImageFont.load_default())
            
            def draw_analyst_side(a_data, is_left):
                if not a_data: a_data = {}
                rec = str(a_data.get("recommendationKey", "KEINE DATEN")).upper().replace('_', ' ')
                rec_ger = {"STRONG BUY": "STARKER KAUF", "BUY": "KAUFEN", "HOLD": "HALTEN", 
                           "SELL": "VERKAUFEN", "STRONG SELL": "STARKER VERKAUF"}.get(rec, rec)
                if not rec_ger: rec_ger = "KEINE DATEN"
                
                c_prc = a_data.get("currentPrice", 0) or 0
                m_t = a_data.get("targetMeanPrice", 0) or 0
                n_a = a_data.get("numberOfAnalysts", 0) or 0
                pot = ((m_t - c_prc) / c_prc * 100) if c_prc else 0
                
                txt_ziel = f"Ziel: "
                txt_pot = f"{'+' if pot > 0 else ''}{pot:.1f}%" if m_t else "N/A"
                txt_tail = f" ({int(n_a)} Analysten)" if n_a else ""
                
                if rec_ger in ["STARKER KAUF", "KAUFEN"]:
                    bg_col = (16, 185, 129)  # Green
                elif rec_ger in ["VERKAUFEN", "STARKER VERKAUF"]:
                    bg_col = (239, 68, 68)   # Red
                else:
                    bg_col = (156, 163, 175) # Gray
                    
                tw_rec = int(draw.textlength(rec_ger, font=f_an_val))
                badge_w = tw_rec + 24
                badge_h = 32
                
                txt_ziel = f"Ziel: "
                txt_pot = f"{'+' if pot > 0 else ''}{pot:.1f}%" if m_t else "N/A"
                txt_tail = f" ({int(n_a)} Analysten)" if n_a else ""
                
                tw_ziel = int(draw.textlength(txt_ziel, font=f_an_lbl))
                tw_pot = int(draw.textlength(txt_pot, font=f_an_bld))
                tw_tail = int(draw.textlength(txt_tail, font=f_an_lbl))
                
                if is_left:
                    # Badge Top-Left
                    bx = PAD + 24
                    by = an_y + 16
                    draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=16, fill=bg_col)
                    draw.text((bx + 12, by + 1), rec_ger, fill=WHITE, font=f_an_val)
                    
                    # Details Left
                    dx = PAD + 24
                    dy = an_y + 60
                    draw.text((dx, dy), txt_ziel, fill=MUTED, font=f_an_lbl)
                    dx += tw_ziel
                    draw.text((dx, dy), txt_pot, fill=bg_col, font=f_an_bld)
                    dx += tw_pot
                    draw.text((dx, dy), txt_tail, fill=MUTED, font=f_an_lbl)
                else:
                    # Badge Top-Right
                    bx = W - PAD - 24 - badge_w
                    by = an_y + 16
                    draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=16, fill=bg_col)
                    draw.text((bx + 12, by + 1), rec_ger, fill=WHITE, font=f_an_val)
                    
                    # Details Right
                    dw = tw_ziel + tw_pot + tw_tail
                    dx = W - PAD - 24 - dw
                    dy = an_y + 60
                    draw.text((dx, dy), txt_ziel, fill=MUTED, font=f_an_lbl)
                    dx += tw_ziel
                    draw.text((dx, dy), txt_pot, fill=bg_col, font=f_an_bld)
                    dx += tw_pot
                    draw.text((dx, dy), txt_tail, fill=MUTED, font=f_an_lbl)
                    
            draw_analyst_side(a1, True)
            draw_analyst_side(a2, False)
            an_y += AN_H + 20

    # ── 7. AI Verdict Section (New) ──────────────────────────────
    if ai_verdict and ai_verdict.strip():
        av_pad = 40
        av_w = W - 2*PAD
        f_av_bld = _font(FONT_BLD_PATH, 24, ImageFont.load_default())
        
        # Calculate text wrapping
        av_text = ai_verdict.strip()
        av_lines = wrap_title(draw, av_text, f_av_bld, av_w - 60)
        # Dynamic box height: header + lines * line_height + bottom padding
        av_box_h = 65 + len(av_lines) * 28
        
        av_y = an_y + 2
        # Draw AI Branding / Box
        draw.rounded_rectangle([PAD, av_y, W - PAD, av_y + av_box_h], radius=15, fill=(10, 35, 25, 240))
        draw.rounded_rectangle([PAD, av_y, W - PAD, av_y + av_box_h], radius=15, outline=(16, 185, 129, 200), width=3)
        
        # Icon/Label (Centered)
        ai_label = "KI-BEWERTUNG"
        al_w = int(draw.textlength(ai_label, font=f_av_bld))
        draw.text(((W - al_w) // 2, av_y + 12), ai_label, fill=WHITE, font=f_av_bld)
        
        for li, line in enumerate(av_lines):
            lw = int(draw.textlength(line, font=f_av_bld))
            draw.text(((W - lw) // 2, av_y + 50 + li * 28), line, fill=WHITE, font=f_av_bld)
            
        an_y = av_y + av_box_h + 20

    # ── 8. Score Panel ─────────────────────────────────────────────
    score_y = an_y
    total_scored = max(score1 + score2, 1)
    PANEL_H  = 155
    panel_bottom = score_y + PANEL_H

    draw.rounded_rectangle([PAD, score_y, W - PAD, panel_bottom],
                            radius=18, fill=(8, 14, 35, 200))
    draw.rounded_rectangle([PAD, score_y, W - PAD, panel_bottom],
                            radius=18, outline=(16, 185, 129, 80), width=2)

    # Score labels
    draw.text((PAD + 20, score_y + 16), f"{sym1}:  {score1} Punkte",
              fill=WIN_COL if score1 >= score2 else MUTED, font=f_scap)
    rhs_lbl = f"{score2} Punkte  :{sym2}"
    rhs_w   = int(draw.textlength(rhs_lbl, font=f_scap))
    draw.text((W - PAD - 20 - rhs_w, score_y + 16), rhs_lbl,
              fill=WIN_COL if score2 > score1 else MUTED, font=f_scap)

    # Score bar
    SBAR_X = PAD + 40
    SBAR_W = W - 2 * PAD - 80
    SBAR_Y = score_y + 48
    SBAR_H = 18
    draw.rounded_rectangle([SBAR_X, SBAR_Y, SBAR_X + SBAR_W, SBAR_Y + SBAR_H],
                            radius=9, fill=(255, 255, 255, 20))
    frac1   = score1 / total_scored
    bar_end = SBAR_X + int(SBAR_W * frac1)
    if bar_end > SBAR_X:
        draw.rounded_rectangle([SBAR_X, SBAR_Y, bar_end, SBAR_Y + SBAR_H],
                                radius=9, fill=BAR_LEFT)

    # Winner / Draw label
    if score1 != score2:
        winner = sym1 if score1 > score2 else sym2
        banner = f"⭐  SIEGER: {winner}"
    else:
        banner = "UNENTSCHIEDEN"
    bw = int(draw.textlength(banner, font=f_score))
    banner_col = WIN_COL if score1 != score2 else MUTED
    draw.text((MID - bw // 2, score_y + 102), banner, fill=banner_col, font=f_score)

    # Footer attribution — subtle, inside panel
    foot = f"STAND: {datetime.today().strftime('%d.%m.%Y')}  •  DATENQUELLE: YAHOO FINANCE  •  v{__version__}"
    if watermark:
        foot = watermark.upper() + "  •  " + foot
    tw_f = int(draw.textlength(foot, font=f_foot))
    draw.text(((W - tw_f) // 2, score_y + 72), foot, fill=(110, 125, 150), font=f_foot)

    _draw_watermark(draw, W, H)
    return img

def render_blog_header(selected_stocks: List[Dict[str, Any]], title_text: str = "AKTIEN-ANALYSE: TOP 3 DIVIDENDEN-STOCKS", bg_img: Image.Image = None) -> Image.Image:
    """
    Renders a landscape (1200x630) header image for blog posts with 3 stocks.
    If bg_img is provided (e.g. from DALL-E 3), it composites the corporate logos and text using glassmorphism.
    """
    W, H = 1200, 630
    
    if bg_img:
        # Resize/Crop the DALL-E image to exactly 1200x630 using LANCZOS
        from PIL import ImageOps
        img = ImageOps.fit(bg_img, (W, H), method=Image.Resampling.LANCZOS).convert("RGBA")
        
        # Create a darkening overlay so white text reads well
        overlay = Image.new("RGBA", (W, H), (15, 23, 42, 100)) # Dark transparent layer
        img = Image.alpha_composite(img, overlay)
    else:
        img = Image.new("RGBA", (W, H), COLOR_DARK_BG)
        # Gradient/Pattern BG
        draw_temp = ImageDraw.Draw(img)
        for i in range(H):
            alpha = int(20 + 30 * (i / H))
            draw_temp.line([(0, i), (W, i)], fill=(255, 255, 255, alpha))

    draw = ImageDraw.Draw(img)
    MID = W // 2
    PAD = 40

    # Fonts
    f_title = _font(FONT_BLD_PATH, 42, ImageFont.load_default())
    f_ticker = _font(FONT_BLD_PATH, 36, ImageFont.load_default())
    f_name = _font(FONT_REG_PATH, 24, ImageFont.load_default())
    f_meta = _font(FONT_REG_PATH, 18, ImageFont.load_default())

    # Header Title
    tw = int(draw.textlength(title_text, font=f_title))
    draw.text((MID - tw // 2, 60), title_text, fill=COLOR_ACCENT, font=f_title)

    # 3 Columns for stocks
    COL_W = (W - 4 * PAD) // 3
    for i, stock in enumerate(selected_stocks):
        symbol = str(stock.get('Symbol', 'N/A'))
        name = get_clean_name(stock)[:25]
        
        cx = PAD + i * (COL_W + PAD) + COL_W // 2
        cy_base = 180
        
        # Draw panel only if NOT using a background image
        if not bg_img:
            px1, py1 = PAD + i * (COL_W + PAD), 150
            px2, py2 = px1 + COL_W, H - 100
            draw.rounded_rectangle([px1, py1, px2, py2], radius=15, fill=(255, 255, 255, 10), outline=(255, 255, 255, 40), width=2)
        else:
            # Elegant circular backdrop behind logo for contrast/readability
            logo_r = 55
            draw.ellipse([cx - logo_r, cy_base + 25, cx + logo_r, cy_base + 135], fill=(255, 255, 255, 220), outline=(255, 255, 255, 80), width=2)
            
        # Logo
        logo_path = os.path.join(LOGO_DIR, f"{symbol}.png")
        logo_loaded = False
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo.thumbnail((90, 90))
                lx = cx - logo.width // 2
                ly = cy_base + 80 - logo.height // 2
                img.paste(logo, (lx, ly), logo)
                logo_loaded = True
            except: pass
            
        if not logo_loaded and bg_img:
            # Draw fallback text inside the circle if logo is missing and we drew a circle
            first_letter = symbol[0]
            f_letter = _font(FONT_BLD_PATH, 48, ImageFont.load_default())
            tw_l = int(draw.textlength(first_letter, font=f_letter))
            draw.text((cx - tw_l // 2, cy_base + 80 - 28), first_letter, fill=(30, 41, 59), font=f_letter)
            
        # Ticker & Name
        ty = cy_base + 170
        tw_t = int(draw.textlength(symbol, font=f_ticker))
        draw.text((cx - tw_t // 2, ty), symbol, fill=(255, 255, 255), font=f_ticker)
        
        ny = ty + 50
        tw_n = int(draw.textlength(name, font=f_name))
        draw.text((cx - tw_n // 2, ny), name, fill=COLOR_MUTED, font=f_name)

    # Footer
    footer = f"SCHATZSUCHE 4.0  •  MARKT-UPDATE  •  {datetime.today().strftime('%d.%m.%Y')}"
    tw_f = int(draw.textlength(footer, font=f_meta))
    draw.text((MID - tw_f // 2, H - 50), footer, fill=(150, 160, 180), font=f_meta)

    _draw_watermark(draw, W, H)
    return img

def render_social_square_header(selected_stocks: List[Dict[str, Any]], title_text: str = "AKTIEN-DUELL & ANALYSE", bg_img: Image.Image = None) -> Image.Image:
    """
    Renders a square (1080x1080) header image optimized for Instagram and Facebook.
    Ideal for sharing the "Top 3" or similar highlights.
    """
    W, H = 1080, 1080
    
    if bg_img:
        from PIL import ImageOps
        img = ImageOps.fit(bg_img, (W, H), method=Image.Resampling.LANCZOS).convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (15, 23, 42, 140)) # Slightly darker for square
        img = Image.alpha_composite(img, overlay)
    else:
        img = Image.new("RGBA", (W, H), (10, 18, 35, 255))
        draw_temp = ImageDraw.Draw(img)
        for i in range(H):
            alpha = int(30 + 40 * (i / H))
            draw_temp.line([(0, i), (W, i)], fill=(255, 255, 255, alpha))

    draw = ImageDraw.Draw(img)
    MID = W // 2
    PAD = 60

    # Fonts
    f_title = _font(FONT_BLD_PATH, 54, ImageFont.load_default())
    f_ticker = _font(FONT_BLD_PATH, 42, ImageFont.load_default())
    f_name = _font(FONT_REG_PATH, 32, ImageFont.load_default())
    f_meta = _font(FONT_REG_PATH, 24, ImageFont.load_default())

    # Header Title
    tw = int(draw.textlength(title_text.upper(), font=f_title))
    draw.text((MID - tw // 2, 100), title_text.upper(), fill=(16, 185, 129), font=f_title)

    # 3 Stocks in vertical or grid? Let's do a vertical stack for square
    BOX_H = 220
    START_Y = 220
    GAP = 40
    
    for i, stock in enumerate(selected_stocks[:3]):
        symbol = str(stock.get('Symbol', 'N/A'))
        name = get_clean_name(stock)[:30]
        
        y1 = START_Y + i * (BOX_H + GAP)
        y2 = y1 + BOX_H
        
        # Logo loading first so we can center it
        logo_path = os.path.join(LOGO_DIR, f"{symbol}.png")
        logo = None
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
            except: pass

        # Glass panel & Logo background
        logo_loaded = False
        if not bg_img:
            draw.rounded_rectangle([PAD, y1, W - PAD, y2], radius=20, fill=(255, 255, 255, 15), outline=(255, 255, 255, 50), width=3)
            if logo:
                logo.thumbnail((120, 120))
                lx = PAD + 40
                ly = y1 + (BOX_H - logo.height) // 2
                img.paste(logo, (lx, ly), logo)
                logo_loaded = True
        else:
            # Elegant circular backdrop for logo
            logo_r = 50
            cx_logo = PAD + 90
            cy_logo = y1 + BOX_H // 2
            draw.ellipse([cx_logo - logo_r, cy_logo - logo_r, cx_logo + logo_r, cy_logo + logo_r], fill=(255, 255, 255, 220), outline=(255, 255, 255, 80), width=2)
            if logo:
                logo.thumbnail((80, 80))
                lx = cx_logo - logo.width // 2
                ly = cy_logo - logo.height // 2
                img.paste(logo, (lx, ly), logo)
                logo_loaded = True
            else:
                # Fallback text in circle
                first_letter = symbol[0]
                f_letter = _font(FONT_BLD_PATH, 42, ImageFont.load_default())
                tw_l = int(draw.textlength(first_letter, font=f_letter))
                draw.text((cx_logo - tw_l // 2, cy_logo - 24), first_letter, fill=(30, 41, 59), font=f_letter)
            
        # Text
        tx = PAD + 200
        draw.text((tx, y1 + 55), symbol, fill=(255, 255, 255), font=f_ticker)
        draw.text((tx, y1 + 115), name, fill=(180, 195, 220), font=f_name)
        
        # Arrow or chevron
        draw.text((W - PAD - 80, y1 + 75), "→", fill=(16, 185, 129), font=f_ticker)

    # Footer
    footer = f"JETZT ONLINE: SCHATZSUCHE40.DE  •  {datetime.today().strftime('%d.%m.%Y')}"
    tw_f = int(draw.textlength(footer, font=f_meta))
    draw.text((MID - tw_f // 2, H - 80), footer, fill=(150, 160, 180), font=f_meta)

    _draw_watermark(draw, W, H)
    return img

