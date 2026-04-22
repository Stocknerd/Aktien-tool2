import os
import random
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from core import load_df, render_stock_card
from ai_logic import get_ai_verdict, get_ai_long_analysis, get_social_caption, get_ai_excerpt, generate_blog_header_image
from social_publisher import run_social_sync
from datetime import datetime
import io
import tempfile
import json
from pathlib import Path

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts"
WP_MEDIA_URL = "https://schatzsuche40.de/wp-json/wp/v2/media"
WP_TAGS_URL = "https://schatzsuche40.de/wp-json/wp/v2/tags"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def get_or_create_tag(tag_name):
    search_res = requests.get(f"{WP_TAGS_URL}?search={tag_name}", auth=HTTPBasicAuth(WP_USER, WP_PASS))
    if search_res.status_code == 200:
        for tag in search_res.json():
            if tag['name'].lower() == tag_name.lower():
                return tag['id']
                
    create_res = requests.post(WP_TAGS_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json={"name": tag_name})
    if create_res.status_code == 201:
        return create_res.json().get('id')
    elif create_res.status_code == 400:
        # term existing fallback
        return create_res.json().get('data', {}).get('term_id')
    return None

def generate_blog_post():
    print("Lade Aktien-Datenbank...")
    df = load_df()
    
    if df.empty:
        print("Fehler: stock_data.csv konnte nicht geladen werden.")
        return

    social_data = [] # Stores data for post-WP social push
    featured_media_id = None
    
    raw_data_dir = Path("data/raw")
    
    # Filter out invalid stuff
    clean_df = df.dropna(subset=['Symbol', 'Security', 'Marktkapitalisierung', 'Dividendenrendite']).copy()
    
    try:
        clean_df['MarketCap_Num'] = pd.to_numeric(clean_df['Marktkapitalisierung'], errors='coerce')
        # Ensure it's a string before calling replace
        clean_df['DivYield_Num'] = clean_df['Dividendenrendite'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        
        # Super-caps with high dividends (> 3%)
        candidates = clean_df[(clean_df['MarketCap_Num'] > 50_000_000_000) & (clean_df['DivYield_Num'] > 3.0)]
        
        if len(candidates) < 3:
            candidates = clean_df[(clean_df['MarketCap_Num'] > 10_000_000_000) & (clean_df['DivYield_Num'] > 2.0)]
            
    except Exception as e:
        print(f"Filter fehlgeschlagen: {e}. Nutze Fallback.")
        candidates = clean_df

    if len(candidates) < 3:
        # ABSOLUTE Fallback
        candidates = clean_df

    selected = candidates.sample(n=3)
    
    date_str = datetime.today().strftime("%d.%m.%Y")
    title = f"Top 3 Dividendenaktien im Check: Analyse & Ausblick ({date_str})"
    
    stock_names = [str(r.get('Security')) for _, r in selected.iterrows()]
    
    # Generate SEO Outro/Intro early so we can embed it
    print("Generiere SEO-Vorschautext...")
    excerpt = get_ai_excerpt(title, f"Analyse der Aktien {', '.join(stock_names)}")
    
    html_content = f"""
    <!-- wp:paragraph {{"className":"is-style-default"}} -->
    <p><em><strong>{excerpt}</strong></em></p>
    <!-- /wp:paragraph -->
    
    <!-- wp:paragraph -->
    <p>Herzlich willkommen zu unserem heutigen Markt-Screening. Basierend auf aktuellen Datenbank-Auswertungen haben wir drei spannende Unternehmen herausgefiltert, die derzeit durch attraktive Kennzahlen und eine solide Marktstellung auffallen. Diese Analyse wird durch moderne Daten-Algorithmen unterstützt, um objektive Einblicke in die fundamentale Entwicklung zu geben.</p>
    <!-- /wp:paragraph -->
    """

    # --- NEW: Generate Premium Landscape Blog Header via DALL-E ---
    print("Generiere Premium Querformat-Blog-Header via DALL-E 3...")
    header_img = generate_blog_header_image(stock_names)
    
    # Fallback if DALL-E fails
    if not header_img:
        print("Fallback auf lokale Grafik...")
        
    from core import render_blog_header
    selected_list = selected.to_dict('records')
    # Use render_blog_header to composite logos and stats over the bg_img
    header_img = render_blog_header(selected_list, bg_img=header_img)
        
    header_byte_arr = io.BytesIO()
    header_img.save(header_byte_arr, format='PNG')
    header_bytes = header_byte_arr.getvalue()

    print("Lade Blog-Header in WordPress hoch...")
    header_response = requests.post(
        WP_MEDIA_URL,
        auth=HTTPBasicAuth(WP_USER, WP_PASS),
        data=header_bytes,
        headers={
            'Content-Type': 'image/png',
            'Content-Disposition': 'attachment; filename="blog_header_premium.png"'
        }
    )
    if header_response.status_code == 201:
        featured_media_id = header_response.json().get('id')
        print("Update Bild-Metadaten (SEO Alt Text & Titel)...")
        # Update Media metadata for better SEO
        meta_data = {
            "title": f"Aktienanalyse {date_str}: {', '.join(stock_names)}",
            "alt_text": f"Geprüfte Aktienanalyse und Dividenden-Check für {', '.join(stock_names)}",
            "caption": "Generierte Analyse von Schatzsuche 4.0",
            "description": "Premium Finanz-Analyse Header"
        }
        requests.post(f"{WP_MEDIA_URL}/{featured_media_id}", auth=HTTPBasicAuth(WP_USER, WP_PASS), json=meta_data)
    for _, row in selected.iterrows():
        symbol = str(row.get('Symbol'))
        name = str(row.get('Security'))
        
        # Get Analyst Mean Target and other keys correctly
        mean_t = str(row.get("Analyst Mean Target") or row.get("Analysten_Kursziel", "N/A"))
        num_an = str(row.get("Number of Analysts") or row.get("Anzahl Analystenmeinungen", "N/A"))
        
        financial_data = {
            "KGV": str(row.get("KGV", "N/A")),
            "Dividendenrendite": str(row.get("Dividendenrendite", "N/A")),
            "Eigenkapitalrendite": str(row.get("Eigenkapitalrendite", "N/A")),
            "Analysten Kursziel": mean_t,
            "Anzahl Analysten": num_an,
            "Wachstum (3J)": str(row.get("Umsatzwachstum 3J (erwartet)", "N/A"))
        }

        # Load Business Summary from raw JSON if available
        business_summary = ""
        try:
            json_path = raw_data_dir / f"{symbol}.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw_info = json.load(f)
                    business_summary = raw_info.get("longBusinessSummary", "")
        except Exception as e:
            print(f"Warnung: Konnte Rohdaten für {symbol} nicht lesen: {e}")
        
        print(f"Hole KI Analyse für {name} ({symbol})...")
        short_verdict = get_ai_verdict(symbol, name, financial_data)
        long_analysis = get_ai_long_analysis(symbol, name, financial_data, business_summary=business_summary)
        
        # Bild generieren
        print(f"Generiere Infografik für {symbol}...")
        img = render_stock_card(row, None, fetch_analyst=True, ai_verdict=short_verdict)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # Bild hochladen
        print(f"Lade Bild für {symbol} hoch...")
        media_response = requests.post(
            WP_MEDIA_URL,
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            data=img_bytes,
            headers={
                'Content-Type': 'image/png',
                'Content-Disposition': f'attachment; filename="{symbol}_analysis.png"'
            }
        )
        
        img_url = ""
        media_id = None
        if media_response.status_code == 201:
            media_id = media_response.json().get('id')
            img_url = media_response.json().get('source_url', '')
            
            # Note: We no longer set featured_media_id here, as we use the landscape header
        
        html_content += f"""
        <!-- wp:heading {{"level":3}} -->
        <h3>{name} ({symbol})</h3>
        <!-- /wp:heading -->
        
        {long_analysis}
        """
        
        if img_url:
            html_content += f"""
            <!-- wp:image {{"align":"center","sizeSlug":"large"}} -->
            <figure class="wp-block-image aligncenter size-large"><img src="{img_url}" alt="Aktienanalyse {name}"/></figure>
            <!-- /wp:image -->

            <!-- wp:table {{"className":"is-style-stripes"}} -->
            <figure class="wp-block-table is-style-stripes"><table class="has-fixed-layout"><tbody>
            {"".join([f"<tr><td><strong>{k.replace('_', ' ')}</strong></td><td>{v}</td></tr>" for k, v in financial_data.items()])}
            </tbody></table></figure>
            <!-- /wp:table -->
            """
            
        # Prepare Social Media Data
        social_data.append({
            "symbol": symbol,
            "name": name,
            "image": img,
            "financial_data": financial_data
        })

        html_content += f"""
        <!-- wp:quote -->
        <blockquote class="wp-block-quote"><p><strong>Zusammenfassung:</strong> {short_verdict}</p></blockquote>
        <!-- /wp:quote -->
        
        <!-- wp:spacer {{"height":"30px"}} -->
        <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
        <!-- /wp:spacer -->
        """

    # Add disclaimer at the end
    html_content += f"""
    <!-- wp:paragraph -->
    <p><em>Hinweis: Diese Analyse dient der allgemeinen Information und stellt keine Anlageberatung dar. Aktieninvestments sind mit Risiken verbunden. Führe immer deine eigene Recherche durch.</em></p>
    <!-- /wp:paragraph -->
    """
    
    # Determine publishing status: 'publish' on Mondays (weekday 0), 'draft' otherwise
    current_weekday = datetime.today().weekday()
    status = "publish" if current_weekday == 0 else "draft"
    
    # Prepare dynamic tags
    print("Bereite dynamische SEO-Schlagwörter vor...")
    tag_names = ["Aktienanalyse", "Dividende", "Börse", "Finanzen"]
    tag_ids = [tid for tid in (get_or_create_tag(t) for t in tag_names) if tid]
    
    post_data = {
        "title": title,
        "content": html_content,
        "excerpt": excerpt,
        "status": status,
        "categories": [5],
        "tags": tag_ids, 
        "custom_seo_data": {
            "yoast_desc": excerpt,
            "yoast_kw": tag_names[0],
            "prosodia_active": True
        }
    }
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    print("Veröffentliche Beitrag in WordPress...")
    response = requests.post(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json=post_data, headers={'Content-Type': 'application/json'})

    if response.status_code == 201:
        blog_url = response.json().get('link')
        print(f"Erfolg! Post erstellt: {blog_url}")
        
        # Now trigger Social Media for all 3 stocks
        for item in social_data:
            try:
                symbol, name = item["symbol"], item["name"]
                print(f"Hole Social-Media-Caption für {name} ({symbol})...")
                social_caption = get_social_caption(symbol, name, item["financial_data"])
                
                # Save to public static folder for Meta API fetch
                public_dir = os.path.join("static", "temp_social")
                os.makedirs(public_dir, exist_ok=True)
                public_path = os.path.join(public_dir, f"{symbol}_post.png")
                
                item["image"].save(public_path)
                run_social_sync(symbol, social_caption, public_path, blog_url=blog_url)
                
            except Exception as e:
                print(f"Fehler bei Social-Push {item['symbol']}: {e}")
    else:
        print(f"Warnung: Veröffentlichung fehlgeschlagen. Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    generate_blog_post()
