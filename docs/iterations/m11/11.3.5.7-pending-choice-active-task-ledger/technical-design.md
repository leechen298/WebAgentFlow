# 技术设计（Technical Design）

状态：implementation complete（code review passed，targeted tests passed）

## 当前状态（Current State）

当前 conversation runtime 已有：

| 状态 / 能力 | 当前情况 |
|---|---|
| `pending_intake` | 已用于缺字段追问、补字段续接、过期和 target change guard |
| `pending_target` | 已用于用户只给 URL 后追问操作目标 |
| `last_no_path_reason` | 已用于无路径时记录原因 |
| `learned_actions` | 学习完成后写入 session metadata |
| `/cancel` / cancel command | 已有部分清理逻辑，主要覆盖 pending intake / target |
| `pending_choice` | 未实现 |
| `active_task` | 未实现完整最小 contract |

当前 `_match_session_action()` 在多个候选时返回 `None`，容易让模糊输入落到 no-path /
ask-user，而不是稳定进入 choice mode。本包在这个位置补 code-owned choice handling。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| `pending_choice` 只由 Runtime 写 | 新增 runtime helper `_save_pending_choice()` / `_clear_pending_choice()` | PC-1 / PC-2 | Router 只建议，不写 metadata |
| 用户可见 choice 不含真实 id | visible payload 和 private map 分离 | PC-3 / SEC-1 | trace / response 都要检查 |
| 用户 `A` / `1` / `第一个` 可选中 | deterministic choice parser | PC-4 | 不依赖 LLM |
| 修正输入重新 intake | detect correction text and clear old choice | PC-5 | 不把“不是，我要...”误当无效 choice |
| choice 过期 | `turns_remaining` 递减与清理 | PC-6 | 防止污染后续任务 |
| cancel 清理 pending 和 active task | 扩展 `clear_pending_runtime_context()` | CAN-1 / CAN-2 | 包括中文取消和 `/cancel` |
| `active_task` 最小状态 | metadata helper `_set_active_task()` / `_clear_active_task()` | AT-1 - AT-4 | 不做完整 ledger |
| 旧 happy path 不变 | 单候选仍直接 replay | REG-1 | TaskPathPlanner 不进入 P0 |

## 实现方案（Proposed Implementation）

### 1. Internal models

推荐在 `apps/api/app/services/conversation/context.py` 或新的
`apps/api/app/services/conversation/runtime_state.py` 中定义内部 Pydantic model：

```python
class PendingChoiceOption(BaseModel):
    choice_id: str
    label: str
    description: str | None = None
    intent: Literal[
        "execute_operation",
        "learn_operation",
        "understand_page",
        "cancel",
        "other",
    ]


class PendingChoice(BaseModel):
    type: Literal["pending_choice"] = "pending_choice"
    choice_group_id: str
    question: str
    choices: list[PendingChoiceOption]
    turns_remaining: int = 2
    created_at: datetime


class ActiveTask(BaseModel):
    task_id: str
    kind: Literal[
        "learn_operation",
        "execute_operation",
        "understand_page",
        "clarify",
    ]
    target_url: str | None = None
    goal: str | None = None
    owner: Literal[
        "runtime",
        "learning_agent",
        "web_operation_agent",
        "page_understanding",
    ]
    status: Literal[
        "collecting_requirements",
        "waiting_for_user_input",
        "learning",
        "executing",
        "reporting",
        "completed",
        "failed",
        "cancelled",
    ]
    created_at: datetime
    updated_at: datetime
```

Internal private map 可以保持 `dict[str, dict[str, Any]]`，但必须通过 helper 创建和读取。

### 2. Context Collector

扩展 `ConversationContextBundle`：

```text
pending_choice: PendingChoice | None
active_task: ActiveTask | None
```

LLM-facing context 必须只包含 `pending_choice` visible payload，不包含
`pending_choice_private_map`。如果现有 context 会整体 redaction metadata，需要确保 private map
在传给 Router 之前被移除。

### 3. Entry Gate

`Conversation Entry Gate` 当前在有 `pending_intake` / `pending_target` 时强制进入 heavy
runtime。本包应补：

```text
pending_choice_exists
active_task_exists
```

有 `pending_choice` 时，短输入如 `A`、`1`、`第一个` 不能被当作普通闲聊直接回复。

