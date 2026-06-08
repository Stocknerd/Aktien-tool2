import os
import requests
import io
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops
from src.config import COLORS, FONT_PATHS, LOGO_PATH, DISCLAIMERS, BRAND_PROFILE, BASE_DIR
from src.content_generator import client

def get_font(font_name, size):
    """Loads cached font or falls back to system fonts."""
    path = FONT_PATHS.get(font_name, "arial.ttf")
    try:
        return ImageFont.truetype(path, size)
    except Exception as e:
        print(f"FONT: Could not load {font_name} from {path}, falling back: {e}")
        return ImageFont.load_default()

def draw_rounded_rect_with_border(draw, coords, radius, fill, outline, width=2):
    """Draws a rounded rectangle with a clean outline of a specific width."""
    draw.rounded_rectangle(coords, radius=radius, fill=fill)
    draw.rounded_rectangle(coords, radius=radius, outline=outline, width=width)

def generate_dalle_image(prompt, aspect_ratio="1:1"):
    """
    Generates an image from OpenAI and returns a PIL Image object.
    Supports gpt-image-1 proxy or dall-e-3 fallback.
    """
    model_name = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    size = "1024x1024" if aspect_ratio == "1:1" else "1024x1792"
    
    print(f"IMAGE: Generating visual via {model_name}...")
    try:
        response = client.images.generate(
            model=model_name,
            prompt=prompt,
            size=size,
            quality="auto",
            n=1
        )
        data = response.data[0]
        if hasattr(data, 'url') and data.url:
            r = requests.get(data.url, timeout=20)
            r.raise_for_status()
            return Image.open(io.BytesIO(r.content))
        elif hasattr(data, 'b64_json') and data.b64_json:
            import base64
            img_data = base64.b64decode(data.b64_json)
            return Image.open(io.BytesIO(img_data))
    except Exception as e:
        print(f"WARNING: Image generation failed with {model_name}: {e}.")
            
    # Always return a beautiful brand fallback image if the API route fails
    print("IMAGE: API generation failed completely. Creating beautiful brand vector fallback image...")
    fallback_img = Image.new("RGB", (800, 800), COLORS["card_bg"])
    f_draw = ImageDraw.Draw(fallback_img)
    # Draw simple elegant geometric pattern in brand gold
    f_draw.rectangle([20, 20, 780, 780], outline=COLORS["primary"], width=2)
    f_draw.regular_polygon((400, 360, 100), 3, rotation=90, fill=COLORS["primary"])
    font_hl = get_font("Outfit-Bold.ttf", 36)
    f_draw.text((400, 520), "SCHATZSUCHE 4.0", fill=COLORS["text"], font=font_hl, anchor="mm")
    font_sub = get_font("Inter-Regular.ttf", 24)
    f_draw.text((400, 580), "Clever investieren, langfristig wachsen.", fill=COLORS["text_secondary"], font=font_sub, anchor="mm")
    return fallback_img

