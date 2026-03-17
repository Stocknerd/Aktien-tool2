import sys
import io
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "    layout_mode = (request.form.get('layout') or request.args.get('layout') or 'default').lower()"
end_marker = "    draw.text((fx, fy), foot, fill=text_color, font=f_foot)"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker) + len(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found")
    sys.exit(1)

extracted = content[start_idx:end_idx]

extracted_deindented = extracted

# Clean up variables passed as args
extracted_deindented = extracted_deindented.replace(
    "layout_mode = (request.form.get('layout') or request.args.get('layout') or 'default').lower()\n",
    ""
)
extracted_deindented = extracted_deindented.replace(
    "watermark = (request.form.get('watermark') or request.args.get('watermark') or '').strip()\n",
    ""
)

# Fix background logic
bg_block = """bg_path = BACKGROUND
    if 'background' in request.files and request.files['background'] and request.files['background'].filename:
        try:
            bg_file = request.files['background']
            bg_bytes = bg_file.read()
            bg_img = Image.open(io.BytesIO(bg_bytes)).convert('RGBA')
            bg_img = resize_cover(bg_img, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        except Exception:
            bg_img = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (20, 24, 28, 255)) if layout_mode == 'dark' else resize_cover(Image.open(bg_path).convert('RGBA'), OUTPUT_WIDTH, OUTPUT_HEIGHT)
    else:
        if layout_mode == 'dark':
            bg_img = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (20, 24, 28, 255))
        else:
            bg_img = resize_cover(Image.open(bg_path).convert('RGBA'), OUTPUT_WIDTH, OUTPUT_HEIGHT)"""

new_bg_block = """if bg_img is None:
        if layout_mode == 'dark':
            bg_img = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (20, 24, 28, 255))
        else:
            bg_img = resize_cover(Image.open(BACKGROUND).convert('RGBA'), OUTPUT_WIDTH, OUTPUT_HEIGHT)"""

extracted_deindented = extracted_deindented.replace(bg_block, new_bg_block)

new_function = f'''def render_stock_card(row, selected: list, layout_mode: str = 'default', watermark: str = "", bg_img = None):
    layout_mode = layout_mode.lower()
{extracted_deindented}
    return img

'''

route_logic = '''    layout_mode = (request.form.get('layout') or request.args.get('layout') or 'default').lower()
    watermark = (request.form.get('watermark') or request.args.get('watermark') or '').strip()

    bg_img = None
    if 'background' in request.files and request.files['background'] and request.files['background'].filename:
        try:
            bg_file = request.files['background']
            bg_bytes = bg_file.read()
            bg_img = Image.open(io.BytesIO(bg_bytes)).convert('RGBA')
            bg_img = resize_cover(bg_img, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        except Exception:
            pass

    img = render_stock_card(row, selected, layout_mode, watermark, bg_img)'''

new_content = content.replace(extracted, route_logic, 1)

route_marker = "@app.route('/generate_image', methods=['POST'])"
new_content = new_content.replace(route_marker, new_function + route_marker, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
