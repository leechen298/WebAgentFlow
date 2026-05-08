# Deterministic E2E

WebAgentFlow uses Playwright Test for browser E2E and API request validation.
The E2E workspace lives in `apps/e2e/`.

## First Stage Goal

The first E2E stage covers the completed M10.2 replay capability:

- LearnedPath replay API.
- LearnedPath catalog UI replay section.

This does not add product behavior and does not expand the M10.2 scope.

## Environment

The first version assumes the developer starts the required services manually:

- FastAPI server.
- Validation site.
- Console.
- PostgreSQL with migrated schema and E2E seed data.

The Playwright config intentionally does not orchestrate all servers with
`webServer` yet. That can come later after the regression track is stable.

## Seed Strategy

E2E fixtures are inserted directly into `learned_paths`.

- Do not create LearnedPath rows through autonomous runs.
- Do not call `/exploration/autonomous-runs`.
- Do not depend on an LLM provider.
- Use `dedup_key` values with the `e2e:replay:` prefix so fixtures can be
  reset without affecting other data.
- Write generated fixture ids to `apps/e2e/.tmp/replay-fixtures.json`.

The seed script computes the current `/users` page signature through the API
side page analyzer and execution runtime. That is deterministic page analysis,
not an autonomous run.

## First Case Matrix

| Case                             | Expected assertion                                                     |
| -------------------------------- | ---------------------------------------------------------------------- |
| replay API happy path            | `status=succeeded`, `drift_status=none`, step logs exist               |
| catalog UI happy path            | drawer replay result shows success and no drift                        |
| `actions=[]` observational path  | `status=observed`, steps are empty                                     |
| `page_mismatch`                  | `status=drifted`, `drift_status=page_mismatch`                         |
| `target_missing`                 | `status=drifted`, `drift_status=target_missing`                        |
| `unsupported_action`             | `status=unsupported`, `drift_status=unsupported_action`                |
| flaky warning                    | replay succeeds and warnings include the flaky trust warning           |
| deprecated 422                   | replay request returns HTTP 422                                        |
| signature changed but executable | `drift_status=signature_changed`, warning exists, replay is executable |

## Deferred

- Failed action caused by real DOM obstruction.
- Live autonomous learning to replay smoke coverage.
- Multi-page workflow.
- Task postcondition verification.

Those belong to later testing work, not the first deterministic E2E pass.
