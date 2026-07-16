#!/usr/bin/env python3
import os
import sys
import time
import random
import argparse
import math
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path to allow importing from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import BASE_DIR, COLORS, COLORS_HEX
from src.graphic_generator import render_viral_list, render_dividend_calendar, render_pure_ai_infographic
from src.reel_generator import build_reel_mp4
from src.content_generator import generate_structured_content
from src.content_strategy import PRIORITY_EVERGREEN_TOPICS, choose_automated_topic
from src.canva_packet import create_personal_canva_packet_from_json
from src.news_sources import (
    filter_fresh_headlines,
    first_news_title,
    format_news_context,
    parse_rss_headlines,
)
from src.youtube_uploader import upload_video as youtube_upload_video

from src.publishing_safety import (
    content_dispatch_allowed,
    dispatch_or_prepare,
    external_transfer_enabled,
    review_metadata_for_content,
    validate_calendar_entries,
)
from core import render_stock_card, render_compare, CSV_FILE
from ai_logic import get_tool_promotion_caption, get_ai_verdict, get_ai_comparison_verdict
from social_publisher import (
    live_public_dispatch_enabled,
    post_facebook_reel,
    post_instagram_reel,
    run_social_sync,
    save_for_manual_upload,
)

## A deep and structured list of 80 evergreen financial topics for Track 3 (AI Infographics)
EVERGREEN_FINANCIAL_TOPICS = [
    # --- ETFs & Passive Investing ---
    "Zinseszins: Warum Zeit dein größter Hebel an der Börse ist",
    "Warum breit gestreute ETFs die beste Basis für dein Depot sind",
    "Was ist der Unterschied zwischen Ausschüttend und Thesaurierend?",
    "Was ist ein MSCI World und warum kennt ihn jeder Anleger?",
    "Der Cost-Average-Effekt: Warum fallende Kurse auch Chancen sind",
    "ETFs im Sparplan: Warum du auch in einer Korrektur weiterkaufen solltest",
    "All-World-ETFs: Reicht ein einziger ETF für die Altersvorsorge?",
    "Was ist der MSCI Emerging Markets und warum gehört er ins Depot?",
    "Sektor-ETFs vs. Welt-ETFs: Warum Spezialisierung oft Underperformance bringt",
    "Die besten Dividenden-ETFs für regelmäßigen passiven Cashflow",
    "Was sind synthetische vs. physische ETFs? Replikation einfach erklärt",
    "Core-Satellite-Strategie: So baust du ein stabiles Depot mit Rendite-Kick auf",
    
    # --- Stock Analysis & Metrics ---
    "Einzelaktien vs. ETFs: Das sind die Vor- und Nachteile",
    "Was ist das KGV? Die wichtigste Aktienkennzahl richtig verstehen",
    "Die Ausschüttungsquote: Warum sie wichtiger ist als die Dividendenrendite",
    "Was ist der Free Cashflow und warum ist er wichtiger als der Gewinn?",
    "KBV & KUV: Wie du Substanzwerte und Wachstumsaktien bewertest",
    "PEG-Ratio: So erkennst du, ob eine Wachstumsaktie überteuert ist",
    "Eigenkapitalrendite & RoA: Wie profitabel wirtschaftet ein Unternehmen?",
    "Was sind Aktienrückkäufe und warum treiben sie den Kurs?",
    "Was passiert bei einem Aktiensplit? Am Beispiel von Nvidia & Apple",
    "Value vs. Growth Investing: Der ewige Kampf der Investment-Stile",
    "Zyklische vs. Nicht-zyklische Aktien: So machst du dein Depot krisenfest",
    "Die 3 wichtigsten Bilanz-Kennzahlen, die jeder Investor kennen muss",
    
    # --- Dividend Strategies ---
    "Dividenden-Wachstum vs. High-Yield: Was ist besser für Cashflow?",
    "Wie du deine Dividenden reinvestierst für maximales Wachstum",
    "Die Macht der Dividenden: Historischer Treiber des Aktienmarkts",
    "5 Dividenden-Aristokraten, die seit über 25 Jahren ihre Ausschüttung steigern",
    "Dividenden-Fallen: Warum eine extrem hohe Dividendenrendite gefährlich ist",
    "Was ist ein Dividenden-König? Die Elite der Dividenden-Zahler",
    "Ex-Tag vs. Zahltag: Wie Dividendentermine genau funktionieren",
    "Dividenden-Adel in Deutschland: Die zuverlässigsten DAX-Zahler",
    
    # --- Financial Psychology & Traps ---
    "3 typische Anfänger-Fehler an der Börse und wie du sie vermeidest",
    "Psychologie an der Börse: Warum Panikverkäufe dich Rendite kosten",
    "Warum Market Timing scheitert: Time in the market beats timing the market",
    "Der Home Bias: Warum zu viele deutsche Aktien im Depot deine Rendite bremsen",
    "Fear of Missing Out (FOMO): Warum Hype-Aktien oft im Verlust enden",
    "Verlustaversion: Warum es uns so schwerfällt, Verlierer-Aktien zu verkaufen",
    "Die Illusion der Sicherheit: Warum Tagesgeld langfristig Kaufkraft raubt",
    "Gier vs. Angst: Wie du deine Emotionen beim Investieren ausschaltest",
    
    # --- Personal Finance & Budgeting ---
    "Warum der Notgroschen immer vor dem Investieren stehen muss",
    "Sparquote erhöhen: 3 Hebel, um monatlich mehr zu investieren",
    "Wie viel Geld braucht man zum Starten? Depotaufbau ab 25 Euro",
    "Die 50-30-20 Regel: Das einfachste System für deine Budgetplanung",
    "Die Macht der Gewohnheit: Wie automatisierte Sparpläne dein Leben verändern",
    "Konsumschulden abbauen: Der schnellste Weg in die finanzielle Freiheit",
    "Finanzielle Freiheit: Die 4%-Regel und wie viel Vermögen du brauchst",
    "Frugalismus: Wie man mit bewusstem Verzicht extrem viel spart",
    "Die 72er-Regel: Wie schnell verdoppelt sich dein Investment?",
    "Haushaltsbuch führen: Der Gamechanger für deine Finanzen",
    "Lifestyle Inflation: Warum mehr Gehalt oft nicht mehr Vermögen bedeutet",
    
    # --- Macroeconomics & News ---
    "Wie Inflation dein Erspartes entwertet und wie Aktien schützen",
    "Warum Zinsentscheidungen der Fed und EZB deine Aktienkurse bewegen",
    "Was ist die Schuldengrenze der USA und warum betrifft sie dein Depot?",
    "Der Leitzins: Wie Zentralbanken die Wirtschaft steuern",
    "Was ist eine Rezession und wie verhält man sich als Investor?",
    "Anleihen vs. Aktien: Was bedeutet die Zinswende für Anleger?",
    "Kryptowährungen vs. Aktien: Was unterscheidet Bitcoin vom Sachwert Aktie?",
    "Gold als sicherer Hafen? Vor- und Nachteile des Edelmetalls",
    
    # --- Tax Hacks & Brokerage ---
    "Steuern auf Kapitalerträge in Deutschland kurz erklärt",
    "Der Freistellungsauftrag: Wie du 1.000€ Kapitalerträge steuerfrei stellst",
    "Die geheimen Kosten beim Aktienkauf: Spread, Ordergebühren & Steuern",
    "Neobroker vs. Filialbank: Wo du die meisten Gebühren sparst",
    "Depotübertrag: So wechselst du einfach und kostenlos deinen Broker",
    "Nichtveranlagungsbescheinigung (NV): Steuern sparen für Studenten & Rentner",
    "Quellensteuer zurückfordern: So vermeidest du Doppelbesteuerung im Ausland",
    "Rebalancing im Depot: Warum du Gewinner stutzen und Verlierer aufbauen musst",
    "Sparer-Pauschbetrag ausnutzen: Der Steuertrick am Jahresende",
    "Kinderdepot eröffnen: So sparst du Steuern für deine Kinder",
    "Aktien im Betriebsvermögen: Wann lohnt sich eine vermögensverwaltende GmbH?"
]

