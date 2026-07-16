"""Dependency-free validation and formatting for grounded finance-news inputs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree


def _element_text(element, tag: str) -> str:
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _bounded_text(value: object, limit: int) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def parse_rss_headlines(xml_content: bytes | str, *, limit: int = 12) -> list[dict[str, str]]:
    """Parse standard RSS items into title, URL and publication metadata."""

    if limit < 1:
        return []
    root = ElementTree.fromstring(xml_content)
    headlines: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = _bounded_text(_element_text(item, "title"), 180)
        if not title:
            continue
        headlines.append(
            {
                "title": title,
                "url": _bounded_text(_element_text(item, "link"), 500),
                "published": _bounded_text(_element_text(item, "pubDate"), 100),
            }
        )
        if len(headlines) >= limit:
            break
    return headlines


def filter_fresh_headlines(
    items: list[dict[str, str]],
    *,
    now: datetime | None = None,
    max_age_hours: int = 48,
) -> list[dict[str, str]]:
    """Keep only dated, recent HTTPS headlines with complete provenance."""

    if max_age_hours < 1:
        raise ValueError("max_age_hours must be positive")
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)
    oldest = reference - timedelta(hours=max_age_hours)
    newest = reference + timedelta(hours=1)

    fresh: list[dict[str, str]] = []
    for item in items:
        title = _bounded_text(item.get("title"), 180)
        url = _bounded_text(item.get("url"), 500)
        published = _bounded_text(item.get("published"), 100)
        parsed_url = urlparse(url)
        try:
            hostname = parsed_url.hostname
            has_credentials = parsed_url.username is not None or parsed_url.password is not None
        except ValueError:
            hostname = None
            has_credentials = True
        if (
            not title
            or parsed_url.scheme != "https"
            or not hostname
            or has_credentials
            or not published
        ):
            continue
        try:
            published_at = parsedate_to_datetime(published)
        except (TypeError, ValueError, OverflowError):
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        published_at = published_at.astimezone(timezone.utc)
        if not oldest <= published_at <= newest:
            continue
        fresh.append({"title": title, "url": url, "published": published})
    return fresh


def validate_source_records(
    items: object,
    *,
    now: datetime | None = None,
    max_age_hours: int = 48,
) -> list[dict[str, str]]:
    """Normalize complete source records and reject the whole set if one is unsafe or stale."""

    if not isinstance(items, list) or not items:
        raise ValueError("source_records must contain at least one fresh source")
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("source_records must contain only source objects")
    validated = filter_fresh_headlines(items, now=now, max_age_hours=max_age_hours)
    if len(validated) != len(items):
        raise ValueError("every source record must be a fresh source with title, dated HTTPS URL and hostname")
    return validated


def format_news_context(items: list[dict[str, str]]) -> str:
    """Serialize bounded source records as JSON data, not prompt instructions."""

    bounded = [
        {
            "title": _bounded_text(item.get("title"), 180),
            "url": _bounded_text(item.get("url"), 500),
            "published": _bounded_text(item.get("published"), 100),
        }
        for item in items[:12]
        if _bounded_text(item.get("title"), 180)
    ]
    return json.dumps(bounded, ensure_ascii=False, separators=(",", ":"))


def first_news_title(context: str) -> str | None:
    """Return the first bounded title from a serialized validated source context."""

    try:
        items = json.loads(context)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    if not isinstance(first, dict):
        return None
    title = _bounded_text(first.get("title"), 180)
    return title or None
