from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.send_product_news import (
    NewsItem,
    apply_env_aliases,
    archive_briefing,
    build_email_message,
    build_search_queries,
    dedupe_key,
    load_env_file,
    parse_rss_items,
    parse_datetime,
    render_briefing,
    render_email_html,
    score_item,
    select_top_items,
)


class ProductNewsTests(unittest.TestCase):
    def test_parse_rss_items_reads_basic_feed(self) -> None:
        xml = """<?xml version="1.0"?>
        <rss><channel><item>
          <title>Acme launches AI robot arm</title>
          <link>https://example.com/robot-arm</link>
          <description><![CDATA[New embodied AI product for factories.]]></description>
          <pubDate>Mon, 06 Jul 2026 02:00:00 +0800</pubDate>
        </item></channel></rss>
        """

        items = parse_rss_items(
            xml,
            source="Example",
            category="startup",
            weight=3,
            timezone=ZoneInfo("Asia/Shanghai"),
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Acme launches AI robot arm")
        self.assertEqual(items[0].source, "Example")
        self.assertEqual(items[0].published_at.hour, 2)

    def test_score_item_rewards_product_release_keywords(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        item = NewsItem(
            title="Startup launches open source AI agent",
            url="https://example.com/a",
            source="Example",
            category="startup",
            summary="A new developer tool was released today.",
            published_at=now - timedelta(hours=1),
            weight=2,
        )

        scored = score_item(item, ["AI", "agent", "robotics"], now)

        self.assertGreaterEqual(scored.score, 14)
        self.assertIn("AI", scored.reasons)
        self.assertIn("product-release", scored.reasons)

    def test_parse_datetime_accepts_common_chinese_feed_format(self) -> None:
        parsed = parse_datetime("2026-07-06 08:02:20  +0800", ZoneInfo("Asia/Shanghai"))

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.hour, 8)

    def test_select_top_items_dedupes_urls_and_filters_old_items(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        recent = NewsItem(
            "AI robot released",
            "https://example.com/news/",
            "A",
            "robotics",
            "robotics launch",
            now - timedelta(hours=2),
            3,
        )
        duplicate = NewsItem(
            "AI robot released duplicate",
            "https://example.com/news",
            "B",
            "robotics",
            "robotics launch",
            now - timedelta(hours=1),
            3,
        )
        old = NewsItem(
            "Old AI launch",
            "https://example.com/old",
            "A",
            "startup",
            "AI launch",
            now - timedelta(days=5),
            5,
        )

        selected = select_top_items(
            [recent, duplicate, old],
            keywords=["AI", "robotics"],
            now=now,
            lookback_hours=30,
            limit=5,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(dedupe_key(recent), dedupe_key(duplicate))

    def test_render_briefing_includes_email_sections(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        item = NewsItem(
            "Open source AI release",
            "https://example.com/release",
            "GitHub",
            "open_source",
            "A useful AI tool release.",
            now,
            3,
        )
        scored = score_item(item, ["AI", "release"], now)

        subject, body = render_briefing([scored], run_date=now)

        self.assertEqual(subject, "产品新闻助手日报 - 2026-07-06")
        self.assertIn("## 今日主要发现", body)
        self.assertIn("Open source AI release", body)
        self.assertIn("## 趋势观察", body)

    def test_render_briefing_accepts_custom_report_name(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

        subject, body = render_briefing(
            [],
            run_date=now,
            briefing={
                "report_name": "OpenClaw 战略信息简报",
                "findings_heading": "关键战略信号",
                "no_items_message": "本轮没有筛选出足够高置信度的战略观点信号。",
            },
        )

        self.assertEqual(subject, "OpenClaw 战略信息简报 - 2026-07-06")
        self.assertIn("## 关键战略信号", body)
        self.assertIn("战略观点信号", body)

    def test_render_email_html_formats_markdown_briefing(self) -> None:
        html = render_email_html(
            "\n".join(
                [
                    "# 产品新闻助手日报 - 2026-07-06",
                    "",
                    "## 今日主要发现",
                    "",
                    "1. Open source AI release",
                    "   - 类型：open_source",
                    "   - 链接：https://example.com/release",
                    "",
                    "## 趋势观察",
                    "",
                    "- 今日高相关信号集中在：open_source。",
                ]
            ),
            "产品新闻助手日报 - 2026-07-06",
        )

        self.assertIn("<h1>产品新闻助手日报 - 2026-07-06</h1>", html)
        self.assertIn('<section class="finding">', html)
        self.assertIn('<span class="label">类型</span>', html)
        self.assertIn('<a href="https://example.com/release">https://example.com/release</a>', html)

    def test_build_email_message_is_multipart_with_html_alternative(self) -> None:
        import os

        os.environ["SMTP_USER"] = "sender@example.com"
        os.environ["PRODUCT_NEWS_EMAIL_TO"] = "daily@example.com"
        try:
            message = build_email_message("产品新闻助手日报 - 2026-07-06", "# 标题\n")

            self.assertTrue(message.is_multipart())
            self.assertEqual(message.get_content_type(), "multipart/alternative")
            self.assertIsNotNone(message.get_body(("plain",)))
            html_part = message.get_body(("html",))
            self.assertIsNotNone(html_part)
            self.assertIn("<h1>标题</h1>", html_part.get_content())
        finally:
            os.environ.pop("SMTP_USER", None)
            os.environ.pop("PRODUCT_NEWS_EMAIL_TO", None)

    def test_archive_briefing_writes_date_file(self) -> None:
        now = datetime(2026, 7, 6, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = archive_briefing("hello", Path(temp_dir), now)

            self.assertEqual(path, Path(temp_dir) / "2026-07-06.md")
            self.assertEqual(path.read_text(encoding="utf-8"), "hello")

    def test_load_env_file_does_not_override_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".env"
            path.write_text("PRODUCT_NEWS_EMAIL_TO=one@example.com\n", encoding="utf-8")
            import os

            os.environ["PRODUCT_NEWS_EMAIL_TO"] = "two@example.com"
            try:
                load_env_file(path)
                self.assertEqual(os.environ["PRODUCT_NEWS_EMAIL_TO"], "two@example.com")
            finally:
                os.environ.pop("PRODUCT_NEWS_EMAIL_TO", None)

    def test_apply_env_aliases_maps_existing_host_names(self) -> None:
        import os

        os.environ["MAIL_TO"] = "daily@example.com"
        os.environ["QQ_SMTP_HOST"] = "smtp.qq.com"
        os.environ["TAVILY_API_KEY"] = "tvly-example"
        for key in ("PRODUCT_NEWS_EMAIL_TO", "SMTP_HOST", "PRODUCT_NEWS_SEARCH_PROVIDER"):
            os.environ.pop(key, None)
        try:
            apply_env_aliases()
            self.assertEqual(os.environ["PRODUCT_NEWS_EMAIL_TO"], "daily@example.com")
            self.assertEqual(os.environ["SMTP_HOST"], "smtp.qq.com")
            self.assertEqual(os.environ["PRODUCT_NEWS_SEARCH_PROVIDER"], "tavily")
        finally:
            for key in (
                "MAIL_TO",
                "QQ_SMTP_HOST",
                "TAVILY_API_KEY",
                "PRODUCT_NEWS_EMAIL_TO",
                "SMTP_HOST",
                "PRODUCT_NEWS_SEARCH_PROVIDER",
            ):
                os.environ.pop(key, None)

    def test_build_search_queries_expands_watched_entities(self) -> None:
        queries = build_search_queries(
            {
                "max_search_queries": 10,
                "search_queries": ["AI product launch", "AI product launch"],
                "search_templates": ["{term} 产品 发布", "{term} product release"],
                "watched_entities": [
                    {"name": "优必选", "terms": ["优必选", "UBTECH"]},
                ],
            }
        )

        self.assertEqual(queries[0], "AI product launch")
        self.assertIn("优必选 产品 发布", queries)
        self.assertIn("UBTECH product release", queries)
        self.assertEqual(queries.count("AI product launch"), 1)

    def test_build_search_queries_respects_max_search_queries(self) -> None:
        queries = build_search_queries(
            {
                "max_search_queries": 2,
                "search_queries": ["one", "two", "three"],
                "search_templates": ["{term} product release"],
                "watched_entities": [{"name": "Hugging Face", "terms": ["Hugging Face"]}],
            }
        )

        self.assertEqual(queries, ["one", "two"])


if __name__ == "__main__":
    unittest.main()
