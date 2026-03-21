# WebAgentFlow API

FastAPI backend for the first CRUD/data layer of WebAgentFlow.

## Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
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
