#!/usr/bin/env python3
"""Replace three confirmed broken depot-logo images with neutral text labels.

Dry-run is the default. Use --apply for the bounded REST mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SITE_URL = "https://schatzsuche40.de"
PAGE_URL = f"{SITE_URL}/meine-depots/"
PAGE_ID = 114
EXPECTED_RAW_SHA256 = "27fb754765b33ea1e61d31d50c4ccc8b38b493241af3c743ad704e1646381c0f"
APPLIED_RAW_SHA256 = "2e949a491e22a4b3482b6a218c48c88a6ac7db9b59831d31931525ed5c882015"

CSS_ANCHOR = """.depot-logo img {
  max-width: 100%;
  height: auto;
}"""
CSS_REPLACEMENT = """.depot-logo img {
  max-width: 100%;
  height: auto;
}
.depot-logo-text {
  color: #0B1E21;
  font-size: 1rem;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: 0.02em;
  text-align: center;
  overflow-wrap: anywhere;
}"""

IMAGE_REPLACEMENTS = {
    '<img src="https://schatzsuche40.de/wp-content/uploads/2026/01/tradersplace_logo.png" alt="Traders Place">': '<span class="depot-logo-text">Traders Place</span>',
    '<img src="https://schatzsuche40.de/wp-content/uploads/2026/01/c24_logo.png" alt="C24 Bank">': '<span class="depot-logo-text">C24 Bank</span>',
    '<img src="https://schatzsuche40.de/wp-content/uploads/2026/01/scalable_logo.png" alt="Scalable Capital">': '<span class="depot-logo-text">Scalable Capital</span>',
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mutate(raw: str) -> str:
    if raw.count(CSS_ANCHOR) != 1:
        raise RuntimeError(f"Expected one CSS anchor; found {raw.count(CSS_ANCHOR)}")
    result = raw.replace(CSS_ANCHOR, CSS_REPLACEMENT, 1)
    for old, new in IMAGE_REPLACEMENTS.items():
        count = result.count(old)
        if count != 1:
            raise RuntimeError(f"Expected one broken image fragment; found {count}")
        result = result.replace(old, new, 1)
    return result


def public_check(session: requests.Session, suffix: str = "") -> dict[str, object]:
    response = session.get(f"{PAGE_URL}{suffix}", timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    canonical = soup.find("link", rel="canonical")
    canonical_value = canonical.get("href") if canonical else None
    canonical_url = canonical_value if isinstance(canonical_value, str) else None
    broken_sources = [
        str(img.get("src", ""))
        for img in soup.find_all("img")
        if any(name in str(img.get("src", "")) for name in ("tradersplace_logo.png", "c24_logo.png", "scalable_logo.png"))
    ]
    return {
        "http": response.status_code,
        "canonical": canonical_url,
        "h1_count": len(soup.find_all("h1")),
        "text_logo_count": len(soup.select(".depot-logo-text")),
        "broken_logo_source_count": len(broken_sources),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    session = requests.Session()
    session.auth = (
        os.environ["SCHATZSUCHE_WP_USER"],
        os.environ["SCHATZSUCHE_WP_APP_PASSWORD"],
    )
    session.headers["User-Agent"] = "SchatzsucheDepotLogoRepair/1.0"
    public_session = requests.Session()
    public_session.headers["User-Agent"] = "SchatzsucheDepotLogoVerifier/1.0"
    endpoint = f"{SITE_URL}/wp-json/wp/v2/pages/{PAGE_ID}?context=edit"

    before_response = session.get(endpoint, timeout=30)
    before_response.raise_for_status()
    before_json = before_response.json()
    before_raw = before_json["content"]["raw"]
    before_hash = sha256(before_raw)
    if before_hash == APPLIED_RAW_SHA256:
        normal = public_check(public_session)
        if (
            normal["canonical"] != PAGE_URL
            or normal["h1_count"] != 1
            or normal["text_logo_count"] != 3
            or normal["broken_logo_source_count"] != 0
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
    if before_hash != EXPECTED_RAW_SHA256:
        raise RuntimeError(f"Optimistic hash mismatch: {before_hash}")

    after_raw = mutate(before_raw)
    after_hash = sha256(after_raw)
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "page_id": PAGE_ID,
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "broken_images_replaced": 3,
    }
    if not args.apply:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    backup_dir = root / "traffic" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"page-{PAGE_ID}-pre-logo-repair-{stamp}.json"
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
        update = session.post(endpoint, json={"content": after_raw}, timeout=45)
        update.raise_for_status()
        mutated = True
        if update.json()["content"]["raw"] != after_raw:
            raise RuntimeError("REST response content mismatch")
        readback = session.get(endpoint, timeout=30)
        readback.raise_for_status()
        readback_raw = readback.json()["content"]["raw"]
        if sha256(readback_raw) != after_hash:
            raise RuntimeError("REST readback hash mismatch")

        normal = public_check(public_session)
        bypass = public_check(public_session, f"?logoverify={stamp}")
        for label, check in (("normal", normal), ("bypass", bypass)):
            if check["canonical"] != PAGE_URL or check["h1_count"] != 1:
                raise RuntimeError(f"{label}: canonical or H1 regression")
            if check["text_logo_count"] != 3 or check["broken_logo_source_count"] != 0:
                raise RuntimeError(f"{label}: logo repair not publicly complete")

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
                raise RuntimeError("Mutation failed and rollback verification failed")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
