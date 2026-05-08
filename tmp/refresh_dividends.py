import pandas as pd
import yfinance as yf
from datetime import datetime
import concurrent.futures
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core

CSV_FILE = core.CSV_FILE

def fetch_div(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        ex_date = info.get("exDividendDate")
        return {
            "Symbol": ticker,
            "Ex-Dividenden-Datum": datetime.fromtimestamp(ex_date).strftime("%Y-%m-%d") if ex_date else None,
            "Dividenden-Betrag": info.get("dividendRate") or info.get("trailingAnnualDividendRate"),
            "Dividendenrendite": info.get("dividendYield")
        }
    except:
        return None

def main():
    print("Starting specialized Dividend Refresh...")
    df = pd.read_csv(CSV_FILE)
    tickers = df['Symbol'].tolist()
    
    # Use 20 threads for speed
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(fetch_div, t): t for t in tickers[:500]} # Top 500 for now
        for future in concurrent.futures.as_completed(future_to_ticker):
            res = future.result()
            if res:
                results.append(res)
    
    # Merge back to DF
    div_df = pd.DataFrame(results)
    for col in ["Ex-Dividenden-Datum", "Dividenden-Betrag", "Dividendenrendite"]:
        if col not in df.columns:
            df[col] = None
            
    df.set_index('Symbol', inplace=True)
    div_df.set_index('Symbol', inplace=True)
    
    df.update(div_df)
    df.reset_index(inplace=True)
    
    df.to_csv(CSV_FILE, index=False)
    print(f"Successfully updated {len(results)} stocks with dividend data.")

if __name__ == "__main__":
    main()
