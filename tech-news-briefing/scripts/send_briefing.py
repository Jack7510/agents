#!/usr/bin/env python3
"""Send a Markdown briefing through QQ Mail SMTP."""

from __future__ import annotations

import argparse
import html
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def markdown_to_basic_html(markdown: str) -> str:
    link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

    def render_inline(text: str) -> str:
        rendered = []
        last_index = 0
        for match in link_pattern.finditer(text):
            rendered.append(html.escape(text[last_index : match.start()]))
            label = html.escape(match.group(1))
            url = html.escape(match.group(2), quote=True)
            rendered.append(f'<a href="{url}">{label}</a>')
            last_index = match.end()
        rendered.append(html.escape(text[last_index:]))
        return "".join(rendered)

    lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("<br>")
        elif stripped.startswith("# "):
            lines.append(f"<h1>{render_inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            lines.append(f"<h2>{render_inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            lines.append(f"<h3>{render_inline(stripped[4:])}</h3>")
        else:
            lines.append(f"<p>{render_inline(line)}</p>")

    return "\n".join(
        [
            "<html>",
            "<body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1f2937;\">",
            *lines,
            "</body>",
            "</html>",
        ]
    )


def build_message(subject: str, body: str) -> EmailMessage:
    sender = require_env("QQ_SMTP_USER")
    recipient = require_env("MAIL_TO")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    message.add_alternative(markdown_to_basic_html(body), subtype="html")
    return message


def send_message(message: EmailMessage) -> None:
    host = os.environ.get("QQ_SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("QQ_SMTP_PORT", "465"))
    password = require_env("QQ_SMTP_PASS")
    username = require_env("QQ_SMTP_USER")
    use_ssl = os.environ.get("QQ_SMTP_SSL", "true").lower() in {"1", "true", "yes"}

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(username, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(username, password)
        server.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a technology briefing email.")
    parser.add_argument("--subject", required=True, help="Email subject.")
    parser.add_argument("--body-file", required=True, type=Path, help="Markdown body file.")
    parser.add_argument("--send", action="store_true", help="Actually send the email.")
    return parser.parse_args()


def main() -> None:
    load_env(PROJECT_ROOT / ".env")
    args = parse_args()
    body_path = args.body_file if args.body_file.is_absolute() else PROJECT_ROOT / args.body_file
    body = body_path.read_text(encoding="utf-8")
    message = build_message(args.subject, body)

    if not args.send:
        print(f"Dry run: would send '{args.subject}' to {message['To']}")
        return

    send_message(message)
    print(f"Sent '{args.subject}' to {message['To']}")


if __name__ == "__main__":
    main()
