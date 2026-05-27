import os
from PIL import Image, ImageDraw, ImageFont

def generate_brand_logo(output_path="context/logos/logo.png"):
    width, height = 600, 150
    # Create an image with alpha channel for transparency
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Color palette
    gold = (201, 162, 39, 255)       # #C9A227
    gold_light = (255, 215, 0, 255)  # Gold
    white = (247, 247, 247, 255)     # Off-White
    teal = (26, 83, 92, 255)         # #1A535C

    # Try to load a nice Windows font, fallback to standard
    font_bold = None
    font_regular = None
    
    font_paths_bold = [
        "C:\\Windows\\Fonts\\Outfit-Bold.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "arial.ttf"
    ]
    font_paths_reg = [
        "C:\\Windows\\Fonts\\Outfit-Regular.ttf",
        "C:\\Windows\\Fonts\\segoeuil.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "arial.ttf"
    ]

    for p in font_paths_bold:
        if os.path.exists(p):
            try:
                font_bold = ImageFont.truetype(p, 42)
                break
            except:
                pass
    
    for p in font_paths_reg:
        if os.path.exists(p):
            try:
                font_regular = ImageFont.truetype(p, 28)
                break
            except:
                pass

    if not font_bold:
        font_bold = ImageFont.load_default()
    if not font_regular:
        font_regular = ImageFont.load_default()

    # --- Draw Compass/Treasure Emblem on the left ---
    # Center of emblem: x=75, y=75, radius=45
    cx, cy, r = 75, 75, 45
    
    # Draw outer gold ring with thickness
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=gold, width=4)
    draw.ellipse([cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6], outline=gold, width=1)
    
    # Draw cardinal direction ticks (N, S, E, W)
    tick_len = 8
    draw.line([cx, cy - r, cx, cy - r + tick_len], fill=gold_light, width=2) # N
    draw.line([cx, cy + r, cx, cy + r - tick_len], fill=gold_light, width=2) # S
    draw.line([cx - r, cy, cx - r + tick_len, cy], fill=gold_light, width=2) # W
    draw.line([cx + r, cy, cx + r - tick_len, cy], fill=gold_light, width=2) # E

    # Draw compass needle star (4 points)
    # North point: (cx, cy-r+10), South: (cx, cy+r-10), West: (cx-r+10, cy), East: (cx+r-10, cy)
    # Draw beautiful diamond star shapes
    # Vertical needle
    draw.polygon([cx, cy - 35, cx - 8, cy, cx + 8, cy], fill=gold)
    draw.polygon([cx, cy + 35, cx - 8, cy, cx + 8, cy], fill=gold_light)
    # Horizontal needle
    draw.polygon([cx - 35, cy, cx, cy - 8, cx, cy + 8], fill=gold)
    draw.polygon([cx + 35, cy, cx, cy - 8, cx, cy + 8], fill=gold_light)
    
    # Center dot
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=white)

    # --- Draw brand text "SCHATZSUCHE" & "4.0" ---
    # Draw "SCHATZSUCHE"
    draw.text((150, 40), "SCHATZSUCHE", font=font_bold, fill=white)
    
    # Draw "4.0" (larger, gold highlight)
    try:
        font_large_gold = ImageFont.truetype(font_paths_bold[1], 48) if font_bold else ImageFont.load_default()
    except:
        font_large_gold = font_bold
        
    draw.text((455, 33), "4.0", font=font_large_gold, fill=gold_light)

    # Draw subtitle "CLEVERES INVESTIEREN"
    draw.text((150, 90), "CLEVER INVESTIEREN", font=font_regular, fill=gold)

    # Save image
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Branded logo generated successfully at {output_path}")

if __name__ == "__main__":
    generate_brand_logo()
