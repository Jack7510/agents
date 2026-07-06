---
name: qq-mail
description: 通过 QQ 邮箱 SMTP 发送纯文本或 Markdown 风格邮件，供其他 Skill 复用。
---

# QQ 邮箱发送工具

这个 Skill 提供通用邮件发送脚本：

```text
scripts/qq_mail_tool.py
scripts/briefing_utils.py
```

其他 Skill 可以在生成日报、告警或摘要后调用该脚本发送邮件。

## 运行方式

从文件发送正文：

```bash
python3 ~/.openclaw/workspace/skills/qq-mail/scripts/qq_mail_tool.py \
  --subject "OpenClaw 测试邮件" \
  --to "13827420406@qq.com" \
  --body-file /tmp/openclaw-mail.md \
  --html
```

从管道发送正文：

```bash
printf '# 标题\n\n正文内容\n' | python3 ~/.openclaw/workspace/skills/qq-mail/scripts/qq_mail_tool.py \
  --subject "OpenClaw 测试邮件" \
  --to "13827420406@qq.com" \
  --html
```

冒烟测试只构建邮件、不发送：

```bash
python3 ~/.openclaw/workspace/skills/qq-mail/scripts/qq_mail_tool.py \
  --subject "OpenClaw 测试邮件" \
  --to "13827420406@qq.com" \
  --body "这是一封测试邮件。" \
  --dry-run
```

## 环境变量

密钥只保存在主机的 `~/.openclaw/.env`，不要提交到仓库。

```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=qq_mail_authorization_code
```

也兼容当前主机上的 QQ 命名：

```bash
QQ_SMTP_HOST=smtp.qq.com
QQ_SMTP_PORT=465
QQ_SMTP_USER=sender@example.com
QQ_SMTP_PASS=qq_mail_authorization_code
```

默认收件人可以配置为：

```bash
QQ_MAIL_TO=13827420406@qq.com
```

脚本也会读取 `MAIL_TO`、`PRODUCT_NEWS_EMAIL_TO`、`TECH_PAPERS_EMAIL_TO` 作为兼容别名。

## 调用约定

- 使用 `--body-file` 传递长正文，避免 shell 引号和换行问题。
- 使用 `--html` 时，脚本会把 Markdown 风格日报正文渲染成 HTML alternative，同时保留纯文本正文。
- QQ 邮箱使用授权码作为 `SMTP_PASSWORD`，不是网页登录密码。
