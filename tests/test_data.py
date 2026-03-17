import pandas as pd
import sys

# Test-Script für weitere potenzielle Prozent-Bugs

import os

# Test-Script für weitere potenzielle Prozent-Bugs

CSV_PATH = "stock_data.csv"

def test_csv_data_quality():
    """Test data quality in stock_data.csv if available."""
    CSV_PATH = "stock_data.csv"
    if not os.path.exists(CSV_PATH):
        print(f"SKIPPING: {CSV_PATH} not found.")
        return

    try:
        df = pd.read_csv(CSV_PATH)
        
        # Teste Aktien mit bekannten Werten
        test_tickers = ["MSFT", "META", "GOOGL", "AAPL", "TSLA"]
        
        # Relevante Spalten
        cols = ["Symbol", "Dividendenrendite", "Gewinnwachstum", "5Y Dividendenrendite", 
                "Verschuldungsgrad", "Bruttomarge", "Operative Marge", "Nettomarge"]
        
        # Filter vorhandene Spalten
        existing_cols = ["Symbol"] + [c for c in cols[1:] if c in df.columns]
        
        subset = df[df["Symbol"].isin(test_tickers)][existing_cols]
        
        print("\n" + "=" * 80)
        print("PRÜFUNG: Prozent-Metriken (Rohdaten aus CSV)")
        print("=" * 80)
        print(subset.to_string(index=False))
        
        # Prüfe auf Ausreißer
        for col in existing_cols[1:]:
            if col in subset.columns:
                subset[col] = pd.to_numeric(subset[col], errors='coerce')
                max_val = subset[col].max()
                if max_val > 500: # Allow for high growth but flag extreme outliers
                    print(f"⚠️  {col}: MAX={max_val:.2f} (Extremer Wert!)")
                    
    except Exception as e:
        pytest.fail(f"Fehler bei Datenprüfung: {e}")
