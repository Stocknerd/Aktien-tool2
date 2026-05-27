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
    "Outfit-Bold.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/outfit/static/Outfit-Bold.ttf",
    "Outfit-Regular.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/outfit/static/Outfit-Regular.ttf",
    "Inter-Regular.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inter/static/Inter-Regular.ttf",
    "Inter-Bold.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inter/static/Inter-Bold.ttf"
}

def ensure_fonts():
    """Downloads Google Fonts if they do not exist locally."""
    downloaded = {}
    for name, url in FONT_LINKS.items():
        path = os.path.join(FONTS_DIR, name)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            downloaded[name] = path
            continue
        
        print(f"FONT: Downloading Google Font {name}...")
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            downloaded[name] = path
            print(f"FONT: Successfully downloaded and cached {name}")
        except Exception as e:
            print(f"WARNING: Font download failed for {name}: {e}. Will fall back to system fonts.")
            # Map fallbacks
            fallback_system = "C:\\Windows\\Fonts\\arialbd.ttf" if "Bold" in name else "C:\\Windows\\Fonts\\arial.ttf"
            if os.path.exists(fallback_system):
                downloaded[name] = fallback_system
            else:
                downloaded[name] = "arial.ttf"
    return downloaded

# Pre-cached Font paths mapping
FONT_PATHS = ensure_fonts()
