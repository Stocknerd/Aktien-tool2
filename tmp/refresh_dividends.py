#!/usr/bin/env python3
"""
Dividend Data Refresh — fetches Ex-Dividend-Date, Yield, Amount for ALL stocks.
Designed to run unattended via cronjob on a Linux machine.
Supports batching with rate-limiting to avoid Yahoo Finance blocks.
"""
import pandas as pd
import yfinance as yf
from datetime import datetime
import concurrent.futures
import sys
import os
import time
import logging

# ── Path setup ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import core
    CSV_FILE = core.CSV_FILE
except ImportError:
    CSV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock_data.csv")

# ── Config ──
BATCH_SIZE = 200          # Stocks per batch
BATCH_PAUSE = 3           # Seconds between batches
MAX_WORKERS = 15          # Parallel threads per batch
TIMEOUT_PER_STOCK = 10    # Seconds before giving up on a single stock

# ── Logging ──
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"dividend_refresh_{datetime.now().strftime('%Y-%m-%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


def fetch_div(ticker: str) -> dict | None:
    """Fetch dividend data for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return None

        ex_date_raw = info.get("exDividendDate")
        ex_date = None
        if ex_date_raw:
            try:
                ex_date = datetime.fromtimestamp(ex_date_raw).strftime("%Y-%m-%d")
            except (ValueError, OSError, TypeError):
                pass

        div_yield = info.get("dividendYield")
        if div_yield is not None:
            try:
                # Yahoo returns yield as decimal (e.g. 0.0037 = 0.37%)
                # The CSV stores it as-is — the display layer handles formatting
                div_yield = round(float(div_yield), 6)
            except (ValueError, TypeError):
                div_yield = None

        div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
        if div_rate is not None:
            try:
                div_rate = round(float(div_rate), 4)
            except (ValueError, TypeError):
                div_rate = None

        # Only return if we have at least yield OR ex-date
        if div_yield is None and ex_date is None:
            return None

        return {
            "Symbol": ticker,
            "Ex-Dividenden-Datum": ex_date,
            "Dividenden-Betrag": div_rate,
            "Dividendenrendite": div_yield,
        }
    except Exception as e:
        # Silently skip — will be logged as a miss
        return None


def process_batch(tickers: list[str], batch_num: int, total_batches: int) -> list[dict]:
    """Process a batch of tickers with thread pool."""
    results = []
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(fetch_div, t): t for t in tickers}
        for future in concurrent.futures.as_completed(future_map, timeout=60):
            try:
                res = future.result(timeout=TIMEOUT_PER_STOCK)
                if res:
                    results.append(res)
            except Exception:
                errors += 1

    log.info(f"  Batch {batch_num}/{total_batches}: {len(results)}/{len(tickers)} OK, {errors} errors")
    return results


def main():
    start_time = time.time()
    log.info("=" * 60)
    log.info("DIVIDEND REFRESH — Starting full refresh for ALL stocks")
    log.info("=" * 60)

    if not os.path.exists(CSV_FILE):
        log.error(f"CSV not found: {CSV_FILE}")
        sys.exit(1)

    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig", on_bad_lines="skip")
    tickers = df["Symbol"].dropna().unique().tolist()
    total = len(tickers)
    log.info(f"Total stocks to process: {total}")

    # ── Batch processing ──
    all_results = []
    batches = [tickers[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    total_batches = len(batches)

    for i, batch in enumerate(batches, 1):
        pct = round(i / total_batches * 100)
        processed = min(i * BATCH_SIZE, total)
        log.info(f"[{processed}/{total}] {pct}% — Processing batch {i}/{total_batches}...")

        batch_results = process_batch(batch, i, total_batches)
        all_results.extend(batch_results)

        # Rate-limit pause (skip on last batch)
        if i < total_batches:
            time.sleep(BATCH_PAUSE)

    log.info(f"Fetched dividend data for {len(all_results)}/{total} stocks")

    # ── Merge back into CSV ──
    for col in ["Ex-Dividenden-Datum", "Dividenden-Betrag", "Dividendenrendite"]:
        if col not in df.columns:
            df[col] = None

    if all_results:
        div_df = pd.DataFrame(all_results)
        df.set_index("Symbol", inplace=True)
        div_df.set_index("Symbol", inplace=True)
        df.update(div_df)
        df.reset_index(inplace=True)
        df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    elapsed = round(time.time() - start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    log.info(f"✅ Done in {mins}m {secs}s — {len(all_results)} stocks updated")
    log.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    main()
