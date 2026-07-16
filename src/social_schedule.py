"""Render and safely install the quality-first Schatzsuche social crontab."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.content_strategy import recommended_weekly_schedule


SOCIAL_JOB_MARKER = "src.social_reels_autoposter"
BLOCK_START = "# BEGIN SCHATZSUCHE SOCIAL QUEUE"
BLOCK_END = "# END SCHATZSUCHE SOCIAL QUEUE"
BLOCK_HEADER = "# Schatzsuche 4.0: quality-first social queue (3 stock / 2 current / 1 calendar)"
DAY_NUMBER = {"sun": "0", "mon": "1", "tue": "2", "wed": "3", "thu": "4", "fri": "5", "sat": "6"}


def _cron_days(days: tuple[str, ...]) -> str:
    try:
        return ",".join(DAY_NUMBER[day] for day in days)
    except KeyError as exc:
        raise ValueError(f"unsupported schedule day: {exc.args[0]}") from exc


def optimized_social_cron_lines(project_dir: str, python_path: str) -> tuple[str, ...]:
    """Render the runtime cron mix directly from the performance schedule."""

    schedule = recommended_weekly_schedule()
    project = shlex.quote(str(Path(project_dir)))
    python = shlex.quote(str(Path(python_path)))
    logs = Path(project_dir) / "logs"
    prefix = f"cd {project} && timeout 25m nice -n 19 ionice -c 3 {python} -m {SOCIAL_JOB_MARKER}"

    def line(minute: int, hour: int, days: tuple[str, ...], track: str, log_name: str) -> str:
        log_path = shlex.quote(str(logs / log_name))
        return (
            f"{minute} {hour} * * {_cron_days(days)} {prefix} --track {track} "
            f">> {log_path} 2>&1"
        )

    return (
        line(0, 16, schedule["stock_feed"], "stock", "cron_stock.log"),
        line(0, 18, schedule["current_topic_reel"], "ai", "cron_ai.log"),
        line(0, 18, schedule["dividend_calendar"], "calendar", "cron_calendar.log"),
    )


LEGACY_SOCIAL_JOB = re.compile(
    r"^(?:\S+\s+){5}.*(?:^|\s)-m\s+src\.social_reels_autoposter(?:\s|$)"
    r".*--track\s+(?:stock|ai|calendar)(?:\s|$)"
)


def _is_legacy_social_job(line: str) -> bool:
    return bool(LEGACY_SOCIAL_JOB.match(line))


def render_optimized_crontab(existing: str, *, project_dir: str, python_path: str) -> str:
    """Replace the owned block and legacy social jobs while preserving all others."""

    lines = [raw_line.rstrip() for raw_line in existing.splitlines()]
    starts = [index for index, line in enumerate(lines) if line == BLOCK_START]
    ends = [index for index, line in enumerate(lines) if line == BLOCK_END]
    if starts or ends:
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            raise ValueError("malformed owned cron block; refusing to render replacement")

    kept: list[str] = []
    inside_owned_block = False
    for line in lines:
        if line == BLOCK_START:
            inside_owned_block = True
            continue
        if line == BLOCK_END:
            inside_owned_block = False
            continue
        if inside_owned_block or _is_legacy_social_job(line) or line == BLOCK_HEADER:
            continue
        kept.append(line)

    while kept and not kept[-1]:
        kept.pop()
    if kept:
        kept.append("")
    kept.extend(
        [
            BLOCK_START,
            "CRON_TZ=Europe/Berlin",
            BLOCK_HEADER,
            *optimized_social_cron_lines(project_dir, python_path),
            BLOCK_END,
        ]
    )
    return "\n".join(kept) + "\n"


def read_existing_crontab() -> str:
    """Read crontab fail-closed; distinguish an empty table from read errors."""

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 1 and "no crontab" in result.stderr.lower():
        return ""
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise RuntimeError(f"cannot read existing crontab safely: {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or install the optimized social crontab")
    parser.add_argument("--project-dir", default="/home/ubuntu/aktien-tool2")
    parser.add_argument("--python-path", default="/home/ubuntu/aktien-tool2/venv/bin/python")
    parser.add_argument("--apply", action="store_true", help="Install the rendered crontab; default is dry-run")
    args = parser.parse_args()

    existing = read_existing_crontab()
    rendered = render_optimized_crontab(existing, project_dir=args.project_dir, python_path=args.python_path)

    if not args.apply:
        print(rendered, end="")
        return 0

    backup_dir = Path(args.project_dir) / "logs"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"crontab_before_social_optimization_{timestamp}.txt"
    backup_path.write_text(existing, encoding="utf-8")
    subprocess.run(["crontab", "-"], input=rendered, text=True, check=True)
    print(f"Optimized social crontab installed. Backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
