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

4. Start the worker:

   ```bash
   pnpm run dev:worker
   ```

## Build and Quality Checks

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`
