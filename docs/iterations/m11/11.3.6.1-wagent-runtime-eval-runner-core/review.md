# 复盘 / 评审（Review）

状态：implemented_and_live_eval_passed

## Current Decision

- Decision：closeout_passed
- Code：implemented
- Live eval：pass
- Parent program：accepted_program_plan
- Notes：
  - 11.3.6.1 runner core 已在 commit `6157626` 实现。
  - 2026-05-23 最终收口重跑 `pnpm run eval:wagent:items`，exit code `0`。
  - Eval status：`pass`。
  - JSON artifact：
    `artifacts/wagent-eval/wagent-runtime-eval-20260523T134338Z.json`。
  - Markdown result：
    `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260523T134338Z.md`。
  - Session ID：`88c1412d-d3e5-4039-adc6-fb8d515c794b`。
  - Final rerun evidence commit：`f2d7d55`。

## 2026-05-23 最终收口重跑

- Author：Codex
- Decision：final_closeout_rerun_passed
- Evidence commit：`f2d7d55`
- Command：`pnpm run eval:wagent:items`
- Exit code：`0`
- JSON artifact：
  `artifacts/wagent-eval/wagent-runtime-eval-20260523T134338Z.json`
- Markdown result：
  `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260523T134338Z.md`
- Session ID：`88c1412d-d3e5-4039-adc6-fb8d515c794b`
- Cases：
  - `items_closed_loop`：`pass`，required gates `10/10`，warnings `2`
  - `single_path_direct_replay_regression`：`pass`，required gates `9/9`
- Caveats：
  - `effective_value_B` remains a non-required `not_observable` warning.
  - `evidence_target_item_list` remains a non-required `not_observable` warning.

## 2026-05-23 实际运行与 Closeout

- Runner commit：`6157626 · feat: add wagent runtime eval runner`
- Run commit：`820b066 · docs: mark failure recovery eval ready`
- Command：

```bash
pnpm run eval:wagent:items
```

- Exit code：`0`
- Runner stdout：

```text
status=pass
exit_code=0
json_artifact=artifacts/wagent-eval/wagent-runtime-eval-20260522T162710Z.json
markdown_result=docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260522T162710Z.md
session_id=9af0e6e3-84c3-4771-b72c-25ddb6c2d85b
case=items_closed_loop status=pass
case=single_path_direct_replay_regression status=pass
```

### Gate Summary

| Case | Status | Required gates | Warnings |
|---|---|---:|---:|
| `items_closed_loop` | `pass` | 9 / 9 | 2 |
| `single_path_direct_replay_regression` | `pass` | 8 / 8 | 0 |

Global summary:

```json
{
  "required_total": 17,
  "required_passed": 17,
  "required_failed": 0,
  "required_blocked": 0,
  "warnings": 2
}
```

### Key Evidence

| Evidence | Value |
|---|---|
| Session ID | `9af0e6e3-84c3-4771-b72c-25ddb6c2d85b` |
| Current-session LearnedPath ID | `c4c86c45-3999-4850-ad46-02735f993f80` |
| `learned_path_parameterized` | `LearnedPath c4c86c45-3999-4850-ad46-02735f993f80 has value_slot=item_name` |
| `slot_override_B` | `slot_overrides.item_name=测试项目B-20260522162547` |
| `dom_evidence_verified_B` | `dom_text_present verified target=测试项目B-20260522162547` |
| B reporter | `verification_outcome=verified` |
| `single_candidate_detected` | `one current-session learned action matched c4c86c45-3999-4850-ad46-02735f993f80` |
| `execution_uses_current_learned_path` | `chat_execution_started.learned_path_id=c4c86c45-3999-4850-ad46-02735f993f80` |
| `slot_override_C` | `slot_overrides.item_name=测试项目C-20260522162547` |
| `dom_evidence_verified_C` | `dom_text_present verified target=测试项目C-20260522162547` |
| C reporter | `verification_outcome=verified` |

