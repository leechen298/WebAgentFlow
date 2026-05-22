# 契约（Contract）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## Scope Contract

11.3.6.2 只为 WAgent Runtime Eval Program 增加 failure recovery eval coverage。它验证
11.3.5.8 已实现的基础 recovery 边界，不新增产品能力，不进入 M12 复杂 recovery / retry /
abort。

Runner 必须继续遵守 11.3.6 program 的通用原则：

- 通过 Conversation API 驱动 runtime conversation。
- 不调用 autonomous-run endpoints。
- 不用 direct replay API 冒充 conversation closed loop。
- hard gates 决定 pass / fail。
- Codex 只做 artifact 审计员。
- public artifact 必须 redaction。

## Case Contract

### `failure_recovery_menu_safety`

推荐流程：

```text
1. 复用 11.3.6.1 的 `/items` learned path setup，或在本 case 内显式完成 setup。
2. 对一次执行 turn 使用稳定 failure trigger，使 TaskResultReporter / recovery path 进入
   `needs_review` 或 `evidence_missing`。
3. 读取 session、messages、events、history 和 runner raw responses。
4. 校验 recovery menu、private payload safety 和 happy-path no-recovery gates。
```

首版不要求选择 A 继续 retry，也不要求验证 retry 后新增成功。retry execution 可以作为后续
case 或 optional diagnostic。

## Failure Trigger Contract

本 case 必须使用稳定、可复现、可审计的 failure trigger。允许的实现优先级：

1. 现有 public Conversation API / runtime behavior 已能稳定产出 recovery path。
2. 新增最小 eval-only fault injection hook。
3. 非 live gate evaluator fixture，仅用于 unit / artifact 测试；不能声称 live runtime eval pass。

如果实现 eval-only fault injection hook，必须满足：

- 只在 session / dispatch metadata 明确声明 `client=wagent_eval` 且 opt-in key 存在时生效。
- 默认关闭；普通 conversation、CLI chat、Console 和 product runtime 不受影响。
- hook 只允许强制 reporter outcome / evidence status 进入 `needs_review` 或 `evidence_missing`
  这类保守 failure class。
- hook 不得跳过 Conversation API dispatch。
- hook 不得直接调用 replay service 或 internal recovery service 来伪造闭环。
- hook 的 public event 只能记录脱敏后的 fault class，不得暴露 private retry payload。

推荐 metadata shape：

```json
{
  "client": "wagent_eval",
  "eval_fault_injection": {
    "case_id": "failure_recovery_menu_safety",
    "reporter_outcome": "needs_review"
  }
}
```

## Gate Contract

| Gate | Required | Source | Pass semantics |
|---|---:|---|---|
| `failure_triggered` | yes | events / history / raw dispatch response | 本 turn 明确进入 `needs_review`、`evidence_missing`、`uncertain`、`blocked` 或 `replay_failed` |
| `recovery_menu_shown` | yes | final WAgent message / assistant message | visible reply 出现 A/B/C recovery menu |
| `retry_wording_safe` | yes | final WAgent message | A 选项必须是“重试执行该操作”，不能只写模糊“重试” |
| `retry_side_effect_warning` | conditional | final WAgent message | 对 `needs_review` / `evidence_missing` / `uncertain` 必须提示重试可能再次执行操作 |
| `relearn_option_shown` | yes | final WAgent message | B 选项明确为“重新学习”或等价重新教学入口 |
| `cancel_option_shown` | yes | final WAgent message | C 选项明确为“取消” |
| `private_payload_not_visible` | yes | visible messages / session public payload | 不出现 private retry payload、raw selector、ReplayAction、slot_overrides、execution_payload |
| `recovery_events_sanitized` | yes | events / history | public events 不暴露 private retry / relearn / cancel payload |
| `verified_happy_path_no_recovery` | yes | previous or control turn messages/events | verified happy path 不出现 recovery menu |
| `no_autonomous_or_direct_replay` | yes | runner source / raw request log | runner 不调用 autonomous-run endpoints 或 direct replay endpoint |
| `retry_execution_verified` | optional | later retry turn evidence | 首版可不执行；若执行，必须证明 retry 后由 reporter verified |

如果某个 source 当前不可观察，runner 只能给该 gate 标记 `not_observable` / `warning`，并在
Markdown result 中写出 follow-up；不得从 final text 推断 private map 或 selector safety。

## Redaction Contract

JSON artifact、Markdown result 和 public gate evidence 必须脱敏：

- `learned_path_id`
- `slot_overrides`
- `evidence_targets`
- raw CSS selector / XPath selector
- `ReplayAction`
- `execution_payload`
- `pending_choice_private_map`
- `private_retry_payload`
- `credential` / `password` / `secret` / `token` / `cookie` / `authorization` / `api_key`

`item_name` 作为 `/items` 测试数据可以保留，但不得包含真实用户敏感内容。

## Artifact Contract

沿用 11.3.6 program artifact 规则。推荐本 case 输出：

```text
artifacts/wagent-eval/wagent-runtime-eval-${timestamp}.json
docs/testing/results/m11-11.3.6.2-failure-recovery-eval-${date}.md
```

Markdown result 必须显式说明：

- live runtime eval 是否实际运行。
- failure trigger 使用了现有行为、eval-only hook，还是非 live fixture。
- required gates / warnings / not observable。
- 未执行 retry 时，不得声称 retry recovery 成功。

## Exit Code Contract

沿用 11.3.6 program exit code：

| Exit code | Meaning |
|---:|---|
| 0 | all required gates pass |
| 1 | required gate fail |
| 2 | environment blocked |
| 3 | timeout |
| 4 | artifact write failed |
| 5 | runner internal error |
