---
name: text-notes
description: Capture short Chinese text notes from OpenClaw chat channels, preserve the original wording, extract hashtags, and append them to weekly Markdown inbox files. Use when a message starts with 记一下, 笔记, or 想法, or when the user asks to record,整理,归纳,总结,提炼, or查找 personal notes.
---

# Text Notes

Use this skill for the personal OpenClaw text-note loop.

## Capture

When a message starts with one of these prefixes, store it as a note:

- `记一下：`
- `记一下:`
- `笔记：`
- `笔记:`
- `想法：`
- `想法:`

Remove only the capture prefix. Preserve the remaining wording exactly.

Append notes with:

```bash
python3 ~/.openclaw/workspace/skills/text-notes/scripts/append_note.py "<message>" --source <channel> --require-prefix
```

Use `--source feishu`, `--source wechat`, or `--source manual` as appropriate.

## Storage

The script writes weekly Markdown files under:

```text
~/.openclaw/workspace/data/notes/YYYY/YYYY-Www.md
```

Each entry includes timestamp, source, tags, and raw text. Hashtags in the note body become tags. If no tag exists, the script uses `未分类`.

## Replies

After capture, reply briefly:

```text
已记到 2026-W28。
```

Do not summarize the note immediately unless the user asks.

## Summaries And Search

When the user asks to 整理, 归纳, 总结, 提炼, or 查找 notes:

1. Read the relevant files under `~/.openclaw/workspace/data/notes/`.
2. Keep raw Inbox entries as evidence.
3. Produce a concise synthesis grouped by theme.
4. Mark uncertain conclusions as inferences.
