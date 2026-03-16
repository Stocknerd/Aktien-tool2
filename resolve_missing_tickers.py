import pandas as pd
import yfinance as yf
import time
from tqdm import tqdm
import os
import random

def search_ticker(query, retries=3):
    for i in range(retries):
        try:
            search = yf.Search(query, max_results=5)
            results = search.quotes
            if not results:
                return None
            
            # Return first active common stock if possible
            for res in results:
                if res.get('quoteType') == 'EQUITY' or res.get('typeDisp') == 'Equity':
                    symbol = res.get('symbol')
                    # Basic validation: check if symbol looks like a ticker
                    if symbol and len(symbol) <= 12:
                        return symbol
            return results[0].get('symbol')
        except Exception as e:
            if "Connection" in str(e) or "reset" in str(e):
                wait = (i + 1) * 2
                print(f"Connection error for {query}, retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                print(f"Error searching for {query}: {e}")
                return None
    return None

def main():
    csv_path = 'stock_data.csv'
    if not os.path.exists(csv_path):
        print(f"File {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    # Identify rows missing symbol
    mask = df['Symbol'].isna() | (df['Symbol'] == '')
    missing_count = mask.sum()
    print(f"Found {missing_count} rows missing Symbol.")

    if missing_count == 0:
        print("Nothing to do.")
        return

    # To avoid losing progress, we process in chunks or save periodically
    updated_indices = df[mask].index.tolist()
    
    processed = 0
    found = 0
    
    try:
        for idx in tqdm(updated_indices, desc="Resolving Tickers"):
            row = df.loc[idx]
            name = row.get('Langname')
            if pd.isna(name) or not str(name).strip():
                name = row.get('Security')
            
            if pd.isna(name) or not str(name).strip():
                continue
                
            land = row.get('Land', '')
            base_name = str(name).strip()
            
            # Try 1: Name + Land
            query = base_name
            if not pd.isna(land) and str(land).strip():
                query += f" {str(land).strip()}"
            
            ticker = search_ticker(query)
            
            # Try 2: Just Name (if Try 1 failed)
            if not ticker and " {str(land).strip()}" in query:
                ticker = search_ticker(base_name)
            
            if ticker:
                df.at[idx, 'Symbol'] = ticker
                if 'valid_yahoo_ticker' in df.columns:
                    df.at[idx, 'valid_yahoo_ticker'] = ticker
                found += 1
            
            processed += 1
            
            # Save periodically
            if processed % 50 == 0:
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # Slightly longer random delay to be less "bot-like"
            time.sleep(random.uniform(0.6, 1.2))
            
    except KeyboardInterrupt:
        print("Interrupted by user. Saving current progress...")
    finally:
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"Finished. Resolved {found} out of {processed} processed rows.")

if __name__ == "__main__":
    main()
