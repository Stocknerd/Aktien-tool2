"""Performance-based topic selection for the Schatzsuche 4.0 social pipeline."""

from __future__ import annotations

import random
from collections.abc import Sequence


# Based on the 2026-07 performance audit: personal posts and current financial
# changes consistently outperformed generic automated stock clips.
CONTENT_PRIORITY = {
    "personal_update": 100,
    "current_finance_news": 90,
    "evergreen_education": 60,
    "stock_feed": 35,
    "generic_stock_video": 10,
}

# Deliberately narrow fallback pool. Generic single-stock checks and random
# comparisons stay out of the automated video track.
PRIORITY_EVERGREEN_TOPICS = (
    "ETF-Rente: Was sie für die private Altersvorsorge bedeutet",
    "Altersvorsorge für Familien: Die wichtigsten Stellschrauben",
    "Kinderdepot: Chancen, Steuern und typische Fehler",
    "Elterngeld und Geldanlage: Was Familien beachten sollten",
    "ETF-Sparplan in der Familienplanung sinnvoll strukturieren",
    "Freistellungsauftrag für Familien einfach erklärt",
    "Notgroschen oder ETF-Sparplan: Was kommt zuerst?",
    "Dividenden richtig einordnen: Cashflow ist nicht gleich Rendite",
)


def recommended_weekly_schedule() -> dict[str, tuple[str, ...]]:
    """Return the quality-first weekly mix used by the optimized scheduler."""

    return {
        "stock_feed": ("mon", "wed", "fri"),
        "current_topic_reel": ("tue", "thu"),
        "dividend_calendar": ("sun",),
        "personal_canva": ("on_demand",),
    }


def choose_automated_topic(
    dynamic_topic: str | None,
    evergreen_topics: Sequence[str] = PRIORITY_EVERGREEN_TOPICS,
    *,
    random_index: int | None = None,
) -> tuple[str, str]:
    """Choose a current topic first, then a curated family-finance fallback.

    The returned tuple contains ``(topic, content_pillar)``. A caller can pass
    ``random_index`` to make dry-runs and tests deterministic.
    """

    cleaned_dynamic = (dynamic_topic or "").strip()
    if cleaned_dynamic:
        return cleaned_dynamic, "current_finance_news"

    topics = tuple(topic.strip() for topic in evergreen_topics if topic and topic.strip())
    if not topics:
        raise ValueError("evergreen_topics must contain at least one topic")

    if random_index is None:
        chosen = random.choice(topics)
    else:
        chosen = topics[random_index % len(topics)]
    return chosen, "evergreen_education"
