import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.approved_api_publisher import (
    ApiPublishError,
    OfficialApiAdapter,
    PublicationBlocked,
    PublisherJournal,
    _gate_enabled,
    _platform_copy_matches,
    build_publish_plan,
    execute_plan,
    scan_approved_packets,
)
from src.review_packets import approve_review_packet, build_review_manifest, write_review_manifest


NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture(autouse=True)
def _enable_approved_packet_gate(monkeypatch):
    monkeypatch.setenv("APPROVED_PACKET_PUBLISHING_ALLOWED", "true")


def _approved_packet(
    tmp_path: Path,
    *,
    post_type="social_feed",
    targets=("meta_facebook",),
    media_kind="image",
    label="default",
    base_now=NOW,
    ttl_hours=24,
) -> Path:
    packet = tmp_path / f"packet-{post_type}-{label}"
    packet.mkdir()
    asset = packet / ("media.png" if media_kind == "image" else "media.mp4")
    asset.write_bytes(b"approved-image" if media_kind == "image" else b"approved-video")
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type=post_type,
        title="Geprüfter Inhalt",
        caption="Geprüfter Text. Keine Anlageberatung.",
        comment_text="Optionaler erster Kommentar.",
        tags=["Finanzen", "Shorts"],
        copied_assets=[asset],
        review_metadata={
            "generated_at": base_now.isoformat(),
            "review_expires_at": (base_now + timedelta(hours=ttl_hours)).isoformat(),
            "source_records": [],
        },
        now=base_now,
    )
    path = packet / "review_manifest.json"
    write_review_manifest(path, manifest)
    approve_review_packet(
        path,
        approved_by="Frank via Telegram",
        targets=list(targets),
        apply=True,
        now=base_now,
    )
    return path


def test_platform_copy_match_allows_only_whitespace_normalization():
    expected = "Erster Absatz.  \nMehr erfahren 👉 Link"

    assert _platform_copy_matches(expected, "Erster Absatz. \nMehr erfahren 👉 Link") is True
    assert _platform_copy_matches(expected, "Erster Absatz. Mehr erfahren Link") is False
    assert _platform_copy_matches(expected, "Erster Absatz. Mehr erfahren 👉 anderer Link") is False


def _inspector(kind):
    return lambda _path: {"kind": kind, "mime_type": "image/png" if kind == "image" else "video/mp4"}


class FakeAdapter:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.preflight_calls = 0
        self.publish_calls = 0

    def preflight(self, plan):
        self.preflight_calls += 1
        return {"verified": True, "target": plan.target}

    def publish(self, plan, spool_path):
        self.publish_calls += 1
        assert spool_path.is_file()
        assert spool_path.read_bytes() == plan.media_path.read_bytes()
        if self.fail:
            raise ApiPublishError("simulated ambiguous timeout")
        return {
            "status": "public",
            "external_id": f"external-{plan.target}",
            "external_url": f"https://example.test/{plan.target}/1",
            "evidence": ["public state verified by GET"],
        }


def test_schema3_plan_binds_approval_target_copy_asset_and_public_mode(tmp_path):
    path = _approved_packet(tmp_path)

    plan = build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )

    assert plan.target == "meta_facebook"
    assert plan.visibility == "public"
    assert plan.media_kind == "image"
    assert plan.caption.startswith("Geprüfter Text")
    assert plan.comment == "Optionaler erster Kommentar."
    assert len(plan.fingerprint) == 64
    assert plan.approval_payload_sha256


def test_plan_rejects_wrong_media_kind_for_target_and_tampered_approval(tmp_path):
    path = _approved_packet(tmp_path)
    with pytest.raises(PublicationBlocked, match="requires image"):
        build_publish_plan(
            path,
            "meta_facebook",
            now=NOW + timedelta(minutes=2),
            media_inspector=_inspector("video"),
        )

    data = json.loads(path.read_text())
    data["copy"]["meta_caption"] = "tampered"
    path.write_text(json.dumps(data))
    with pytest.raises(Exception, match="payload sha256 changed"):
        build_publish_plan(
            path,
            "meta_facebook",
            now=NOW + timedelta(minutes=2),
            media_inspector=_inspector("image"),
        )


def test_target_specific_fingerprints_differ_for_same_reel(tmp_path):
    path = _approved_packet(
        tmp_path,
        post_type="ai_reel_bundle",
        targets=("youtube", "meta_facebook", "meta_instagram"),
        media_kind="video",
    )
    plans = [
        build_publish_plan(
            path,
            target,
            now=NOW + timedelta(minutes=2),
            media_inspector=_inspector("video"),
        )
        for target in ("youtube", "meta_facebook", "meta_instagram")
    ]
    assert len({plan.fingerprint for plan in plans}) == 3
    assert all(plan.visibility == "public" for plan in plans)


def test_dry_plan_does_not_create_journal_or_change_manifest(tmp_path):
    path = _approved_packet(tmp_path)
    before = path.read_bytes()
    journal_path = tmp_path / "state" / "publisher.sqlite3"

    build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )

    assert not journal_path.exists()
    assert path.read_bytes() == before


