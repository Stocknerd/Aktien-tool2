import pandas as pd
import yfinance as yf
from datetime import datetime
import concurrent.futures

CSV = 'stock_data.csv'
df = pd.read_csv(CSV)
tickers = df['Symbol'].dropna().unique().tolist()[:50]
print(f'Testing with {len(tickers)} stocks...')

def fetch_div(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        ex_date_raw = info.get('exDividendDate')
        ex_date = None
        if ex_date_raw:
            ex_date = datetime.fromtimestamp(ex_date_raw).strftime('%Y-%m-%d')
        dy = info.get('dividendYield')
        if dy:
            dy = round(float(dy) * 100, 2)
        rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        if rate:
            rate = round(float(rate), 4)
        if dy or ex_date:
            return {'symbol': ticker, 'ex': ex_date, 'yield': dy, 'rate': rate}
    except:
        pass
    return None

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(fetch_div, t): t for t in tickers}
    for f in concurrent.futures.as_completed(futures):
        r = f.result()
        if r:
            results.append(r)

print(f'Got dividend data for {len(results)}/{len(tickers)} stocks')
for r in results[:15]:
    sym = r['symbol']
    y = r['yield']
    ex = r['ex']
    rate = r['rate']
    print(f'  {sym:8s} yield={y}%  ex={ex}  rate={rate}')
