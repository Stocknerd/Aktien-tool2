import pandas as pd
import sys

# Test-Script für weitere potenzielle Prozent-Bugs

try:
    df = pd.read_csv("stock_data.csv")
    
    # Teste Aktien mit bekannten Werten
    test_tickers = ["MSFT", "META", "GOOGL", "AAPL", "TSLA"]
    
    # Relevante Spalten
    cols = ["Symbol", "Dividendenrendite", "Gewinnwachstum", "5Y Dividendenrendite", 
            "Verschuldungsgrad", "Bruttomarge", "Operative Marge", "Nettomarge"]
    
    # Filter vorhandene Spalten
    existing_cols = ["Symbol"] + [c for c in cols[1:] if c in df.columns]
    
    subset = df[df["Symbol"].isin(test_tickers)][existing_cols]
    
    print("=" * 80)
    print("PRÜFUNG: Prozent-Metriken (Rohdaten aus CSV)")
    print("=" * 80)
    print(subset.to_string(index=False))
    print("\n" + "=" * 80)
    print("ERWARTETE WERTE:")
    print("=" * 80)
    print("Dividendenrendite: < 5% (typisch 0.3-2%)")
    print("Gewinnwachstum: -100% bis +200% (kann negativ sein)")
    print("5Y Dividendenrendite: < 10% (historischer Durchschnitt)")
    print("Verschuldungsgrad: 0-300% (Schulden/Eigenkapital)")
    print("Margen: 0-100% (typisch 5-40%)")
    print("=" * 80)
    
    # Prüfe auf Ausreißer
    print("\nPRÜFUNG AUF VERDÄCHTIGE WERTE:")
    for col in existing_cols[1:]:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors='coerce')
            max_val = subset[col].max()
            if max_val > 100:
                print(f"⚠️  {col}: MAX={max_val:.2f} (könnte falsch skaliert sein!)")
            elif max_val > 10 and "Dividenden" in col:
                print(f"⚠️  {col}: MAX={max_val:.2f} (Dividenden >10% unwahrscheinlich!)")
            else:
                print(f"✓  {col}: MAX={max_val:.2f}")
                
except Exception as e:
    print(f"Fehler: {e}", file=sys.stderr)
    sys.exit(1)
