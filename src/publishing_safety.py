"""Fail-closed helpers shared by every social distribution path."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date, datetime, timezone
from typing import Any


INVALID_FACT_VALUES = {
    "",
    "--",
    "n/a",
    "na",
    "nan",
    "inf",
    "-inf",
    "infinity",
    "none",
    "null",
    "unknown",
    "unbekannt",
}
SUPPORTED_CALENDAR_CURRENCIES = {
    "AUD",
    "CAD",
    "CHF",
    "DKK",
    "EUR",
    "GBP",
    "HKD",
    "JPY",
    "NOK",
    "NZD",
    "SEK",
    "SGD",
    "USD",
}


def public_dispatch_enabled(*, prepare_only: bool, public_allowed: bool) -> bool:
    """Require two independent typed opt-ins before any public API dispatch."""

    return prepare_only is False and public_allowed is True


def explicit_public_dispatch_enabled(prepare_value: object, allowed_value: object) -> bool:
    """Parse the two ENV switches strictly; malformed or missing values stay disabled."""

    if not isinstance(prepare_value, str) or not isinstance(allowed_value, str):
        return False
    return prepare_value.strip().lower() == "false" and allowed_value.strip().lower() == "true"


def external_transfer_enabled(*, requested: bool, allowed: bool) -> bool:
    """Require a request plus a separate opt-in for non-publishing transfers."""

    return requested and allowed


def content_dispatch_allowed(content: Mapping[str, Any]) -> bool:
    """Honor content-level review state in addition to global environment gates."""

    return (
        content.get("requires_manual_review") is False
        and content.get("publishing_allowed") is True
    )


def review_metadata_for_content(
    content: Mapping[str, Any],
    *,
    content_pillar: str,
) -> dict[str, Any]:
    """Preserve source and safety state in the manual-review artifact."""

    mandatory_review = (
        content_pillar in {"current_finance_news", "manual_override"}
        or not content_dispatch_allowed(content)
    )
    sources = content.get("source_records")
    if not isinstance(sources, list):
        sources = []
    generated_at = content.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        generated_at = datetime.now(timezone.utc).isoformat()
    expires_at = content.get("review_expires_at")
    if not isinstance(expires_at, str) or not expires_at.strip():
        expires_at = None
    return {
        "schema_version": 1,
        "content_pillar": content_pillar,
        "generated_at": generated_at,
        "review_expires_at": expires_at,
        "requires_manual_review": mandatory_review,
        "publishing_allowed": False if mandatory_review else content.get("publishing_allowed", True),
        "source_records": sources,
    }


def dispatch_or_prepare(
    *,
    prepare_only: bool,
    prepare: Callable[[], Any],
    dispatchers: Iterable[tuple[str, Callable[[], Any]]],
) -> dict[str, Any]:
    """Prepare one artifact or run external dispatchers, never both.

    The preparation branch returns before the dispatcher iterable is consumed.
    This central short-circuit protects optional uploaders, comments and future
    crossposts from accidentally bypassing a platform-specific flag.
    """

    if prepare_only:
        return {"mode": "prepared", "artifact": prepare()}

    results: dict[str, Any] = {}
    for name, dispatch in dispatchers:
        results[name] = dispatch()
    return {"mode": "dispatched", "results": results}


def _finite_number(value: object, *, field: str, index: int) -> float:
    text = str(value).strip()
    match = re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", text)
    if not match:
        raise ValueError(f"calendar entry {index} has invalid {field}")
    number = float(match.group(0))
    if not math.isfinite(number):
        raise ValueError(f"calendar entry {index} has invalid {field}")
    return number


def validate_calendar_entries(
    entries: Sequence[dict[str, Any]],
    *,
    minimum: int = 3,
) -> list[dict[str, Any]]:
    """Require enough complete, sourced dividend entries or fail closed."""

    if len(entries) < minimum:
        raise ValueError(
            f"calendar requires at least {minimum} verified dividend entries; got {len(entries)}"
        )

    required = ("symbol", "name", "ex_date", "dividend", "yield", "currency")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"calendar entry {index} is incomplete")
        for field in required:
            value = entry.get(field)
            normalized = "" if value is None else str(value).strip().lower()
            if normalized in INVALID_FACT_VALUES:
                raise ValueError(f"calendar entry {index} is incomplete: {field}")

        symbol = str(entry["symbol"]).strip().upper()
        name = str(entry["name"]).strip()
        if not re.fullmatch(r"[A-Z0-9.^=-]{1,20}", symbol) or name.upper() == symbol:
            raise ValueError(f"calendar entry {index} has invalid symbol or company name")

        ex_date = str(entry["ex_date"]).strip()
        try:
            parsed_date = date.fromisoformat(ex_date)
        except ValueError as exc:
            raise ValueError(f"calendar entry {index} has invalid ex_date") from exc
        if parsed_date.isoformat() != ex_date:
            raise ValueError(f"calendar entry {index} has invalid ex_date")

        currency = str(entry["currency"]).strip().upper()
        if currency not in SUPPORTED_CALENDAR_CURRENCIES:
            raise ValueError(f"calendar entry {index} has unsupported currency")

        dividend_text = str(entry["dividend"]).strip()
        currency_suffix = f" {currency}"
        if not dividend_text.upper().endswith(currency_suffix):
            raise ValueError(f"calendar entry {index} has invalid dividend")
        dividend = _finite_number(
            dividend_text[: -len(currency_suffix)],
            field="dividend",
            index=index,
        )
        if dividend <= 0:
            raise ValueError(f"calendar entry {index} has invalid dividend")

        yield_text = str(entry["yield"]).strip()
        if not yield_text.endswith("%"):
            raise ValueError(f"calendar entry {index} has invalid yield")
        dividend_yield = _finite_number(yield_text[:-1], field="yield", index=index)
        if not 0 < dividend_yield <= 100:
            raise ValueError(f"calendar entry {index} has invalid yield")

        validated.append(entry)
    return validated
