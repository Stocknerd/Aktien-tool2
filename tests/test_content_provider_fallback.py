import json
from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import pytest
import httpx

from src import content_generator


def _valid_viral_content():
    return {
        "headline": "ETF-Rente im Überblick",
        "subheadline": "Was Familien jetzt prüfen sollten",
        "highlight_value": "5 Punkte",
        "highlight_label": "Kurzcheck",
        "card_points": [f"Punkt {index}: sachliche Erklärung" for index in range(1, 6)],
        "image_prompt": "Eine klar strukturierte 9:16-Finanzinfografik in Gold und Petrol.",
        "caption_ig": (
            "Was bedeutet das für Familien? Sachlicher Überblick. "
            "Keine Anlageberatung. Alle Angaben ohne Gewähr. Investments bergen Risiken."
        ),
        "caption_tiktok": "ETF-Rente kurz erklärt. Keine Anlageberatung.",
        "caption_shorts": "ETF-Rente für Familien kompakt. Keine Anlageberatung.",
        "reel_script": " ".join(f"Wort{index}" for index in range(60)),
    }


@pytest.fixture(autouse=True)
def _configured_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


class _GoogleResponse:
    def __init__(self, content, *, status_code=200, headers=None):
        self._content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"google status {self.status_code}")

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(self._content, ensure_ascii=False)}]
                    }
                }
            ]
        }


def test_openai_failure_falls_back_to_google_and_reuses_strict_validator(monkeypatch):
    captured = {}

    quota_response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )

    def fail_openai(**kwargs):
        raise content_generator.RateLimitError(
            "insufficient_quota",
            response=quota_response,
            body={"error": {"code": "insufficient_quota"}},
        )

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, payload=json, timeout=timeout)
        return _GoogleResponse(_valid_viral_content())

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_CHAT_MODEL", "gemini-test-model")
    monkeypatch.setattr(content_generator.client.chat.completions, "create", fail_openai)
    monkeypatch.setattr(content_generator.requests, "post", fake_post)

    result = content_generator.generate_structured_content(
        "Warum ETF-Sparpläne eine solide Basis sind",
        template_type="viral_list",
    )

    assert result["headline"] == "ETF-Rente im Überblick"
    assert result["requires_manual_review"] is True
    assert result["publishing_allowed"] is False
    assert captured["url"].endswith("/models/gemini-test-model:generateContent")
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "x-goog-api-key": "test-google-key",
    }
    assert "key=" not in captured["url"]
    assert captured["payload"]["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.parametrize("transient_status", [408, 503])
def test_google_fallback_retries_transient_provider_failure(monkeypatch, transient_status):
    responses = [
        _GoogleResponse({}, status_code=transient_status),
        _GoogleResponse(_valid_viral_content()),
    ]
    waits = []

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            content_generator.PrimaryProviderUnavailable("quota exhausted")
        ),
    )
    monkeypatch.setattr(
        content_generator.requests,
        "post",
        lambda *args, **kwargs: responses.pop(0),
    )
    monkeypatch.setattr(content_generator.time, "sleep", waits.append)

    result = content_generator.generate_structured_content(
        "ETF-Grundlagen",
        template_type="viral_list",
    )

    assert result["headline"] == "ETF-Rente im Überblick"
    assert waits == [2]
    assert responses == []


