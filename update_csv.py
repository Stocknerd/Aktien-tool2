import pandas as pd
from datetime import datetime
import yfinance as yf
from tqdm import tqdm
import time

# Pfade
FILE_INPUT  = 'data/ticker_resolved.csv'
FILE_OUTPUT = 'stock_data.csv'

# Aktuelles Datum
heute = datetime.today().strftime('%Y-%m-%d')

# Spaltenliste
spalten_kennzahlen = [
    "Währung", "Region", "Sektor", "Branche",
    "Vortagesschlusskurs", "Dividendenrendite", "Ausschüttungsquote",
    "KGV", "Forward PE", "KBV", "KUV", "PEG-Ratio",
    "EV/EBITDA",
    "EBIT", "Bruttomarge", "Operative Marge", "Nettomarge",
    "Marktkapitalisierung", "Free Cashflow", "Free Cashflow Yield", "Operativer Cashflow",
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    "Umsatzwachstum 10J", "Umsatzwachstum 3J (erwartet)", "Gewinn je Aktie", "Gewinnwachstum 5J",
    "Verschuldungsgrad", "Interest Coverage", "Current Ratio", "Quick Ratio",
    "Beta", "52Wochen Hoch", "52Wochen Tief", "52Wochen Change",
    "Analysten_Kursziel", "Empfehlungsdurchschnitt",
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest"
]
spalten = spalten_kennzahlen + ["Abfragedatum", "Datenquelle"]

# CSV einlesen und vorbereiten
df = pd.read_csv(FILE_INPUT)
df = df[df['valid_yahoo_ticker'].notnull()].copy()
for col in spalten:
    if col not in df.columns:
        df[col] = None

def get_financial_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        return {
            "Währung": info.get("currency"),
            "Region": info.get("region"),
            "Sektor": info.get("sector"),
            "Branche": info.get("industry"),
            "Vortagesschlusskurs": info.get("previousClose"),
            "Dividendenrendite": info.get("dividendYield"),
            "Ausschüttungsquote": info.get("payoutRatio"),
            "KGV": info.get("trailingPE"),
            "Forward PE": info.get("forwardPE"),
            "KBV": info.get("priceToBook"),
            "KUV": info.get("priceToSalesTrailing12Months"),
            "PEG-Ratio": info.get("pegRatio"),
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "EBIT": info.get("ebit"),
            "Bruttomarge": info.get("grossMargins"),
            "Operative Marge": info.get("operatingMargins"),
            "Nettomarge": info.get("netMargins"),
            "Marktkapitalisierung": info.get("marketCap"),
            "Free Cashflow": info.get("freeCashflow"),
            "Operativer Cashflow": info.get("operatingCashflow"),
            "Eigenkapitalrendite": info.get("returnOnEquity"),
            "Return on Assets": info.get("returnOnAssets"),
            "ROIC": info.get("returnOnCapital"),
            # Umsatzwachstum über 10 Jahre liefert yfinance nicht direkt;
            # hier vorerst None. Eine manuelle Berechnung aus historischen Jahresabschlüssen wäre nötig.
            "Umsatzwachstum 10J": None,
            "Umsatzwachstum 3J (erwartet)": info.get("revenueGrowth"),
            "Gewinn je Aktie": info.get("forwardEps"),
            "Gewinnwachstum 5J": info.get("earningsQuarterlyGrowth"),
            "Verschuldungsgrad": info.get("debtToEquity"),
            "Interest Coverage": info.get("interestCoverage"),
            "Current Ratio": info.get("currentRatio"),
            "Quick Ratio": info.get("quickRatio"),
            "Beta": info.get("beta"),
            "52Wochen Hoch": info.get("fiftyTwoWeekHigh"),
            "52Wochen Tief": info.get("fiftyTwoWeekLow"),
            "52Wochen Change": info.get("52WeekChange"),
            "Analysten_Kursziel": info.get("targetMeanPrice"),
            "Empfehlungsdurchschnitt": info.get("recommendationMean"),
            "Insider_Anteil": info.get("heldPercentInsiders"),
            "Institutioneller_Anteil": info.get("heldPercentInstitutions"),
            "Short Interest": info.get("shortPercentOfFloat"),
        }
    except Exception as e:
        print(f"⚠️ Fehler bei {ticker}: {e}")
        return {}

fehlgeschlagen = []
fehler_counter = 0

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Daten werden abgerufen"):
    ticker = row["valid_yahoo_ticker"]
    data = get_financial_data(ticker)

    if not data:
        fehlgeschlagen.append(ticker)
        fehler_counter += 1
        continue

    # Schreibe alle zurückgegebenen Kennzahlen in das DataFrame
    for key, value in data.items():
        if key in spalten_kennzahlen:
            df.at[idx, key] = value

    # Free Cashflow Yield berechnen (falls Free Cashflow & Marktkapitalisierung vorhanden)
    fc = data.get("Free Cashflow")
    mc = data.get("Marktkapitalisierung")
    if fc is not None and mc:
        try:
            df.at[idx, "Free Cashflow Yield"] = fc / mc
        except Exception:
            df.at[idx, "Free Cashflow Yield"] = None

    # Abfragedatum und Datenquelle setzen
    df.at[idx, "Abfragedatum"] = heute
    df.at[idx, "Datenquelle"] = "Yahoo Finance"

    # Kurz warten, um Rate-Limits abzudämpfen
    time.sleep(0.1)

# Ausgabe der fehlgeschlagenen Ticker (falls vorhanden)
if fehlgeschlagen:
    print(f"Anzahl fehlgeschlagener Abfragen: {fehler_counter}")
    print("Folgende Ticker konnten nicht abgefragt werden:")
    for t in fehlgeschlagen:
        print(f" - {t}")

# Ergebnis in CSV schreiben
df.to_csv(FILE_OUTPUT, index=False, encoding='utf-8-sig')
print(f"Fertig! Alle Daten wurden in '{FILE_OUTPUT}' geschrieben.")
