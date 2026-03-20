#!/usr/bin/env python3
# update_csv_server.py – Server-optimierte Variante mit Sharding, dynamischem Backoff & Start-Staggering
#
# Ziel:
# - Schonend für Rate-Limits/CF: kleinere Batches, weniger Threads, längere Sleeps + Jitter
# - Horizontale Aufteilung via SHARD_TOTAL/SHARD_INDEX (Ticker werden deterministisch auf Shards verteilt)
# - Dynamisches Nachregeln bei Fehlerwellen (Backoff & längere Schlafzeiten)
# - Start-Staggering, um Cron-„Thundering Herd“ zu vermeiden
#
# Beispiel (PowerShell):
#   $env:SHARD_TOTAL="8"; $env:SHARD_INDEX="0"; $env:STAGGER_MAX="120"; python .\update_csv_server.py
# Beispiel (Linux):
#   SHARD_TOTAL=8 SHARD_INDEX=0 STAGGER_MAX=120 python3 update_csv_server.py
#
# Kompatibel zur Desktop-Version: gleiche Spaltendefinitionen, Merge-Logik & Quick-Mode.
# Nutzt weiterhin yfinance .info (einfachster Weg) – für Full-Auto später Batch-API erwägen.

from __future__ import annotations

import hashlib
import json # Added json import
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
RAW_DATA_DIR = BASE_DIR / "data" / "raw" # Added RAW_DATA_DIR definition
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True) # Ensure RAW_DATA_DIR exists

# Konservative Server-Defaults (via ENV überschreibbar)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 20))        # kleine Gruppen
SLEEP_GROUP = float(os.getenv("SLEEP_GROUP", 6))     # längere Pause zwischen Gruppen
PER_TICKER_JITTER = [
    float(os.getenv("PER_TICKER_JITTER_MIN", 0.30)),
    float(os.getenv("PER_TICKER_JITTER_MAX", 0.60)),
]
MAX_TRIES = int(os.getenv("MAX_TRIES", 3))
BACKOFF_START = float(os.getenv("BACKOFF_START", 0.8))
THREADS_BASE = int(os.getenv("THREADS", 4))          # wird dynamisch angepasst
THREADS_MIN = int(os.getenv("THREADS_MIN", 2))
THREADS_MAX = int(os.getenv("THREADS_MAX", 6))
PARTIAL_SAVE_EVERY = int(os.getenv("PARTIAL_SAVE_EVERY", 200))

# Quick-Mode (aggressiver speichern, weniger Retries)
QUICK = os.getenv("QUICK") == "1"
MIN_UPDATED_QUOTE = 0.0 if QUICK else float(os.getenv("MIN_UPDATED_QUOTE", 0.75))
if QUICK:
    MAX_TRIES = min(MAX_TRIES, 2)

# Sharding
SHARD_TOTAL = int(os.getenv("SHARD_TOTAL", "1"))
SHARD_INDEX = int(os.getenv("SHARD_INDEX", "0"))
if SHARD_TOTAL < 1:
    SHARD_TOTAL = 1
if SHARD_INDEX < 0 or SHARD_INDEX >= SHARD_TOTAL:
    SHARD_INDEX = 0

# Start-Staggering (um gleichzeitige Crons zu entkoppeln)
STAGGER_MIN = int(os.getenv("STAGGER_MIN", "15"))
STAGGER_MAX = int(os.getenv("STAGGER_MAX", "90"))
STAGGER_ENABLED = bool(int(os.getenv("STAGGER_ENABLED", "1")))

# Dynamik-Grenzen
SLEEP_GROUP_MAX = float(os.getenv("SLEEP_GROUP_MAX", 30))
JITTER_MAX_CAP = float(os.getenv("JITTER_MAX_CAP", 1.2))

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
    # Analysten
    "Empfehlungsdurchschnitt", "Anzahl Analystenmeinungen", "Analysten_Kursziel", "Kursziel_Hoch", "Kursziel_Tief",
    # Metadaten
    "Land", "Langname",
    # Risiko & Bilanz
    "Verschuldungsgrad", "Current Ratio", "Gesamtschulden", "Beta",
    # Kurs-Historie & Wachstum
    "52W Hoch", "52W Tief", "Gewinnwachstum",
    # Dividenden-Historie
    "5Y Dividendenrendite",
]
META_SPALTEN = ["Abfragedatum", "Datenquelle", "Datenqualität", "Fehlende_Kennzahlen"]

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
    
        "Empfehlungsdurchschnitt": info.get("recommendationMean"),
        "Anzahl Analystenmeinungen": info.get("numberOfAnalystOpinions"),
        "Analysten_Kursziel": info.get("targetMeanPrice"),
        "Kursziel_Hoch": info.get("targetHighPrice"),
        "Kursziel_Tief": info.get("targetLowPrice"),
        
        "Land": info.get("country"),
        "Langname": info.get("longName"),
        
        "Verschuldungsgrad": info.get("debtToEquity"),
        "Current Ratio": info.get("currentRatio"),
        "Gesamtschulden": info.get("totalDebt"),
        "Beta": info.get("beta"),
        
        "52W Hoch": info.get("fiftyTwoWeekHigh"),
        "52W Tief": info.get("fiftyTwoWeekLow"),
        "Gewinnwachstum": info.get("earningsGrowth"),
        "5Y Dividendenrendite": info.get("fiveYearAvgDividendYield"),
}


