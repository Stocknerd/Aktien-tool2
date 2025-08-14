#!/usr/bin/env python3
"""
update_csv.py – Robustes Yahoo-Finance-Update für stock_data.csv

Änderungen ggü. der alten Version:
• Entfernt: Warming-Call via yf.download (reduziert Requests)
• Hinzugefügt: Retry mit Exponential Backoff + per‑Ticker‑Jitter
• Duplikat-fähige Updates (alle Zeilen je Ticker werden angepasst)
• Merge mit bestehender stock_data.csv, um alte Werte zu behalten
• Erfolgsquote misst tatsächliche Änderungen (nicht nur Zeilenzahl)
• Persistente Fehlversuchs-Liste in logs/
"""

from __future__ import annotations

import os
import math
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
from tqdm import tqdm
import yfinance as yf


# --------------------------------------------------
# Konfiguration
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

FILE_INPUT  = BASE_DIR / "data" / "ticker_resolved.csv"
FILE_OUTPUT = BASE_DIR / "stock_data.csv"
LOG_FOLDER  = BASE_DIR / "logs"

# Rate-Limit / Stabilität
BATCH_SIZE        = 40         # kleiner als vorher (75) → weniger Burst
SLEEP_GROUP       = 3          # Pause nach jeder Gruppe (Sekunden)
PER_TICKER_JITTER = (0.15, 0.35)  # per-Ticker Random-Sleep
MAX_TRIES         = 3          # Retries pro Ticker
BACKOFF_START     = 0.5        # Exponential Backoff (Sek.)
MIN_UPDATED_QUOTE = 0.80       # 80% der Ticker müssen mind. eine Spalte geändert haben, sonst speichern wir nicht

# Spalten-Definitionen
SPALTEN_KENNZAHLEN = [
    # Grunddaten
    "Währung", "Region", "Sektor", "Branche",
    # Kurse & Dividende
    "Vortagesschlusskurs", "Dividendenrendite", "Ausschüttungsquote",
    # Multiples
    "KGV", "Forward PE", "KBV", "KUV", "PEG-Ratio",
    # Unternehmenswert & Profitabilität
    "EV/EBITDA", "EBIT", "Bruttomarge", "Operative Marge", "Nettomarge",
    # Cashflows & Bewertung
    "Marktkapitalisierung", "Free Cashflow", "Free Cashflow Yield", "Operativer Cashflow",
    # Renditen
    "Eigenkapitalrendite", "Return on Assets", "ROIC",
    # Wachstum (Achtung: 10J aktuell nicht befüllt, siehe TODO)
    "Umsatzwachstum 10J", "Umsatzwachstum 3J (erwartet)", "Gewinn je Aktie", "Gewinnwachstum 5J",
    # Bilanz & Risiko
    "Verschuldungsgrad", "Interest Coverage", "Current Ratio", "Quick Ratio",
    "Beta", "52Wochen Hoch", "52Wochen Tief", "52Wochen Change",
    # Analysten & Besitz
    "Analysten_Kursziel", "Empfehlungsdurchschnitt",
    "Insider_Anteil", "Institutioneller_Anteil", "Short Interest",
]
META_SPALTEN = ["Abfragedatum", "Datenquelle"]


# --------------------------------------------------
# Utilities
# --------------------------------------------------
def chunkify(seq: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def map_info(info: Dict) -> Dict:
    """Extrahiert nur die benötigten Felder aus yfinance .info"""
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
        # Anmerkung: earningsQuarterlyGrowth ist kein "5J"-Wert – ggf. künftig umbenennen oder anders beschaffen.
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
        # TODO: "Umsatzwachstum 10J" ist in .info nicht direkt vorhanden – ggf. historisch berechnen.
    }


def get_info_with_retry(ticker: str, max_tries: int = MAX_TRIES, base_sleep: float = BACKOFF_START) -> Dict:
    """Holt yf.Ticker(t).info mit Jitter + Exponential Backoff."""
    last_err = None
    backoff = base_sleep
    for attempt in range(max_tries):
        try:
            time.sleep(random.uniform(*PER_TICKER_JITTER))
            info = yf.Ticker(ticker).info or {}
            return info
        except Exception as e:
            last_err = e
            time.sleep(backoff)
            backoff *= 2
    # nach max_tries fehlgeschlagen
    raise last_err


def ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df


def log_failed_tickers(failed: List[str]) -> None:
    if not failed:
        return
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = LOG_FOLDER / f"failed_{ts}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(failed))
    print(f"⚠️ Fehlgeschlagene Ticker: {len(failed)} – Beispiel: {failed[:10]}")
    print(f"   → Liste gespeichert unter: {path}")


