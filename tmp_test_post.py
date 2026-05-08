import os
import sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import render_stock_card, CSV_FILE
from ai_logic import get_tool_promotion_caption, get_ai_verdict
from social_publisher import run_social_sync

def test_single_post(symbol="AAPL"):
    print(f"Starte Test-Post für {symbol}...")
    df = pd.read_csv(CSV_FILE)
    candidate = df[df['Symbol'] == symbol].iloc[0]
    
    name = str(candidate.get('Security'))
    fin = {
        "KGV": str(candidate.get("KGV", "N/A")),
        "Dividendenrendite": str(candidate.get("Dividendenrendite", "N/A")),
        "Umsatzwachstum 3J": str(candidate.get("Umsatzwachstum 3J (erwartet)", "N/A")),
        "EK-Rendite": str(candidate.get("Eigenkapitalrendite", "N/A"))
    }
    
    print("Hole KI-Verdict...")
    verdict = get_ai_verdict(symbol, name, fin)
    
    print("Generiere Infografik (Portrait 1080x1350)...")
    img = render_stock_card(candidate, None, fetch_analyst=True, ai_verdict=verdict)
    
    public_dir = os.path.join("static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    public_path = os.path.join(public_dir, f"test_{symbol}.png")
    img.save(public_path)
    
    # Instagram-kompatible URL über WordPress generieren
    from wp_auto_publisher import WP_MEDIA_URL, WP_USER, WP_PASS, HTTPBasicAuth
    import requests
    import io
    
    print("Lade Bild nach WordPress hoch...")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    media_response = requests.post(
        WP_MEDIA_URL,
        auth=HTTPBasicAuth(WP_USER, WP_PASS),
        data=img_byte_arr.getvalue(),
        headers={
            'Content-Type': 'image/png',
            'Content-Disposition': f'attachment; filename="test_{symbol}.png"'
        }
    )
    wp_img_url = media_response.json().get('source_url', '') if media_response.status_code == 201 else None
    
    print(f"Hole Caption (mit neuem Link-Support)...")
    caption = get_tool_promotion_caption(False, name, symbol, str(fin))
    
    print("Feuere Post ab...")
    run_social_sync(symbol, caption, public_path, blog_url="https://schatzsuche40.de", wp_img_url=wp_img_url, title=name)
    print("Fertig!")

if __name__ == "__main__":
    test_single_post("AAPL")
