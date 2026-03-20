#!/usr/bin/env python3
# wp_inject_iframes.py – Scannt WP-Artikel auf Aktien-Ticker und injiziert iFrame-Blöcke
#
# Verwendung:
#   python wp_inject_iframes.py            (live, schreibt auf WP)
#   python wp_inject_iframes.py --dry-run  (zeigt nur was passieren würde)

import os, re, json, base64, time, argparse
import requests
import pandas as pd

# ─── Konfiguration ──────────────────────────────────────────────────────────────
WP_BASE_URL   = "https://schatzsuche40.de/wp-json/wp/v2"
WP_USER       = "schatzsuche40"
WP_PASS       = "R33G PRPb mqee hBGc pvKJ 51iz"
TOOL_BASE_URL = "https://tool.schatzsuche40.de"
CSV_PATH      = os.path.join(os.path.dirname(__file__), "stock_data.csv")

CREDS = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {CREDS}",
    "Content-Type":  "application/json",
}

# Marker, damit wir keine Dopplungen erzeugen
IFRAME_MARKER        = "tool.schatzsuche40.de"
OLD_IFRAME_MARKER    = "tools.schatzsuche40.de"

# Generische Wörter die zufällig wie Ticker aussehen — nicht einbetten
TICKER_BLACKLIST = {
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "CNY",
    "DE", "US", "UK", "AG", "SE", "NV", "SA", "AB", "AS",
    "ETF", "ETC", "ESG", "KGV", "BIP", "DAX", "TER", "NAV",
    "REF", "TOP", "CEO", "CFO", "CTO", "API", "APP",
    "C",   # "C" allein ist zu kurz/generisch
}

# Findet Tickers in Klammern wie (AAPL) oder (MSFT.DE) oder als alleinstehende CAPS-Wörter
TICKER_PATTERN = re.compile(r'\(([A-Z]{1,6}(?:\.[A-Za-z]{1,4})?)\)')

def load_known_tickers() -> set:
    df = pd.read_csv(CSV_PATH, usecols=["valid_yahoo_ticker"], dtype=str)
    return set(df["valid_yahoo_ticker"].dropna().str.strip())

def make_iframe_block(ticker: str) -> str:
    url = f"{TOOL_BASE_URL}/{ticker}?embed=1"
    return (
        f'\n\n<!-- wp:html -->\n'
        f'<div style="margin:32px 0;border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.12);">'
        f'<iframe src="{url}" width="100%" height="540" frameborder="0" '
        f'style="border-radius:14px;display:block;" loading="lazy" '
        f'title="Aktienanalyse {ticker}"></iframe>'
        f'</div>\n<!-- /wp:html -->'
    )

