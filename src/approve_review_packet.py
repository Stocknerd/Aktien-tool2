#!/usr/bin/env python3
"""Review-Paket vorprüfen oder eine explizite Freigabe atomar dokumentieren.

Dieses Kommando veröffentlicht nichts und ruft keine Plattform-API auf.
"""

from __future__ import annotations

import argparse
import json

from src.review_packets import TARGET_CONTRACTS, approve_review_packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Pfad zu review_manifest.json")
    parser.add_argument("--approved-by", required=True, help="Name der freigebenden Person")
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        choices=sorted(TARGET_CONTRACTS),
        required=True,
        help="Exakt freigegebenes Ziel; für mehrere Ziele wiederholen",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Freigabe atomar speichern; ohne diesen Schalter nur Read-only-Preflight",
    )
    args = parser.parse_args()
    result = approve_review_packet(
        args.manifest,
        approved_by=args.approved_by,
        targets=args.targets,
        apply=args.approve,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
