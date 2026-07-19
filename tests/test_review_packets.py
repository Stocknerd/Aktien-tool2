import hashlib
import json
from datetime import datetime, timezone

import pytest

from src.review_packets import (
    ApprovalError,
    approve_review_packet,
    build_review_manifest,
    verify_approved_review_packet,
    write_review_manifest,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stock_packet_manifest_is_schema3_and_fail_closed(tmp_path):
    packet = tmp_path / "stock-packet"
    packet.mkdir()
    media = packet / "media.png"
    media.write_bytes(b"real-stock-image")

    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="social_feed",
        title="Boeing vs Honeywell",
        caption="Sachlicher Vergleich. Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata=None,
        now=datetime(2026, 7, 19, 16, tzinfo=timezone.utc),
    )

    assert manifest["schema_version"] == 3
    assert manifest["project"] == "schatzsuche4.0"
    assert manifest["packet_id"] == packet.name
    assert manifest["status"] == "needs_review"
    assert manifest["requires_manual_approval"] is True
    assert manifest["review_expires_at"] == "2026-07-22T16:00:00+00:00"
    assert manifest["media"]["assets"] == [
        {
            "path": "media.png",
            "sha256": _sha256(media),
            "role": "primary",
            "reviewed": False,
        }
    ]
    assert manifest["publishing"]["allowed"] is False
    assert manifest["publishing"]["approval"] is None
    assert manifest["publishing"]["requested_targets"] == [
        "meta_facebook",
        "meta_instagram",
    ]
    assert manifest["publishing"]["blocked_targets"] == {
        "pinterest": "stable target identity is not configured in the packet contract",
        "x": "stable target identity is not configured in the packet contract",
    }
    assert manifest["publishing"]["results"] == {}


def test_ai_packet_manifest_preserves_sources_expiry_copy_and_companion_hash(tmp_path):
    packet = tmp_path / "ai-packet"
    packet.mkdir()
    video = packet / "media.mp4"
    image = packet / "media_1.png"
    video.write_bytes(b"reviewed-video-bytes")
    image.write_bytes(b"reviewed-image-bytes")
    metadata = {
        "content_pillar": "current_finance_news",
        "generated_at": "2026-07-19T15:00:00+00:00",
        "review_expires_at": "2026-07-21T15:00:00+00:00",
        "requires_manual_review": True,
        "publishing_allowed": False,
        "source_records": [
            {
                "title": "Belegte Meldung",
                "published": "Sun, 19 Jul 2026 14:00:00 GMT",
                "url": "https://example.test/source",
            }
        ],
    }

    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="ai_reel_bundle",
        title="Belegtes Finanzthema",
        caption="Quellenbasiert. Keine Anlageberatung.",
        comment_text="Mehr im Profil.",
        tags=["Finanzen", "Shorts"],
        copied_assets=[video, image],
        review_metadata=metadata,
    )

    assert manifest["content_pillar"] == "current_finance_news"
    assert manifest["review_expires_at"] == metadata["review_expires_at"]
    assert manifest["source_records"] == metadata["source_records"]
    assert manifest["copy"]["meta_caption"].startswith("Quellenbasiert")
    assert manifest["copy"]["youtube_title"].endswith("#shorts")
    assert manifest["copy"]["youtube_description"].startswith("Quellenbasiert")
    assert manifest["media"]["assets"][1]["role"] == "companion"
    assert manifest["media"]["assets"][1]["sha256"] == _sha256(image)
    assert manifest["publishing"]["requested_targets"] == [
        "youtube",
        "meta_facebook",
        "meta_instagram",
    ]


