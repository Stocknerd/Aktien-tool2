import os
import json
from pathlib import Path
import pandas as pd
from core import load_df
from ai_logic import get_ai_long_analysis

def test_enhancement():
    print("Testing Blog Enhancement Logic...")
    df = load_df()
    # Pick AAPL if available for a grounded test
    symbol = "AAPL"
    row = df[df['Symbol'] == symbol].iloc[0]
    
    name = row.get('Security')
    financial_data = {
        "KGV": str(row.get("KGV", "N/A")),
        "Dividendenrendite": str(row.get("Dividendenrendite", "N/A"))
    }
    
    # Check if we can load the summary
    raw_data_dir = Path("data/raw")
    json_path = raw_data_dir / f"{symbol}.json"
    business_summary = ""
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_info = json.load(f)
            business_summary = raw_info.get("longBusinessSummary", "")
            print(f"Loaded summary for {symbol} ({len(business_summary)} characters)")
    
    print("Generating AI Long analysis with summary...")
    long_analysis = get_ai_long_analysis(symbol, name, financial_data, business_summary=business_summary)
    
    print("\n--- GENERATED CONTENT ---")
    print(long_analysis)
    print("-------------------------\n")
    
    if "Apple" in long_analysis and len(long_analysis) > 200:
        print("SUCCESS: Content seems rich and grounded.")
    else:
        print("FAILURE: Content generation failed or is too short.")

if __name__ == "__main__":
    test_enhancement()
