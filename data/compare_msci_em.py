import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_MSCI_EM_RAW = BASE_DIR / "msci_em_raw.csv"
FILE_TICKER_RESOLVED = BASE_DIR / "data" / "ticker_resolved.csv"

# Global suffix mapping based on iShares "Location" or "Exchange" for EM
# Note: iShares CSV usually has "Location" and "Exchange".
# "Location" acts as a primary geographical filter.
LOCATION_SUFFIX_EM = {
    "Taiwan": ".TW",
    "China": ".SS", # Default, but need logic for Shanghai vs Shenzhen vs Hong Kong
    "Korea (South)": ".KS", # Most KOSPI. KOSDAQ is .KQ
    "India": ".NS", # NSE is standard
    "Brazil": ".SA",
    "South Africa": ".JO",
    "Saudi Arabia": ".SR",
    "Mexico": ".MX",
    "Thailand": ".BK",
    "Indonesia": ".JK",
    "Malaysia": ".KL",
    "United Arab Emirates": ".AE", # Dubai .DU? Abu Dhabi .AD? Need check
    "Qatar": ".QA",
    "Poland": ".WA",
    "Turkey": ".IS",
    "Philippines": ".PS",
    "Chile": ".SN",
    "Greece": ".AT",
    "Hungary": ".BD",
    "Czech Republic": ".PR",
    "Egypt": ".CA",
    "Kuwait": ".KW",
    # Add others as encountered
}

# Specific exchange overrides if Location isn't enough
EXCHANGE_SUFFIX_EM = {
    "Hong Kong Exchanges And Clearing Ltd": ".HK",
    "Shanghai Stock Exchange": ".SS",
    "Shenzhen Stock Exchange": ".SZ",
    "Korea Exchange (Kosdaq)": ".KQ",
    "Korea Exchange (Stock Market)": ".KS",
    "Bse Ltd": ".BO", # Bombay Stock Exchange
    "National Stock Exchange Of India": ".NS",
    "XBSP": ".SA", # B3 Brazil
    "Johannesburg Stock Exchange": ".JO",
    "Saudi Stock Exchange": ".SR",
    "Bolsa Mexicana De Valores": ".MX",
    "Stock Exchange Of Thailand": ".BK",
    "Indonesia Stock Exchange": ".JK",
    "Bursa Malaysia": ".KL",
    "Dubai Financial Market": ".DU", # Yahoo uses .DU for Dubai? No, often just suffix
    "Abu Dhabi Securities Exchange": ".AD", # Yahoo uses .AD?? Often not available or different
    "Qatar Exchange": ".QA",
    "Warsaw Stock Exchange/Equities/Main Market": ".WA",
    "Istanbul Stock Exchange": ".IS",
    "Philippine Stock Exchange Inc.": ".PS",
    "Santiago Stock Exchange": ".SN",
    "Athens Exchange S.A. Cash Market": ".AT",
    "Budapest Stock Exchange": ".BD",
    "Prague Stock Exchange": ".PR",
    "Egyptian Exchange": ".CA",
    "Kuwait Stock Exchange": ".KW",
    "Taiwan Stock Exchange": ".TW",
    "Gretai Securities Market": ".TWO", # Taiwan OTC
    "New York Stock Exchange Inc.": "", # ADRs usually no suffix
    "NASDAQ": "",
    "London Stock Exchange": ".L",
}

# Special ticker cleanup for Yahoo
def clean_ticker_for_yahoo(ticker, suffix):
    ticker = str(ticker).strip().replace('"', '')
    
    # Korea: 6 digits. Yahoo often Ticker.KS
    # Taiwan: 4 digits. Yahoo Ticker.TW
    # Hong Kong: 4 digits (usually no leading zeros in Yahoo if <4?? No, Yahoo usually takes "0700.HK" or "700.HK" -> "0700.HK")
    # Actually checking: "0700.HK" works. "700.HK" often works too. iShares has "700".
    
    # India: "RELIANCE" -> "RELIANCE.NS". iShares has "RELIANCE". Good.
    
    if suffix == ".HK":
        # Ensure 4 chars with leading zeros for HK ??
        # iShares: "700". Yahoo: "0700.HK" is preferred usually.
        if ticker.isdigit() and len(ticker) < 4:
            ticker = ticker.zfill(4)
            
    if suffix == ".TW" or suffix == ".TWO":
        # usually just the number
        pass
        
    return f"{ticker}{suffix}"

