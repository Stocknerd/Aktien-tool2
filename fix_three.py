import pandas as pd
import yfinance as yf
import numpy as np

df = pd.read_csv('stock_data.csv', dtype=str)

# Fix Symbols first
df.loc[df['Langname'].str.contains('The Coca-Cola Company', na=False, case=False), 'Symbol'] = 'KO'
df.loc[df['Langname'].str.contains('Sixt SE', na=False, case=False), 'Symbol'] = 'SIX2.DE'
df.loc[df['Symbol'] == 'SIEMENS', 'Langname'] = 'Siemens AG'
df.loc[df['Symbol'] == 'SIEMENS', 'Symbol'] = 'SIE.DE'

tickers = ['KO', 'SIX2.DE', 'SIE.DE']
for t in tickers:
    try:
        info = yf.Ticker(t).info
        mask = df['Symbol'] == t
        if mask.any():
            df.loc[mask, 'Analysten_Empfehlung'] = info.get('recommendationKey')
            df.loc[mask, 'Analysten_Kursziel'] = info.get('targetMeanPrice')
            df.loc[mask, 'Dividendenrendite'] = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else np.nan
            df.loc[mask, 'KGV'] = info.get('trailingPE')
            df.loc[mask, 'Forward_PE'] = info.get('forwardPE')
            df.loc[mask, 'Industrie'] = info.get('industry', 'Unknown')
            df.loc[mask, 'Sektor'] = info.get('sector', 'Unknown')
            print(f"Updated {t}")
    except Exception as e:
        print(f"Error {t}: {e}")

df.to_csv('stock_data.csv', index=False)
print("Saved!")