def render_base_layout(content, bg_image_path=None):
    """Renders the common background (color or image), double golden borders, logo, and titles."""
    # 9:16 Canvas (1080 x 1920)
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            bg_img = Image.open(bg_image_path)
            # Crop image to 9:16 aspect ratio from the center
            bw, bh = bg_img.size
            target_ratio = 1080 / 1920
            current_ratio = bw / bh
            if current_ratio > target_ratio:
                new_w = int(bh * target_ratio)
                left = (bw - new_w) // 2
                bg_img = bg_img.crop((left, 0, left + new_w, bh))
            else:
                new_h = int(bw / target_ratio)
                top = (bh - new_h) // 2
                bg_img = bg_img.crop((0, top, bw, top + new_h))
            bg_img = bg_img.resize((1080, 1920), Image.Resampling.LANCZOS)
            
            # Semi-transparent dark petrol overlay for premium look & text readability
            overlay = Image.new("RGBA", (1080, 1920), (11, 30, 33, 210))
            img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
        except Exception as e:
            print(f"WARNING: Base layout background image error: {e}")
            img = Image.new("RGB", (1080, 1920), COLORS["background"])
    else:
        img = Image.new("RGB", (1080, 1920), COLORS["background"])
        
    draw = ImageDraw.Draw(img)

    # --- Double Golden Borders ---
    margin1 = 25
    margin2 = 35
    draw.rectangle([margin1, margin1, 1080 - margin1, 1920 - margin1], outline=COLORS["primary"], width=2)
    draw.rectangle([margin2, margin2, 1080 - margin2, 1920 - margin2], outline=COLORS["primary"], width=1)

    # --- Header Brand Logo ---
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH)
            # Resize proportionally to fit top area (width 400px)
            aspect = logo.height / logo.width
            logo_w = 400
            logo_h = int(logo_w * aspect)
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            # Paste onto canvas
            img.paste(logo, (int((1080 - logo_w) / 2), 80), logo if logo.mode == "RGBA" else None)
        except Exception as e:
            print(f"WARNING: Logo pasting failed: {e}")
    else:
        # Text logo fallback
        font_logo = get_font("Outfit-Bold.ttf", 40)
        draw.text((540, 100), "SCHATZSUCHE 4.0", fill=COLORS["primary"], font=font_logo, anchor="mm")

    # --- Headline ---
    font_hl = get_font("Outfit-Bold.ttf", 52)
    headline_text = content.get("headline", "Finanztipp").upper()
    # Wrap text
    hl_lines = textwrap.wrap(headline_text, width=22)
    hl_y = 230
    for line in hl_lines:
        draw.text((540, hl_y), line, fill=COLORS["text"], font=font_hl, anchor="mm")
        hl_y += 65

    # --- Subheadline ---
    font_sub = get_font("Inter-Regular.ttf", 28)
    subheadline_text = content.get("subheadline", "")
    sub_lines = textwrap.wrap(subheadline_text, width=42)
    sub_y = hl_y + 10
    for line in sub_lines:
        draw.text((540, sub_y), line, fill=COLORS["text_secondary"], font=font_sub, anchor="mm")
        sub_y += 38

    # --- Footer Brand & Disclaimer ---
    font_footer = get_font("Inter-Bold.ttf", 24)
    # Draw website URL and social tag
    footer_text = f"{BRAND_PROFILE.get('website', 'schatzsuche40.de')}  |  @schatzsuche40"
    draw.text((540, 1800), footer_text, fill=COLORS["primary"], font=font_footer, anchor="mm")

    # Draw Disclaimer
    font_disc = get_font("Inter-Regular.ttf", 18)
    disclaimer_text = DISCLAIMERS.get("short_disclaimer", "")
    disc_lines = textwrap.wrap(disclaimer_text, width=95)
    disc_y = 1845
    for line in disc_lines:
        draw.text((540, disc_y), line, fill=COLORS["text_secondary"], font=font_disc, anchor="mm")
        disc_y += 24

    return img, draw, sub_y

def render_finance_evergreen(content, output_path):
    """Renders Evergreen Card-Layout template."""
    img, draw, top_y = render_base_layout(content)
    
    # Calculate starting position for cards (centered in remaining space)
    # Remaining space between sub_y and footer (approx 1750)
    card_y = max(550, top_y + 40)
    card_h = 240
    card_spacing = 50
    card_w = 920
    card_x = 80
    
    font_num = get_font("Outfit-Bold.ttf", 46)
    font_card = get_font("Inter-Regular.ttf", 30)
    
    points = content.get("card_points", ["Fakt 1", "Fakt 2", "Fakt 3"])
    
    for i, pt in enumerate(points[:3]):
        box_coords = [card_x, card_y, card_x + card_w, card_y + card_h]
        # Rounded container
        draw_rounded_rect_with_border(draw, box_coords, radius=24, fill=COLORS["card_bg"], outline=COLORS["primary"], width=2)
        
        # Circle badge for number
        cx, cy, cr = card_x + 70, card_y + 120, 36
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=COLORS["primary"])
        draw.text((cx, cy), str(i+1), fill=COLORS["background"], font=font_num, anchor="mm")
        
        # Wrapped text block
        text_lines = textwrap.wrap(pt, width=42)
        ty = card_y + 120 - (len(text_lines) * 18)  # Centered text vertically
        for line in text_lines:
            draw.text((card_x + 140, ty), line, fill=COLORS["text"], font=font_card, anchor="lm")
            ty += 38
            
        card_y += card_h + card_spacing

    img.save(output_path, "PNG")
    print(f"GRAPHIC: Saved Evergreen Infographic to {output_path}")
    return img