def get_info_with_retry(ticker: str, max_tries: int = MAX_TRIES, base_sleep: float = BACKOFF_START, jitter=(0.3, 0.6)) -> Dict:
    last_err: Exception | None = None
    for attempt in range(1, max_tries + 1):
        try:
            time.sleep(random.uniform(*jitter))
            info = yf.Ticker(ticker).info
            
            # G1: Speichern als rohes JSON für Data-Lake / RAG
            try:
                raw_path = RAW_DATA_DIR / f"{ticker}.json"
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
            except Exception as io_err:
                print(f"[WARN] Konnte JSON Data-Lake Dump für {ticker} nicht schreiben: {io_err}")

            return info
        except Exception as e:
            last_err = e
            print(f"[WARN] Ticker {ticker} Fetch-Fehler (Versuch {attempt}/{max_tries}): {e}")
            time.sleep(base_sleep * (2 ** (attempt - 1)))
    print(f"[ERROR] Ticker {ticker} fatal fehlgeschlagen nach {max_tries} Versuchen.")
    raise last_err  # type: ignore[return-value]


def write_failed_list(failed: List[str]) -> None:
    if not failed:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_FOLDER / f"failed_{ts}.txt"
    try:
        with open(path, "w", encoding="utf-8") as f:
            for t in failed:
                f.write(str(t))
                f.write("\n")
        print(f"[WARN] Failed tickers: {len(failed)} - Sample: {failed[:10]}")
        print(f"   -> List saved to: {path}")
    except Exception as e:
        print(f"[WARN] Could not write failed list: {e}")


def md5_bucket(s: str) -> int:
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)  # 32-bit bucket


# --------------------------------------------------
# Main
# --------------------------------------------------

