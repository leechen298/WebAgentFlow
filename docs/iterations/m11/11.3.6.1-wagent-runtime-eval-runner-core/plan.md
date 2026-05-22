# 实施计划（Implementation Plan）

状态：ready_for_implementation（design review passed，未实现代码）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- [`../11.3.5.6-wagent-chat-items-closed-loop-evaluation/review.md`](../11.3.5.6-wagent-chat-items-closed-loop-evaluation/review.md)
- [`../11.3.5.7-pending-choice-active-task-ledger/review.md`](../11.3.5.7-pending-choice-active-task-ledger/review.md)
- [`../11.3.5.8-basic-failure-recovery/review.md`](../11.3.5.8-basic-failure-recovery/review.md)
- [`../11.3.5.9-taskpathplanner-multi-candidate-chat-integration/review.md`](../11.3.5.9-taskpathplanner-multi-candidate-chat-integration/review.md)

## 文件 / 模块

Planned implementation files:

- `scripts/evals/wagent_runtime_eval.py`
  - CLI args and config.
  - Conversation driver.
  - Evidence collector.
  - Gate evaluator.
  - Artifact writer.
  - exit code reducer.
- `docs/testing/wagent-runtime-eval.md`
  - how to start services.
  - how to run eval.
  - how to read JSON / Markdown outputs.
  - exit code and blocked / fail handling.
  - Codex audit workflow.
- `package.json`
  - add `eval:wagent:items`.
  - optionally add `eval:wagent`.

Optional, only if needed:

- `apps/api/tests/test_wagent_runtime_eval.py` or another repo-appropriate test file.
- `scripts/evals/lib/` if `wagent_runtime_eval.py` becomes too large.

Do not modify by default:

- Conversation API endpoints.
- TaskResultReporter.
- TaskPathPlanner.
- LearnedPath replay execution.
- autonomous exploration code.

Only modify API / history / event payloads if implementation proves required gate evidence is impossible to observe
through existing read-only surfaces. In that case, update `contract.md` and `technical-design.md` first.

## 步骤

### Step 0 · 设计评审

- Review all seven docs.
- Confirm first version only includes:
  - `items_closed_loop`
  - `single_path_direct_replay_regression`
- Confirm `failure_recovery_menu_safety` is deferred.
- Confirm direct Conversation API is allowed and autonomous endpoints remain prohibited.
- Confirm no product runtime capability will be added.
- Confirm `evidence_target_item_list` is conditional unless `evidence_targets` are observable.
- Confirm `single_path_direct_replay_regression` is session-scoped and ignores old global
  `/items` LearnedPaths.

### Step 1 · Current-state preflight

Run read-only discovery:

```bash
rg -n "conversation.*dispatch|/dispatch|history|events" apps/api/app/routers apps/api/app/services apps/cli/wagent
rg -n "chat_learning_completed|chat_execution_started|chat_execution_completed|task_result_reported" apps/api/app apps/api/tests docs/testing docs/iterations/m11
rg -n "ExecutionEvidenceTarget|class ExecutionEvidence|evidence_targets|execution_evidence" apps/api/app/schemas apps/api/app/services apps/api/tests
rg -n "eval:wagent|dev:product|product-test-site|5176" package.json apps/product-test-site/package.json docs
```

Expected:

- Conversation session / dispatch / events / history endpoints exist.
- Runtime emits or persists learning / execution / reporter events.
- Selector observability is confirmed from `evidence_targets`, not `ExecutionEvidence`.
- Product-test-site `/items` is available under port 5176 by default.

### Step 2 · Add runner skeleton

Create `scripts/evals/wagent_runtime_eval.py` with:

- `argparse` config.
- dataclasses for `GateResult`, `TurnRecord`, `CaseResult`, `EvalResult`.
- `main()` and exit reducer.
- `--help` works without services.

Run:

```bash
.venv/bin/python scripts/evals/wagent_runtime_eval.py --help
```

Expected: prints help and exits 0.

### Step 3 · Implement preflight

Add:

- API health check.
- product URL check.
- blocked result generation.

