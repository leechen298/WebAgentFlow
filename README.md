# WebAgentFlow

WebAgentFlow is a monorepo for an agent-driven web workflow engine with a Vue console, FastAPI backend, Python worker, and Chrome extension recorder.

## Scope

This repository currently contains Task Pack 2 backend CRUD foundation on top of the initial engineering setup. The API exposes action-based CRUD routes for `recordings`, `skills`, and `runs`, while larger workflow features such as extension recording, recording-to-skill compilation, and worker execution remain out of scope.

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

5. Apply API migrations:

   ```bash
   pnpm run db:migrate:api
   ```

## Configuration

### Frontend-Backend Communication

WebAgentFlow is designed to support separate frontend/backend deployment by default:

- **Frontend** sends requests directly to the backend via `VITE_API_BASE_URL`
- **Backend** allows frontend origins via `CORS_ALLOWED_ORIGINS`

**Recommended local development variables (in `.env`):**

```bash
# Frontend: Keep API on localhost and let Vite proxy requests
VITE_API_BASE_URL=http://localhost:8001
VITE_USE_DEV_PROXY=true

# Backend: Only needed if you disable the proxy and call API directly
CORS_ALLOWED_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
```

With this setup:

- Your Mac opens the console at `http://localhost:5174`
- Your iPad opens the console at `http://<当前Mac的局域网IP>:5174`
- Both clients call `/api/*` on the console origin
- Vite proxies those requests to `http://localhost:8001` on the Mac

**Optional: Direct API Mode**

If you explicitly want the browser to call the API directly instead of using the proxy:

```bash
VITE_USE_DEV_PROXY=false
VITE_API_BASE_URL=http://<your-current-lan-ip>:8001
CORS_ALLOWED_ORIGINS=http://<your-current-lan-ip>:5174,http://localhost:5174,http://127.0.0.1:5174
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

- Worker:

  ```bash
  pnpm run dev:worker
  ```

- All services together (LAN accessible):

  ```bash
  pnpm run dev:lan
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