def resolve_yahoo_ticker_em(row):
    orig_ticker = str(row["Ticker"]).strip().replace('"', '')
    location = str(row["Location"]).strip().replace('"', '')
    exchange = str(row["Exchange"]).strip().replace('"', '')
    
    # Determine Suffix
    suffix = ""
    
    # 1. Check Exchange Map (Specific)
    if exchange in EXCHANGE_SUFFIX_EM:
        suffix = EXCHANGE_SUFFIX_EM[exchange]
    # 2. Check Location Map (General)
    elif location in LOCATION_SUFFIX_EM:
        suffix = LOCATION_SUFFIX_EM[location]
        
    # Special Handling for ADRs (US Listed)
    if location in ["United States"] or exchange in ["NASDAQ", "New York Stock Exchange Inc."]:
        suffix = "" 
        
    # Clean Ticker
    final_ticker = clean_ticker_for_yahoo(orig_ticker, suffix)
    
    return final_ticker

def process_msci_em():
    print("Loading MSCI EM holdings...")
    try:
        # Load raw data, skip first 2 lines
        em = pd.read_csv(FILE_MSCI_EM_RAW, skiprows=2)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Filter for Equities
    if "Asset Class" in em.columns:
        em = em[em["Asset Class"] == "Equity"].copy()
    
    print(f"Total Equity holdings in MSCI EM: {len(em)}")
    
    # Resolve Tickers
    em["valid_yahoo_ticker"] = em.apply(resolve_yahoo_ticker_em, axis=1)
    
    # Load resolved data
    if not FILE_TICKER_RESOLVED.exists():
        print("ticker_resolved.csv not found!")
        return
        
    resolved = pd.read_csv(FILE_TICKER_RESOLVED)
    existing_tickers = set(resolved["valid_yahoo_ticker"].astype(str))
    
    # Find missing
    missing_mask = ~em["valid_yahoo_ticker"].isin(existing_tickers)
    missing = em[missing_mask].copy()
    
    # Filter out empty tickers or failed resolutions (e.g. cash)
    missing = missing[missing["valid_yahoo_ticker"] != ""]
    
    # Optional: Filter for "Important" stocks?
    # Maybe limit to top X by weight?
    # Let's verify weight column. "Weight (%)"
    # To avoid 3000 tiny stocks? 
    # For now, let's take top 500 missing ones by weight?
    # Or just all? 3000 is manageable if we update slowly.
    # User asked for "Important stocks from Emerging Markets".
    # Taking top 200-300 by weight from the missing set seems prudent to avoid junk.
    
    try:
        missing["Weight (%)"] = pd.to_numeric(missing["Weight (%)"].astype(str).str.replace(",", ""), errors='coerce')
        missing = missing.sort_values("Weight (%)", ascending=False)
    except:
        pass

    # Let's take top 350 missing stocks to start with.
    top_missing = missing.head(350)
    
    print(f"Found {len(missing)} tickers missing in ticker_resolved.csv.")
    print(f"Selecting top {len(top_missing)} by weight to add.")
    
    if not top_missing.empty:
        # Prepare for addition
        to_add = pd.DataFrame({
            "valid_yahoo_ticker": top_missing["valid_yahoo_ticker"],
            "resolved_name": top_missing["Name"],
            "Sektor": top_missing["Sector"],
            "SourceIndex": "MSCI EM Top"
        })
        
        # Deduplicate
        to_add = to_add.drop_duplicates(subset=["valid_yahoo_ticker"])
        
        print(f"Adding {len(to_add)} unique NEW tickers to ticker_resolved.csv...")
        
        combined = pd.concat([resolved, to_add], ignore_index=True)
        combined.to_csv(FILE_TICKER_RESOLVED, index=False, encoding="utf-8-sig")
        print(f"Updated {FILE_TICKER_RESOLVED.name} with new total of {len(combined)} tickers.")
    else:
        print("No (significant) missing tickers found.")

if __name__ == "__main__":
    process_msci_em()
