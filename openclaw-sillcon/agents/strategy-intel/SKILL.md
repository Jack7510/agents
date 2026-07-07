---
name: strategy-intel
description: 定时收集科技巨头高管、开源社区意见领袖和资深研究员的访谈、博客、演讲与研究观点，生成中文战略信息简报。
---

# 战略信息收集助手

这个 Skill 用于定时生成 OpenClaw 战略信息简报。

## 任务目标

每个工作日 `Asia/Shanghai` 时间 02:00，通过 OpenClaw cron 收集以下方向的高价值观点信号：

- 科技巨头 CEO、CTO、首席科学家和 AI/机器人业务负责人的访谈、博客、公开信、财报电话会观点和主题演讲。
- 开源社区意见领袖对模型、Agent、机器人、开发者工具、生态治理和商业化的判断。
- 资深研究员、实验室负责人和技术作者的博客、论文解读、播客访谈和演讲材料。
- 与 OpenClaw 战略相关的长期趋势：AI Agent、机器人、开源生态、模型基础设施、推理成本、开发者平台和企业采用。

目标不是复述新闻，而是提炼可用于战略判断的观点变化、路线图暗示、生态分歧和潜在机会，并发送中文邮件简报到：

```text
13827420406@qq.com
```

## 运行方式

手动冒烟测试：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config ~/.openclaw/workspace/skills/strategy-intel/sources.json --archive-root ~/.openclaw/workspace/data/strategy-intel --lookback-hours 96 --limit 8 --dry-run
```

定时任务只通过 OpenClaw cron 运行，不使用系统 `systemd` 机制。cron 任务命令：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config ~/.openclaw/workspace/skills/strategy-intel/sources.json --archive-root ~/.openclaw/workspace/data/strategy-intel --lookback-hours 96 --limit 8
```

## 环境变量

密钥只保存在主机的 `~/.openclaw/.env`，不要提交到仓库。

邮件发送沿用产品新闻助手的 SMTP 配置，收件人固定为：

```bash
PRODUCT_NEWS_EMAIL_TO=13827420406@qq.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=mail_app_password
```

可选搜索接口配置：

```bash
PRODUCT_NEWS_SEARCH_PROVIDER=brave
BRAVE_SEARCH_API_KEY=xxx
PRODUCT_NEWS_MAX_SEARCH_QUERIES=60
```

或：

```bash
PRODUCT_NEWS_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=xxx
PRODUCT_NEWS_MAX_SEARCH_QUERIES=60
```

## 信息源策略

优先采用可追溯的一手和准一手来源：

1. 个人博客、公司官方博客、研究实验室博客。
2. 播客、访谈、主题演讲、财报电话会和公开视频的官方摘要。
3. GitHub Releases、项目博客和维护者公开讨论。
4. 搜索接口只作为补漏，尤其用于发现近期访谈、会议演讲和没有 RSS 的个人站点。

## 简报风格

邮件使用中文，强调战略解读：

- 主题：`OpenClaw 战略信息简报 - YYYY-MM-DD`
- 正文包含 5-8 条主要信号。
- 每条信号包含人物/组织、来源、时间、观点摘要、为什么重要、对 OpenClaw 的启发、原文链接。
- 单独列出 `待验证`，标记二手转述、无完整文字稿或发布时间不明确的内容。
- 避免把普通产品更新包装成战略洞察；没有观点变化或路线图暗示的内容可以丢弃。

## 仍需用户补充

请用户补充或确认：

- 工作日 02:00 是否合适。
- 必须关注或屏蔽的人物、机构、播客、YouTube 频道和中文来源。
- 是否允许接入搜索接口；如果启用，选择 `brave` 或 `tavily`。
