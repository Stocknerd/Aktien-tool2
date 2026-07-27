#!/usr/bin/env python3
"""Bounded, hash-guarded homepage hub-link update for Schatzsuche 4.0.

Dry-run is the default. Use --apply for the single approved REST mutation.
Credentials are loaded from the repository .env and are never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SITE_URL = "https://schatzsuche40.de"
PAGE_ID = 1045
EXPECTED_RAW_SHA256 = "d837922b74b841b33054b706a77057b713c42576e14f81096c3f0b1d29d6e38d"
LEGACY_APPLIED_RAW_SHA256 = "1553a1cc4ea4cc7e314a1852eb6e7e3b13a436a569c4bb41f54f6a910b844667"
WRAP_ONLY_APPLIED_RAW_SHA256 = "fb661fae596a98008894cfe1a671dc7e5306bb2efd5941e10e7740d92dfbe23c"
LAYOUT_ONLY_APPLIED_RAW_SHA256 = "786cc6e080a8d65218db004f3b3f7f87a30e900e5b8631309b0cf2b86e4ca83e"
APPLIED_RAW_SHA256 = "d60a11e2d69a03c0563d671d0740acdf9d37ee41a8aa56b9fc12d24d4d49de91"
DEPOT_URL = f"{SITE_URL}/meine-depots/"
GUIDE_URL = f"{SITE_URL}/leitfaden-aktienbewertung/"

CSS_ANCHOR = """.s40-depot-btn:hover {
  opacity: 0.9;
  color: #0B1E21 !important;
}"""
CSS_REPLACEMENT = """.s40-depot-btn:hover {
  opacity: 0.9;
  color: #0B1E21 !important;
}
.s40-inline-link {
  color: #C9A227 !important;
  font-weight: 700;
  text-decoration: none !important;
  white-space: normal;
}
.s40-inline-link:hover {
  opacity: 0.85;
  color: #C9A227 !important;
}
.s40-guide-online {
  margin: 14px auto 16px !important;
  font-size: 0.9rem !important;
}"""

DEPOT_ANCHOR = "Im Juni haben wir alle Benchmarks mit dem Dividendendepot geschlagen. Erfahre alles über meine Sparraten, Dividenden und die aktuelle Performance.</p>"
DEPOT_REPLACEMENT = f"""Im Juni haben wir alle Benchmarks mit dem Dividendendepot geschlagen. Erfahre alles über meine Sparraten, Dividenden und die aktuelle Performance. <a class="s40-inline-link" href="{DEPOT_URL}">Alle Depots ansehen →</a></p>"""

GUIDE_ANCHOR = '<p style="font-size: 0.75rem; margin-top: 15px; opacity: 0.5;">'
GUIDE_REPLACEMENT = f"""<p class="s40-guide-online"><a class="s40-inline-link" href="{GUIDE_URL}">Online-Leitfaden direkt lesen →</a></p>
{GUIDE_ANCHOR}"""

MOBILE_MEDIA_ANCHOR = """@media (max-width: 640px) {
  .s40-hero { padding: 40px 20px; }
  .s40-hero h1 { font-size: 1.6rem; }
  .s40-stats { grid-template-columns: 1fr; }
  .s40-wrapper { padding: 28px 20px; }
}"""
MOBILE_MEDIA_LAYOUT_ONLY = """@media (max-width: 640px) {
  .s40-hero { padding: 40px 20px; }
  .s40-hero h1 { font-size: 1.6rem; }
  .s40-stats { grid-template-columns: 1fr; }
  .s40-wrapper { padding: 28px 20px; }
  .s40-depot-banner { padding: 20px 16px; gap: 16px; }
  .s40-depot-info, .s40-depot-stats { min-width: 0; width: 100%; }
  .s40-depot-stats { flex-wrap: wrap; }
}"""
MOBILE_MEDIA_REPLACEMENT = """@media (max-width: 640px) {
  .s40-hero { padding: 40px 20px; }
  .s40-hero h1 { font-size: 1.6rem; }
  .s40-stats { grid-template-columns: 1fr; }
  .s40-wrapper { padding: 28px 20px; }
  .s40-depot-banner { padding: 20px 16px; gap: 16px; }
  .s40-depot-info, .s40-depot-stats { min-width: 0; width: 100%; }
  .s40-depot-stats { flex-wrap: wrap; }
  .s40-inline-link { display: block; margin-top: 6px; }
}"""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mutate(raw: str) -> str:
    replacements = [
        (CSS_ANCHOR, CSS_REPLACEMENT, "CSS anchor"),
        (DEPOT_ANCHOR, DEPOT_REPLACEMENT, "depot paragraph"),
        (GUIDE_ANCHOR, GUIDE_REPLACEMENT, "guide section"),
    ]
    result = raw
    for old, new, label in replacements:
        count = result.count(old)
        if count != 1:
            raise RuntimeError(f"Expected exactly one {label}; found {count}")
        result = result.replace(old, new, 1)
    return add_mobile_constraints(result)


def add_mobile_constraints(raw: str) -> str:
    if raw.count(MOBILE_MEDIA_ANCHOR) != 1:
        raise RuntimeError(
            f"Expected one mobile media anchor; found {raw.count(MOBILE_MEDIA_ANCHOR)}"
        )
    return raw.replace(MOBILE_MEDIA_ANCHOR, MOBILE_MEDIA_REPLACEMENT, 1)


def add_mobile_cta_block(raw: str) -> str:
    if raw.count(MOBILE_MEDIA_LAYOUT_ONLY) != 1:
        raise RuntimeError(
            f"Expected one layout-only media block; found {raw.count(MOBILE_MEDIA_LAYOUT_ONLY)}"
        )
    return raw.replace(MOBILE_MEDIA_LAYOUT_ONLY, MOBILE_MEDIA_REPLACEMENT, 1)


def repair_mobile_wrap(raw: str) -> str:
    old = """.s40-inline-link {
  color: #C9A227 !important;
  font-weight: 700;
  text-decoration: none !important;
  white-space: nowrap;
}"""
    new = """.s40-inline-link {
  color: #C9A227 !important;
  font-weight: 700;
  text-decoration: none !important;
  white-space: normal;
}"""
    if raw.count(old) != 1:
        raise RuntimeError(f"Expected one legacy inline-link CSS block; found {raw.count(old)}")
    return raw.replace(old, new, 1)


def public_check(session: requests.Session, suffix: str = "") -> dict[str, object]:
    response = session.get(f"{SITE_URL}/{suffix}", timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    canonical = soup.find("link", rel="canonical")
    canonical_href = canonical.get("href") if canonical else None
    canonical_url = canonical_href if isinstance(canonical_href, str) else None
    robots = soup.find("meta", attrs={"name": "robots"})
    robots_value = robots.get("content") if robots else None
    robots_content = robots_value if isinstance(robots_value, str) else ""
    links: list[str] = []
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if isinstance(href, str):
            links.append(urljoin(response.url, href))
    inline_links = soup.select("a.s40-inline-link")
    depot_inline_links = [
        link
        for link in inline_links
        if urljoin(response.url, str(link.get("href", ""))) == DEPOT_URL
        and link.get_text(" ", strip=True) == "Alle Depots ansehen →"
    ]
    guide_inline_links = [
        link
        for link in inline_links
        if urljoin(response.url, str(link.get("href", ""))) == GUIDE_URL
        and link.get_text(" ", strip=True) == "Online-Leitfaden direkt lesen →"
    ]
    return {
        "http": response.status_code,
        "canonical": canonical_url,
        "h1_count": len(soup.find_all("h1")),
        "noindex": "noindex" in robots_content.lower(),
        "depot_link_count": links.count(DEPOT_URL),
        "guide_link_count": links.count(GUIDE_URL),
        "depot_inline_link_count": len(depot_inline_links),
        "guide_inline_link_count": len(guide_inline_links),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Perform the approved REST update")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    username = os.environ["SCHATZSUCHE_WP_USER"]
    password = os.environ["SCHATZSUCHE_WP_APP_PASSWORD"]
    session = requests.Session()
    session.auth = (username, password)
    session.headers["User-Agent"] = "SchatzsucheHomepageHubUpdater/1.0"
    public_session = requests.Session()
    public_session.headers["User-Agent"] = "SchatzsucheHomepageHubVerifier/1.0"

    endpoint = f"{SITE_URL}/wp-json/wp/v2/pages/{PAGE_ID}?context=edit"
    before_response = session.get(endpoint, timeout=30)
    before_response.raise_for_status()
    before_json = before_response.json()
    before_raw = before_json["content"]["raw"]
    before_hash = sha256(before_raw)
    if before_hash == APPLIED_RAW_SHA256:
        normal = public_check(public_session)
        depot_count = normal["depot_link_count"]
        guide_count = normal["guide_link_count"]
        if (
            normal["canonical"] != f"{SITE_URL}/"
            or normal["h1_count"] != 1
            or normal["noindex"]
            or not isinstance(depot_count, int)
            or not isinstance(guide_count, int)
            or depot_count < 1
            or guide_count < 1
            or normal["depot_inline_link_count"] != 1
            or normal["guide_inline_link_count"] != 1
        ):
            raise RuntimeError(f"Already-applied content failed public verification: {normal}")
        print(
            json.dumps(
                {
                    "mode": "verify",
                    "status": "already-applied",
                    "page_id": PAGE_ID,
                    "current_sha256": before_hash,
                    "public_check": normal,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if before_hash == LEGACY_APPLIED_RAW_SHA256:
        after_raw = add_mobile_constraints(repair_mobile_wrap(before_raw))
        action = "repair-mobile-layout"
    elif before_hash == WRAP_ONLY_APPLIED_RAW_SHA256:
        after_raw = add_mobile_constraints(before_raw)
        action = "repair-mobile-layout"
    elif before_hash == LAYOUT_ONLY_APPLIED_RAW_SHA256:
        after_raw = add_mobile_cta_block(before_raw)
        action = "repair-mobile-cta-block"
    elif before_hash == EXPECTED_RAW_SHA256:
        after_raw = mutate(before_raw)
        action = "add-hub-links"
    else:
        raise RuntimeError(f"Optimistic hash mismatch: {before_hash}")

    after_hash = sha256(after_raw)
    if after_hash != APPLIED_RAW_SHA256:
        raise RuntimeError(f"Unexpected after hash: {after_hash}")
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "action": action,
        "page_id": PAGE_ID,
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "depot_link_added": DEPOT_URL in after_raw and DEPOT_URL not in before_raw,
        "guide_link_added": GUIDE_URL in after_raw and GUIDE_URL not in before_raw,
    }
    if not args.apply:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    backup_dir = root / "traffic" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"page-{PAGE_ID}-pre-hub-links-{stamp}.json"
    backup_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "page_id": PAGE_ID,
                "source_url": before_json.get("link"),
                "raw_sha256": before_hash,
                "content_raw": before_raw,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    mutated = False
    write_attempted = False
    try:
        prewrite = session.get(endpoint, timeout=30)
        prewrite.raise_for_status()
        if sha256(prewrite.json()["content"]["raw"]) != before_hash:
            raise RuntimeError("Content changed between read and write; refusing update")
        write_attempted = True
        update_response = session.post(endpoint, json={"content": after_raw}, timeout=45)
        update_response.raise_for_status()
        mutated = True
        returned_raw = update_response.json()["content"]["raw"]
        if returned_raw != after_raw:
            raise RuntimeError("REST response content did not match requested content")

        readback = session.get(endpoint, timeout=30)
        readback.raise_for_status()
        readback_raw = readback.json()["content"]["raw"]
        if sha256(readback_raw) != after_hash:
            raise RuntimeError("REST readback hash mismatch")

        normal = public_check(public_session)
        bypass = public_check(public_session, f"?hubverify={stamp}")
        for label, check in (("normal", normal), ("bypass", bypass)):
            if check["canonical"] != f"{SITE_URL}/":
                raise RuntimeError(f"{label}: canonical changed")
            if check["h1_count"] != 1 or check["noindex"]:
                raise RuntimeError(f"{label}: heading/indexability regression")
            depot_count = check["depot_link_count"]
            guide_count = check["guide_link_count"]
            if (
                not isinstance(depot_count, int)
                or not isinstance(guide_count, int)
                or depot_count < 1
                or guide_count < 1
                or check["depot_inline_link_count"] != 1
                or check["guide_inline_link_count"] != 1
            ):
                raise RuntimeError(f"{label}: expected hub links missing")

        summary.update(
            {
                "backup_path": str(backup_path),
                "rest_readback_sha256": sha256(readback_raw),
                "normal_public_check": normal,
                "bypass_public_check": bypass,
            }
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except Exception:
        if write_attempted:
            current = session.get(endpoint, timeout=30)
            current.raise_for_status()
            current_hash = sha256(current.json()["content"]["raw"])
            if current_hash == after_hash:
                mutated = True
            elif current_hash == before_hash:
                mutated = False
            else:
                raise RuntimeError(
                    "Write outcome is ambiguous and content changed again; refusing destructive rollback"
                )
        if mutated:
            rollback = session.post(endpoint, json={"content": before_raw}, timeout=45)
            rollback.raise_for_status()
            restored = session.get(endpoint, timeout=30)
            restored.raise_for_status()
            if sha256(restored.json()["content"]["raw"]) != before_hash:
                raise RuntimeError("Mutation failed and rollback verification also failed")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
