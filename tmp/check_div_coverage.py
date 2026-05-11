import pandas as pd
df = pd.read_csv('stock_data.csv')
print(f'Total stocks: {len(df)}')
dy = pd.to_numeric(df['Dividendenrendite'], errors='coerce')
print(f'With yield > 0: {(dy > 0).sum()}')
has_ex = df['Ex-Dividenden-Datum'].notna()
print(f'With Ex-Date: {has_ex.sum()}')
print(f'With Ex-Date AND yield > 0: {(has_ex & (dy > 0)).sum()}')
print()
print('Sectors of dividend payers:')
print(df[dy > 0]['Sektor'].value_counts().to_string())
print()
print('Available metric columns:')
for c in ['KGV','Forward PE','KBV','KUV','PEG-Ratio','EV/EBITDA','Dividendenrendite','Ausschüttungsquote','Marktkapitalisierung']:
    if c in df.columns:
        valid = pd.to_numeric(df[c], errors='coerce').notna().sum()
        print(f'  {c}: {valid} stocks with data')
