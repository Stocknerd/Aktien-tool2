import pandas as pd
import yfinance as yf
import requests, os

LOGO_DIR = os.path.abspath('static/logos')
CSV_PATH = os.path.abspath('stock_data.csv')

df = pd.read_csv(CSV_PATH, encoding='utf-8')

missing_syms = []
missing_logos = []

for _, row in df.iterrows():
    sym = str(row.get('Symbol', '')).strip()
    sec = str(row.get('Security', 'Unknown')).strip()
    
    if not sym or sym == 'nan':
        if sec and sec != 'nan':
            missing_syms.append(sec)
        continue
        
    logo_path = os.path.join(LOGO_DIR, f"{sym}.png")
    if not os.path.exists(logo_path):
        missing_logos.append((sym, sec))

print(f"Missing logos count: {len(missing_logos)}")
for sym, sec in missing_logos:
    print(f"Downloading logo for {sym}...")
    try:
        t = yf.Ticker(sym)
        url = t.info.get('logo_url')
        if not url:
            if '-' in sym:
                alt = sym.replace('-', '.')
                url = yf.Ticker(alt).info.get('logo_url')
        if url:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                with open(os.path.join(LOGO_DIR, f'{sym}.png'), 'wb') as f:
                    f.write(r.content)
                print(f"  -> SUCCESS ({sym})")
            else:
                print(f"  -> Failed to download from URL")
        else:
            print(f"  -> No logo URL found in yfinance")
    except Exception as e:
        print(f"  -> Error: {e}")

print(f"\nMissing symbols (with valid security names) count: {len(missing_syms)}")
if missing_syms:
    print("Sample missing symbols:", missing_syms[:10])
