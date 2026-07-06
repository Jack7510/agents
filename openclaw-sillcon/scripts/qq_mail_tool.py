#!/usr/bin/env python3
"""Send plain text or Markdown-like email through QQ Mail SMTP."""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

try:
    from . import briefing_utils as utils
except ImportError:  # pragma: no cover - supports `python scripts/qq_mail_tool.py`.
    import briefing_utils as utils


DEFAULT_ENV_FILE = Path.home() / ".openclaw" / ".env"
DEFAULT_SMTP_HOST = "smtp.qq.com"
DEFAULT_SMTP_PORT = "465"
ENV_ALIASES = {
    "SMTP_HOST": ("QQ_SMTP_HOST",),
    "SMTP_PORT": ("QQ_SMTP_PORT",),
    "SMTP_USER": ("QQ_SMTP_USER",),
    "SMTP_PASSWORD": ("QQ_SMTP_PASS", "QQ_SMTP_PASSWORD"),
    "QQ_MAIL_TO": ("MAIL_TO", "PRODUCT_NEWS_EMAIL_TO", "TECH_PAPERS_EMAIL_TO"),
    "QQ_MAIL_FROM": ("MAIL_FROM", "PRODUCT_NEWS_EMAIL_FROM", "TECH_PAPERS_EMAIL_FROM"),
}


def apply_env_aliases() -> None:
    utils.apply_env_aliases(ENV_ALIASES)
    os.environ.setdefault("SMTP_HOST", DEFAULT_SMTP_HOST)
    os.environ.setdefault("SMTP_PORT", DEFAULT_SMTP_PORT)


def resolve_recipient(to: str | None = None, env_key: str | None = None) -> str:
    candidates = []
    if to:
        candidates.append(to)
    if env_key:
        candidates.append(os.environ.get(env_key, ""))
    candidates.append(os.environ.get("QQ_MAIL_TO", ""))

    for candidate in candidates:
        cleaned = candidate.strip()
        if cleaned:
            return cleaned
    raise RuntimeError("missing recipient: pass --to or set QQ_MAIL_TO/MAIL_TO")


def resolve_sender(from_addr: str | None = None, env_key: str | None = None) -> str:
    candidates = []
    if from_addr:
        candidates.append(from_addr)
    if env_key:
        candidates.append(os.environ.get(env_key, ""))
    candidates.extend([os.environ.get("QQ_MAIL_FROM", ""), os.environ.get("SMTP_USER", "")])

    for candidate in candidates:
        cleaned = candidate.strip()
        if cleaned:
            return cleaned
    raise RuntimeError("missing sender: set SMTP_USER or pass --from")


def build_email_message(
    *,
    subject: str,
    body: str,
    to: str,
    from_addr: str,
    html_body: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to
    message.set_content(body)
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")
    return message


def send_message(message: EmailMessage) -> None:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"missing required SMTP environment variables: {', '.join(missing)}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"]), context=context, timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def send_email(
    *,
    subject: str,
    body: str,
    to: str | None = None,
    from_addr: str | None = None,
    to_env_key: str | None = None,
    from_env_key: str | None = None,
    html_body: str | None = None,
) -> EmailMessage:
    recipient = resolve_recipient(to, to_env_key)
    sender = resolve_sender(from_addr, from_env_key)
    message = build_email_message(
        subject=subject,
        body=body,
        to=recipient,
        from_addr=sender,
        html_body=html_body,
    )
    send_message(message)
    return message


def read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.body:
        return args.body
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise RuntimeError("missing body: pass --body, --body-file, or pipe content on stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send email through QQ Mail SMTP.")
    parser.add_argument("--subject", required=True, help="Email subject.")
    parser.add_argument("--to", help="Recipient email address. Defaults to QQ_MAIL_TO or MAIL_TO.")
    parser.add_argument("--from", dest="from_addr", help="Sender address. Defaults to QQ_MAIL_FROM or SMTP_USER.")
    parser.add_argument("--body", help="Email body text.")
    parser.add_argument("--body-file", help="Path to email body text.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to .env file with SMTP secrets.")
    parser.add_argument("--html", action="store_true", help="Also send an HTML alternative rendered from the body.")
    parser.add_argument("--dry-run", action="store_true", help="Build the message and print a summary without sending.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        utils.load_env_file(Path(args.env_file))
        apply_env_aliases()
        body = read_body(args)
        recipient = resolve_recipient(args.to)
        sender = resolve_sender(args.from_addr)
        html_body = utils.render_email_html(body, args.subject) if args.html else None
        message = build_email_message(
            subject=args.subject,
            body=body,
            to=recipient,
            from_addr=sender,
            html_body=html_body,
        )
        if args.dry_run:
            print(f"Dry run: would send '{args.subject}' from {sender} to {recipient}")
            print(f"Body bytes: {len(body.encode('utf-8'))}")
            return 0
        send_message(message)
    except Exception as exc:
        print(f"qq_mail_tool failed: {exc}", file=sys.stderr)
        return 1

    print(f"Sent email to {recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
