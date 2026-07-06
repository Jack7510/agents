#!/usr/bin/env python3
"""Collect technical-paper signals and email a concise daily briefing."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from . import briefing_utils as utils
    from . import qq_mail_tool
except ImportError:  # pragma: no cover - supports `python scripts/send_tech_papers.py`.
    import briefing_utils as utils
    import qq_mail_tool


DEFAULT_CONFIG = Path("agents/tech-papers/sources.json")
DEFAULT_ARCHIVE_ROOT = Path("data/tech-papers")
DEFAULT_ENV_FILE = Path.home() / ".openclaw" / ".env"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_EMAIL_TO = "13827420406@qq.com"
USER_AGENT = "OpenClawTechPapers/1.0"
ENV_ALIASES = {
    "TECH_PAPERS_EMAIL_TO": ("MAIL_TO", "PRODUCT_NEWS_EMAIL_TO"),
    "SMTP_HOST": ("QQ_SMTP_HOST",),
    "SMTP_PORT": ("QQ_SMTP_PORT",),
    "SMTP_USER": ("QQ_SMTP_USER",),
    "SMTP_PASSWORD": ("QQ_SMTP_PASS",),
    "TECH_PAPERS_TIMEZONE": ("TIMEZONE", "PRODUCT_NEWS_TIMEZONE"),
}


@dataclass(frozen=True)
class PaperItem:
    title: str
    url: str
    source: str
    category: str
    summary: str
    published_at: datetime | None
    authors: str = ""
    pdf_url: str = ""
    code_url: str = ""
    weight: int = 1


@dataclass(frozen=True)
class ScoredPaperItem:
    item: PaperItem
    score: int
    reasons: tuple[str, ...]


load_env_file = utils.load_env_file
load_config = utils.load_config
parse_datetime = utils.parse_datetime
strip_markup = utils.strip_markup
atom_text = utils.atom_text
text_from_element = utils.text_from_element
one_line = utils.one_line
linkify_text = utils.linkify_text
render_email_html = utils.render_email_html
archive_briefing = utils.archive_briefing


def apply_env_aliases() -> None:
    utils.apply_env_aliases(ENV_ALIASES)

    if not os.environ.get("TECH_PAPERS_EMAIL_TO"):
        os.environ["TECH_PAPERS_EMAIL_TO"] = DEFAULT_EMAIL_TO


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return utils.fetch_json(url, user_agent=USER_AGENT, timeout=25, headers=headers)


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    return utils.fetch_text(url, user_agent=USER_AGENT, timeout=25, headers=headers)


def parse_arxiv_items(
    xml_text: str,
    *,
    source: str,
    category: str,
    weight: int,
    timezone: ZoneInfo,
) -> list[PaperItem]:
    root = ET.fromstring(xml_text)
    items: list[PaperItem] = []

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = re.sub(r"\s+", " ", atom_text(entry, "title")).strip()
        summary = strip_markup(atom_text(entry, "summary"))
        published = parse_datetime(atom_text(entry, "published") or atom_text(entry, "updated"), timezone)
        authors = ", ".join(
            atom_text(author, "name")
            for author in entry.findall("{http://www.w3.org/2005/Atom}author")
            if atom_text(author, "name")
        )
        link = atom_text(entry, "id")
        pdf_url = ""
        for child in entry:
            if child.tag.rsplit("}", 1)[-1] != "link":
                continue
            href = child.attrib.get("href", "")
            if child.attrib.get("title") == "pdf" or child.attrib.get("type") == "application/pdf":
                pdf_url = href
            elif not link and href:
                link = href
        if title and link:
            items.append(PaperItem(title, link, source, category, summary, published, authors, pdf_url, weight=weight))

    return items


def parse_rss_items(
    xml_text: str,
    *,
    source: str,
    category: str,
    weight: int,
    timezone: ZoneInfo,
) -> list[PaperItem]:
    return utils.parse_rss_items(
        xml_text,
        source=source,
        category=category,
        weight=weight,
        timezone=timezone,
        item_factory=PaperItem,
    )


def collect_arxiv(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    items: list[PaperItem] = []
    endpoint = "https://export.arxiv.org/api/query"
    for source in config.get("arxiv", []):
        query = source.get("query")
        if not query:
            continue
        params = urllib.parse.urlencode(
            {
                "search_query": query,
                "start": "0",
                "max_results": str(source.get("max_results", 40)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        try:
            xml_text = fetch_text(f"{endpoint}?{params}")
            items.extend(
                parse_arxiv_items(
                    xml_text,
                    source=source.get("name", "arXiv"),
                    category=source.get("category", "paper"),
                    weight=int(source.get("weight", 1)),
                    timezone=timezone,
                )
            )
        except (ET.ParseError, KeyError, OSError, urllib.error.URLError) as exc:
            print(f"warning: failed to collect arXiv source {source.get('name')}: {exc}", file=sys.stderr)
    return items


def collect_rss(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    items: list[PaperItem] = []
    for source in config.get("rss", []):
        try:
            xml_text = fetch_text(source["url"])
            items.extend(
                parse_rss_items(
                    xml_text,
                    source=source["name"],
                    category=source.get("category", "rss"),
                    weight=int(source.get("weight", 1)),
                    timezone=timezone,
                )
            )
        except (ET.ParseError, KeyError, OSError, urllib.error.URLError) as exc:
            print(f"warning: failed to collect RSS source {source.get('name')}: {exc}", file=sys.stderr)
    return items


def build_search_queries(config: dict[str, Any]) -> list[str]:
    return utils.build_search_queries(
        config,
        watched_key="watched_topics",
        max_queries_env="TECH_PAPERS_MAX_SEARCH_QUERIES",
        default_max_queries=20,
    )


def collect_search(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    provider = os.environ.get("TECH_PAPERS_SEARCH_PROVIDER", "").lower().strip()
    if provider == "brave" and os.environ.get("BRAVE_SEARCH_API_KEY"):
        return collect_brave_search(config, timezone)
    if provider == "tavily" and os.environ.get("TAVILY_API_KEY"):
        return collect_tavily_search(config, timezone)
    return []


def collect_brave_search(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    items: list[PaperItem] = []
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"],
    }
    for query in build_search_queries(config):
        params = urllib.parse.urlencode({"q": query, "count": "5", "freshness": "pd"})
        try:
            data = fetch_json(f"https://api.search.brave.com/res/v1/web/search?{params}", headers=headers)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"warning: Brave search failed for {query}: {exc}", file=sys.stderr)
            continue
        for result in data.get("web", {}).get("results", []):
            title = strip_markup(result.get("title") or "")
            link = result.get("url") or ""
            if title and link:
                items.append(
                    PaperItem(
                        title=title,
                        url=link,
                        source=f"Brave Search: {query}",
                        category="search",
                        summary=strip_markup(result.get("description") or ""),
                        published_at=parse_datetime(result.get("page_age"), timezone),
                        weight=1,
                    )
                )
    return items


def collect_tavily_search(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    items: list[PaperItem] = []
    endpoint = "https://api.tavily.com/search"
    for query in build_search_queries(config):
        payload = json.dumps(
            {
                "query": query,
                "topic": "general",
                "search_depth": "basic",
                "max_results": 5,
                "time_range": "day",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"warning: Tavily search failed for {query}: {exc}", file=sys.stderr)
            continue
        for result in data.get("results", []):
            title = strip_markup(result.get("title") or "")
            link = result.get("url") or ""
            if title and link:
                items.append(
                    PaperItem(
                        title=title,
                        url=link,
                        source=f"Tavily Search: {query}",
                        category="search",
                        summary=strip_markup(result.get("content") or ""),
                        published_at=parse_datetime(result.get("published_date"), timezone),
                        weight=1,
                    )
                )
    return items


def is_recent(item: PaperItem, now: datetime, lookback_hours: int) -> bool:
    return utils.is_recent(item, now, lookback_hours)


def score_item(item: PaperItem, keywords: list[str], now: datetime) -> ScoredPaperItem:
    haystack = f"{item.title} {item.summary} {item.authors}".lower()
    score = item.weight
    reasons: list[str] = []

    for keyword in keywords:
        if keyword.lower() in haystack:
            score += 2
            reasons.append(keyword)

    if re.search(r"\b(code|github|project page|dataset|benchmark|model|checkpoint|open[- ]source)\b", haystack):
        score += 3
        reasons.append("reproducibility")

    if re.search(r"\b(reasoning|agent|robot|robotics|embodied|humanoid|multimodal|vla|inference|post[- ]training)\b", haystack):
        score += 4
        reasons.append("core-topic")

    category_bonus = {
        "llm": 4,
        "robotics": 4,
        "multimodal": 3,
        "agent": 3,
        "systems": 3,
        "hf_papers": 3,
        "conference": 3,
        "search": 1,
    }.get(item.category, 1)
    score += category_bonus

    if item.published_at is not None and now - item.published_at <= timedelta(hours=48):
        score += 3
        reasons.append("recent")

    return ScoredPaperItem(item=item, score=score, reasons=tuple(dict.fromkeys(reasons)))


def dedupe_key(item: PaperItem) -> str:
    arxiv_match = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9.]+)", item.url)
    if arxiv_match:
        return f"arxiv:{arxiv_match.group(1)}"

    parsed = urllib.parse.urlparse(item.url)
    path = re.sub(r"/+$", "", parsed.path)
    if parsed.netloc and path:
        return f"{parsed.netloc.lower()}{path.lower()}"
    normalized_title = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
    return normalized_title[:100]


def select_top_items(
    items: list[PaperItem],
    *,
    keywords: list[str],
    now: datetime,
    lookback_hours: int,
    limit: int,
) -> list[ScoredPaperItem]:
    return utils.select_top_items(
        items,
        keywords=keywords,
        now=now,
        lookback_hours=lookback_hours,
        limit=limit,
        min_score=6,
        dedupe_key=dedupe_key,
        score_item=score_item,
        score_value=lambda scored: scored.score,
        published_at=lambda scored: scored.item.published_at,
    )


def render_briefing(items: list[ScoredPaperItem], *, run_date: datetime) -> tuple[str, str]:
    date_text = run_date.strftime("%Y-%m-%d")
    subject = f"技术论文助手日报 - {date_text}"

    lines = [
        f"# {subject}",
        "",
        "## 今日主要发现",
        "",
    ]

    if not items:
        lines.extend(
            [
                "今天没有筛选出足够高置信度的大模型/机器人技术论文信号。",
                "",
                "建议检查 arXiv、RSS、搜索接口配额和脚本日志。",
            ]
        )
        return subject, "\n".join(lines).strip() + "\n"

    for index, scored in enumerate(items, start=1):
        item = scored.item
        published = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "时间未标注"
        summary = one_line(item.summary) or "来源未提供摘要，建议点开链接确认论文贡献。"
        reasons = ", ".join(scored.reasons[:5]) or "source-weight"
        links = item.url
        if item.pdf_url and item.pdf_url != item.url:
            links = f"{links} ; PDF: {item.pdf_url}"
        if item.code_url:
            links = f"{links} ; Code: {item.code_url}"
        lines.extend(
            [
                f"{index}. {item.title}",
                f"   - 类型：{item.category}",
                f"   - 来源：{item.source}",
                f"   - 时间：{published}",
                f"   - 发生了什么：{summary}",
                f"   - 为什么重要：匹配 {reasons}，综合评分 {scored.score}。",
                f"   - 链接：{links}",
                "",
            ]
        )
        if item.authors:
            lines.insert(-1, f"   - 作者：{one_line(item.authors, 180)}")

    categories = sorted({scored.item.category for scored in items})
    lines.extend(
        [
            "## 趋势观察",
            "",
            f"- 今日高相关论文集中在：{', '.join(categories)}。",
            "- 搜索接口结果仅作为补漏，正式判断优先采用 arXiv、会议页面、官方项目页和论文元数据。",
            "",
            "## 待跟进",
            "",
            "- 对搜索来源、无摘要来源和无代码论文保持低置信度，必要时人工打开原文确认。",
        ]
    )
    return subject, "\n".join(lines).strip() + "\n"


def build_email_message(subject: str, body: str) -> EmailMessage:
    return qq_mail_tool.build_email_message(
        subject=subject,
        body=body,
        from_addr=qq_mail_tool.resolve_sender(env_key="TECH_PAPERS_EMAIL_FROM"),
        to=qq_mail_tool.resolve_recipient(env_key="TECH_PAPERS_EMAIL_TO"),
        html_body=render_email_html(body, subject),
    )


def send_email(subject: str, body: str) -> None:
    qq_mail_tool.send_email(
        subject=subject,
        body=body,
        to_env_key="TECH_PAPERS_EMAIL_TO",
        from_env_key="TECH_PAPERS_EMAIL_FROM",
        html_body=render_email_html(body, subject),
    )


def collect_items(config: dict[str, Any], timezone: ZoneInfo) -> list[PaperItem]:
    items: list[PaperItem] = []
    items.extend(collect_arxiv(config, timezone))
    items.extend(collect_rss(config, timezone))
    items.extend(collect_search(config, timezone))
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send the daily technical-paper briefing.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to technical-paper sources JSON.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to .env file with SMTP/search secrets.")
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT), help="Directory for Markdown archives.")
    parser.add_argument("--lookback-hours", type=int, default=120, help="Only include recent items inside this window.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum findings to include.")
    parser.add_argument("--dry-run", action="store_true", help="Print briefing and do not send email.")
    parser.add_argument("--no-email", action="store_true", help="Archive briefing without sending email.")
    parser.add_argument("--timezone", help="IANA timezone for the run date and schedule expectation.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(Path(args.env_file))
    apply_env_aliases()
    timezone = ZoneInfo(args.timezone or os.environ.get("TECH_PAPERS_TIMEZONE", DEFAULT_TIMEZONE))
    now = datetime.now(timezone)

    config = load_config(Path(args.config))
    items = collect_items(config, timezone)
    selected = select_top_items(
        items,
        keywords=list(config.get("keywords", [])),
        now=now,
        lookback_hours=args.lookback_hours,
        limit=args.limit,
    )
    subject, body = render_briefing(selected, run_date=now)
    archive_path = archive_briefing(body, Path(args.archive_root), now)

    if args.dry_run:
        print(body)
        print(textwrap.dedent(f"\nDry run complete. Archived to {archive_path}").strip())
        return 0

    if not args.no_email:
        send_email(subject, body)
        print(f"Sent briefing to {os.environ.get('TECH_PAPERS_EMAIL_TO')}")
    print(f"Archived briefing to {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
