# 战略信息收集助手

本文档记录 OpenClaw 战略信息收集助手的目标、配置、测试和部署方式。它参考产品新闻助手的实现方式，但关注点从“产品发布”切换为“高价值战略观点”。

## 目标

每个工作日 02:00 通过 OpenClaw cron 收集科技巨头 CEO/CTO、开源社区意见领袖、资深研究员的访谈、博客、播客、演讲和研究观点，筛选 5-8 个重要信号，并把中文战略简报发送到 `13827420406@qq.com`。

重点回答：

- 谁的观点发生了变化，或透露了路线图/组织优先级。
- 这对 AI Agent、机器人、开源生态、模型基础设施和开发者平台意味着什么。
- OpenClaw 应该关注什么机会、风险或后续验证动作。

## 本地文件

```text
agents/strategy-intel/SKILL.md
agents/strategy-intel/sources.json
scripts/send_product_news.py
```

## 采集范围

优先级从高到低：

1. 一手来源：个人博客、官方博客、研究实验室博客、GitHub 讨论和 Release。
2. 准一手来源：播客、访谈、主题演讲、财报电话会、公开视频及官方摘要。
3. 补漏来源：搜索接口发现的近期访谈、中文报道、会议材料和没有 RSS 的个人站点。

人物和组织初始列表在 `agents/strategy-intel/sources.json` 中维护，包括科技巨头 CEO/CTO、研究负责人、开源社区维护者和机器人/AI 研究者。

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

可选 GitHub 配置，用于提高 API 速率限制：

```bash
GITHUB_TOKEN=xxx
```

## 手动测试

本地运行，不发送邮件：

```bash
python scripts/send_product_news.py --config agents/strategy-intel/sources.json --archive-root data/strategy-intel --lookback-hours 96 --limit 8 --dry-run
```

部署后在主机上运行：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config ~/.openclaw/workspace/skills/strategy-intel/sources.json --archive-root ~/.openclaw/workspace/data/strategy-intel --lookback-hours 96 --limit 8 --dry-run
```

发送真实邮件：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config ~/.openclaw/workspace/skills/strategy-intel/sources.json --archive-root ~/.openclaw/workspace/data/strategy-intel --lookback-hours 96 --limit 8
```

## 部署

把 Skill 源码部署到 OpenClaw 主机：

```bash
ssh admin@47.88.66.246 'mkdir -p ~/.openclaw/workspace/skills-src/strategy-intel'
scp agents/strategy-intel/SKILL.md admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/strategy-intel/
scp agents/strategy-intel/sources.json admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/strategy-intel/
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw skills install /home/admin/.openclaw/workspace/skills-src/strategy-intel --as strategy-intel --force'
```

脚本复用已部署的产品新闻助手：

```bash
python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py
```

如果主机尚未部署产品新闻助手，先按 `docs/product/product-news-assistant.md` 部署 `product-news`。

## OpenClaw cron 定时任务

战略信息收集助手只使用 OpenClaw 的 cron 机制，不使用系统 `systemd` 机制。

创建每个工作日 `Asia/Shanghai` 02:00 执行的 cron 任务：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron add --name strategy-intel --cron "0 2 * * 1-5" --tz Asia/Shanghai --command-cwd "$HOME/.openclaw/workspace" --command "set -a; . ~/.openclaw/.env; set +a; PRODUCT_NEWS_EMAIL_TO=13827420406@qq.com python3 ~/.openclaw/workspace/skills/product-news/scripts/send_product_news.py --config ~/.openclaw/workspace/skills/strategy-intel/sources.json --archive-root ~/.openclaw/workspace/data/strategy-intel --lookback-hours 96 --limit 8" --timeout-seconds 600 --no-deliver'
```

查看任务：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron list'
```

手动触发验证：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron list'
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron run <strategy-intel-job-id>'
```

如果主机上曾经启用过同名 `systemd` 用户定时器，应先禁用并删除，避免重复发送邮件。

## 筛选原则

- 优先选观点、路线图、生态判断和战略含义，不把普通产品更新当成战略信号。
- 同一人物或机构的重复内容只保留最原始、信息量最高的一条。
- 搜索结果、二手报道、无完整文字稿内容标记为低置信度，人工确认后再用于决策。
- 每期简报应附上可执行的后续动作，例如继续跟进某个仓库、验证某个生态方向、更新 OpenClaw Agent 路线图。

## 仍需补充的信息

- 确认工作日 02:00 是否合适；如果希望周末也运行，可把 cron 表达式改为 `0 2 * * *`。
- 补充必须关注或屏蔽的人物、公司、研究机构、播客、YouTube 频道和中文信息源。
- 决定是否启用搜索接口；如启用，提供 Brave 或 Tavily 的 API Key。
