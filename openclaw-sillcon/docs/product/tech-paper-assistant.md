# 技术论文助手

本文档记录 OpenClaw 技术论文助手的目标、配置、测试和部署方式。

## 目标

每天 02:00 收集大模型、Agent、机器人、具身智能、多模态和推理系统相关技术论文，筛选 5-8 个重要发现，并把中文日报发送到 `13827420406@qq.com`。

邮件格式与产品新闻助手保持一致：主题、编号发现、类型、来源、时间、发生了什么、为什么重要、链接、趋势观察和待跟进。

## 本地文件

```text
agents/tech-papers/SKILL.md
agents/tech-papers/sources.json
scripts/send_tech_papers.py
tests/test_tech_papers.py
```

## 主机配置

密钥只保存在远程主机的 `~/.openclaw/.env`：

```bash
TECH_PAPERS_EMAIL_TO=13827420406@qq.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=qq_mail_authorization_code
TECH_PAPERS_TIMEZONE=Asia/Shanghai
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

## 手动测试

本机开发默认使用 conda `base` 环境：

```bash
python -m unittest tests.test_tech_papers
python scripts/send_tech_papers.py --dry-run
```

部署后在主机上运行：

```bash
python3 ~/.openclaw/workspace/skills/tech-papers/scripts/send_tech_papers.py --dry-run
```

发送真实邮件：

```bash
python3 ~/.openclaw/workspace/skills/tech-papers/scripts/send_tech_papers.py
```

## 部署

把 Skill 源码部署到 OpenClaw 主机：

```bash
ssh admin@47.88.66.246 'mkdir -p ~/.openclaw/workspace/skills-src/tech-papers/scripts'
scp agents/tech-papers/SKILL.md admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/tech-papers/
scp agents/tech-papers/sources.json admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/tech-papers/
scp scripts/briefing_utils.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/tech-papers/scripts/
scp scripts/qq_mail_tool.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/tech-papers/scripts/
scp scripts/send_tech_papers.py admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/tech-papers/scripts/
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw skills install /home/admin/.openclaw/workspace/skills-src/tech-papers --as tech-papers --force'
```

## OpenClaw cron 定时任务

技术论文助手只使用 OpenClaw 的 cron 机制，不使用系统 `systemd` 机制。

创建每天 `Asia/Shanghai` 02:00 执行的 cron 任务：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron add --name tech-papers --cron "0 2 * * *" --tz Asia/Shanghai --command-cwd "$HOME/.openclaw/workspace" --command "set -a; . ~/.openclaw/.env; set +a; python3 ~/.openclaw/workspace/skills/tech-papers/scripts/send_tech_papers.py --config ~/.openclaw/workspace/skills/tech-papers/sources.json --archive-root ~/.openclaw/workspace/data/tech-papers" --timeout-seconds 600'
```

查看任务：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron list'
```

手动触发一次：

```bash
ssh admin@47.88.66.246 '~/.npm-global/bin/openclaw cron run tech-papers'
```

如果主机上曾经启用过同名 `systemd` 用户定时器，应先禁用并删除，避免重复发送邮件。

## 仍需补充的信息

- 确认 `SMTP_USER` 中的发件邮箱，以及 `SMTP_PASSWORD` 中的 QQ 邮箱 SMTP 授权码。
- 确认 OpenClaw cron 是否按 `Asia/Shanghai` 的 02:00 执行。
- 决定是否启用搜索接口；如启用，提供 Brave 或 Tavily 的 API Key。
- 把必须关注的实验室、作者、会议、GitHub 仓库和中文来源补充到 `agents/tech-papers/sources.json`。
- 第二阶段可以接入 OpenReview、Semantic Scholar、Hugging Face Papers 或 Papers with Code，提高会议和可复现性判断质量。
