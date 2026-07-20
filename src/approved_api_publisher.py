#!/usr/bin/env python3
"""Public API publisher for explicitly approved Schatzsuche schema-3 packets.

The content generators remain in manual-preparation mode.  This module is the
only path allowed to turn a hash-bound, target-specific approval into a public
platform mutation.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pickle
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from src.review_packets import (
    ApprovalError,
    TARGET_CONTRACTS,
    verify_approved_review_packet,
    write_review_manifest,
)


PROJECT = "schatzsuche4.0"
PUBLISHER_PROTOCOL = "schatzsuche-schema3-publication/v1"
DEFAULT_GRAPH_VERSION = "v24.0"
DEFAULT_STATE_DB = Path("state/schatzsuche_publisher.sqlite3")
DEFAULT_PACKET_ROOT = Path("manual_uploads")
PUBLIC_GATE = "APPROVED_PACKET_PUBLISHING_ALLOWED"

_MEDIA_RULES: dict[tuple[str, str], str] = {
    ("social_feed", "meta_facebook"): "image",
    ("social_feed", "meta_instagram"): "image",
    ("ai_reel_bundle", "youtube"): "video",
    ("ai_reel_bundle", "meta_facebook"): "video",
    ("ai_reel_bundle", "meta_instagram"): "video",
    ("youtube_shorts", "youtube"): "video",
    ("facebook_feed", "meta_facebook"): "image_or_text",
    ("instagram_feed", "meta_instagram"): "image",
    ("instagram_reel", "meta_instagram"): "video",
}


class PublicationBlocked(RuntimeError):
    """The approved packet cannot safely be mutated."""


class ApiPublishError(RuntimeError):
    """A platform operation failed at or after a mutation boundary."""


@dataclass(frozen=True)
class PublishPlan:
    manifest_path: Path
    packet_id: str
    post_type: str
    target: str
    target_contract: dict[str, str]
    approval_payload_sha256: str
    media_path: Path | None
    media_sha256: str | None
    media_kind: str
    mime_type: str | None
    visibility: str
    title: str
    description: str
    caption: str
    comment: str
    tags: tuple[str, ...]
    fingerprint: str


class PlatformAdapter(Protocol):
    def preflight(self, plan: PublishPlan) -> Mapping[str, Any]: ...

    def publish(self, plan: PublishPlan, spool_path: Path | None) -> Mapping[str, Any]: ...


def _publication_evidence(plan: PublishPlan, message: str) -> list[str]:
    evidence = [message]
    if plan.comment:
        evidence.append("separate first comment is outside publication protocol v1 and was not posted")
    return evidence


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: str | Path) -> tuple[Path, dict[str, Any]]:
    raw = Path(path).expanduser()
    if raw.is_symlink():
        raise PublicationBlocked("manifest symlinks are not allowed")
    resolved = raw.resolve()
    if not resolved.is_file():
        raise PublicationBlocked(f"manifest not found: {resolved}")
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationBlocked("manifest is not readable JSON") from exc
    if not isinstance(data, dict):
        raise PublicationBlocked("manifest must contain an object")
    return resolved, data


def _inspect_media(path: Path) -> dict[str, Any]:
    """Inspect bytes rather than trusting an extension."""

    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = str(image.format or "").upper()
            if image_format not in {"PNG", "JPEG"}:
                raise PublicationBlocked(f"unsupported image format: {image_format or 'unknown'}")
            return {
                "kind": "image",
                "mime_type": "image/png" if image_format == "PNG" else "image/jpeg",
                "width": int(image.width),
                "height": int(image.height),
            }
    except PublicationBlocked:
        raise
    except Exception:
        pass

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        probe = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise PublicationBlocked("asset is neither a supported image nor a readable video") from exc
    streams = probe.get("streams") if isinstance(probe, dict) else None
    video_streams = [s for s in streams or [] if isinstance(s, dict) and s.get("codec_type") == "video"]
    if not video_streams:
        raise PublicationBlocked("video asset has no video stream")
    format_name = str((probe.get("format") or {}).get("format_name") or "")
    if not any(name in format_name.split(",") for name in ("mp4", "mov")):
        raise PublicationBlocked(f"unsupported video container: {format_name or 'unknown'}")
    stream = video_streams[0]
    return {
        "kind": "video",
        "mime_type": "video/mp4",
        "codec": str(stream.get("codec_name") or ""),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
    }


def build_publish_plan(
    manifest_path: str | Path,
    target: str,
    *,
    now: datetime | None = None,
    media_inspector: Callable[[Path], Mapping[str, Any]] = _inspect_media,
) -> PublishPlan:
    """Build a target-specific read-only plan from an approved schema-3 packet."""

    try:
        verification = verify_approved_review_packet(manifest_path, target=target, now=now)
    except ApprovalError as exc:
        raise PublicationBlocked(str(exc)) from exc
    path, data = _load_manifest(manifest_path)
    if data.get("schema_version") != 3 or data.get("project") != PROJECT:
        raise PublicationBlocked("only Schatzsuche schema-3 packets are supported")
    post_type = str(data.get("post_type") or "")
    required_kind = _MEDIA_RULES.get((post_type, target))
    if required_kind is None:
        raise PublicationBlocked(f"unsupported publication combination: {post_type}/{target}")

    publishing = data.get("publishing")
    copy = data.get("copy")
    media = data.get("media")
    if not isinstance(publishing, dict) or not isinstance(copy, dict) or not isinstance(media, dict):
        raise PublicationBlocked("manifest publishing, copy and media objects are required")
    contract = publishing.get("targets", {}).get(target)
    if contract != TARGET_CONTRACTS.get(target):
        raise PublicationBlocked(f"target contract changed: {target}")
    approval = publishing.get("approval")
    if not isinstance(approval, dict):
        raise PublicationBlocked("approval is missing")
    approval_hash = str(approval.get("payload_sha256") or "")
    if len(approval_hash) != 64:
        raise PublicationBlocked("approval payload hash is invalid")

    assets = media.get("assets")
    if not isinstance(assets, list):
        raise PublicationBlocked("media.assets must be a list")
    primary = assets[0] if assets else None
    media_path: Path | None = None
    media_sha256: str | None = None
    media_kind = "text"
    mime_type: str | None = None
    if primary is not None:
        if not isinstance(primary, dict) or primary.get("role") != "primary" or primary.get("reviewed") is not True:
            raise PublicationBlocked("the first reviewed asset must be the primary asset")
        relative = Path(str(primary.get("path") or ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise PublicationBlocked("primary asset path is unsafe")
        media_path = (path.parent / relative).resolve()
        try:
            media_path.relative_to(path.parent)
        except ValueError as exc:
            raise PublicationBlocked("primary asset escapes packet directory") from exc
        if media_path.is_symlink() or not media_path.is_file():
            raise PublicationBlocked("primary asset is missing or unsafe")
        media_sha256 = _file_sha256(media_path)
        if media_sha256 != primary.get("sha256"):
            raise PublicationBlocked("primary asset sha256 changed")
        inspected = dict(media_inspector(media_path))
        media_kind = str(inspected.get("kind") or "")
        mime_type = str(inspected.get("mime_type") or "") or None
    elif required_kind != "image_or_text":
        raise PublicationBlocked(f"{post_type}/{target} requires media")

    if required_kind == "image_or_text":
        if media_kind not in {"image", "text"}:
            raise PublicationBlocked(f"{post_type}/{target} requires image or text")
    elif media_kind != required_kind:
        raise PublicationBlocked(f"{post_type}/{target} requires {required_kind} media")

    title = str(copy.get("youtube_title") or "").strip() if target == "youtube" else ""
    description = str(copy.get("youtube_description") or "").strip() if target == "youtube" else ""
    caption = str(copy.get("meta_caption") or "").strip() if target.startswith("meta_") else ""
    comment = str(copy.get("comment") or "").strip()
    raw_tags = copy.get("tags")
    tags = tuple(str(tag).strip() for tag in raw_tags or [] if str(tag).strip()) if isinstance(raw_tags, list) else ()
    if target == "youtube":
        if not title or len(title) > 100:
            raise PublicationBlocked("YouTube title must contain 1-100 characters")
        if len(description) > 5000:
            raise PublicationBlocked("YouTube description exceeds 5000 characters")
        if sum(len(tag) for tag in tags) > 450:
            raise PublicationBlocked("YouTube tags exceed the safe aggregate limit")
    else:
        if not caption or len(caption) > 2200:
            raise PublicationBlocked("Meta caption must contain 1-2200 characters")

    payload = {
        "protocol": PUBLISHER_PROTOCOL,
        "schema_version": 3,
        "project": PROJECT,
        "packet_id": data.get("packet_id"),
        "post_type": post_type,
        "target": target,
        "target_contract": contract,
        "approval_payload_sha256": approval_hash,
        "media": {
            "sha256": media_sha256,
            "kind": media_kind,
            "mime_type": mime_type,
        },
        "request": {
            "visibility": "public",
            "title": title,
            "description": description,
            "caption": caption,
            "comment": comment,
            "comment_policy": "not_published",
            "tags": list(tags),
        },
    }
    return PublishPlan(
        manifest_path=path,
        packet_id=str(data.get("packet_id")),
        post_type=post_type,
        target=target,
        target_contract=dict(contract),
        approval_payload_sha256=approval_hash,
        media_path=media_path,
        media_sha256=media_sha256,
        media_kind=media_kind,
        mime_type=mime_type,
        visibility="public",
        title=title,
        description=description,
        caption=caption,
        comment=comment,
        tags=tags,
        fingerprint=_canonical_sha256(payload),
    )


class PublisherJournal:
    """Crash-conservative SQLite journal outside editable packet manifests."""

    def __init__(self, path: str | Path = DEFAULT_STATE_DB):
        self.path = Path(path).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                packet_id TEXT NOT NULL,
                target TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                approval_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                external_id TEXT,
                external_url TEXT,
                result_json TEXT,
                error_class TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (packet_id, target)
            )
            """
        )
        connection.commit()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return connection

    def get(self, plan: PublishPlan) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE packet_id=? AND target=?",
                (plan.packet_id, plan.target),
            ).fetchone()
        return dict(row) if row else None

    def prepare(self, plan: PublishPlan) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM operations WHERE packet_id=? AND target=?",
                (plan.packet_id, plan.target),
            ).fetchone()
            if row:
                current = dict(row)
                if current["fingerprint"] != plan.fingerprint:
                    raise PublicationBlocked("journal fingerprint conflict for packet target")
                connection.commit()
                return current
            connection.execute(
                """INSERT INTO operations
                (packet_id,target,fingerprint,approval_hash,state,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    plan.packet_id,
                    plan.target,
                    plan.fingerprint,
                    plan.approval_payload_sha256,
                    "prepared",
                    now,
                    now,
                ),
            )
            connection.commit()
        return self.get(plan) or {}

    def _transition(self, plan: PublishPlan, state: str, **fields: Any) -> None:
        assignments = ["state=?", "updated_at=?"]
        values: list[Any] = [state, datetime.now(timezone.utc).isoformat()]
        for name in ("external_id", "external_url", "result_json", "error_class"):
            if name in fields:
                assignments.append(f"{name}=?")
                values.append(fields[name])
        values.extend([plan.packet_id, plan.target, plan.fingerprint])
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                f"UPDATE operations SET {', '.join(assignments)} WHERE packet_id=? AND target=? AND fingerprint=?",
                values,
            )
            if cursor.rowcount != 1:
                raise PublicationBlocked("journal operation is missing or changed")
            connection.commit()

    def mark_started(self, plan: PublishPlan) -> None:
        row = self.get(plan)
        if not row or row["state"] != "prepared":
            raise PublicationBlocked("only a prepared operation may start")
        self._transition(plan, "mutation_started")

    def mark_unknown(self, plan: PublishPlan, error: BaseException | str) -> None:
        self._transition(plan, "unknown", error_class=type(error).__name__ if isinstance(error, BaseException) else str(error))

    def mark_completed(self, plan: PublishPlan, result: Mapping[str, Any]) -> None:
        encoded = json.dumps(dict(result), ensure_ascii=False, sort_keys=True)
        self._transition(
            plan,
            "completed",
            external_id=result.get("external_id"),
            external_url=result.get("external_url"),
            result_json=encoded,
            error_class=None,
        )


@contextmanager
def _operation_lock(state_dir: Path, plan: PublishPlan) -> Iterator[None]:
    lock_dir = state_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = lock_dir / f"{plan.packet_id}.{plan.target}.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _make_spool(plan: PublishPlan, state_dir: Path) -> Path | None:
    if plan.media_path is None:
        return None
    spool_dir = state_dir / "spool"
    spool_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    suffix = plan.media_path.suffix.lower()
    descriptor, name = tempfile.mkstemp(prefix=f"{plan.fingerprint}.", suffix=suffix, dir=spool_dir)
    destination = Path(name)
    digest = hashlib.sha256()
    source_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        source_flags |= os.O_NOFOLLOW
    source_fd = os.open(plan.media_path, source_flags)
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode) or source_stat.st_size < 1:
            raise PublicationBlocked("approved media is no longer a regular non-empty file")
        with os.fdopen(source_fd, "rb", closefd=False) as source, os.fdopen(descriptor, "wb") as target:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(destination, 0o600)
    finally:
        os.close(source_fd)
    if digest.hexdigest() != plan.media_sha256:
        destination.unlink(missing_ok=True)
        raise PublicationBlocked("media changed while creating immutable publisher spool")
    return destination


def _record_manifest_result(plan: PublishPlan, result: Mapping[str, Any]) -> None:
    lock_path = plan.manifest_path.parent / ".publisher-result.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        path, data = _load_manifest(plan.manifest_path)
        publishing = data.get("publishing")
        approval = publishing.get("approval") if isinstance(publishing, dict) else None
        if not isinstance(approval, dict) or approval.get("payload_sha256") != plan.approval_payload_sha256:
            raise PublicationBlocked("manifest approval changed before result persistence")
        assert isinstance(publishing, dict)
        results = publishing.setdefault("results", {})
        if not isinstance(results, dict):
            raise PublicationBlocked("publishing.results must be an object")
        existing = results.get(plan.target)
        record = {
            "status": "public",
            "visibility": "public",
            "fingerprint": plan.fingerprint,
            "approval_payload_sha256": plan.approval_payload_sha256,
            "media_sha256": plan.media_sha256,
            "external_id": result.get("external_id"),
            "external_url": result.get("external_url"),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "evidence": [str(item) for item in result.get("evidence", [])],
        }
        if existing is not None:
            if not isinstance(existing, dict) or existing.get("fingerprint") != plan.fingerprint:
                raise PublicationBlocked("conflicting platform result already exists")
            if (
                existing.get("status") != "public"
                or existing.get("external_id") != result.get("external_id")
                or existing.get("external_url") != result.get("external_url")
            ):
                raise PublicationBlocked("manifest and journal platform results disagree")
            return
        results[plan.target] = record
        write_review_manifest(path, data)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def execute_plan(
    plan: PublishPlan,
    *,
    journal: PublisherJournal,
    adapter: PlatformAdapter,
    state_dir: str | Path,
) -> dict[str, Any]:
    """Execute once; ambiguous failures become terminal ``unknown`` records."""

    if not _gate_enabled():
        raise PublicationBlocked(f"public mutation requires {PUBLIC_GATE}=true")
    state_root = Path(state_dir).expanduser().resolve()
    with _operation_lock(state_root, plan):
        existing = journal.get(plan)
        if existing and existing["fingerprint"] != plan.fingerprint:
            raise PublicationBlocked("journal fingerprint conflict")
        if existing and existing["state"] == "completed":
            result = json.loads(existing["result_json"] or "{}")
            _record_manifest_result(plan, result)
            return result
        if existing and existing["state"] == "mutation_started":
            journal.mark_unknown(plan, "recovered_mutation_started")
            raise PublicationBlocked("publication state is unknown; automatic retry is forbidden")
        if existing and existing["state"] == "unknown":
            raise PublicationBlocked("publication state is unknown; automatic retry is forbidden")
        if not existing:
            _, manifest = _load_manifest(plan.manifest_path)
            publishing = manifest.get("publishing")
            manifest_results = publishing.get("results") if isinstance(publishing, dict) else None
            prior_result = manifest_results.get(plan.target) if isinstance(manifest_results, dict) else None
            if prior_result is not None:
                raise PublicationBlocked(
                    "manifest already records this target but the journal is missing; reconciliation is required"
                )
            journal.prepare(plan)

        adapter.preflight(plan)
        spool_path = _make_spool(plan, state_root)
        try:
            try:
                refreshed = verify_approved_review_packet(
                    plan.manifest_path,
                    target=plan.target,
                    now=datetime.now(timezone.utc),
                )
            except ApprovalError as exc:
                raise PublicationBlocked(str(exc)) from exc
            if refreshed.get("payload_sha256") != plan.approval_payload_sha256:
                raise PublicationBlocked("approved plan changed before the mutation boundary")
            journal.mark_started(plan)
            try:
                result = dict(adapter.publish(plan, spool_path))
                if result.get("status") != "public" or not result.get("external_id"):
                    raise ApiPublishError("platform did not return a persistently verified public object")
                journal.mark_completed(plan, result)
            except Exception as exc:
                journal.mark_unknown(plan, exc)
                raise
            _record_manifest_result(plan, result)
            return result
        finally:
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)


class OfficialApiAdapter:
    """Official Meta Graph and YouTube Data API implementation."""

    def __init__(self, project_root: str | Path = "."):
        self.project_root = Path(project_root).expanduser().resolve()
        load_dotenv(self.project_root / ".env", override=False)
        self.graph_version = os.getenv("META_GRAPH_VERSION", DEFAULT_GRAPH_VERSION)
        self.graph_base = f"https://graph.facebook.com/{self.graph_version}"
        self.session = requests.Session()
        self.timeout = (10, 45)

    def _meta_token(self) -> str:
        token = os.getenv("PAGE_TOKEN") or os.getenv("META_PAGE_ACCESS_TOKEN")
        if not token:
            raise PublicationBlocked("Meta page token is missing")
        return token

    def _meta(
        self,
        method: str,
        path_or_url: str,
        *,
        data: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        bearer: bool = True,
        timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        url = path_or_url if path_or_url.startswith("https://") else f"{self.graph_base}/{path_or_url.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self._meta_token()}"} if bearer else {}
        response = self.session.request(
            method,
            url,
            headers=headers,
            data=data,
            files=files,
            params=params,
            timeout=timeout or self.timeout,
            allow_redirects=False,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiPublishError(f"Meta {method} returned non-JSON HTTP {response.status_code}") from exc
        if not response.ok or not isinstance(payload, dict) or payload.get("error"):
            code = (payload.get("error") or {}).get("code") if isinstance(payload, dict) else None
            raise ApiPublishError(f"Meta {method} failed with HTTP {response.status_code}, code {code}")
        return payload

    def _youtube_service(self):
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        token_path = self.project_root / "token_finance.pickle"
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(token_path, flags)
        except OSError as exc:
            raise PublicationBlocked("YouTube OAuth token file is missing or unsafe") from exc
        try:
            token_stat = os.fstat(descriptor)
            if not stat.S_ISREG(token_stat.st_mode) or token_stat.st_uid != os.getuid():
                raise PublicationBlocked("YouTube OAuth token file owner or type is unsafe")
            if token_stat.st_mode & 0o077:
                raise PublicationBlocked("YouTube OAuth token file must use mode 0600")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                credentials = pickle.load(handle)
        finally:
            os.close(descriptor)
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                raise PublicationBlocked("YouTube OAuth token is invalid and cannot refresh headlessly")
        return build("youtube", "v3", credentials=credentials, cache_discovery=False)

    def preflight(self, plan: PublishPlan) -> Mapping[str, Any]:
        if plan.target == "youtube":
            service = self._youtube_service()
            items = service.channels().list(part="id", mine=True).execute(num_retries=0).get("items", [])
            channel_id = plan.target_contract["channel_id"]
            if len(items) != 1 or items[0].get("id") != channel_id:
                raise PublicationBlocked("YouTube OAuth identity does not match approved channel")
            return {"verified": True, "channel_id": channel_id}

        page_id = TARGET_CONTRACTS["meta_facebook"]["asset_id"]
        page = self._meta(
            "GET",
            page_id,
            params={"fields": "id,name,instagram_business_account{id}"},
        )
        if page.get("id") != page_id:
            raise PublicationBlocked("Meta page identity mismatch")
        if plan.target == "meta_facebook":
            me = self._meta("GET", "me", params={"fields": "id"})
            if me.get("id") != page_id or plan.target_contract.get("asset_id") != page_id:
                raise PublicationBlocked("Meta token is not the approved Facebook page token")
            return {"verified": True, "page_id": page_id}
        instagram_id = plan.target_contract.get("asset_id")
        linked = page.get("instagram_business_account") or {}
        if linked.get("id") != instagram_id:
            raise PublicationBlocked("approved Instagram account is not linked to the Meta page")
        instagram = self._meta("GET", str(instagram_id), params={"fields": "id,username"})
        if instagram.get("id") != instagram_id:
            raise PublicationBlocked("Instagram identity mismatch")
        return {"verified": True, "instagram_id": instagram_id}

    def publish(self, plan: PublishPlan, spool_path: Path | None) -> Mapping[str, Any]:
        if plan.target == "youtube":
            if spool_path is None:
                raise ApiPublishError("YouTube requires a video spool")
            return self._publish_youtube(plan, spool_path)
        if plan.target == "meta_facebook":
            return self._publish_facebook(plan, spool_path)
        if plan.target == "meta_instagram":
            if spool_path is None:
                raise ApiPublishError("Instagram requires a media spool")
            return self._publish_instagram(plan, spool_path)
        raise PublicationBlocked(f"unsupported target: {plan.target}")

    def _publish_youtube(self, plan: PublishPlan, spool_path: Path) -> Mapping[str, Any]:
        from googleapiclient.http import MediaFileUpload

        service = self._youtube_service()
        body = {
            "snippet": {
                "title": plan.title,
                "description": plan.description,
                "tags": list(plan.tags),
                "categoryId": "22",
                "defaultLanguage": "de",
                "defaultAudioLanguage": "de",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(str(spool_path), mimetype="video/mp4", chunksize=-1, resumable=True)
        request = service.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = request.next_chunk(num_retries=0)
        video_id = str((response or {}).get("id") or "")
        if not video_id:
            raise ApiPublishError("YouTube upload returned no video ID")
        items = service.videos().list(part="snippet,status", id=video_id).execute(num_retries=0).get("items", [])
        if len(items) != 1:
            raise ApiPublishError("YouTube video could not be verified by ID")
        item = items[0]
        snippet = item.get("snippet") or {}
        status = item.get("status") or {}
        if (
            snippet.get("channelId") != plan.target_contract["channel_id"]
            or snippet.get("title") != plan.title
            or snippet.get("description") != plan.description
            or status.get("privacyStatus") != "public"
        ):
            raise ApiPublishError("YouTube persisted state differs from the approved public plan")
        return {
            "status": "public",
            "external_id": video_id,
            "external_url": f"https://www.youtube.com/shorts/{video_id}",
            "evidence": _publication_evidence(
                plan, "channel, copy and public visibility verified by videos.list"
            ),
        }

    def _publish_facebook(self, plan: PublishPlan, spool_path: Path | None) -> Mapping[str, Any]:
        page_id = plan.target_contract["asset_id"]
        if plan.media_kind == "text":
            created = self._meta("POST", f"{page_id}/feed", data={"message": plan.caption})
            external_id = str(created.get("id") or "")
            fields = "id,permalink_url,from,message"
            copy_field = "message"
        elif plan.media_kind == "image":
            if spool_path is None:
                raise ApiPublishError("Facebook image spool is missing")
            with spool_path.open("rb") as handle:
                created = self._meta(
                    "POST",
                    f"{page_id}/photos",
                    data={"caption": plan.caption, "published": "true"},
                    files={"source": (spool_path.name, handle, plan.mime_type or "application/octet-stream")},
                    timeout=(10, 120),
                )
            post_id = str(created.get("post_id") or "")
            external_id = post_id or str(created.get("id") or "")
            fields = "id,permalink_url,from,message" if post_id else "id,link,from,name"
            copy_field = "message" if post_id else "name"
        else:
            if spool_path is None:
                raise ApiPublishError("Facebook video spool is missing")
            started = self._meta("POST", f"{page_id}/video_reels", data={"upload_phase": "start"})
            video_id = str(started.get("video_id") or "")
            upload_url = str(started.get("upload_url") or "")
            parsed_upload_url = urlparse(upload_url)
            if (
                not video_id
                or parsed_upload_url.scheme != "https"
                or parsed_upload_url.hostname != "rupload.facebook.com"
            ):
                raise ApiPublishError("Facebook Reel start returned no stable upload contract")
            headers = {
                "Authorization": f"OAuth {self._meta_token()}",
                "offset": "0",
                "file_size": str(spool_path.stat().st_size),
                "Content-Type": "application/octet-stream",
            }
            with spool_path.open("rb") as handle:
                response = self.session.post(
                    upload_url,
                    headers=headers,
                    data=handle,
                    timeout=(10, 180),
                    allow_redirects=False,
                )
            try:
                uploaded = response.json()
            except ValueError as exc:
                raise ApiPublishError("Facebook Reel upload returned non-JSON") from exc
            if not response.ok or not uploaded.get("success"):
                raise ApiPublishError(f"Facebook Reel upload failed with HTTP {response.status_code}")
            finished = self._meta(
                "POST",
                f"{page_id}/video_reels",
                data={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "description": plan.caption,
                    "video_state": "PUBLISHED",
                },
            )
            if finished.get("success") is not True:
                raise ApiPublishError("Facebook Reel did not confirm publication")
            external_id = video_id
            fields = "id,permalink_url,from,description"
            copy_field = "description"
        if not external_id:
            raise ApiPublishError("Facebook publication returned no external ID")
        deadline = time.monotonic() + (90 if plan.media_kind == "video" else 1)
        while True:
            verified = self._meta("GET", external_id, params={"fields": fields})
            external_url = verified.get("permalink_url") or verified.get("link")
            if external_url or time.monotonic() >= deadline:
                break
            time.sleep(5)
        owner = verified.get("from") or {}
        if owner.get("id") != page_id:
            raise ApiPublishError("Facebook result owner does not match approved page")
        if verified.get(copy_field) != plan.caption:
            raise ApiPublishError("Facebook persisted copy differs from the approved caption")
        if not external_url:
            raise ApiPublishError("Facebook public permalink could not be verified")
        return {
            "status": "public",
            "external_id": external_id,
            "external_url": external_url,
            "evidence": _publication_evidence(
                plan, "Facebook owner, copy and public permalink verified by Graph GET"
            ),
        }

    def _stage_instagram_asset(self, plan: PublishPlan, spool_path: Path) -> tuple[Path, str]:
        public_dir = self.project_root / "static" / "temp_social"
        public_dir.mkdir(parents=True, exist_ok=True)
        extension = ".mp4" if plan.media_kind == "video" else (".jpg" if plan.mime_type == "image/jpeg" else ".png")
        staged = public_dir / f"approved-{plan.media_sha256}{extension}"
        if staged.exists() and (staged.is_symlink() or _file_sha256(staged) != plan.media_sha256):
            raise PublicationBlocked("conflicting Instagram staging asset exists")
        if not staged.exists():
            temporary_fd, temporary_name = tempfile.mkstemp(prefix=".approved-", suffix=extension, dir=public_dir)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(temporary_fd, "wb") as target, spool_path.open("rb") as source:
                    shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
                os.chmod(temporary, 0o644)
                os.replace(temporary, staged)
            finally:
                temporary.unlink(missing_ok=True)
        url = f"https://tool.schatzsuche40.de/static/temp_social/{staged.name}"
        head = self.session.head(url, timeout=(10, 30), allow_redirects=False)
        if head.status_code != 200:
            staged.unlink(missing_ok=True)
            raise ApiPublishError(f"Instagram staging URL returned HTTP {head.status_code}")
        length = head.headers.get("content-length")
        if length and int(length) != staged.stat().st_size:
            staged.unlink(missing_ok=True)
            raise ApiPublishError("Instagram staging URL length mismatch")
        return staged, url

    def _publish_instagram(self, plan: PublishPlan, spool_path: Path) -> Mapping[str, Any]:
        account_id = plan.target_contract["asset_id"]
        staged, public_url = self._stage_instagram_asset(plan, spool_path)
        try:
            data: dict[str, Any] = {"caption": plan.caption}
            if plan.media_kind == "video":
                data.update({"media_type": "REELS", "video_url": public_url, "share_to_feed": "true"})
            else:
                data["image_url"] = public_url
            container = self._meta("POST", f"{account_id}/media", data=data)
            container_id = str(container.get("id") or "")
            if not container_id:
                raise ApiPublishError("Instagram container returned no ID")
            deadline = time.monotonic() + 120
            while True:
                status = self._meta("GET", container_id, params={"fields": "status_code,status"})
                status_code = str(status.get("status_code") or "")
                if status_code == "FINISHED":
                    break
                if status_code in {"ERROR", "EXPIRED"}:
                    raise ApiPublishError(f"Instagram container entered {status_code}")
                if time.monotonic() >= deadline:
                    raise ApiPublishError("Instagram container processing timed out")
                time.sleep(5)
            published = self._meta("POST", f"{account_id}/media_publish", data={"creation_id": container_id})
            media_id = str(published.get("id") or "")
            if not media_id:
                raise ApiPublishError("Instagram media_publish returned no media ID")
            verified = self._meta(
                "GET",
                media_id,
                params={"fields": "id,owner,media_type,permalink,caption"},
            )
            owner = verified.get("owner") or {}
            expected_media_type = "VIDEO" if plan.media_kind == "video" else "IMAGE"
            if (
                owner.get("id") != account_id
                or not verified.get("permalink")
                or verified.get("caption") != plan.caption
                or verified.get("media_type") != expected_media_type
            ):
                raise ApiPublishError("Instagram persisted owner, copy, media type or permalink differs")
            return {
                "status": "public",
                "external_id": media_id,
                "external_url": verified["permalink"],
                "evidence": _publication_evidence(
                    plan,
                    "Instagram owner, copy, media type and public permalink verified by Graph GET",
                ),
            }
        finally:
            staged.unlink(missing_ok=True)


def _gate_enabled() -> bool:
    return os.getenv(PUBLIC_GATE, "").strip().lower() == "true"


def cleanup_stale_instagram_assets(
    project_root: str | Path,
    *,
    older_than_seconds: int = 6 * 60 * 60,
    current_timestamp: float | None = None,
) -> int:
    """Remove content-addressed staging assets left by a hard process crash."""

    public_dir = Path(project_root).expanduser().resolve() / "static" / "temp_social"
    if not public_dir.is_dir():
        return 0
    cutoff = (current_timestamp if current_timestamp is not None else time.time()) - older_than_seconds
    removed = 0
    for candidate in public_dir.glob("approved-*"):
        try:
            candidate_stat = candidate.lstat()
            if stat.S_ISREG(candidate_stat.st_mode) and candidate_stat.st_mtime < cutoff:
                candidate.unlink()
                removed += 1
        except FileNotFoundError:
            continue
    return removed


def scan_approved_packets(
    root: str | Path,
    *,
    journal: PublisherJournal,
    adapter: PlatformAdapter,
    state_dir: str | Path,
    execute: bool,
    limit: int = 3,
    now: datetime | None = None,
    media_inspector: Callable[[Path], Mapping[str, Any]] = _inspect_media,
) -> list[dict[str, Any]]:
    packet_root = Path(root).expanduser().resolve()
    if not packet_root.is_dir():
        return []
    current = now or datetime.now(timezone.utc)
    events: list[dict[str, Any]] = []
    attempted = 0
    manifests = sorted(
        packet_root.rglob("review_manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for manifest_path in manifests:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 3 or data.get("status") != "approved":
            continue
        expires_raw = data.get("review_expires_at")
        try:
            expires_at = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if expires_at <= current:
            continue
        publishing = data.get("publishing")
        targets = publishing.get("requested_targets") if isinstance(publishing, dict) else None
        manifest_results = publishing.get("results") if isinstance(publishing, dict) else None
        if not isinstance(targets, list):
            continue
        for target in targets:
            target_name = str(target)
            persisted = manifest_results.get(target_name) if isinstance(manifest_results, dict) else None
            if isinstance(persisted, dict) and persisted.get("status") == "public":
                continue
            try:
                plan = build_publish_plan(
                    manifest_path,
                    target_name,
                    now=current,
                    media_inspector=media_inspector,
                )
                before = journal.get(plan)
                if before and before.get("state") in {"unknown", "mutation_started"}:
                    continue
                if before and before.get("state") == "completed":
                    if execute:
                        execute_plan(plan, journal=journal, adapter=adapter, state_dir=state_dir)
                    continue
                if attempted >= limit:
                    return events
                attempted += 1
                if not execute:
                    events.append({"packet_id": plan.packet_id, "target": plan.target, "fingerprint": plan.fingerprint})
                else:
                    result = execute_plan(plan, journal=journal, adapter=adapter, state_dir=state_dir)
                    events.append({"packet_id": plan.packet_id, "target": plan.target, **result})
            except Exception as exc:
                events.append(
                    {
                        "packet_id": data.get("packet_id"),
                        "target": target_name,
                        "status": "blocked",
                        "error_class": type(exc).__name__,
                        "message": str(exc),
                    }
                )
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify-manifest", "scan", "publish-one"))
    parser.add_argument("--manifest")
    parser.add_argument("--target", choices=sorted(TARGET_CONTRACTS))
    parser.add_argument("--packet-root", default=str(DEFAULT_PACKET_ROOT))
    parser.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    load_dotenv(project_root / ".env", override=False)
    state_db = Path(args.state_db).expanduser().resolve()
    journal = PublisherJournal(state_db)
    adapter = OfficialApiAdapter(project_root)
    if args.execute:
        cleanup_stale_instagram_assets(project_root)
    if args.action == "verify-manifest":
        if not args.manifest or not args.target:
            parser.error("--manifest and --target are required")
        plan = build_publish_plan(args.manifest, args.target)
        print(json.dumps({
            "packet_id": plan.packet_id,
            "target": plan.target,
            "visibility": plan.visibility,
            "media_kind": plan.media_kind,
            "fingerprint": plan.fingerprint,
        }, ensure_ascii=False, indent=2))
        return 0
    if args.execute and not _gate_enabled():
        raise SystemExit(f"Refusing public mutation: {PUBLIC_GATE}=true is required")
    if args.action == "publish-one":
        if not args.manifest or not args.target:
            parser.error("--manifest and --target are required")
        plan = build_publish_plan(args.manifest, args.target)
        if not args.execute:
            print(json.dumps({"packet_id": plan.packet_id, "target": plan.target, "fingerprint": plan.fingerprint}, indent=2))
            return 0
        result = execute_plan(plan, journal=journal, adapter=adapter, state_dir=state_db.parent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    events = scan_approved_packets(
        args.packet_root,
        journal=journal,
        adapter=adapter,
        state_dir=state_db.parent,
        execute=args.execute,
    )
    if events:
        print(json.dumps(events, ensure_ascii=False, indent=2))
    return 2 if args.execute and any(event.get("status") == "blocked" for event in events) else 0


if __name__ == "__main__":
    raise SystemExit(main())
