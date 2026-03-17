# WebAgentFlow

WebAgentFlow is a monorepo for an agent-driven web workflow engine with a Vue console, FastAPI backend, Python worker, and Chrome extension recorder.

## Scope

This repository currently contains Task Pack 1: engineering initialization. It focuses on a clean, runnable foundation and intentionally excludes business features such as recording workflows, skill execution, and run orchestration.

## Tech Choices

- `pnpm workspace` manages the JavaScript/TypeScript monorepo.
- Vue 3 + Vite + Pinia + Vue Router + Naive UI power the console.
- FastAPI + SQLAlchemy 2.x + Alembic provide the API skeleton.
- The worker is a separate Python package with a minimal long-running runner.
- WXT is used for the Chrome MV3 extension to keep the extension scaffold simple and mainstream.
- Python dependency management stays on plain `venv + pip` in this phase to avoid adding a second package manager such as Poetry or uv before runtime needs are clear.

## Repository Layout

```text
web-agent-flow/
├─ apps/
│  ├─ api/
│  ├─ console/
│  ├─ extension/
│  └─ worker/
├─ docs/
├─ examples/
├─ infra/
│  ├─ docker/
│  └─ scripts/
├─ packages/
│  ├─ sdk-js/
│  ├─ shared-types/
│  └─ skill-schema/
└─ .github/workflows/
```

## Prerequisites

- Node.js `>=20`
- pnpm `>=10`
- Python `>=3.11`
- Docker with Compose support

## Local Setup

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Install JavaScript dependencies:

   ```bash
   pnpm install
   ```

3. Create a Python virtual environment and install API/worker dependencies:

   ```bash
   python3.11 -m venv .venv
   .venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'
   ```

4. Start local infrastructure:

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d
   ```

## Run Apps

- Console:

  ```bash
  pnpm run dev:console
  ```

- API:

  ```bash
  pnpm run dev:api
  ```

- Worker:

  ```bash
  pnpm run dev:worker
  ```

- Extension development build:

  ```bash
  pnpm --filter @web-agent-flow/extension dev
  ```

## Common Commands

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`
- `pnpm run docker:up`
- `pnpm run docker:down`

## Additional Docs

- [Development setup](./docs/dev-setup.md)
- [Architecture overview](./docs/architecture.md)
- [Roadmap](./docs/roadmap.md)
- [Skill spec](./docs/skill-spec.md)
