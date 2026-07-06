#!/usr/bin/env python3
"""Collect product-news signals and email a concise daily briefing."""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import os
import re
import smtplib
import ssl
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


DEFAULT_CONFIG = Path("agents/product-news/sources.json")
DEFAULT_ARCHIVE_ROOT = Path("data/product-news")
DEFAULT_ENV_FILE = Path.home() / ".openclaw" / ".env"
DEFAULT_TIMEZONE = "Asia/Shanghai"
USER_AGENT = "OpenClawProductNews/1.0"
ENV_ALIASES = {
    "PRODUCT_NEWS_EMAIL_TO": ("MAIL_TO",),
    "SMTP_HOST": ("QQ_SMTP_HOST",),
    "SMTP_PORT": ("QQ_SMTP_PORT",),
    "SMTP_USER": ("QQ_SMTP_USER",),
    "SMTP_PASSWORD": ("QQ_SMTP_PASS",),
    "PRODUCT_NEWS_TIMEZONE": ("TIMEZONE",),
}


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    category: str
    summary: str
    published_at: datetime | None
    weight: int = 1


@dataclass(frozen=True)
class ScoredNewsItem:
    item: NewsItem
    score: int
    reasons: tuple[str, ...]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def apply_env_aliases() -> None:
    for canonical, aliases in ENV_ALIASES.items():
        if os.environ.get(canonical):
            continue
        for alias in aliases:
            if os.environ.get(alias):
                os.environ[canonical] = os.environ[alias]
                break

    if not os.environ.get("PRODUCT_NEWS_SEARCH_PROVIDER") and os.environ.get("TAVILY_API_KEY"):
        os.environ["PRODUCT_NEWS_SEARCH_PROVIDER"] = "tavily"


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def parse_datetime(value: str | None, timezone: ZoneInfo) -> datetime | None:
    if not value:
        return None

    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        normalized = re.sub(r"\s+", " ", value).strip()
        for date_format in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(normalized, date_format)
                break
            except ValueError:
                parsed = None
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def parse_iso_datetime(value: str | None, timezone: ZoneInfo) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return parse_datetime(value, timezone)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def text_from_element(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    return "" if child is None or child.text is None else child.text.strip()


def atom_text(element: ET.Element, local_name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == local_name and child.text:
            return child.text.strip()
    return ""


def parse_rss_items(
    xml_text: str,
    *,
    source: str,
    category: str,
    weight: int,
    timezone: ZoneInfo,
) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items: list[NewsItem] = []

    for entry in root.findall(".//item"):
        title = text_from_element(entry, "title")
        link = text_from_element(entry, "link")
        summary = strip_markup(text_from_element(entry, "description"))
        published = parse_datetime(
            text_from_element(entry, "pubDate") or text_from_element(entry, "published"),
            timezone,
        )
        if title and link:
            items.append(NewsItem(title, link, source, category, summary, published, weight))

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = atom_text(entry, "title")
        summary = strip_markup(atom_text(entry, "summary") or atom_text(entry, "content"))
        published = parse_iso_datetime(
            atom_text(entry, "published") or atom_text(entry, "updated"),
            timezone,
        )
        link = ""
        for child in entry:
            if child.tag.rsplit("}", 1)[-1] == "link":
                link = child.attrib.get("href", "")
                if link:
                    break
        if title and link:
            items.append(NewsItem(title, link, source, category, summary, published, weight))

    return items


def strip_markup(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def collect_rss(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    items: list[NewsItem] = []
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


def collect_github_releases(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    items: list[NewsItem] = []
    headers = {}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

    for source in config.get("github_releases", []):
        repo = source.get("repo")
        if not repo:
            continue
        url = f"https://api.github.com/repos/{repo}/releases?per_page=5"
        try:
            releases = fetch_json(url, headers=headers)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"warning: failed to collect GitHub releases {repo}: {exc}", file=sys.stderr)
            continue

        for release in releases:
            title = release.get("name") or release.get("tag_name")
            link = release.get("html_url")
            if not title or not link:
                continue
            items.append(
                NewsItem(
                    title=f"{source.get('name', repo)} {title}",
                    url=link,
                    source=f"GitHub: {repo}",
                    category=source.get("category", "open_source"),
                    summary=strip_markup(release.get("body") or ""),
                    published_at=parse_iso_datetime(release.get("published_at"), timezone),
                    weight=int(source.get("weight", 1)),
                )
            )
    return items


def collect_search(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    provider = os.environ.get("PRODUCT_NEWS_SEARCH_PROVIDER", "").lower().strip()
    if provider == "brave" and os.environ.get("BRAVE_SEARCH_API_KEY"):
        return collect_brave_search(config, timezone)
    if provider == "tavily" and os.environ.get("TAVILY_API_KEY"):
        return collect_tavily_search(config, timezone)
    return []


def build_search_queries(config: dict[str, Any]) -> list[str]:
    queries = [str(query) for query in config.get("search_queries", []) if str(query).strip()]
    templates = [str(template) for template in config.get("search_templates", []) if str(template).strip()]

    watched_terms: list[str] = []
    for entity in config.get("watched_entities", []):
        for term in entity.get("terms") or [entity.get("name", "")]:
            if not str(term).strip():
                continue
            watched_terms.append(str(term).strip())

    for template in templates:
        for term in watched_terms:
            queries.append(template.format(term=term))

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = re.sub(r"\s+", " ", query).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)

    max_queries = int(os.environ.get("PRODUCT_NEWS_MAX_SEARCH_QUERIES", config.get("max_search_queries", 30)))
    return deduped[:max_queries]


def collect_brave_search(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    items: list[NewsItem] = []
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
                    NewsItem(
                        title=title,
                        url=link,
                        source=f"Brave Search: {query}",
                        category="search",
                        summary=strip_markup(result.get("description") or ""),
                        published_at=parse_iso_datetime(result.get("page_age"), timezone),
                        weight=1,
                    )
                )
    return items


def collect_tavily_search(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    items: list[NewsItem] = []
    endpoint = "https://api.tavily.com/search"
    for query in build_search_queries(config):
        payload = json.dumps(
            {
                "query": query,
                "topic": "news",
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
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"warning: Tavily search failed for {query}: {exc}", file=sys.stderr)
            continue
        for result in data.get("results", []):
            title = strip_markup(result.get("title") or "")
            link = result.get("url") or ""
            if title and link:
                items.append(
                    NewsItem(
                        title=title,
                        url=link,
                        source=f"Tavily Search: {query}",
                        category="search",
                        summary=strip_markup(result.get("content") or ""),
                        published_at=parse_iso_datetime(result.get("published_date"), timezone),
                        weight=1,
                    )
                )
    return items


def is_recent(item: NewsItem, now: datetime, lookback_hours: int) -> bool:
    if item.published_at is None:
        return True
    return now - timedelta(hours=lookback_hours) <= item.published_at <= now + timedelta(minutes=5)


def score_item(item: NewsItem, keywords: list[str], now: datetime) -> ScoredNewsItem:
    haystack = f"{item.title} {item.summary}".lower()
    score = item.weight
    reasons: list[str] = []

    for keyword in keywords:
        if keyword.lower() in haystack:
            score += 2
            reasons.append(keyword)

    if re.search(r"\b(launch|released|release|announces|introduces|beta|preview|open[- ]source)\b", haystack):
        score += 4
        reasons.append("product-release")

    category_bonus = {
        "tech_giant": 3,
        "open_source": 3,
        "robotics": 4,
        "startup": 3,
        "search": 1,
    }.get(item.category, 0)
    score += category_bonus

    if item.published_at is not None and now - item.published_at <= timedelta(hours=30):
        score += 3
        reasons.append("recent")

    return ScoredNewsItem(item=item, score=score, reasons=tuple(dict.fromkeys(reasons)))


def dedupe_key(item: NewsItem) -> str:
    parsed = urllib.parse.urlparse(item.url)
    path = re.sub(r"/+$", "", parsed.path)
    if parsed.netloc and path:
        return f"{parsed.netloc.lower()}{path.lower()}"
    normalized_title = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
    return normalized_title[:90]


def select_top_items(
    items: list[NewsItem],
    *,
    keywords: list[str],
    now: datetime,
    lookback_hours: int,
    limit: int,
) -> list[ScoredNewsItem]:
    seen: set[str] = set()
    scored: list[ScoredNewsItem] = []
    for item in items:
        if not is_recent(item, now, lookback_hours):
            continue
        key = dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        scored_item = score_item(item, keywords, now)
        if scored_item.score >= 5:
            scored.append(scored_item)

    scored.sort(
        key=lambda scored_item: (
            scored_item.score,
            scored_item.item.published_at or datetime.min.replace(tzinfo=now.tzinfo),
        ),
        reverse=True,
    )
    return scored[:limit]


def one_line(value: str, max_length: int = 220) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "..."


def render_briefing(items: list[ScoredNewsItem], *, run_date: datetime) -> tuple[str, str]:
    date_text = run_date.strftime("%Y-%m-%d")
    subject = f"产品新闻助手日报 - {date_text}"

    lines = [
        f"# {subject}",
        "",
        "## 今日主要发现",
        "",
    ]

    if not items:
        lines.extend(
            [
                "今天没有筛选出足够高置信度的 AI/机器人产品发布信号。",
                "",
                "建议检查新闻源、搜索接口配额和脚本日志。",
            ]
        )
        return subject, "\n".join(lines).strip() + "\n"

    for index, scored in enumerate(items, start=1):
        item = scored.item
        published = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "时间未标注"
        summary = one_line(item.summary) or "来源未提供摘要，建议点开链接确认细节。"
        reasons = ", ".join(scored.reasons[:5]) or "source-weight"
        lines.extend(
            [
                f"{index}. {item.title}",
                f"   - 类型：{item.category}",
                f"   - 来源：{item.source}",
                f"   - 时间：{published}",
                f"   - 发生了什么：{summary}",
                f"   - 为什么重要：匹配 {reasons}，综合评分 {scored.score}。",
                f"   - 链接：{item.url}",
                "",
            ]
        )

    categories = sorted({scored.item.category for scored in items})
    lines.extend(
        [
            "## 趋势观察",
            "",
            f"- 今日高相关信号集中在：{', '.join(categories)}。",
            "- 搜索接口结果仅作为补漏，正式判断优先采用官方源、RSS 和 GitHub Release。",
            "",
            "## 待跟进",
            "",
            "- 对搜索来源和无发布时间来源保持低置信度，必要时人工打开原文确认。",
        ]
    )
    return subject, "\n".join(lines).strip() + "\n"


def send_email(subject: str, body: str) -> None:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "PRODUCT_NEWS_EMAIL_TO"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"missing required email environment variables: {', '.join(missing)}")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ.get("PRODUCT_NEWS_EMAIL_FROM", os.environ["SMTP_USER"])
    message["To"] = os.environ["PRODUCT_NEWS_EMAIL_TO"]
    message.set_content(body)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def archive_briefing(body: str, archive_root: Path, run_date: datetime) -> Path:
    path = archive_root / f"{run_date.strftime('%Y-%m-%d')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def collect_items(config: dict[str, Any], timezone: ZoneInfo) -> list[NewsItem]:
    items: list[NewsItem] = []
    items.extend(collect_rss(config, timezone))
    items.extend(collect_github_releases(config, timezone))
    items.extend(collect_search(config, timezone))
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send the daily product-news briefing.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to product-news sources JSON.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to .env file with SMTP/search secrets.")
    parser.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT), help="Directory for Markdown archives.")
    parser.add_argument("--lookback-hours", type=int, default=30, help="Only include recent items inside this window.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum findings to include.")
    parser.add_argument("--dry-run", action="store_true", help="Print briefing and do not send email.")
    parser.add_argument("--no-email", action="store_true", help="Archive briefing without sending email.")
    parser.add_argument("--timezone", help="IANA timezone for the run date and schedule expectation.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(Path(args.env_file))
    apply_env_aliases()
    timezone = ZoneInfo(args.timezone or os.environ.get("PRODUCT_NEWS_TIMEZONE", DEFAULT_TIMEZONE))
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
        print(f"Sent briefing to {os.environ.get('PRODUCT_NEWS_EMAIL_TO')}")
    print(f"Archived briefing to {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
