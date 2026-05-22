# 技术设计（Technical Design）

状态：draft_docs（待评审，未开始实现）

## 当前状态（Current State）

当前代码已具备：

| 能力 | 当前状态 |
|---|---|
| `TaskPathPlanner` | 已实现 deterministic service，输入 `TaskIntent` + `LearnedPathCandidate[]` |
| `LearnedPathRetrievalService` | 已实现 repo-backed ranking，但 chat 本包默认不扩大到全局 catalog |
| `PlanningPreviewService` | 已实现 preview path，但 raw response 会显示 selected path id |
| `pending_choice` | 已实现 visible choice + private map |
| `active_task` | 已实现最小 waiting / executing / learning 状态 |
| Chat multi-candidate | 当前 runtime 能直接把多个 session learned actions 转成 choice |
| `/items` single path | 已验证直接 replay happy path |

当前缺口是：chat multi-candidate path 没有经过 TaskPathPlanner，无法利用已有 ranking /
warnings / risk hints / ambiguity 语义。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry |
|---|---|---|
| 单路径不走 Planner | `_match_session_action()` 命中唯一 action 后直接 replay | REG-1 |
| 多候选走 Planner | `_handle_execute_task()` 多候选分支调用 planner adapter | PL-1 |
| Planner 不引入 session 外 path | adapter 只从 `metadata.learned_actions` 构造 candidates | SEC-1 |
| visible choice 不含 path id | sanitized pending choice builder | SEC-2 |
| private map 保存 path id | `pending_choice_private_map` internal only | PL-4 |
| 选择后执行 selected path | existing `_handle_pending_choice_selection()` branch | EX-1 |
| recovery 不走 Planner | recovery private choice kind remains separate | REG-2 |

## 实现方案（Proposed Implementation）

### 1. Chat planner adapter

建议在 `chat_runtime.py` 内新增 internal helpers，保持本包最小改动：

```python
def _build_task_intent_for_planner(
    raw_input: str,
    intake: ConversationIntakeResult | None,
    *,
    target_url: str | None,
) -> TaskIntent:
    ...

def _planner_candidates_from_session_actions(
    actions: list[dict[str, Any]],
    *,
    learned_path_repo: LearnedPathRepository,
) -> list[LearnedPathCandidate]:
    ...
```

如果实现后 `chat_runtime.py` 继续膨胀，可以在后续重构包拆出
`services/conversation/planner_bridge.py`。本包不强制新增文件。

### 2. Candidate adapter

输入：

```text
current session learned_actions
LearnedPathRepository lookup result
```

输出：

```text
LearnedPathCandidate[]
```

规则：

- 只为当前 session learned actions 构造 candidate。
- repo 行存在时读取 `scenario`、`page_template`、`trust`、`hit_count`、`trust_reason`。
- repo 行不存在时可以跳过该候选，或用 session action 生成 provisional candidate；
  但必须记录 warning，并且不得引入外部 path。
- `deprecated` candidate 不应出现在最终可执行 choice。

### 3. TaskIntent adapter

映射建议：

```python
TaskIntent(
    raw_text=raw_input,
    normalized_goal=intake.action.canonical_goal or intake.action.goal,
    target_page_hint=_target_page_hint(intake, target_url),
    scenario_hint=intake.action.canonical_goal or intake.action.goal,
    uncertainty=["vague_goal"] if _looks_like_vague_operation_request(raw_input) else [],
)
```

实现要避免把 slot value 明文塞入 planner prompt / event。`item_name` 等运行时参数仍走
`slot_overrides`，不作为 planner 排名的 private 执行授权。

### 4. Runtime 接入点

当前 `_handle_execute_task()` 的多候选分支大致是：

```text
action = _match_session_action(...)
if action is None:
  candidates = _matching_session_actions(...)
  if len(candidates) > 1 and not user_url:
    _handle_pending_choice_question(...)
```

11.3.5.9 目标：

