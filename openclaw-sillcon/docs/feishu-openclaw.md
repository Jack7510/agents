# Feishu OpenClaw Configuration

This document records how to configure the Feishu/Lark channel for the OpenClaw host at `admin@47.88.66.246`.

## Secret Location

Store Feishu credentials only on the remote host:

```bash
ssh admin@47.88.66.246
chmod 600 ~/.openclaw/.env
```

Add these variables to `~/.openclaw/.env`:

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

Do not commit these values to this repository. If the app is for international Lark instead of domestic Feishu, keep the same variable names and set `domain` to `lark` in the OpenClaw config.

## OpenClaw Channel Config

After the variables are present, patch `~/.openclaw/openclaw.json` on the host:

```bash
ssh admin@47.88.66.246
set -a
. ~/.openclaw/.env
set +a

openclaw config patch --stdin <<EOF
{
  channels: {
    feishu: {
      enabled: true,
      domain: "feishu",
      connectionMode: "websocket",
      defaultAccount: "default",
      accounts: {
        default: {
          appId: "${FEISHU_APP_ID}",
          appSecret: "${FEISHU_APP_SECRET}",
          name: "OpenClaw Feishu Bot"
        }
      },
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      requireMention: true
    }
  }
}
EOF
```

This writes the current environment variable values into OpenClaw config. If you prefer not to place credentials in `openclaw.json`, use the interactive setup instead and let OpenClaw manage the channel credentials:

```bash
openclaw channels login --channel feishu
```

Choose manual setup and paste the App ID and App Secret from Feishu Open Platform.

## Feishu Platform Checks

In Feishu Open Platform, confirm the bot app is published or approved for the target tenant. Enable bot messaging and event delivery. WebSocket mode is the default OpenClaw transport; webhook mode additionally needs `verificationToken`, `encryptKey`, and reachable webhook routing.

## Validation

Run these checks after configuration:

```bash
openclaw config validate
openclaw channels list
openclaw channels status --deep
openclaw gateway restart
```

For direct messages, the default `dmPolicy` is `pairing`; unknown users receive a pairing code. Approve with:

```bash
openclaw pairing list feishu
openclaw pairing approve feishu <CODE>
```

For group chats, the default `groupPolicy` in this guide is `allowlist`, so add target group IDs before expecting replies:

```json5
{
  channels: {
    feishu: {
      groupAllowFrom: ["oc_xxx"],
      requireMention: true
    }
  }
}
```

## Text Notes Skill Deployment

The text-notes Agent is deployed as an OpenClaw workspace skill. This lets the main OpenClaw Agent load the capture instructions when a Feishu or WeChat message starts with `记一下`, `笔记`, or `想法`.

Local source files:

```text
agents/text-notes/SKILL.md
agents/text-notes/scripts/append_note.py
```

Cloud locations after deployment:

```text
/home/admin/.openclaw/workspace/skills-src/text-notes
/home/admin/.openclaw/workspace/skills/text-notes
/home/admin/.openclaw/workspace/data/notes
```

Deployment commands used:

```bash
ssh admin@47.88.66.246 'mkdir -p ~/.openclaw/workspace/skills-src'
scp -r agents/text-notes admin@47.88.66.246:/home/admin/.openclaw/workspace/skills-src/
ssh admin@47.88.66.246 \
  '~/.npm-global/bin/openclaw skills install /home/admin/.openclaw/workspace/skills-src/text-notes --as text-notes --force'
```

Verify the skill is installed and visible to the model:

```bash
ssh admin@47.88.66.246
~/.npm-global/bin/openclaw skills info text-notes
```

Expected signals:

```text
text-notes ✓ Ready
Visible to model: yes
Available as command: yes
Path: ~/.openclaw/workspace/skills/text-notes/SKILL.md
```

Verify the append script writes a weekly Markdown note:

```bash
python3 ~/.openclaw/workspace/skills/text-notes/scripts/append_note.py \
  "记一下 #验证：测试 OpenClaw 文字笔记 Agent。" \
  --source manual \
  --require-prefix

tail -80 ~/.openclaw/workspace/data/notes/$(date +%G)/$(date +%G)-W$(date +%V).md
```

Expected note entry:

```text
- 来源：manual
- 标签：验证
- 原文：
  #验证：测试 OpenClaw 文字笔记 Agent。
```

Verify the gateway and channels are still healthy:

```bash
~/.npm-global/bin/openclaw status
```

Expected deployment-time status:

```text
Gateway service      systemd user installed · enabled · running
Channels             openclaw-weixin OK / feishu configured
```

For an end-to-end channel test, send this in Feishu or WeChat:

```text
记一下 #验证：从聊天入口记录一条笔记。
```

Then inspect the current week file under `~/.openclaw/workspace/data/notes/`. If the message appears there, the full flow is working:

```text
chat channel -> OpenClaw -> text-notes skill -> Markdown note file
```

Do not restart the gateway for ordinary skill updates. Reinstall the skill with `--force`, then use `openclaw skills info text-notes` and a manual append smoke test.
