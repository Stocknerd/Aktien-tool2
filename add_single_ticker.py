import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def add_ticker(ticker_symbol, csv_path):
    print(f"Fetching data for {ticker_symbol}...")
    from curl_cffi import requests as curl_requests
    session = curl_requests.Session(impersonate="chrome")
    ticker = yf.Ticker(ticker_symbol, session=session)
    info = ticker.info
    
    if not info or 'symbol' not in info:
        print(f"Error: Could not find data for {ticker_symbol}")
        return

    # Map yfinance info to CSV columns
    # Adjust mapping based on stock_data.csv header
    data = {
        "Symbol": ticker_symbol,
        "Security": info.get("longName", ticker_symbol),
        "GICS Sector": info.get("sector", ""),
        "valid_yahoo_ticker": ticker_symbol,
        "resolved_name": info.get("longName", ""),
        "resolved_exchange": info.get("exchange", ""),
        "resolved_score": 1.0,
        "SourceIndex": "MANUAL",
        "Sektor": info.get("sector", ""),
        "Währung": info.get("currency", "USD"),
        "Region": info.get("country", ""),
        "Branche": info.get("industry", ""),
        "Vortagesschlusskurs": info.get("previousClose", info.get("currentPrice")),
        "Dividendenrendite": info.get("dividendYield"), 
        "Ausschüttungsquote": info.get("payoutRatio", 0) * 100 if info.get("payoutRatio") else None,
        "KGV": info.get("trailingPE"),
        "Forward PE": info.get("forwardPE"),
        "KBV": info.get("priceToBook"),
        "KUV": info.get("priceToSalesTrailing12Months"),
        "PEG-Ratio": info.get("pegRatio"),
        "EV/EBITDA": info.get("enterpriseToEbitda"),
        "EBIT": info.get("ebitda"), # simplified
        "Bruttomarge": info.get("grossMargins", 0) * 100 if info.get("grossMargins") else None,
        "Operative Marge": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None,
        "Nettomarge": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None,
        "Marktkapitalisierung": info.get("marketCap"),
        "Free Cashflow": info.get("freeCashflow"),
        "Free Cashflow Yield": (info.get("freeCashflow") / info.get("marketCap")) if info.get("freeCashflow") and info.get("marketCap") else None,
        "Operativer Cashflow": info.get("operatingCashflow"),
        "Eigenkapitalrendite": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
        "Return on Assets": info.get("returnOnAssets", 0) * 100 if info.get("returnOnAssets") else None,
        "ROIC": None,
        "Umsatzwachstum 3J (erwartet)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None,
        "Abfragedatum": datetime.now().strftime("%Y-%m-%d"),
        "Datenquelle": "Yahoo Finance (Manual)"
    }
    
    new_row = pd.DataFrame([data])
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Remove existing if already there
        df = df[df['Symbol'] != ticker_symbol]
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(csv_path, index=False)
        print(f"Successfully added/updated {ticker_symbol} in {csv_path}")
    else:
        new_row.to_csv(csv_path, index=False)
        print(f"Created {csv_path} and added {ticker_symbol}")

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "KO"
    add_ticker(ticker, "stock_data.csv")