```text
if len(candidates) > 1 and not user_url:
  return _handle_planner_pending_choice_question(...)
```

`_handle_planner_pending_choice_question()` 负责：

1. 构造 `TaskIntent`。
2. 构造 `LearnedPathCandidate[]`。
3. 调 `TaskPathPlanner.plan(task_intent, candidates)`。
4. 将 planner output 转成 sanitized `pending_choice`。
5. 写 `pending_choice_private_map`。
6. 写 `active_task(status=waiting_for_user_input)`。
7. 记录 sanitized `planner_choice_created` event。

### 5. Pending choice mapping

visible choice 示例：

```json
{
  "choice_id": "A",
  "label": "新增项目",
  "description": "/items · confirmed · 需要你确认后执行",
  "intent": "execute_operation"
}
```

private map 示例：

```json
{
  "A": {
    "kind": "planner_route_choice",
    "learned_path_id": "<internal>",
    "target_url": "<runtime target URL>",
    "action_alias": "新增项目",
    "page_template": "/items",
    "slot_overrides": {
      "item_name": "测试项目B"
    },
    "planner_summary": {
      "candidate_index": 0,
      "purpose": "Execute learned path ...",
      "confirmation_required": true,
      "warnings": ["Retrieval match: ..."],
      "risk_hints": [],
      "uncertainty": []
    }
  }
}
```

注意：private map 可以含 `learned_path_id` 和 `slot_overrides`；visible choice / event /
WAgent reply 不得含这些字段。

### 6. Selection execution

推荐在 `_handle_pending_choice_selection()` 中支持：

```text
kind == "planner_route_choice"
```

处理方式等同 learned action：

1. 用 private map 的 `learned_path_id` 找 session action。
2. 如果找不到，走 choice unavailable。
3. 用 private map 的 `slot_overrides` 调 `_execute_matched_action()`。
4. 清理 pending choice。
5. 记录 sanitized `planner_choice_selected` event。

不需要新建 replay path。

### 7. Planner unable path

如果 planner 返回 `route_plan is None` 或候选为空：

```text
我还不能可靠判断要执行哪个已学习操作。你可以说得更具体，或者重新学习一个操作。
```

状态：

- 不执行 replay。
- 不写可执行 private map。
- 可以写 `last_no_path_reason`。
- 可以保留 / 设置 `active_task(kind=clarify, status=waiting_for_user_input)`。

### 8. Event / trace safety

`planner_candidates_generated` / `planner_choice_created` event 只记录：

```json
{
  "progress_kind": "planner_choice_created",
  "candidate_count": 3,
  "choice_group_id": "choice-group-...",
  "confirmation_required": true,
  "planner_warning_count": 2,
  "planner_risk_count": 1
}
```

不得记录：

```text
learned_path_id
selected_path_id
slot_overrides
route_plan.steps
pending_choice_private_map
```

## 文件 / 模块

Planned implementation files:

- `apps/api/app/services/conversation/chat_runtime.py` - planner adapter helpers、
  multi-candidate branch、planner choice private map、selection handling。
- `apps/api/tests/test_conversation_chat_runtime.py` - chat integration tests。
- `apps/api/tests/test_task_planning_preview.py` - 如 adapter 需要复用 preview contract，可补安全回归。
- `docs/iterations/m11/11.3.5.9-taskpathplanner-multi-candidate-chat-integration/review.md` -
  实现证据。

预计不修改：

- `apps/api/app/services/task_planning/planner.py` - planner 已存在，本包应当消费它。
- `apps/api/app/services/task_planning/retrieval.py` - 除非实现发现 session-candidate adapter
  必须复用 ranking helper；默认不改。
- `apps/api/app/schemas/task_planning.py` - 不新增 schema。

## 回滚策略

- 如果 Planner adapter 出现风险，可退回 11.3.5.7 直接 pending_choice 行为。
- 回滚时必须保留 single-path `/items` happy path、failure recovery 和 pending_choice
  safety tests。
