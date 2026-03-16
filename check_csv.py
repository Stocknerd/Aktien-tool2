import pandas as pd
import yfinance as yf
import requests, os

LOGO_DIR = os.path.abspath('static/logos')
CSV_PATH = os.path.abspath('stock_data.csv')

df = pd.read_csv(CSV_PATH, encoding='utf-8')
print('Total rows in CSV:', len(df))

missing_syms = []
missing_logos = []

for _, row in df.iterrows():
    sym = str(row.get('Symbol', '')).strip()
    sec = str(row.get('Security', 'Unknown')).strip()
    
    if not sym or sym == 'nan':
        missing_syms.append(sec)
        continue
        
    logo_path = os.path.join(LOGO_DIR, f"{sym}.png")
    if not os.path.exists(logo_path):
        missing_logos.append((sym, sec))

print("\n--- Missing Symbols ---")
print(f"Count: {len(missing_syms)}")
if missing_syms:
    print("Examples:", missing_syms[:10])

print("\n--- Missing Logos ---")
print(f"Count: {len(missing_logos)}")
if missing_logos:
    print("Examples:", missing_logos[:10])
    
# Check a sample missing symbol to see if we can resolve it
if missing_syms:
    print("\nAttempting to resolve first missing symbol via Yahoo Finance search...")
    sec = missing_syms[0]
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(sec)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers).json()
        quotes = res.get('quotes', [])
        if quotes:
            print(f"Found match for '{sec}': {quotes[0]['symbol']} ({quotes[0]['shortname']})")
        else:
            print(f"No match found for '{sec}'")
    except Exception as e:
        print("Search failed:", e)