### Warnings / Not Observable

- `effective_value_B`：`not_observable`，public history/events 未暴露 replay step
  effective value。
- `evidence_target_item_list`：`not_observable`，public history/events 未暴露
  `evidence_targets` selector；runner 没有从 `ExecutionEvidence` 反推 selector。

### Service / Preflight Evidence

| Command / Surface | Actual result | Exit code | Notes |
|---|---|---:|---|
| `docker ps --format ...` | PostgreSQL / Redis / MinIO running, PostgreSQL healthy | 0 | infra already up |
| `pnpm run db:migrate:api` | failed with stale `.venv/bin/alembic` shebang | 126 | local env issue, not product eval result |
| `.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head` | migration completed | 0 | used current root venv Python |
| `.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8001` | API started | N/A | foreground service for eval |
| `pnpm run dev:product` | Vite product-test-site started on `127.0.0.1:5176` | N/A | foreground service for eval |
| `curl -i http://127.0.0.1:8001/health` | HTTP `200`, `database=ok` | 0 | preflight |
| `curl -i http://127.0.0.1:5176/items` | HTTP `200` | 0 | required elevated shell because default sandbox could not connect to port 5176 |

### Boundary

- `verify-scenario`：not run。
- autonomous-run endpoints：not called by runner。
- Console UI smoke：not run。
- Direct replay endpoint / service substitution：not used。
- Runner flow：Conversation API session + dispatch + read-only evidence collection。

### Fresh Closeout Verification

After writing the closeout evidence, the current working tree also contained unrelated, uncommitted
11.3.6.2 failure-recovery eval edits in `scripts/evals/wagent_runtime_eval.py`,
`apps/api/tests/test_wagent_runtime_eval.py`, and
`apps/api/tests/test_conversation_chat_runtime.py`. The 11.3.6.1 verification below is therefore
split between the scoped 11.3.6.1 subset and the full current dirty-tree result.

| Command / Surface | Actual result | Exit code | Notes |
|---|---|---:|---|
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q -k 'not failure_recovery'` | `14 passed, 11 deselected` | 0 | scoped to 11.3.6.1 runner tests |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q` | `11 failed, 14 passed` | 1 | failures are the uncommitted 11.3.6.2 `failure_recovery_menu_safety` tests expecting future gates/case support |
| `uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py` | `All checks passed!` | 0 | lint only |
| `uv run ruff format --check scripts/evals/wagent_runtime_eval.py` | `1 file already formatted` | 0 | runner file only |
| `uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py` | `Would reformat: apps/api/tests/test_wagent_runtime_eval.py` | 1 | caused by unrelated uncommitted 11.3.6.2 test edits |
| `git diff --check` | pass | 0 | no whitespace errors |

## 2026-05-22 原 11.3.6 文档生成（拆分前）

- Author：Codex
- Scope：生成原 11.3.6 runner 七件套，定义 WAgent Runtime Eval Runner、API driver、
  evidence collector、hard gates、artifact、exit code 和安全边界；该设计现已下沉为
  11.3.6.1 runner core。
- Decision：docs_created
- Notes：
  - 本包定位为 M11 working runtime 的本地 eval harness。
  - 本包不新增产品 runtime 能力。
  - 本包不新增内部 Agent 角色。
  - 本包第一版只覆盖 `items_closed_loop` 和
    `single_path_direct_replay_regression`。
  - `failure_recovery_menu_safety` 延后到有稳定 fault injection / eval-only hook 后再做。
  - Runner 直接调用 Conversation API，不使用交互式 `wagent chat` 作为主 harness。
  - Runner 禁止调用 `verify-scenario` 和 autonomous-run endpoints。
  - Codex 在该流程中是审计员，不是 pass / fail 裁判。
  - 未实现代码。
  - 未修改 `package.json`。
  - 未运行 pytest / ruff / build / eval。

## 初始设计评审（Initial Design Review）

