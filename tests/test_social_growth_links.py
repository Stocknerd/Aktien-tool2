from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.social_growth_links import calendar_url, stock_analysis_url, stock_duel_url


def _query(url):
    return parse_qs(urlparse(url).query)


def test_stock_analysis_url_prefills_ticker_and_has_bounded_social_attribution():
    url = stock_analysis_url(" brk-b ")

    assert urlparse(url).netloc == "tool.schatzsuche40.de"
    assert _query(url) == {
        "ticker": ["BRK-B"],
        "utm_source": ["social"],
        "utm_medium": ["organic_social"],
        "utm_campaign": ["stock_analysis"],
        "utm_content": ["BRK-B"],
    }


def test_stock_duel_url_prefills_both_tickers_and_has_social_attribution():
    url = stock_duel_url("AAPL", "MSFT")

    assert urlparse(url).netloc == "compare.schatzsuche40.de"
    assert _query(url) == {
        "t1": ["AAPL"],
        "t2": ["MSFT"],
        "utm_source": ["social"],
        "utm_medium": ["organic_social"],
        "utm_campaign": ["stock_duel"],
        "utm_content": ["AAPL_vs_MSFT"],
    }


def test_calendar_url_targets_the_interactive_tool_with_social_attribution():
    url = calendar_url()

    assert urlparse(url).path == "/dividenden-kalender"
    assert _query(url) == {
        "utm_source": ["social"],
        "utm_medium": ["organic_social"],
        "utm_campaign": ["dividend_calendar"],
    }


def test_social_deep_links_reject_untrusted_ticker_characters():
    try:
        stock_duel_url("AAPL&redirect=https://example.test", "MSFT")
    except ValueError as error:
        assert "ticker" in str(error).lower()
    else:
        raise AssertionError("unsafe ticker must be rejected")


def test_runtime_stock_and_calendar_tracks_use_the_central_deep_link_helpers():
    source = Path("src/social_reels_autoposter.py").read_text(encoding="utf-8")

    assert "stock_duel_url(sym_a, sym_b)" in source
    assert "stock_analysis_url(sym)" in source
    assert "calendar_url()" in source
