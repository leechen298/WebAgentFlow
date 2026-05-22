# 契约（Contract）

状态：implementation complete（code review passed，targeted tests passed）

## 概念 / 边界契约

### Pending Choice

`pending_choice` 是 Runtime 写入 conversation session metadata 的用户澄清状态。
它用于“下一轮用户需要从若干候选中选择一个”的场景。

`pending_choice` 是 code-owned runtime state：

- Router 可以推荐 ask / clarify，但不能写 `pending_choice`。
- LLM 可以辅助理解用户话语，但不能直接解析真实 `learned_path_id`。
- Runtime / Orchestrator 负责创建、解析、过期和清理。

### Choice Visible Payload

用户和 LLM 可见层只允许看到 choice id、label、description、intent 等安全字段：

```ts
type PendingChoice = {
  type: "pending_choice";
  choice_group_id: string;
  question: string;
  choices: Array<{
    choice_id: string;
    label: string;
    description?: string;
    intent:
      | "execute_operation"
      | "learn_operation"
      | "understand_page"
      | "cancel"
      | "other";
  }>;
  turns_remaining: number;
  created_at: string;
};
```

`choices[*]` 不得包含：

```text
learned_path_id
selector
browser_action
slot_overrides
ReplayAction
private mapping payload
```

### Private Choice Map

真实执行所需的内部映射只允许 Runtime / Orchestrator 使用：

```ts
type PendingChoicePrivateMap = Record<
  string,
  {
    kind: "learned_action" | "new_learning" | "understand_page" | "cancel";
    learned_path_id?: string;
    action_alias?: string;
    target_url?: string;
    page_template?: string;
  }
>;
```

推荐 metadata key：

```text
pending_choice
pending_choice_private_map
```

如果实现选择不同 key，必须保持同等安全边界：真实 `learned_path_id` 不得出现在
用户可见回复、Router prompt、LLM trace、progress event 或 `pending_choice` visible object。

### Active Task

`active_task` 是最小运行态账本，不是完整 RuntimeLedger。它只记录当前 runtime 正在做什么，
方便后续“继续 / 取消 / 失败恢复”有状态基础。

```ts
type ActiveTask = {
  task_id: string;
  kind:
    | "learn_operation"
    | "execute_operation"
    | "understand_page"
    | "clarify";
  target_url?: string;
  goal?: string;
  owner:
    | "runtime"
    | "learning_agent"
    | "web_operation_agent"
    | "page_understanding";
  status:
    | "collecting_requirements"
    | "waiting_for_user_input"
    | "learning"
    | "executing"
    | "reporting"
    | "completed"
    | "failed"
    | "cancelled";
  created_at: string;
  updated_at: string;
};
```

本包只做最小字段，不做完整 ledger event sourcing。

## 状态 / 结果契约

### PendingChoice Lifecycle

| 状态 | 触发 | Runtime 行为 |
|---|---|---|
| create | 多候选、低置信、目标模糊 | 写 `pending_choice` 和 private map，回复 A/B/C |
| select | 用户输入 `A` / `1` / `第一个` / label | 代码解析 choice，清理 `pending_choice`，继续对应 runtime branch |
| revise | 用户输入“不是，我要...” | 清理旧 choice，把新消息重新送入 intake |
| cancel | 用户输入“算了”或 `/cancel` | 清理 choice 和 active task，回复已取消 |
| expire | `turns_remaining <= 0` | 清理 choice，追问用户重新说明目标 |

默认 `turns_remaining = 2`。每次未命中 choice 的普通用户消息应递减一次。

### ActiveTask Lifecycle

| 阶段 | 写入 / 更新 |
|---|---|
| clarify start | `kind=clarify`, `status=waiting_for_user_input` |
| learning start | `kind=learn_operation`, `status=learning` |
| execution start | `kind=execute_operation`, `status=executing` |
| reporting | 可选更新 `status=reporting` |
| completed | 标记 `completed` 后清理或保留最近完成摘要 |
| failed | 标记 `failed` 并保留最小失败摘要 |
| cancelled | `/cancel` 或中文取消时标记 `cancelled`，随后清理 live active task |

本包不要求保存完整历史；conversation events 仍是可审计历史来源。

## Schema / API 契约

本包默认不新增 public API endpoint，不新增 DB migration。

允许修改：

- conversation session `metadata_json`
- conversation context schema / internal Pydantic model
- conversation event payload
- targeted tests

可选新增 event type。如果不新增 enum，可以复用现有 `CHAT_PROGRESS_RECORDED`、
`CHAT_NO_PATH`、`AGENT_TRACE_RECORDED` 等事件记录安全 payload。无论哪种实现，
event payload 都不得暴露 private map 给 LLM-facing trace。

## Choice 解析契约

Deterministic matching 优先级：

1. `A` / `B` / `C` / `D` 对应 choices 顺序。
2. `1` / `2` / `3` / `4` 对应 choices 顺序。
3. `第一个` / `第二个` / `第三个` / `第四个`。
4. 精确匹配 `choice_id`。
5. 精确或归一化匹配 label。

如果仍无法匹配：

- 如果消息像修正意图（例如“不是，我要搜索”），清理旧 choice，重新 intake。
- 否则递减 `turns_remaining` 并继续追问。

## Evidence / Observation 契约

本包不新增 DOM evidence contract。

必须记录的 runtime evidence：

| Evidence | Required | 说明 |
|---|---:|---|
| `pending_choice` visible payload | Yes | 只能包含 safe choice fields |
| private map existence | Yes | 可在 unit test 中检查，不写入 LLM trace |
| choice select event / branch | Yes | 用户 A/B/C 后进入正确 runtime branch |
| active_task start / completion | Yes | metadata 或 event 可查 |
| cancel cleanup | Yes | pending 和 active task 清干净 |
| no leaked learned_path_id | Yes | Router trace / LLM trace / WAgent reply 中不能出现真实 id |

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：本包增强 L3 actual work 的 conversation runtime 状态边界，不新增 Agent role。
- Scope boundary 对齐：只处理 WebAgentFlow 如何安全操作网页前的用户选择和状态，不引入外部业务系统。
- Roadmap / milestone 对齐：属于 11.3.5.7 P1 runtime robustness。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- 旧 session 没有 `pending_choice` / `active_task` 时必须继续按现有逻辑运行。
- 既有 `pending_intake` / `pending_target` 行为保持兼容。
- 既有 `/items` 单路径 happy path 不应被 choice mode 干扰。
- Existing learned actions summary 结构保持兼容。
- `pending_choice` 过期或损坏时必须安全清理并追问，不抛 500。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变。
- Replay status semantics：不变。
- TaskResultReporter outcome：不变。
- Recovery / abort 边界：不进入 failure recovery，cancel 只做当前 runtime state cleanup。

## 非目标

- 不接 TaskPathPlanner。
- 不做复杂多步骤计划。
- 不实现 retry / relearn failure menu。
- 不让 LLM 直接调用 `start_replay` 或内部 adapter。
- 不把 `learned_path_id` 放进 Router output。
- 不新增 product-test-site 页面功能。
- 不运行 `verify-scenario` 或 autonomous run。

## 未决问题

- 是否新增 dedicated event type（例如 `pending_choice_created` / `active_task_updated`）：
  实现前可在技术评审中决定。默认可复用已有 chat progress / trace event，避免扩大 enum。
- `active_task` completed 后是立即清理还是保留最近完成摘要：默认清理 live `active_task`，
  完成事实由 conversation events 承担。
