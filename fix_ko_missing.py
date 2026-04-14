#!/usr/bin/env python3
"""
Fix: Add KO (Coca-Cola) and repair COL resolved_name collision.
"""
import pandas as pd
import yfinance as yf
from datetime import date
import math

CSV_PATH = "stock_data.csv"

def fetch_ticker_data(symbol):
    """Fetch all relevant fields for a ticker from yfinance."""
    t = yf.Ticker(symbol)
    info = t.info

    def g(key, default=None):
        val = info.get(key, default)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return val

    # Analyst recommendation
    rec_key = g("recommendationKey", "")
    rec_map = {
        "strong_buy": "strong buy", "buy": "buy",
        "hold": "hold", "underperform": "underperform", "sell": "sell"
    }
    rec_str = rec_map.get(rec_key, rec_key)

    return {
        "Symbol": symbol,
        "Security": g("longName", symbol),
        "GICS Sector": g("sector", ""),
        "valid_yahoo_ticker": symbol,
        "resolved_name": g("longName", symbol),
        "resolved_exchange": g("exchange", ""),
        "resolved_score": 1000000,
        "SourceIndex": "SP500",
        "Sektor": g("sector", ""),
        "Währung": g("currency", "USD"),
        "Region": "US",
        "Branche": g("industry", ""),
        "Vortagesschlusskurs": g("previousClose"),
        "Dividendenrendite": round(g("dividendYield", 0) * 100, 4) if g("dividendYield") else None,
        "Ausschüttungsquote": g("payoutRatio"),
        "KGV": g("trailingPE"),
        "Forward PE": g("forwardPE"),
        "KBV": g("priceToBook"),
        "KUV": g("priceToSalesTrailing12Months"),
        "PEG-Ratio": g("pegRatio"),
        "EV/EBITDA": g("enterpriseToEbitda"),
        "EBIT": g("ebit"),
        "Bruttomarge": g("grossMargins"),
        "Operative Marge": g("operatingMargins"),
        "Nettomarge": g("profitMargins"),
        "Marktkapitalisierung": g("marketCap"),
        "Free Cashflow": g("freeCashflow"),
        "Free Cashflow Yield": None,
        "Operativer Cashflow": g("operatingCashflow"),
        "Eigenkapitalrendite": g("returnOnEquity"),
        "Return on Assets": g("returnOnAssets"),
        "ROIC": None,
        "Umsatzwachstum 3J (erwartet)": g("revenueGrowth"),
        "Empfehlungsdurchschnitt": g("recommendationMean"),
        "Anzahl Analystenmeinungen": g("numberOfAnalystOpinions"),
        "Analysten_Kursziel": g("targetMeanPrice"),
        "Kursziel_Hoch": g("targetHighPrice"),
        "Kursziel_Tief": g("targetLowPrice"),
        "Analysten_Empfehlung": rec_str,
        "Land": g("country", "United States"),
        "Langname": g("longName", symbol),
        "Verschuldungsgrad": g("debtToEquity"),
        "Current Ratio": g("currentRatio"),
        "Gesamtschulden": g("totalDebt"),
        "Beta": g("beta"),
        "52W Hoch": g("fiftyTwoWeekHigh"),
        "52W Tief": g("fiftyTwoWeekLow"),
        "Gewinnwachstum": g("earningsGrowth"),
        "5Y Dividendenrendite": g("fiveYearAvgDividendYield"),
        "Abfragedatum": str(date.today()),
        "Datenquelle": "Yahoo Finance",
        "Datenqualität": 0.9,
        "Fehlende_Kennzahlen": 0,
    }


def main():
    print("Loading stock_data.csv...")
    df = pd.read_csv(CSV_PATH)
    print(f"  Loaded {len(df)} rows.")

    # --- Fix 1: Add KO if not present ---
    ko_exists = df["Symbol"].str.upper().eq("KO").any()
    if ko_exists:
        print("KO already present — skipping add.")
    else:
        print("Fetching KO (Coca-Cola) data from yfinance...")
        ko_data = fetch_ticker_data("KO")
        print(f"  Name: {ko_data['resolved_name']}, Price: {ko_data['Vortagesschlusskurs']}")
        ko_row = pd.DataFrame([ko_data])
        # Align columns to match existing CSV
        for col in df.columns:
            if col not in ko_row.columns:
                ko_row[col] = None
        ko_row = ko_row[df.columns]
        df = pd.concat([df, ko_row], ignore_index=True)
        print(f"  KO added. Total rows now: {len(df)}")

    # --- Fix 2: Repair COL resolved_name (Coles Group wrongly tagged as Coca-Cola) ---
    col_mask = (df["Symbol"] == "COL") & (df["resolved_name"].str.contains("Coca", case=False, na=False))
    if col_mask.any():
        print(f"Fixing COL (Coles Group) resolved_name — currently '{df.loc[col_mask, 'resolved_name'].iloc[0]}'")
        df.loc[col_mask, "resolved_name"] = "Coles Group Ltd"
        df.loc[col_mask, "Langname"] = "Coles Group Ltd"
        print("  COL fixed.")
    else:
        print("COL resolved_name looks correct — no fix needed.")

    # --- Remove NaN-Symbol rows if they're Coca-Cola duplicates ---
    nan_coca = df["Symbol"].isna() & df["resolved_name"].str.contains("Coca", case=False, na=False)
    n_removed = nan_coca.sum()
    if n_removed > 0:
        df = df[~nan_coca]
        print(f"Removed {n_removed} stale NaN/Coca-Cola orphan rows.")

    # Save
    df.to_csv(CSV_PATH, index=False)
    print(f"Saved. Total rows: {len(df)}")

    # Verify
    check = df[df["Symbol"].str.upper().eq("KO")]
    if not check.empty:
        print(f"\nVerification - KO row:")
        print(f"  Symbol: {check.iloc[0]['Symbol']}")
        print(f"  Name:   {check.iloc[0]['resolved_name']}")
        print(f"  Price:  {check.iloc[0]['Vortagesschlusskurs']}")
        print(f"  Datum:  {check.iloc[0]['Abfragedatum']}")


if __name__ == "__main__":
    main()