def test_manifest_write_and_approval_are_atomic_and_do_not_publish(tmp_path):
    packet = tmp_path / "packet"
    packet.mkdir()
    media = packet / "media.png"
    media.write_bytes(b"immutable")
    manifest_path = packet / "review_manifest.json"
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="social_feed",
        title="Vergleich",
        caption="Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata=None,
        now=datetime(2026, 7, 19, 16, tzinfo=timezone.utc),
    )
    write_review_manifest(manifest_path, manifest)
    before = manifest_path.read_bytes()

    preflight = approve_review_packet(
        manifest_path,
        approved_by="Frank",
        targets=["meta_facebook"],
        apply=False,
        now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
    )
    assert preflight["approved"] is False
    assert preflight["external_mutations"] == []
    assert manifest_path.read_bytes() == before

    applied = approve_review_packet(
        manifest_path,
        approved_by="Frank",
        targets=["meta_facebook"],
        apply=True,
        now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
    )
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert applied["approved"] is True
    assert applied["external_mutations"] == []
    assert stored["status"] == "approved"
    assert stored["requires_manual_approval"] is False
    assert stored["publishing"]["allowed"] is True
    assert stored["publishing"]["approval"]["approved_by"] == "Frank"
    assert stored["publishing"]["approval"]["approved_targets"] == ["meta_facebook"]
    assert stored["publishing"]["intended_targets"] == ["meta_facebook", "meta_instagram"]
    assert stored["publishing"]["requested_targets"] == ["meta_facebook"]
    assert list(stored["publishing"]["targets"]) == ["meta_facebook"]
    assert stored["media"]["assets"][0]["reviewed"] is True
    assert not list(packet.glob(".review_manifest.json.*.tmp"))

    verified = verify_approved_review_packet(
        manifest_path,
        target="meta_facebook",
        now=datetime(2026, 7, 19, 17, 30, tzinfo=timezone.utc),
    )
    assert verified["verified"] is True
    assert verified["external_mutations"] == []

    tampered_approval = json.loads(json.dumps(stored))
    tampered_approval["publishing"]["approval"]["approved_by"] = "Mallory"
    manifest_path.write_text(json.dumps(tampered_approval), encoding="utf-8")
    with pytest.raises(ApprovalError, match="payload sha256 changed"):
        verify_approved_review_packet(
            manifest_path,
            target="meta_facebook",
            now=datetime(2026, 7, 19, 17, 30, tzinfo=timezone.utc),
        )

    stored["copy"]["meta_caption"] = "Nach Freigabe manipuliert"
    manifest_path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ApprovalError, match="payload sha256 changed"):
        verify_approved_review_packet(
            manifest_path,
            target="meta_facebook",
            now=datetime(2026, 7, 19, 17, 30, tzinfo=timezone.utc),
        )


def test_manual_upload_writer_always_emits_schema3_manifest(tmp_path, monkeypatch):
    from social_publisher import save_for_manual_upload

    source = tmp_path / "generated.png"
    source.write_bytes(b"generated-stock-image")
    uploads = tmp_path / "uploads"
    monkeypatch.setenv("MANUAL_UPLOADS_DIR", str(uploads))
    monkeypatch.setenv("UPLOAD_TO_GDRIVE", "False")
    monkeypatch.setenv("GDRIVE_TRANSFER_ALLOWED", "False")

    assert save_for_manual_upload(
        post_type="social_feed",
        title="Boeing vs Honeywell",
        caption="Keine Anlageberatung.",
        asset_path=str(source),
    ) is True

    packets = list(uploads.iterdir())
    assert len(packets) == 1
    manifest_path = packets[0] / "review_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 3
    assert manifest["status"] == "needs_review"
    assert manifest["publishing"]["allowed"] is False
    assert manifest["media"]["assets"][0]["sha256"] == _sha256(packets[0] / "media.png")

    assert save_for_manual_upload(
        post_type="social_feed",
        title="Boeing vs Honeywell",
        caption="Keine Anlageberatung.",
        asset_path=str(source),
    ) is True
    assert len(list(uploads.iterdir())) == 2


def test_manifest_writer_does_not_follow_fixed_temp_or_target_symlinks(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("unchanged", encoding="utf-8")
    packet = tmp_path / "packet"
    packet.mkdir()
    fixed_temp = packet / "review_manifest.json.tmp"
    fixed_temp.symlink_to(victim)

    target = packet / "review_manifest.json"
    write_review_manifest(target, {"safe": True})
    assert victim.read_text(encoding="utf-8") == "unchanged"
    assert json.loads(target.read_text(encoding="utf-8")) == {"safe": True}

    target.unlink()
    target.symlink_to(victim)
    with pytest.raises(ApprovalError, match="symlinks"):
        write_review_manifest(target, {"unsafe": True})
    assert victim.read_text(encoding="utf-8") == "unchanged"


def test_review_window_is_capped_and_expires_at_the_exact_boundary(tmp_path):
    packet = tmp_path / "packet"
    packet.mkdir()
    media = packet / "media.png"
    media.write_bytes(b"asset")
    path = packet / "review_manifest.json"
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="social_feed",
        title="Zeitgebunden",
        caption="Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata={
            "generated_at": "2026-07-19T12:00:00+00:00",
            "review_expires_at": "2026-08-01T12:00:00+00:00",
        },
        now=datetime(2026, 7, 19, 13, tzinfo=timezone.utc),
    )
    assert manifest["review_expires_at"] == "2026-07-22T12:00:00+00:00"
    write_review_manifest(path, manifest)

    with pytest.raises(ApprovalError, match="expired"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["meta_facebook"],
            now=datetime(2026, 7, 22, 12, tzinfo=timezone.utc),
        )