Unit-test or manually test with invalid ports:

```bash
.venv/bin/python scripts/evals/wagent_runtime_eval.py --api-base http://127.0.0.1:9
```

Expected: exit 2 and blocked result.

### Step 4 · Implement ConversationDriver

Add:

- create session.
- dispatch turn.
- response / duration recording.
- timeout handling.

Keep the driver independent from gate evaluation.

### Step 5 · Implement EvidenceCollector

Add:

- session read.
- messages read.
- events read.
- history read.
- LearnedPath detail read.
- event helpers to find learning / execution / reporter evidence.

No pass / fail logic in collector.

### Step 6 · Implement `items_closed_loop`

Implement case flow:

```text
URL turn
learn A
execute B
collect evidence
evaluate gates
```

Required gates come from `contract.md`.

If step log effective value is not exposed, record warning / not_observable but do not infer from final text.

If evidence target selector is not exposed through `evidence_targets`, record warning / not_observable but
do not infer selector from `ExecutionEvidence`.

### Step 7 · Implement `single_path_direct_replay_regression`

Run after Case 1 by default:

```text
execute C
collect evidence
verify direct replay
verify no pending_choice / planner_choice
verify DOM evidence and reporter outcome
```

Do not seed data through direct replay or DB writes.

Do not use global `/exploration/learned-paths?page_template=/items` row count to decide whether this is
single path. Use this eval session's learned path id, session learned actions and execution events.

### Step 8 · Implement artifact writers

Add:

- JSON writer under `artifacts/wagent-eval/`.
- Markdown writer under `docs/testing/results/`.
- redaction pass.
- artifact write error handling exit 4.

### Step 9 · Add package scripts

Add root `package.json` script:

```json
"eval:wagent:items": ".venv/bin/python scripts/evals/wagent_runtime_eval.py"
```

If adding both scripts:

```json
"eval:wagent": ".venv/bin/python scripts/evals/wagent_runtime_eval.py",
"eval:wagent:items": ".venv/bin/python scripts/evals/wagent_runtime_eval.py --case items_closed_loop --case single_path_direct_replay_regression"
```

Prefer the repo's existing script naming style.

### Step 10 · Add user-facing docs

Create `docs/testing/wagent-runtime-eval.md` covering:

- purpose.
- prerequisites.
- service startup.
- command.
- options.
- outputs.
- gate meanings.
- exit codes.
- blocked / fail handling.
- Codex audit workflow.
- live run boundaries.

### Step 11 · Verification

Run static / unit checks:

```bash
uv run ruff check scripts/evals/wagent_runtime_eval.py
git diff --check
```

If tests were added:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
```

Run live eval only if services are available and user did not restrict live execution:

```bash
pnpm run eval:wagent:items
```

Record exact output summary, exit code, JSON artifact path and Markdown result path in `review.md`.

### Step 12 · Fill review

Update `review.md` with:

- implementation summary.
- changed files.
- exact commands and outputs.
- generated artifact paths.
- gate summaries.
- not-run items.
- follow-ups.

Do not claim live eval pass unless the runner actually executed and generated artifacts.

## Commit suggestion

```bash
git add docs/iterations/m11/11.3.6.1-wagent-runtime-eval-runner-core \
  docs/iterations/m11/README.md \
  docs/iterations/m11/m11-plan.md \
  scripts/evals/wagent_runtime_eval.py \
  docs/testing/wagent-runtime-eval.md \
  package.json

git commit -m "feat: add wagent runtime eval runner"
```

Commit only after implementation and verification. For this documentation-only preparation step, do not commit unless
the user asks.

## Review checklist

- [ ] Runner only uses allowed Conversation API and read-only evidence APIs.
- [ ] Runner does not call autonomous-run endpoints.
- [ ] Case gates are hard-coded enough to be reliable, not language-only.
- [ ] `effective_value` is not guessed when unobservable.
- [ ] single-path regression checks no pending choice / planner choice.
- [ ] artifacts are redacted.
- [ ] exit code matches final gate status.
- [ ] `review.md` distinguishes live pass, blocked, fail and not run.
