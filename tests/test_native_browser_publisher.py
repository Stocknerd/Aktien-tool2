import hashlib
import json
from pathlib import Path

import pytest

from src.approve_canva_packet import approve_packet
from src.native_browser_publisher import (
    DuplicatePublication,
    ManifestValidationError,
    META_BUSINESS_ID,
    META_FACEBOOK_ASSET_ID,
    META_FACEBOOK_PAGE_NAME,
    YOUTUBE_CHANNEL_ID,
    YOUTUBE_CHANNEL_NAME,
    build_action_plan,
    record_result,
)
from src.publishing_safety import (
    dispatch_or_prepare,
    public_dispatch_enabled,
    validate_calendar_entries,
)


def _write_approved_packet(tmp_path: Path, target: str = "youtube") -> Path:
    media = tmp_path / "approved-export.mp4"
    media.write_bytes(b"reviewed-video")
    digest = hashlib.sha256(media.read_bytes()).hexdigest()
    targets = {
        "youtube": {
            "channel_name": YOUTUBE_CHANNEL_NAME,
            "channel_id": YOUTUBE_CHANNEL_ID,
            "mode": "private",
        },
        "meta_facebook": {
            "page_name": META_FACEBOOK_PAGE_NAME,
            "asset_id": META_FACEBOOK_ASSET_ID,
            "business_id": META_BUSINESS_ID,
            "mode": "draft",
        },
    }
    manifest = {
        "schema_version": 2,
        "packet_id": "packet-001",
        "project": "schatzsuche4.0",
        "status": "approved",
        "requires_manual_approval": False,
        "media": {
            "path": media.name,
            "sha256": digest,
            "reviewed": True,
            "audio_strategy": "platform_audio_later",
        },
        "copy": {
            "youtube_title": "Geprüfter Test #shorts",
            "youtube_description": "Nur ein privater Test.",
            "meta_caption": "Geprüfter Facebook-Entwurf.",
        },
        "publishing": {
            "allowed": True,
            "requested_targets": ["youtube", "meta_facebook"],
            "approval": {
                "approved_by": "frank",
                "approved_at": "2026-07-16T12:00:00+02:00",
            },
            "targets": targets,
            "results": {},
        },
    }
    path = tmp_path / "post_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_reviewed_export_approval_unlocks_a_valid_safe_plan(tmp_path, monkeypatch):
    manifest_path = _write_approved_packet(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["status"] = "needs_canva"
    data["requires_manual_approval"] = True
    data["media"] = {
        "path": None,
        "sha256": None,
        "reviewed": False,
        "audio_strategy": "unset",
    }
    data["publishing"]["allowed"] = False
    data["publishing"]["approval"] = None
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    source = tmp_path / "canva-export.mp4"
    source.write_bytes(b"technically-reviewed-video")
    monkeypatch.setattr(
        "src.approve_canva_packet.inspect_video",
        lambda _path, _audio: {
            "codec": "h264",
            "width": 1080,
            "height": 1920,
            "duration_seconds": 25.3,
            "size_bytes": 14_000_000,
            "audio_streams": 0,
        },
    )

    result = approve_packet(
        manifest_path,
        source,
        approved_by="frank",
        audio_strategy="platform_audio_later",
        apply=True,
    )
    plan = build_action_plan(manifest_path, "youtube")

    assert result["approved"] is True
    assert plan.media_path.name == "reviewed_export.mp4"
    assert plan.mode == "private"


def test_youtube_plan_requires_exact_safe_target_and_reviewed_media(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)

    plan = build_action_plan(manifest_path, "youtube")

    assert plan.mode == "private"
    assert plan.visible_name == YOUTUBE_CHANNEL_NAME
    assert plan.stable_id == YOUTUBE_CHANNEL_ID
    assert plan.media_path.name == "approved-export.mp4"
    assert plan.title == "Geprüfter Test #shorts"


def test_meta_plan_is_draft_only(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)

    plan = build_action_plan(manifest_path, "meta_facebook")

    assert plan.mode == "draft"
    assert plan.visible_name == META_FACEBOOK_PAGE_NAME
    assert plan.stable_id == META_FACEBOOK_ASSET_ID
    assert plan.caption == "Geprüfter Facebook-Entwurf."


def test_manifest_fails_closed_without_explicit_approval(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["publishing"]["allowed"] = False
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="publishing.allowed"):
        build_action_plan(manifest_path, "youtube")


def test_manifest_rejects_wrong_channel_id(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["publishing"]["targets"]["youtube"]["channel_id"] = "WRONG"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="target contract"):
        build_action_plan(manifest_path, "youtube")


def test_manifest_rejects_changed_media_after_review(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)
    (tmp_path / "approved-export.mp4").write_bytes(b"changed-after-review")

    with pytest.raises(ManifestValidationError, match="sha256"):
        build_action_plan(manifest_path, "youtube")


def test_recorded_result_blocks_duplicate_platform_action(tmp_path):
    manifest_path = _write_approved_packet(tmp_path)
    plan = build_action_plan(manifest_path, "youtube")
    record_result(
        manifest_path,
        plan,
        status="private",
        external_id="video-123",
        external_url="https://studio.youtube.com/video/video-123/edit",
        evidence=["title persisted", "visibility private"],
    )

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["publishing"]["results"]["youtube"]["status"] == "private"
    assert saved["publishing"]["results"]["youtube"]["fingerprint"] == plan.fingerprint

    with pytest.raises(DuplicatePublication):
        build_action_plan(manifest_path, "youtube")


def test_public_dispatch_requires_two_independent_opt_ins():
    assert public_dispatch_enabled(prepare_only=True, public_allowed=True) is False
    assert public_dispatch_enabled(prepare_only=False, public_allowed=False) is False
    assert public_dispatch_enabled(prepare_only=False, public_allowed=True) is True


def test_manual_mode_short_circuits_every_external_dispatch():
    calls = []

    result = dispatch_or_prepare(
        prepare_only=True,
        prepare=lambda: calls.append("prepare") or "packet-dir",
        dispatchers=(
            ("instagram", lambda: calls.append("instagram")),
            ("facebook", lambda: calls.append("facebook")),
            ("youtube", lambda: calls.append("youtube")),
            ("tiktok", lambda: calls.append("tiktok")),
        ),
    )

    assert result == {"mode": "prepared", "artifact": "packet-dir"}
    assert calls == ["prepare"]


def test_calendar_requires_real_complete_entries_and_never_fills_fallbacks():
    verified = [
        {
            "symbol": "REAL",
            "name": "Real Company",
            "ex_date": "2026-07-20",
            "dividend": "0.42 EUR",
            "yield": "2.1%",
            "currency": "EUR",
        },
        {
            "symbol": "TRUE",
            "name": "True Company",
            "ex_date": "2026-07-22",
            "dividend": "0.30 EUR",
            "yield": "1.8%",
            "currency": "EUR",
        },
        {
            "symbol": "FACT",
            "name": "Fact Company",
            "ex_date": "2026-07-24",
            "dividend": "0.55 EUR",
            "yield": "2.4%",
            "currency": "EUR",
        },
    ]
    assert validate_calendar_entries(verified, minimum=3) == verified

    with pytest.raises(ValueError, match="verified dividend entries"):
        validate_calendar_entries(verified[:2], minimum=3)

    incomplete = [dict(verified[0], ex_date="--"), *verified[1:]]
    with pytest.raises(ValueError, match="incomplete"):
        validate_calendar_entries(incomplete, minimum=3)