### 4. Choice Handler

在 heavy runtime 早期增加一个 code-owned branch：

```text
if pending_choice exists:
  if cancel input:
    clear pending + active_task
  elif choice input matches:
    resolve private map
    clear pending_choice
    dispatch selected branch
  elif correction input:
    clear pending_choice
    continue normal intake with current message
  else:
    decrement turns_remaining or expire
```

解析私有映射后，本包只要求能进入已有 runtime branch。对于 learned action：

```text
selected kind = learned_action
-> load learned action summary from private map
-> if target / runtime slots sufficient, call existing execution branch
-> if slots missing, ask_user_for_missing_info and write pending_intake
```

本包不通过 TaskPathPlanner 生成 choices；只使用已有 `learned_actions` 或测试构造的
候选。

### 5. Pending choice creation

创建 choice 的最小触发：

| Trigger | Mechanism |
|---|---|
| 多个 matching learned actions | `_match_session_action()` 返回多个候选时创建 choice |
| 低置信 / 模糊目标且 learned actions 多个 | runtime 根据 context learned_actions 创建 choice |
| 用户只给 URL 且已有多个 learned actions | 可继续用 pending_target 或创建 choice；实现应优先保持当前 pending_target 行为，避免扩大范围 |

建议先把 `_matching_actions()` 拆成可复用候选函数，保留单候选直接执行，多候选进入
`pending_choice`。

### 6. Active task helpers

新增 helpers：

```text
_set_active_task(session_id, task)
_update_active_task(session_id, status, ...)
_clear_active_task(session_id)
```

插入点：

| Branch | Active task |
|---|---|
| ask missing info / pending choice | `kind=clarify`, `status=waiting_for_user_input` |
| start learning | `kind=learn_operation`, `status=learning` |
| learning success | `completed` then clear live active task |
| learning fail | `failed` |
| start replay | `kind=execute_operation`, `status=executing` |
| reporter building | optional `reporting` |
| execution success | `completed` then clear live active task |
| execution fail | `failed` |
| cancel | `cancelled` then clear live active task |

### 7. Cancel cleanup

扩展 `clear_pending_runtime_context()` 和 Runtime cancel branch，清理：

```text
pending_intake
pending_target
pending_choice
pending_choice_private_map
last_no_path_reason
active_task
```

同时调用 `clear_pending_sensitive_values(session_id)`。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 不新增 route | 只读 history / events 继续工作 |
| API response schema | No | 不改 public response schema | metadata 可能新增 key |
| Database schema / migration | No | 使用 session metadata JSON | 旧 session 兼容 |
| CLI | No | `wagent chat` 行为增强 | 不新增 CLI 参数 |
| Console UI | No | 不改 Console | N/A |
| Conversation events | Maybe | 可选新增安全事件 payload | 不暴露 private map |
| Replay execution | No | 只在选中 learned action 后复用已有 replay | 不改 replay schema |
| Reporter | No | 不改 reporter | N/A |
| Worker / async jobs | No | 不涉及 worker | N/A |
| Tests / fixtures | Yes | 新增 conversation runtime targeted tests | 不新增 live autonomous tests |
| Docs | Yes | 本迭代文档和 review 更新 | 向后兼容 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No DB migration。

Session metadata 新增 key：

```json
{
  "pending_choice": {
    "type": "pending_choice",
    "choice_group_id": "choice-group-...",
    "question": "你想让我做哪个操作？",
    "choices": [
      {
        "choice_id": "A",
        "label": "新增项目",
        "intent": "execute_operation"
      }
    ],
    "turns_remaining": 2,
    "created_at": "2026-05-21T..."
  },
  "pending_choice_private_map": {
    "A": {
      "kind": "learned_action",
      "learned_path_id": "..."
    }
  },
  "active_task": {
    "task_id": "...",
    "kind": "clarify",
    "owner": "runtime",
    "status": "waiting_for_user_input",
    "created_at": "2026-05-21T...",
    "updated_at": "2026-05-21T..."
  }
}
```

## 服务 / 模块设计（Service / Module Design）

Expected touched files:

