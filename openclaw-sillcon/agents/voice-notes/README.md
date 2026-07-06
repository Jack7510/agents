# Text Notes Agent

This agent captures short text notes from OpenClaw channels and stores them as weekly Markdown files.

The first MVP intentionally supports text only. Voice messages can be added later by transcribing audio before calling the same append flow.

## User Flow

Send OpenClaw a short message such as:

```text
记一下：OpenClaw 应该先成为我的信息助理，再扩展成完整知识库。
```

The agent should append the note to the current ISO-week file under:

```text
data/notes/YYYY/YYYY-Www.md
```

For example, a note on 2026-07-06 in the Asia/Shanghai timezone is stored in:

```text
data/notes/2026/2026-W28.md
```

## Message Detection

Treat these prefixes as capture intent:

- `记一下：`
- `记一下:`
- `笔记：`
- `笔记:`
- `想法：`
- `想法:`

If a message is already sent in a dedicated personal note chat, the channel adapter may call the append script without requiring a prefix.

## Storage Rule

Keep the original text unchanged in the `Inbox` section. Later summarization may write to `本周整理` or generate a separate report, but it should not overwrite raw notes.

## Local Command

```bash
python3 scripts/append_note.py "记一下：OpenClaw 应该先做好文字笔记。" --source manual --tag 产品
```

For channel adapters that receive mixed conversation, pass `--require-prefix` so only explicit capture messages are stored:

```bash
python3 scripts/append_note.py "笔记：今天继续打磨 OpenClaw。" --source feishu --require-prefix
```
