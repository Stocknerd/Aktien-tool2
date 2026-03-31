import os
import random
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from core import load_df, render_stock_card
from ai_logic import get_ai_verdict, get_ai_long_analysis
from datetime import datetime
import io

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts"
WP_MEDIA_URL = "https://schatzsuche40.de/wp-json/wp/v2/media"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def generate_blog_post():
    print("Lade Aktien-Datenbank...")
    df = load_df()
    
    if df.empty:
        print("Fehler: stock_data.csv konnte nicht geladen werden.")
        return

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
    title = f"KI-Analyse: 3 Spannende Einkommensaktien für dein Depot ({date_str})"
    
    html_content = f"""
    <!-- wp:paragraph -->
    <p>Willkommen zu unserem tagesaktuellen KI-Aktienscreening! Unser automatisches Python-Tool durchsucht täglich unsere Datenbank von tiefgründig recherchierten globalen Werten und lässt die aktuellen Kennzahlen von <strong>gpt-5.4-mini</strong> bewerten. Hier sind drei starke Einkommenskandidaten für heute:</p>
    <!-- /wp:paragraph -->
    """

    for _, row in selected.iterrows():
        symbol = str(row.get('Symbol'))
        name = str(row.get('Security'))
        
        financial_data = {
            "KGV": str(row.get("KGV", "N/A")),
            "Dividendenrendite": str(row.get("Dividendenrendite", "N/A")),
            "Eigenkapitalrendite": str(row.get("Eigenkapitalrendite", "N/A")),
            "Analysten Kursziel": str(row.get("Analysten_Kursziel", "N/A")),
            "Wachstum (3J)": str(row.get("Umsatzwachstum 3J (erwartet)", "N/A"))
        }
        
        print(f"Hole KI Analyse für {name} ({symbol})...")
        short_verdict = get_ai_verdict(symbol, name, financial_data)
        long_analysis = get_ai_long_analysis(symbol, name, financial_data)
        
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
        if media_response.status_code == 201:
            img_url = media_response.json().get('source_url', '')
        
        html_content += f"""
        <!-- wp:heading {{"level":3}} -->
        <h3>{name} ({symbol})</h3>
        <!-- /wp:heading -->
        
        <!-- wp:paragraph -->
        {long_analysis}
        <!-- /wp:paragraph -->
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
            
        html_content += f"""
        <!-- wp:quote -->
        <blockquote class="wp-block-quote"><p><strong>Zusammenfassung:</strong> {short_verdict}</p></blockquote>
        <!-- /wp:quote -->
        
        <!-- wp:spacer {{"height":"30px"}} -->
        <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
        <!-- /wp:spacer -->
        """

    # Add YouTube video at the end
    html_content += f"""
    <!-- wp:heading {{"level":2}} -->
    <h2 class="wp-block-heading">Passendes Video: Meine Strategie</h2>
    <!-- /wp:heading -->

    <!-- wp:embed {{"url":"https://youtu.be/XofAcibiofU","type":"video","providerNameSlug":"youtube","responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"}} -->
    <figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">
    https://youtu.be/XofAcibiofU
    </div></figure>
    <!-- /wp:embed -->

    <!-- wp:paragraph -->
    <p><em>Hinweis: Dies ist keine Anlageberatung. Führt immer eure eigene Recherche durch (Do Your Own Research - DYOR).</em></p>
    <!-- /wp:paragraph -->
    """
    
    post_data = {
        "title": title,
        "content": html_content,
        "status": "draft",
        "categories": [5]
    }

    print("Veröffentliche Beitrag in WordPress...")
    response = requests.post(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json=post_data, headers={'Content-Type': 'application/json'})

    if response.status_code == 201:
        print(f"Erfolg! Post erstellt: {response.json().get('link')}")
    else:
        print(f"Warnung: Veröffentlichung fehlgeschlagen. Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    generate_blog_post()