def render_portfolio_highlight(content, output_path, visual_mode="chart"):
    """
    Renders Portfolio Highlight template.
    Two visual modes:
    - 'chart': Draws a beautiful custom vector asset-allocation ring chart with legends.
    - 'image': Embeds a concept DALL-E generated illustration inside a gold frame.
    """
    img, draw, top_y = render_base_layout(content)
    
    # Calculate starting position
    content_y = max(520, top_y + 30)
    
    if visual_mode == "chart":
        # Draw dynamic investment asset allocation ring chart
        # Ring chart center: (540, content_y + 260)
        cx, cy = 540, content_y + 240
        r_out, r_in = 200, 120
        
        # Data slices (70% ETFs, 20% Real Estate, 10% P2P/Crowd)
        slices = [
            {"label": "70% ETFs", "angle": 252, "color": COLORS["primary"]},
            {"label": "20% Immobilien", "angle": 72, "color": COLORS["accent"]},
            {"label": "10% Crowdinvesting", "angle": 36, "color": COLORS["highlight"]}
        ]
        
        # Draws slices
        start_angle = -90
        for s in slices:
            end_angle = start_angle + s["angle"]
            draw.pieslice([cx - r_out, cy - r_out, cx + r_out, cy + r_out], start_angle, end_angle, fill=s["color"])
            start_angle = end_angle
            
        # Draw inner cutout circle to make it a ring/doughnut chart
        draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=COLORS["background"])
        
        # Draw text inside doughnut
        font_ring = get_font("Outfit-Bold.ttf", 26)
        draw.text((cx, cy - 18), "PORTFOLIO", fill=COLORS["text_secondary"], font=font_ring, anchor="mm")
        draw.text((cx, cy + 18), "ALLOKATION", fill=COLORS["primary"], font=font_ring, anchor="mm")
        
        # Draw legends underneath the chart
        legend_y = cy + 240
        font_legend = get_font("Inter-Bold.ttf", 26)
        
        # Legend items spaced horizontally
        legend_items = [
            {"text": "ETFs (70%)", "color": COLORS["primary"], "x": 180},
            {"text": "Real Estate (20%)", "color": COLORS["accent"], "x": 480},
            {"text": "Crowd (10%)", "color": COLORS["highlight"], "x": 860}
        ]
        
        for item in legend_items:
            # Draw color box
            box_sz = 20
            draw.rectangle([item["x"] - 60, legend_y - 10, item["x"] - 60 + box_sz, legend_y - 10 + box_sz], fill=item["color"])
            draw.text((item["x"] - 30, legend_y), item["text"], fill=COLORS["text"], font=font_legend, anchor="lm")
            
        # Add 2 structured content text cards below the chart
        card_y = legend_y + 80
        card_w, card_h = 920, 160
        card_x = 80
        font_card = get_font("Inter-Regular.ttf", 28)
        
        points = content.get("card_points", ["Fokus auf Cashflow", "Langfristiges ETF-Wachstum"])
        for i, pt in enumerate(points[:2]):
            box_coords = [card_x, card_y, card_x + card_w, card_y + card_h]
            draw_rounded_rect_with_border(draw, box_coords, radius=18, fill=COLORS["card_bg"], outline=COLORS["primary"], width=2)
            
            # Draw point bullet/icon
            bx, by = card_x + 50, card_y + 80
            draw.regular_polygon((bx, by, 16), 3, rotation=90, fill=COLORS["primary"])
            
            # Text block
            text_lines = textwrap.wrap(pt, width=46)
            ty = card_y + 80 - (len(text_lines) * 18)
            for line in text_lines:
                draw.text((card_x + 100, ty), line, fill=COLORS["text"], font=font_card, anchor="lm")
                ty += 36
            card_y += card_h + 30
            
    elif visual_mode == "image":
        # DALL-E generated Concept Illustration embedded in a golden frame
        frame_w, frame_h = 800, 700
        frame_x = 140
        frame_y = content_y + 30
        
        # Call DALL-E to generate illustration
        prompt = content.get("dalle_prompt", "High contrast concept art of wealth in deep teal and gold.")
        illust = generate_dalle_image(prompt, aspect_ratio="1:1")
        
        # Frame background/border
        draw_rounded_rect_with_border(draw, [frame_x - 10, frame_y - 10, frame_x + frame_w + 10, frame_y + frame_h + 10], radius=24, fill=COLORS["card_bg"], outline=COLORS["primary"], width=4)
        
        # Resize illustration to fit frame nicely
        illust = illust.resize((frame_w, frame_h), Image.Resampling.LANCZOS)
        img.paste(illust, (frame_x, frame_y))
        
        # Add 1 long, clean text card at the bottom explaining the highlight
        card_y = frame_y + frame_h + 50
        card_w, card_h = 920, 240
        card_x = 80
        font_card = get_font("Inter-Regular.ttf", 30)
        
        points = content.get("card_points", ["Investiere diversifiziert in ETFs und Sachwerte"])
        full_text = "  |  ".join(points[:2]) if len(points) > 1 else points[0]
        box_coords = [card_x, card_y, card_x + card_w, card_y + card_h]
        draw_rounded_rect_with_border(draw, box_coords, radius=24, fill=COLORS["card_bg"], outline=COLORS["primary"], width=2)
        
        text_lines = textwrap.wrap(full_text, width=45)
        ty = card_y + 120 - (len(text_lines) * 20)
        for line in text_lines:
            draw.text((540, ty), line, fill=COLORS["text"], font=font_card, anchor="mm")
            ty += 40

    img.save(output_path, "PNG")
    print(f"GRAPHIC: Saved Portfolio Infographic to {output_path}")
    return img