def main() -> None:
    heute = datetime.today().strftime("%Y-%m-%d")

    # Staggering
    if STAGGER_ENABLED:
        delay = random.randint(STAGGER_MIN, STAGGER_MAX)
        print(f"Waiting {delay}s (staggering)...")
        time.sleep(delay)

    # Eingabe
    if not FILE_INPUT.exists():
        raise FileNotFoundError(f"Eingabedatei nicht gefunden: {FILE_INPUT}")

    df = pd.read_csv(FILE_INPUT)
    if "valid_yahoo_ticker" not in df.columns:
        raise KeyError("Eingabedatei enthält keine Spalte 'valid_yahoo_ticker'.")

    raw_rows = len(df)
    raw_unique = df["valid_yahoo_ticker"].nunique(dropna=True)
    df = df[df["valid_yahoo_ticker"].notna()].copy()
    df = df.drop_duplicates("valid_yahoo_ticker", keep="first").reset_index(drop=True)
    print(f"[INFO] Input: {raw_rows} rows, {raw_unique} unique tickers -> after dedup: {len(df)} rows.")

    # Ziel-/Meta-Spalten anlegen
    df = ensure_columns(df, SPALTEN_KENNZAHLEN + META_SPALTEN)

    # Merge mit Bestand
    if FILE_OUTPUT.exists():
        try:
            old = pd.read_csv(FILE_OUTPUT)
            if "valid_yahoo_ticker" not in old.columns and "Symbol" in old.columns:
                old = old.rename(columns={"Symbol": "valid_yahoo_ticker"})
            if "valid_yahoo_ticker" in old.columns:
                keep_cols = [c for c in old.columns if c in (SPALTEN_KENNZAHLEN + META_SPALTEN + ["valid_yahoo_ticker"])]
                old = old[keep_cols].copy()
                if "Abfragedatum" in old.columns:
                    old = old.sort_values("Abfragedatum")
                old = old.dropna(subset=["valid_yahoo_ticker"]).drop_duplicates("valid_yahoo_ticker", keep="last")
                merged = df.merge(old, on="valid_yahoo_ticker", how="left", suffixes=("", "_old"))
                for col in SPALTEN_KENNZAHLEN + META_SPALTEN:
                    col_old = f"{col}_old"
                    if col_old in merged.columns:
                        merged[col] = merged[col].combine_first(merged[col_old])
                        merged.drop(columns=[col_old], inplace=True)
                df = merged
        except Exception as e:
            print(f"[INFO] Could not merge existing '{FILE_OUTPUT.name}': {e}")

    # Stale/Missing-Filter
    need_cols = SPALTEN_KENNZAHLEN
    stale_mask = df["Abfragedatum"].ne(heute) | df["Abfragedatum"].isna()
    missing_mask = df[need_cols].isna().any(axis=1)
    df_run = df[stale_mask | missing_mask].copy()

    if df_run.empty:
        print("[OK] Everything fresh - nothing to do.")
        return

    # Sharding anwenden (deterministisch via md5)
    if SHARD_TOTAL > 1:
        before = len(df_run)
        subset_mask = df_run["valid_yahoo_ticker"].astype(str).apply(lambda t: md5_bucket(t) % SHARD_TOTAL == SHARD_INDEX)
        df_run = df_run[subset_mask].copy()
        print(f"[SHARD] Shard {SHARD_INDEX+1}/{SHARD_TOTAL}: {len(df_run)} of {before} tickers this run.")

    # Tickerliste eindeutig machen
    tickers: List[str] = list(dict.fromkeys(df_run["valid_yahoo_ticker"].astype(str)))
    ticker_total = len(tickers)
    print(f"Starting update for {ticker_total} tickers...")

    failed: List[str] = []
    updated_rows_count = 0
    threads_current = max(THREADS_MIN, min(THREADS_BASE, THREADS_MAX))
    jitter = list(PER_TICKER_JITTER)  # mutable copy
    sleep_group = SLEEP_GROUP

    def fetch_one(t: str) -> Tuple[str, Dict | None, Exception | None]:
        try:
            info = get_info_with_retry(t, max_tries=MAX_TRIES, base_sleep=BACKOFF_START, jitter=tuple(jitter))
            return t, info, None
        except Exception as e:
            return t, None, e

    total_batches = math.ceil(len(tickers) / BATCH_SIZE) if BATCH_SIZE > 0 else 1
    processed_since_partial = 0

    for gi, group in enumerate(chunkify(tickers, BATCH_SIZE), start=1):
        # parallele Abfragen in aktueller Gruppe
        results: List[Tuple[str, Dict | None, Exception | None]] = []
        with ThreadPoolExecutor(max_workers=threads_current) as ex:
            futs = {ex.submit(fetch_one, t): t for t in group}
            for fut in as_completed(futs):
                results.append(fut.result())

        # sequentiell in df schreiben
        group_fail = 0
        for ticker, info, err in results:
            mask = df["valid_yahoo_ticker"] == ticker
            if err is not None or info is None:
                failed.append(ticker)
                group_fail += 1
                print(f"[FAIL] {ticker}: failed to fetch.")
                continue
            else:
                print(f"[OK] {ticker}: fetched successfully.")

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
                    print(f"Saved partial: {tmp.name} (updated: {updated_rows_count}/{ticker_total})")
                except Exception as e:
                    print(f"[WARN] Partial save failed: {e}")
                processed_since_partial = 0

        # Dynamische Anpassung nach Gruppenfehlerquote
        fail_rate = group_fail / max(1, len(group))
        if fail_rate >= 0.25:
            # Mehr Backoff: längere Sleeps, breiteres Jitter, weniger Threads (bis Minimum)
            sleep_group = min(SLEEP_GROUP_MAX, sleep_group * 1.5)
            jitter[0] = min(JITTER_MAX_CAP, jitter[0] * 1.2)
            jitter[1] = min(JITTER_MAX_CAP, jitter[1] * 1.2)
            if threads_current > THREADS_MIN:
                threads_current = max(THREADS_MIN, threads_current - 1)
            print(f"[ADJUST] High failure rate ({fail_rate:.0%}). Adjusting: sleep={sleep_group:.1f}s, threads={threads_current}")
        elif fail_rate == 0 and threads_current < THREADS_BASE:
            # leichtes Hochfahren bis Threads_BASE
            threads_current = min(THREADS_BASE, threads_current + 1)

        print(f"Group {gi}/{total_batches} processed - Sleeping {sleep_group:.1f}s... (Failures {group_fail}/{len(group)})")
        time.sleep(sleep_group)

    # failed-Log schreiben
    write_failed_list(failed)

    # --- Quality Flags am Ende berechnen ---
    total_kennzahlen = len(SPALTEN_KENNZAHLEN)
    df["Fehlende_Kennzahlen"] = df[SPALTEN_KENNZAHLEN].isna().sum(axis=1)
    df["Datenqualität"] = (1.0 - (df["Fehlende_Kennzahlen"] / total_kennzahlen)).round(2)

    # Speichern je nach Erfolgsquote
    updated_ratio = (updated_rows_count / max(1, ticker_total))
    if updated_ratio < MIN_UPDATED_QUOTE and not QUICK:
        print(
            f"[SKIP] Only {updated_rows_count}/{ticker_total} tickers updated "
            f"({updated_ratio:.0%}) - CSV remains unchanged (Threshold {MIN_UPDATED_QUOTE:.0%})."
        )
        return

    if QUICK and updated_ratio < MIN_UPDATED_QUOTE:
        print("[INFO] QUICK=1 active -> ignoring threshold, saving CSV.")

    try:
        df.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
        print(f"[OK] Done - Data saved to '{FILE_OUTPUT.name}' ({updated_rows_count}/{ticker_total} tickers changed).")
    except Exception as e:
        print(f"[ERROR] Could not write '{FILE_OUTPUT}': {e}")


if __name__ == "__main__":
    main()