# --------------------------------------------------
# Main
# --------------------------------------------------
def main() -> None:
    heute = datetime.today().strftime("%Y-%m-%d")

    # --- Eingabe laden
    if not FILE_INPUT.exists():
        raise FileNotFoundError(f"Eingabedatei nicht gefunden: {FILE_INPUT}")

    df = pd.read_csv(FILE_INPUT)
    if "valid_yahoo_ticker" not in df.columns:
        raise KeyError("Eingabedatei enthält keine Spalte 'valid_yahoo_ticker'.")

    # nur gültige Ticker
    df = df[df["valid_yahoo_ticker"].notna()].copy()

    # Zielspalten anlegen
    df = ensure_columns(df, SPALTEN_KENNZAHLEN + META_SPALTEN)

    # --- Bestehende stock_data.csv mergen (alte Werte behalten)
    if FILE_OUTPUT.exists():
        try:
            old = pd.read_csv(FILE_OUTPUT)
            # Wenn die alte Datei keine 'valid_yahoo_ticker' hat, versuchen wir mit 'Symbol'
            join_key = "valid_yahoo_ticker" if "valid_yahoo_ticker" in old.columns else (
                "Symbol" if "Symbol" in old.columns else None
            )
            if join_key and join_key in df.columns:
                # Suffix für alte Werte
                keep_cols = [c for c in old.columns if c in (SPALTEN_KENNZAHLEN + META_SPALTEN + ["valid_yahoo_ticker", "Symbol"])]
                old = old[keep_cols].copy()

                # Merge (Left, um unsere aktuelle Tickerliste als Basis zu behalten)
                merged = df.merge(old, on=join_key, how="left", suffixes=("", "_old"))

                # Für jede Kennzahl: wenn neu leer, alten Wert behalten
                for col in SPALTEN_KENNZAHLEN + META_SPALTEN:
                    if col + "_old" in merged.columns:
                        merged[col] = merged[col].where(merged[col].notna(), merged[col + "_old"])
                        merged.drop(columns=[col + "_old"], inplace=True)

                df = merged
            else:
                print("ℹ️ Konnte stock_data.csv nicht sinnvoll mergen (kein passender Join-Key).")
        except Exception as e:
            print(f"⚠️ Konnte bestehende stock_data.csv nicht mergen: {e}")

    tickers = df["valid_yahoo_ticker"].tolist()
    if not tickers:
        print("❌ Keine gültigen Ticker gefunden – Abbruch.")
        return

    # --- Verarbeitung
    fehlgeschlagen: List[str] = []
    updated_rows_count = 0     # gezählte, tatsächlich geänderte Zeilen
    success_info_calls = 0     # wie viele Ticker-Infos kamen ohne Exception zurück

    # Hinweis: KEIN yf.download Warming-Call mehr.
    total_batches = math.ceil(len(tickers) / BATCH_SIZE)

    for grp in tqdm(chunkify(tickers, BATCH_SIZE), total=total_batches, desc="Ticker-Gruppen"):
        for ticker in grp:
            try:
                info = get_info_with_retry(ticker)
                success_info_calls += 1
            except Exception as e:
                fehlgeschlagen.append(ticker)
                print(f"⚠️ Fehler bei {ticker} nach Retries: {e}")
                continue

            # Alle Zeilen mit diesem Ticker (Duplikate abdecken)
            mask = (df["valid_yahoo_ticker"] == ticker)
            if not mask.any():
                # sollte nicht passieren, zur Sicherheit
                continue

            changed_any_row = False

            # 1) Map direkte Felder
            mapped = map_info(info)
            for key, val in mapped.items():
                if key not in SPALTEN_KENNZAHLEN:
                    continue
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    continue

                current = df.loc[mask, key]
                to_update = current.isna() | (current != val)
                if to_update.any():
                    df.loc[mask & to_update, key] = val
                    changed_any_row = True

            # 2) Free Cashflow Yield (nur wenn FC & MK vorhanden)
            fc = df.loc[mask, "Free Cashflow"]
            mc = df.loc[mask, "Marktkapitalisierung"]

            valid = fc.notna() & mc.notna() & (mc != 0)
            if valid.any():
                fcfy_new = fc[valid] / mc[valid]
                current = df.loc[mask & valid, "Free Cashflow Yield"]
                to_update_yield = current.isna() | (current != fcfy_new)
                if to_update_yield.any():
                    df.loc[mask & valid & to_update_yield, "Free Cashflow Yield"] = fcfy_new
                    changed_any_row = True

            # 3) Meta-Spalten aktualisieren, wenn in dieser Runde etwas geändert wurde
            if changed_any_row:
                df.loc[mask, "Abfragedatum"] = heute
                df.loc[mask, "Datenquelle"] = "Yahoo Finance"
                updated_rows_count += int(mask.sum())

        time.sleep(SLEEP_GROUP)

    # --- Reporting & Speichern
    if fehlgeschlagen:
        log_failed_tickers(fehlgeschlagen)

    ticker_total = len(tickers)
    updated_ratio = (updated_rows_count / ticker_total) if ticker_total else 0.0

    print(f"ℹ️ Info-Calls erfolgreich: {success_info_calls}/{ticker_total}")
    print(f"ℹ️ Geänderte Zeilen (inkl. Duplikate): {updated_rows_count} "
          f"→ Update-Quote (pro Ticker): {updated_ratio:.0%}")

    if ticker_total == 0:
        print("❌ Ticker-Liste leer – CSV bleibt unverändert.")
        return

    if updated_ratio < MIN_UPDATED_QUOTE:
        print(f"❌ Nur {updated_rows_count}/{ticker_total} Ticker mit Änderungen "
              f"({updated_ratio:.0%}) – CSV bleibt unverändert.")
        return

    # Speichern
    try:
        df.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
        print(f"✅ Fertig – Daten in '{FILE_OUTPUT.name}' gespeichert "
              f"({updated_rows_count}/{ticker_total} Ticker mit Änderungen).")
    except Exception as e:
        print(f"❌ Konnte '{FILE_OUTPUT}' nicht schreiben: {e}")


if __name__ == "__main__":
    main()