# Backward-compatible name for old diagnostics; the runtime and legacy helpers
# both consume the same performance-based, family-finance-focused topic pool.
EVERGREEN_FINANCIAL_TOPICS = list(PRIORITY_EVERGREEN_TOPICS)

def fetch_current_market_news() -> str:
    """Fetch and parse current Boerse Frankfurt RSS headlines with source metadata."""
    import requests

    url = "https://api.boerse-frankfurt.de/v1/feeds/news.rss"
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        items = parse_rss_headlines(response.content, limit=12)
        fresh_items = filter_fresh_headlines(items, max_age_hours=48)
        if not fresh_items:
            print("TREND DETECTOR: No fresh, dated HTTPS headlines passed validation.")
            return ""
        return format_news_context(fresh_items)
    except Exception as error:
        print(f"TREND DETECTOR: Warning: Failed to fetch current market news: {error}")
        return ""

def get_dynamic_trending_topic(news_context: str | None = None) -> str | None:
    """Select the first already-validated source headline without another model call."""

    context = news_context or fetch_current_market_news()
    if not context:
        print("TREND DETECTOR: No sourced headlines available; using curated evergreen fallback.")
        return None
    topic = first_news_title(context)
    if not topic:
        print("TREND DETECTOR: Source context was invalid; using curated evergreen fallback.")
        return None
    return topic