- Reviewer：ChatGPT
- Decision：revise_before_ready
- Notes：
  - 方向通过，可以作为 11.3.6 WAgent Runtime Eval Runner 的设计底稿。
  - `evidence_target_item_list` 的 source 需要修订：当前 `ExecutionEvidenceTarget`
    有 selector，但 `ExecutionEvidence` 没有 selector，runner 不得从
    `execution_evidence` 猜 selector。
  - `single_path_direct_replay_regression` 需要明确以当前 eval session 的 learned path /
    learned actions / runtime events 为准，不能用全局 `/items` LearnedPath catalog 数量判断。

## 2026-05-22 文档修订

- Author：Codex
- Decision：revisions_applied
- Notes：
  - 将 `evidence_target_item_list` 改为 conditional gate。
  - 明确 selector 只能来自 request-side / history-side `evidence_targets`，不能来自
    `ExecutionEvidence`。
  - 若 `evidence_targets` 当前 public read surface 不可读，该 gate 只能记为
    `not_observable` / `warning`，并要求补最小只读暴露。
  - 明确 `single_path_direct_replay_regression` 以当前 eval session 的
    `new_learned_path_id`、session `learned_actions`、runtime route events 和
    `chat_execution_started` 为准。
  - 明确全局旧 `/items` LearnedPath rows 不得污染 single-path 判定。
  - `README.md`、`intent.md`、`contract.md`、`technical-design.md`、`test-plan.md`、
    `plan.md`、M11 README 和 `m11-plan.md` 状态切到
    `ready_for_implementation（design review passed，未实现代码）`。

## 2026-05-22 设计状态

- Reviewer：Codex
- Decision：ready_for_implementation
- Final Decision：ready_for_implementation
- Notes：
  - 两个 required contract revisions 已应用。
  - 尚未实现代码，后续实现必须先按 `plan.md` Step 1 复核当前 API / event / history
    可观测性。

## 2026-05-22 迭代拆分

- Author：Codex
- Decision：moved_to_child_iteration
- Notes：
  - 用户确认 11.3.6 更适合作为 WAgent Runtime Eval Program 总体测试规划。
  - 原 11.3.6 runner 实现设计整体下沉为
    `11.3.6.1-wagent-runtime-eval-runner-core`。
  - 本包继续承接已通过评审的 runner core 实现范围：`items_closed_loop` 和
    `single_path_direct_replay_regression`。
  - `11.3.6-wagent-runtime-eval-program` 只作为总体规划和后续 11.3.6.x 路线图。

## 代码评审（Code Review）

- Reviewer：ChatGPT
- Decision：implementation_passed_enter_live_eval_closeout
- Notes：
  - commit `6157626 · feat: add wagent runtime eval runner` 范围通过。
  - 新增 runner、unit tests、testing doc 和 npm scripts；未修改产品 runtime /
    replay / Planner / Reporter 主逻辑。
  - 上轮 false-pass 风险已修复：
    `single_path_direct_replay_regression` 新增
    `execution_uses_current_learned_path` required gate，校验 C turn 的
    `chat_execution_started.payload.learned_path_id`。
  - evidence collection timeout 已统一归类为 `timeout` / exit code `3`。
  - 评审结论：runner implementation 通过；仍需实际运行
    `pnpm run eval:wagent:items` 后回填 closeout。

## 实现收口（Implementation Closeout）

- Author：Codex
- Code commit：`6157626`
- Live eval run commit：`820b066`
- Decision：closeout_passed
- Notes：
  - `pnpm run eval:wagent:items` 已实际运行并返回 exit code `0`。
  - Eval status：`pass`。
  - `items_closed_loop`：`pass`，required gates `9 / 9`。
  - `single_path_direct_replay_regression`：`pass`，required gates `8 / 8`。
  - JSON artifact：
    `artifacts/wagent-eval/wagent-runtime-eval-20260522T162710Z.json`。
  - Markdown result：
    `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260522T162710Z.md`。
  - Session ID：`9af0e6e3-84c3-4771-b72c-25ddb6c2d85b`。

