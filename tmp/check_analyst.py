import pandas as pd
df = pd.read_csv('stock_data.csv')
r = df[df['Symbol']=='AAPL'].iloc[0]
print('Recommendation Key:', r.get('Recommendation Key'))
print('Analyst Mean Target:', r.get('Analyst Mean Target'))
print('Current Price:', r.get('Current Price'))
print('Number of Analysts:', r.get('Number of Analysts'))
