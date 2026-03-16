# WebAgentFlow API

Minimal FastAPI application skeleton for Task Pack 1.

## Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Check

Visit `http://localhost:8000/health` and expect:

```json
{ "status": "ok" }
```
