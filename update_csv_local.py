#!/usr/bin/env python3
# update_csv.py – Schnelleres Yahoo-Finance-Update mit Quick-Mode, Parallelisierung und Stale/Missing-Filter
#
# Was ist neu?
# - QUICK-Mode per Umgebungsvariable QUICK=1 (spart Zeit, speichert Teilerfolge)
# - Nur „stale/missing“-Ticker abfragen (heute noch nicht abgefragt ODER Datenlücken)
# - Moderate Parallelisierung (standardmäßig 6 Threads) + Jitter + Backoff
# - Inkrementelles Teilspeichern alle N verarbeiteten Ticker
# - Merge mit bestehender stock_data.csv robust als 1:1 (Deduplizierung)
#
# PowerShell-Beispiele:
#   $env:QUICK="1"; $env:THREADS="6"; python .\update_csv.py

from __future__ import annotations

import math
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# --------------------------------------------------
# Pfade & Parameter
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
FILE_INPUT = BASE_DIR / "data" / "ticker_resolved.csv"
FILE_OUTPUT = BASE_DIR / "stock_data.csv"
LOG_FOLDER = BASE_DIR / "logs"
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

# Rate-Limit / Stabilität (via ENV überschreibbar)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 40))       # Größe der Gruppen (nur fürs Throttling zwischen Gruppen)
SLEEP_GROUP = float(os.getenv("SLEEP_GROUP", 3))     # Schlaf nach jeder Gruppe (Sekunden)
PER_TICKER_JITTER = (
    float(os.getenv("PER_TICKER_JITTER_MIN", 0.15)),
    float(os.getenv("PER_TICKER_JITTER_MAX", 0.35)),
)
MAX_TRIES = int(os.getenv("MAX_TRIES", 3))
BACKOFF_START = float(os.getenv("BACKOFF_START", 0.5))
THREADS = int(os.getenv("THREADS", 6))
PARTIAL_SAVE_EVERY = int(os.getenv("PARTIAL_SAVE_EVERY", 300))  # alle N verarbeitete Ticker .partial.csv schreiben

# Quick-Mode (aggressiver speichern, weniger Retries)
QUICK = os.getenv("QUICK") == "1"
MIN_UPDATED_QUOTE = 0.0 if QUICK else float(os.getenv("MIN_UPDATED_QUOTE", 0.80))
if QUICK:
    MAX_TRIES = min(MAX_TRIES, 2)

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
    # Renditen & Wachstum
    "Eigenkapitalrendite", "Return on Assets", "ROIC", "Umsatzwachstum 3J (erwartet)",
]
META_SPALTEN = ["Abfragedatum", "Datenquelle"]

# --------------------------------------------------
# Utils
# --------------------------------------------------

def ensure_columns(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df


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
    }


def get_info_with_retry(ticker: str, max_tries: int = MAX_TRIES, base_sleep: float = BACKOFF_START) -> Dict:
    last_err: Exception | None = None
    for attempt in range(1, max_tries + 1):
        try:
            # pro Ticker etwas Jitter
            time.sleep(random.uniform(*PER_TICKER_JITTER))
            return yf.Ticker(ticker).info  # schnelle Lösung über .info
        except Exception as e:
            last_err = e
            time.sleep(base_sleep * (2 ** (attempt - 1)))
    raise last_err  # type: ignore[return-value]


