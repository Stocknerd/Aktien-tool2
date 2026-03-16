import pandas as pd

def clean_csv(path):
    df = pd.read_csv(path)
    if 'valid_yahoo_ticker' not in df.columns:
        return
    # Match Options (e.g. AAPL250321C00150000), Futures (=F), and Currencies (=X, XDR=X)
    mask = df['valid_yahoo_ticker'].str.contains(r'\d{6}[CP]\d{8}|=[FX]$|=X$', na=False, regex=True)
    drop_count = mask.sum()
    if drop_count > 0:
        df_clean = df[~mask]
        df_clean.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Removed {drop_count} derivatives/currencies from {path}")
    else:
        print(f"No derivatives found in {path}")

clean_csv('stock_data.csv')
clean_csv('data/ticker_resolved.csv')
