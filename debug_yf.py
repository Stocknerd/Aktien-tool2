import yfinance as yf
info = yf.Ticker("AAPL").info
print("targetMeanPrice:", info.get("targetMeanPrice"))
print("targetHighPrice:", info.get("targetHighPrice"))
print("targetLowPrice:", info.get("targetLowPrice"))
print("currentPrice:", info.get("currentPrice"))
print("recommendationKey:", info.get("recommendationKey"))
