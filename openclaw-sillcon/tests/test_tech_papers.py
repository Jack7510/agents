from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.send_tech_papers import (
    DEFAULT_EMAIL_TO,
    PaperItem,
    apply_env_aliases,
    archive_briefing,
    build_email_message,
    build_search_queries,
    dedupe_key,
    parse_arxiv_items,
    render_briefing,
    render_email_html,
    score_item,
    select_top_items,
)


class TechPapersTests(unittest.TestCase):
    def test_parse_arxiv_items_reads_atom_feed(self) -> None:
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>https://arxiv.org/abs/2607.00001</id>
            <updated>2026-07-06T02:00:00Z</updated>
            <published>2026-07-06T02:00:00Z</published>
            <title>Reasoning Agents for Robot Manipulation</title>
            <summary>We introduce a large language model agent for embodied AI.</summary>
            <author><name>Ada Lovelace</name></author>
            <author><name>Alan Turing</name></author>
            <link href="https://arxiv.org/pdf/2607.00001" title="pdf" type="application/pdf" />
          </entry>
        </feed>
        """

        items = parse_arxiv_items(
            xml,
            source="arXiv Robotics",
            category="robotics",
            weight=5,
            timezone=ZoneInfo("Asia/Shanghai"),
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Reasoning Agents for Robot Manipulation")
        self.assertEqual(items[0].authors, "Ada Lovelace, Alan Turing")
        self.assertEqual(items[0].pdf_url, "https://arxiv.org/pdf/2607.00001")
        self.assertEqual(items[0].published_at.hour, 10)

    def test_score_item_rewards_core_paper_topics(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        item = PaperItem(
            title="Large language model reasoning for embodied robot agents",
            url="https://arxiv.org/abs/2607.00001",
            source="arXiv",
            category="robotics",
            summary="The paper includes a GitHub project page and robot manipulation benchmark.",
            published_at=now - timedelta(hours=1),
            weight=5,
        )

        scored = score_item(item, ["large language model", "robot", "agent"], now)

        self.assertGreaterEqual(scored.score, 20)
        self.assertIn("core-topic", scored.reasons)
        self.assertIn("reproducibility", scored.reasons)

    def test_select_top_items_dedupes_arxiv_links(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        first = PaperItem(
            "LLM robot reasoning",
            "https://arxiv.org/abs/2607.00001",
            "arXiv",
            "robotics",
            "robot agent reasoning",
            now - timedelta(hours=2),
            weight=5,
        )
        duplicate = PaperItem(
            "LLM robot reasoning PDF",
            "https://arxiv.org/pdf/2607.00001",
            "Search",
            "search",
            "robot agent reasoning code",
            now - timedelta(hours=1),
            weight=1,
        )

        selected = select_top_items(
            [first, duplicate],
            keywords=["LLM", "robot", "reasoning"],
            now=now,
            lookback_hours=48,
            limit=5,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(dedupe_key(first), dedupe_key(duplicate))

    def test_render_briefing_matches_product_news_style(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        item = PaperItem(
            "Reasoning Agents for Robot Manipulation",
            "https://arxiv.org/abs/2607.00001",
            "arXiv Robotics",
            "robotics",
            "A large language model agent improves robot manipulation.",
            now,
            authors="Ada Lovelace",
            pdf_url="https://arxiv.org/pdf/2607.00001",
            weight=5,
        )
        scored = score_item(item, ["large language model", "robot", "agent"], now)

        subject, body = render_briefing([scored], run_date=now)

        self.assertEqual(subject, "技术论文助手日报 - 2026-07-06")
        self.assertIn("## 今日主要发现", body)
        self.assertIn("   - 类型：robotics", body)
        self.assertIn("   - 发生了什么：", body)
        self.assertIn("   - 为什么重要：", body)
        self.assertIn("## 趋势观察", body)

    def test_render_email_html_formats_markdown_briefing(self) -> None:
        html = render_email_html(
            "\n".join(
                [
                    "# 技术论文助手日报 - 2026-07-06",
                    "",
                    "## 今日主要发现",
                    "",
                    "1. Reasoning Agents",
                    "   - 类型：robotics",
                    "   - 链接：https://arxiv.org/abs/2607.00001",
                ]
            ),
            "技术论文助手日报 - 2026-07-06",
        )

        self.assertIn("<h1>技术论文助手日报 - 2026-07-06</h1>", html)
        self.assertIn('<section class="finding">', html)
        self.assertIn('<span class="label">类型</span>', html)
        self.assertIn('<a href="https://arxiv.org/abs/2607.00001">https://arxiv.org/abs/2607.00001</a>', html)

    def test_build_email_message_uses_default_recipient(self) -> None:
        os.environ["SMTP_USER"] = "sender@example.com"
        for key in ("TECH_PAPERS_EMAIL_TO", "MAIL_TO"):
            os.environ.pop(key, None)
        try:
            apply_env_aliases()
            message = build_email_message("技术论文助手日报 - 2026-07-06", "# 标题\n")

            self.assertEqual(os.environ["TECH_PAPERS_EMAIL_TO"], DEFAULT_EMAIL_TO)
            self.assertEqual(message["To"], DEFAULT_EMAIL_TO)
            self.assertTrue(message.is_multipart())
        finally:
            os.environ.pop("SMTP_USER", None)
            os.environ.pop("TECH_PAPERS_EMAIL_TO", None)

    def test_archive_briefing_writes_date_file(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = archive_briefing("hello", Path(temp_dir), now)

            self.assertEqual(path, Path(temp_dir) / "2026-07-06.md")
            self.assertEqual(path.read_text(encoding="utf-8"), "hello")

    def test_build_search_queries_expands_watched_topics(self) -> None:
        queries = build_search_queries(
            {
                "max_search_queries": 10,
                "search_queries": ["LLM paper code", "LLM paper code"],
                "search_templates": ["{term} arXiv paper code"],
                "watched_topics": [{"name": "Robotics", "terms": ["embodied AI", "humanoid robot"]}],
            }
        )

        self.assertEqual(queries[0], "LLM paper code")
        self.assertIn("embodied AI arXiv paper code", queries)
        self.assertIn("humanoid robot arXiv paper code", queries)
        self.assertEqual(queries.count("LLM paper code"), 1)


if __name__ == "__main__":
    unittest.main()