def test_openai_http_408_is_an_approved_fallback_boundary():
    response = httpx.Response(
        408,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    error = content_generator.APIStatusError(
        "request timeout",
        response=response,
        body={"error": {"code": "request_timeout"}},
    )

    assert content_generator._openai_fallback_allowed(error) is True


def test_google_retry_after_is_honored_but_bounded():
    assert content_generator._retry_delay_seconds(
        _GoogleResponse({}, status_code=429, headers={"Retry-After": "7"}),
        0,
    ) == 7
    assert content_generator._retry_delay_seconds(
        _GoogleResponse({}, status_code=429, headers={"Retry-After": "120"}),
        0,
    ) == 30


def test_google_fallback_repairs_mechanical_caption_and_unused_script_contract(monkeypatch):
    repairable = _valid_viral_content()
    repairable["caption_ig"] = "Sachlicher Überblick für Familien."
    repairable["reel_script"] = " ".join(f"Wort{index}" for index in range(105))
    requests_made = []

    def fake_post(url, *, headers, json, timeout):
        requests_made.append(json["contents"][0]["parts"][0]["text"])
        return _GoogleResponse(repairable)

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            content_generator.PrimaryProviderUnavailable("quota exhausted")
        ),
    )
    monkeypatch.setattr(content_generator.requests, "post", fake_post)

    result = content_generator.generate_structured_content(
        "ETF-Grundlagen",
        template_type="viral_list",
    )

    assert result["headline"] == "ETF-Rente im Überblick"
    assert result["caption_ig"].endswith(
        "Keine Anlageberatung. Alle Angaben ohne Gewähr. Investments bergen Risiken."
    )
    assert len(result["reel_script"].split()) == 80
    assert len(requests_made) == 1


def test_google_fallback_output_cannot_bypass_content_validation(monkeypatch):
    unsafe = _valid_viral_content()
    unsafe["card_points"] = unsafe["card_points"][:4]

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            content_generator.PrimaryProviderUnavailable("quota exhausted")
        ),
    )
    monkeypatch.setattr(
        content_generator.requests,
        "post",
        lambda *args, **kwargs: _GoogleResponse(unsafe),
    )

    with pytest.raises(ValueError, match="card_points"):
        content_generator.generate_structured_content("ETF-Grundlagen", template_type="viral_list")


def test_affirmative_anlageberatung_wording_is_not_a_valid_disclaimer():
    content = _valid_viral_content()
    content["caption_ig"] = "Dies ist individuelle Anlageberatung für dich."

    with pytest.raises(ValueError, match="canonical disclaimer"):
        content_generator.validate_structured_content(content, template_type="viral_list")


def test_google_news_fallback_remains_manual_review_only(monkeypatch):
    source_records = [
        {
            "title": "Aktuelle ETF-Meldung",
            "url": "https://example.test/aktuell",
            "published": format_datetime(datetime.now(timezone.utc)),
        }
    ]

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            content_generator.PrimaryProviderUnavailable("quota exhausted")
        ),
    )
    monkeypatch.setattr(
        content_generator.requests,
        "post",
        lambda *args, **kwargs: _GoogleResponse(_valid_viral_content()),
    )

    result = content_generator.generate_structured_content(
        "Aktuelle ETF-Meldung",
        template_type="viral_list",
        source_context=json.dumps(source_records),
    )

    assert result["requires_manual_review"] is True
    assert result["publishing_allowed"] is False
    assert result["source_records"] == source_records


def test_programming_error_does_not_trigger_cross_provider_fallback(monkeypatch):
    google_called = False

    def fake_google(*args, **kwargs):
        nonlocal google_called
        google_called = True
        return _GoogleResponse(_valid_viral_content())

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("programming defect")),
    )
    monkeypatch.setattr(content_generator.requests, "post", fake_google)

    with pytest.raises(RuntimeError, match="programming defect"):
        content_generator.generate_structured_content("ETF-Grundlagen", template_type="viral_list")
    assert google_called is False


def test_openai_success_does_not_call_google(monkeypatch):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(_valid_viral_content(), ensure_ascii=False)
                )
            )
        ]
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: response,
    )
    monkeypatch.setattr(
        content_generator.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Google called")),
    )

    result = content_generator.generate_structured_content(
        "ETF-Grundlagen",
        template_type="viral_list",
    )

    assert result["headline"] == "ETF-Rente im Überblick"


def test_missing_google_key_preserves_openai_failure(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        content_generator.client.chat.completions,
        "create",
        lambda **kwargs: (_ for _ in ()).throw(
            content_generator.PrimaryProviderUnavailable("quota exhausted")
        ),
    )

    with pytest.raises(RuntimeError, match="quota exhausted"):
        content_generator.generate_structured_content("ETF-Grundlagen", template_type="viral_list")
