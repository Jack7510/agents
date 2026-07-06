# Text Notes MVP

## Goal

Build the first personal note loop for cloud OpenClaw:

1. Receive short text notes from WeChat, Feishu, or a manual command.
2. Store raw notes as weekly Markdown files.
3. Preserve original wording.
4. Leave room for later weekly summaries and topic extraction.

Voice input is out of scope for this MVP.

## Weekly Markdown Format

Notes are grouped by ISO week:

```text
data/notes/
  2026/
    2026-W28.md
```

Each week file contains:

```md
# 2026-W28 口头笔记

## Inbox

### 2026-07-06 09:32

- 来源：wechat
- 标签：产品, AI
- 原文：
  这里保留用户原始笔记。

## 本周整理

待整理。

## 主题索引

待整理。
```

## Capture Rules

The channel adapter should capture messages that start with:

- `记一下：`
- `记一下:`
- `笔记：`
- `笔记:`
- `想法：`
- `想法:`

Hashtags in the note body are extracted as tags. For example:

```text
记一下 #产品 #Agent：Agent 的价值是把碎片想法变成可复用资产。
```

If no tags are found, the note is stored with `未分类`.

## Append Command

```bash
python3 scripts/append_note.py "今天想到 OpenClaw 应该先做好文字笔记。" --source manual
```

Useful options:

```bash
python3 scripts/append_note.py "想法 #AI：先做可靠记录，再做复杂检索。" --source wechat
python3 scripts/append_note.py "产品判断：信息入口比知识库结构更重要。" --tag 产品 --tag 信息助理
python3 scripts/append_note.py "测试笔记" --timestamp 2026-07-06T09:30:00
```

Channel adapters can require an explicit capture prefix before appending:

```bash
python3 scripts/append_note.py "记一下：测试笔记" --source feishu --require-prefix
```

## Later Summarization

Future summarization should read one or more weekly Markdown files and produce:

- 本周要点
- 重复出现的主题
- 可以沉淀成原则的观点
- 值得后续追问的问题

Summaries may update `本周整理`, but raw `Inbox` entries should remain untouched.
