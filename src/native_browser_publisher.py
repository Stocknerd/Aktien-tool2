#!/usr/bin/env python3
"""Native, fail-closed publisher for reviewed Schatzsuche Canva packets.

Only two mutation modes are intentionally supported:
- YouTube Shorts saved as ``private``
- Facebook Reels saved as a Meta Business Suite ``draft``

Public posting, scheduling and Instagram publishing are deliberately absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse


PROJECT = "schatzsuche4.0"
YOUTUBE_CHANNEL_NAME = "Schatzsuche 4.0"
YOUTUBE_CHANNEL_ID = "UCDj-MBezZKZIGMiK8t21oVA"
META_FACEBOOK_PAGE_NAME = "Schatzsuche4.0"
META_FACEBOOK_ASSET_ID = "112395201353218"
META_BUSINESS_ID = "625626605438788"

TARGET_CONTRACTS: dict[str, dict[str, str]] = {
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
COMPLETED_STATUS = {"youtube": "private", "meta_facebook": "draft"}


class ManifestValidationError(ValueError):
    """The packet is not approved or does not match the target contract."""


class DuplicatePublication(RuntimeError):
    """The same reviewed packet has already completed this platform action."""


@dataclass(frozen=True)
class ActionPlan:
    manifest_path: Path
    target: str
    mode: str
    visible_name: str
    stable_id: str
    business_id: str | None
    media_path: Path
    media_sha256: str
    fingerprint: str
    title: str = ""
    description: str = ""
    caption: str = ""


def _load_manifest(path: str | Path) -> tuple[Path, dict[str, Any]]:
    manifest_path = Path(path).expanduser().resolve()
    if not manifest_path.is_file():
        raise ManifestValidationError(f"manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest must contain an object")
    return manifest_path, data


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} is required")
    return value.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(data: dict[str, Any], target: str, media_sha256: str) -> str:
    raw_copy = data.get("copy")
    copy: dict[str, Any] = raw_copy if isinstance(raw_copy, dict) else {}
    target_copy = (
        {
            "youtube_title": copy.get("youtube_title"),
            "youtube_description": copy.get("youtube_description"),
        }
        if target == "youtube"
        else {"meta_caption": copy.get("meta_caption")}
    )
    target_data = data["publishing"]["targets"][target]
    payload = {
        "packet_id": data.get("packet_id"),
        "project": data.get("project"),
        "target": target,
        "target_contract": target_data,
        "requested_targets": data["publishing"].get("requested_targets"),
        "media_sha256": media_sha256,
        "copy": target_copy,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_action_plan(
    manifest_path: str | Path,
    target: str,
    *,
    check_duplicate: bool,
) -> ActionPlan:
    path, data = _load_manifest(manifest_path)
    if target not in TARGET_CONTRACTS:
        raise ManifestValidationError(f"unsupported safe target: {target}")
    if data.get("schema_version") != 2:
        raise ManifestValidationError("schema_version must be 2")
    if data.get("project") != PROJECT:
        raise ManifestValidationError(f"project must be {PROJECT}")
    _text(data.get("packet_id"), "packet_id")
    if data.get("status") != "approved":
        raise ManifestValidationError("status must be approved")
    if data.get("requires_manual_approval") is not False:
        raise ManifestValidationError("requires_manual_approval must be false")

    publishing = data.get("publishing")
    if not isinstance(publishing, dict) or publishing.get("allowed") is not True:
        raise ManifestValidationError("publishing.allowed must be true")
    approval = publishing.get("approval")
    if not isinstance(approval, dict):
        raise ManifestValidationError("publishing.approval is required")
    _text(approval.get("approved_by"), "publishing.approval.approved_by")
    _text(approval.get("approved_at"), "publishing.approval.approved_at")

    requested_targets = publishing.get("requested_targets")
    if (
        not isinstance(requested_targets, list)
        or not requested_targets
        or any(item not in TARGET_CONTRACTS for item in requested_targets)
        or len(set(requested_targets)) != len(requested_targets)
    ):
        raise ManifestValidationError("publishing.requested_targets is invalid")
    if target not in requested_targets:
        raise ManifestValidationError(f"{target} was not included in requested_targets")

    targets = publishing.get("targets")
    target_data = targets.get(target) if isinstance(targets, dict) else None
    if target_data != TARGET_CONTRACTS[target]:
        raise ManifestValidationError(f"{target} target contract does not match the Schatzsuche contract")
    assert isinstance(target_data, dict)

    media = data.get("media")
    if not isinstance(media, dict):
        raise ManifestValidationError("media is required")
    if media.get("reviewed") is not True:
        raise ManifestValidationError("media.reviewed must be true")
    _text(media.get("audio_strategy"), "media.audio_strategy")
    relative_media = Path(_text(media.get("path"), "media.path"))
    if relative_media.is_absolute() or ".." in relative_media.parts:
        raise ManifestValidationError("media.path must stay inside the packet directory")
    media_path = (path.parent / relative_media).resolve()
    try:
        media_path.relative_to(path.parent)
    except ValueError as exc:
        raise ManifestValidationError("media.path escapes the packet directory") from exc
    if not media_path.is_file():
        raise ManifestValidationError(f"reviewed media not found: {media_path}")
    expected_sha = _text(media.get("sha256"), "media.sha256").lower()
    actual_sha = _sha256(media_path)
    if actual_sha != expected_sha:
        raise ManifestValidationError("media sha256 no longer matches the reviewed export")

    copy = data.get("copy")
    if not isinstance(copy, dict):
        raise ManifestValidationError("copy is required")
    title = description = caption = ""
    if target == "youtube":
        title = _text(copy.get("youtube_title"), "copy.youtube_title")
        description = _text(copy.get("youtube_description"), "copy.youtube_description")
        visible_name = target_data["channel_name"]
        stable_id = target_data["channel_id"]
        business_id = None
    else:
        caption = _text(copy.get("meta_caption"), "copy.meta_caption")
        visible_name = target_data["page_name"]
        stable_id = target_data["asset_id"]
        business_id = target_data["business_id"]

    fingerprint = _fingerprint(data, target, actual_sha)
    results = publishing.get("results")
    previous = results.get(target) if isinstance(results, dict) else None
    if (
        check_duplicate
        and isinstance(previous, dict)
        and previous.get("fingerprint") == fingerprint
        and previous.get("status") == COMPLETED_STATUS[target]
    ):
        raise DuplicatePublication(
            f"{target} already completed for packet fingerprint {fingerprint[:12]}"
        )

    return ActionPlan(
        manifest_path=path,
        target=target,
        mode=target_data["mode"],
        visible_name=visible_name,
        stable_id=stable_id,
        business_id=business_id,
        media_path=media_path,
        media_sha256=actual_sha,
        fingerprint=fingerprint,
        title=title,
        description=description,
        caption=caption,
    )


def build_action_plan(manifest_path: str | Path, target: str) -> ActionPlan:
    """Validate an approved packet and return one safe platform action."""

    return _build_action_plan(manifest_path, target, check_duplicate=True)


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record_result(
    manifest_path: str | Path,
    plan: ActionPlan,
    *,
    status: str,
    external_id: str | None,
    external_url: str | None,
    evidence: list[str],
) -> None:
    """Atomically persist a verified platform result in the packet manifest."""

    if status != COMPLETED_STATUS[plan.target]:
        raise ManifestValidationError(
            f"{plan.target} result must be {COMPLETED_STATUS[plan.target]}"
        )
    current = _build_action_plan(manifest_path, plan.target, check_duplicate=False)
    if current.fingerprint != plan.fingerprint:
        raise ManifestValidationError("manifest changed after the action plan was created")
    path, data = _load_manifest(manifest_path)
    results = data["publishing"].setdefault("results", {})
    existing = results.get(plan.target)
    if (
        isinstance(existing, dict)
        and existing.get("fingerprint") == plan.fingerprint
        and existing.get("status") == status
    ):
        raise DuplicatePublication(f"{plan.target} result already recorded")
    results[plan.target] = {
        "status": status,
        "mode": plan.mode,
        "fingerprint": plan.fingerprint,
        "media_sha256": plan.media_sha256,
        "external_id": external_id,
        "external_url": external_url,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "evidence": [str(item) for item in evidence],
    }
    _write_json_atomic(path, data)


@contextmanager
def packet_lock(manifest_path: Path) -> Iterator[None]:
    """Prevent two publisher processes from handling one packet concurrently."""

    lock_path = manifest_path.with_suffix(manifest_path.suffix + ".publisher.lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DuplicatePublication(f"publisher lock already exists: {lock_path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()}\ncreated_at={datetime.now(timezone.utc).isoformat()}\n")
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _connect(cdp_url: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required: pip install playwright") from exc
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.connect_over_cdp(cdp_url)
    except Exception:
        manager.stop()
        raise
    return manager, browser


def _visible_body(page) -> str:
    return page.locator("body").inner_text()


def _rightmost_button(page, name: str):
    candidates = page.get_by_role("button", name=name, exact=True)
    usable = []
    for index in range(candidates.count()):
        item = candidates.nth(index)
        if item.is_visible() and item.is_enabled():
            box = item.bounding_box() or {"x": -1}
            usable.append((box["x"], item))
    if not usable:
        raise RuntimeError(f"no visible enabled button found: {name}")
    return max(usable, key=lambda pair: pair[0])[1]


def _page_for(browser, url_fragment: str, fallback_url: str):
    pages = [page for context in browser.contexts for page in context.pages]
    for page in pages:
        if url_fragment in page.url:
            page.bring_to_front()
            return page
    context = browser.contexts[0]
    page = context.new_page()
    page.goto(fallback_url, wait_until="domcontentloaded", timeout=120_000)
    return page


def verify_target_sessions(cdp_url: str = "http://127.0.0.1:9223") -> dict[str, Any]:
    """Verify the currently authenticated Schatzsuche target identities."""

    manager, browser = _connect(cdp_url)
    try:
        youtube = _page_for(
            browser,
            YOUTUBE_CHANNEL_ID,
            f"https://studio.youtube.com/channel/{YOUTUBE_CHANNEL_ID}",
        )
        youtube.wait_for_timeout(1_000)
        if YOUTUBE_CHANNEL_ID not in youtube.url:
            raise RuntimeError("YouTube stable channel ID is not active")

        meta = _page_for(
            browser,
            f"asset_id={META_FACEBOOK_ASSET_ID}",
            (
                "https://business.facebook.com/latest/"
                f"?asset_id={META_FACEBOOK_ASSET_ID}&business_id={META_BUSINESS_ID}"
            ),
        )
        meta.wait_for_timeout(1_000)
        meta_text = _visible_body(meta)
        if META_FACEBOOK_PAGE_NAME not in meta_text:
            raise RuntimeError("Meta visible page name does not match the target contract")
        if f"asset_id={META_FACEBOOK_ASSET_ID}" not in meta.url:
            raise RuntimeError("Meta stable asset ID is not active")
        return {
            "youtube": {
                "channel_name": YOUTUBE_CHANNEL_NAME,
                "channel_id": YOUTUBE_CHANNEL_ID,
                "url": youtube.url,
                "verified": True,
            },
            "meta_facebook": {
                "page_name": META_FACEBOOK_PAGE_NAME,
                "asset_id": META_FACEBOOK_ASSET_ID,
                "business_id": META_BUSINESS_ID,
                "url": meta.url,
                "verified": True,
            },
        }
    finally:
        manager.stop()


def publish_youtube_private(plan: ActionPlan, cdp_url: str) -> dict[str, Any]:
    """Upload one approved video and persistently verify YouTube privacy."""

    if plan.target != "youtube" or plan.mode != "private":
        raise ManifestValidationError("YouTube browser action is private-only")
    manager, browser = _connect(cdp_url)
    try:
        page = _page_for(
            browser,
            YOUTUBE_CHANNEL_ID,
            f"https://studio.youtube.com/channel/{YOUTUBE_CHANNEL_ID}",
        )
        if YOUTUBE_CHANNEL_ID not in page.url:
            raise RuntimeError("wrong YouTube channel before upload")

        content = browser.contexts[0].new_page()
        content.goto(
            f"https://studio.youtube.com/channel/{YOUTUBE_CHANNEL_ID}/videos/short",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        content.wait_for_timeout(2_000)
        if plan.title in _visible_body(content):
            raise DuplicatePublication(f"YouTube already contains title: {plan.title}")
        content.close()

        upload = page.get_by_role("button", name="Videos hochladen")
        upload.click(force=True)
        page.wait_for_timeout(600)
        file_input = page.locator("input[type=file]")
        if not file_input.count():
            raise RuntimeError("YouTube upload input did not appear")
        file_input.set_input_files(str(plan.media_path))
        page.wait_for_timeout(3_000)

        page.get_by_role(
            "textbox",
            name=re.compile(r"Gib einen Titel ein|title", re.I),
        ).fill(plan.title)
        page.get_by_role(
            "textbox",
            name=re.compile(r"Erzähle Nutzern|description", re.I),
        ).fill(plan.description)
        not_kids = page.get_by_role("radio", name=re.compile(r"nicht speziell für Kinder", re.I))
        if not not_kids.is_checked():
            not_kids.check()
        altered_no = page.get_by_role("radio", name=re.compile(r"keine KI verwendet", re.I))
        if altered_no.count() and not altered_no.is_checked():
            altered_no.check()
        notify = page.get_by_role(
            "checkbox", name=re.compile(r"Abofeed.*benachrichtigen", re.I)
        )
        if notify.count() and notify.is_checked():
            notify.click(force=True)

        for _ in range(3):
            _rightmost_button(page, "Weiter").click()
            page.wait_for_timeout(900)
        private = page.get_by_role("radio", name="Privat", exact=True)
        private.check()
        if not private.is_checked():
            raise RuntimeError("YouTube private selector did not persist before save")
        dialog_text = page.get_by_role("dialog").inner_text()
        match = re.search(r"youtube\.com/shorts/([A-Za-z0-9_-]+)", dialog_text)
        _rightmost_button(page, "Speichern").click()
        page.wait_for_timeout(2_500)
        if not match:
            raise RuntimeError("YouTube video ID not found after upload")
        video_id = match.group(1)

        edit = browser.contexts[0].new_page()
        edit_url = f"https://studio.youtube.com/video/{video_id}/edit"
        edit.goto(edit_url, wait_until="domcontentloaded", timeout=120_000)
        edit.wait_for_timeout(2_500)
        body = _visible_body(edit)
        if plan.title not in body or plan.description not in body:
            raise RuntimeError("YouTube title or description did not persist")
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        private_persisted = any(
            line == "Privat" and "Sichtbarkeit" in lines[max(0, index - 3) : index + 1]
            for index, line in enumerate(lines)
        )
        if not private_persisted:
            raise RuntimeError("YouTube visibility is not persistently private")
        return {
            "status": "private",
            "external_id": video_id,
            "external_url": edit_url,
            "evidence": [
                "target channel ID matched",
                "title and description persisted",
                "visibility persisted as private",
            ],
        }
    finally:
        manager.stop()


def publish_meta_facebook_draft(plan: ActionPlan, cdp_url: str) -> dict[str, Any]:
    """Save one approved Facebook Reel as a Meta Business Suite draft."""

    if plan.target != "meta_facebook" or plan.mode != "draft":
        raise ManifestValidationError("Meta browser action is Facebook-draft-only")
    manager, browser = _connect(cdp_url)
    try:
        dashboard_url = (
            "https://business.facebook.com/latest/"
            f"?asset_id={plan.stable_id}&business_id={plan.business_id}"
        )
        preflight = browser.contexts[0].new_page()
        preflight.goto(dashboard_url, wait_until="domcontentloaded", timeout=120_000)
        preflight.wait_for_timeout(2_000)
        if f"asset_id={plan.stable_id}" not in preflight.url:
            raise RuntimeError("wrong Meta asset during duplicate preflight")
        drafts = preflight.get_by_role("button", name="Beitragsentwürfe", exact=True)
        drafts.click(force=True)
        preflight.wait_for_timeout(1_000)
        if plan.caption in _visible_body(preflight):
            raise DuplicatePublication("Meta draft list already contains the approved caption")
        preflight.close()

        url = (
            "https://business.facebook.com/latest/reels_composer/"
            f"?asset_id={plan.stable_id}&business_id={plan.business_id}"
        )
        page = browser.contexts[0].new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(2_000)
        if f"asset_id={plan.stable_id}" not in page.url:
            raise RuntimeError("wrong Meta asset before upload")
        body = _visible_body(page)
        if plan.visible_name not in body:
            raise RuntimeError("wrong visible Meta page before upload")

        combo = page.get_by_role("combobox").first
        combo.click()
        page.wait_for_timeout(300)
        options = page.get_by_role("option")
        for index in range(options.count()):
            option = options.nth(index)
            name = " ".join(option.inner_text().split())
            selected = option.get_attribute("aria-selected") == "true"
            if name == META_FACEBOOK_PAGE_NAME and not selected:
                option.click()
            elif name != META_FACEBOOK_PAGE_NAME and selected:
                option.click()
        page.keyboard.press("Escape")
        if " ".join(combo.inner_text().split()) != META_FACEBOOK_PAGE_NAME:
            raise RuntimeError("Meta target selection is not Facebook-only")

        with page.expect_file_chooser(timeout=15_000) as chooser:
            page.get_by_role("button", name="Video hinzufügen", exact=True).click()
        chooser.value.set_files(str(plan.media_path))
        page.wait_for_function("() => document.body.innerText.includes('100 %')", timeout=120_000)
        textbox = page.get_by_role("textbox", name=re.compile(r"Text hinzufügen", re.I))
        textbox.fill(plan.caption)
        _rightmost_button(page, "Weiter").click()
        page.wait_for_timeout(900)
        if "Keine Urheberrechtsprobleme festgestellt" not in _visible_body(page):
            raise RuntimeError("Meta copyright precheck did not pass")
        _rightmost_button(page, "Weiter").click()
        page.wait_for_timeout(900)

        draft = page.get_by_role("button", name="Als Entwurf speichern", exact=True)
        if not draft.is_enabled():
            raise RuntimeError("Meta draft is disabled for the selected target")
        draft.click()
        if draft.get_attribute("aria-pressed") != "true":
            raise RuntimeError("Meta draft option was not selected")
        save = _rightmost_button(page, "Speichern")
        save.click()
        page.wait_for_timeout(2_000)
        confirmation = _visible_body(page)
        if "Reel als Entwurf gespeichert" not in confirmation:
            raise RuntimeError("Meta draft confirmation was not shown")

        dashboard = browser.contexts[0].new_page()
        dashboard.goto(
            (
                "https://business.facebook.com/latest/"
                f"?asset_id={plan.stable_id}&business_id={plan.business_id}"
            ),
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        dashboard.wait_for_timeout(2_000)
        drafts = dashboard.get_by_role("button", name="Beitragsentwürfe", exact=True)
        drafts.click(force=True)
        dashboard.wait_for_timeout(1_000)
        if plan.caption not in _visible_body(dashboard):
            raise RuntimeError("Meta draft did not persist in the draft list")
        return {
            "status": "draft",
            "external_id": None,
            "external_url": dashboard.url,
            "evidence": [
                "target asset and visible page name matched",
                "copyright precheck passed",
                "draft confirmation shown",
                "caption persisted in Beitragsentwürfe",
            ],
        }
    finally:
        manager.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("verify-session", "verify-manifest", "youtube-private", "meta-facebook-draft"),
    )
    parser.add_argument("--manifest")
    parser.add_argument("--target", choices=("youtube", "meta_facebook"))
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9223")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required for a platform mutation; verification is the default",
    )
    args = parser.parse_args()

    if args.action == "verify-session":
        print(json.dumps(verify_target_sessions(args.cdp_url), ensure_ascii=False, indent=2))
        return 0
    if not args.manifest:
        parser.error("--manifest is required for this action")
    if args.action == "verify-manifest":
        if not args.target:
            parser.error("--target is required for verify-manifest")
        target = args.target
    else:
        target = "youtube" if args.action == "youtube-private" else "meta_facebook"
    plan = build_action_plan(args.manifest, target)
    if args.action == "verify-manifest":
        print(
            json.dumps(
                {
                    "packet": plan.manifest_path.parent.name,
                    "target": plan.target,
                    "mode": plan.mode,
                    "visible_name": plan.visible_name,
                    "stable_id": plan.stable_id,
                    "media": plan.media_path.name,
                    "fingerprint": plan.fingerprint,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not args.execute:
        raise SystemExit("Refusing mutation without --execute")

    with packet_lock(plan.manifest_path):
        if args.action == "youtube-private":
            result = publish_youtube_private(plan, args.cdp_url)
        else:
            result = publish_meta_facebook_draft(plan, args.cdp_url)
        record_result(
            plan.manifest_path,
            plan,
            status=result["status"],
            external_id=result["external_id"],
            external_url=result["external_url"],
            evidence=result["evidence"],
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
