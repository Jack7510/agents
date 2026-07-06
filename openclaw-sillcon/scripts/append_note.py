#!/usr/bin/env python3
"""Append a text note to the current ISO-week Markdown note file."""

from __future__ import annotations

import argparse
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import fcntl
except ImportError:  # pragma: no cover - this project currently targets Linux/macOS.
    fcntl = None


DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_NOTES_ROOT = Path("data/notes")
HASHTAG_PATTERN = re.compile(r"(?<!\w)#([A-Za-z0-9_\-\u4e00-\u9fff]+)")
CAPTURE_PREFIX_PATTERN = re.compile(r"^(记一下|笔记|想法)(?:[：:\s]+)")


@contextmanager
def file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def parse_timestamp(value: str | None, timezone: str) -> datetime:
    if value is None:
        return datetime.now(ZoneInfo(timezone))

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(ZoneInfo(timezone))


def extract_tags(text: str, explicit_tags: list[str]) -> list[str]:
    tags: list[str] = []
    for tag in explicit_tags:
        cleaned = tag.strip().lstrip("#")
        if cleaned and cleaned not in tags:
            tags.append(cleaned)

    for match in HASHTAG_PATTERN.findall(text):
        if match not in tags:
            tags.append(match)

    return tags or ["未分类"]


def has_capture_prefix(text: str) -> bool:
    return CAPTURE_PREFIX_PATTERN.match(text.strip()) is not None


def normalize_note_text(text: str) -> str:
    stripped = text.strip()
    stripped = CAPTURE_PREFIX_PATTERN.sub("", stripped, count=1).strip()
    if not stripped:
        raise ValueError("note text cannot be empty")
    return stripped


def note_file_for(timestamp: datetime, notes_root: Path) -> Path:
    iso_year, iso_week, _ = timestamp.isocalendar()
    return notes_root / str(iso_year) / f"{iso_year}-W{iso_week:02d}.md"


def initial_week_file(timestamp: datetime) -> str:
    iso_year, iso_week, _ = timestamp.isocalendar()
    return (
        f"# {iso_year}-W{iso_week:02d} 口头笔记\n\n"
        "## Inbox\n\n"
        "## 本周整理\n\n"
        "待整理。\n\n"
        "## 主题索引\n\n"
        "待整理。\n"
    )


def format_note_entry(
    *,
    timestamp: datetime,
    source: str,
    entry: str,
    tags: list[str],
) -> str:
    tag_text = ", ".join(tags)
    indented_entry = "\n".join(f"  {line}" if line else "" for line in entry.splitlines())
    return (
        f"### {timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"- 来源：{source}\n"
        f"- 标签：{tag_text}\n"
        "- 原文：\n"
        f"{indented_entry}\n\n"
    )


def insert_into_inbox(existing: str, entry: str) -> str:
    marker = "\n## 本周整理\n"
    if marker not in existing:
        return existing.rstrip() + "\n\n## Inbox\n\n" + entry
    return existing.replace(marker, "\n" + entry + marker, 1)


def append_note(
    *,
    text: str,
    notes_root: Path,
    source: str,
    tags: list[str],
    timestamp: datetime,
    require_prefix: bool = False,
) -> Path:
    if require_prefix and not has_capture_prefix(text):
        raise ValueError("message does not start with a supported note capture prefix")

    clean_text = normalize_note_text(text)
    note_file = note_file_for(timestamp, notes_root)
    note_file.parent.mkdir(parents=True, exist_ok=True)

    note_tags = extract_tags(clean_text, tags)
    entry = format_note_entry(
        timestamp=timestamp,
        source=source,
        entry=clean_text,
        tags=note_tags,
    )

    lock_path = notes_root / ".append_note.lock"
    with file_lock(lock_path):
        if note_file.exists():
            existing = note_file.read_text(encoding="utf-8")
        else:
            existing = initial_week_file(timestamp)
        updated = insert_into_inbox(existing, entry)
        note_file.write_text(updated, encoding="utf-8")

    return note_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a text note to data/notes/YYYY/YYYY-Www.md."
    )
    parser.add_argument("text", help="Text note to append.")
    parser.add_argument(
        "--source",
        default="manual",
        help="Note source, for example wechat, feishu, or manual.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Explicit tag. Can be passed multiple times.",
    )
    parser.add_argument(
        "--notes-root",
        default=os.environ.get("OPENCLAW_NOTES_ROOT", str(DEFAULT_NOTES_ROOT)),
        help="Root directory for weekly Markdown notes.",
    )
    parser.add_argument(
        "--timestamp",
        help="ISO timestamp. Naive values are interpreted in --timezone.",
    )
    parser.add_argument(
        "--timezone",
        default=os.environ.get("OPENCLAW_NOTES_TIMEZONE", DEFAULT_TIMEZONE),
        help="IANA timezone used for week calculation and display.",
    )
    parser.add_argument(
        "--require-prefix",
        action="store_true",
        help="Only append messages that start with a supported capture prefix.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        timestamp = parse_timestamp(args.timestamp, args.timezone)
        note_file = append_note(
            text=args.text,
            notes_root=Path(args.notes_root),
            source=args.source,
            tags=args.tag,
            timestamp=timestamp,
            require_prefix=args.require_prefix,
        )
    except Exception as exc:
        print(f"append_note failed: {exc}", file=sys.stderr)
        return 1

    print(f"Appended note to {note_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
