"""Auditierbare, fail-closed Freigabemanifeste für manuelle Social-Pakete."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT = "schatzsuche4.0"
SCHEMA_VERSION = 3
TEXT_ONLY_POST_TYPES = {"facebook_feed", "x_post"}

TARGET_CONTRACTS: dict[str, dict[str, str]] = {
    "youtube": {
        "channel_name": "Schatzsuche 4.0",
        "channel_id": "UCDj-MBezZKZIGMiK8t21oVA",
        "mode": "public_after_separate_staging_verification",
    },
    "meta_facebook": {
        "page_name": "Schatzsuche4.0",
        "asset_id": "112395201353218",
        "business_id": "625626605438788",
        "mode": "public_after_separate_draft_verification",
    },
    "meta_instagram": {
        "account_name": "schatzsuche4.0",
        "asset_id": "17841450855354386",
        "mode": "public_after_separate_preflight",
    },
}

_BLOCKED_REASON = "stable target identity is not configured in the packet contract"
_TARGETS_BY_POST_TYPE: dict[str, tuple[list[str], list[str]]] = {
    "social_feed": (["meta_facebook", "meta_instagram"], ["pinterest", "x"]),
    "ai_reel_bundle": (
        ["youtube", "meta_facebook", "meta_instagram"],
        ["pinterest", "tiktok", "x"],
    ),
    "youtube_shorts": (["youtube"], []),
    "facebook_feed": (["meta_facebook"], []),
    "instagram_feed": (["meta_instagram"], []),
    "instagram_reel": (["meta_instagram"], []),
    "x_post": ([], ["x"]),
    "pinterest_pin": ([], ["pinterest"]),
}
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ApprovalError(ValueError):
    """Das Paket darf in seinem aktuellen Zustand nicht freigegeben werden."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApprovalError(f"{field} is required")
    return value.strip()


