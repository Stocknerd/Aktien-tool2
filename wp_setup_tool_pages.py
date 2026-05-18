#!/usr/bin/env python3
# wp_setup_tool_pages.py – Erstellt dedizierte Landingpages für die Tools auf WordPress

import os, base64, json, requests

# Konfiguration (aus wp_inject_iframes.py übernommen)
WP_BASE_URL   = "https://schatzsuche40.de/wp-json/wp/v2"
WP_USER       = "schatzsuche40"
WP_PASS       = "R33G PRPb mqee hBGc pvKJ 51iz"
TOOL_BASE_URL = "https://tool.schatzsuche40.de"

CREDS = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {CREDS}",
    "Content-Type":  "application/json",
}

PAGES = [
    {
        "title": "Aktien-Analyse Tool",
        "slug": "aktien-tool",  # Nutze den existierenden Slug
        "content": (
            '<!-- wp:paragraph --><p>Nutze unser professionelles Aktien-Analyse Tool, um Kennzahlen, '
            'Analysten-Ratings und Kursziele in einer übersichtlichen Infografik zu visualisieren.</p><!-- /wp:paragraph -->'
            '<!-- wp:html -->\n'
            '<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
            f'<iframe src="{TOOL_BASE_URL}/?embed=1" width="100%" height="850" frameborder="0" '
            'style="border-radius:14px;display:block;" loading="lazy" title="Aktienanalyse Tool"></iframe>'
            '</div>\n<!-- /wp:html -->'
        )
    },
    {
        "title": "Aktien-Vergleichstool",
        "slug": "aktien-vergleichstool",
        "content": (
            '<!-- wp:paragraph --><p>Vergleiche zwei Aktien direkt miteinander. Unser Tool stellt '
            'die wichtigsten Kennzahlen gegenüber und kürt einen Gewinner basierend auf den Fundamentaldaten.</p><!-- /wp:paragraph -->'
            '<!-- wp:html -->\n'
            '<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
            f'<iframe src="{TOOL_BASE_URL}/compare?embed=1" width="100%" height="850" frameborder="0" '
            'style="border-radius:14px;display:block;" loading="lazy" title="Aktien Vergleichstool"></iframe>'
            '</div>\n<!-- /wp:html -->'
        )
    },
    {
        "title": "Aktien-Screener",
        "slug": "screener",
        "content": (
            '<!-- wp:paragraph --><p>Nutze unseren kostenlosen Aktien-Screener, um aus über 4.000 Aktien weltweit die perfekten Werte für dein Portfolio zu finden. Filtere nach KGV, Dividendenrendite, Umsatzwachstum und Marge.</p><!-- /wp:paragraph -->'
            '<!-- wp:html -->\n'
            '<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
            f'<iframe src="{TOOL_BASE_URL}/screener?embed=1" width="100%" height="900" frameborder="0" '
            'style="border-radius:14px;display:block;" loading="lazy" title="Aktien Screener"></iframe>'
            '</div>\n<!-- /wp:html -->'
        )
    },
    {
        "title": "P2P Dashboard",
        "slug": "p2p-dashboard",
        "content": (
            '<!-- wp:paragraph --><p>Vergleiche die besten P2P-Plattformen und berechne dein potenzielles passives Einkommen mit unserem Zinseszins-Rechner.</p><!-- /wp:paragraph -->'
            '<!-- wp:html -->\n'
            '<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
            f'<iframe src="{TOOL_BASE_URL}/p2p?embed=1" width="100%" height="1100" frameborder="0" '
            'style="border-radius:14px;display:block;" loading="lazy" title="P2P Dashboard"></iframe>'
            '</div>\n<!-- /wp:html -->'
        )
    },
    {
        "title": "Dividenden-Rechner",
        "slug": "dividend-rechner",
        "content": (
            '<!-- wp:paragraph --><p>Simuliere und berechne dein passives Dividenden-Einkommen mit deinen Lieblingsaktien und unserem interaktiven Zinseszins-Rechner.</p><!-- /wp:paragraph -->'
            '<!-- wp:html -->\n'
            '<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
            f'<iframe src="{TOOL_BASE_URL}/dividend-rechner?embed=1" width="100%" height="950" frameborder="0" '
            'style="border-radius:14px;display:block;" loading="lazy" title="Dividenden Rechner"></iframe>'
            '</div>\n<!-- /wp:html -->'
        )
    }
]

def setup_pages():
    # Redundante Seite löschen falls vorhanden
    resp = requests.get(f"{WP_BASE_URL}/pages", headers=HEADERS, params={"slug": "aktien-analyse-tool"})
    if resp.status_code == 200 and resp.json():
        pid = resp.json()[0]["id"]
        print(f"[DELETE] Lösche redundante Seite: aktien-analyse-tool (ID: {pid})")
        requests.delete(f"{WP_BASE_URL}/pages/{pid}", headers=HEADERS, params={"force": "true"})

    for p_data in PAGES:
        # Prüfen ob Seite schon existiert
        resp = requests.get(f"{WP_BASE_URL}/pages", headers=HEADERS, params={"slug": p_data["slug"]})
        existing = resp.json() if resp.status_code == 200 else []
        
        if existing:
            page_id = existing[0]["id"]
            print(f"[UPDATE] Seite: {p_data['title']} (ID: {page_id})")
            requests.post(f"{WP_BASE_URL}/pages/{page_id}", headers=HEADERS, json={
                "title": p_data["title"],
                "content": p_data["content"],
                "status": "publish"
            })
        else:
            print(f"[NEW] Erstelle neue Seite: {p_data['title']}")
            requests.post(f"{WP_BASE_URL}/pages", headers=HEADERS, json={
                "title": p_data["title"],
                "slug": p_data["slug"],
                "content": p_data["content"],
                "status": "publish"
            })

if __name__ == "__main__":
    setup_pages()
