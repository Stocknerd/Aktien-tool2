#!/usr/bin/env python3
# check_data_quality.py
#
# Analyzes stock_data.csv to report on:
# 1. Data Freshness (when was the last update?)
# 2. Completeness (how many missing values in key columns?)
# 3. Coverage (how many "important" tickers are missing data?)

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
FILE_DATA = BASE_DIR / "stock_data.csv"
FILE_TICKERS = BASE_DIR / "data" / "ticker_resolved.csv"

def check_freshness(df):
    print("\n--- 1. Data Freshness ---")
    if "Abfragedatum" not in df.columns:
        print("'Abfragedatum' column missing!")
        return

    # Convert to datetime
    df["Abfragedatum"] = pd.to_datetime(df["Abfragedatum"], errors="coerce")
    
    total = len(df)
    today = datetime.now().date()
    
    # Fresh (today)
    fresh = df[df["Abfragedatum"].dt.date == today]
    print(f"Updated Today ({today}): {len(fresh)} / {total} ({len(fresh)/total:.1%})")
    
    # Recent (last 7 days)
    recent = df[df["Abfragedatum"] >= pd.Timestamp(today) - pd.Timedelta(days=7)]
    print(f"Updated last 7 days: {len(recent)} / {total} ({len(recent)/total:.1%})")
    
    # Stale (> 30 days)
    stale = df[df["Abfragedatum"] < pd.Timestamp(today) - pd.Timedelta(days=30)]
    print(f"Stale (>30 days): {len(stale)} / {total}")
    
    if not stale.empty:
        print("   Sample stale tickers:", stale["valid_yahoo_ticker"].head(5).tolist())

def check_completeness(df):
    print("\n--- 2. Data Completeness ---")
    key_cols = ["Vortagesschlusskurs", "KGV", "Marktkapitalisierung", "Dividendenrendite"]
    
    for col in key_cols:
        if col not in df.columns:
            print(f"Column '{col}' missing")
            continue
            
        missing = df[col].isna().sum()
        total = len(df)
        print(f"   {col}: {total - missing} present, {missing} missing ({missing/total:.1%})")

def check_coverage(df):
    print("\n--- 3. Index Coverage ---")
    if not FILE_TICKERS.exists():
        print("No ticker_resolved.csv found to compare against.")
        return

    df_tickers = pd.read_csv(FILE_TICKERS)
    
    # Check if 'SourceIndex' exists
    if "SourceIndex" in df_tickers.columns:
        indices = df_tickers["SourceIndex"].dropna().unique()
        for idx in indices:
            subset = df_tickers[df_tickers["SourceIndex"] == idx]
            stock_subset = df[df["valid_yahoo_ticker"].isin(subset["valid_yahoo_ticker"])]
            
            total_idx = len(subset)
            found_in_csv = len(stock_subset)
            
            # Check meaningful data (e.g. Price is set)
            valid_in_csv = stock_subset["Vortagesschlusskurs"].notna().sum() if "Vortagesschlusskurs" in stock_subset.columns else 0
            
            print(f"   {idx}: {found_in_csv}/{total_idx} present in CSV. {valid_in_csv} have price data.")
    else:
        print("'SourceIndex' not available in ticker list.")

def main():
    if not FILE_DATA.exists():
        print(f"File not found: {FILE_DATA}")
        return

    print(f"Analyzing {FILE_DATA.name}...")
    df = pd.read_csv(FILE_DATA)
    print(f"Total Rows: {len(df)}")
    
    check_freshness(df)
    check_completeness(df)
    check_coverage(df)
    print("\n------------------------------")

if __name__ == "__main__":
    main()
