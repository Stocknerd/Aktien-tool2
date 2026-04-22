import os
import sys
import time
import random
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Add to path to import correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import render_stock_card, render_comparison_card_vertical, CSV_FILE
from ai_logic import get_tool_promotion_caption, get_ai_verdict, get_ai_comparison_verdict
from social_publisher import run_social_sync

def get_top_100_stocks(csv_path=CSV_FILE):
    """Liest die CSV, sortiert nach Market Cap und liefert die Top 100 zurück."""
    if not os.path.exists(csv_path):
        print(f"Fehler: {csv_path} existiert nicht.")
        return None
        
    df = pd.read_csv(csv_path)
    
    # Sicherstellen, dass Market Cap als numerischer Wert nutzbar ist
    if 'Market Cap' in df.columns:
        df['Market_Cap_Num'] = pd.to_numeric(df['Market Cap'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        df = df.sort_values(by='Market_Cap_Num', ascending=False)
        
    df = df.dropna(subset=['Symbol', 'Security', 'KGV'])
    
    top_100 = df.head(100)
    return top_100

def extract_financial_data(row):
    """Extrahiert Kennzahlen für den KI Prompt."""
    return {
        "KGV": str(row.get("KGV", "N/A")),
        "Dividendenrendite": str(row.get("Dividendenrendite", "N/A")),
        "Umsatzwachstum 3J": str(row.get("Umsatzwachstum 3J (erwartet)", "N/A")),
        "EK-Rendite": str(row.get("Eigenkapitalrendite", "N/A")),
        "Nettomarge": str(row.get("Nettomarge", "N/A"))
    }

def run_daily_poster():
    print("Starte täglichen Standalone Social Auto-Poster...")
    top_100 = get_top_100_stocks()
    
    if top_100 is None or top_100.empty:
        print("Konnte keine Aktien-Daten laden. Skript bricht ab.")
        return
        
    # Zufall: 0 = Einzelaktie, 1 = Vergleich
    is_comparison = random.choice([True, False])
    
    public_dir = os.path.join("static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    if is_comparison:
        print("Würfel entscheidet: BÖRSEN-DUELL (Vergleich)")
        candidates = top_100.sample(n=2).to_dict('records')
        row_a = candidates[0]
        row_b = candidates[1]
        
        sym_a, name_a = str(row_a.get('Symbol')), str(row_a.get('Security'))
        sym_b, name_b = str(row_b.get('Symbol')), str(row_b.get('Security'))
        
        print(f"Gewählt: {name_a} ({sym_a}) vs {name_b} ({sym_b})")
        
        # KI Vergleich
        fin_a = extract_financial_data(row_a)
        fin_b = extract_financial_data(row_b)
        verdict = get_ai_comparison_verdict(sym_a, name_a, fin_a, sym_b, name_b, fin_b)
        
        # Grafik generieren
        print("Generiere Infografik...")
        img = render_comparison_card_vertical(row_a, row_b, ai_verdict=verdict)
        
        # Meta Infos für Social Publisher
        names = f"{name_a} vs {name_b}"
        symbols = f"{sym_a} vs {sym_b}"
        fin_texts = f"{name_a}: {fin_a}\n{name_b}: {fin_b}"
        
        out_filename = f"comparison_{sym_a}_{sym_b}.png"
        
    else:
        print("Würfel entscheidet: EINZEL-ANALYSE")
        candidate = top_100.sample(n=1).iloc[0]
        sym, name = str(candidate.get('Symbol')), str(candidate.get('Security'))
        print(f"Gewählt: {name} ({sym})")
        
        fin = extract_financial_data(candidate)
        verdict = get_ai_verdict(sym, name, fin)
        
        print("Generiere Infografik...")
        img = render_stock_card(candidate, None, fetch_analyst=True, ai_verdict=verdict)
        
        names = name
        symbols = sym
        fin_texts = str(fin)
        
        out_filename = f"single_{sym}.png"

    # Bild speichern
    public_path = os.path.join(public_dir, out_filename)
    img.save(public_path)
    print(f"Bild gespeichert unter {public_path}")
    
    # Social Caption mit Promotion
    print("Hole KI Texte für Social Media...")
    caption = get_tool_promotion_caption(is_comparison, names, symbols, fin_texts)
    
    # Posten
    print("Feuere Post an Meta Server...")
    # Da dieses Skript unabhängig läuft und wir kein direktes WP Image brauchen,
    # reicht public_path und wir nutzen Local HTTP oder übergeben wp_img_url=None.
    # Da Instagram aber HTTPS braucht für den Remote Fetch, können wir für dieses Skript
    # den Image-Server der eigenen Domain nutzen, wenn wir den Pfad mappen oder 
    # wir laden es kurz als blindes attachment nach WordPress.
    
    # Workaround: Um Meta's HTTPS CDN Fetch zu ermöglichen, laden wir das Bild als blindes Media in WP hoch
    # oder nutzen den direkten ngrok/https static Pfad, falls statisch gehostet.
    # Da Schatzsuche40 eine aktive WP Installation ist, können wir das Bild einmal dorthin hochjagen
    # und die URL nutzen.
    
    from wp_auto_publisher import WP_MEDIA_URL, WP_USER, WP_PASS, HTTPBasicAuth
    import requests
    import io
    
    try:
        print("Lade Bild kurz als Asset nach WordPress, um eine legitime HTTPS URL für Meta Instagram zu generieren...")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        media_response = requests.post(
            WP_MEDIA_URL,
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            data=img_bytes,
            headers={
                'Content-Type': 'image/png',
                'Content-Disposition': f'attachment; filename="{out_filename}"'
            }
        )
        wp_img_url = None
        if media_response.status_code == 201:
            wp_img_url = media_response.json().get('source_url', '')
            print(f"HTTPS Asset URL generiert: {wp_img_url}")
        else:
            print("Fehler beim Bilder-Upload, Instagram Fetch könnte fehlschlagen.")
            
    except Exception as e:
        print(f"WordPress Asset Upload gescheitert: {e}")
        wp_img_url = None

    url_link = "https://schatzsuche40.de"
    
    run_social_sync(symbols, caption, public_path, blog_url=url_link, wp_img_url=wp_img_url)
    
    print("✅ Täglicher Post erfolgreich abgesetzt!")

if __name__ == "__main__":
    run_daily_poster()
