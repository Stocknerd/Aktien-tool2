import pandas as pd
from datetime import datetime
import yfinance as yf
from tqdm import tqdm



# Neue CSV-Datei mit validierten Tickern einlesen
file_path = 'data/ticker_resolved.csv'

df = pd.read_csv(file_path)

# Nur gültige Ticker verarbeiten
df = df[df['valid_yahoo_ticker'].notnull()].copy()

# Aktuelles Datum erfassen
heute = datetime.today().strftime('%Y-%m-%d')

# Neue Kennzahlen-Spalten definieren
spalten_kennzahlen = [
    "Währung", "Region", "Sektor", "Branche",
    "Vortagesschlusskurs", "Dividendenrendite", "Ausschüttungsquote", "KGV", "KUV",
    "EBIT", "Marktkapitalisierung", "Eigenkapitalrendite", "Free Cashflow",
    "Operativer Cashflow", "Umsatzwachstum 10J", "Umsatzwachstum 3J (erwartet)",
    "Gewinn je Aktie", "Gewinnwachstum 5J", "Verschuldungsgrad"
]
spalten = spalten_kennzahlen + ["Abfragedatum", "Datenquelle"]
df[spalten] = None


# Funktion zur Abfrage der Finanzdaten aus yfinance
def get_financial_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Wenn kritische Felder fehlen oder leer sind → Fehler auslösen
        required_keys = ["sector", "marketCap", "previousClose"]
        if not all(k in info and info[k] is not None for k in required_keys):
            raise ValueError(f"Unvollständige Daten für {ticker}")

        return [
            info.get("currency"),
            info.get("region"),
            info.get("sector"),
            info.get("industry"),
            info.get("previousClose"),
            info.get("dividendYield"),
            info.get("payoutRatio"),
            info.get("trailingPE"),
            info.get("priceToSalesTrailing12Months"),
            info.get("ebit"),
            info.get("marketCap"),
            info.get("returnOnEquity"),
            info.get("freeCashflow"),
            info.get("operatingCashflow"),
            info.get("revenueGrowth"),
            info.get("revenueGrowth"),
            info.get("forwardEps"),
            info.get("earningsQuarterlyGrowth"),
            info.get("debtToEquity")
        ]

    except Exception as e:
        print(f"⚠️ Fehler bei {ticker}: {e}")
        return [None] * len(spalten)


# Fortschrittsbalken und Fehlerprotokollierung
fehlgeschlagen = []
fehler_counter = 0

import time  # für sleep

# Daten abrufen
for index, row in tqdm(df.iterrows(), total=len(df), desc="Daten werden abgerufen"):
    ticker = row["valid_yahoo_ticker"]
    data = get_financial_data(ticker)
    if all(d is None for d in data):
        fehler_counter += 1
        fehlgeschlagen.append(ticker)
    else:
                                        df.loc[index, spalten] = data + [heute, "Yahoo Finance"]
    time.sleep(1)  # Vermeide zu viele Anfragen

# Ergebnis speichern
output_path = 'stock_data.csv'
df.to_csv(output_path, index=False)

print(f"Fertig! Datei gespeichert unter: {output_path}")
print(f"Fehlgeschlagene Abfragen: {fehler_counter}")