| File | Planned change |
|---|---|
| `apps/api/app/services/conversation/context.py` | Add PendingChoice / ActiveTask parsing and context fields |
| `apps/api/app/services/conversation/entry_gate.py` | Treat pending choice / active task as runtime-forcing context |
| `apps/api/app/services/conversation/chat_runtime.py` | Add choice handler, metadata helpers, active task updates, cancel cleanup |
| `apps/api/app/services/conversation/router_agent.py` | Ensure router payload gets visible choice only, no private map |
| `apps/api/app/services/conversation/intake.py` | Optional correction / choice phrase fallback helpers if needed |
| `apps/api/tests/test_conversation_chat_runtime.py` | Main targeted coverage |
| `apps/api/tests/test_conversation_entry_gate.py` | Pending choice forces heavy runtime |
| `apps/api/tests/test_conversation_router_agent.py` | Router trace does not expose private ids, if existing tests make this practical |

## 数据流（Data Flow）

### Multi-candidate choice

```text
User: 帮我处理一下这个页面
  |
  v
Intake: low confidence / vague execute intent
  |
  v
Context: multiple learned_actions
  |
  v
Runtime Adjudicator
  |
  +-- builds visible choices A/B/C
  +-- writes pending_choice
  +-- writes pending_choice_private_map
  +-- writes active_task(kind=clarify, waiting_for_user_input)
  |
  v
WAgent response: A/B/C question
```

### Choice selection

```text
User: A
  |
  v
Entry Gate: pending_choice exists -> heavy runtime
  |
  v
Runtime choice handler
  |
  +-- parse A
  +-- lookup private map internally
  +-- clear pending_choice
  +-- update active_task
  |
  v
existing execution / ask-missing-info branch
```

### Cancel

```text
User: 算了
  |
  v
Runtime cancel handler
  |
  +-- clear pending_intake
  +-- clear pending_target
  +-- clear pending_choice
  +-- clear pending_choice_private_map
  +-- clear last_no_path_reason
  +-- clear active_task
  +-- clear sensitive pending values
  |
  v
WAgent response: 已取消当前任务。
```

## 状态推导（Status / State Derivation）

优先级：

1. Cancel input always wins.
2. Existing `pending_choice` is handled before normal intake.
3. Existing `pending_intake` / `pending_target` behavior remains intact.
4. Single matched learned action continues direct execution.
5. Multiple matched learned actions create choice.
6. Expired / invalid pending choice is cleared before new task handling.

## 兼容性（Compatibility）

- No existing session metadata key is removed.
- Corrupt `pending_choice` should be ignored and cleared, not raise 500.
- Missing private map for a visible choice should clear choice and ask the user to restate the operation.
- Single-path `/items` happy path remains unchanged.
- Sensitive values remain redacted through existing `redact_sensitive_payload`.

## 失败 / 边界情况（Failure / Edge Cases）

| Case | Handling |
|---|---|
| User answers `A` without pending choice | Ask what they want to do; do not execute |
| Choice id exists but private map missing | Clear pending choice, ask user to restate |
| Private map learned path no longer exists | Clear choice, report learned action unavailable |
| User gives new URL while choice pending | Clear old choice and treat message as new target |
| User says correction text | Clear old choice and rerun intake |
| `turns_remaining` reaches zero | Clear choice and ask user to restate |
| Cancel during learning / execution | Mark active task cancelled when possible; clear metadata |

## 非目标（Non-goals）

- No TaskPathPlanner integration.
- No failure recovery menu.
- No automated relearn / retry.
- No direct browser action changes.
- No DB migration.
- No live autonomous verification.

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| PendingChoice creation | multi-candidate or vague input creates safe visible choice | `test-plan.md` PC-* |
| Choice selection | A / 1 / 第一个 selects internally mapped choice | `test-plan.md` SEL-* |
| Private map safety | no learned_path_id leaks to Router prompt / WAgent response / LLM trace | `test-plan.md` SEC-* |
| ActiveTask | learning / execution / clarify writes and clears task state | `test-plan.md` AT-* |
| Cancel / expiry | pending and active task cleanup | `test-plan.md` CAN-* / EXP-* |
| Regression | P0 `/items` single path still works through targeted tests | `test-plan.md` REG-* |

## 验证命令入口（Validation Commands）

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py \
  tests/test_learning_run_service.py

uv run ruff check \
  apps/api/app/services/conversation/context.py \
  apps/api/app/services/conversation/entry_gate.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/conversation/router_agent.py \
  apps/api/tests/test_conversation_chat_runtime.py

git diff --check
```
