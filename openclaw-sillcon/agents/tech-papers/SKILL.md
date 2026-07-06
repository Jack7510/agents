---
name: tech-papers
description: 每天收集大模型、Agent、机器人、具身智能和多模态方向的技术论文，筛选主要发现，生成中文邮件日报。
---

# 技术论文助手

这个 Skill 用于定时生成技术论文日报。

## 任务目标

每天 `Asia/Shanghai` 时间 02:00，收集以下方向的技术论文信号：

- 大模型、推理、后训练、RAG、Agent 和工具使用。
- 多模态、视觉语言模型、VLA 和世界模型。
- 机器人、具身智能、人形机器人、操作策略和模仿学习。
- LLM 推理、服务、训练系统和工程优化。

筛选 5-8 个主要发现，并发送中文邮件日报到：

```text
13827420406@qq.com
```

## 运行方式

手动冒烟测试：

```bash
python3 ~/.openclaw/workspace/skills/tech-papers/scripts/send_tech_papers.py --dry-run
```

定时任务只通过 OpenClaw cron 运行，不使用系统 `systemd` 机制。cron 任务命令：

```bash
python3 ~/.openclaw/workspace/skills/tech-papers/scripts/send_tech_papers.py --config ~/.openclaw/workspace/skills/tech-papers/sources.json --archive-root ~/.openclaw/workspace/data/tech-papers
```

## 环境变量

密钥只保存在主机的 `~/.openclaw/.env`，不要提交到仓库。

邮件发送必需配置：

```bash
TECH_PAPERS_EMAIL_TO=13827420406@qq.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=mail_app_password
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
TECH_PAPERS_SEARCH_PROVIDER=brave
BRAVE_SEARCH_API_KEY=xxx
TECH_PAPERS_MAX_SEARCH_QUERIES=20
```

或：

```bash
TECH_PAPERS_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=xxx
TECH_PAPERS_MAX_SEARCH_QUERIES=20
```

## 信息源策略

优先采用稳定的一手论文来源：

1. arXiv API。
2. 重点研究机构 RSS。
3. 搜索接口只作为补漏发现代码、项目页和中文线索。

不要只依赖搜索结果。搜索用于发现还没有进入固定观察列表的项目页、GitHub 代码和论文解读。

## 日报风格

邮件使用中文，保持和产品新闻助手相同格式：

- 主题：`技术论文助手日报 - YYYY-MM-DD`
- 正文包含 5-8 条编号发现。
- 每条发现包含类型、来源、时间、发生了什么、为什么重要、链接。
- 尽量补充作者、PDF、代码或项目页。
- 附上一段简短趋势观察。
- 对搜索来源、无摘要来源和无代码论文标记为待跟进。

## 仍需用户补充

请用户补充或确认：

- `~/.openclaw/.env` 中的 SMTP 发件邮箱和 QQ 邮箱授权码。
- 是否启用搜索接口；如果启用，选择 `brave` 或 `tavily`。
- 必须关注的实验室、作者、会议、GitHub 仓库或中文信息源。
- 是否需要加入 OpenReview、Semantic Scholar、Hugging Face Papers 或 Papers with Code 作为第二阶段增强源。
