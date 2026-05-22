# 复盘 / 评审（Review）

状态：ready_for_implementation（design review passed，未实现代码）

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

- Reviewer：N/A
- Decision：not_started
- Notes：
  - 尚未实现代码。

## 实现收口（Implementation Closeout）

- Author：N/A
- Code commit：N/A
- Decision：not_started
- Notes：
  - 尚未实现代码。

## 最终差异（Final Delta）

### 实际交付

- 文档包：
  - `README.md`
  - `intent.md`
  - `contract.md`
  - `technical-design.md`
  - `test-plan.md`
  - `plan.md`
  - `review.md`

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- N/A，尚未实现。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本次文档生成未运行：

- `verify-scenario`
- autonomous run
- Console UI smoke
- live Conversation API eval
- `wagent chat`

后续实现如需 live eval，只能通过 runner 调 Conversation API，并在 result / review 中记录真实
session id、artifact path、gate summary 和 exit code。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| pytest | not run | not run | N/A | Skip | N/A | docs-only generation |
| ruff | not run | not run | N/A | Skip | N/A | no code implemented |
| eval runner | not run | not run | N/A | Skip | N/A | runner not implemented |
| autonomous run | prohibited | not run | N/A | Skip | N/A | boundary maintained |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| runner implementation | 当前只写迭代文档 | 用户确认后进入实现 |
| unit tests | 无 runner 代码 | 实现阶段补 |
| live eval | runner 未实现 | 实现阶段按 `test-plan.md` 执行 |
| generated artifacts | runner 未实现 | 实现阶段生成 |

### 后续事项（Follow-ups）

- 用户确认 11.3.6.1 文档后，进入实现阶段。
- 实现前先核对当前 Conversation API request / response schema。
- 如果 step log `effective_value` 当前不可读，只允许 warning / not_observable，并记录只读
  可观测性 follow-up。
