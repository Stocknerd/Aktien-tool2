"""Create Canva Bulk Create packets for factual personal posts."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.native_browser_publisher import PROJECT, TARGET_CONTRACTS


MAX_FACTS = 5


def _required_text(payload: dict[str, Any], key: str) -> str:
    raw_value = payload.get(key)
    if not isinstance(raw_value, str):
        raise ValueError(f"{key} is required and must be text")
    value = raw_value.strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(payload: dict[str, Any], key: str) -> str:
    raw_value = payload.get(key)
    if raw_value is None:
        return ""
    if not isinstance(raw_value, str):
        raise ValueError(f"{key} must be text")
    return raw_value.strip()


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß]+", "-", value).strip("-").lower()
    return normalized[:48] or "personal-post"


def _validate_facts(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_facts = payload.get("facts")
    if not isinstance(raw_facts, list) or not raw_facts:
        raise ValueError("facts must contain at least one supplied fact")
    if len(raw_facts) > MAX_FACTS:
        raise ValueError(f"facts supports at most {MAX_FACTS} entries")

    facts: list[dict[str, str]] = []
    for index, fact in enumerate(raw_facts, start=1):
        if not isinstance(fact, dict):
            raise ValueError(f"facts[{index}] must be an object")
        raw_label = fact.get("label")
        raw_value = fact.get("value")
        raw_context = fact.get("context")
        if not isinstance(raw_label, str) or not isinstance(raw_value, str):
            raise ValueError(f"facts[{index}] label and value must be text")
        if raw_context is not None and not isinstance(raw_context, str):
            raise ValueError(f"facts[{index}] context must be text")
        label = raw_label.strip()
        value = raw_value.strip()
        context = "" if raw_context is None else raw_context.strip()
        if not label or not value:
            raise ValueError(f"facts[{index}] requires label and value")
        facts.append({"label": label, "value": value, "context": context})
    return facts


def _build_caption(payload: dict[str, Any], facts: list[dict[str, str]]) -> str:
    headline = _required_text(payload, "headline")
    period = _required_text(payload, "period")
    lesson = _optional_text(payload, "lesson")
    question = _optional_text(payload, "question")

    lines = [headline, "", f"Zeitraum: {period}", ""]
    for fact in facts:
        suffix = f" – {fact['context']}" if fact["context"] else ""
        lines.append(f"• {fact['label']}: {fact['value']}{suffix}")
    if lesson:
        lines.extend(["", f"Mein Fazit: {lesson}"])
    if question:
        lines.extend(["", question])
    lines.extend(["", "Keine Anlageberatung."])
    return "\n".join(lines)


def create_personal_canva_packet(
    payload: dict[str, Any],
    output_root: str | Path,
    *,
    now: datetime | None = None,
) -> Path:
    """Write a reviewable Canva packet without inventing personal facts.

    The CSV is intended for Canva's Bulk Create workflow. The packet never
    posts by itself and remains in ``needs_canva`` until a human-approved Canva
    export is attached.
    """

    content_type = _required_text(payload, "content_type")
    period = _required_text(payload, "period")
    headline = _required_text(payload, "headline")
    subheadline = _optional_text(payload, "subheadline")
    lesson = _optional_text(payload, "lesson")
    question = _optional_text(payload, "question")
    facts = _validate_facts(payload)
    raw_targets = payload.get("targets", ["youtube", "meta_facebook"])
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("targets must be a non-empty list")
    if any(not isinstance(target, str) or target not in TARGET_CONTRACTS for target in raw_targets):
        raise ValueError("targets must use supported publisher contract keys")
    requested_targets = list(dict.fromkeys(raw_targets))

    timestamp = now or datetime.now(timezone.utc)
    folder_name = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S_%f')}_personal_{_slug(headline)}"
    packet_dir = Path(output_root).expanduser().resolve() / folder_name
    packet_dir.mkdir(parents=True, exist_ok=False)

    row: dict[str, str] = {
        "content_type": content_type,
        "period": period,
        "headline": headline,
        "subheadline": subheadline,
        "lesson": lesson,
        "question": question,
        "disclaimer": "Keine Anlageberatung.",
    }
    for index in range(1, MAX_FACTS + 1):
        fact = facts[index - 1] if index <= len(facts) else {"label": "", "value": "", "context": ""}
        row[f"fact_{index}_label"] = fact["label"]
        row[f"fact_{index}_value"] = fact["value"]
        row[f"fact_{index}_context"] = fact["context"]

    csv_path = packet_dir / "canva_bulk_create.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    caption = _build_caption(payload, facts)
    youtube_caption = f"{caption}\n\n#finanzen #geldanlage #schatzsuche40\n"
    (packet_dir / "caption_instagram.txt").write_text(caption + "\n", encoding="utf-8")
    (packet_dir / "caption_youtube.txt").write_text(
        youtube_caption,
        encoding="utf-8",
    )

    brief_lines = [
        "# Canva-Brief: persönlicher Beitrag",
        "",
        f"- Format: {content_type}",
        f"- Zeitraum: {period}",
        "- Ziel: echter persönlicher Einblick, keine generische Stock-Grafik",
        "- Status: Canva-Gestaltung und manuelle Freigabe erforderlich",
        "",
        "## Canva Bulk Create",
        "",
        "1. Bestehende persönliche Schatzsuche-4.0-Vorlage duplizieren.",
        "2. In Canva `Apps > Bulk Create` öffnen und `canva_bulk_create.csv` hochladen.",
        "3. Vorlagenfelder mit den gleichnamigen CSV-Spalten verbinden.",
        "4. Leere Faktenfelder ausblenden, nicht mit erfundenen Werten füllen.",
        "5. Als 1080×1920 MP4 (H.264) exportieren und in diesen Ordner legen.",
        "6. Text und Zahlen vor Veröffentlichung persönlich prüfen.",
        "",
        "## Gestaltungsregeln",
        "",
        "- Echte Zahlen und eigene Beobachtung klar in den Mittelpunkt.",
        "- Bekannte Canva-Vorlage und wiedererkennbare Schrift/Farben beibehalten.",
        "- Keine KI-generierten Gesichter oder vermeintlich persönlichen Fotos.",
        "- Hook oben, zwei bis fünf Kennzahlen in der Mitte, persönliches Fazit unten.",
        "- Nicht automatisch veröffentlichen; finaler Post bleibt freigabepflichtig.",
    ]
    (packet_dir / "canva_brief.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "packet_id": packet_dir.name,
        "project": PROJECT,
        "created_at": timestamp.isoformat(),
        "status": "needs_canva",
        "content_pillar": "personal_update",
        "content_type": content_type,
        "period": period,
        "requires_manual_approval": True,
        "canva": {
            "workflow": "bulk_create",
            "csv": csv_path.name,
            "brief": "canva_brief.md",
            "template_url": _optional_text(payload, "canva_template_url") or None,
        },
        "media": {
            "path": None,
            "sha256": None,
            "reviewed": False,
            "audio_strategy": "unset",
        },
        "copy": {
            "youtube_title": f"{headline} #shorts",
            "youtube_description": youtube_caption.strip(),
            "meta_caption": caption,
        },
        "publishing": {
            "allowed": False,
            "reason": "A reviewed Canva export has not been attached and approved yet.",
            "approval": None,
            "requested_targets": requested_targets,
            "targets": {name: dict(contract) for name, contract in TARGET_CONTRACTS.items()},
            "results": {},
        },
    }
    (packet_dir / "post_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return packet_dir


def create_personal_canva_packet_from_json(
    input_path: str | Path,
    output_root: str | Path,
) -> Path:
    """Load a UTF-8 JSON brief and turn it into a Canva queue packet."""

    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"input file does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"input file is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("input JSON must contain an object")
    return create_personal_canva_packet(payload, output_root)
