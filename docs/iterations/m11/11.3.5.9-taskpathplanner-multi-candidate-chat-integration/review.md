# 复盘 / 评审（Review）

状态：draft_docs（revise_before_ready，待二次评审，未开始实现）

## 2026-05-22 文档生成

- Author：Codex
- Scope：生成 11.3.5.9 七件套，定义 TaskPathPlanner multi-candidate chat integration、
  planner candidate adapter、sanitized pending choice、private map 和 targeted test plan。
- Decision：docs_created
- Notes：
  - 本包属于 P2 planning integration。
  - 本包不改变 11.3.5.6 `/items` 单路径 happy path。
  - 本包复用 11.3.5.7 `pending_choice` / private map。
  - 本包依赖 11.3.5.8 failure recovery 的实现能力，但不扩展 recovery。
  - 进入实现前必须 preflight 确认 11.3.5.8 closeout 状态和 targeted tests。
  - 未实现代码。
  - 未运行 pytest / ruff / build。
  - 未运行 `verify-scenario` 或 autonomous run。

## 设计评审（Design Review）

- Reviewer：ChatGPT
- Decision：revise_before_ready
- Notes：
  - 方向通过，但不能直接标 `ready_for_implementation`。
  - 现有 `TaskPathPlanner.plan()` 只输出单一 top `route_plan` 和
    confirmation / risk / uncertainty，不输出多候选列表；文档必须改为 Runtime 生成 A/B/C。
  - Planner 触发条件不得使用 `len(candidates) > 1 and not user_url`；URL 只是 target hint。
  - “继续”必须先尊重 pending choice / recovery choice / active task / pending intake /
    pending target，不能默认进入 Planner。
  - 11.3.5.8 必须作为实现完成前置检查；实现前要确认 recovery choice、retry / relearn /
    cancel、private payload safety 和 targeted tests 通过。

## 2026-05-22 文档修订

- Author：Codex
- Decision：revisions_applied
- Notes：
  - 将 Planner 语义修正为 top route plan / warning / risk / uncertainty provider。
  - 明确 A/B/C 候选列表由 Runtime 基于 ranked session candidates 生成。
  - 修改 planner trigger 为 `len(candidates) > 1 and cannot_confidently_select_single_action`。
  - 补充 live context 优先级，避免“继续”绕过 pending / active / recovery。
  - 补充 11.3.5.8 implementation preflight dependency。
  - 补充 planner fallback sanitized event 和 event slot value 禁止项。
  - 尚未实现代码，需二次设计评审。

## 代码评审（Code Review）

- Reviewer：
- Decision：pending
- Notes：

## 用户反馈

- N/A。

## 最终差异（Final Delta）

### 实际交付

- 待实现。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- 待实现。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本包不运行 `verify-scenario` 或 autonomous run。

如果后续用户显式要求 live smoke，只能作为外部测试操作员通过 `wagent chat`
记录真实输出；不得调用 autonomous-run endpoint，不得编造内部 Agent verdict。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 当前没有 E2E / UI smoke。
- 当前没有 CLI live run。
- 当前只有文档生成。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| pytest targeted chat runtime | planner choice tests pass | not run | N/A | Skip | N/A | 文档生成阶段 |
| planner regression tests | existing planner tests pass | not run | N/A | Skip | N/A | 文档生成阶段 |
| scoped Ruff | changed Python files clean | not run | N/A | Skip | N/A | 文档生成阶段 |
| `git diff --check` | clean | not run | N/A | Skip | N/A | 文档生成阶段 |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| Python tests | 尚未实现代码 | 实现阶段必须运行 |
| Ruff | 尚未实现代码 | 实现阶段必须运行 |
| live `wagent chat` | 本包默认 targeted tests，不要求 live run | 如后续需要手工验证再记录 |
| `verify-scenario` | 本包明确禁止 | 无 |
| autonomous run | 本包明确禁止 | 无 |
| multi-step route execution | 超出本包范围 | 后续独立包 |

### 后续事项（Follow-ups）

- 设计评审通过后，把状态改为 `ready_for_implementation`。
- 实现阶段必须守住 TaskPathPlanner 不进入单路径 happy path 的边界。
- 实现阶段不得把 `PlanningPreviewService` raw response 直接展示给用户。
