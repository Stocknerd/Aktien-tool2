import pandas as pd
import requests

def get_wiki_table(url, match_str):
    header = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=header)
    tables = pd.read_html(r.text, match=match_str)
    return tables[0]

indices = {
    'DAX (Germany)': {
        'url': 'https://en.wikipedia.org/wiki/DAX',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.DE'
    },
    'CAC 40 (France)': {
        'url': 'https://en.wikipedia.org/wiki/CAC_40',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.PA'
    },
    'FTSE 100 (UK)': {
        'url': 'https://en.wikipedia.org/wiki/FTSE_100_Index',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.L'
    },
    'S&P 500 (USA)': {
        'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'match': 'Symbol',
        'ticker_col': 'Symbol',
        'name_col': 'Security',
        'suffix': ''
    }
}

df_local = pd.read_csv('stock_data.csv', dtype=str)
local_symbols = set(df_local['Symbol'].dropna().unique())
local_names = df_local['Langname'].dropna().str.lower().tolist()
local_name_to_symbol = dict(zip(df_local['Langname'].dropna().str.lower(), df_local['Symbol'].dropna()))

report = []

for idx_name, info in indices.items():
    print(f"Fetching {idx_name}...")
    try:
        df_idx = get_wiki_table(info['url'], info['match'])
        for _, row in df_idx.iterrows():
            raw_ticker = str(row[info['ticker_col']]).strip()
            # Clean ticker (e.g. BRK.B -> BRK-B for Yahoo finance)
            raw_ticker = raw_ticker.replace('.', '-')
            yf_ticker = raw_ticker + info['suffix']
            
            comp_name = str(row[info['name_col']]).strip()
            
            # Check if yf_ticker is in our DB
            if yf_ticker in local_symbols:
                continue # All good
            
            # If ticker is missing, check if company name is in DB under a wrong ticker
            found_by_name = False
            for ln, lsym in local_name_to_symbol.items():
                # Simple substring match for names (e.g. 'Apple Inc.' vs 'Apple')
                if comp_name.lower() in ln or ln in comp_name.lower():
                    if len(comp_name) > 4:
                        report.append(f"[{idx_name}] Ticker Mismatch: {comp_name} is in DB as '{lsym}', but official Yahoo Ticker is '{yf_ticker}'")
                        found_by_name = True
                        break
            
            if not found_by_name:
                report.append(f"[{idx_name}] Missing Completely: {comp_name} ({yf_ticker}) is not in DB.")
                
    except Exception as e:
        print(f"Error processing {idx_name}: {e}")

print("\n--- AUDIT REPORT ---\n")
for r in report:
    print(r)
print(f"\nTotal Issues Found: {len(report)}")

with open('audit_report.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(report))
