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
f_an_val = core._font(core.FONT_BLD_PATH, 22, None)
f_an_lbl = core._font(core.FONT_REG_PATH, 22, None)
f_an_bld = core._font(core.FONT_BLD_PATH, 22, None)
MUTED = (180, 195, 220)
WHITE = (255, 255, 255)

an_y = 200
AN_H = 100
draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, fill=(8, 14, 35, 200))
draw.rounded_rectangle([PAD, an_y, W - PAD, an_y + AN_H], radius=16, outline=(255, 255, 255, 40), width=2)
draw.text((MID - draw.textlength("ANALYSTENRATING", font=f_lbl)//2, an_y + 12), "ANALYSTENRATING", fill=MUTED, font=f_lbl)

def draw_analyst_side(is_left, rec_ger, pot, n_a):
    if rec_ger in ["STARKER KAUF", "KAUFEN"]:
        bg_col = (16, 185, 129)  # Green
    elif rec_ger in ["VERKAUFEN", "STARKER VERKAUF"]:
        bg_col = (239, 68, 68)   # Red
    else:
        bg_col = (156, 163, 175) # Gray
        
    tw_rec = draw.textlength(rec_ger, font=f_an_val)
    badge_w = tw_rec + 24
    badge_h = 32
    
    txt_ziel = f"Ziel: "
    txt_pot = f"{'+' if pot > 0 else ''}{pot:.1f}%"
    txt_tail = f" ({n_a} Analysten)"
    
    tw_ziel = draw.textlength(txt_ziel, font=f_an_lbl)
    tw_pot = draw.textlength(txt_pot, font=f_an_bld)
    tw_tail = draw.textlength(txt_tail, font=f_an_lbl)
    
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

draw_analyst_side(True, "STARKER KAUF", 13.7, 41)
draw_analyst_side(False, "HALTEN", -5.2, 53)

img.convert('RGB').save('static/generated/mock_an_badge.png')
print("Done")
