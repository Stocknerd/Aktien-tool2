import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILE_MSCI_RAW = BASE_DIR / "msci_world_raw.csv"
FILE_TICKER_RESOLVED = BASE_DIR / "data" / "ticker_resolved.csv"

# Global suffix mapping based on iShares "Location" or "Exchange"
LOCATION_SUFFIX = {
    "United States": "",
    "Netherlands": ".AS",
    "Switzerland": ".SW",
    "United Kingdom": ".L",
    "Germany": ".DE",
    "Canada": ".TO",
    "Japan": ".T",
    "Spain": ".MC",
    "Italy": ".MI",
    "Hong Kong": ".HK",
    "Australia": ".AX",
    "France": ".PA",
    "Denmark": ".CO",
    "Finland": ".HE",
    "Norway": ".OL",
    "Israel": ".TA",
    "Singapore": ".SI",
    "Sweden": ".ST",
}

def resolve_yahoo_ticker(row):
    ticker = str(row["Ticker"]).strip().replace('"', '')
    location = str(row["Location"]).strip().replace('"', '')
    
    # Special cases for classes
    if location == "United States":
        if ticker.endswith("B") and "CLASS B" in str(row["Name"]):
            # Berkshire BRKB -> BRK-B
            if ticker == "BRKB": return "BRK-B"
            # others usually .B or -B
        if ticker.endswith("A") and "CLASS A" in str(row["Name"]):
             # Alphabet GOOGL is fine, but some need dash
             pass

    suffix = LOCATION_SUFFIX.get(location, "")
    
    # Handle iShares format specific quirks
    # Example: "NOVO B" -> "NOVO-B.CO"
    if " " in ticker:
        ticker = ticker.replace(" ", "-")
        
    # Clean ticker from dots at the end (some iShares tickers have them like "RR.")
    if ticker.endswith("."):
        ticker = ticker[:-1]

    return f"{ticker}{suffix}"

def process_msci():
    print("Loading MSCI World holdings...")
    # Skip first 2 lines
    msci = pd.read_csv(FILE_MSCI_RAW, skiprows=2)
    
    # Filter for Equities
    msci = msci[msci["Asset Class"] == "Equity"].copy()
    
    print(f"Total Equity holdings in MSCI World: {len(msci)}")
    
    # Resolve Tickers
    msci["valid_yahoo_ticker"] = msci.apply(resolve_yahoo_ticker, axis=1)
    
    # Load resolved data
    if not FILE_TICKER_RESOLVED.exists():
        print("ticker_resolved.csv not found!")
        return
        
    resolved = pd.read_csv(FILE_TICKER_RESOLVED)
    existing_tickers = set(resolved["valid_yahoo_ticker"].astype(str))
    
    # Find missing
    missing_mask = ~msci["valid_yahoo_ticker"].isin(existing_tickers)
    missing = msci[missing_mask].copy()
    
    print(f"Found {len(missing)} tickers missing in ticker_resolved.csv")
    
    if not missing.empty:
        # Prepare for addition
        to_add = pd.DataFrame({
            "valid_yahoo_ticker": missing["valid_yahoo_ticker"],
            "resolved_name": missing["Name"],
            "Sektor": missing["Sector"],
            "SourceIndex": "MSCI World Full"
        })
        
        # Deduplicate
        to_add = to_add.drop_duplicates(subset=["valid_yahoo_ticker"])
        
        print(f"Adding {len(to_add)} unique NEW tickers to ticker_resolved.csv...")
        
        combined = pd.concat([resolved, to_add], ignore_index=True)
        combined.to_csv(FILE_TICKER_RESOLVED, index=False, encoding="utf-8-sig")
        print(f"Updated {FILE_TICKER_RESOLVED.name} with new total of {len(combined)} tickers.")
    else:
        print("No missing tickers found. Coverage is 100%.")

if __name__ == "__main__":
    process_msci()
