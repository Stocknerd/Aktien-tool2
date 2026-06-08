import os
import json
import requests
from dotenv import load_dotenv

# Try multiple locations for .env to leverage the existing credentials
env_paths = [
    ".env",
    "../videoautomation/.env",
    "c:/Users/fhofm/Dropbox/videoautomation/.env",
    "c:/Users/fhofm/Dropbox/antigrav_schatzsuche/.env"
]
env_loaded = False
for p in env_paths:
    if os.path.exists(p):
        load_dotenv(p)
        env_loaded = True
        break
if not env_loaded:
    load_dotenv()

# Base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTEXT_DIR = os.path.join(BASE_DIR, "context")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

def hex_to_rgb(hex_str):
    """Converts hex color string (e.g. '#C9A227') to RGB tuple (e.g. (201, 162, 39))."""
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# Load brand, portfolio, colors, and disclaimers context
try:
    with open(os.path.join(CONTEXT_DIR, "brand_profile.json"), "r", encoding="utf-8") as f:
        BRAND_PROFILE = json.load(f)
except Exception as e:
    print(f"WARNING: Could not load brand_profile.json: {e}")
    BRAND_PROFILE = {}

try:
    with open(os.path.join(CONTEXT_DIR, "portfolio_profile.json"), "r", encoding="utf-8") as f:
        PORTFOLIO_PROFILE = json.load(f)
except Exception as e:
    print(f"WARNING: Could not load portfolio_profile.json: {e}")
    PORTFOLIO_PROFILE = {}

try:
    with open(os.path.join(CONTEXT_DIR, "disclaimers.json"), "r", encoding="utf-8") as f:
        DISCLAIMERS = json.load(f)
except Exception as e:
    print(f"WARNING: Could not load disclaimers.json: {e}")
    DISCLAIMERS = {}

try:
    with open(os.path.join(CONTEXT_DIR, "brand_colors.json"), "r", encoding="utf-8") as f:
        hex_colors = json.load(f)
        COLORS = {k: hex_to_rgb(v) if isinstance(v, str) and v.startswith("#") else v for k, v in hex_colors.items()}
        # For gradient list
        if "gold_gradient" in hex_colors:
            COLORS["gold_gradient"] = [hex_to_rgb(c) for c in hex_colors["gold_gradient"]]
        # Raw hex values preserved
        COLORS_HEX = hex_colors
except Exception as e:
    print(f"WARNING: Could not load brand_colors.json: {e}")
    COLORS = {
        "primary": (201, 162, 39),
        "accent": (26, 83, 92),
        "background": (11, 30, 33),
        "text": (247, 247, 247),
        "text_secondary": (160, 176, 178),
        "card_bg": (20, 44, 48),
        "border": (201, 162, 39)
    }
    COLORS_HEX = {
        "primary": "#C9A227",
        "accent": "#1A535C",
        "background": "#0B1E21",
        "text": "#F7F7F7",
        "text_secondary": "#A0B0B2",
        "card_bg": "#142C30",
        "border": "#C9A227"
    }

# Logo configuration
LOGO_PATH = os.path.join(CONTEXT_DIR, "logos", "logo.png")
if not os.path.exists(LOGO_PATH):
    # Try generating if missing
    try:
        from context.logos.generate_logo import generate_brand_logo
        generate_brand_logo(LOGO_PATH)
    except Exception as e:
        print(f"WARNING: Could not auto-generate logo: {e}")

# Cache modern Google Fonts for premium visuals
FONT_LINKS = {
    "Outfit-Bold.ttf": "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-Bold.ttf",
    "Outfit-Regular.ttf": "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-Regular.ttf",
    "Inter-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf",
    "Inter-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf"
}

def ensure_fonts():
    """Downloads Google Fonts if they do not exist locally."""
    downloaded = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for name, url in FONT_LINKS.items():
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            downloaded[name] = path
            continue
        
        print(f"FONT: Downloading Google Font {name}...")
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            downloaded[name] = path
            print(f"FONT: Successfully downloaded and cached {name}")
        except Exception as e:
            print(f"WARNING: Font download failed for {name}: {e}. Will fall back to system fonts.")
            # Map fallbacks: try Outfit (premium cached font) first, then system fonts, then arial
            fallback_system = os.path.join(FONTS_DIR, f"Outfit-{'Bold' if 'Bold' in name else 'Regular'}.ttf")
            if not (os.path.exists(fallback_system) and os.path.getsize(fallback_system) > 1000):
                if os.name == 'nt':
                    fallback_system = "C:\\Windows\\Fonts\\arialbd.ttf" if "Bold" in name else "C:\\Windows\\Fonts\\arial.ttf"
                else:
                    linux_paths = [
                        f"/usr/share/fonts/opentype/inter/Inter-{'Bold' if 'Bold' in name else 'Regular'}.otf",
                        f"/usr/share/fonts/truetype/inter/Inter-{'Bold' if 'Bold' in name else 'Regular'}.ttf",
                        f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if "Bold" in name else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if "Bold" in name else "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
                    ]
                    fallback_system = "arial.ttf"
                    for lp in linux_paths:
                        if os.path.exists(lp):
                            fallback_system = lp
                            break
            if os.path.exists(fallback_system):
                downloaded[name] = fallback_system
            else:
                downloaded[name] = "arial.ttf"
    return downloaded

# Pre-cached Font paths mapping
FONT_PATHS = ensure_fonts()
