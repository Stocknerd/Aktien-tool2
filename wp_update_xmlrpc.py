#!/usr/bin/env python3
"""
WordPress XML-RPC Page Updater
Uses XML-RPC (which bypasses Authorization header restrictions) to update pages.
"""

import sys
import xmlrpc.client

WP_URL = "https://schatzsuche40.de/xmlrpc.php"
WP_USER = "fhofmann"
WP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BLOG_ID = 1

HTML_PAGE_1210 = """
<h3>Kurzanleitung: So erstellst du dein Bild</h3>
<ol>
  <li><strong>Aktie suchen</strong>: Gib den Namen oder das Kürzel (z.B. Apple oder AAPL) in das Suchfeld ein.</li>
  <li><strong>Design w\u00e4hlen</strong>: Entscheide dich f\u00fcr das helle Standard-Design oder den eleganten <strong>Dark Mode</strong>.</li>
  <li><strong>Metriken anpassen</strong>: W\u00e4hle bis zu 8 Kennzahlen (Dividende, KGV, Marge etc.), die dir wichtig sind.</li>
  <li><strong>KI-Check</strong>: Aktiviere die <strong>KI-Insights</strong>, um eine automatisierte Einsch\u00e4tzung von GPT-4o zu erhalten.</li>
  <li><strong>Download</strong>: Klicke auf "Bild erzeugen" und lade dein PNG direkt herunter.</li>
</ol>
<div style="max-width:1200px;margin-top:24px;">
  <iframe src="https://tool.schatzsuche40.de/?embed=1" style="width:100%;height:950px;border:0;border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.1);" loading="lazy"></iframe>
</div>
"""

HTML_PAGE_1384 = """
<h3>Aktien-Vergleich auf Profi-Niveau</h3>
<p>Finde heraus, welches Unternehmen fundamental die Nase vorn hat. Unser Tool vergleicht f\u00fcr dich Rentabilit\u00e4t, Bewertung und Dividenden-Check im direkten Duell.</p>
<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
  <iframe src="https://tool.schatzsuche40.de/compare?embed=1" width="100%" height="850" frameborder="0" style="border-radius:14px;display:block;" loading="lazy" title="Aktien Vergleichstool"></iframe>
</div>
<h3>So geht\u2019s:</h3>
<ol>
  <li>Gib links und rechts die beiden Ticker-Symbole ein (z.B. MSFT vs. AAPL).</li>
  <li>W\u00e4hle ein Set an Kennzahlen oder bleib beim Standard.</li>
  <li>Erhalte sofort einen visuellen Vergleich inklusive Analysten-Kurszielen beider Werte.</li>
</ol>
"""

def main():
    print("=" * 60)
    print("WordPress XML-RPC Updater")
    print("=" * 60)
    
    try:
        server = xmlrpc.client.ServerProxy(WP_URL, allow_none=True)
        
        # Test connection
        print("Testing connection...")
        user_info = server.wp.getProfile(BLOG_ID, WP_USER, WP_PASS)
        print(f"  Connected as: {user_info.get('display_name', WP_USER)}")
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False

    updates = [
        (1210, "Aktien-Analyse Tool", HTML_PAGE_1210),
        (1384, "Aktien-Vergleich", HTML_PAGE_1384),
    ]
    
    results = {}
    for page_id, name, html_content in updates:
        print(f"\nUpdating page {page_id} ({name})...")
        try:
            # Get post first
            post = server.wp.getPost(BLOG_ID, WP_USER, WP_PASS, page_id, ['post_content', 'post_title'])
            current = post.get('post_content', '')
            title = post.get('post_title', f'Page {page_id}')
            print(f"  Title: {title}")
            print(f"  Current length: {len(current)} chars")
            
            # Build new content: instructions + existing iframe/content
            # Check for existing guide content to avoid duplication
            if 'Kurzanleitung' in current and page_id == 1210:
                print("  Guide already present - replacing for freshness")
                # Remove old block by using only new html
                new_content = html_content.strip()
            elif 'Profi-Niveau' in current and page_id == 1384:
                print("  Guide already present - replacing for freshness")
                new_content = html_content.strip()
            else:
                # Prepend instructions to existing content
                new_content = html_content.strip() + "\n\n" + current
            
            # Edit post
            content_struct = {
                'post_content': new_content,
            }
            result = server.wp.editPost(BLOG_ID, WP_USER, WP_PASS, page_id, content_struct)
            if result:
                print(f"  SUCCESS! Page {page_id} updated (content: {len(new_content)} chars)")
                results[page_id] = True
            else:
                print(f"  FAILED: editPost returned False")
                results[page_id] = False
        except Exception as e:
            print(f"  ERROR: {e}")
            results[page_id] = False
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    for pid, ok in results.items():
        print(f"  Page {pid}: {'✅ SUCCESS' if ok else '❌ FAILED'}")
    
    return all(results.values())


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
