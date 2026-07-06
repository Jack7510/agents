---
name: product-news
description: 每天收集 AI、机器人、初创公司、科技巨头和开源项目的产品发布信号，筛选主要发现，生成中文邮件日报。
---

# 产品新闻助手

这个 Skill 用于定时生成产品新闻日报。

## 任务目标

每天 `Asia/Shanghai` 时间 02:00，收集以下方向的产品发布信号：

- AI 产品、模型、Agent 和开发者工具。
- 机器人、具身智能、人形机器人和自动化系统。
- 初创公司新品、公开发布和 beta 测试。
- 科技巨头产品更新。
- 开源项目版本发布。

筛选 3-5 个主要发现，并发送中文邮件日报到：

```text
13827420406@qq.com
```

## 运行方式

手动冒烟测试：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --dry-run
```

定时任务运行：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py
```

## 环境变量

密钥只保存在主机的 `~/.openclaw/.env`，不要提交到仓库。

邮件发送必需配置：

```bash
PRODUCT_NEWS_EMAIL_TO=13827420406@qq.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=mail_app_password
```

可选配置：

```bash
PRODUCT_NEWS_EMAIL_FROM="OpenClaw Product News <sender@example.com>"
PRODUCT_NEWS_TIMEZONE=Asia/Shanghai
PRODUCT_NEWS_SEARCH_PROVIDER=brave
BRAVE_SEARCH_API_KEY=xxx
TAVILY_API_KEY=xxx
GITHUB_TOKEN=xxx
```

## 信息源策略

优先采用稳定的一手来源：

1. 官方博客和 RSS。
2. 重点开源项目的 GitHub Releases。
3. 搜索接口只作为补漏发现。

不要只依赖搜索结果。搜索用于发现还没有进入固定观察列表的新公司、新产品和新发布。

## 日报风格

邮件使用中文，保持简洁：

- 主题：`产品新闻助手日报 - YYYY-MM-DD`
- 正文包含 3-5 条编号发现。
- 每条发现包含产品/项目、类型、方向、发生了什么、为什么重要、来源链接。
- 附上一段简短趋势观察。
- 对低置信度内容标记为 `待跟进`。

## 仍需用户补充

请用户补充或确认：

- `~/.openclaw/.env` 中的 SMTP 发件邮箱和 QQ 邮箱授权码。
- 每天 02:00 是否明确使用 `Asia/Shanghai`。
- 是否启用搜索接口；如果启用，选择 `brave` 或 `tavily`。
- 必须关注的公司、GitHub 仓库或中文信息源。
- 日报是否同时覆盖中文来源和英文来源。
