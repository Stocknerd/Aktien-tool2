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
    'Nikkei 225 (Japan)': {
        'url': 'https://en.wikipedia.org/wiki/Nikkei_225',
        'match': 'Company',
        'ticker_col': 'Code', # Changed for Nikkei
        'name_col': 'Company',
        'suffix': '.T'
    },
    'S&P 500 (USA)': {
        'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'match': 'Symbol',
        'ticker_col': 'Symbol',
        'name_col': 'Security',
        'suffix': ''
    },
    'Taiwan 50 (Taiwan)': {
        'url': 'https://en.wikipedia.org/wiki/FTSE_TWSE_Taiwan_50_Index',
        'match': 'Ticker', # Try Ticker
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.TW'
    }
}

df_local = pd.read_csv('stock_data.csv', dtype=str)
fixed_count = 0
added_count = 0

for idx_name, info in indices.items():
    print(f"Processing {idx_name}...")
    try:
        # For Nikkei, the table has different headers sometimes, let's catch it
        df_idx = get_wiki_table(info['url'], info['match'])
        
        # Nikkei 'Code' column is sometimes 'Ticker' or 'Code'
        if idx_name == 'Nikkei 225 (Japan)':
            if 'Code' not in df_idx.columns and 'Ticker' in df_idx.columns:
                 info['ticker_col'] = 'Ticker'
            elif 'Code' not in df_idx.columns and 'Ticker' not in df_idx.columns and 'Symbol' in df_idx.columns:
                 info['ticker_col'] = 'Symbol'
            elif 'Code' not in df_idx.columns:
                 # fallback, assume it's the thirtieth column or something, or print columns to debug
                 print(f"Nikkei columns: {df_idx.columns}")
                 info['ticker_col'] = df_idx.columns[0]
             
        for _, row in df_idx.iterrows():
            if str(row[info['ticker_col']]) == 'nan': continue
            raw_ticker = str(row[info['ticker_col']]).replace('.0', '').strip()
            raw_ticker = raw_ticker.replace('.', '-')
            yf_ticker = raw_ticker + info['suffix']
            
            comp_name = str(row[info['name_col']]).replace('\n', '').strip()
            
            # Recompute symbols to catch newly added ones!
            local_symbols = set(df_local['Symbol'].dropna().unique())
            
            if yf_ticker in local_symbols:
                continue # All good
            
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
                # Add as completely new row
                new_row = {'Symbol': yf_ticker, 'Langname': comp_name, 'Sektor': 'Unknown', 'Industrie': 'Unknown'}
                df_local = pd.concat([df_local, pd.DataFrame([new_row])], ignore_index=True)
                print(f"[{idx_name}] ADDED: {comp_name} ({yf_ticker})")
                added_count += 1
                
    except Exception as e:
        print(f"Error processing {idx_name}: {e}")

df_local = df_local.drop_duplicates(subset=['Symbol'], keep='first')
df_local.to_csv('stock_data.csv', index=False)
print(f"\nFinished! Fixed {fixed_count} existing mappings and added {added_count} completely new tickers.")
