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

def make_iframe_block(slug, title, height):
    iframe_id = f"iframe-{slug}"
    url = f"{TOOL_BASE_URL}/?embed=1" if slug == "aktien-tool" else f"{TOOL_BASE_URL}/{slug}?embed=1"
    if slug == "aktien-vergleichstool":
        url = f"{TOOL_BASE_URL}/compare?embed=1"
        
    css_fix = (
        '<style>\n'
        '.entry-content { margin-top: 80px !important; }\n'
        '@media (max-width: 768px) { .entry-content { margin-top: 100px !important; } }\n'
        'header, .site-header, #masthead, .navigation-bar, .main-navigation, .sticky-header {\n'
        '    background-color: #0B1E21 !important;\n'
        '    opacity: 1 !important;\n'
        '    z-index: 9999 !important;\n'
        '}\n'
        '/* Full-width container overrides for Betheme */\n'
        '.entry-content .section_wrapper,\n'
        '.entry-content .container,\n'
        '.entry-content .the_content_wrapper {\n'
        '    max-width: 100% !important;\n'
        '    width: 100% !important;\n'
        '    padding-left: 0 !important;\n'
        '    padding-right: 0 !important;\n'
        '    margin-left: 0 !important;\n'
        '    margin-right: 0 !important;\n'
        '}\n'
        '</style>\n'
    )
    
    return (
        css_fix +
        f'<!-- wp:html -->\n'
        f'<div style="margin:24px 0;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.1);">'
        f'<iframe id="{iframe_id}" src="{url}" width="100%" height="{height}" frameborder="0" '
        f'style="border-radius:14px;display:block;min-height:450px;transition:height 0.2s ease;" loading="lazy" title="{title}"></iframe>'
        f'</div>\n'
        f'<script>\n'
        f'(function() {{\n'
        f'    var iframe = document.getElementById("{iframe_id}");\n'
        f'    if (iframe) {{\n'
        f'        var parentParams = window.location.search;\n'
        f'        if (parentParams) {{\n'
        f'            var currentSrc = iframe.src;\n'
        f'            if (currentSrc.indexOf("?") !== -1) {{\n'
        f'                iframe.src = currentSrc + "&" + parentParams.substring(1);\n'
        f'            }} else {{\n'
        f'                iframe.src = currentSrc + parentParams;\n'
        f'            }}\n'
        f'        }}\n'
        f'    }}\n'
        f'    window.addEventListener("message", function(e) {{\n'
        f'        if (e.data && e.data.type === "setHeight" && e.data.height) {{\n'
        f'            var ifr = document.getElementById("{iframe_id}");\n'
        f'            if (ifr) {{\n'
        f'                ifr.style.height = e.data.height + "px";\n'
        f'            }}\n'
        f'        }}\n'
        f'    }});\n'
        f'}})();\n'
        f'</script>\n'
        f'<!-- /wp:html -->'
    )

