#!/usr/bin/env python3
"""Attach and explicitly approve one reviewed Canva MP4 export."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIO_STRATEGIES = ("embedded_licensed", "platform_audio_later", "silent_intentional")


class ApprovalError(ValueError):
    pass


def _load(path: str | Path) -> tuple[Path, dict[str, Any]]:
    manifest_path = Path(path).expanduser().resolve()
    if not manifest_path.is_file():
        raise ApprovalError(f"manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApprovalError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ApprovalError("manifest must contain an object")
    return manifest_path, data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect_video(video_path: str | Path, audio_strategy: str) -> dict[str, Any]:
    """Validate the technical export contract through ffprobe."""

    path = Path(video_path).expanduser().resolve()
    if not path.is_file():
        raise ApprovalError(f"export not found: {path}")
    if path.suffix.lower() != ".mp4":
        raise ApprovalError("reviewed export must be an MP4")
    if audio_strategy not in AUDIO_STRATEGIES:
        raise ApprovalError(f"unsupported audio strategy: {audio_strategy}")
    if not shutil.which("ffprobe"):
        raise ApprovalError("ffprobe is required for export approval")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ApprovalError(f"ffprobe rejected the export: {result.stderr.strip()}")
    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ApprovalError("ffprobe returned invalid JSON") from exc

    streams = probe.get("streams") if isinstance(probe, dict) else None
    if not isinstance(streams, list):
        raise ApprovalError("ffprobe found no streams")
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1:
        raise ApprovalError("export must contain exactly one video stream")
    video = video_streams[0]
    if video.get("codec_name") != "h264":
        raise ApprovalError("export video codec must be H.264")
    if (video.get("width"), video.get("height")) != (1080, 1920):
        raise ApprovalError("export resolution must be 1080x1920")

    raw_format = probe.get("format")
    format_data = raw_format if isinstance(raw_format, dict) else {}
    try:
        duration = float(format_data.get("duration", 0))
        size = int(format_data.get("size", 0))
    except (TypeError, ValueError) as exc:
        raise ApprovalError("export duration or size is invalid") from exc
    if not 3 <= duration <= 180:
        raise ApprovalError("export duration must be between 3 and 180 seconds")
    if size < 100_000:
        raise ApprovalError("export is unexpectedly small")

    if audio_strategy == "embedded_licensed" and not audio_streams:
        raise ApprovalError("embedded_licensed requires an audio stream")
    if audio_strategy in ("platform_audio_later", "silent_intentional") and audio_streams:
        raise ApprovalError(f"{audio_strategy} requires an export without embedded audio")

    return {
        "codec": video["codec_name"],
        "width": video["width"],
        "height": video["height"],
        "frame_rate": video.get("r_frame_rate"),
        "duration_seconds": round(duration, 3),
        "size_bytes": size,
        "audio_streams": len(audio_streams),
    }


def approve_packet(
    manifest_path: str | Path,
    export_path: str | Path,
    *,
    approved_by: str,
    audio_strategy: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Validate an export and optionally atomically approve its packet."""

    path, data = _load(manifest_path)
    if data.get("schema_version") != 2 or data.get("project") != "schatzsuche4.0":
        raise ApprovalError("manifest is not a Schatzsuche schema-2 packet")
    if data.get("status") != "needs_canva":
        raise ApprovalError("only a needs_canva packet can be approved")
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise ApprovalError("approved_by is required")
    publishing = data.get("publishing")
    if not isinstance(publishing, dict) or publishing.get("allowed") is not False:
        raise ApprovalError("unapproved packet must be fail-closed")
    if publishing.get("results") not in ({}, None):
        raise ApprovalError("packet already contains platform results")

    source = Path(export_path).expanduser().resolve()
    inspection = inspect_video(source, audio_strategy)
    result = {
        "manifest": str(path),
        "source_export": str(source),
        "inspection": inspection,
        "approved": False,
    }
    if not apply:
        return result

    target = path.parent / "reviewed_export.mp4"
    if source != target:
        shutil.copy2(source, target)
    digest = _sha256(target)
    approved_at = datetime.now(timezone.utc).isoformat()
    data["status"] = "approved"
    data["requires_manual_approval"] = False
    data["media"] = {
        "path": target.name,
        "sha256": digest,
        "reviewed": True,
        "audio_strategy": audio_strategy,
        "inspection": inspection,
    }
    data["publishing"]["allowed"] = True
    data["publishing"]["reason"] = "Reviewed Canva export explicitly approved."
    data["publishing"]["approval"] = {
        "approved_by": approved_by.strip(),
        "approved_at": approved_at,
    }
    data["publishing"].setdefault("results", {})
    _write_atomic(path, data)
    result.update(
        {
            "approved": True,
            "approved_at": approved_at,
            "media": target.name,
            "sha256": digest,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--export", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--audio-strategy", required=True, choices=AUDIO_STRATEGIES)
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mutate the manifest after validation; default is read-only preflight",
    )
    args = parser.parse_args()
    result = approve_packet(
        args.manifest,
        args.export,
        approved_by=args.approved_by,
        audio_strategy=args.audio_strategy,
        apply=args.approve,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
