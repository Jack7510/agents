# QQ 邮箱发送 Tool

`qq-mail` 是一个通用脚本型 Tool，用于给其他 Skill 发送邮件。

## 文件

```text
agents/qq-mail/SKILL.md
scripts/qq_mail_tool.py
scripts/briefing_utils.py
tests/test_qq_mail_tool.py
```

## 本地冒烟测试

```bash
python scripts/qq_mail_tool.py \
  --subject "OpenClaw 测试邮件" \
  --to "13827420406@qq.com" \
  --body "这是一封测试邮件。" \
  --dry-run
```

## 部署

把 Tool 源码部署到 OpenClaw 主机：

```bash
ssh admin@47.88.66.246 'mkdir -p ~/.openclaw/workspace/skills-src/qq-mail/scripts'
scp agents/qq-mail/SKILL.md admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/qq-mail/
scp scripts/briefing_utils.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/qq-mail/scripts/
scp scripts/qq_mail_tool.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/qq-mail/scripts/
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw skills install /home/admin/.openclaw/workspace/skills-src/qq-mail --as qq-mail --force'
```

## 环境变量

密钥只保存在主机的 `~/.openclaw/.env`：

```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=qq_mail_authorization_code
QQ_MAIL_TO=13827420406@qq.com
```

脚本兼容 `QQ_SMTP_HOST`、`QQ_SMTP_PORT`、`QQ_SMTP_USER`、`QQ_SMTP_PASS`、`MAIL_TO` 等别名。

## Skill 调用示例

建议长正文使用临时文件：

```bash
python3 ~/.openclaw/workspace/skills/qq-mail/scripts/qq_mail_tool.py \
  --subject "OpenClaw 日报" \
  --body-file /tmp/openclaw-daily.md \
  --html
```

也可以显式指定收件人：

```bash
python3 ~/.openclaw/workspace/skills/qq-mail/scripts/qq_mail_tool.py \
  --subject "OpenClaw 日报" \
  --to "13827420406@qq.com" \
  --body-file /tmp/openclaw-daily.md \
  --html
```
