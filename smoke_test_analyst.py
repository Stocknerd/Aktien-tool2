import pandas as pd
from core import render_stock_card, load_df
import os

def smoke_test():
    df = load_df()
    aapl = df[df['Symbol'] == 'AAPL'].iloc[0].to_dict()
    
    print(f"Testing Symbol: {aapl.get('Symbol')}")
    # Verify we have the analyst keys
    keys = ["Analyst Mean Target", "Analyst High Target", "Analyst Low Target", "Number of Analysts", "Recommendation Key"]
    for k in keys:
        print(f"{k}: {aapl.get(k)}")
    
    # Try to render
    img = render_stock_card(aapl, selected=None, ai_verdict="AAPL Test Verdict")
    out_path = "test_aapl_analyst_fix.png"
    img.save(out_path)
    print(f"Saved test rendering to {out_path}")

if __name__ == "__main__":
    smoke_test()
