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

# Liste aller Kennzahlen-Spalten
spalten_kennzahlen = [
    # Grunddaten
    "Währung", "Region", "Sektor", "Branche",
    # Kurse & Dividende
    "Vortagesschlusskurs", "Dividendenrendite", "Ausschüttungsquote",
    # Basis-Multiples
    "KGV", "Forward PE", "KBV", "KUV", "PEG-Ratio",
    # Unternehmenswert-Multiples
    "EV/EBITDA",
    # Profitabilität & Margen
    "EBIT", "Bruttomarge", "Operative Marge", "Nettomarge",
    # Kapital & Cashflow
    "Marktkapitalisierung", "Free Cashflow", "Free Cashflow Yield", "Operativer Cashflow",
    # Rentabilität
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    # Wachstum
    "Umsatzwachstum 10J", "Umsatzwachstum 3J (erwartet)", "Gewinn je Aktie", "Gewinnwachstum 5J",
    # Verschuldung & Liquidität
    "Verschuldungsgrad", "Interest Coverage", "Current Ratio", "Quick Ratio",
    # Risiko & Markt
    "Beta", "52Wochen Hoch", "52Wochen Tief", "52Wochen Change",
    # Analysten-Daten
    "Analysten_Kursziel", "Empfehlungsdurchschnitt",
    # Eigentümerstruktur
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest"
]
spalten = spalten_kennzahlen + ["Abfragedatum", "Datenquelle"]

# CSV einlesen und vorbereiten
df = pd.read_csv(FILE_INPUT)
df = df[df['valid_yahoo_ticker'].notnull()].copy()
df[spalten] = None

def get_financial_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    # Hole alle Rohdaten
    currency    = info.get("currency")
    region      = info.get("region")
    sector      = info.get("sector")
    industry    = info.get("industry")
    prev_close  = info.get("previousClose")
    div_yield   = info.get("dividendYield")
    payout      = info.get("payoutRatio")
    pe_trail    = info.get("trailingPE")
    pe_forward  = info.get("forwardPE")
    pb_ratio    = info.get("priceToBook")
    ps_ratio    = info.get("priceToSalesTrailing12Months")
    peg_ratio   = info.get("pegRatio")
    ebit        = info.get("ebit")
    ev          = info.get("enterpriseValue")
    market_cap  = info.get("marketCap")
    gross_mgn   = info.get("grossMargins")
    op_mgn      = info.get("operatingMargins")
    net_mgn     = info.get("netMargins")
    roe         = info.get("returnOnEquity")
    roa         = info.get("returnOnAssets")
    roic        = info.get("returnOnCapital")
    fcf         = info.get("freeCashflow")
    ocf         = info.get("operatingCashflow")
    debt_eq     = info.get("debtToEquity")
    icov       = info.get("interestCoverage")
    curr_ratio  = info.get("currentRatio")
    quick_ratio = info.get("quickRatio")
    beta        = info.get("beta")
    high52      = info.get("fiftyTwoWeekHigh")
    low52       = info.get("fiftyTwoWeekLow")
    chg52       = info.get("52WeekChange")
    tgt_price   = info.get("targetMeanPrice")
    rec_mean    = info.get("recommendationMean")
    ins_pct     = info.get("heldPercentInsiders")
    inst_pct    = info.get("heldPercentInstitutions")
    short_pct   = info.get("shortPercentOfFloat")
    # Umsatzwachstum (aktuelles Jahr) als Proxy
    rev_growth  = info.get("revenueGrowth")
    # Gewinnwachstum vierteljährlich
    eps_forward = info.get("forwardEps")
    earn_qtr_g  = info.get("earningsQuarterlyGrowth")

<<<<<<< Updated upstream
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
=======
    # Zusammengesetzte Kennzahlen
    ev_ebitda = (ev / info["ebitda"]) if ev and info.get("ebitda") else None
    fcf_yield = (fcf / market_cap) if fcf and market_cap else None

    return [
        currency, region, sector, industry,
        prev_close, div_yield, payout,
        pe_trail, pe_forward, pb_ratio, ps_ratio, peg_ratio,
        ebit, ev_ebitda,
        gross_mgn, op_mgn, net_mgn,
        market_cap, roe, roa, roic,
        fcf, fcf_yield, ocf,
        rev_growth, rev_growth,
        eps_forward, earn_qtr_g,
        debt_eq, icov, curr_ratio, quick_ratio,
        beta, high52, low52, chg52,
        tgt_price, rec_mean,
        ins_pct, inst_pct, short_pct
    ]

>>>>>>> Stashed changes
fehlgeschlagen = []
fehler_counter = 0

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Daten werden abgerufen"):
    ticker = row["valid_yahoo_ticker"]
    try:
        daten = get_financial_data(ticker)
        if all(d is None for d in daten):
            fehler_counter += 1
            fehlgeschlagen.append(ticker)
        else:
            df.loc[idx, spalten] = daten + [heute, "Yahoo Finance"]
    except Exception:
        fehler_counter += 1
        fehlgeschlagen.append(ticker)
    time.sleep(1)

# Speichern
df.to_csv(FILE_OUTPUT, index=False)
print(f"Fertig! Datei gespeichert unter: {FILE_OUTPUT}")
print(f"Fehlgeschlagene Abfragen: {fehler_counter}", fehlgeschlagen)
