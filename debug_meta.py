import pandas as pd

try:
    df = pd.read_csv("stock_data.csv")
    targets = ["META", "GOOGL", "GOOG", "MSFT", "KO"]
    rows = df[df["Symbol"].isin(targets)]
    
    # Check relevant columns
    cols = ["Symbol", "Dividendenrendite", "dividendYield", "Div.-Rendite", "Abfragedatum"]
    # Filter valid columns
    cols = [c for c in cols if c in df.columns]
    
    print(rows[cols])
except Exception as e:
    print(f"Error: {e}")
