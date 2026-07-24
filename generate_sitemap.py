import os
import pandas as pd
from datetime import datetime

def generate_sitemap(csv_path="stock_data.csv", output_path=None):
    print("Generating sitemap...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(base_dir, csv_path)
        
    if not output_path:
        output_path = os.path.join(base_dir, "static", "sitemap.xml")
    elif not os.path.isabs(output_path):
        output_path = os.path.join(base_dir, output_path)
        
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
        
    try:
        df = pd.read_csv(csv_path)
        # Ensure Symbol column exists
        if "Symbol" not in df.columns and "valid_yahoo_ticker" in df.columns:
            df = df.rename(columns={"valid_yahoo_ticker": "Symbol"})
            
        if "Symbol" not in df.columns:
            print("Error: 'Symbol' column not found in CSV.")
            return False
            
        tickers = df["Symbol"].dropna().unique().tolist()
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return False
        
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_footer = '</urlset>\n'
    
    urls = [
        ("https://tool.schatzsuche40.de/", "daily", "1.0"),
        ("https://tool.schatzsuche40.de/screener", "daily", "0.8"),
        ("https://tool.schatzsuche40.de/dividenden-kalender", "daily", "0.8"),
        ("https://tool.schatzsuche40.de/dividend-rechner", "daily", "0.8"),
        ("https://tool.schatzsuche40.de/p2p", "daily", "0.8"),
    ]
    
    xml_body = ""
    for url, freq, prio in urls:
        xml_body += f"  <url>\n    <loc>{url}</loc>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>\n"
        
    today = datetime.now().strftime("%Y-%m-%d")
    for ticker in sorted(tickers):
        ticker_str = str(ticker).strip().upper()
        if not ticker_str or ticker_str.lower() in ["nan", "null", "none"]:
            continue
        # Escape any special characters in ticker
        ticker_escaped = ticker_str.replace("&", "&amp;").replace("'", "&apos;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        url = f"https://tool.schatzsuche40.de/analyse/{ticker_escaped}"
        xml_body += f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"
        
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_header + xml_body + xml_footer)
        print(f"Sitemap successfully generated at {output_path} with {len(tickers)} stock links.")
        return True
    except Exception as e:
        print(f"Error writing sitemap: {e}")
        return False

if __name__ == "__main__":
    generate_sitemap()
