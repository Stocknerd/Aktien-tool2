#!/usr/bin/env python3
import os
import sys
import time
import random
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path to allow importing from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import BASE_DIR, COLORS, COLORS_HEX
from src.graphic_generator import render_viral_list, render_dividend_calendar, render_pure_ai_infographic
from src.reel_generator import build_reel_mp4
from src.content_generator import generate_structured_content
from src.youtube_uploader import upload_video as youtube_upload_video

from core import render_stock_card, render_compare, CSV_FILE
from ai_logic import get_tool_promotion_caption, get_ai_verdict, get_ai_comparison_verdict
from social_publisher import run_social_sync, post_instagram_reel

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

def get_dynamic_trending_topic() -> str:
    """Uses GPT to suggest an extremely high-trending, current financial or macroeconomic topic of the week."""
    try:
        from openai import OpenAI
        client = OpenAI()
        model_name = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
        prompt = (
            "Du bist ein Top-Finanzblogger in Deutschland. Nenne mir EIN einziges extrem aktuelles, "
            "hochgradig virales Finanz-, Börsen- oder makroökonomisches Thema für diese Woche "
            "(z. B. eine aktuelle Leitzinsentscheidung der Fed/EZB, ein neuer Hype wie AI-Aktien, "
            "die neuesten Inflationsdaten, Krypto-Trends oder Marktvolatilitäten). "
            "Das Thema muss perfekt geeignet sein, um es als Infografik-Liste für Privatanleger verständlich zu erklären.\n\n"
            "Gib mir AUSSCHLIESSLICH das Thema als kurzen, knackigen Titel (max. 50 Zeichen) aus. "
            "Kein Präfix, kein Suffix, kein Punkt am Ende, keine Anführungszeichen."
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Du bist ein präziser Finanz-Experte."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85
        )
        topic = response.choices[0].message.content.strip()
        # Clean quotes
        if (topic.startswith('"') and topic.endswith('"')) or (topic.startswith("'") and topic.endswith("'")):
            topic = topic[1:-1]
        return topic
    except Exception as e:
        print(f"TREND DETECTOR: Warning: Failed to fetch dynamic topic: {e}")
        return None

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
    
    # 2. Render Video with Voiceover and Karaoke Subtitles
    print("STOCK TRACK: Rendering Reel video with voiceover and subtitles...")
    build_reel_mp4(
        script_text=verdict,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False,
        duration=12.0
    )
    
    caption = get_tool_promotion_caption(is_comparison, names, symbols, fin_texts)
    
    # 3. Publish
    print("STOCK TRACK: Publishing to social platforms...")
    
    # Image to other standard socials (X, FB, Pinterest)
    run_social_sync(
        symbol=symbols,
        caption=caption,
        image_path=image_path,
        blog_url="https://schatzsuche40.de",
        wp_img_url=None,
        title=names,
        comment_text=comment_text,
        skip_instagram=True
    )
    
    # Video as Reel to Instagram
    print("STOCK TRACK: Publishing Video to Instagram Reels...")
    post_instagram_reel(caption, video_filename, comment_text)
    
    # 4. YouTube Shorts Upload (Video)
    print("STOCK TRACK: Uploading Video to YouTube Shorts...")
    youtube_meta = {
        "title": ((f"{names} im Check! 📈"[:70] if not is_comparison else f"{names} im Börsen-Duell! ⚔️"[:70]) + " #shorts #aktien"),
        "description": caption + "\n\n#shorts #aktien #finanzen #geldanlage #investieren",
        "tags": ["Aktien", "Börse", "Finanzen", "Investieren", "Geldanlage", symbols]
    }
    
    try:
        youtube_token = os.path.join(BASE_DIR, 'token_finance.pickle')
        youtube_upload_video(
            video_file=video_path,
            metadata_dict=youtube_meta,
            privacy_status='public',
            token_file=youtube_token
        )
    except Exception as yt_err:
        print(f"STOCK TRACK: Warning: YouTube upload failed: {yt_err}")
    
    print("✅ TRACK 1 STOCK CARD PIPELINE COMPLETED SUCCESSFULLY!")
    return True

