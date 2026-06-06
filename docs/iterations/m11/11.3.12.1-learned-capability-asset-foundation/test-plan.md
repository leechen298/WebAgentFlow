# Test Plan

状态：proposed

## Test Scope

This package requires `test-plan.md` because it changes database schema, ORM, repository behavior,
Pydantic schemas. It does not add HTTP API routes.

No live autonomous validation is authorized by this package.

## Required Unit Tests

### LearnedCapability repository

File: `apps/api/tests/test_learned_capabilities_repo.py`

Required cases:

- `test_ingest_creates_capability_with_required_fields`
- `test_ingest_duplicate_returns_existing_without_overwriting_evidence`
- `test_compute_dedup_key_is_stable_for_sorted_json`
- `test_compute_dedup_key_excludes_sample_value_policy`
- `test_set_trust_allows_legal_transition`
- `test_set_trust_rejects_illegal_transition`
- `test_deleted_source_run_or_path_can_be_null`

Command:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py -v
```

Expected: all tests pass.

## Required Regression Tests

Existing LearnedPath compatibility must be verified.

Command:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v
```

Expected: all existing LearnedPath repo/API tests pass without updating expectations to hide regressions.

## Required Migration Verification

The repository pytest fixtures create tables from SQLAlchemy metadata and do not prove the Alembic migration chain.
Run the repo migration entry after implementing the migration:

```bash
pnpm run db:migrate:api
```

Expected: command exits 0 and Alembic upgrades to head.

If local database services are unavailable, run the closest direct command and record the exact failure:

```bash
cd apps/api && ../../.venv/bin/alembic -c alembic.ini upgrade head
```

Expected when services are available: command exits 0. If it fails because Postgres is not reachable, record
the connection error in `review.md` and do not claim migration verification passed.

## Required Schema Tests

Schema assertions may live in `apps/api/tests/test_learned_capabilities_repo.py` or a dedicated
`apps/api/tests/test_learned_capability_schema.py`.

Required cases:

- summary projection includes identity, source ids, trust, provenance, timestamps, and evidence summary;
- detail projection includes `action_schema`, `sample_value_policy`, and `terminal_target`;
- normal projection does not expose raw DOM snippets or raw selector-only debug payload.

## Static Checks

Run the repo ruff entry if available:

```bash
uv run ruff check apps/api/app apps/api/tests
```

If `uv` or dependencies are unavailable, run the closest repo-local equivalent and record the exact failure.

## Hardcoding Scan

Run:

```bash
rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app
```

Expected: no new runtime hardcoding introduced by this package. Existing unrelated hits must be identified
as pre-existing or test-only; do not hide true positives.

## Live Validation Boundary

Not authorized:

- `verify-scenario`
- product UI autonomous run
- `wagent chat` live learning
- direct autonomous-run endpoint

If live validation is later requested, it belongs after implementation and explicit approval under the parent
campaign live-validation rule.

## Acceptance Gates

Implementation may close only if:

- required unit tests pass;
- migration verification passes, or an environment failure is recorded as not run / unverified;
- LearnedPath regression tests pass;
- schema projection tests pass;
- static check is clean or any environment failure is recorded truthfully;
- hardcoding scan is reviewed;
- no old LearnedPath compatibility regression is found;
- `review.md` records commands run and commands not run.