PAGES = [
    {
        "title": "Aktien-Analyse Tool",
        "slug": "aktien-tool",
        "content": (
            '<!-- wp:html -->\n'
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "SoftwareApplication",\n'
            '  "name": "Schatzsuche 4.0 Aktien-Analyse Tool",\n'
            '  "operatingSystem": "All",\n'
            '  "applicationCategory": "FinancialApplication",\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "0.00",\n'
            '    "priceCurrency": "EUR"\n'
            '  },\n'
            '  "description": "Erstelle interaktive Aktien-Infografiken mit über 30 fundamentalen Kennzahlen und KI-gestütztem Sentiment in Sekunden."\n'
            '}\n'
            '</script>\n'
            '<!-- /wp:html -->\n'
            '<!-- wp:paragraph --><p>Nutze unser professionelles Aktien-Analyse Tool, um Kennzahlen, '
            'Analysten-Ratings und Kursziele in einer übersichtlichen Infografik zu erhalten. Gib einfach das Tickersymbol ein und erhalte sofort ein umfassendes Bild.</p><!-- /wp:paragraph -->'
            + make_iframe_block("aktien-tool", "Aktienanalyse Tool", 950) +
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Professionelle Aktienanalyse leicht gemacht</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Eine fundierte Aktienanalyse ist die Grundlage für jeden langfristig erfolgreichen Vermögensaufbau. Mit unserem interaktiven Aktien-Bild Generator musst du nicht mehr mühsam Geschäftsberichte und Excel-Tabellen durchsuchen. Unser Tool bereitet über 30 fundamentale Kennzahlen wie KGV, Dividendenrendite, EBIT-Marge und Gewinnwachstum visuell ansprechend auf.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Die wichtigsten Kennzahlen zur Aktienbewertung</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:list -->\n'
            '<ul>\n'
            '  <li><strong>Kurs-Gewinn-Verhältnis (KGV):</strong> Zeigt an, wie günstig oder teuer eine Aktie im Verhältnis zu ihrem aktuellen Gewinn bewertet ist.</li>\n'
            '  <li><strong>Ausschüttungsquote:</strong> Wie viel Prozent des Gewinns werden als Dividende an die Aktionäre gezahlt? Eine gesunde Quote liegt zwischen 30% und 60%.</li>\n'
            '  <li><strong>EBIT-Marge:</strong> Ein Maß für die operative Profitabilität des Unternehmens. Je höher, desto widerstandsfähiger ist das Geschäftsmodell.</li>\n'
            '</ul>\n'
            '<!-- /wp:list -->\n'
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Häufig gestellte Fragen (FAQ)</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Wie funktioniert die KI-Aktienbewertung?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Unser Tool nutzt ein hochentwickeltes KI-Modell (GPT-5.4), um die Fundamentaldaten, Analystenziele und das Sentiment in Sekundenschnelle zu analysieren. Du erhältst eine objektive, datenbasierte Einschätzung zur aktuellen Bewertung der Aktie.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Sind die generierten Grafiken für Social Media geeignet?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Ja, absolut! Das Layout ist optimiert für den PNG-Export im 1:1 Quadratformat – perfekt für Instagram, LinkedIn oder deinen eigenen Blog. Du kannst die Infografik mit einem Klick herunterladen.</p>\n'
            '<!-- /wp:paragraph -->'
        )
    },
    {
        "title": "Aktien-Vergleichstool",
        "slug": "aktien-vergleichstool",
        "content": (
            '<!-- wp:html -->\n'
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "SoftwareApplication",\n'
            '  "name": "Schatzsuche 4.0 Aktien-Vergleichstool",\n'
            '  "operatingSystem": "All",\n'
            '  "applicationCategory": "FinancialApplication",\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "0.00",\n'
            '    "priceCurrency": "EUR"\n'
            '  },\n'
            '  "description": "Vergleiche zwei Aktientitel direkt auf einen Blick hinsichtlich Bewertung, Profitabilität und Dividendenstärke."\n'
            '}\n'
            '</script>\n'
            '<!-- /wp:html -->\n'
            '<!-- wp:paragraph --><p>Vergleiche zwei Aktien direkt miteinander. Unser Tool stellt '
            'die wichtigsten Kennzahlen gegenüber und kürt einen Gewinner basierend auf den Fundamentaldaten.</p><!-- /wp:paragraph -->'
            + make_iframe_block("aktien-vergleichstool", "Aktien Vergleichstool", 1800) +
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Zwei Aktien direkt vergleichen und analysieren</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Wer vor der Wahl steht, eine Aktie wie Apple oder Microsoft, Allianz oder Münchener Rück zu kaufen, benötigt einen klaren Fundamentaldaten-Vergleich. Unser Aktien-Vergleichstool stellt die wichtigsten Kennzahlen von zwei Unternehmen direkt nebeneinander dar, um dir die Kaufentscheidung zu erleichtern.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Welche Faktoren werden verglichen?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:list -->\n'
            '<ul>\n'
            '  <li><strong>Rentabilität:</strong> EBIT-Marge, Eigenkapitalrendite und Nettomarge im direkten Duell.</li>\n'
            '  <li><strong>Bewertung:</strong> Vergleich von KGV, KUV und KBV, um teure Überbewertungen systematisch zu vermeiden.</li>\n'
            '  <li><strong>Dividendenstärke:</strong> Wer bietet die sicherere Einstiegsrendite und die nachhaltigere Ausschüttungsquote?</li>\n'
            '</ul>\n'
            '<!-- /wp:list -->\n'
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Häufig gestellte Fragen (FAQ)</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Wer gewinnt das Aktienduell?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Unser Algorithmus berechnet einen Gesamt-Score basierend auf 12 verschiedenen Kriterien aus Bewertung, Profitabilität und Wachstum. Das Unternehmen mit den besseren Fundamentaldaten wird als Sieger des Duells gekürt.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Kann ich auch internationale Aktien vergleichen?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Ja, du kannst jede Aktie eingeben, die in unserer Datenbank erfasst ist. Das Tool unterstützt über 4.000 Werte aus allen wichtigen globalen Indizes.</p>\n'
            '<!-- /wp:paragraph -->'
        )
    },
    {
        "title": "Aktien-Screener",
        "slug": "screener",
        "content": (
            '<!-- wp:html -->\n'
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "SoftwareApplication",\n'
            '  "name": "Schatzsuche 4.0 Aktien-Screener",\n'
            '  "operatingSystem": "All",\n'
            '  "applicationCategory": "FinancialApplication",\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "0.00",\n'
            '    "priceCurrency": "EUR"\n'
            '  },\n'
            '  "description": "Filtere tausende weltweite Aktien nach Marktkapitalisierung, KGV, Dividendenrendite, Margen und Wachstum."\n'
            '}\n'
            '</script>\n'
            '<!-- /wp:html -->\n'
            '<!-- wp:paragraph --><p>Nutze unseren kostenlosen Aktien-Screener, um aus über 4.000 Aktien weltweit die perfekten Werte für dein Portfolio zu finden. Filtere nach KGV, Dividendenrendite, Umsatzwachstum und Marge.</p><!-- /wp:paragraph -->'
            + make_iframe_block("screener", "Aktien Screener", 1100) +
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Aktien-Screener: Finde die besten Aktien weltweit</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Mit unserem High-Speed Aktien-Screener filterst du über 4.000 weltweite Aktien in Echtzeit. Stelle einfach deine Kriterien ein und filtere nach Marktkapitalisierung, KGV, Dividendenrendite, Umsatzwachstum und Margen.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Beliebte Suchstrategien im Screener</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:list -->\n'
            '<ul>\n'
            '  <li><strong>Dividendenwachstum:</strong> Filtere nach Dividendenrendite &ge; 1.5%, Payout Ratio &le; 60% und Umsatzwachstum &ge; 5%. Erfahre mehr in unserem exklusiven <a href="https://schatzsuche40.de/dividendenwachstum-strategie-guide/">Dividendenwachstum-Strategie Guide</a>.</li>\n'
            '  <li><strong>Value Investing:</strong> KGV &le; 15, KBV &le; 2 und Nettomarge &ge; 10%. So findest du unterbewertete Substanzwerte.</li>\n'
            '  <li><strong>High-Growth:</strong> Umsatzwachstum &ge; 15% und positive operative Marge für dynamische Wachstumsaktien.</li>\n'
            '</ul>\n'
            '<!-- /wp:list -->\n'
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Häufig gestellte Fragen (FAQ)</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Werden Währungen im Screener umgerechnet?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Ja, absolut. Um eine verlässliche Filterung nach der Marktkapitalisierung zu garantieren, werden alle 44 Währungen (wie TWD, EUR, GBP, ZAR) im Hintergrund automatisch zum aktuellen Wechselkurs in US-Dollar (USD) umgerechnet.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Wie oft werden die Screener-Daten aktualisiert?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Unsere Aktiendaten werden täglich vollautomatisch aus den globalen Märkten geladen und aktualisiert. So arbeitest du immer mit frischen Bewertungs-Multiples und Kurszielen.</p>\n'
            '<!-- /wp:paragraph -->'
        )
    },
    {
        "title": "P2P Dashboard",
        "slug": "p2p-dashboard",
        "content": (
            '<!-- wp:html -->\n'
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "SoftwareApplication",\n'
            '  "name": "Schatzsuche 4.0 P2P Dashboard",\n'
            '  "operatingSystem": "All",\n'
            '  "applicationCategory": "FinancialApplication",\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "0.00",\n'
            '    "priceCurrency": "EUR"\n'
            '  },\n'
            '  "description": "Analysiere und vergleiche Renditen, Rückkaufgarantien und Risiken führender europäischer P2P-Plattformen."\n'
            '}\n'
            '</script>\n'
            '<!-- /wp:html -->\n'
            '<!-- wp:paragraph --><p>Vergleiche die besten P2P-Plattformen und berechne dein potenzielles passives Einkommen mit unserem Zinseszins-Rechner.</p><!-- /wp:paragraph -->'
            + make_iframe_block("p2p", "P2P Dashboard", 1100) +
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Die besten P2P Plattformen im Rendite-Vergleich</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>P2P-Kredite (Privatkredite) bieten eine hervorragende Möglichkeit, ein monatliches passives Einkommen abseits der Börse aufzubauen. Unser P2P-Dashboard vergleicht führende europäische Plattformen wie Mintos, Bondora, PeerBerry und Estateguru hinsichtlich ihrer Konditionen.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Worauf sollte man beim P2P-Investing achten?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:list -->\n'
            '<ul>\n'
            '  <li><strong>Rendite:</strong> Typische Zinssätze liegen zwischen 9% und 14% pro Jahr.</li>\n'
            '  <li><strong>Rückkaufgarantie (Buyback Obligation):** Schützt dein Kapital, falls ein Kreditnehmer ausfällt.</li>\n'
            '  <li><strong>Diversifikation:</strong> Verteile deine Investitionen über mehrere Anbahnungspartner, Kreditarten und Länder.</li>\n'
            '</ul>\n'
            '<!-- /wp:list -->\n'
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Häufig gestellte Fragen (FAQ)</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Wie funktioniert der Zinseszins-Rechner im Dashboard?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Trage einfach dein Startkapital, die geplante monatliche Sparrate und den erwarteten Zinssatz ein. Der Rechner simuliert das Wachstum deines P2P-Portfolios über die Jahre hinweg.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Sind P2P-Kredite risikolos?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Nein, P2P-Investments sind mit Risiken wie dem Plattform-Ausfall oder dem Ausfall des Kreditvermittlers verbunden. Investiere daher nur Kapital, auf das du im Notfall verzichten kannst, und streue breit.</p>\n'
            '<!-- /wp:paragraph -->'
        )
    },
    {
        "title": "Dividenden-Rechner",
        "slug": "dividend-rechner",
        "content": (
            '<!-- wp:html -->\n'
            '<script type="application/ld+json">\n'
            '{\n'
            '  "@context": "https://schema.org",\n'
            '  "@type": "SoftwareApplication",\n'
            '  "name": "Schatzsuche 4.0 Dividenden-Rechner",\n'
            '  "operatingSystem": "All",\n'
            '  "applicationCategory": "FinancialApplication",\n'
            '  "offers": {\n'
            '    "@type": "Offer",\n'
            '    "price": "0.00",\n'
            '    "priceCurrency": "EUR"\n'
            '  },\n'
            '  "description": "Simuliere die langfristige Entwicklung deines Portfolios durch monatliche Sparraten und reinvestierte Dividenden."\n'
            '}\n'
            '</script>\n'
            '<!-- /wp:html -->\n'
            '<!-- wp:paragraph --><p>Simuliere und berechne dein passives Dividenden-Einkommen mit deinen Lieblingsaktien und unserem interaktiven Zinseszins-Rechner.</p><!-- /wp:paragraph -->'
            + make_iframe_block("dividend-rechner", "Dividenden Rechner", 950) +
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Dividenden-Rechner: Zinseszins & Cashflow simulieren</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Berechne dein zukünftiges passives Einkommen mit unserem interaktiven Dividendenrechner. Simuliere, wie sich monatliche Sparraten, Dividendenerhöhungen und konsequente Reinvestitionen langfristig auf dein Vermögen auswirken.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Die Kraft des Zinseszinses (Dividenden-Compounding)</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:list -->\n'
            '<ul>\n'
            '  <li><strong>Regelmäßige Sparrate:</strong> Kontinuierliches Ansparen beschleunigt das Depotwachstum exponentiell.</li>\n'
            '  <li><strong>Dividendenwachstum:</strong> Erhöht deine Yield on Cost über die Jahre hinweg automatisch. Erfahre mehr dazu in unserem <a href="https://schatzsuche40.de/dividendenwachstum-strategie-guide/">Dividendenwachstum-Leitfaden</a>.</li>\n'
            '  <li><strong>Konsequente Reinvestition (DRIP):</strong> Der Zinseszinseffekt entfaltet seine volle Stärke, wenn du erhaltene Dividenden sofort wieder in neue Anteile anlegst.</li>\n'
            '</ul>\n'
            '<!-- /wp:list -->\n'
            '<!-- wp:heading {"level":2} -->\n'
            '<h2 class="wp-block-heading">Häufig gestellte Fragen (FAQ)</h2>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Wie nutze ich den Dividenden-Rechner für mein Depot?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Trage einfach deine geplante Einmalsumme, die monatliche Sparrate, die erwartete Dividendenrendite und das jährliche Dividendenwachstum ein. Das Tool zeigt dir die Entwicklung deiner monatlichen Ausschüttungen über 10, 20 und 30 Jahre.</p>\n'
            '<!-- /wp:paragraph -->\n'
            '<!-- wp:heading {"level":3} -->\n'
            '<h3 class="wp-block-heading">Was bedeutet die persönliche Dividendenrendite (Yield on Cost)?</h3>\n'
            '<!-- /wp:heading -->\n'
            '<!-- wp:paragraph -->\n'
            '<p>Die Yield on Cost beschreibt deine persönliche Dividendenrendite bezogen auf deinen ursprünglichen Kaufpreis. Steigert eine Aktie ihre Dividende über Jahre hinweg, steigt deine persönliche Rendite auf das investierte Kapital massiv an – oft weit über die am Markt sichtbare Rendite hinaus.</p>\n'
            '<!-- /wp:paragraph -->'
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