## 最终差异（Final Delta）

### 实际交付

- Runtime eval runner：
  - `scripts/evals/wagent_runtime_eval.py`
- Unit tests：
  - `apps/api/tests/test_wagent_runtime_eval.py`
- User-facing docs：
  - `docs/testing/wagent-runtime-eval.md`
- npm scripts：
  - `eval:wagent`
  - `eval:wagent:items`
- Generated eval evidence：
  - `artifacts/wagent-eval/wagent-runtime-eval-20260522T162710Z.json`
  - `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260522T162710Z.md`
- Closeout update：
  - `docs/iterations/m11/11.3.6.1-wagent-runtime-eval-runner-core/review.md`

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- `effective_value_B` 为 conditional gate；当前 public history/events 未暴露 replay step
  effective value，因此 live result 中记录为 `not_observable`，不阻断 required gate。
- `evidence_target_item_list` 为 conditional gate；当前 public history/events 未暴露
  `evidence_targets` selector，因此 live result 中记录为 `not_observable`，runner 未从
  `ExecutionEvidence` 反推 selector。
- `single_path_direct_replay_regression` 比原 contract 增加了 required gate
  `execution_uses_current_learned_path`，这是代码评审后补强的 false-pass 防线。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本次 live eval 运行了 Conversation API driven runner。未运行：

- `verify-scenario`
- autonomous-run endpoints direct call
- Console UI smoke
- `wagent chat`

Runner 通过 Conversation API 创建 session / dispatch turns，并通过 session / messages /
events / history / LearnedPath detail 只读接口收集证据。没有用 direct replay endpoint 或内部
service substitution 代替 Conversation dispatch。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q` | unit tests pass | `14 passed` | 0 | Pass | test output | run from `apps/api` during implementation review |
| `uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py` | lint pass | `All checks passed` | 0 | Pass | command output | implementation review |
| `uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py` | format pass | `2 files already formatted` | 0 | Pass | command output | implementation review |
| `git diff --check` | whitespace pass | pass | 0 | Pass | command output | implementation review |
| `.venv/bin/python scripts/evals/wagent_runtime_eval.py --help` | CLI help exits 0 | exit `0` | 0 | Pass | command output | implementation review |
| blocked path with invalid API base | blocked artifact | exit `2` | 2 | Pass | JSON / Markdown artifact generated | implementation review |
| `pnpm run eval:wagent:items` | live eval pass | `status=pass`; both cases pass | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260522T162710Z.json` and `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260522T162710Z.md` | 2026-05-23 closeout |
| autonomous run endpoints | prohibited | not called | N/A | Pass | boundary statement and safety review | runner uses Conversation API |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| `verify-scenario` | 本包验证 Conversation runtime eval runner，不走 autonomous verification skill | 不运行 |
| autonomous-run endpoint direct call | AGENTS 边界禁止 | 不运行 |
| Console UI smoke | 本包是 API-driven eval runner | 用户显式要求时另开 |
| `wagent chat` interactive TTY | runner 直接调用 Conversation API | 不运行 |
| non-`/items` cases | 第一版只覆盖 core `/items` closed loop 和 single-path regression | 后续 11.3.6.x 扩展 |
| `effective_value_B` direct step log | public history/events 当前未暴露 | 后续可补最小只读可观测性 |
| `evidence_targets` selector direct read | public history/events 当前未暴露 | 后续可补最小只读可观测性 |

### 后续事项（Follow-ups）

- 在扩展到登录 / 敏感表单 eval 前，把 `slot_overrides` 做按 key 递归脱敏。
- 若希望把 conditional gates 升级为 required gates，先给 public history/events 补最小只读字段：
  replay step effective value 和 request-side `evidence_targets`。
- 11.3.6.2 failure recovery eval 应继续沿用本 runner 的 gate / artifact / exit code 模式，
  但需要独立 contract 和稳定 fault hook。
