from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts import qq_mail_tool


class QqMailToolTests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in (
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "QQ_SMTP_HOST",
            "QQ_SMTP_PORT",
            "QQ_SMTP_USER",
            "QQ_SMTP_PASS",
            "QQ_MAIL_TO",
            "QQ_MAIL_FROM",
            "MAIL_TO",
            "PRODUCT_NEWS_EMAIL_TO",
            "TECH_PAPERS_EMAIL_TO",
        ):
            os.environ.pop(key, None)

    def test_apply_env_aliases_maps_qq_names_and_defaults(self) -> None:
        os.environ["QQ_SMTP_USER"] = "sender@example.com"
        os.environ["QQ_SMTP_PASS"] = "secret"
        os.environ["MAIL_TO"] = "daily@example.com"

        qq_mail_tool.apply_env_aliases()

        self.assertEqual(os.environ["SMTP_HOST"], "smtp.qq.com")
        self.assertEqual(os.environ["SMTP_PORT"], "465")
        self.assertEqual(os.environ["SMTP_USER"], "sender@example.com")
        self.assertEqual(os.environ["SMTP_PASSWORD"], "secret")
        self.assertEqual(os.environ["QQ_MAIL_TO"], "daily@example.com")

    def test_build_email_message_can_include_html_alternative(self) -> None:
        message = qq_mail_tool.build_email_message(
            subject="测试邮件",
            body="# 标题\n",
            to="daily@example.com",
            from_addr="sender@example.com",
            html_body="<h1>标题</h1>",
        )

        self.assertEqual(message["Subject"], "测试邮件")
        self.assertEqual(message["To"], "daily@example.com")
        self.assertTrue(message.is_multipart())
        self.assertIsNotNone(message.get_body(("html",)))

    def test_resolve_recipient_prefers_explicit_then_env_key(self) -> None:
        os.environ["PRODUCT_NEWS_EMAIL_TO"] = "product@example.com"
        os.environ["QQ_MAIL_TO"] = "default@example.com"

        self.assertEqual(qq_mail_tool.resolve_recipient("direct@example.com"), "direct@example.com")
        self.assertEqual(qq_mail_tool.resolve_recipient(env_key="PRODUCT_NEWS_EMAIL_TO"), "product@example.com")

    def test_cli_dry_run_accepts_body_file(self) -> None:
        os.environ["SMTP_USER"] = "sender@example.com"
        os.environ["QQ_MAIL_TO"] = "daily@example.com"
        with tempfile.TemporaryDirectory() as temp_dir:
            body_file = Path(temp_dir) / "body.md"
            body_file.write_text("# 标题\n", encoding="utf-8")

            exit_code = qq_mail_tool.main(
                [
                    "--subject",
                    "测试邮件",
                    "--body-file",
                    str(body_file),
                    "--dry-run",
                ]
            )

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
