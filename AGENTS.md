# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready # Find available work
bd show <id> # View issue details
bd update <id> --status in_progress # Claim work
bd close <id> # Complete work
bd sync # Sync with git
```

## Project Overview

FreshRSS MCP server using **Streamable HTTP** transport for OpenClaw integration.

**Key files:**
- `src/freshrss_mcp/server.py` — Entry point, FastMCP with streamable-http
- `src/freshrss_mcp/tools.py` — All MCP tool definitions
- `src/freshrss_mcp/client.py` — FreshRSS Google Reader API client
- `src/freshrss_mcp/config.py` — pydantic-settings config from env vars
- `tests/` — 67 tests across config, client, tools, and models

**Running:**
```bash
uv sync && uv run pytest -v    # test
uv run freshrss-mcp             # start server
```

**Transport:** Streamable HTTP (not stdio). OpenClaw's `openclaw-mcp-bridge` plugin connects via HTTP POST to `/mcp`.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
 ```bash
 git pull --rebase
 bd sync
 git push
 git status # MUST show "up to date with origin"
 ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