def load_stock_database():
    """Loads the main stock CSV database."""
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"Stock database not found at {CSV_FILE}")
    return pd.read_csv(CSV_FILE)

def run_track_stock():
    """
    Track 1: Stock Cards or Duels (Daily at 12:00 PM).
    Generates a high-contrast stock card or peer duel, renders a Silent Reel
    (zoom animation + music), and publishes it to all social channels.
    """
    print("🚀 TRACK 1: RUNNING DAILY STOCK CARD / DUEL PIPELINE...")
    
    df = load_stock_database()
    
    # Sort by Market Cap to get high-quality tickers
    if 'Market Cap' in df.columns:
        df['Market_Cap_Num'] = pd.to_numeric(df['Market Cap'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        top_100 = df.dropna(subset=['Symbol', 'Security', 'KGV']).sort_values(by='Market_Cap_Num', ascending=False).head(100)
    else:
        top_100 = df.dropna(subset=['Symbol', 'Security', 'KGV']).head(100)
        
    if top_100.empty:
        print("Error: Could not load top stocks.")
        return False
        
    is_comparison = random.choice([True, False])
    public_dir = os.path.join(BASE_DIR, "static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def extract_financial_data(row):
        return {
            "KGV": str(row.get("KGV", "N/A")),
            "Dividendenrendite": str(row.get("Dividendenrendite", "N/A")),
            "Umsatzwachstum 3J": str(row.get("Umsatzwachstum 3J (erwartet)", "N/A")),
            "EK-Rendite": str(row.get("Eigenkapitalrendite", "N/A")),
            "Nettomarge": str(row.get("Nettomarge", "N/A"))
        }

    if is_comparison:
        print("STOCK TRACK: Duel mode selected!")
        row_a_series = top_100.sample(n=1).iloc[0]
        sym_a = str(row_a_series.get('Symbol'))
        name_a = str(row_a_series.get('Security'))
        sect_a = row_a_series.get('Sektor')
        
        # Look for a peer in the same sector
        peers_top = top_100[(top_100['Sektor'] == sect_a) & (top_100['Symbol'] != sym_a)]
        if not peers_top.empty:
            row_b_series = peers_top.sample(n=1).iloc[0]
        else:
            peers_all = df[(df['Sektor'] == sect_a) & (df['Symbol'] != sym_a) & df['KGV'].notna()]
            if not peers_all.empty:
                row_b_series = peers_all.sample(n=1).iloc[0]
            else:
                fallback_peers = top_100[top_100['Symbol'] != sym_a]
                row_b_series = fallback_peers.sample(n=1).iloc[0]
                
        row_a = row_a_series.to_dict()
        row_b = row_b_series.to_dict()
        
        sym_b, name_b = str(row_b.get('Symbol')), str(row_b.get('Security'))
        print(f"Duel Matchup: {name_a} ({sym_a}) vs {name_b} ({sym_b})")
        
        fin_a = extract_financial_data(row_a)
        fin_b = extract_financial_data(row_b)
        verdict = get_ai_comparison_verdict(sym_a, name_a, fin_a, sym_b, name_b, fin_b)
        
        # Draw image
        img = render_compare([row_a, row_b], ai_verdict=verdict)
        
        names = f"{name_a} vs {name_b}"
        symbols = f"{sym_a} vs {sym_b}"
        fin_texts = f"{name_a}: {fin_a}\n{name_b}: {fin_b}"
        
        comment_text = (
            "👉 Vergleiche selbst deine Lieblingsaktien in unserem interaktiven Vergleichstool:\n"
            "https://compare.schatzsuche40.de/\n\n"
            "Analysiere über 4.000 Aktien im Screener auf schatzsuche40.de! 📈"
        )
        
        image_filename = f"comparison_{sym_a}_{sym_b}_{timestamp}.png"
        video_filename = f"comparison_{sym_a}_{sym_b}_{timestamp}.mp4"
    else:
        print("STOCK TRACK: Single check mode selected!")
        candidate = top_100.sample(n=1).iloc[0]
        sym, name = str(candidate.get('Symbol')), str(candidate.get('Security'))
        print(f"Stock Pick: {name} ({sym})")
        
        fin = extract_financial_data(candidate)
        verdict = get_ai_verdict(sym, name, fin)
        
        img = render_stock_card(candidate, None, fetch_analyst=True, ai_verdict=verdict)
        
        names = name
        symbols = sym
        fin_texts = str(fin)
        
        comment_text = (
            "👉 Analysiere diese Aktie interaktiv in unserem Aktien-Screener:\n"
            "https://tool.schatzsuche40.de/\n\n"
            "Dividenden-Termine findest du im Kalender auf schatzsuche40.de! 💰"
        )
        
        image_filename = f"single_{sym}_{timestamp}.png"
        video_filename = f"single_{sym}_{timestamp}.mp4"
        
    image_path = os.path.join(public_dir, image_filename)
    video_path = os.path.join(public_dir, video_filename)
    
    img.save(image_path)
    print(f"STOCK TRACK: Image saved at {image_path}")
    
    caption = get_tool_promotion_caption(is_comparison, names, symbols, fin_texts)
    
    # 3. Publish
    print("STOCK TRACK: Publishing to social platforms...")
    
    # Image to all standard socials (X, FB, Pinterest, and Instagram Feed!)
    run_social_sync(
        symbol=symbols,
        caption=caption,
        image_path=image_path,
        blog_url="https://schatzsuche40.de",
        wp_img_url=None,
        title=names,
        comment_text=comment_text,
        skip_instagram=False,
        strip_links_on_x=True
    )
    
    print("STOCK TRACK: Reel video and YouTube Shorts uploads disabled to focus on high-engagement feed posts.")
    
    print("✅ TRACK 1 STOCK CARD PIPELINE COMPLETED SUCCESSFULLY!")
    return True

def run_track_calendar():
    """
    Track 2: Dividend Calendar (weekly).
    Filters complete sourced ex-dividend rows, renders a 2x3 grid and prepares
    or publishes the feed image through the central gate.
    """
    print("🚀 TRACK 2: RUNNING WEEKLY DIVIDEND CALENDAR PIPELINE...")
    
    df = load_stock_database()
    public_dir = os.path.join(BASE_DIR, "static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Filter upcoming ex-dividend dates
    payouts = []
    if "Ex-Dividenden-Datum" in df.columns:
        # Filter rows with valid ex-date and symbol
        df_div = df.dropna(subset=["valid_yahoo_ticker", "Ex-Dividenden-Datum"]).copy()
        
        # Sort out future ex-dates
        heute = datetime.today()
        upcoming_limit = heute + timedelta(days=14)
        
        valid_payouts = []
        for idx, row in df_div.iterrows():
            date_str = str(row["Ex-Dividenden-Datum"])
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if heute - timedelta(days=1) <= dt <= upcoming_limit:
                    # Validate source facts before adding display formatting.
                    try:
                        yield_float = float(str(row.get("Dividendenrendite", pd.NA)))
                        dividend_float = float(str(row.get("Dividenden-Betrag", pd.NA)))
                    except (TypeError, ValueError):
                        continue
                    if (
                        not math.isfinite(yield_float)
                        or not math.isfinite(dividend_float)
                        or not 0 < yield_float <= 100
                        or dividend_float <= 0
                    ):
                        continue

                    currency_val = row.get("Währung", pd.NA)
                    if pd.isna(currency_val) or not str(currency_val).strip():
                        continue
                    currency = str(currency_val).strip().upper()

                    name_val = row.get("Security", pd.NA)
                    if pd.isna(name_val) or not str(name_val).strip():
                        continue
                    name_str = str(name_val).strip()
                    yield_str = f"{yield_float:.1f}%"
                    div_str = f"{dividend_float:.2f} {currency}"
                    market_cap = pd.to_numeric(
                        "".join(
                            character
                            for character in str(row.get("Marktkapitalisierung", "0"))
                            if character.isdigit() or character == "."
                        ),
                        errors="coerce",
                    )
                    if pd.isna(market_cap):
                        market_cap = 0.0
                    valid_payouts.append({
                        "symbol": str(row["valid_yahoo_ticker"]),
                        "name": name_str,
                        "ex_date": date_str,
                        "dividend": div_str,
                        "yield": yield_str,
                        "currency": currency,
                        "market_cap": float(market_cap),
                    })
            except Exception:
                continue
                
        # Sort by Ex-Date and then Market Cap to keep well-known high cap stocks first
        valid_payouts = sorted(valid_payouts, key=lambda x: (x["ex_date"], -x["market_cap"]))
        payouts = valid_payouts[:6]

    # Never invent calendar dates, dividends or yields to fill the layout.
    try:
        payouts = validate_calendar_entries(payouts, minimum=6)
    except ValueError as error:
        print(f"CALENDAR TRACK: Skip publication because verified source data is incomplete: {error}")
        return False

    print(f"CALENDAR TRACK: Rendering calendar with {len(payouts)} payouts:")
    for p in payouts:
        print(f" - {p['symbol']} | Ex: {p['ex_date']} | Div: {p['dividend']} | Yield: {p['yield']}")

    # Render image
    image_filename = f"calendar_{timestamp}.png"
    image_path = os.path.join(public_dir, image_filename)
    
    render_dividend_calendar(payouts, image_path)
    print(f"CALENDAR TRACK: Image saved at {image_path}")
    
    # Captions & Text
    payout_mentions = ", ".join(p["symbol"] for p in payouts)
    caption = (
        "📈 DER WÖCHENTLICHE DIVIDENDEN-KALENDER IST DA! 📈\n\n"
        "Hier sind die ex-dividend Termine für die kommenden Tage. "
        "Wer diese Aktien rechtzeitig im Depot hat, sichert sich die nächste Ausschüttung! 💰\n\n"
        f"Im Fokus diese Woche: {payout_mentions}\n\n"
        "Welche dieser Werte hast du bereits im Depot oder auf deiner Watchlist? Schreib es uns in die Kommentare! 👇\n\n"
        "👉 Den interaktiven Dividendenkalender für über 4.000 Aktien findest du auf schatzsuche40.de! Link in der Bio.\n\n"
        "#dividenden #aktien #geldanlage #passiveseinkommen #etf #finanzen #investieren #boerse #reichwerden"
    )
    comment_text = (
        f"💡 Alle Ex-Dividenden-Termine im Jahr {datetime.today().year} findest du in unserem kostenlosen Dividendenkalender:\n"
        "https://schatzsuche40.de/dividendenkalender/\n\n"
        "Verpasse keine Ausschüttungen mehr!"
    )

    # 3. Publish
    print("CALENDAR TRACK: Publishing to socials...")
    run_social_sync(
        symbol="DIVIDENDEN-KALENDER",
        caption=caption,
        image_path=image_path,
        blog_url="https://schatzsuche40.de",
        wp_img_url=None,
        title="Dividendenkalender der Woche",
        comment_text=comment_text,
        skip_instagram=False,
        strip_links_on_x=True
    )
    
    print("CALENDAR TRACK: Reel video and YouTube Shorts uploads disabled to focus on high-engagement feed posts.")
    
    print("✅ TRACK 2 DIVIDEND CALENDAR PIPELINE COMPLETED SUCCESSFULLY!")
    return True

def run_track_ai(topic=None):
    """
    Track 3: AI Infographics (3 times a week, Tue/Thu/Sat at 8:00 AM).
    Generates dynamic educational content via GPT, renders "Elterngeld"-style facts list,
    synthesizes a Full Voiceover Reel (speech, whisper karaoke subtitles),
    and posts to Instagram Reels + YouTube Shorts.
    """
    print("🚀 TRACK 3: RUNNING AI INFOGRAPHIC (EVERGREEN) PIPELINE...")
    
    source_context = None
    if topic:
        content_pillar = "manual_override"
    else:
        # Performance audit: current financial changes materially outperform
        # generic automated clips. Always try a sourced fresh topic first and
        # only then fall back to a curated family-finance evergreen pool.
        print("AI TRACK: Fetching current finance headlines...")
        source_context = fetch_current_market_news()
        dynamic_topic = get_dynamic_trending_topic(source_context)
        topic, content_pillar = choose_automated_topic(
            dynamic_topic=dynamic_topic,
            evergreen_topics=PRIORITY_EVERGREEN_TOPICS,
        )
        if content_pillar != "current_finance_news":
            source_context = None

    print(f"AI TRACK: Chosen Topic: '{topic}'")
    print(f"AI TRACK: Content Pillar: {content_pillar}")

    # 1. GPT Copywriting
    content = generate_structured_content(
        topic,
        template_type="viral_list",
        source_context=source_context,
    )
    if content_pillar == "manual_override":
        content["requires_manual_review"] = True
        content["publishing_allowed"] = False
    review_metadata = review_metadata_for_content(content, content_pillar=content_pillar)
    
    public_dir = os.path.join(BASE_DIR, "static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    image_filename = f"ai_infographic_{timestamp}.png"
    video_filename = f"ai_infographic_{timestamp}.mp4"
    image_path = os.path.join(public_dir, image_filename)
    video_path = os.path.join(public_dir, video_filename)
    
    # 2. Render Hybrid Image (AI Background Illustration + Programmatic Text Overlay & Logos)
    bg_path = os.path.join(public_dir, f"ai_bg_{timestamp}.png")
    bg_success = False
    try:
        from src.graphic_generator import generate_dalle_image
        print("AI TRACK: Generating AI background illustration...")
        image_prompt_text = content.get("image_prompt") or content.get("dalle_prompt") or "Abstract finance background in gold and dark petrol"
        bg_img = generate_dalle_image(image_prompt_text, aspect_ratio="9:16")
        # Check if gpt-image-2 returned a successful vertical image (1024x1792) instead of the 800x800 fallback
        if bg_img and bg_img.size == (1024, 1792):
            bg_img.save(bg_path)
            print(f"AI TRACK: Background saved at {bg_path}")
            bg_success = True
        else:
            print("AI TRACK: Background generation returned fallback or invalid size image.")
            bg_path = None
    except Exception as e:
        print(f"AI TRACK: Warning: Background generation failed: {e}")
        bg_path = None

    if bg_success and bg_path and os.path.exists(bg_path):
        import shutil
        shutil.copy(bg_path, image_path)
        print(f"AI TRACK: Using raw AI infographic directly (no programmatic overlay): {image_path}")
    else:
        print("AI TRACK: Rendering programmatic infographic list on fallback background...")
        render_viral_list(content, image_path, bg_image_path=None)
    print(f"AI TRACK: Image saved at {image_path}")
    
    # Determine content-aware background music mood
    script_lower = (content.get("reel_script", "") + " " + topic).lower()
    if any(w in script_lower for w in ["crash", "krise", "warnung", "risiko", "gefahr", "verlust", "schulden", "inflation", "steuer", "abgabe"]):
        detected_mood = "dark"
    elif any(w in script_lower for w in ["dividende", "gewinn", "erfolg", "rendite", "reichtum", "sparen", "frei", "passiv", "zins"]):
        detected_mood = "happy"
    elif any(w in script_lower for w in [" künstliche", " ai ", "tech", "crypto", "krypto", "bitcoin", "nvidia", "zukunft"]):
        detected_mood = "action"
    else:
        detected_mood = "chill"
    print(f"AI TRACK: Dynamic background music mood detected: {detected_mood}")

    # 3. Render Reel Video with Voiceover and Karaoke Subtitles
    print("AI TRACK: Rendering Reel video with voiceover and karaoke subtitles...")
    build_reel_mp4(
        script_text=content.get("reel_script"),
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False,
        duration=15.0,
        mood=detected_mood
    )
    
    # 4. Route all preparation/publication through one central fail-closed gate.
    caption_ig = content.get("caption_ig", "")
    comment_text = "👉 Folge @schatzsuche40 für dein tägliches Finanzwissen! 🚀"
    youtube_meta = {
        "title": (content.get("headline", "")[:70] + " #shorts #finanzen"),
        "description": content.get(
            "caption_shorts", "Lerne clever investieren mit Schatzsuche 4.0!"
        )
        + "\n\n#finanzen #shorts #aktien #sparen",
        "tags": ["Finanzen", "Investieren", "Geld anlegen", "ETFs", "Zinseszins", "Sparen"],
    }

    def prepare_bundle():
        return save_for_manual_upload(
            post_type="ai_reel_bundle",
            title=content.get("headline", "Finanz-Fakten"),
            caption=caption_ig,
            asset_path=video_path,
            comment_text=comment_text,
            tags=youtube_meta["tags"],
            additional_assets=[image_path],
            review_metadata=review_metadata,
        )

    def dispatch_feed():
        print("AI TRACK: Publishing image to standard socials...")
        return run_social_sync(
            symbol="FINANZ-TIPP",
            caption=caption_ig,
            image_path=image_path,
            blog_url="https://schatzsuche40.de",
            wp_img_url=None,
            title=content.get("headline", "Finanz-Fakten"),
            comment_text=comment_text,
            skip_instagram=True,
            strip_links_on_x=True,
        )

    def dispatch_instagram_reel():
        print("AI TRACK: Publishing video to Instagram Reels...")
        return post_instagram_reel(caption_ig, video_filename, comment_text)

    def dispatch_facebook_reel():
        print("AI TRACK: Publishing video to Facebook Reels...")
        return post_facebook_reel(caption_ig, video_path)

    def dispatch_youtube_short():
        print("AI TRACK: Uploading video to YouTube Shorts...")
        return youtube_upload_video(
            video_file=video_path,
            metadata_dict=youtube_meta,
            privacy_status="public",
            token_file=os.path.join(BASE_DIR, "token_finance.pickle"),
        )

    def dispatch_tiktok():
        tiktok_token = os.path.join(BASE_DIR, "token_tiktok.pickle")
        if not os.path.exists(tiktok_token):
            print("TIKTOK: Skip. token_tiktok.pickle not found on server.")
            return False
        try:
            from src.tiktok_uploader import upload_video_to_tiktok

            tiktok_key = os.getenv("TIKTOK_CLIENT_KEY")
            tiktok_secret = os.getenv("TIKTOK_CLIENT_SECRET")
            if not tiktok_key or not tiktok_secret:
                print("TIKTOK: Skip. Client key or secret missing.")
                return False
            return upload_video_to_tiktok(
                video_path=video_path,
                caption=content.get("caption_tiktok", caption_ig),
                client_key=tiktok_key,
                client_secret=tiktok_secret,
                token_file=tiktok_token,
            )
        except Exception as error:
            print(f"TIKTOK: Warning: Upload failed: {error}")
            return False

    distribution = dispatch_or_prepare(
        prepare_only=(
            not content_dispatch_allowed(content)
            or not live_public_dispatch_enabled()
        ),
        prepare=prepare_bundle,
        dispatchers=(
            ("feed", dispatch_feed),
            ("instagram_reel", dispatch_instagram_reel),
            ("facebook_reel", dispatch_facebook_reel),
            ("youtube_short", dispatch_youtube_short),
            ("tiktok", dispatch_tiktok),
        ),
    )
    if distribution["mode"] == "prepared":
        print(
            "AI TRACK: Preparation/review gate stopped every external dispatcher; "
            f"bundle: {distribution['artifact']}"
        )

    print("✅ TRACK 3 AI INFOGRAPHIC PIPELINE COMPLETED SUCCESSFULLY!")
    return True


def run_track_personal(input_file, output_dir=None):
    """Create a Canva-ready personal post packet without publishing it."""

    if not input_file:
        raise ValueError("PERSONAL TRACK: --input is required")

    uploads_base = output_dir or os.getenv("MANUAL_UPLOADS_DIR")
    if not uploads_base:
        uploads_base = os.path.join(BASE_DIR, "manual_uploads")

    print("🎨 PERSONAL TRACK: Creating factual Canva Bulk Create packet...")
    packet_dir = create_personal_canva_packet_from_json(input_file, uploads_base)
    print(f"PERSONAL TRACK: Canva packet created at {packet_dir}")
    print("PERSONAL TRACK: No social post was published; manual Canva export and approval are required.")

    if external_transfer_enabled(
        requested=os.getenv("UPLOAD_TO_GDRIVE", "False").lower() == "true",
        allowed=os.getenv("GDRIVE_TRANSFER_ALLOWED", "False").lower() == "true",
    ):
        try:
            from google_drive_uploader import push_folder_to_drive

            if not push_folder_to_drive(str(packet_dir)):
                print("PERSONAL TRACK: Warning: Google Drive upload did not complete.")
        except Exception as drive_error:
            print(f"PERSONAL TRACK: Warning: Google Drive upload failed: {drive_error}")

    return str(packet_dir)


if __name__ == "__main__":
    # Set resource memory limit to 1000MB (soft) / 1250MB (hard) to prevent swap-thrashing on AWS micro instance
    try:
        import resource
        soft_limit = 1000 * 1024 * 1024  # 1000 MB
        hard_limit = 1250 * 1024 * 1024  # 1250 MB
        resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
        print(f"RESOURCE LIMIT: Virtual memory ceiling set to {soft_limit / (1024*1024):.0f} MB")
    except Exception as e:
        # Ignore on Windows or unsupported platforms
        pass

    parser = argparse.ArgumentParser(description="Schatzsuche 4.0 Social Media Autoposter Controller")
    parser.add_argument("--track", type=str, choices=["stock", "calendar", "ai", "personal"], required=True,
                        help="Select: stock feed, dividend calendar, current-topic AI draft, or personal Canva packet")
    parser.add_argument("--topic", type=str, default=None,
                        help="Optional: Explicit topic override for the AI track")
    parser.add_argument("--input", type=str, default=None,
                        help="Required for personal: path to a factual personal-post JSON brief")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Optional output directory for the personal Canva packet")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        if args.track == "stock":
            run_track_stock()
        elif args.track == "calendar":
            run_track_calendar()
        elif args.track == "ai":
            run_track_ai(args.topic)
        elif args.track == "personal":
            run_track_personal(args.input, args.output_dir)
            
        print(f"🎬 Done! Execution took {time.time() - start_time:.1f} seconds.")
    except Exception as e:
        print(f"❌ FATAL ERROR IN SOCIAL AUTOPOSTER PIPELINE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