def write_failed_list(failed: List[str]) -> None:
    """Schreibt fehlgeschlagene Ticker in eine Logdatei."""
    if not failed:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_FOLDER / f"failed_{ts}.txt"
    try:
        with open(path, "w", encoding="utf-8") as f:
            for t in failed:
                f.write(str(t))
                f.write("\n")
        try:
            print(f"⚠️ Fehlgeschlagene Ticker: {len(failed)} – Beispiel: {failed[:10]}")
            print(f"   → Liste gespeichert unter: {path}")
        except Exception:
            print(f"Fehlgeschlagene Ticker: {len(failed)} – Beispiel: {failed[:10]}")
            print(f"   -> Liste gespeichert unter: {path}")
    except Exception as e:
        print(f"⚠️ Konnte Fehlerticker nicht schreiben: {e}")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main() -> None:
    heute = datetime.today().strftime("%Y-%m-%d")

    # Eingabe
    if not FILE_INPUT.exists():
        raise FileNotFoundError(f"Eingabedatei nicht gefunden: {FILE_INPUT}")

    df = pd.read_csv(FILE_INPUT)
    if "valid_yahoo_ticker" not in df.columns:
        raise KeyError("Eingabedatei enthält keine Spalte 'valid_yahoo_ticker'.")

    # Nur gültige Ticker + Deduplizierung (Schutz vor Merge-Explosion)
    raw_rows = len(df)
    raw_unique = df["valid_yahoo_ticker"].nunique(dropna=True)
    df = df[df["valid_yahoo_ticker"].notna()].copy()
    df = df.drop_duplicates("valid_yahoo_ticker", keep="first").reset_index(drop=True)
    print(f"ℹ️ Eingabe: {raw_rows} Zeilen, {raw_unique} eindeutige Ticker → nach Deduplizierung: {len(df)} Zeilen.")

    # Ziel-/Meta-Spalten anlegen
    df = ensure_columns(df, SPALTEN_KENNZAHLEN + META_SPALTEN)

    # Bestehende stock_data.csv mergen (alte Werte behalten) – robust & 1:1
    if FILE_OUTPUT.exists():
        try:
            old = pd.read_csv(FILE_OUTPUT)

            # Join-Column erzwingen: valid_yahoo_ticker
            if "valid_yahoo_ticker" not in old.columns and "Symbol" in old.columns:
                old = old.rename(columns={"Symbol": "valid_yahoo_ticker"})

            if "valid_yahoo_ticker" in old.columns:
                # Nur relevante Spalten behalten
                keep_cols = [
                    c for c in old.columns
                    if c in (SPALTEN_KENNZAHLEN + META_SPALTEN + ["valid_yahoo_ticker"])
                ]
                old = old[keep_cols].copy()

                # Deduplizieren nach Key (neueste/letzte Zeile behalten)
                old_rows = len(old)
                old_unique = old["valid_yahoo_ticker"].nunique(dropna=True)
                if "Abfragedatum" in old.columns:
                    old = old.sort_values("Abfragedatum")
                old = old.dropna(subset=["valid_yahoo_ticker"]).drop_duplicates("valid_yahoo_ticker", keep="last")
                if old_rows != len(old):
                    print(f"ℹ️ Bestand: {old_rows} Zeilen, {old_unique} eindeutige Ticker → nach Deduplizierung: {len(old)} Zeilen.")

                # Merge strikt als 1:1 absichern
                try:
                    merged = df.merge(
                        old,
                        on="valid_yahoo_ticker",
                        how="left",
                        suffixes=("", "_old"),
                        validate="one_to_one",
                    )
                except Exception as e:
                    print(
                        "⚠️ Merge-Validierung fehlgeschlagen (kein 1:1). "
                        f"Versuche automatische Deduplizierung und erneuten Merge… {e}"
                    )
                    df = df.drop_duplicates("valid_yahoo_ticker", keep="first")
                    old = old.drop_duplicates("valid_yahoo_ticker", keep="last")
                    merged = df.merge(old, on="valid_yahoo_ticker", how="left", suffixes=("", "_old"))

                # Wenn neue Werte fehlen, alte behalten
                for col in SPALTEN_KENNZAHLEN + META_SPALTEN:
                    old_col = f"{col}_old"
                    if old_col in merged.columns:
                        merged[col] = merged[col].combine_first(merged[old_col])
                        merged.drop(columns=[old_col], inplace=True)
                df = merged
            else:
                print("ℹ️ Bestand hat keine Spalte 'valid_yahoo_ticker' – überspringe Merge.")
        except Exception as e:
            print(f"ℹ️ Konnte bestehende '{FILE_OUTPUT.name}' nicht mergen: {e}")

    # --- Stale/Missing-Filter ---
    need_cols = SPALTEN_KENNZAHLEN
    stale_mask = df["Abfragedatum"].ne(heute) | df["Abfragedatum"].isna()
    missing_mask = df[need_cols].isna().any(axis=1)
    df_run = df[stale_mask | missing_mask].copy()

    if df_run.empty:
        print("✅ Alles frisch – nichts zu tun.")
        return

    # Tickerliste eindeutig machen (keine Doppelarbeit)
    tickers: List[str] = list(dict.fromkeys(df_run["valid_yahoo_ticker"].astype(str)))
    ticker_total = len(tickers)
    print(f"🟡 Starte Update für {ticker_total} Ticker (stale/missing gefiltert)…")

    # Parallel fetch
    failed: List[str] = []
    updated_rows_count = 0

    def fetch_one(t: str) -> Tuple[str, Dict | None, Exception | None]:
        try:
            info = get_info_with_retry(t)
            return t, info, None
        except Exception as e:
            return t, None, e

    total_batches = math.ceil(len(tickers) / BATCH_SIZE) if BATCH_SIZE > 0 else 1
    processed_since_partial = 0

    for gi, group in enumerate(chunkify(tickers, BATCH_SIZE), start=1):
        # parallele Abfragen innerhalb der Gruppe
        results: List[Tuple[str, Dict | None, Exception | None]] = []
        with ThreadPoolExecutor(max_workers=THREADS) as ex:
            futs = {ex.submit(fetch_one, t): t for t in group}
            for fut in as_completed(futs):
                results.append(fut.result())

        # sequentiell in df schreiben (kein pandas-Rennen)
        for ticker, info, err in results:
            mask = df["valid_yahoo_ticker"] == ticker
            if err is not None or info is None:
                failed.append(ticker)
                continue

            mapped = map_info(info)
            changed_any_row = False
            for key, val in mapped.items():
                if key not in SPALTEN_KENNZAHLEN:
                    continue
                current = df.loc[mask, key]
                to_update = current.isna() | (current != val)
                if bool(to_update.any()):
                    df.loc[mask & to_update, key] = val
                    changed_any_row = True

            # Abgeleitete Felder
            try:
                fcf = pd.to_numeric(df.loc[mask, "Free Cashflow"], errors="coerce")
                mcap = pd.to_numeric(df.loc[mask, "Marktkapitalisierung"], errors="coerce")
                fcf_yield = fcf / mcap
                fcf_yield = fcf_yield.replace([np.inf, -np.inf], np.nan)
                before = df.loc[mask, "Free Cashflow Yield"]
                to_update = before.isna() | (before != fcf_yield)
                if bool(to_update.any()):
                    df.loc[mask & to_update, "Free Cashflow Yield"] = fcf_yield
                    changed_any_row = True
            except Exception:
                pass

            if changed_any_row:
                df.loc[mask, "Abfragedatum"] = heute
                df.loc[mask, "Datenquelle"] = "Yahoo Finance"
                updated_rows_count += int(mask.sum())

            processed_since_partial += 1
            if PARTIAL_SAVE_EVERY and processed_since_partial >= PARTIAL_SAVE_EVERY:
                tmp = FILE_OUTPUT.with_suffix(".partial.csv")
                try:
                    df.to_csv(tmp, index=False, encoding="utf-8-sig")
                    print(f"💾 Teilspeicher: {tmp.name} (aktualisiert: {updated_rows_count}/{ticker_total})")
                except Exception as e:
                    print(f"⚠️ Teilspeicher fehlgeschlagen: {e}")
                processed_since_partial = 0

        print(f"✅ Gruppe {gi}/{total_batches} verarbeitet – Schläft {SLEEP_GROUP:.1f}s…")
        time.sleep(SLEEP_GROUP)

    # failed-Log schreiben
    write_failed_list(failed)

    # Speichern je nach Erfolgsquote
    updated_ratio = (updated_rows_count / max(1, ticker_total))
    if updated_ratio < MIN_UPDATED_QUOTE and not QUICK:
        print(
            f"❌ Nur {updated_rows_count}/{ticker_total} Ticker mit Änderungen "
            f"({updated_ratio:.0%}) – CSV bleibt unverändert (Schwellwert {MIN_UPDATED_QUOTE:.0%})."
        )
        return

    if QUICK and updated_ratio < MIN_UPDATED_QUOTE:
        print("ℹ️ QUICK=1 aktiv → MIN_UPDATED_QUOTE wird ignoriert, CSV wird trotzdem gespeichert.")

    try:
        df.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
        print(f"✅ Fertig – Daten in '{FILE_OUTPUT.name}' gespeichert ({updated_rows_count}/{ticker_total} Ticker mit Änderungen).")
    except Exception as e:
        print(f"❌ Konnte '{FILE_OUTPUT}' nicht schreiben: {e}")


if __name__ == "__main__":
    main()
