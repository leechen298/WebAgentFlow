# Development Setup

## Requirements

- Node.js `>=20`
- pnpm `>=10`
- Python `>=3.11`
- Docker Desktop or Docker Engine with Compose

## Install

1. Copy `.env.example` to `.env`.
2. Run `pnpm install`.
3. Create a virtual environment with `python3.11 -m venv .venv`.
4. Run `.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'`.
   The last one installs `wagent` into `.venv/bin/` — used for
   `wagent verify` (run a scenario) and `wagent skill install`
   (materialize the Claude Code skill). See
   [the wagent CLI section](#wagent-cli) below.
5. Apply API migrations before launching the API:

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d postgres
   .venv/bin/alembic -c apps/api/alembic.ini upgrade head
   ```

## Start Services

1. Start infrastructure:

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d
   ```

2. Start the console:

   ```bash
   pnpm run dev:console
   ```

3. Start the API:

   ```bash
   pnpm run dev:api
   ```

   `GET /health` should return:

   ```json
   {
     "code": 0,
     "data": {
       "status": "ok",
       "database": "ok"
     },
     "msg": "ok"
   }
   ```

4. Start the worker:

   ```bash
   pnpm run dev:worker
   ```

5. Start the external Fixture-Site (port 5175) from its standalone repo:

   ```bash
   cd /Users/leechen/projects/WebAgentFlow-Fixture-Site
   pnpm dev
   ```

   Configure WebAgentFlow to use that external fixture URL and spec root:

   ```bash
   export WAF_FIXTURE_SITE_URL=https://example.invalid
   export WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs
   # Local example:
   export WAF_PAGE_SPEC_ROOT=/Users/leechen/projects/WebAgentFlow-Fixture-Site/web/specs
   ```

   `WAF_PAGE_SPEC_ROOT` is the explicit spec source for page verification.
   It is required when listing or loading page verification specs; API startup
   and `/health` do not require it.

Or start repo-local WebAgentFlow services with `pnpm run dev` from the repo
root. The external Fixture-Site remains a separate process outside this
workspace.

## Build and Quality Checks

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`

## wagent CLI

`wagent` is the WebAgentFlow command-line interface. Once
`pip install -e ./apps/cli` is done in step 4 of Install, the
binary lives at `.venv/bin/wagent`.

## Project-level Agent skills

Project-specific coding-agent skills live in `.agents/skills/` and are
committed with the repository. Treat those `SKILL.md` files as the canonical
source.

Claude Code discovers project skills from `.claude/skills/`, so this repo may
commit `.claude/skills/<skill-name>` symlinks that point back to
`.agents/skills/<skill-name>`. Do not edit the symlink target through a local
Claude copy; edit `.agents/skills/<skill-name>/SKILL.md` first.

`.codex/` and non-skill `.claude/` contents are local tool configuration /
state and remain ignored.

### Verify a scenario

Runs one autonomous exploration via the HTTP API and prints the
result JSON. The API must be running (`pnpm run dev:api`).

```bash
.venv/bin/wagent verify --url "${WAF_FIXTURE_SITE_URL:-<fixture-site-url>}/<fixture-path>" \
    --fill-values '{"<field>":"<value>"}'
```

- stdout → one JSON object (trimmed; add `--full` for the complete
  snapshot, `--pretty` for indented output).
- stderr → one-line banner with verdict + scorecard summary.
- exit 0 on `success`, 1 on non-success verdicts, 2 on CLI errors.

### Install the Claude Code skill

```bash
.venv/bin/wagent skill install     # writes ~/.claude/skills/verify-scenario/
.venv/bin/wagent skill uninstall   # removes it
```

Installing is idempotent — re-run after a `git pull` or after
re-creating the venv to refresh the embedded absolute paths.

Claude Code can then invoke the `verify-scenario` skill from any
project directory (as long as WebAgentFlow's API is running). The
reporting contract lives in the generated `SKILL.md` and mirrors
[`CLAUDE.md`](../CLAUDE.md)'s execution-boundary section.
