import pandas as pd
import requests

def get_wiki_table(url, match_str):
    header = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=header)
    tables = pd.read_html(r.text, match=match_str)
    return tables[0]

indices = {
    'SDAX (Germany)': {
        'url': 'https://en.wikipedia.org/wiki/SDAX',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.DE'
    },
    'MDAX (Germany)': {
        'url': 'https://en.wikipedia.org/wiki/MDAX',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.DE'
    },
    'TecDAX (Germany)': {
        'url': 'https://en.wikipedia.org/wiki/TecDAX',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.DE'
    },
    'Dow Jones (USA)': {
        'url': 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average',
        'match': 'Symbol',
        'ticker_col': 'Symbol',
        'name_col': 'Company',
        'suffix': ''
    },
    'Nasdaq-100 (USA)': {
        'url': 'https://en.wikipedia.org/wiki/Nasdaq-100',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': ''
    },
    'SMI (Switzerland)': {
        'url': 'https://en.wikipedia.org/wiki/Swiss_Market_Index',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.SW'
    },
    'IBEX 35 (Spain)': {
        'url': 'https://en.wikipedia.org/wiki/IBEX_35',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.MC'
    },
    'AEX (Netherlands)': {
        'url': 'https://en.wikipedia.org/wiki/AEX_index',
        'match': 'Ticker symbol',
        'ticker_col': 'Ticker symbol',
        'name_col': 'Company',
        'suffix': '.AS'
    },
    'FTSE MIB (Italy)': {
        'url': 'https://en.wikipedia.org/wiki/FTSE_MIB',
        'match': 'Ticker',
        'ticker_col': 'Ticker',
        'name_col': 'Company',
        'suffix': '.MI'
    }
}

df_local = pd.read_csv('stock_data.csv', dtype=str)
fixed_count = 0
added_count = 0

for idx_name, info in indices.items():
    print(f"Processing {idx_name}...")
    try:
        df_idx = get_wiki_table(info['url'], info['match'])
             
        for _, row in df_idx.iterrows():
            if str(row[info['ticker_col']]) == 'nan': continue
            raw_ticker = str(row[info['ticker_col']]).replace('.0', '').strip()
            raw_ticker = raw_ticker.replace('.', '-')
            yf_ticker = raw_ticker + info['suffix']
            
            comp_name = str(row[info['name_col']]).replace('\n', '').strip()
            
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
                new_row = {'Symbol': yf_ticker, 'Langname': comp_name, 'Sektor': 'Unknown', 'Industrie': 'Unknown'}
                df_local = pd.concat([df_local, pd.DataFrame([new_row])], ignore_index=True)
                print(f"[{idx_name}] ADDED: {comp_name} ({yf_ticker})")
                added_count += 1
                
    except Exception as e:
        print(f"Error processing {idx_name}: {e}")

df_local = df_local.drop_duplicates(subset=['Symbol'], keep='first')
df_local.to_csv('stock_data.csv', index=False)
print(f"\nFinished! Fixed {fixed_count} existing mappings and added {added_count} completely new tickers.")
