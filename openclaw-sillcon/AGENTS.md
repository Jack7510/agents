# Repository Guidelines

## Project Structure & Module Organization

This workspace manages the OpenClaw deployment on `admin@47.88.66.246` and local tooling for Agent applications. Keep operational notes in `docs/`, host scripts in `scripts/`, Agent code in `agents/<agent-name>/`, and shared examples in `templates/`. Do not mix generated logs, secrets, or one-off host dumps into source directories.

## Build, Test, and Development Commands

No build system is present yet. As tooling is added, prefer stable wrapper commands:

- `ssh admin@47.88.66.246`: connect to the OpenClaw host for inspection.
- `make test`: run local tests for scripts and Agent apps.
- `make lint`: run formatting and static checks.
- `make deploy-agent AGENT=<name>`: deploy one Agent application after tests pass.
- `make host-status`: print OpenClaw service, disk, memory, and process status.

Local Python development uses the active conda `base` environment by default. Use `python` for local commands and Makefile targets; reserve explicit `/usr/bin/python3` or `python3` for remote host commands where conda is not part of the runtime contract.

Document package-native commands in each Agent README, for example `npm test`, `pytest`, or `go test ./...`.

## Coding Style & Naming Conventions

Follow each language formatter once configured. Use `snake_case` for Python files and functions, `camelCase` for JavaScript/TypeScript variables, `PascalCase` for classes and components, and `kebab-case` for script and Agent directories. Shell scripts should start with `set -euo pipefail`, accept explicit arguments, and avoid hard-coded destructive paths.

## Documentation Language

Use Chinese as the default language for repository documentation, Agent READMEs, operational notes, and deployment guides. Keep commands, environment variable names, API names, and code identifiers in their original spelling.

## Testing Guidelines

Add tests for Agent behavior and deployment script changes. Keep unit tests local and deterministic; mark host-dependent checks as integration tests. Use names such as `test_*.py`, `*.test.ts`, or `*_test.go`. Before changing the remote host, run local tests, capture the intended command, and verify service health afterward.

## Commit & Pull Request Guidelines

No Git history is available here, so no existing convention can be inferred. Use short, imperative commit subjects such as `Add host status script` or `Fix agent deployment config`. Pull requests should include purpose, affected Agent or service, test results, deployment impact, rollback notes, and screenshots or logs for UI-visible changes.

## Host Operations & Safety

Treat `admin@47.88.66.246` as a production-like host. Inspect before modifying: check service status, config, disk space, and recent logs. Prefer additive changes and reversible scripts. Do not run destructive commands, database resets, firewall changes, or service restarts without explicit confirmation and a rollback path.

## Security & Configuration Tips

Do not commit private keys, API tokens, `.env` files, or host credentials. Track only examples such as `.env.example`. Store required environment variables in Agent-specific READMEs. Redact secrets from logs before saving them under `docs/` or sharing them in issues.