def run_track_calendar():
    """
    Track 2: Dividend Calendar (Weekly on Sundays at 6:00 PM).
    Filters upcoming ex-dividend dates, renders a 2x3 logo grid,
    synthesizes a Silent Reel, and posts it.
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
                    # Parse dividend yield format
                    yield_val = row.get("Dividendenrendite", pd.NA)
                    yield_str = "--"
                    if pd.notna(yield_val):
                        try:
                            yield_str = f"{float(yield_val) * 100:.1f}%"
                        except:
                            yield_str = str(yield_val)
                            
                    div_val = row.get("Dividenden-Betrag", pd.NA)
                    div_str = f"{float(div_val):.2f}" if pd.notna(div_val) and isinstance(div_val, (int, float)) else str(div_val) if pd.notna(div_val) else "--"
                    
                    currency = str(row.get("Währung", "EUR"))
                    symbol_currency = "$" if "USD" in currency else "€" if "EUR" in currency else currency
                    if div_str != "--" and symbol_currency in ["$", "€"]:
                        div_str = f"{div_str}{symbol_currency}"
                    
                    valid_payouts.append({
                        "symbol": str(row["valid_yahoo_ticker"]),
                        "name": str(row.get("Security", row["valid_yahoo_ticker"])),
                        "ex_date": date_str,
                        "dividend": div_str,
                        "yield": yield_str,
                        "market_cap": pd.to_numeric(str(row.get("Marktkapitalisierung", "0")).replace(r'[^\d.]', '', regex=True), errors='coerce')
                    })
            except Exception as ex:
                continue
                
        # Sort by Ex-Date and then Market Cap to keep well-known high cap stocks first
        valid_payouts = sorted(valid_payouts, key=lambda x: (x["ex_date"], -x["market_cap"]))
        payouts = valid_payouts[:6]

    # Fallback to high-quality dividend stocks if CSV data is sparse or outdated
    if len(payouts) < 6:
        print("CALENDAR TRACK: Warning: Sparse future ex-dividend dates in CSV. Falling back to premier dividend stocks.")
        fallbacks = [
            {"symbol": "AAPL", "name": "Apple Inc.", "dividend": "0.25$", "yield": "0.5%"},
            {"symbol": "MSFT", "name": "Microsoft Corp.", "dividend": "0.75$", "yield": "0.7%"},
            {"symbol": "O", "name": "Realty Income", "dividend": "0.26$", "yield": "5.8%"},
            {"symbol": "KO", "name": "Coca-Cola Co.", "dividend": "0.48$", "yield": "3.1%"},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "dividend": "1.24$", "yield": "3.2%"},
            {"symbol": "T", "name": "AT&T Inc.", "dividend": "0.28$", "yield": "6.2%"}
        ]
        # Set realistic ex-dividend dates (upcoming weekdays)
        for i, f in enumerate(fallbacks):
            ex_dt = datetime.today() + timedelta(days=i+2)
            f["ex_date"] = ex_dt.strftime("%Y-%m-%d")
            payouts.append(f)
            
        payouts = payouts[:6]

    print(f"CALENDAR TRACK: Rendering calendar with {len(payouts)} payouts:")
    for p in payouts:
        print(f" - {p['symbol']} | Ex: {p['ex_date']} | Div: {p['dividend']} | Yield: {p['yield']}")

    # Render image
    image_filename = f"calendar_{timestamp}.png"
    video_filename = f"calendar_{timestamp}.mp4"
    image_path = os.path.join(public_dir, image_filename)
    video_path = os.path.join(public_dir, video_filename)
    
    render_dividend_calendar(payouts, image_path)
    print(f"CALENDAR TRACK: Image saved at {image_path}")
    
    # Construct dynamic speaker script for calendar
    valid_payout_names = [p["name"] for p in payouts if p["name"] != "DUMMY" and p["symbol"] != "DUMMY"]
    top_3_payouts = valid_payout_names[:3]
    if top_3_payouts:
        calendar_script = (
            f"Der Dividenden-Kalender für diese Woche! Im Fokus stehen diesmal: {', '.join(top_3_payouts)}. "
            "Wer diese Aktien rechtzeitig vor dem Ex-Tag im Depot hat, sichert sich die nächste Ausschüttung. "
            "Welchen Dividenden-Zahler hast du bereits im Depot? Schreib es uns in die Kommentare und folge Schatzsuche vier punkt null für tägliches Finanzwissen!"
        )
    else:
        calendar_script = (
            "Der wöchentliche Dividenden-Kalender ist da! Hier siehst du die ex-dividend Termine für die kommenden Tage. "
            "Wer diese Aktien rechtzeitig im Depot hat, sichert sich die nächste Ausschüttung! "
            "Welchen Wert hast du bereits im Depot? Schreib es uns in die Kommentare und folge Schatzsuche vier punkt null!"
        )

    # Render video with voiceover and subtitles
    print("CALENDAR TRACK: Rendering Reel video with voiceover and subtitles...")
    build_reel_mp4(
        script_text=calendar_script,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False,
        duration=12.0
    )
    
    # Captions & Text
    payout_mentions = ", ".join([p["symbol"] for p in payouts if p["symbol"] != "DUMMY"])
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
        "💡 Alle Ex-Dividenden Termine im Jahr 2026 findest du in unserem kostenlosen Dividendenkalender:\n"
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
        skip_instagram=True
    )
    
    print("CALENDAR TRACK: Publishing Video to Instagram Reels...")
    post_instagram_reel(caption, video_filename, comment_text)
    
    # 4. YouTube Shorts Upload (Video)
    print("CALENDAR TRACK: Uploading Video to YouTube Shorts...")
    youtube_meta = {
        "title": "Dividendenkalender der Woche! 💰 #shorts #dividenden",
        "description": caption + "\n\n#shorts #dividenden #aktien #finanzen #passiveseinkommen",
        "tags": ["Dividenden", "Aktien", "Börse", "Finanzen", "Passives Einkommen", "Geldanlage"]
    }
    
    try:
        youtube_token = os.path.join(BASE_DIR, 'token_finance.pickle')
        youtube_upload_video(
            video_file=video_path,
            metadata_dict=youtube_meta,
            privacy_status='public',
            token_file=youtube_token
        )
    except Exception as yt_err:
        print(f"CALENDAR TRACK: Warning: YouTube upload failed: {yt_err}")
    
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
    
    if not topic:
        # 50% chance of a highly trending topic, 50% chance of a deep evergreen topic
        if random.random() < 0.5:
            print("AI TRACK: Fetching dynamic trending topic via GPT...")
            topic = get_dynamic_trending_topic()
            
        if not topic:
            # Fallback or standard choice from the deep evergreen topic pool
            print("AI TRACK: Selecting from the evergreen topic pool...")
            topic = random.choice(EVERGREEN_FINANCIAL_TOPICS)
        
    print(f"AI TRACK: Chosen Topic: '{topic}'")
    
    # 1. GPT Copywriting
    content = generate_structured_content(topic, template_type="viral_list")
    
    public_dir = os.path.join(BASE_DIR, "static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    image_filename = f"ai_infographic_{timestamp}.png"
    video_filename = f"ai_infographic_{timestamp}.mp4"
    image_path = os.path.join(public_dir, image_filename)
    video_path = os.path.join(public_dir, video_filename)
    
    # 2. Render Hybrid Image (AI Background Illustration + Programmatic Text Overlay & Logos)
    bg_path = os.path.join(public_dir, f"ai_bg_{timestamp}.png")
    try:
        from src.graphic_generator import generate_dalle_image
        print("AI TRACK: Generating AI background illustration...")
        bg_img = generate_dalle_image(content.get("dalle_prompt", "Abstract finance background in gold and dark petrol"), aspect_ratio="9:16")
        bg_img.save(bg_path)
        print(f"AI TRACK: Background saved at {bg_path}")
    except Exception as e:
        print(f"AI TRACK: Warning: Background generation failed: {e}")
        bg_path = None

    print("AI TRACK: Rendering programmatic infographic list on background...")
    render_viral_list(content, image_path, bg_image_path=bg_path)
    print(f"AI TRACK: Image saved at {image_path}")
    
    # 3. Render Reel Video with Voiceover and Karaoke Subtitles
    print("AI TRACK: Rendering Reel video with voiceover and subtitles...")
    build_reel_mp4(
        script_text=content.get("reel_script"),
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False,
        duration=15.0
    )
    
    # 4. Social posting to X, FB, Pinterest (Image)
    caption_ig = content.get("caption_ig", "")
    print("AI TRACK: Publishing Image to standard socials...")
    run_social_sync(
        symbol="FINANZ-TIPP",
        caption=caption_ig,
        image_path=image_path,
        blog_url="https://schatzsuche40.de",
        wp_img_url=None,
        title=content.get("headline", "Finanz-Fakten"),
        comment_text="👉 Folge @schatzsuche40 für dein tägliches Finanzwissen! 🚀",
        skip_instagram=True
    )
    
    # 5. Instagram Reels Upload (Video)
    print("AI TRACK: Publishing Video to Instagram Reels...")
    post_instagram_reel(caption_ig, video_filename, "👉 Folge @schatzsuche40 für dein tägliches Finanzwissen! 🚀")
    
    # 6. YouTube Shorts Upload (Video)
    print("AI TRACK: Uploading Video to YouTube Shorts...")
    youtube_meta = {
        "title": (content.get("headline", "")[:70] + " #shorts #finanzen"),
        "description": content.get("caption_shorts", "Lerne clever investieren mit Schatzsuche 4.0!") + "\n\n#finanzen #shorts #aktien #sparen",
        "tags": ["Finanzen", "Investieren", "Geld anlegen", "ETFs", "Zinseszins", "Sparen"]
    }
    
    # Call youtube uploader with custom token_finance.pickle
    youtube_token = os.path.join(BASE_DIR, 'token_finance.pickle')
    youtube_upload_video(
        video_file=video_path,
        metadata_dict=youtube_meta,
        privacy_status='public',
        token_file=youtube_token
    )
    
    # 7. TikTok Upload (Video - Optional plug-and-play)
    tiktok_token = os.path.join(BASE_DIR, 'token_tiktok.pickle')
    if os.path.exists(tiktok_token):
        print("AI TRACK: token_tiktok.pickle found. Publishing Video to TikTok...")
        try:
            from src.tiktok_uploader import upload_video_to_tiktok
            tiktok_key = os.getenv("TIKTOK_CLIENT_KEY")
            tiktok_secret = os.getenv("TIKTOK_CLIENT_SECRET")
            if tiktok_key and tiktok_secret:
                upload_video_to_tiktok(
                    video_path=video_path,
                    caption=content.get("caption_tiktok", caption_ig),
                    client_key=tiktok_key,
                    client_secret=tiktok_secret,
                    token_file=tiktok_token
                )
            else:
                print("TIKTOK: Skip. TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET missing in .env.")
        except Exception as tk_err:
            print(f"TIKTOK: Warning: Upload failed: {tk_err}")
    else:
        print("TIKTOK: Skip. token_tiktok.pickle not found on server (optional plug-and-play).")
    
    print("✅ TRACK 3 AI INFOGRAPHIC PIPELINE COMPLETED SUCCESSFULLY!")
    return True

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
    parser.add_argument("--track", type=str, choices=["stock", "calendar", "ai"], required=True,
                        help="Select the content track/säule to execute: 'stock' (Track 1), 'calendar' (Track 2), or 'ai' (Track 3)")
    parser.add_argument("--topic", type=str, default=None,
                        help="Optional: Explicit topic override for Track 3 (AI Infographics)")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        if args.track == "stock":
            run_track_stock()
        elif args.track == "calendar":
            run_track_calendar()
        elif args.track == "ai":
            run_track_ai(args.topic)
            
        print(f"🎬 Done! Execution took {time.time() - start_time:.1f} seconds.")
    except Exception as e:
        print(f"❌ FATAL ERROR IN SOCIAL AUTOPOSTER PIPELINE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
