# 契约（Contract）

状态：draft_docs（待评审，未开始实现）

## 概念 / 边界契约

### Basic Failure Recovery

Basic Failure Recovery 是 Runtime 层的基础恢复菜单，不是完整 Failure Recovery Agent。
它只处理已经执行过或准备执行的 chat task 在失败 / 不确定后的下一步选择。

Runtime 负责：

- 根据 replay result、drift status、reporter outcome 和 execution evidence 分类失败。
- 生成用户可见恢复选项。
- 将真实 retry / relearn payload 放入 private map。
- 解析用户选择并执行对应分支。

LLM / Router 不负责：

- 不解析真实 `learned_path_id`。
- 不输出 retry payload。
- 不选择是否安全重试。
- 不调用 replay / learning。

### Recovery Choice Visible Payload

本包复用 11.3.5.7 的 `pending_choice` visible payload。用户只看到：

```text
A. 重试
B. 重新学习
C. 取消
```

visible payload 不得包含：

```text
learned_path_id
selector
browser_action
ReplayAction
slot_overrides
execution_payload
private mapping payload
```

### Recovery Private Map

private map 只允许 Runtime / Orchestrator 使用。推荐在 `pending_choice_private_map`
中保存：

```ts
type RecoveryPrivateChoice =
  | {
      kind: "retry_replay";
      learned_path_id: string;
      target_url: string;
      action_alias?: string;
      slot_overrides?: Record<string, string>;
      evidence_targets?: unknown[];
      retry_count: number;
      failure_reason: string;
    }
  | {
      kind: "relearn_operation";
      target_url: string;
      action_alias?: string;
      fill_values?: Record<string, string>;
      failure_reason: string;
    }
  | {
      kind: "cancel";
      failure_reason?: string;
    };
```

如果实现使用其他 key，必须保持同等安全边界。

### Failure Classification

P2 基础版只分类到能驱动用户下一步的粒度：

| Failure class | 触发条件 | 用户回复策略 | Recovery choices |
|---|---|---|---|
| `replay_failed` | replay status failed / runtime error | 说明执行失败，不说成功 | retry / relearn / cancel |
| `blocked` | drift、URL mismatch、unsupported、page mismatch | 说明当前页面不匹配或被阻断 | retry / relearn / cancel |
| `evidence_missing` | replay succeeded but no useful evidence | 说明已执行但无法确认 | retry / relearn / cancel |
| `needs_review` | Reporter outcome `needs_review` | 说明未确认目标结果 | retry / relearn / cancel |
| `uncertain` | Reporter outcome `uncertain` | 说明结果不确定 | retry / relearn / cancel |

本包不新增复杂错误 taxonomy。

## 状态 / 结果契约

### Retry

Retry 必须满足：

- 只重试同一个 learned action。
- 复用原 target URL。
- 复用原 `slot_overrides` 和 evidence targets。
- 不通过 TaskPathPlanner。
- 默认最多自动重试一次。再次失败可以再次展示恢复选项，但不得循环自动重试。

如果原失败没有足够 payload 重试，Runtime 不得猜测，应回复无法重试并建议重新学习或取消。

### Relearn

Relearn 必须满足：

- 进入 learning branch，而不是直接执行。
- 使用原 target URL 和 action alias 作为学习目标。
- 如果必要 slot / target 不足，写 pending 并追问。
- 学习完成后不自动执行旧失败任务。用户需要再次提出执行，或后续包再设计显式确认链路。

### Cancel

Cancel 必须清理：

```text
pending_choice
pending_choice_private_map
pending_intake
pending_target
last_no_path_reason
active_task
pending sensitive values
```

回复必须简短明确：

```text
已取消当前任务。
```

### Active Task

当恢复菜单展示时，`active_task` 应进入等待用户输入状态：

```json
{
  "kind": "execute_operation",
  "owner": "runtime",
  "status": "waiting_for_user_input"
}
```

用户选择 retry 后更新为 `executing`。选择 relearn 后更新为 `learning` 或
`waiting_for_user_input`。选择 cancel 后清理。

## Schema / API 契约

本包默认不新增 public API endpoint，不新增 DB migration。

允许修改：

- conversation session metadata
- conversation event payload
- `chat_runtime.py` 内部 recovery helpers
- targeted tests

可选复用 `CHAT_PROGRESS_RECORDED` 记录：

```text
failure_recovery_offered
failure_recovery_selected
failure_recovery_retry_started
failure_recovery_relearn_started
failure_recovery_cancelled
```

event payload 不得暴露 private map 给 LLM-facing trace。

## 兼容性契约

- 没有 pending recovery choice 的旧 session 必须继续正常运行。
- 11.3.5.6 `/items` verified happy path 不应展示 recovery menu。
- 11.3.5.7 普通多候选 choice 行为不应被 recovery choice 破坏。
- `learn_then_execute` 继续保持保守阻断。
- TaskPathPlanner 不进入本包。

## 非目标

- 不做 selector repair。
- 不做 DOM 自主搜索恢复。
- 不做多页面导航恢复。
- 不做自动切换 URL。
- 不做 retry backoff / scheduler。
- 不做完整 M12 recovery / abort / interruption。

