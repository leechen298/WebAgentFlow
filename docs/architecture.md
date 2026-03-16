# Architecture

## Goal

WebAgentFlow aims to provide a structured platform for capturing web interactions, organizing reusable skills, and executing runs through a coordinated console, API, worker, and browser extension.

## System Layers

1. Presentation layer: the Vue console and Chrome extension provide operator-facing interfaces.
2. Application layer: the FastAPI service owns API contracts, orchestration entry points, and system integration boundaries.
3. Execution layer: the worker handles asynchronous tasks and future browser automation jobs.
4. Infrastructure layer: PostgreSQL, Redis, and MinIO provide persistence, queue/cache support, and object storage.

## App Responsibilities

- `apps/console`: operator UI for recordings, skills, and runs.
- `apps/api`: HTTP API, config loading, persistence integration, and system health endpoints.
- `apps/worker`: asynchronous execution shell for future job runners and Playwright-based tasks.
- `apps/extension`: Chrome MV3 recorder shell with background, content, and popup entrypoints.
