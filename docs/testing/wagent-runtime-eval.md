# WAgent Runtime Eval Runner

This page describes the local M11.3.6.1 WAgent runtime eval runner.

The runner drives WebAgentFlow through the Conversation API and writes
auditable JSON plus Markdown artifacts. It is not a product Agent, does not
call autonomous-run endpoints, and does not use Codex judgment as a pass
criterion.

## Prerequisites

Start required services separately. The runner does not start API, PostgreSQL,
Redis, Docker, or product-test-site.

```bash
docker compose -f infra/docker/docker-compose.yml up -d
pnpm run db:migrate:api
pnpm run dev:api
pnpm run dev:product
```

`pnpm run dev:api` and `pnpm run dev:product` are foreground processes. Run
them in separate terminals or with your own process manager.

Expected defaults:

- API base: `http://127.0.0.1:8001`
- Product URL: `http://127.0.0.1:5176/items`

## Run

```bash
pnpm run eval:wagent:items
```

Equivalent full command:

```bash
.venv/bin/python scripts/evals/wagent_runtime_eval.py \
  --case items_closed_loop \
  --case single_path_direct_replay_regression
```

Useful options:

```bash
--api-base http://127.0.0.1:8001
--product-url http://127.0.0.1:5176/items
--timeout 300
--browser-visibility headless
--artifact-dir artifacts/wagent-eval
--result-dir docs/testing/results
--no-markdown
```

## Cases

`items_closed_loop`:

1. Creates an `interactive_chat` session.
2. Sends the `/items` URL.
3. Learns "新增项目" with item A.
4. Executes "新增项目" with item B.
5. Reads session, messages, events, history, and LearnedPath detail.
6. Evaluates hard gates such as `value_slot=item_name`,
   `slot_overrides.item_name=B`, verified DOM evidence, Reporter outcome, and
   final evidence-based WAgent response.

`single_path_direct_replay_regression`:

1. Reuses the LearnedPath produced by the same eval session.
2. Executes item C.
3. Checks that the current session has one clear learned action, no pending
   choice path, no planner choice path, verified DOM evidence, Reporter
   `verified`, and evidence-based final response.

The single-path case ignores old global `/items` LearnedPath rows. It uses the
current eval session's learned action and runtime events as evidence.

## Outputs

JSON artifact:

```text
artifacts/wagent-eval/wagent-runtime-eval-<timestamp>.json
```

Markdown result:

```text
docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-<timestamp>.md
```

Both outputs are derived from the normalized `EvalResult`. The JSON artifact
also stores raw API request / response records with sensitive keys redacted.

## Gate Status

- `pass`: auditable evidence satisfies the gate.
- `fail`: auditable evidence exists and violates a required gate.
- `blocked`: an environment or prerequisite prevented evaluation.
- `not_observable`: current public read surfaces do not expose a conditional
  field.
- `warning`: non-blocking evidence gap.

Required gates must be `pass` for the case to pass. Conditional gates such as
`effective_value_B` and `evidence_target_item_list` may be `not_observable`
when current public history/events do not expose sanitized step logs or
request-side `evidence_targets`. The runner must not infer selector data from
`ExecutionEvidence`.

## Exit Codes

| Code | Meaning |
|---:|---|
| 0 | all required gates pass |
| 1 | at least one required gate fails |
| 2 | environment blocked |
| 3 | timeout |
| 4 | artifact write failed |
| 5 | runner internal error |

## Boundaries

This runner must not:

- call `verify-scenario`;
- call autonomous-run endpoints;
- call direct replay APIs as a substitute for Conversation API dispatch;
- start long-running services implicitly;
- treat Codex natural-language judgment as pass / fail evidence;
- expose private payload maps, credentials, tokens, cookies, or authorization
  values in artifacts.

Codex may audit the generated artifacts and raw records, but the runner's gates
and exit code are the eval decision surface.
