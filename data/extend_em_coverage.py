import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_MSCI_EM_RAW = BASE_DIR / "msci_em_raw.csv"
FILE_TICKER_RESOLVED = BASE_DIR / "data" / "ticker_resolved.csv"

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
    "Indonesia Stock Exchange": ".JK", "Bursa Malaysia": ".KL",
    "Dubai Financial Market": ".AE", # Yahoo often uses .AE for DFM too
    "Abu Dhabi Securities Exchange": ".AE", # Yahoo often uses .AE for ADX too
    "Qatar Exchange": ".QA",
    "Warsaw Stock Exchange/Equities/Main Market": ".WA", "Istanbul Stock Exchange": ".IS",
    "Philippine Stock Exchange Inc.": ".PS", "Santiago Stock Exchange": ".SN",
    "Athens Exchange S.A. Cash Market": ".AT", "Budapest Stock Exchange": ".BD",
    "Prague Stock Exchange": ".PR", "Egyptian Exchange": ".CA", "Kuwait Stock Exchange": ".KW",
    "Taiwan Stock Exchange": ".TW", "Gretai Securities Market": ".TWO",
    "New York Stock Exchange Inc.": "", "NASDAQ": "", "London Stock Exchange": ".L"
}

def clean_ticker_for_yahoo(ticker, suffix):
    ticker = str(ticker).strip().replace('"', '')
    if suffix == ".HK" and ticker.isdigit() and len(ticker) < 4:
        ticker = ticker.zfill(4)
    if (suffix == ".TW" or suffix == ".TWO") and " " in ticker:
        ticker = ticker.split(" ")[0]
    return f"{ticker}{suffix}"

def resolve_yahoo_ticker_em(row):
    orig = str(row["Ticker"]).strip().replace('"', '')
    loc = str(row["Location"]).strip().replace('"', '')
    exch = str(row["Exchange"]).strip().replace('"', '')
    suffix = ""
    if exch in EXCHANGE_SUFFIX_EM: suffix = EXCHANGE_SUFFIX_EM[exch]
    elif loc in LOCATION_SUFFIX_EM: suffix = LOCATION_SUFFIX_EM[loc]
    if loc == "United States" or exch in ["NASDAQ", "New York Stock Exchange Inc."]: suffix = ""
    return clean_ticker_for_yahoo(orig, suffix)

def process_msci_em_extended():
    print("Loading MSCI EM holdings (Extended Check)...")
    em = pd.read_csv(FILE_MSCI_EM_RAW, skiprows=2)
    em = em[em["Asset Class"] == "Equity"].copy()
    
    # Sort by weight
    try:
        em["Weight (%)"] = pd.to_numeric(em["Weight (%)"].astype(str).str.replace(",", ""), errors='coerce')
        em = em.sort_values("Weight (%)", ascending=False)
    except:
        pass

    em["valid_yahoo_ticker"] = em.apply(resolve_yahoo_ticker_em, axis=1)
    
    resolved = pd.read_csv(FILE_TICKER_RESOLVED)
    existing_tickers = set(resolved["valid_yahoo_ticker"].astype(str))
    
    missing_mask = ~em["valid_yahoo_ticker"].isin(existing_tickers)
    missing = em[missing_mask].copy()
    
    # EXPANDED LIMIT: Top 1000 missing
    # This should cover everything down to ~0.01% weight (small caps)
    top_missing = missing.head(1000)
    
    print(f"Adding next {len(top_missing)} missing EM tickers to resolved list.")
    
    # List some prominent names for the user
    examples = top_missing.head(10)[["Name", "Location", "Sector"]].to_dict('records')
    print("Examples of large caps being added:")
    for ex in examples:
        print(f"- {ex['Name']} ({ex['Location']}, {ex['Sector']})")

    if not top_missing.empty:
        to_add = pd.DataFrame({
            "valid_yahoo_ticker": top_missing["valid_yahoo_ticker"],
            "resolved_name": top_missing["Name"],
            "Sektor": top_missing["Sector"],
            "SourceIndex": "MSCI EM Extended"
        })
        to_add = to_add.drop_duplicates(subset=["valid_yahoo_ticker"])
        
        combined = pd.concat([resolved, to_add], ignore_index=True)
        combined.to_csv(FILE_TICKER_RESOLVED, index=False, encoding="utf-8-sig")
        print(f"Updated ticker_resolved.csv. New Total: {len(combined)}")

if __name__ == "__main__":
    process_msci_em_extended()
