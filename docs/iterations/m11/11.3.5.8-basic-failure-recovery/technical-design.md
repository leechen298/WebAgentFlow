# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未开始实现）

## 当前状态（Current State）

当前 11.3.5.x 已具备：

| 能力 | 当前状态 |
|---|---|
| `/records` P0 closed loop | 已有实跑 pass 证据 |
| parameterized replay | 已有 `value_slot` / `slot_overrides` |
| execution evidence | 已有 `ExecutionEvidence` |
| TaskResultReporter adapter | 已有 verified / needs_review / uncertain 路径 |
| `pending_choice` | 依赖 11.3.5.7 实现；实现前必须 preflight 确认 |
| `pending_choice_private_map` | 依赖 11.3.5.7 实现；实现前必须确认 public session / history safety |
| `active_task` | 依赖 11.3.5.7 实现；实现前必须 preflight 确认 |

当前缺口是：失败 / 不确定后，用户缺少一个稳定恢复入口。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry |
|---|---|---|
| 失败时不编造成果 | reporter outcome / replay status 决定回复 | FR-1 / FR-2 |
| 展示 A/B/C 恢复选项 | 复用 `pending_choice` visible payload | RC-1 |
| private map 不外泄 | private map only in metadata, public sanitizer / trace sanitizer | SEC-1 / SEC-2 |
| retry 复用原 payload | private map 保存 learned path、target、slot overrides | RT-1 / RT-2 |
| relearn 不自动执行 | selected branch enters learning only | RL-1 |
| cancel 清理状态 | reuse `clear_pending_runtime_context()` | CAN-1 |
| TaskPathPlanner 不介入 | retry uses direct replay only | REG-1 |

## 实现方案（Proposed Implementation）

### 1. Recovery trigger points

主要接入 `InteractiveChatRuntime._execute_matched_action()` 的 replay/report 结果处理：

```text
replay_summary.replay_status failed
report.outcome in failed / blocked / needs_review / uncertain
drift_status not none
execution evidence missing target
```

注意：verified happy path 不应进入 recovery。

### 2. Recovery offer helper

新增内部 helper：

```python
def _offer_basic_failure_recovery(
    *,
    session_id: str,
    action: dict[str, Any],
    slot_overrides: dict[str, str],
    replay_summary: ConversationReplaySummary | None,
    report: TaskResultReport | None,
    failure_class: str,
    events: list[str],
    message_id: str | None,
    previous_status: str,
) -> DispatchResult:
    ...
```

职责：

- 生成保守失败说明。
- 构造 recovery `pending_choice` visible payload。
- 构造 private map。
- 设置 `active_task.status=waiting_for_user_input`。
- 记录 `failure_recovery_offered` progress event。

### 3. Recovery pending choice

visible choices：

```json
[
  {"choice_id": "A", "label": "重试执行该操作", "intent": "execute_operation"},
  {"choice_id": "B", "label": "重新学习", "intent": "learn_operation"},
  {"choice_id": "C", "label": "取消", "intent": "cancel"}
]
```

private map：

```json
{
  "A": {
    "kind": "retry_replay",
    "learned_path_id": "internal",
    "target_url": "<runtime target URL>",
    "slot_overrides": {"record_name": "测试项目B"},
    "failure_reason": "evidence_missing",
    "retry_count": 0
  },
  "B": {
    "kind": "relearn_operation",
    "target_url": "<runtime target URL>",
    "action_alias": "新增项目",
    "fill_values": {"record_name": "测试项目B"},
    "failure_reason": "evidence_missing"
  },
  "C": {"kind": "cancel", "failure_reason": "evidence_missing"}
}
```

`<runtime target URL>` 必须来自当前 runtime / learned action 的目标 URL。`localhost:<fixture-port>`
只能作为本地示例端口，不能在实现中硬编码。

### 4. Choice selection integration

11.3.5.7 的 pending choice selection handler 需要识别新的 private map kinds：

| kind | Runtime branch |
|---|---|
| `retry_replay` | 调 direct replay retry helper |
| `relearn_operation` | 进入 learning branch 或缺信息追问 |
| `cancel` | 清理 runtime context |
| `learned_action` | 保持 11.3.5.7 既有行为 |

### 5. Retry helper

新增内部 helper：

```python
def _retry_replay_from_recovery_choice(...):
    ...
```

要求：

- 不走 TaskPathPlanner。
- 不走 Router。
- 使用 private map 中的 `learned_path_id` / `target_url` / `slot_overrides`。
- 重新构造 evidence targets。
- 记录 retry started event。
- 每次用户选择 A 只触发一次 replay retry。
- 如果 retry 再次失败，允许再次 offer recovery，但必须递增 `retry_count`，系统不得自动再次 retry。

### 6. Relearn helper

新增内部 helper：

```python
def _start_relearn_from_recovery_choice(...):
    ...
```

要求：

- 使用原 target URL / action alias 作为 learning intent。
- 如果 fill values 足够，可以组织 learning request。
- 如果缺 target 或 goal，写 pending 并追问。
- 学习成功后只回复已重新学习，不自动执行。

### 7. Response wording

示例：

```text
这次操作已经执行过，但我没有拿到足够证据确认结果。我没有在列表中看到“测试项目B”。

你可以选择：
A. 重试执行该操作（可能会重复新增 / 提交）
B. 重新学习
C. 取消
```

blocked 示例：

```text
我找到了已学习路径，但当前页面和学习时的页面不匹配，所以没有继续确认执行结果。

你可以选择：
A. 重试执行该操作
B. 重新学习
C. 取消
```

### 8. Security / redaction

- Recovery visible payload 不得包含 `learned_path_id`。
- progress event 可以记录 failure class，但不能包含 private map。
- session public API 继续通过 `session_public_payload()` 过滤 private map。
- 如果 future slot 包含 credential / token / secret，不得明文记录在 visible payload 或 LLM trace。

Recovery events 不得包含：

```text
pending_choice_private_map
learned_path_id
slot_overrides
evidence_targets
ReplayAction
selector
private retry / relearn payload
```

Recovery events 只允许记录 public diagnostics，例如 `failure_class`、`choice_group_id`、
`selected_choice_id`、`recovery_kind`、`retry_count`、public action alias。

## 预期触及文件

- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/context.py`（仅当需要扩展内部 model）
- `apps/api/app/services/conversation/history.py`（仅当 private payload sanitizer 需要扩展）
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_conversation_api.py`（如新增 public sanitizer 回归）

## 不触及

- 不改 `apps/fixture-site`。
- 不改 TaskPathPlanner。
- 不改 TaskResultReporter outcome enum。
- 不新增 DB migration。
- 不新增 public endpoint。
