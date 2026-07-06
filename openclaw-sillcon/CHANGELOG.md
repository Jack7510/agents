# Change Log

## 2026-07-04 13:07 CST - OpenClaw Host Setup and Channel Configuration

### Summary

- Created `AGENTS.md` as the contributor and operations guide for this workspace.
- Upgraded the remote OpenClaw installation on `admin@47.88.66.246` to stable version `2026.6.11`.
- Verified the OpenClaw CLI version and confirmed configuration validation passes.
- Configured DeepSeek as the default model provider using credentials stored on the remote host in `~/.openclaw/.env`.
- Verified DeepSeek model access with a local OpenClaw agent test request.
- Installed and enabled the Feishu plugin, confirmed Feishu channel configuration, and documented setup notes in `docs/feishu-openclaw.md`.
- Confirmed Feishu pairing was completed by the user.
- Installed and enabled the WeChat plugin `@tencent-weixin/openclaw-weixin`.
- Configured OpenClaw to allow `deepseek`, `feishu`, and `openclaw-weixin` plugins.
- Set `session.dmScope` to `per-account-channel-peer` so Feishu and WeChat direct-message sessions remain separated by channel/account/peer.
- Completed WeChat QR login; user confirmed the WeChat bot can chat.

### Follow-up Rule

For future host or OpenClaw configuration changes, append a short entry to this file with:

- Time
- Topic
- Summary
