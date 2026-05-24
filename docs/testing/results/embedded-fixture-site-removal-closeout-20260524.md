# Embedded Fixture Site Removal Closeout — 2026-05-24

Status: embedded fixture-site removal complete.

This closeout covers only removal of the embedded `apps/validation-site`
source, its workspace scripts, the main-repo validation API router, and the
temporary page-spec fallback to `apps/validation-site/specs`.

## Completed

- `apps/validation-site` removed from the main repository.
- Root `dev`, `dev:lan`, and `build` scripts no longer start or build the
  embedded validation-site workspace.
- `pnpm-lock.yaml` updated by `pnpm install --lockfile-only`.
- `apps/api/app/routers/validation_api.py` removed; the external
  WebAgentFlow Fixture-Site owns `/validation-api`.
- Page verification now requires explicit `WAF_PAGE_SPEC_ROOT` when specs are
  loaded or listed.
- API startup and `/health` do not require `WAF_PAGE_SPEC_ROOT`.
- Active E2E fixture smoke remains, but targets the external fixture URL via
  `WAF_FIXTURE_SITE_URL`.

## Boundaries

- This package does not rewrite legacy `5175` API/CLI unit-test scenarios.
- This package does not touch `scripts/evals/*`.
- This package does not update historical docs or historical result records.
- This package does not add the external Fixture-Site as a workspace,
  dependency, source copy, or submodule.
- No live autonomous run, `verify-scenario`, UI smoke, or E2E browser run is
  claimed by this closeout.

## Follow-ups

- Phase 2C should classify and rewrite legacy tests/evals that still use
  synthetic `5175` URLs or old validation-site wording.
- External fixture smoke can be run separately with:
  `WAF_FIXTURE_SITE_URL=http://127.0.0.1:5175` and
  `WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs`.
