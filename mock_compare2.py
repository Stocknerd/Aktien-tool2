import core, pandas as pd
from PIL import Image, ImageDraw

def _color(hex_str, a=255):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)

W, H = 1080, 1350
img = Image.new("RGBA", (W, H), (15, 23, 42, 255))
draw = ImageDraw.Draw(img)

PAD = 64
MID = W // 2
f_lbl = core._font(core.FONT_REG_PATH, 24, None)
f_val = core._font(core.FONT_BLD_PATH, 34, None)
f_an_val = core._font(core.FONT_BLD_PATH, 24, None)
f_an_lbl = core._font(core.FONT_REG_PATH, 22, None)
MUTED = (180, 195, 220)
WIN_COL = (52, 211, 153)
BAR_LEFT = (16, 185, 129, 210)
BAR_RIGHT = (96, 165, 250, 210)

ROW_START = 240
ROW_H = 66
ROW_GAP = 12

for i, m in enumerate(["KGV (AKTUELL)", "KGV (ERWARTET)", "KUV", "KBV", "OP. MARGE (%)", "EK-RENDITE (%)", "DIVIDENDE (%)", "UMSATZ-WACHSTUM (3J EXP)"]):
    row_y = ROW_START + i * (ROW_H + ROW_GAP)
    
    # Card
    draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, fill=(8, 14, 35, 200))
    draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, outline=(255, 255, 255, 20), width=2)
    
    # Label
    tw_l = draw.textlength(m, font=f_lbl)
    draw.text((MID - tw_l / 2, row_y + 18), m, fill=MUTED, font=f_lbl)
    
    # Value 1 (Left)
    v1 = "33.23"
    draw.text((PAD + 24, row_y + 14), v1, fill=WIN_COL, font=f_val)
    
    # Value 2 (Right)
    v2 = "25.39"
    tw2 = draw.textlength(v2, font=f_val)
    draw.text((W - PAD - 24 - tw2, row_y + 14), v2, fill=WIN_COL, font=f_val)
    
    # Bars
    BAR_MAX = int((W - 2 * PAD - tw_l - 80)/2)
    b_y = row_y + ROW_H - 12
    draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + BAR_MAX, b_y + 4], radius=2, fill=(255,255,255,20))
    draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + int(BAR_MAX * 0.4), b_y + 4], radius=2, fill=BAR_LEFT)
    
    draw.rounded_rectangle([W - PAD - 24 - BAR_MAX, b_y, W - PAD - 24, b_y + 4], radius=2, fill=(255,255,255,20))
    draw.rounded_rectangle([W - PAD - 24 - int(BAR_MAX * 0.7), b_y, W - PAD - 24, b_y + 4], radius=2, fill=BAR_RIGHT)

# Analyst panel
an_y = ROW_START + 8 * (ROW_H + ROW_GAP) + 10
AN_H = 100
draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, fill=(255, 255, 255, 12))
draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, outline=(255, 255, 255, 40), width=2)

draw.text((MID - draw.textlength("ANALYSTENRATING", font=f_lbl)/2, an_y + 12), "ANALYSTENRATING", fill=MUTED, font=f_lbl)

# left side:
draw.text((PAD + 24, an_y + 50), "🟢 KAUFEN", fill=(16, 185, 129), font=f_an_val)
draw.text((PAD + 180, an_y + 52), "Ziel: +13.7% (41 Analysten)", fill=MUTED, font=f_an_lbl)

# right side:
tw = draw.textlength("Ziel: +45.2% (53 Analysten)", font=f_an_lbl)
draw.text((W - PAD - 24 - tw, an_y + 52), "Ziel: +45.2% (53 Analysten)", fill=MUTED, font=f_an_lbl)
tw = draw.textlength("🟢 KAUFEN", font=f_an_val) + tw + 20
draw.text((W - PAD - 24 - tw, an_y + 50), "🟢 KAUFEN", fill=(16, 185, 129), font=f_an_val)

# Score Panel
score_y = an_y + AN_H + 20
PANEL_H = 130
draw.rounded_rectangle([PAD, score_y, W - PAD, score_y + PANEL_H], radius=18, fill=(8, 14, 35, 200))

# save
img.convert('RGB').save('static/generated/mock_compare2.png')
print("Done")
