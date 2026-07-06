from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.append_note import (
    append_note,
    extract_tags,
    has_capture_prefix,
    normalize_note_text,
    note_file_for,
)


class AppendNoteTests(unittest.TestCase):
    def test_note_file_uses_iso_week(self) -> None:
        timestamp = datetime(2026, 7, 6, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))

        self.assertEqual(
            note_file_for(timestamp, Path("data/notes")),
            Path("data/notes/2026/2026-W28.md"),
        )

    def test_normalize_note_text_removes_capture_prefix_only(self) -> None:
        self.assertEqual(
            normalize_note_text("记一下：#产品 OpenClaw 先做好文字笔记。"),
            "#产品 OpenClaw 先做好文字笔记。",
        )

    def test_extract_tags_deduplicates_explicit_and_hashtag_tags(self) -> None:
        self.assertEqual(
            extract_tags("想法 #产品 #Agent：先可靠记录。", ["产品", "#信息助理"]),
            ["产品", "信息助理", "Agent"],
        )

    def test_extract_tags_defaults_to_uncategorized(self) -> None:
        self.assertEqual(extract_tags("没有标签的笔记", []), ["未分类"])

    def test_has_capture_prefix_matches_supported_prefixes(self) -> None:
        self.assertTrue(has_capture_prefix("笔记：今天继续做 OpenClaw。"))
        self.assertTrue(has_capture_prefix("想法: 先做可靠记录。"))
        self.assertFalse(has_capture_prefix("今天继续做 OpenClaw。"))

    def test_append_note_creates_week_file(self) -> None:
        timestamp = datetime(2026, 7, 6, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))

        with tempfile.TemporaryDirectory() as temp_dir:
            note_file = append_note(
                text="记一下 #产品：OpenClaw 先做好文字笔记。",
                notes_root=Path(temp_dir),
                source="manual",
                tags=[],
                timestamp=timestamp,
            )

            self.assertEqual(note_file, Path(temp_dir) / "2026" / "2026-W28.md")
            content = note_file.read_text(encoding="utf-8")
            self.assertIn("# 2026-W28 口头笔记", content)
            self.assertIn("### 2026-07-06 09:30", content)
            self.assertIn("- 来源：manual", content)
            self.assertIn("- 标签：产品", content)
            self.assertIn("  #产品：OpenClaw 先做好文字笔记。", content)

    def test_append_note_can_require_capture_prefix(self) -> None:
        timestamp = datetime(2026, 7, 6, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "capture prefix"):
                append_note(
                    text="普通聊天，不应该进入笔记。",
                    notes_root=Path(temp_dir),
                    source="feishu",
                    tags=[],
                    timestamp=timestamp,
                    require_prefix=True,
                )


if __name__ == "__main__":
    unittest.main()
