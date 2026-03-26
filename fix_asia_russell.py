import pandas as pd
import requests
import io

def get_wiki_table(url, match_str):
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    r = requests.get(url, headers=header)
    if r.status_code != 200:
        print(f"Error fetching {url}: {r.status_code}")
        return None
    tables = pd.read_html(io.StringIO(r.text), match=match_str)
    return tables[0]

indices = {
    'Hang Seng (Hong Kong)': {
        'url': 'https://en.wikipedia.org/wiki/Hang_Seng_Index',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Name',
        'suffix': '.HK'
    },
    'KOSPI 200 (South Korea)': {
        'url': 'https://en.wikipedia.org/wiki/KOSPI_200',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.KS'
    },
    'Nifty 50 (India)': {
        'url': 'https://en.wikipedia.org/wiki/NIFTY_50',
        'match': 'Symbol',
        'ticker_col': 'Symbol',
        'name_col': 'Company name',
        'suffix': '.NS'
    },
    'Straits Times (Singapore)': {
        'url': 'https://en.wikipedia.org/wiki/Straits_Times_Index',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Stock',
        'suffix': '.SI'
    },
    'Russell 1000 (USA)': {
        'url': 'https://en.wikipedia.org/wiki/Russell_1000_Index',
        'match': 'Symbol',
        'ticker_col': 'Symbol',
        'name_col': 'Company',
        'suffix': ''
    }
}

df_local = pd.read_csv('stock_data.csv', dtype=str)
fixed_count = 0
added_count = 0

for idx_name, info in indices.items():
    print(f"Processing {idx_name}...")
    try:
        df_idx = get_wiki_table(info['url'], info['match'])
        if df_idx is None: continue
        
        ticker_col = info['ticker_col']
        name_col = info['name_col']
        
        is_hk = idx_name == 'Hang Seng (Hong Kong)'
             
        for _, row in df_idx.iterrows():
            if ticker_col not in row or str(row[ticker_col]) == 'nan': continue
            raw_ticker = str(row[ticker_col]).replace('.0', '').strip()
            
            if is_hk:
                raw_ticker = raw_ticker.zfill(4)
                
            raw_ticker = raw_ticker.replace('.', '-')
            yf_ticker = raw_ticker + info['suffix']
            
            comp_name = str(row[name_col]).replace('\n', '').strip()
            
            local_symbols = set(df_local['Symbol'].dropna().unique())
            if yf_ticker in local_symbols:
                continue
            
            # Find in local by name
            found_by_name = False
            for idx, r in df_local.iterrows():
                if pd.isna(r['Langname']): continue
                ln = str(r['Langname']).lower()
                cn_low = comp_name.lower()
                if (cn_low in ln or ln in cn_low) and len(cn_low) >= 5:
                    df_local.at[idx, 'Symbol'] = yf_ticker
                    print(f"[{idx_name}] FIXED: {comp_name} -> {yf_ticker}")
                    fixed_count += 1
                    found_by_name = True
                    break
            
            if not found_by_name:
                new_row = {'Symbol': yf_ticker, 'Langname': comp_name, 'Sektor': 'Unknown', 'Industrie': 'Unknown'}
                df_local = pd.concat([df_local, pd.DataFrame([new_row])], ignore_index=True)
                print(f"[{idx_name}] ADDED: {comp_name} ({yf_ticker})")
                added_count += 1
                
    except Exception as e:
        print(f"Error processing {idx_name}: {e}")

df_local = df_local.drop_duplicates(subset=['Symbol'], keep='first')
df_local.to_csv('stock_data.csv', index=False)
print(f"\nFinished! Fixed {fixed_count} existing mappings and added {added_count} completely new tickers.")
