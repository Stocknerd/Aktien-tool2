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

import json
import math
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


import numpy as np
import pandas as pd
import requests
import yfinance as yf

# --------------------------------------------------
# Pfade & Parameter
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_FOLDER = BASE_DIR / "data"
LOG_FOLDER = BASE_DIR / "logs"
RAW_DATA_DIR = DATA_FOLDER / "raw"

FILE_INPUT = Path(os.getenv("FILE_INPUT", DATA_FOLDER / "ticker_resolved.csv"))
FILE_OUTPUT = Path(os.getenv("FILE_OUTPUT", BASE_DIR / "stock_data.csv"))

# Ordner anlegen
LOG_FOLDER.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

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
MIN_UPDATED_QUOTE = 0.0 if QUICK else float(os.getenv("MIN_UPDATED_QUOTE", 0.70))
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
    # Analysten & Kursziele
    "Analyst Mean Target", "Analyst High Target", "Analyst Low Target", 
    "Current Price", "Recommendation Key", "Number of Analysts",
    # Dividenden-Kalender (NEU)
    "Ex-Dividenden-Datum", "Dividenden-Frequenz", "Dividenden-Betrag",
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
        "Nettomarge": info.get("profitMargins"),
        "Marktkapitalisierung": info.get("marketCap"),
        "Free Cashflow": info.get("freeCashflow"),
        "Operativer Cashflow": info.get("operatingCashflow"),
        "Eigenkapitalrendite": info.get("returnOnEquity"),
        "Return on Assets": info.get("returnOnAssets"),
        "ROIC": info.get("returnOnCapital"),
        "Umsatzwachstum 3J (erwartet)": info.get("revenueGrowth"),
        "Analyst Mean Target": info.get("targetMeanPrice"),
        "Analyst High Target": info.get("targetHighPrice"),
        "Analyst Low Target": info.get("targetLowPrice"),
        "Current Price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "Recommendation Key": info.get("recommendationKey"),
        "Number of Analysts": info.get("numberOfAnalystOpinions"),
        # Dividenden-Kalender
        "Ex-Dividenden-Datum": datetime.fromtimestamp(info.get("exDividendDate")).strftime("%Y-%m-%d") if info.get("exDividendDate") else None,
        "Dividenden-Frequenz": info.get("dividendRate"), # This is often the rate, I'll need to check how to get frequency
        "Dividenden-Betrag": info.get("dividendRate") or info.get("trailingAnnualDividendRate"),
    }


def get_session():
    """Erstellt eine curl_cffi Session mit Chrome-Impersonation."""
    from curl_cffi import requests as curl_requests
    session = curl_requests.Session(impersonate="chrome")
    return session

# Single global shared curl_cffi session for all threads
_SHARED_SESSION = None
_session_lock = threading.Lock()

def get_shared_session():
    global _SHARED_SESSION
    with _session_lock:
        if _SHARED_SESSION is None:
            _SHARED_SESSION = get_session()
        return _SHARED_SESSION

def reset_shared_session():
    global _SHARED_SESSION
    with _session_lock:
        try:
            print("🔄 Resetting global curl_cffi session to bypass rate limit.")
            _SHARED_SESSION = get_session()
        except Exception as e:
            print(f"⚠️ Failed to reset global session: {e}")

_cooldown_lock = threading.Lock()
_global_cooldown_until = 0.0