def process_posts(known_tickers: set, dry_run: bool = False):
    """
    Scannt WP-Artikel. HINWEIS: Auf Wunsch des Nutzers werden keine neuen iFrames mehr 
    unter Blogartikel injiziert (Landingpages werden stattdessen genutzt).
    Dieses Skript dient nun primär der Migration/Reinigung bestehender Inhalte.
    """
    page, updated = 1, 0
    total_checked = 0
    while True:
        resp = requests.get(f"{WP_BASE_URL}/posts", headers=HEADERS, params={
            "per_page": 20, "page": page,
            "_fields": "id,title,link,content",
            "status": "publish"
        })
        if resp.status_code != 200 or not resp.json():
            break

        posts = resp.json()
        for post in posts:
            total_checked += 1
            post_id  = post["id"]
            title    = post["title"]["rendered"]
            content  = post["content"]["rendered"]

            modified = False
            new_content = content

            # Migration 1: Plural tools. -> tool.
            if OLD_IFRAME_MARKER in new_content:
                print(f"  🔄  #{post_id} '{title}' – Migriere tools. -> tool.")
                new_content = new_content.replace(OLD_IFRAME_MARKER, IFRAME_MARKER)
                modified = True

            # Migration 2: Query Params -> Clean URL (/ticker?embed=1)
            # Findet https://tool.schatzsuche40.de/?embed=1&ticker=AAPL
            # Beachte: WP wandelt & in &#038; um
            query_pattern = rf'https://{re.escape(IFRAME_MARKER)}/\?embed=1(?:&#038;|&)ticker=([A-Z0-9.]+)'
            if re.search(query_pattern, new_content):
                print(f"  🖇️  #{post_id} '{title}' – Optimiere URL-Struktur")
                new_content = re.sub(query_pattern, rf'https://{IFRAME_MARKER}/\1?embed=1', new_content)
                modified = True

            if modified:
                if not dry_run:
                    patch = requests.post(f"{WP_BASE_URL}/posts/{post_id}", headers=HEADERS, json={"content": new_content})
                    if patch.status_code == 200:
                        updated += 1
                        print(f"       → Update erfolgreich (HTTP 200)")
                    else:
                        print(f"       ❌ Update Fehler: {patch.text[:200]}")
                    time.sleep(0.4)
                else:
                    print(f"       [DRY-RUN] Würde Content updaten")
                    updated += 1
                continue

            # Skip if already has correct iframe
            if IFRAME_MARKER in content:
                # Aber nur wenn es schon die neue Struktur hat (wurde oben geprüft)
                print(f"  ⏭  #{post_id} '{title}' – iFrame vorhanden, skip")
                continue

            # Suche Ticker in Klammern im Text oder Titel
            text_to_search = re.sub(r'<[^>]+>', ' ', content + " " + title)
            found_tickers = []
            for m in TICKER_PATTERN.finditer(text_to_search):
                cand = m.group(1).upper()
                if cand in known_tickers and cand not in found_tickers and cand not in TICKER_BLACKLIST:
                    found_tickers.append(cand)

            # Fallback: Suche nach bekannten Aktiennamen im Text
            NAME_TO_TICKER = {
                "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN",
                "Alphabet": "GOOGL", "Google": "GOOGL", "Meta": "META",
                "Tesla": "TSLA", "NVIDIA": "NVDA", "Nvidia": "NVDA",
                "SAP": "SAP.DE", "Siemens": "SIE.DE", "Allianz": "ALV.DE",
                "Deutsche Bank": "DBK.DE", "BMW": "BMW.DE",
                "Volkswagen": "VOW3.DE", "BASF": "BAS.DE",
                "Daimler": "MBG.DE", "Mercedes": "MBG.DE",
                "Bayer": "BAYN.DE", "Adidas": "ADS.DE",
            }
            for name, ticker in NAME_TO_TICKER.items():
                if ticker and name in text_to_search and ticker not in found_tickers and ticker in known_tickers and ticker not in TICKER_BLACKLIST:
                    found_tickers.append(ticker)

            # found_tickers = found_tickers[:2]
            if not found_tickers:
                # print(f"  - #{post_id} '{title}' - keine Ticker gefunden")
                continue

            # ABBRUCH: Nutzer möchte keine Tools mehr unter Blogartikeln.
            # Landingpages (siehe wp_setup_tool_pages.py) werden stattdessen genutzt.
            print(f"  - #{post_id} '{title}' - Ticker gefunden ({found_tickers}), aber Injection deaktiviert.")
            continue
            
            if len(found_tickers) == 2:
                # Comparison mode
                t1, t2 = found_tickers
                url = f"{TOOL_BASE_URL}/compare?t1={t1}&t2={t2}&auto=1&embed=1"
                iframe_block = (
                    f'\n\n<!-- wp:html -->\n'
                    f'<div style="margin:32px 0;border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.12);">'
                    f'<iframe src="{url}" width="100%" height="640" frameborder="0" '
                    f'style="border-radius:14px;display:block;" loading="lazy" '
                    f'title="Aktienvergleich {t1} vs {t2}"></iframe>'
                    f'</div>\n<!-- /wp:html -->'
                )
                new_content = content + iframe_block
            else:
                # Single stock mode
                iframes = "".join(make_iframe_block(t) for t in found_tickers)
                new_content = content + iframes

            if not dry_run:
                patch = requests.post(
                    f"{WP_BASE_URL}/posts/{post_id}",
                    headers=HEADERS,
                    json={"content": new_content}
                )
                status = patch.status_code
                if status == 200:
                    updated += 1
                    print(f"       → Gespeichert (HTTP {status})")
                else:
                    print(f"       ❌ Fehler HTTP {status}: {patch.text[:200]}")
                time.sleep(0.4)
            else:
                print(f"       [DRY-RUN] Würde {len(found_tickers)} iFrame(s) einbetten")
                updated += 1

        page += 1

    action = "identifiziert" if dry_run else "aktualisiert"
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Fertig – {total_checked} Posts geprüft, {updated} {action}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WordPress iFrame Injector for Stock Tools")
    parser.add_argument("--dry-run", action="store_true", help="Keine Änderungen vornehmen")
    args = parser.parse_args()

    print(f"Lade bekannte Ticker aus stock_data.csv…")
    known = load_known_tickers()
    print(f"  → {len(known)} Ticker geladen\n")
    print(f"Scanne WordPress ({'DRY-RUN' if args.dry_run else 'LIVE'})…\n")
    process_posts(known, dry_run=args.dry_run)
