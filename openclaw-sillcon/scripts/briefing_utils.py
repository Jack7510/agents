from __future__ import annotations

import email.utils
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar
from zoneinfo import ZoneInfo


class BriefingItem(Protocol):
    title: str
    url: str
    summary: str
    published_at: datetime | None
    weight: int


ScoredItemT = TypeVar("ScoredItemT")
ItemT = TypeVar("ItemT", bound=BriefingItem)


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


def apply_env_aliases(aliases: dict[str, tuple[str, ...]]) -> None:
    for canonical, alias_names in aliases.items():
        if os.environ.get(canonical):
            continue
        for alias in alias_names:
            if os.environ.get(alias):
                os.environ[canonical] = os.environ[alias]
                break


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
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
            for date_format in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(normalized, date_format)
                    break
                except ValueError:
                    parsed = None
            if parsed is None:
                return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def fetch_json(url: str, *, user_agent: str, timeout: int, headers: dict[str, str] | None = None) -> Any:
    request_headers = {"User-Agent": user_agent, **(headers or {})}
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, *, user_agent: str, timeout: int, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": user_agent, **(headers or {})}
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def strip_markup(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


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
    item_factory: Callable[..., ItemT],
) -> list[ItemT]:
    root = ET.fromstring(xml_text)
    items: list[ItemT] = []

    for entry in root.findall(".//item"):
        title = text_from_element(entry, "title")
        link = text_from_element(entry, "link")
        summary = strip_markup(text_from_element(entry, "description"))
        published = parse_datetime(text_from_element(entry, "pubDate") or text_from_element(entry, "published"), timezone)
        if title and link:
            items.append(item_factory(title, link, source, category, summary, published, weight=weight))

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = re.sub(r"\s+", " ", atom_text(entry, "title")).strip()
        summary = strip_markup(atom_text(entry, "summary") or atom_text(entry, "content"))
        published = parse_datetime(atom_text(entry, "published") or atom_text(entry, "updated"), timezone)
        link = ""
        for child in entry:
            if child.tag.rsplit("}", 1)[-1] == "link":
                link = child.attrib.get("href", "")
                if link:
                    break
        if title and link:
            items.append(item_factory(title, link, source, category, summary, published, weight=weight))

    return items


def build_search_queries(
    config: dict[str, Any],
    *,
    watched_key: str,
    max_queries_env: str,
    default_max_queries: int,
) -> list[str]:
    queries = [str(query) for query in config.get("search_queries", []) if str(query).strip()]
    templates = [str(template) for template in config.get("search_templates", []) if str(template).strip()]

    watched_terms: list[str] = []
    for item in config.get(watched_key, []):
        for term in item.get("terms") or [item.get("name", "")]:
            if str(term).strip():
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

    max_queries = int(os.environ.get(max_queries_env, config.get("max_search_queries", default_max_queries)))
    return deduped[:max_queries]


def is_recent(item: BriefingItem, now: datetime, lookback_hours: int) -> bool:
    if item.published_at is None:
        return True
    return now - timedelta(hours=lookback_hours) <= item.published_at <= now + timedelta(minutes=5)


def select_top_items(
    items: list[ItemT],
    *,
    keywords: list[str],
    now: datetime,
    lookback_hours: int,
    limit: int,
    min_score: int,
    dedupe_key: Callable[[ItemT], str],
    score_item: Callable[[ItemT, list[str], datetime], ScoredItemT],
    score_value: Callable[[ScoredItemT], int],
    published_at: Callable[[ScoredItemT], datetime | None],
) -> list[ScoredItemT]:
    seen: set[str] = set()
    scored: list[ScoredItemT] = []
    for item in items:
        if not is_recent(item, now, lookback_hours):
            continue
        key = dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        scored_item = score_item(item, keywords, now)
        if score_value(scored_item) >= min_score:
            scored.append(scored_item)

    scored.sort(
        key=lambda scored_item: (
            score_value(scored_item),
            published_at(scored_item) or datetime.min.replace(tzinfo=now.tzinfo),
        ),
        reverse=True,
    )
    return scored[:limit]


def one_line(value: str, max_length: int = 220) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "..."


URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")


def linkify_text(value: str) -> str:
    parts: list[str] = []
    position = 0
    for match in URL_PATTERN.finditer(value):
        parts.append(html.escape(value[position : match.start()]))
        url = match.group(0)
        escaped_url = html.escape(url, quote=True)
        parts.append(f'<a href="{escaped_url}">{html.escape(url)}</a>')
        position = match.end()
    parts.append(html.escape(value[position:]))
    return "".join(parts)


def render_email_html(markdown_body: str, subject: str) -> str:
    content: list[str] = []
    in_finding = False

    for raw_line in markdown_body.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith("# "):
            content.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
            continue

        if line.startswith("## "):
            if in_finding:
                content.append("</section>")
                in_finding = False
            content.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            continue

        finding_match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if finding_match:
            if in_finding:
                content.append("</section>")
            in_finding = True
            number, title = finding_match.groups()
            content.append(
                '<section class="finding">'
                f'<h3><span class="rank">{html.escape(number)}</span>{html.escape(title)}</h3>'
            )
            continue

        field_match = re.match(r"^\s*-\s*([^：:]+)[：:]\s*(.*)$", line)
        if field_match:
            label, value = field_match.groups()
            content.append(
                '<div class="field">'
                f'<span class="label">{html.escape(label.strip())}</span>'
                f'<span class="value">{linkify_text(value.strip())}</span>'
                "</div>"
            )
            continue

        bullet_match = re.match(r"^\s*-\s+(.+)$", line)
        if bullet_match:
            content.append(f'<p class="bullet">{linkify_text(bullet_match.group(1).strip())}</p>')
            continue

        content.append(f"<p>{linkify_text(line.strip())}</p>")

    if in_finding:
        content.append("</section>")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
  <style>
    body {{ margin: 0; padding: 0; background: #f5f7fb; color: #1f2937; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.58; }}
    .wrap {{ max-width: 760px; margin: 0 auto; padding: 28px 18px 36px; }}
    .panel {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 28px; }}
    h1 {{ margin: 0 0 22px; font-size: 24px; line-height: 1.3; color: #111827; }}
    h2 {{ margin: 26px 0 14px; padding-bottom: 8px; border-bottom: 1px solid #e5e7eb; font-size: 18px; color: #111827; }}
    .finding {{ margin: 14px 0; padding: 16px 18px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fbfdff; }}
    h3 {{ margin: 0 0 12px; font-size: 17px; line-height: 1.45; color: #111827; }}
    .rank {{ display: inline-block; min-width: 24px; height: 24px; margin-right: 8px; border-radius: 999px; background: #1f6feb; color: #ffffff; font-size: 13px; line-height: 24px; text-align: center; vertical-align: 1px; }}
    .field {{ margin: 7px 0; font-size: 14px; }}
    .label {{ display: inline-block; min-width: 88px; color: #4b5563; font-weight: 700; }}
    .value {{ color: #1f2937; }}
    p {{ margin: 8px 0; font-size: 14px; }}
    .bullet::before {{ content: "•"; margin-right: 8px; color: #1f6feb; }}
    a {{ color: #1f6feb; text-decoration: none; word-break: break-all; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      {''.join(content)}
    </div>
  </div>
</body>
</html>
"""


def archive_briefing(body: str, archive_root: Path, run_date: datetime) -> Path:
    path = archive_root / f"{run_date.strftime('%Y-%m-%d')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path
