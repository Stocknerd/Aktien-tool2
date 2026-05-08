import yfinance as yf
from datetime import datetime

tickers = ["AAPL", "MSFT", "NSRGY", "ALV.DE", "MUV2.DE", "BMW.DE", "T", "VZ", "MAIN", "O"]

for t in tickers:
    tick = yf.Ticker(t)
    info = tick.info
    ex_date = info.get("exDividendDate")
    readable_date = datetime.fromtimestamp(ex_date).strftime("%Y-%m-%d") if ex_date else "N/A"
    print(f"{t:8} | Ex-Date: {readable_date:12} | Div-Rate: {info.get('dividendRate', 'N/A')} | Yield: {info.get('dividendYield', 'N/A')}")