def render_pure_ai_infographic(content, output_path):
    """
    Generates a complete 9:16 vertical infographic image purely using SOTA gpt-image-2.
    It embeds all copywriting, text layouts, and brand identity elements directly into the prompt.
    """
    headline = content.get("headline", "").upper()
    subheadline = content.get("subheadline", "")
    points = content.get("card_points", [])
    
    pts_prompt = ""
    for i, pt in enumerate(points[:3]):
        pts_prompt += f"\n- Point {i+1}: \"{pt}\""
        
    prompt = f"""
    Create an ultra-premium, modern 9:16 vertical infographic Instagram card designed specifically for the brand "SCHATZSUCHE 4.0".
    
    Visual Identity & Branding:
    - Vibe: Premium digital finance dashboard meets ancient explorer's navigation map. High-end, clean, professional, and visually stunning.
    - Background: Deep dark petrol blue (#0B1E21) slate surface with a very subtle overlay of glowing gold navigator coordinate grid lines (longitudes and latitudes).
    - Top Emblem: Near the top center, display a beautiful golden circular compass emblem (cardinal direction ticks N, S, E, W, with a 4-point gold star needle inside).
    - Main Card Layout: In the middle, there is a large, elegant, vertical semi-transparent dark petrol glassmorphic card with a thin, glowing warm gold (#C9A227) border and soft drop shadows. All texts are written inside this card for maximum readability and visual excellence.
    - Accent: Warm glowing gold (#C9A227) and off-white (#F7F7F7) are used as high-contrast colors.
    
    Layout & Text Elements (Must be written perfectly in clean, geometric sans-serif fonts like Outfit and Inter):
    1. Top Header: Inside the glassmorphic card at the top, write "SCHATZSUCHE 4.0" in neat, clean gold letters.
    2. Main Title: Write the headline "{headline}" in large, bold, premium off-white letters.
    3. Subtitle: Below the title, write: "{subheadline}" in a smaller warm gold font.
    4. Info Points: Below the subtitle, present three clean, left-aligned bullet points. Each point must start with a small, stylized gold compass icon:
       {pts_prompt}
    5. Footer: At the very bottom, below the glassmorphic card, in elegant small gold letters, write the website and Instagram handle:
       "schatzsuche40.de | @schatzsuche40"
       and the legal disclaimer below it:
       "Keine Anlageberatung. Historische Renditen sind keine Garantie für die Zukunft."
    
    Style constraints:
    - Extremely clean grid alignment. Perfectly balanced white space.
    - No chaotic or cartoonish drawings, no messy overlays.
    - High-end corporate and luxury brand aesthetic, custom-made for an elite Instagram finance page.
    """
    
    print(f"IMAGE: Rendering complete vertical infographic using SOTA gpt-image-2...")
    img = generate_dalle_image(prompt, aspect_ratio="9:16")
    img.save(output_path, "PNG")
    print(f"IMAGE: Saved pure AI infographic to {output_path}")
    return img

