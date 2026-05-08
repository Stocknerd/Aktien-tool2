import pandas as pd
from core import render_compare, load_df
import os

def smoke_test_compare():
    df = load_df()
    aapl = df[df['Symbol'] == 'AAPL'].iloc[0]
    nvda = df[df['Symbol'] == 'NVDA'].iloc[0]
    
    metrics = ["KGV", "Forward PE", "KUV", "KBV", "Operative Marge", "Eigenkapitalrendite", "Dividendenrendite", "Umsatzwachstum 3J (erwartet)"]
    
    print(f"Testing Comparison: AAPL vs NVDA")
    
    # Try to render
    img = render_compare([aapl, nvda], metrics=metrics, fetch_analyst=True)
    out_path = "test_compare_analyst_fix.png"
    img.save(out_path)
    print(f"Saved test comparison rendering to {out_path}")

if __name__ == "__main__":
    smoke_test_compare()
