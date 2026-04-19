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
4. Run `.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'`.
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

5. Start the validation-site fixtures (port 5175):

   ```bash
   pnpm run dev:validation
   ```

Or start all four at once with `pnpm run dev` from the repo root.

## Build and Quality Checks

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`
