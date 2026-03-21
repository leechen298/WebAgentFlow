# WebAgentFlow API

FastAPI backend for the first CRUD/data layer of WebAgentFlow.

## Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd /path/to/web-agent-flow
docker compose -f infra/docker/docker-compose.yml up -d postgres
.venv/bin/alembic -c apps/api/alembic.ini upgrade head
pnpm run dev:api
```

`/health` verifies database connectivity. If PostgreSQL is not running or migrations have not been applied, it returns `503` instead of a misleading `200`.

All successful responses use the unified envelope:

```json
{
  "code": 0,
  "data": {},
  "msg": "ok"
}
```

Errors use the unified envelope:

```json
{
  "code": 404,
  "msg": "Recording 'xxx' was not found.",
  "data": null
}
```

## Endpoints

- `GET /health`
- `GET /docs`

### Recordings
- `GET /recordings/list` - List recordings
- `POST /recordings/create` - Create recording
- `GET /recordings/get?recording_id=xxx` - Get recording
- `POST /recordings/update` - Update recording (body: `{ recording_id, update_data }`)
- `POST /recordings/delete` - Delete recording (body: `{ recording_id }`)

### Skills
- `GET /skills/list` - List skills
- `POST /skills/create` - Create skill
- `GET /skills/get?skill_id=xxx` - Get skill
- `POST /skills/update` - Update skill (body: `{ skill_id, update_data }`)
- `POST /skills/delete` - Delete skill (body: `{ skill_id }`)

### Runs
- `GET /runs/list` - List runs
- `POST /runs/create` - Create run
- `GET /runs/get?run_id=xxx` - Get run
- `POST /runs/update` - Update run (body: `{ run_id, update_data }`)
- `POST /runs/delete` - Delete run (body: `{ run_id }`)

## Test

```bash
pytest
ruff check .
```
