import yfinance as yf

tickers = ["MSFT", "META", "GOOGL"]
for t in tickers:
    info = yf.Ticker(t).info
    div = info.get("dividendYield")
    print(f"{t}: {div} (Type: {type(div)})")
