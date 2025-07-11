#!/usr/bin/env python3
"""
update_csv.py – lädt Finanzkennzahlen via Yahoo Finance in Batches und aktualisiert stock_data.csv.

• Batch‑Download reduziert HTTP‑Aufrufe (Default 75 Ticker pro Request)
• Threads disabled, um Yahoo‑Rate‑Limit einzuhalten
• Division‑by‑Zero‑Check bei Free‑Cash‑Flow‑Yield
"""

import time
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm
import yfinance as yf

# --------------------------------------------------
# Konfiguration
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
FILE_INPUT = BASE_DIR / "data" / "ticker_resolved.csv"
FILE_OUTPUT = BASE_DIR / "stock_data.csv"

BATCH_SIZE = 75       # Anzahl Symbole pro yf.download‑Call
SLEEP_GROUP = 2       # Sekunden Pause zwischen Gruppen (Rate‑Limit‑Safety)

# --------------------------------------------------
# CSV einlesen & Grundgerüst vorbereiten
# --------------------------------------------------
heute = datetime.today().strftime("%Y-%m-%d")

df = pd.read_csv(FILE_INPUT)
df = df[df["valid_yahoo_ticker"].notnull()].copy()

tickers = df["valid_yahoo_ticker"].tolist()

SPALTEN_KENNZAHLEN = [
    "Währung", "Region", "Sektor", "Branche",
    "Vortagesschlusskurs", "Dividendenrendite", "Ausschüttungsquote",
    "KGV", "Forward PE", "KBV", "KUV", "PEG-Ratio",
    "EV/EBITDA", "EBIT", "Bruttomarge", "Operative Marge", "Nettomarge",
    "Marktkapitalisierung", "Free Cashflow", "Free Cashflow Yield", "Operativer Cashflow",
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    "Umsatzwachstum 10J", "Umsatzwachstum 3J (erwartet)", "Gewinn je Aktie", "Gewinnwachstum 5J",
    "Verschuldungsgrad", "Interest Coverage", "Current Ratio", "Quick Ratio",
    "Beta", "52Wochen Hoch", "52Wochen Tief", "52Wochen Change",
    "Analysten_Kursziel", "Empfehlungsdurchschnitt",
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest",
]

for col in SPALTEN_KENNZAHLEN + ["Abfragedatum", "Datenquelle"]:
    if col not in df.columns:
        df[col] = None

# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------

def chunkify(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def map_info(info: dict):
    """Extrahiert nur die Felder, die wir benötigen."""
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

# --------------------------------------------------
# Haupt‑Batch‑Loop
# --------------------------------------------------
fehlgeschlagen = []

for grp in tqdm(chunkify(tickers, BATCH_SIZE), total=math.ceil(len(tickers)/BATCH_SIZE), desc="Batch-Downloads"):
    try:
        yf.download(
            grp,
            period="1y",
            group_by="ticker",
            threads=False,  # wichtig: serialisiert, um Sleep zu respektieren
            progress=False,
        )
    except Exception as err:
        print(f"⚠️ Batch‑Fehler {grp[:5]}…: {err}")
        fehlgeschlagen.extend(grp)
        time.sleep(10)
        continue

    for ticker in grp:
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as e:
            print(f"⚠️ Fehler bei {ticker}: {e}")
            fehlgeschlagen.append(ticker)
            continue

        idx = df.index[df["valid_yahoo_ticker"] == ticker][0]
        changed = False

        for key, val in map_info(info).items():
            if key in SPALTEN_KENNZAHLEN and val is not None and pd.notna(val):
                if pd.isna(df.at[idx, key]) or df.at[idx, key] != val:
                    df.at[idx, key] = val
                    changed = True

        # Free‑Cash‑Flow‑Yield (ebenfalls gegen 0 checken)
        fc = df.at[idx, "Free Cashflow"]
        mc = df.at[idx, "Marktkapitalisierung"]
        if pd.notna(fc) and pd.notna(mc) and mc != 0:
            df.at[idx, "Free Cashflow Yield"] = fc / mc
            changed = True

        if changed:
            df.at[idx, "Abfragedatum"] = heute
            df.at[idx, "Datenquelle"] = "Yahoo Finance"

    time.sleep(SLEEP_GROUP)

# --------------------------------------------------
# Speichern & Report
# --------------------------------------------------
# ------------------------------------------------------------
#  Statusmeldung zu eventuell fehlgeschlagenen Ticks
# ------------------------------------------------------------
if fehlgeschlagen:
    print(f"⚠️ Fehlgeschlagene Ticker: {len(fehlgeschlagen)} – z. B. {fehlgeschlagen[:10]}")

# ------------------------------------------------------------
#  CSV NUR speichern, wenn genügend Datensätze gültig sind
# ------------------------------------------------------------
erfolg_total   = len(df)                 # df = DataFrame mit allen ERFOLGreichen Rows
ticker_total   = len(tickers)            # komplette Wunschliste
mind_quote     = 0.80                    # 80 % Mindest-Erfolgsquote

if ticker_total == 0:
    print("❌ Ticker-Liste leer – CSV bleibt unverändert.")
elif erfolg_total / ticker_total < mind_quote:
    print(
        f"❌ Nur {erfolg_total}/{ticker_total} Ticker erfolgreich "
        f"({erfolg_total/ticker_total:.0%}) – CSV bleibt unverändert."
    )
else:
    df.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ Fertig – Daten in '{FILE_OUTPUT.name}' gespeichert "
          f"({erfolg_total}/{ticker_total} Ticker).")

