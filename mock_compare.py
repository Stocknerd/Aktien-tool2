import core, pandas as pd
from PIL import Image, ImageDraw

W, H = 1080, 1350
img = Image.new("RGBA", (W, H), (15, 23, 42, 255))
draw = ImageDraw.Draw(img)

PAD = 64
MID = W // 2
f_lbl = core._font(core.FONT_REG_PATH, 24, None)
f_val = core._font(core.FONT_BLD_PATH, 34, None)
MUTED = (180, 195, 220)
WIN_COL = (52, 211, 153)
BAR_LEFT = (16, 185, 129, 210)
BAR_RIGHT = (96, 165, 250, 210)

ROW_START = 280
ROW_H = 76
ROW_GAP = 12

for i, m in enumerate(["KGV (AKTUELL)", "UMSATZ-WACHSTUM (3J EXP)", "OP. MARGE (%)"]):
    row_y = ROW_START + i * (ROW_H + ROW_GAP)
    
    # Card
    draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, fill=(8, 14, 35, 200))
    draw.rounded_rectangle([PAD, row_y, W - PAD, row_y + ROW_H], radius=12, outline=(255, 255, 255, 20), width=2)
    
    # Label
    tw_l = draw.textlength(m, font=f_lbl)
    draw.text((MID - tw_l / 2, row_y + 12), m, fill=MUTED, font=f_lbl)
    
    # Value 1 (Left)
    v1 = "33.23"
    draw.text((PAD + 24, row_y + 14), v1, fill=WIN_COL, font=f_val)
    
    # Value 2 (Right)
    v2 = "25.39"
    tw2 = draw.textlength(v2, font=f_val)
    draw.text((W - PAD - 24 - tw2, row_y + 14), v2, fill=WIN_COL, font=f_val)
    
    # Bars
    BAR_MAX = 220
    b_y = row_y + ROW_H - 16
    draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + BAR_MAX, b_y + 6], radius=3, fill=(255,255,255,20))
    draw.rounded_rectangle([PAD + 24, b_y, PAD + 24 + int(BAR_MAX * 0.4), b_y + 6], radius=3, fill=BAR_LEFT)
    
    draw.rounded_rectangle([W - PAD - 24 - BAR_MAX, b_y, W - PAD - 24, b_y + 6], radius=3, fill=(255,255,255,20))
    draw.rounded_rectangle([W - PAD - 24 - int(BAR_MAX * 0.7), b_y, W - PAD - 24, b_y + 6], radius=3, fill=BAR_RIGHT)

img.convert('RGB').save('static/generated/mock_compare.png')
print("Done")
