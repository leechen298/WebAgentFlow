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
- `GET|POST|PATCH|DELETE /recordings`
- `GET|POST|PATCH|DELETE /skills`
- `GET|POST|PATCH|DELETE /runs`

## Test

```bash
pytest
ruff check .
```
