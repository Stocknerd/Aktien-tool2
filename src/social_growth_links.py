"""Canonical, bounded Social-to-tool links for measurable review packets."""

from __future__ import annotations

import re
from urllib.parse import urlencode


_TICKER_PATTERN = re.compile(r"[A-Z0-9.^=-]{1,24}")
_BASE_ATTRIBUTION = {
    "utm_source": "social",
    "utm_medium": "organic_social",
}


def _ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not _TICKER_PATTERN.fullmatch(ticker):
        raise ValueError("ticker contains unsupported characters")
    return ticker


def _url(base: str, campaign: str, **parameters: str) -> str:
    query = {
        **parameters,
        **_BASE_ATTRIBUTION,
        "utm_campaign": campaign,
    }
    return f"{base}?{urlencode(query)}"


def stock_analysis_url(ticker: object) -> str:
    """Link a stock card to an already-prefilled analysis form."""

    clean_ticker = _ticker(ticker)
    return _url(
        "https://tool.schatzsuche40.de/",
        "stock_analysis",
        ticker=clean_ticker,
        utm_content=clean_ticker,
    )


def stock_duel_url(first_ticker: object, second_ticker: object) -> str:
    """Link a duel card to an already-prefilled comparison form."""

    first = _ticker(first_ticker)
    second = _ticker(second_ticker)
    return _url(
        "https://compare.schatzsuche40.de/",
        "stock_duel",
        t1=first,
        t2=second,
        utm_content=f"{first}_vs_{second}",
    )


def calendar_url() -> str:
    """Link the weekly calendar post directly to the interactive calendar."""

    return _url(
        "https://tool.schatzsuche40.de/dividenden-kalender",
        "dividend_calendar",
    )
