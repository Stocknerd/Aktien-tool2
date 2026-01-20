import pandas as pd
import yfinance as yf
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_MSCI_EM_RAW = BASE_DIR / "msci_em_raw.csv"
FILE_MSCI_WORLD_RAW = BASE_DIR / "msci_world_raw.csv"
FILE_TICKER_RESOLVED = BASE_DIR / "data" / "ticker_resolved.csv"

# Re-use resolution logic (simplified import or copy-paste due to context)
LOCATION_SUFFIX_EM = {
    "Taiwan": ".TW", "China": ".SS", "Korea (South)": ".KS", "India": ".NS",
    "Brazil": ".SA", "South Africa": ".JO", "Saudi Arabia": ".SR", "Mexico": ".MX",
    "Thailand": ".BK", "Indonesia": ".JK", "Malaysia": ".KL", "United Arab Emirates": ".AE",
    "Qatar": ".QA", "Poland": ".WA", "Turkey": ".IS", "Philippines": ".PS",
    "Chile": ".SN", "Greece": ".AT", "Hungary": ".BD", "Czech Republic": ".PR",
    "Egypt": ".CA", "Kuwait": ".KW"
}
EXCHANGE_SUFFIX_EM = {
    "Hong Kong Exchanges And Clearing Ltd": ".HK", "Shanghai Stock Exchange": ".SS",
    "Shenzhen Stock Exchange": ".SZ", "Korea Exchange (Kosdaq)": ".KQ",
    "Korea Exchange (Stock Market)": ".KS", "Bse Ltd": ".BO", "National Stock Exchange Of India": ".NS",
    "XBSP": ".SA", "Johannesburg Stock Exchange": ".JO", "Saudi Stock Exchange": ".SR",
    "Bolsa Mexicana De Valores": ".MX", "Stock Exchange Of Thailand": ".BK",
    "Indonesia Stock Exchange": ".JK", "Bursa Malaysia": ".KL", "Dubai Financial Market": ".AE",
    "Abu Dhabi Securities Exchange": ".AE", "Qatar Exchange": ".QA",
    "Warsaw Stock Exchange/Equities/Main Market": ".WA", "Istanbul Stock Exchange": ".IS",
    "Philippine Stock Exchange Inc.": ".PS", "Santiago Stock Exchange": ".SN",
    "Athens Exchange S.A. Cash Market": ".AT", "Budapest Stock Exchange": ".BD",
    "Prague Stock Exchange": ".PR", "Egyptian Exchange": ".CA", "Kuwait Stock Exchange": ".KW",
    "Taiwan Stock Exchange": ".TW", "Gretai Securities Market": ".TWO",
    "New York Stock Exchange Inc.": "", "NASDAQ": "", "London Stock Exchange": ".L"
}

def resolve_yahoo_ticker_em(row):
    orig = str(row["Ticker"]).strip().replace('"', '')
    loc = str(row["Location"]).strip().replace('"', '')
    exch = str(row["Exchange"]).strip().replace('"', '')
    suffix = ""
    if exch in EXCHANGE_SUFFIX_EM: suffix = EXCHANGE_SUFFIX_EM[exch]
    elif loc in LOCATION_SUFFIX_EM: suffix = LOCATION_SUFFIX_EM[loc]
    if loc == "United States" or exch in ["NASDAQ", "New York Stock Exchange Inc."]: suffix = ""
    
    if suffix == ".HK" and orig.isdigit() and len(orig) < 4: orig = orig.zfill(4)
    if (suffix == ".TW" or suffix == ".TWO") and " " in orig: orig = orig.split(" ")[0]
    
    return f"{orig}{suffix}"

def check_missing():
    print("Checking for missing large caps...")
    
    # Load Resolved
    resolved = pd.read_csv(FILE_TICKER_RESOLVED)
    existing_tickers = set(resolved["valid_yahoo_ticker"].astype(str))
    
    # 1. Check MSCI EM (likely candidates here since we cut off at 350)
    try:
        em = pd.read_csv(FILE_MSCI_EM_RAW, skiprows=2)
        em = em[em["Asset Class"] == "Equity"].copy()
        em["valid_yahoo_ticker"] = em.apply(resolve_yahoo_ticker_em, axis=1)
        
        # Sort by Weight 
        em["Weight (%)"] = pd.to_numeric(em["Weight (%)"].astype(str).str.replace(",", ""), errors='coerce')
        em = em.sort_values("Weight (%)", ascending=False)
        
        missing_mask = ~em["valid_yahoo_ticker"].isin(existing_tickers)
        missing_em = em[missing_mask].copy()
        
        # Check the top 50 missing EM stocks
        candidates = missing_em.head(50)
        print(f"Checking top {len(candidates)} missing EM stocks for Market Cap > 10B...")
        
        potential_giants = []
        tickers_to_fetch = candidates["valid_yahoo_ticker"].tolist()
        
        # Fetch batch
        # yfinance can handle space separated string
        # chunking to be safe
        chunk_size = 20
        for i in range(0, len(tickers_to_fetch), chunk_size):
            chunk = tickers_to_fetch[i:i+chunk_size]
            try:
                tickers_objs = yf.Tickers(" ".join(chunk))
                for t in chunk:
                    info = tickers_objs.tickers[t].info
                    mcap = info.get("marketCap", 0)
                    name = info.get("shortName", "")
                    if mcap > 10_000_000_000: # 10 Billion
                        # Convert to USD roughly if needed? 
                        # info['marketCap'] is usually in local currency? 
                        # WAIT. yfinance marketCap is in the currency of the exchange.
                        # We need USD.
                        # info['currency'] tells us the currency.
                        
                        currency = info.get("currency", "USD")
                        rate = 1.0 # Default USD
                        
                        # Very rough manual rates for key currencies to filter strictly
                        # This is a heuristic check.
                        if currency == "TWD": rate = 0.03
                        elif currency == "INR": rate = 0.012
                        elif currency == "KRW": rate = 0.00075
                        elif currency == "HKD": rate = 0.128
                        elif currency == "CNY": rate = 0.14
                        elif currency == "BRL": rate = 0.20
                        elif currency == "ZAR": rate = 0.05
                        elif currency == "SAR": rate = 0.26
                        elif currency == "EUR": rate = 1.09
                        elif currency == "GBP": rate = 1.27
                        elif currency == "MXN": rate = 0.058
                        
                        mcap_usd = mcap * rate
                        
                        if mcap_usd > 8_000_000_000: # Look for > 8B to be safe for 10B target
                            row = candidates[candidates["valid_yahoo_ticker"] == t].iloc[0]
                            potential_giants.append({
                                "Ticker": t,
                                "Name": row["Name"],
                                "Sector": row["Sector"],
                                "Weight": row["Weight (%)"],
                                "Mcap_USD_Est": f"{mcap_usd/1e9:.2f}B",
                                "Country": row["Location"]
                            })
            except Exception as e:
                print(f"Error fetching chunk {chunk}: {e}")
            
            time.sleep(1)

        print("\n--- Missing EM Stocks likely > $8-10B ---")
        if potential_giants:
            df_giants = pd.DataFrame(potential_giants)
            print(df_giants.to_string(index=False))
            # Save suggestions
            df_giants.to_csv("missing_giants.csv", index=False)
        else:
            print("None found in the top 50 missing EM stocks.")

    except Exception as e:
        print(f"Error checking EM: {e}")

if __name__ == "__main__":
    check_missing()