def test_success_is_journaled_and_second_execute_never_mutates_again(tmp_path):
    path = _approved_packet(tmp_path)
    plan = build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )
    journal = PublisherJournal(tmp_path / "state" / "publisher.sqlite3")
    adapter = FakeAdapter()

    first = execute_plan(plan, journal=journal, adapter=adapter, state_dir=tmp_path / "state")
    second = execute_plan(plan, journal=journal, adapter=adapter, state_dir=tmp_path / "state")

    assert first["external_id"] == "external-meta_facebook"
    assert second == first
    assert adapter.publish_calls == 1
    stored = json.loads(path.read_text())
    result = stored["publishing"]["results"]["meta_facebook"]
    assert result["status"] == "public"
    assert result["fingerprint"] == plan.fingerprint


def test_manifest_result_without_journal_blocks_instead_of_double_posting(tmp_path):
    path = _approved_packet(tmp_path)
    plan = build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )
    adapter = FakeAdapter()
    first_journal = PublisherJournal(tmp_path / "state-a" / "publisher.sqlite3")
    execute_plan(plan, journal=first_journal, adapter=adapter, state_dir=tmp_path / "state-a")

    lost_journal_replacement = PublisherJournal(tmp_path / "state-b" / "publisher.sqlite3")
    with pytest.raises(PublicationBlocked, match="reconciliation"):
        execute_plan(
            plan,
            journal=lost_journal_replacement,
            adapter=adapter,
            state_dir=tmp_path / "state-b",
        )
    assert adapter.publish_calls == 1


def test_failure_after_mutation_boundary_becomes_unknown_and_is_never_retried(tmp_path):
    path = _approved_packet(tmp_path)
    plan = build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )
    journal = PublisherJournal(tmp_path / "state" / "publisher.sqlite3")
    adapter = FakeAdapter(fail=True)

    with pytest.raises(ApiPublishError):
        execute_plan(plan, journal=journal, adapter=adapter, state_dir=tmp_path / "state")
    assert journal.get(plan)["state"] == "unknown"

    with pytest.raises(PublicationBlocked, match="unknown"):
        execute_plan(plan, journal=journal, adapter=adapter, state_dir=tmp_path / "state")
    assert adapter.publish_calls == 1


def test_existing_mutation_started_is_promoted_to_unknown_without_retry(tmp_path):
    path = _approved_packet(tmp_path)
    plan = build_publish_plan(
        path,
        "meta_facebook",
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )
    journal = PublisherJournal(tmp_path / "state" / "publisher.sqlite3")
    journal.prepare(plan)
    journal.mark_started(plan)
    adapter = FakeAdapter()

    with pytest.raises(PublicationBlocked, match="unknown"):
        execute_plan(plan, journal=journal, adapter=adapter, state_dir=tmp_path / "state")
    assert journal.get(plan)["state"] == "unknown"
    assert adapter.publish_calls == 0


def test_expired_packets_do_not_starve_fresh_approved_packet(tmp_path):
    old_base = NOW - timedelta(days=2)
    for index in range(3):
        _approved_packet(
            tmp_path,
            label=f"expired-{index}",
            base_now=old_base,
            ttl_hours=1,
        )
    fresh = _approved_packet(tmp_path, label="fresh")
    fresh_packet_id = json.loads(fresh.read_text())["packet_id"]
    adapter = FakeAdapter()
    journal = PublisherJournal(tmp_path / "state" / "publisher.sqlite3")

    events = scan_approved_packets(
        tmp_path,
        journal=journal,
        adapter=adapter,
        state_dir=tmp_path / "state",
        execute=True,
        limit=1,
        now=NOW + timedelta(minutes=2),
        media_inspector=_inspector("image"),
    )

    assert [event["packet_id"] for event in events] == [fresh_packet_id]
    assert adapter.publish_calls == 1


def test_approved_packet_gate_is_strict(monkeypatch):
    monkeypatch.delenv("APPROVED_PACKET_PUBLISHING_ALLOWED", raising=False)
    assert _gate_enabled() is False
    monkeypatch.setenv("APPROVED_PACKET_PUBLISHING_ALLOWED", "yes")
    assert _gate_enabled() is False
    monkeypatch.setenv("APPROVED_PACKET_PUBLISHING_ALLOWED", " true ")
    assert _gate_enabled() is True


def test_meta_adapter_uses_bearer_header_and_disables_redirects(tmp_path, monkeypatch):
    adapter = OfficialApiAdapter(tmp_path)
    monkeypatch.setenv("PAGE_TOKEN", "secret-page-token")
    captured = {}

    class Response:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"id": "expected"}

    def request(method, url, **kwargs):
        captured.update({"method": method, "url": url, **kwargs})
        return Response()

    monkeypatch.setattr(adapter.session, "request", request)
    assert adapter._meta("GET", "expected", params={"fields": "id"}) == {"id": "expected"}
    assert captured["headers"] == {"Authorization": "Bearer secret-page-token"}
    assert captured["params"] == {"fields": "id"}
    assert "secret-page-token" not in captured["url"]
    assert captured["allow_redirects"] is False
