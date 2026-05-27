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
from src.graphic_generator import render_viral_list, render_dividend_calendar
from src.reel_generator import build_reel_mp4
from src.content_generator import generate_structured_content
from src.youtube_uploader import upload_video as youtube_upload_video

from core import render_stock_card, render_compare, CSV_FILE
from ai_logic import get_tool_promotion_caption, get_ai_verdict, get_ai_comparison_verdict
from social_publisher import run_social_sync, post_instagram_reel

# A solid list of evergreen financial topics for Track 3 (AI Infographics)
EVERGREEN_FINANCIAL_TOPICS = [
    "Zinseszins: Warum Zeit dein größter Hebel an der Börse ist",
    "Warum breit gestreute ETFs die beste Basis für dein Depot sind",
    "3 typische Anfänger-Fehler an der Börse und wie du sie vermeidest",
    "Was ist der Unterschied zwischen Ausschüttend und Thesaurierend?",
    "Die 72er-Regel: Wie schnell verdoppelt sich dein Investment?",
    "Dividenden-Wachstum vs. High-Yield: Was ist besser für Cashflow?",
    "Warum der Notgroschen immer vor dem Investieren stehen muss",
    "Wie Inflation dein Erspartes entwertet und wie Aktien schützen",
    "Diversifikation: Lege niemals alle Eier in einen Korb",
    "Der Cost-Average-Effekt: Warum fallende Kurse auch Chancen sind",
    "Sparquote erhöhen: 3 Hebel, um monatlich mehr zu investieren",
    "Was ist ein MSCI World und warum kennt ihn jeder Anleger?",
    "Einzelaktien vs. ETFs: Das sind die Vor- und Nachteile",
    "Psychologie an der Börse: Warum Panikverkäufe dich Rendite kosten",
    "Wie du deine Dividenden reinvestierst für maximales Wachstum",
    "Steuern auf Kapitalerträge in Deutschland kurz erklärt",
    "Wie viel Geld braucht man zum Starten? Depotaufbau ab 25 Euro",
    "Warum Gold kein produktives Investment ist aber als Schutz dient",
    "Die Macht der Dividenden: Historischer Treiber des Aktienmarkts",
    "Was ist die Ausschüttungsquote und warum ist sie so wichtig?"
]

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
    
    # 2. Render Silent Video (Musik + Zoom)
    print("STOCK TRACK: Rendering Silent Reel video...")
    build_reel_mp4(
        script_text=None,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=True,
        duration=8.0
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
        comment_text=comment_text
    )
    
    # Video as Reel to Instagram
    print("STOCK TRACK: Publishing Video to Instagram Reels...")
    post_instagram_reel(caption, video_filename, comment_text)
    
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
    
    # Render video
    print("CALENDAR TRACK: Rendering Silent Reel video...")
    build_reel_mp4(
        script_text=None,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=True,
        duration=9.0
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
        comment_text=comment_text
    )
    
    print("CALENDAR TRACK: Publishing Video to Instagram Reels...")
    post_instagram_reel(caption, video_filename, comment_text)
    
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
        # Choose a random evergreen topic
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
    
    # 2. Render Image
    render_viral_list(content, image_path)
    print(f"AI TRACK: Image saved at {image_path}")
    
    # 3. Render Full Voiceover Video (Voiceover + Subtitles)
    script_text = content.get("reel_script", "")
    print(f"AI TRACK: Synthesis Voiceover Script ({len(script_text.split())} words):\n'{script_text}'")
    
    build_reel_mp4(
        script_text=script_text,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False
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
        comment_text="👉 Folge @schatzsuche40 für dein tägliches Finanzwissen! 🚀"
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
    
    print("✅ TRACK 3 AI INFOGRAPHIC PIPELINE COMPLETED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
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