def _datetime_value(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ApprovalError(f"{field} must be a datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError(f"{field} must be a valid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ApprovalError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _relative_asset(packet_dir: Path, asset: str | Path) -> tuple[Path, str]:
    raw_path = Path(asset)
    candidate = raw_path if raw_path.is_absolute() else packet_dir / raw_path
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(packet_dir)
    except ValueError as exc:
        raise ApprovalError("asset path escapes the packet directory") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ApprovalError(f"asset is missing or unsafe: {candidate}")
    return resolved, relative.as_posix()


def build_review_manifest(
    *,
    packet_dir: str | Path,
    post_type: str,
    title: str,
    caption: str,
    copied_assets: Sequence[str | Path],
    review_metadata: Mapping[str, Any] | None,
    comment_text: str | None = None,
    tags: Sequence[str] | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Erzeuge ein unveröffentlichtes Schema-3-Manifest für genau ein Paket."""

    directory = Path(packet_dir).expanduser().resolve()
    if not directory.is_dir():
        raise ApprovalError(f"packet directory does not exist: {directory}")
    if not copied_assets and post_type not in TEXT_ONLY_POST_TYPES:
        raise ApprovalError("at least one copied asset is required")

    metadata = dict(review_metadata or {})
    reference = _datetime_value(now or _utc_now(), "now")
    generated_at = metadata.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        generated_datetime = reference
        generated_at = generated_datetime.isoformat()
    else:
        generated_datetime = _parse_utc(generated_at, "generated_at")
    if generated_datetime > reference:
        raise ApprovalError("generated_at cannot be in the future")

    expires_at = metadata.get("review_expires_at")
    maximum_expiry = generated_datetime + timedelta(hours=72)
    if expires_at is not None:
        expires_at = _text(expires_at, "review_expires_at")
        explicit_expiry = _parse_utc(expires_at, "review_expires_at")
        if explicit_expiry <= generated_datetime:
            raise ApprovalError("review_expires_at must be after generated_at")
        expires_at = min(explicit_expiry, maximum_expiry).isoformat()
    else:
        expires_at = maximum_expiry.isoformat()

    source_records = metadata.get("source_records")
    if not isinstance(source_records, list):
        source_records = []

    requested_targets, blocked_targets = _TARGETS_BY_POST_TYPE.get(
        post_type,
        ([], []),
    )
    media_assets: list[dict[str, Any]] = []
    for index, asset in enumerate(copied_assets):
        resolved, relative = _relative_asset(directory, asset)
        media_assets.append(
            {
                "path": relative,
                "sha256": _sha256(resolved),
                "role": "primary" if index == 0 else "companion",
                "reviewed": False,
            }
        )

    clean_title = str(title or "").strip()
    clean_caption = str(caption or "").strip()
    if tags is None:
        normalized_tags: list[str] = []
    elif isinstance(tags, str):
        normalized_tags = [tags]
    elif isinstance(tags, (list, tuple)) and all(isinstance(tag, str) for tag in tags):
        normalized_tags = list(tags)
    else:
        raise ApprovalError("tags must contain only text values")
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_id": directory.name,
        "project": PROJECT,
        "created_at": generated_at,
        "status": "needs_review",
        "post_type": post_type,
        "content_pillar": metadata.get("content_pillar") or "generated_social",
        "review_expires_at": expires_at,
        "source_records": source_records,
        "requires_manual_approval": True,
        "media": {"assets": media_assets},
        "copy": {
            "title": clean_title,
            "caption": clean_caption,
            "comment": str(comment_text or "").strip(),
            "tags": normalized_tags or [],
            "youtube_title": f"{clean_title} #shorts".strip(),
            "youtube_description": clean_caption,
            "meta_caption": clean_caption,
        },
        "publishing": {
            "allowed": False,
            "reason": "Exact assets and targets require explicit manual approval.",
            "approval": None,
            "requested_targets": list(requested_targets),
            "targets": {name: dict(TARGET_CONTRACTS[name]) for name in requested_targets},
            "blocked_targets": {name: _BLOCKED_REASON for name in sorted(blocked_targets)},
            "results": {},
        },
    }


def write_review_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    """Schreibe ein Manifest atomar und dauerhaft auf das Dateisystem."""

    raw_target = Path(path).expanduser()
    parent = raw_target.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / raw_target.name
    if target.is_symlink():
        raise ApprovalError("manifest symlinks are not allowed")

    encoded = json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def _load_manifest(path: str | Path) -> tuple[Path, dict[str, Any]]:
    raw_path = Path(path).expanduser()
    if raw_path.is_symlink():
        raise ApprovalError("manifest symlinks are not allowed")
    manifest_path = raw_path.resolve()
    if not manifest_path.is_file():
        raise ApprovalError(f"manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApprovalError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ApprovalError("manifest must contain an object")
    return manifest_path, data


def _validate_manifest_policy(
    manifest_path: Path,
    data: Mapping[str, Any],
    *,
    approved: bool,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    if data.get("schema_version") != SCHEMA_VERSION or data.get("project") != PROJECT:
        raise ApprovalError("manifest is not a Schatzsuche schema-3 review packet")
    packet_id = _text(data.get("packet_id"), "packet_id")
    if packet_id != manifest_path.parent.name:
        raise ApprovalError("packet_id must match the packet directory")
    post_type = _text(data.get("post_type"), "post_type")
    policy = _TARGETS_BY_POST_TYPE.get(post_type)
    if policy is None:
        raise ApprovalError(f"unsupported post_type: {post_type}")
    intended_targets, blocked_targets = policy

    source_records = data.get("source_records")
    if not isinstance(source_records, list) or any(
        not isinstance(record, dict) for record in source_records
    ):
        raise ApprovalError("source_records must be a list of objects")
    copy = data.get("copy")
    if not isinstance(copy, dict):
        raise ApprovalError("copy must be an object")
    _text(copy.get("title"), "copy.title")
    _text(copy.get("caption"), "copy.caption")
    if not isinstance(copy.get("comment"), str):
        raise ApprovalError("copy.comment must be text")
    tags = copy.get("tags")
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ApprovalError("copy.tags must be a list of text values")
    if not isinstance(copy.get("youtube_title"), str) or not isinstance(
        copy.get("youtube_description"), str
    ) or not isinstance(copy.get("meta_caption"), str):
        raise ApprovalError("platform copy fields must be text")

    publishing = data.get("publishing")
    if not isinstance(publishing, dict):
        raise ApprovalError("publishing must be an object")
    requested = publishing.get("requested_targets")
    contracts = publishing.get("targets")
    results = publishing.get("results")
    if not isinstance(requested, list) or any(
        not isinstance(target, str) for target in requested
    ):
        raise ApprovalError("publishing.requested_targets must be a list of text values")
    if len(set(requested)) != len(requested):
        raise ApprovalError("publishing.requested_targets must be unique")
    if not isinstance(contracts, dict) or not isinstance(results, dict):
        raise ApprovalError("publishing.targets and publishing.results must be objects")
    expected_blocked = {name: _BLOCKED_REASON for name in sorted(blocked_targets)}
    if publishing.get("blocked_targets") != expected_blocked:
        raise ApprovalError("blocked target policy changed")

    if approved:
        if publishing.get("intended_targets") != intended_targets:
            raise ApprovalError("intended target policy changed")
    else:
        expected_contracts = {
            name: dict(TARGET_CONTRACTS[name]) for name in intended_targets
        }
        if requested != intended_targets or contracts != expected_contracts:
            raise ApprovalError("requested target policy changed")

    media = data.get("media")
    assets = media.get("assets") if isinstance(media, dict) else None
    if not isinstance(assets, list):
        raise ApprovalError("media.assets must be a list")
    expected_reviewed = approved
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict) or asset.get("reviewed") is not expected_reviewed:
            raise ApprovalError(
                f"media.assets[{index}].reviewed must be {str(expected_reviewed).lower()}"
            )
    return publishing, requested, contracts


def _validate_assets(manifest_path: Path, data: Mapping[str, Any]) -> dict[str, str]:
    media = data.get("media")
    assets = media.get("assets") if isinstance(media, dict) else None
    if not isinstance(assets, list):
        raise ApprovalError("media.assets must be a list")
    if not assets and data.get("post_type") not in TEXT_ONLY_POST_TYPES:
        raise ApprovalError("media.assets must contain at least one asset")

    hashes: dict[str, str] = {}
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ApprovalError(f"media.assets[{index}] must be an object")
        expected_role = "primary" if index == 0 else "companion"
        if asset.get("role") != expected_role:
            raise ApprovalError(f"media.assets[{index}].role must be {expected_role}")
        relative_text = _text(asset.get("path"), f"media.assets[{index}].path")
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts:
            raise ApprovalError("asset path must stay inside the packet directory")
        candidate = manifest_path.parent / relative
        resolved = candidate.resolve()
        try:
            resolved.relative_to(manifest_path.parent)
        except ValueError as exc:
            raise ApprovalError("asset path escapes the packet directory") from exc
        if candidate.is_symlink() or not resolved.is_file():
            raise ApprovalError(f"asset is missing or unsafe: {relative_text}")
        expected = _text(asset.get("sha256"), f"media.assets[{index}].sha256").lower()
        if not _SHA256_PATTERN.fullmatch(expected):
            raise ApprovalError(f"media.assets[{index}].sha256 is invalid")
        actual = _sha256(resolved)
        if actual != expected:
            raise ApprovalError(f"media asset sha256 changed: {relative_text}")
        normalized_path = relative.as_posix()
        if normalized_path in hashes:
            raise ApprovalError(f"duplicate media asset path: {normalized_path}")
        hashes[normalized_path] = actual
    return hashes


def _validate_review_window(data: Mapping[str, Any], reference: datetime) -> None:
    created_at = _parse_utc(_text(data.get("created_at"), "created_at"), "created_at")
    expires_at = _parse_utc(
        _text(data.get("review_expires_at"), "review_expires_at"),
        "review_expires_at",
    )
    normalized_reference = reference.astimezone(timezone.utc)
    if created_at > normalized_reference:
        raise ApprovalError("created_at cannot be in the future")
    if expires_at <= created_at:
        raise ApprovalError("review_expires_at must be after created_at")
    if expires_at > created_at + timedelta(hours=72):
        raise ApprovalError("review window exceeds 72 hours")
    if normalized_reference >= expires_at:
        raise ApprovalError("review packet has expired")


def _approval_payload_sha256(
    data: Mapping[str, Any],
    selected: Sequence[str],
    *,
    approved_by: str,
    approved_at: str,
) -> str:
    publishing = data.get("publishing")
    if not isinstance(publishing, dict):
        raise ApprovalError("publishing must be an object")
    contracts = publishing.get("targets")
    if not isinstance(contracts, dict):
        raise ApprovalError("publishing.targets must be an object")
    media = data.get("media")
    assets = media.get("assets") if isinstance(media, dict) else None
    if not isinstance(assets, list):
        raise ApprovalError("media.assets must be a list")
    stable_assets = [
        {
            "path": asset.get("path"),
            "sha256": asset.get("sha256"),
            "role": asset.get("role"),
        }
        for asset in assets
        if isinstance(asset, dict)
    ]
    if len(stable_assets) != len(assets):
        raise ApprovalError("media.assets contains an invalid entry")
    payload = {
        "schema_version": data.get("schema_version"),
        "packet_id": data.get("packet_id"),
        "project": data.get("project"),
        "created_at": data.get("created_at"),
        "post_type": data.get("post_type"),
        "content_pillar": data.get("content_pillar"),
        "review_expires_at": data.get("review_expires_at"),
        "source_records": data.get("source_records"),
        "media_assets": stable_assets,
        "copy": data.get("copy"),
        "approved_by": approved_by,
        "approved_at": approved_at,
        "approved_targets": list(selected),
        "target_contracts": {target: contracts.get(target) for target in selected},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@contextmanager
def _approval_lock(manifest_path: str | Path):
    raw_manifest = Path(manifest_path).expanduser()
    parent = raw_manifest.parent.resolve()
    lock_path = parent / f".{raw_manifest.name}.approval.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise ApprovalError(f"cannot open approval lock: {exc}") from exc
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _approve_review_packet_unlocked(
    manifest_path: str | Path,
    *,
    approved_by: str,
    targets: Sequence[str],
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prüfe oder dokumentiere eine Freigabe; führt niemals Plattformaktionen aus."""

    path, data = _load_manifest(manifest_path)
    if data.get("status") != "needs_review":
        raise ApprovalError("only a needs_review packet can be approved")
    if data.get("requires_manual_approval") is not True:
        raise ApprovalError("unapproved packet must require manual approval")
    approver = _text(approved_by, "approved_by")

    publishing, requested, contracts = _validate_manifest_policy(
        path,
        data,
        approved=False,
    )
    if not isinstance(publishing, dict) or publishing.get("allowed") is not False:
        raise ApprovalError("unapproved packet must be fail-closed")
    if publishing.get("approval") is not None or publishing.get("results") not in ({}, None):
        raise ApprovalError("packet already contains approval or platform results")
    selected = list(targets)
    if not selected or any(not isinstance(target, str) or not target for target in selected):
        raise ApprovalError("at least one target is required")
    if len(set(selected)) != len(selected):
        raise ApprovalError("targets must be unique")
    for target in selected:
        if target not in TARGET_CONTRACTS:
            raise ApprovalError(f"unsupported target: {target}")
        if target not in requested:
            raise ApprovalError(f"target was not requested: {target}")
        expected_contract = TARGET_CONTRACTS.get(target)
        stored_contract = contracts.get(target)
        if stored_contract != expected_contract:
            raise ApprovalError(f"target contract changed: {target}")

    reference = _datetime_value(now or _utc_now(), "now")
    _validate_review_window(data, reference)
    asset_hashes = _validate_assets(path, data)
    approved_at = reference.isoformat()
    payload_sha256 = _approval_payload_sha256(
        data,
        selected,
        approved_by=approver,
        approved_at=approved_at,
    )
    result = {
        "manifest": str(path),
        "packet_id": data.get("packet_id"),
        "approved": False,
        "approved_targets": selected,
        "asset_sha256": asset_hashes,
        "payload_sha256": payload_sha256,
        "external_mutations": [],
    }
    if not apply:
        return result

    data["status"] = "approved"
    data["requires_manual_approval"] = False
    for asset in data["media"]["assets"]:
        asset["reviewed"] = True
    publishing["allowed"] = True
    publishing["reason"] = (
        "Exact payload and selected targets explicitly approved; no platform dispatch was performed."
    )
    publishing["intended_targets"] = requested
    publishing["requested_targets"] = selected
    publishing["targets"] = {target: contracts[target] for target in selected}
    publishing["approval"] = {
        "approved_by": approver,
        "approved_at": approved_at,
        "approved_targets": selected,
        "asset_sha256": asset_hashes,
        "payload_sha256": payload_sha256,
    }
    publishing.setdefault("results", {})
    write_review_manifest(path, data)
    result.update({"approved": True, "approved_at": approved_at})
    return result


def approve_review_packet(
    manifest_path: str | Path,
    *,
    approved_by: str,
    targets: Sequence[str],
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prüfe oder dokumentiere eine Freigabe; führt niemals Plattformaktionen aus."""

    if not apply:
        return _approve_review_packet_unlocked(
            manifest_path,
            approved_by=approved_by,
            targets=targets,
            apply=False,
            now=now,
        )
    with _approval_lock(manifest_path):
        return _approve_review_packet_unlocked(
            manifest_path,
            approved_by=approved_by,
            targets=targets,
            apply=True,
            now=now,
        )


def verify_approved_review_packet(
    manifest_path: str | Path,
    *,
    target: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prüfe Hash-, Zeit- und Zielbindung eines freigegebenen Pakets read-only."""

    path, data = _load_manifest(manifest_path)
    if data.get("status") != "approved" or data.get("requires_manual_approval") is not False:
        raise ApprovalError("packet is not approved")
    publishing, requested, contracts = _validate_manifest_policy(
        path,
        data,
        approved=True,
    )
    if not isinstance(publishing, dict) or publishing.get("allowed") is not True:
        raise ApprovalError("approved packet is not enabled")
    approval = publishing.get("approval")
    if not isinstance(approval, dict):
        raise ApprovalError("publishing.approval is required")
    approver = _text(approval.get("approved_by"), "approval.approved_by")
    approved_at_text = _text(approval.get("approved_at"), "approval.approved_at")
    approved_at = _parse_utc(approved_at_text, "approval.approved_at")
    approved_targets = approval.get("approved_targets")
    if (
        not isinstance(approved_targets, list)
        or not approved_targets
        or any(
            not isinstance(approved_target, str)
            or approved_target not in TARGET_CONTRACTS
            for approved_target in approved_targets
        )
        or len(set(approved_targets)) != len(approved_targets)
    ):
        raise ApprovalError("approval.approved_targets is invalid")
    if not isinstance(target, str) or target not in approved_targets:
        raise ApprovalError(f"target is not approved: {target}")
    if requested != approved_targets:
        raise ApprovalError("executable targets differ from approved targets")
    if not isinstance(contracts, dict) or set(contracts) != set(approved_targets):
        raise ApprovalError("executable target contracts differ from approved targets")
    for approved_target in approved_targets:
        if contracts.get(approved_target) != TARGET_CONTRACTS.get(approved_target):
            raise ApprovalError(f"target contract changed: {approved_target}")

    reference = _datetime_value(now or _utc_now(), "now")
    _validate_review_window(data, reference)
    created_at = _parse_utc(_text(data.get("created_at"), "created_at"), "created_at")
    expires_at = _parse_utc(
        _text(data.get("review_expires_at"), "review_expires_at"),
        "review_expires_at",
    )
    if approved_at < created_at or approved_at >= expires_at or approved_at > reference:
        raise ApprovalError("approval.approved_at is outside the valid review window")
    asset_hashes = _validate_assets(path, data)
    expected_payload = _text(approval.get("payload_sha256"), "approval.payload_sha256")
    actual_payload = _approval_payload_sha256(
        data,
        approved_targets,
        approved_by=approver,
        approved_at=approved_at_text,
    )
    if actual_payload != expected_payload:
        raise ApprovalError("approved payload sha256 changed")
    if approval.get("asset_sha256") != asset_hashes:
        raise ApprovalError("approved asset hash set changed")
    return {
        "manifest": str(path),
        "packet_id": data.get("packet_id"),
        "verified": True,
        "target": target,
        "payload_sha256": actual_payload,
        "asset_sha256": asset_hashes,
        "external_mutations": [],
    }
