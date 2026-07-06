# 产品新闻助手

本文档记录 OpenClaw 产品新闻助手的目标、配置、测试和部署方式。

## 目标

每天 02:00 收集 AI、机器人、初创公司、科技巨头和开源项目相关的产品发布信号，筛选 3-5 个重要发现，并把中文日报发送到 `13827420406@qq.com`。

## 本地文件

```text
agents/product-news/SKILL.md
agents/product-news/sources.json
agents/product-news/systemd/product-news.service
agents/product-news/systemd/product-news.timer
scripts/send_product_news.py
tests/test_product_news.py
```

## 主机配置

密钥只保存在远程主机的 `~/.openclaw/.env`：

```bash
PRODUCT_NEWS_EMAIL_TO=13827420406@qq.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=qq_mail_authorization_code
PRODUCT_NEWS_TIMEZONE=Asia/Shanghai
```

脚本也兼容当前主机上已有的变量名：

```bash
MAIL_TO
QQ_SMTP_HOST
QQ_SMTP_PORT
QQ_SMTP_USER
QQ_SMTP_PASS
TIMEZONE
```

可选搜索接口配置：

```bash
PRODUCT_NEWS_SEARCH_PROVIDER=brave
BRAVE_SEARCH_API_KEY=xxx
PRODUCT_NEWS_MAX_SEARCH_QUERIES=30
```

或：

```bash
PRODUCT_NEWS_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=xxx
PRODUCT_NEWS_MAX_SEARCH_QUERIES=30
```

可选 GitHub 配置，用于提高 API 速率限制：

```bash
GITHUB_TOKEN=xxx
```

## 手动测试

本机开发默认使用 conda `base` 环境，直接通过 Makefile 运行：

```bash
make test
make product-news-once
```

本地运行，不发送邮件：

```bash
python scripts/send_product_news.py --dry-run
```

部署后在主机上运行：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --dry-run
```

发送真实邮件：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py
```

## 部署

把 Skill 源码部署到 OpenClaw 主机：

```bash
ssh admin@47.88.66.246 'mkdir -p ~/.openclaw/workspace/skills-src/product-news/scripts'
scp agents/product-news/SKILL.md admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/product-news/
scp agents/product-news/sources.json admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/product-news/
scp scripts/send_product_news.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/product-news/scripts/
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw skills install /home/admin/.openclaw/workspace/skills-src/product-news --as product-news --force'
```

## systemd 用户定时器

创建 `~/.config/systemd/user/product-news.service`：

```ini
[Unit]
Description=OpenClaw 产品新闻日报

[Service]
Type=oneshot
WorkingDirectory=%h/.openclaw/workspace
EnvironmentFile=%h/.openclaw/.env
ExecStart=/usr/bin/python3 %h/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config %h/.openclaw/workspace/skills/product-news/sources.json --archive-root %h/.openclaw/workspace/data/product-news
```

创建 `~/.config/systemd/user/product-news.timer`：

```ini
[Unit]
Description=每天 02:00 运行 OpenClaw 产品新闻日报

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
Unit=product-news.service

[Install]
WantedBy=timers.target
```

仓库中也提供了对应模板：

```text
agents/product-news/systemd/product-news.service
agents/product-news/systemd/product-news.timer
```

启用定时器：

```bash
systemctl --user daemon-reload
systemctl --user enable --now product-news.timer
systemctl --user list-timers product-news.timer
```

查看运行日志：

```bash
journalctl --user -u product-news.service -n 100 --no-pager
```

## 仍需补充的信息

- 确认 `SMTP_USER` 中的发件邮箱，以及 `SMTP_PASSWORD` 中的 QQ 邮箱 SMTP 授权码。
- 确认服务器定时任务是否按 `Asia/Shanghai` 的 02:00 执行。
- 决定是否启用搜索接口；如启用，提供 Brave 或 Tavily 的 API Key。
- 把必须关注的公司、产品、GitHub 仓库和中文来源补充到 `agents/product-news/sources.json`。
- 确认日报覆盖范围：只看英文来源、只看中文来源，还是中英文都看。
