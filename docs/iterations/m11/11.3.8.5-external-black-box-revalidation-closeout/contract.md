# 契约（Contract）

状态：NEEDS_USER_INPUT

## Public Concepts

No public API, DB schema, runtime status, Agent role, or lifecycle stage changes.

This package only governs external validation evidence and closeout status.

## Required Approval Fields

Before any live validation command, `review.md` must record:

- `api_base_url`
- `target_url`
- `db_state_policy`: cleaned, preserved, or explicitly described
- `approved_scenario_list`
- `latest_result_docs_update_approval`: yes / no

If any field is absent, status remains `NEEDS_USER_INPUT`.

## Allowed Changes

- Child package docs.
- Dated external validation report under `docs/testing/results/` if live validation runs.
- `docs/testing/results/external-black-box-validation-latest.md` only if approved and based on actual evidence.
- Parent routing / closeout docs after evidence.

## Forbidden Changes

- Runtime, tests, schema, API, frontend, worker, replay, reporter, recovery, abort, prompt, or eval-runner changes.
- Direct calls to `/exploration/autonomous-runs` or `/exploration/autonomous-runs/stream`.
- Internal service imports, hidden HTTP clients, direct replay API, or ad hoc scripts as WAgent pass evidence.
- External Fixture-Site / Fixture-Site source edits.
- PASS wording without evidence from required gates.

## Validation Surface Contract

Allowed operator surfaces:

- `wagent chat` CLI with explicit `--api-base`.
- Product UI surface if the user explicitly asks for UI smoke.

Every run must record:

- operator surface;
- exact command or UI operation path;
- working directory for CLI or page path for UI;
- API base URL and target URL;
- operator action log and `operator_actions` artifact path;
- raw product-client request / response records when a project CLI is involved;
- scenario inputs;
- observed WAgent responses;
- whether learning / execution started;
- resulting artifacts / session id / evidence paths;
- redacted JSON / Markdown artifact paths;
- stable latest redacted record at a stable repo path;
- integrity checks and redaction checks.

## Required Scenarios

Default required scenario list, unless user approves a different list:

- `PV-CLI-002`
- `PV-CLI-003`
- `PV-CLI-004`
- `PV-INTEGRITY-001`
- `PV-INTEGRITY-002`

Optional:

- `PV-SITE-001`
- `PV-CLI-001`

## Status Contract

| Status | Meaning |
|---|---|
| `NEEDS_USER_INPUT` | Live validation approval fields missing. |
| `BLOCKED` | Services, target, credentials, integrity, or allowed surface unavailable. |
| `UNVERIFIED` | Run happened but evidence is insufficient or not reviewable. |
| `FAIL` | Required scenario contradicted expected behavior. |
| `FOLLOW_UP_REQUIRED` | Required gates partially pass but incomplete product capability remains. |
| `PASS` | All required scenarios and integrity checks pass with reviewable evidence. |

## Evidence Boundary

Repo-local tests from 11.3.8.1-11.3.8.4 are prerequisites, not live pass evidence.
`PV-CLI-003` remains unverified until this package runs approved external validation.