def render_viral_list(content, output_path, bg_image_path=None):
    """
    Renders Track 3 (AI Infographic) in the premium "Elterngeld"-style:
    - 9:16 vertical canvas (1080x1920)
    - Coordinate-grid background, double golden borders
    - Brand Logo and knackige H1/Sub headline
    - Central Gold-bordered Highlight Box with massive gold value and label
    - Exactly 5 structured fact rows with round gold badges (numbers 1-5 inside)
      and wrapped Title & Description text
    - Sand-colored warning disclaimer at the bottom
    """
    img, draw, top_y = render_base_layout(content, bg_image_path=bg_image_path)
    
    # 1. Centered Highlight Box (Gold Border, Dark Petrol Fill)
    box_x = 80
    box_y = top_y + 30
    box_w = 920
    box_h = 200
    box_coords = [box_x, box_y, box_x + box_w, box_y + box_h]
    
    draw_rounded_rect_with_border(
        draw, box_coords, radius=24, 
        fill=COLORS["card_bg"], outline=COLORS["primary"], width=2
    )
    
    # Draw massive gold value
    val_text = content.get("highlight_value", "").upper()
    font_val = get_font("Outfit-Bold.ttf", 75)
    draw.text((540, box_y + 35), val_text, fill=COLORS["primary"], font=font_val, anchor="mt")
    
    # Draw highlight label
    lbl_text = content.get("highlight_label", "").upper()
    font_lbl = get_font("Inter-Bold.ttf", 24)
    draw.text((540, box_y + 125), lbl_text, fill=COLORS["text_secondary"], font=font_lbl, anchor="mt")
    
    # 2. Draw 5 structured fact rows
    start_y = box_y + box_h + 35
    row_h = 170
    row_spacing = 20
    
    font_num = get_font("Outfit-Bold.ttf", 34)
    font_title = get_font("Outfit-Bold.ttf", 28)
    font_desc = get_font("Inter-Regular.ttf", 23)
    
    points = content.get("card_points", [])
    # Guarantee exactly 5 points
    while len(points) < 5:
        points.append("Info: Keine weiteren Angaben vorhanden.")
        
    for i, pt in enumerate(points[:5]):
        row_y = start_y + i * (row_h + row_spacing)
        row_coords = [box_x, row_y, box_x + box_w, row_y + row_h]
        
        # Row container (filled with subtle card background)
        draw_rounded_rect_with_border(
            draw, row_coords, radius=18,
            fill=COLORS["card_bg"], outline=(20, 44, 48), width=1
        )
        
        # Circle badge for number
        cx, cy, cr = box_x + 65, row_y + 85, 32
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=COLORS["primary"])
        draw.text((cx, cy), str(i + 1), fill=COLORS["background"], font=font_num, anchor="mm")
        
        # Parse "Titel: Beschreibung"
        parts = pt.split(":", 1)
        if len(parts) == 2:
            title, desc = parts[0].strip(), parts[1].strip()
        else:
            title, desc = pt.strip(), ""
            
        # Draw Title
        draw.text((box_x + 130, row_y + 30), title, fill=COLORS["primary"], font=font_title, anchor="lm")
        
        # Draw Wrapped Description (up to 3 lines, dynamically centered vertically)
        desc_lines = textwrap.wrap(desc, width=52)
        lines_to_draw = desc_lines[:3]
        total_text_h = len(lines_to_draw) * 28
        start_desc_y = row_y + 60 + (95 - total_text_h) / 2
        
        desc_y = start_desc_y
        for line in lines_to_draw:
            draw.text((box_x + 130, desc_y), line, fill=COLORS["text"], font=font_desc, anchor="lm")
            desc_y += 28

    img.save(output_path, "PNG")
    print(f"GRAPHIC: Saved Viral List (Track 3) Infographic to {output_path}")
    return img