def test_manual_writer_supports_text_only_but_rejects_missing_required_primary(
    tmp_path,
    monkeypatch,
):
    from social_publisher import save_for_manual_upload

    uploads = tmp_path / "uploads"
    monkeypatch.setenv("MANUAL_UPLOADS_DIR", str(uploads))
    monkeypatch.setenv("UPLOAD_TO_GDRIVE", "False")
    monkeypatch.setenv("GDRIVE_TRANSFER_ALLOWED", "False")

    assert save_for_manual_upload(
        post_type="facebook_feed",
        title="Textbeitrag",
        caption="Nur Text.",
        asset_path=None,
    ) is True
    text_packet = next(uploads.iterdir())
    text_manifest = json.loads(
        (text_packet / "review_manifest.json").read_text(encoding="utf-8")
    )
    assert text_manifest["media"]["assets"] == []

    missing_companion = tmp_path / "companion.png"
    missing_companion.write_bytes(b"companion")
    with pytest.raises(ValueError, match="requires a primary"):
        save_for_manual_upload(
            post_type="ai_reel_bundle",
            title="Unvollständig",
            caption="Keine Anlageberatung.",
            asset_path=None,
            additional_assets=[str(missing_companion)],
        )
    assert len(list(uploads.iterdir())) == 1


def test_approval_policy_rejects_cross_type_targets_and_malformed_copy(tmp_path):
    packet = tmp_path / "packet"
    packet.mkdir()
    media = packet / "media.png"
    media.write_bytes(b"asset")
    path = packet / "review_manifest.json"
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="social_feed",
        title="Policy",
        caption="Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata=None,
        now=datetime(2026, 7, 19, 16, tzinfo=timezone.utc),
    )

    manifest["post_type"] = "x_post"
    write_review_manifest(path, manifest)
    with pytest.raises(ApprovalError, match="target policy changed"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["meta_facebook"],
            now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
        )

    manifest["post_type"] = "social_feed"
    manifest["copy"] = None
    write_review_manifest(path, manifest)
    with pytest.raises(ApprovalError, match="copy must be an object"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["meta_facebook"],
            now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
        )

    with pytest.raises(ApprovalError, match="now must be a datetime"):
        build_review_manifest(
            packet_dir=packet,
            post_type="social_feed",
            title="Policy",
            caption="Keine Anlageberatung.",
            copied_assets=[media],
            review_metadata=None,
            now="2026-07-19",  # type: ignore[arg-type]
        )


def test_parallel_approvals_are_serialized(tmp_path, monkeypatch):
    import time
    from concurrent.futures import ThreadPoolExecutor
    import src.review_packets as review_packets

    packet = tmp_path / "packet"
    packet.mkdir()
    media = packet / "media.png"
    media.write_bytes(b"asset")
    path = packet / "review_manifest.json"
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="social_feed",
        title="Parallel",
        caption="Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata=None,
        now=datetime(2026, 7, 19, 16, tzinfo=timezone.utc),
    )
    write_review_manifest(path, manifest)
    original_write = review_packets.write_review_manifest

    def slow_write(*args, **kwargs):
        time.sleep(0.1)
        return original_write(*args, **kwargs)

    monkeypatch.setattr(review_packets, "write_review_manifest", slow_write)

    def approve(target):
        try:
            approve_review_packet(
                path,
                approved_by="Frank",
                targets=[target],
                apply=True,
                now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
            )
            return "approved"
        except ApprovalError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(approve, ["meta_facebook", "meta_instagram"]))
    assert sorted(outcomes) == ["approved", "rejected"]


def test_approval_rejects_changed_expired_or_unrequested_assets(tmp_path):
    packet = tmp_path / "packet"
    packet.mkdir()
    media = packet / "media.mp4"
    media.write_bytes(b"original")
    path = packet / "review_manifest.json"
    manifest = build_review_manifest(
        packet_dir=packet,
        post_type="ai_reel_bundle",
        title="Aktuelles Thema",
        caption="Keine Anlageberatung.",
        copied_assets=[media],
        review_metadata={
            "content_pillar": "current_finance_news",
            "generated_at": "2026-07-19T12:00:00+00:00",
            "review_expires_at": "2026-07-19T18:00:00+00:00",
            "requires_manual_review": True,
            "publishing_allowed": False,
            "source_records": [],
        },
    )
    write_review_manifest(path, manifest)

    with pytest.raises(ApprovalError, match="unsupported target"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["x"],
            now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
        )

    with pytest.raises(ApprovalError, match="expired"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["youtube"],
            now=datetime(2026, 7, 19, 19, tzinfo=timezone.utc),
        )

    media.write_bytes(b"changed")
    with pytest.raises(ApprovalError, match="sha256"):
        approve_review_packet(
            path,
            approved_by="Frank",
            targets=["youtube"],
            now=datetime(2026, 7, 19, 17, tzinfo=timezone.utc),
        )
