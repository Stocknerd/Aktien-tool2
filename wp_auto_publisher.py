import os
import random
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from core import load_df, render_stock_card, render_social_square_header
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
    header_img_raw = generate_blog_header_image(stock_names)
    
    selected_list = selected.to_dict('records')
    
    from core import render_blog_header
    # Use render_blog_header to composite logos and stats over the bg_img
    header_img = render_blog_header(selected_list, bg_img=header_img_raw)
        
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
            "financial_data": financial_data,
            "wp_img_url": img_url
        })

        html_content += f"""
        <!-- wp:quote -->
        <blockquote class="wp-block-quote"><p><strong>Zusammenfassung:</strong> {short_verdict}</p></blockquote>
        <!-- /wp:quote -->
        
        <!-- wp:spacer {{"height":"30px"}} -->
        <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
        <!-- /wp:spacer -->
        """

    # Get Affiliate Links from ENV or use placeholder
    affiliate_url = os.environ.get("AFFILIATE_URL", "https://www.financeads.net/tc.php?t=47128C46917042T")
    affiliate_broker = os.environ.get("AFFILIATE_BROKER", "CapTrader")
    
    # Add Affiliate Monetization Block
    html_content += f"""
    <!-- wp:spacer {{"height":"20px"}} -->
    <div style="height:20px" aria-hidden="true" class="wp-block-spacer"></div>
    <!-- /wp:spacer -->
    
    <!-- wp:group {{"style":{{"border":{{"radius":"10px","color":"#e2e8f0","width":"2px","style":"solid"}},"spacing":{{"padding":{{"top":"20px","right":"20px","bottom":"20px","left":"20px"}}}}}},"backgroundColor":"luminous-vivid-amber","layout":{{"type":"constrained"}}}} -->
    <div class="wp-block-group has-border-color has-luminous-vivid-amber-background-color has-background" style="border-color:#e2e8f0;border-radius:10px;border-style:solid;border-width:2px;padding-top:20px;padding-right:20px;padding-bottom:20px;padding-left:20px">
    <!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"18px","fontWeight":"700"}}}},"textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color" style="font-size:18px;font-weight:700">💰 Du willst in diese Aktien investieren?</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:paragraph {{"align":"center","textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color">Eröffne jetzt dein Depot bei <strong>{affiliate_broker}</strong> und erhalte direkten Zugang zu weltweiten Börsenplätzen, günstigen Ordergebühren und professionellen Trading-Tools!</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:buttons {{"layout":{{"type":"flex","justifyContent":"center"}}}} -->
    <div class="wp-block-buttons">
    <!-- wp:button {{"backgroundColor":"vivid-green-cyan"}} -->
    <div class="wp-block-button"><a class="wp-block-button__link has-vivid-green-cyan-background-color has-background wp-element-button" href="{affiliate_url}" target="_blank" rel="noreferrer noopener"><strong>Kostenlos Depot eröffnen &amp; investieren</strong></a></div>
    <!-- /wp:button -->
    </div>
    <!-- /wp:buttons -->
    
    <!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"12px"}}}},"textColor":"contrast-3"}} -->
    <p class="has-text-align-center has-contrast-3-color has-text-color" style="font-size:12px"><em>(Anzeige / Affiliate Link: Wenn du über diesen Link ein Konto eröffnest, unterstützt du unsere Arbeit ohne Zusatzkosten für dich.)</em></p>
    <!-- /wp:paragraph -->
    </div>
    <!-- /wp:group -->

    <!-- wp:spacer {{"height":"30px"}} -->
    <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
    <!-- /wp:spacer -->

    <!-- wp:group {{"style":{{"border":{{"radius":"10px","color":"#e2e8f0","width":"2px","style":"solid"}},"spacing":{{"padding":{{"top":"20px","right":"20px","bottom":"20px","left":"20px"}}}}}},"backgroundColor":"luminous-vivid-orange","layout":{{"type":"constrained"}}}} -->
    <div class="wp-block-group has-border-color has-luminous-vivid-orange-background-color has-background" style="border-color:#e2e8f0;border-radius:10px;border-style:solid;border-width:2px;padding-top:20px;padding-right:20px;padding-bottom:20px;padding-left:20px">
    <!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"18px","fontWeight":"700"}}}},"textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color" style="font-size:18px;font-weight:700">🏦 Tipp: Das beste Girokonto Deutschlands</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:paragraph {{"align":"center","textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color">Du suchst ein kostenloses Konto mit Top-Zinsen? Die <strong>C24 Bank</strong> bietet alles, was du brauchst: Kostenlose Kontoführung, Mastercard und Echtzeit-Überweisungen.</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:buttons {{"layout":{{"type":"flex","justifyContent":"center"}}}} -->
    <div class="wp-block-buttons">
    <!-- wp:button {{"backgroundColor":"vivid-cyan-blue"}} -->
    <div class="wp-block-button"><a class="wp-block-button__link has-vivid-cyan-blue-background-color has-background wp-element-button" href="https://a.check24.net/misc/click.php?pid=109920&aid=18&deep=c24bank&cat=14" target="_blank" rel="noreferrer noopener"><strong>C24 Konto kostenlos eröffnen</strong></a></div>
    <!-- /wp:button -->
    </div>
    <!-- /wp:buttons -->
    </div>
    <!-- /wp:group -->

    <!-- wp:spacer {{"height":"30px"}} -->
    <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
    <!-- /wp:spacer -->

    <!-- wp:group {{"style":{{"border":{{"radius":"10px","color":"#e2e8f0","width":"2px","style":"solid"}},"spacing":{{"padding":{{"top":"20px","right":"20px","bottom":"20px","left":"20px"}}}}}},"backgroundColor":"pale-cyan-blue","layout":{{"type":"constrained"}}}} -->
    <div class="wp-block-group has-border-color has-pale-cyan-blue-background-color has-background" style="border-color:#e2e8f0;border-radius:10px;border-style:solid;border-width:2px;padding-top:20px;padding-right:20px;padding-bottom:20px;padding-left:20px">
    <!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"18px","fontWeight":"700"}}}},"textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color" style="font-size:18px;font-weight:700">📘 Gratis: Leitfaden Aktienbewertung</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:paragraph {{"align":"center","textColor":"black"}} -->
    <p class="has-text-align-center has-black-color has-text-color">Lerne Schritt für Schritt, wie du den fairen Wert einer Aktie berechnest. Hol dir jetzt unseren kostenlosen PDF-Leitfaden!</p>
    <!-- /wp:paragraph -->
    
    <!-- wp:buttons {{"layout":{{"type":"flex","justifyContent":"center"}}}} -->
    <div class="wp-block-buttons">
    <!-- wp:button {{"backgroundColor":"vivid-cyan-blue"}} -->
    <div class="wp-block-button"><a class="wp-block-button__link has-vivid-cyan-blue-background-color has-background wp-element-button" href="https://schatzsuche40.de/leitfaden-download/" target="_blank" rel="noreferrer noopener"><strong>PDF Leitfaden herunterladen</strong></a></div>
    <!-- /wp:button -->
    </div>
    <!-- /wp:buttons -->
    </div>
    <!-- /wp:group -->

    <!-- wp:heading {{"level":4}} -->
    <h4 class="wp-block-heading">Interessante Links für dich:</h4>
    <!-- /wp:heading -->

    <!-- wp:list -->
    <ul class="wp-block-list">
        <li><a href="https://compare.schatzsuche40.de"><strong>Aktien-Vergleichstool:</strong> Vergleiche deine Lieblingsaktien direkt miteinander.</a></li>
        <li><a href="https://schatzsuche40.de/category/aktienanalysen/"><strong>Alle Analysen:</strong> Entdecke weitere spannende Aktienchecks.</a></li>
        <li><a href="https://schatzsuche40.de/dividenden-strategie/"><strong>Dividenden-Strategie:</strong> So baust du dir ein passives Einkommen auf.</a></li>
    </ul>
    <!-- /wp:list -->
    """

    # Add disclaimer at the end
    html_content += f"""
    <!-- wp:spacer {{"height":"30px"}} -->
    <div style="height:30px" aria-hidden="true" class="wp-block-spacer"></div>
    <!-- /wp:spacer -->
    
    <!-- wp:paragraph -->
    <p><em>Hinweis: Diese Analyse dient der allgemeinen Information und stellt keine Anlageberatung dar. Aktieninvestments sind mit Risiken verbunden. Führe immer deine eigene Recherche durch.</em></p>
    <!-- /wp:paragraph -->
    """
    
    # Determine publishing status: 'publish' on Mondays (0) and Fridays (4), 'draft' otherwise
    current_weekday = datetime.today().weekday()
    status = "publish" if current_weekday in (0, 4) else "draft"
    
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
        post_id = response.json().get('id')
        blog_url = response.json().get('link')
        print(f"Erfolg! Post erstellt: {blog_url}")
        
        # --- NEW: Fallback Meta Injection via XML-RPC ---
        print("Behebe WordPress SEO-Sperren (XML-RPC Injection)...")
        import xmlrpc.client
        try:
            server = xmlrpc.client.ServerProxy("https://schatzsuche40.de/xmlrpc.php")
            custom_fields = [
                {'key': '_yoast_wpseo_metadesc', 'value': excerpt},
                {'key': '_yoast_wpseo_focuskw', 'value': tag_names[0]},
                {'key': '_prosodia_vgw_os_pzm_active', 'value': '1'},
                {'key': '_prosodia_vgw_os_pzm_status', 'value': 'assigned'},
                {'key': 'prosodia_vgw_os_pzm_method', 'value': 'automatic'}
            ]
            server.wp.editPost(0, WP_USER, WP_PASS, post_id, {'custom_fields': custom_fields})
            print("[OK] XML-RPC Meta Update erfolgreich.")
        except Exception as e:
            print(f"Fehler bei XML-RPC Meta-Injizierung: {e}")
        
        # --- NEW: Trigger ONE Social Media Post for the ENTIRE Article ---
        if status == "publish":
            try:
                print("Hole generelle Social-Media-Caption für den Blogartikel...")
                stock_names_str = ", ".join(stock_names)
                social_caption = get_social_caption(stock_names_str, excerpt)
                
                # Generate a separate SQUARE image for Social Media (better for Instagram/Facebook)
                print("Generiere quadratisches Social-Media-Header-Bild...")
                social_img = render_social_square_header(selected_list, title_text="TOP 3 DIVIDENDEN-CHECKS", bg_img=header_img_raw)
                
                # Save the square header image to the public path for Meta API fetch
                public_dir = os.path.join("static", "temp_social")
                os.makedirs(public_dir, exist_ok=True)
                public_path_sq = os.path.join(public_dir, "blog_header_sq.png")
                social_img.save(public_path_sq)
                
                # Upload the square social header image to WordPress to get a secure HTTPS URL for Meta
                print("Lade quadratisches Social-Media-Header-Bild in WordPress hoch...")
                social_img_byte_arr = io.BytesIO()
                social_img.save(social_img_byte_arr, format='PNG')
                social_img_bytes = social_img_byte_arr.getvalue()
                
                sq_wp_img_url = None
                try:
                    sq_media_response = requests.post(
                        WP_MEDIA_URL,
                        auth=HTTPBasicAuth(WP_USER, WP_PASS),
                        data=social_img_bytes,
                        headers={
                            'Content-Type': 'image/png',
                            'Content-Disposition': 'attachment; filename="blog_header_sq.png"'
                        }
                    )
                    if sq_media_response.status_code == 201:
                        sq_wp_img_url = sq_media_response.json().get('source_url', '')
                        print(f"[OK] Quadratisches Header-Bild hochgeladen: {sq_wp_img_url}")
                    else:
                        print(f"[ERR] Quadratisches Header-Bild Upload fehlgeschlagen: {sq_media_response.status_code}")
                except Exception as upload_err:
                    print(f"[ERR] WordPress Asset Upload gescheitert: {upload_err}")
                    
                run_social_sync("MARKET-UPDATE", social_caption, public_path_sq, blog_url=blog_url, wp_img_url=sq_wp_img_url, title=title)
            except Exception as e:
                print(f"Fehler bei Social-Push (Artikel-Ebene): {e}")
        else:
            print("[SKIP] Überspringe Social-Media-Push, da der Beitrag nur als Entwurf (Draft) gespeichert wurde.")
    else:
        print(f"Warnung: Veröffentlichung fehlgeschlagen. Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    generate_blog_post()