def render_dividend_calendar(payouts, output_path):
    """
    Renders Track 2 (Dividend Calendar) weekly overview:
    - 9:16 vertical canvas (1080x1920)
    - Coordinate-grid background, double golden borders
    - Brand Logo and Title
    - 2x3 Grid of 6 company cards showing:
      - Company Logo (loaded from static/logos/ or beautiful fallback badge)
      - Company Name
      - Ex-Dividend Date
      - Dividend amount & yield
    - Footer brand & disclaimer
    """
    content = {
        "headline": "DIVIDENDEN-KALENDER",
        "subheadline": "Kommende Ex-Termine der Woche"
    }
    img, draw, top_y = render_base_layout(content)
    
    # 2x3 Grid configuration
    cols, rows = 2, 3
    start_x = 80
    start_y = max(top_y + 35, 520)
    box_w = 440
    box_h = 360
    gap_x = 40
    gap_y = 30
    
    font_name = get_font("Outfit-Bold.ttf", 28)
    font_date = get_font("Inter-Bold.ttf", 24)
    font_div = get_font("Inter-Regular.ttf", 22)
    font_fallback = get_font("Outfit-Bold.ttf", 40)
    
    # Pad or slice payouts list to exactly 6 elements
    payouts = list(payouts)[:6]
    while len(payouts) < 6:
        payouts.append({
            "symbol": "DUMMY",
            "name": "Aktie gesucht",
            "ex_date": "--.--.----",
            "dividend": "--",
            "yield": "--"
        })
        
    for idx, p in enumerate(payouts):
        r = idx // cols
        c = idx % cols
        
        box_left = start_x + c * (box_w + gap_x)
        box_top = start_y + r * (box_h + gap_y)
        box_right = box_left + box_w
        box_bottom = box_top + box_h
        
        # Draw card container
        draw_rounded_rect_with_border(
            draw, [box_left, box_top, box_right, box_bottom], radius=24,
            fill=COLORS["card_bg"], outline=COLORS["primary"], width=2
        )
        
        # 1. Company Logo or Fallback
        symbol = p.get("symbol", "").upper()
        logo_filename = f"{symbol}.png"
        logo_path = os.path.join(BASE_DIR, "static", "logos", logo_filename)
        
        logo_drawn = False
        if symbol != "DUMMY" and os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                logo_img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                
                lw, lh = logo_img.size
                lx = box_left + int((box_w - lw) / 2)
                ly = box_top + 40 + int((100 - lh) / 2)
                
                img.paste(logo_img, (lx, ly), logo_img if logo_img.mode == "RGBA" else None)
                logo_drawn = True
            except Exception as e:
                print(f"WARNING: Could not draw logo for {symbol}: {e}")
                
        if not logo_drawn:
            cx = box_left + int(box_w / 2)
            cy = box_top + 90
            cr = 45
            draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=COLORS["primary"])
            initial = p.get("name", symbol)[0].upper() if p.get("name") else symbol[0]
            draw.text((cx, cy), initial, fill=COLORS["background"], font=font_fallback, anchor="mm")
            
        # 2. Company Name
        name_text = p.get("name", symbol)
        name_wrapped = textwrap.wrap(name_text, width=18)[0]
        draw.text((box_left + 220, box_top + 185), name_wrapped, fill=COLORS["text"], font=font_name, anchor="mm")
        
        # 3. Ex-Date
        date_str = p.get("ex_date", "")
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                date_str = dt.strftime("%d.%m.%Y")
            except:
                pass
        draw.text((box_left + 220, box_top + 240), f"Ex-Tag: {date_str}", fill=COLORS["primary"], font=font_date, anchor="mm")
        
        # 4. Dividend / Yield
        div_val = p.get("dividend", "")
        yld_val = p.get("yield", "")
        if div_val and yld_val:
            div_text = f"{div_val} ({yld_val})"
        elif div_val:
            div_text = f"Dividende: {div_val}"
        else:
            div_text = f"Rendite: {yld_val}"
        draw.text((box_left + 220, box_top + 290), div_text, fill=COLORS["text_secondary"], font=font_div, anchor="mm")
        
    img.save(output_path, "PNG")
    print(f"GRAPHIC: Saved Dividend Calendar (Track 2) Infographic to {output_path}")
    return img

if __name__ == "__main__":
    # Test graphic generation with mock content
    mock_content = {
      "headline": "Die Macht des Zinseszins",
      "subheadline": "Wie kleine Beträge über Zeit Vermögen schaffen",
      "card_points": [
        "Monatlich 100€ anlegen und Zinseszins wirken lassen.",
        "Der Zinseszinseffekt wächst exponentiell über die Jahre.",
        "Früh starten ist der größte Hebel für Vermögensaufbau."
      ]
    }
    render_finance_evergreen(mock_content, "evergreen_test.png")
    
    mock_portfolio = {
      "headline": "Unsere Asset Allokation 2026",
      "subheadline": "Breit gestreut investieren für maximale Stabilität",
      "card_points": [
        "70% ETFs als unerschütterliches Fundament.",
        "20% Sachwerte in Immobilien für stabilen Cashflow.",
        "10% Crowdinvesting als renditestarke Beimischung."
      ]
    }
    render_portfolio_highlight(mock_portfolio, "portfolio_test.png", visual_mode="chart")