def get_info_with_retry(ticker: str, max_tries: int = MAX_TRIES, base_sleep: float = BACKOFF_START) -> Dict:
    global _global_cooldown_until
    
    session = get_shared_session()
    from threading import current_thread
    tid = current_thread().name
    
    last_err: Exception | None = None
    for attempt in range(1, max_tries + 1):
        # Check global cooldown
        current_time = time.time()
        if current_time < _global_cooldown_until:
            sleep_time = _global_cooldown_until - current_time
            print(f"[COOLDOWN] Thread {tid} sleeping for {sleep_time:.1f}s due to active rate limit cooldown.")
            time.sleep(sleep_time)
            
        try:
            # pro Ticker etwas Jitter
            time.sleep(random.uniform(*PER_TICKER_JITTER))
            
            # yf.Ticker nutzen mit custom session!
            t_obj = yf.Ticker(ticker, session=session)
            info = t_obj.info  # schnelle Lösung über .info
            
            # G1: Speichern als rohes JSON für Data-Lake / RAG
            try:
                raw_path = RAW_DATA_DIR / f"{ticker}.json"
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
            except Exception as io_err:
                print(f"⚠️ [WARN] Konnte JSON Data-Lake Dump für {ticker} nicht schreiben: {io_err}")

            return info
        except Exception as e:
            last_err = e
            err_msg = str(e)
            
            # Check if it is a rate limit error
            is_rate_limit = "Too Many Requests" in err_msg or "Rate limited" in err_msg or "429" in err_msg
            
            if is_rate_limit:
                with _cooldown_lock:
                    cooldown_target = time.time() + 300.0
                    if _global_cooldown_until < cooldown_target:
                        _global_cooldown_until = cooldown_target
                        print(f"🛑 [RATE LIMIT DETECTED] Ticker {ticker} triggered 429. Setting global cooldown for 5 mins.")
                
                # Reset the global session
                reset_shared_session()
                session = get_shared_session()
            
            print(f"⚠️ [WARN] Ticker {ticker} Fetch-Fehler (Versuch {attempt}/{max_tries}): {e}")
            time.sleep(base_sleep * (2 ** (attempt - 1)))
            
    print(f"❌ [ERROR] Ticker {ticker} fatal fehlgeschlagen nach {max_tries} Versuchen.")
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
            print(f"   -> Liste gespeichert unter: {path}")
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
    print(f"Info: Eingabe: {raw_rows} Zeilen, {raw_unique} eindeutige Ticker -> nach Deduplizierung: {len(df)} Zeilen.")

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
                    print(f"[INFO] Bestand: {old_rows} Zeilen, {old_unique} eindeutige Ticker -> nach Deduplizierung: {len(old)} Zeilen.")

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
                        "[WARN] Merge-Validierung fehlgeschlagen (kein 1:1). "
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
                print("[INFO] Bestand hat keine Spalte 'valid_yahoo_ticker' – überspringe Merge.")
        except Exception as e:
            print(f"[INFO] Konnte bestehende '{FILE_OUTPUT.name}' nicht mergen: {e}")

    # --- Stale/Missing-Filter ---
    # Wir aktualisieren nur Ticker, die heute noch nicht erfolgreich aktualisiert wurden (Abfragedatum ist ungleich heute oder fehlt).
    # Damit verhindern wir, dass permanent 4000+ Ticker geladen werden, nur weil bei einigen einzelne Nischen-Kennzahlen fehlen.
    stale_mask = df["Abfragedatum"].ne(heute) | df["Abfragedatum"].isna()
    df_run = df[stale_mask].copy()

    if df_run.empty:
        print("[OK] Alles frisch – nichts zu tun.")
        return

    # Tickerliste eindeutig machen (keine Doppelarbeit)
    tickers: List[str] = list(dict.fromkeys(df_run["valid_yahoo_ticker"].astype(str)))
    ticker_total = len(tickers)
    print(f"[INFO] Starte Update für {ticker_total} Ticker (stale/missing gefiltert)…")

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
                print(f"[ERR] {ticker}: failed to fetch.")
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
                    print(f"[SAVE] Teilspeicher: {tmp.name} (aktualisiert: {updated_rows_count}/{ticker_total})")
                except Exception as e:
                    print(f"[WARN] Teilspeicher fehlgeschlagen: {e}")
                processed_since_partial = 0

        print(f"[OK] Gruppe {gi}/{total_batches} verarbeitet – Schläft {SLEEP_GROUP:.1f}s…")
        time.sleep(SLEEP_GROUP)

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
            f"❌ Nur {updated_rows_count}/{ticker_total} Ticker mit Änderungen "
            f"({updated_ratio:.0%}) – CSV bleibt unverändert (Schwellwert {MIN_UPDATED_QUOTE:.0%})."
        )
        return

    if QUICK and updated_ratio < MIN_UPDATED_QUOTE:
        print("ℹ️ QUICK=1 aktiv → MIN_UPDATED_QUOTE wird ignoriert, CSV wird trotzdem gespeichert.")

    try:
        df.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
        print(f"[OK] Fertig – Daten in '{FILE_OUTPUT.name}' gespeichert ({updated_rows_count}/{ticker_total} Ticker mit Änderungen).")
        
        # Trigger Sitemap Generation
        try:
            from generate_sitemap import generate_sitemap
            generate_sitemap(csv_path=FILE_OUTPUT, output_path=BASE_DIR / "static" / "sitemap.xml")
        except Exception as sm_err:
            print(f"⚠️ [WARN] Sitemap-Generierung fehlgeschlagen: {sm_err}")
    except Exception as e:
        print(f"[ERR] Konnte '{FILE_OUTPUT}' nicht schreiben: {e}")


if __name__ == "__main__":
    main()
