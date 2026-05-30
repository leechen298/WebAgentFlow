# 复盘 / 评审（Review）

状态：implementation complete（code review passed，targeted tests passed）

## 2026-05-22 文档生成

- Author：Codex
- Scope：生成 11.3.5.9 七件套，定义 TaskPathPlanner multi-candidate chat integration、
  planner candidate adapter、sanitized pending choice、private map 和 targeted test plan。
- Decision：docs_created
- Notes：
  - 本包属于 P2 planning integration。
  - 本包不改变 11.3.5.6 `/records` 单路径 happy path。
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

## 2026-05-22 二次设计评审通过

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - TaskPathPlanner 语义已修正为 top route plan / warning / risk / uncertainty provider。
  - A/B/C 候选由 Runtime 基于 ranked session candidates 生成。
  - Planner trigger 已改为 `cannot_confidently_select_single_action`，不再依赖 `not user_url`。
  - “继续”优先尊重 pending / active / recovery context。
  - 11.3.5.8 preflight dependency 已补齐。
  - Planner fallback event 和 event slot value 禁止项已补齐。
  - 可以进入实现阶段。

## 代码评审（Code Review）

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - 代码方向通过：Planner 已接入多候选 / 模糊目标路径，但未进入单路径
    `/records` happy path。
  - Planner 未被误用为 A/B/C 候选生成器；Runtime 仍负责生成 visible choices。
  - `pending_choice` visible payload 和 planner events 做了 sanitized 输出，不暴露
    `learned_path_id`、selector、raw slot values 或 private planner payload。
  - 已修复两项 review feedback：
    - visible planner warning 改为泛化文案，raw warning 只保存在 private map。
    - active task + “继续” 优先返回当前任务提示，不进入 Planner。

## 用户反馈

- 用户确认 11.3.5.9 实现可以进入收口；本文件补齐 closeout review。

## 2026-05-22 实现收口

- Author：Codex
- Code commit：`105eb82 feat: add planner-backed chat choices`
- Decision：implementation_complete
- Notes：
  - 多 learned actions 或模糊目标时，Runtime 生成 ranked session candidates，
    再调用 `TaskPathPlanner` 获取 top candidate 的 route / warning / risk /
    uncertainty 信号。
  - Runtime 生成 sanitized A/B/C `pending_choice`；private map 保存真实
    learned action payload 和 planner metadata。
  - URL 只作为 target hint，不再作为跳过 Planner / choice 的条件。
  - pending choice / recovery choice / active task / pending intake / pending target
    优先于 Planner；`继续` 不默认进入 Planner。
  - planner unavailable / fallback 只记录 sanitized event。
  - 单路径明确目标继续直接 replay，不经过 Planner。

## 最终差异（Final Delta）

### 实际交付

- `apps/api/app/services/conversation/chat_runtime.py`
  - 新增 planner candidate adapter，把 session learned actions 转成
    `LearnedPathCandidate`。
  - 新增 `TaskIntent` 构造和 multi-candidate planner path。
  - 新增 `planner_route_choice` private map payload。
  - 新增 sanitized planner progress events / fallback events。
  - 修正 URL + 多候选 / 模糊动作时直接选第一个的问题。
  - 保持单候选明确目标不进 Planner。
  - 保护 pending / active / recovery 优先级。
- `apps/api/tests/test_conversation_chat_runtime.py`
  - 覆盖 planner 多候选、URL + 模糊动作、单路径跳过 Planner、
    Planner unable / fallback、安全事件、visible warning sanitization、
    active task “继续” 优先级和 choice selection execution regression。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- 无阻断偏差。
- 本包没有扩展正式 risk / consent gate，也没有接复杂组合任务多步执行。
- 本包没有把 `PlanningPreviewService` raw user response 直接展示给用户。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本包不运行 `verify-scenario` 或 autonomous run。

如果后续用户显式要求 live smoke，只能作为外部测试操作员通过 `wagent chat`
记录真实输出；不得调用 autonomous-run endpoint，不得编造内部 Agent verdict。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 本包没有 E2E / UI smoke。
- 本包没有 CLI live run。
- 本包验收基于 mocked runtime / planner targeted tests。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| conversation targeted suite | planner choice / pending choice / API sanitizer / router / entry gate pass | 151 passed | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_api.py tests/test_conversation_entry_gate.py tests/test_conversation_router_agent.py` | Re-run during closeout |
| focused planner / choice slice | planner / pending choice / recovery / items regressions pass | 19 passed, 46 deselected | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -k "planner or pending_choice or recovery or items"` | Includes planner-specific regressions |
| scoped Ruff | changed Python / test files clean | All checks passed | 0 | Pass | `uv run ruff check apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/context.py apps/api/app/services/conversation/history.py apps/api/app/routers/conversation.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_api.py apps/api/tests/test_conversation_entry_gate.py apps/api/tests/test_conversation_router_agent.py` | Closeout check |
| `git diff --check` | clean | clean | 0 | Pass | `git diff --check` | Closeout check |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| live `wagent chat` | 本包默认 targeted tests，不要求 live run | 如后续需要手工验证再记录 |
| `verify-scenario` | 本包明确禁止 | 无 |
| autonomous run | 本包明确禁止 | 无 |
| multi-step route execution | 超出本包范围 | 后续独立包 |

### 后续事项（Follow-ups）

- 后续如果引入正式 risk / consent gate，需要独立 contract，不要把 planner warning
  直接当作用户确认语义。
- 如果 history/debug payload 面向普通用户或 LLM prompt，需单独定义 planner
  route metadata 和 learned path id 的可见性策略。
