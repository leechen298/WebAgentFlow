# 契约（Contract）

状态：draft_for_review

## 概念 / 边界契约

本轮不新增产品概念，只收紧三个已有边界：

1. **Public pending choice payload**：
   - 只允许公开 `choice_id`、`label`、`description`、`intent`、`choice_group_id`、
     `turns_remaining`、`created_at` 等用户选择所需字段。
   - 不得公开 `learned_path_id`、`pending_choice_private_map`、`slot_overrides`、
     selector / XPath、ReplayAction、execution payload、raw planner payload、private retry payload。

2. **Private choice map**：
   - 可以在 runtime 内部保存 selected choice 到 learned action / planner route 的映射。
   - 必须能支持用户选择 A/B/C 后执行正确 action。
   - 不能通过 public session、public events、messages、history 或 committed artifact 暴露 full id。

3. **Planner-backed choice execution**：
   - `planner_route_choice` 被用户选择后，必须 resolve selected private mapping，并启动 selected
     learned action execution。
   - 成功路径必须产生 `planner_choice_selected`、`chat_execution_started`、execution verified、
     reporter verified / evidence-based final response。
   - `planner_single_path_bypass_regression` 继续要求单路径明确目标不进入 Planner。

## 状态 / 结果契约

本包实现完成后，状态只能按实际验证结果推进：

| Status | 含义 |
|---|---|
| `implementation_review_failed` | 代码修复未通过 targeted tests 或 eval required gates。 |
| `implementation_complete_pending_closeout` | 本包 tests 和 required evals pass，但 11.3.6 program 尚未重新 closeout。 |
| `blocked` | 环境不可用或 artifact 写入 / redaction 阻断。 |

不得直接把 M11.3.6 program 标为 complete；program 状态只能在后续 11.3.6.5 closeout rerun 中更新。

## Schema / API 契约

No new public API endpoint or DB schema changes.

允许的兼容性变化：

- Existing public conversation read surfaces may become stricter by stripping private runtime fields.
- Public pending choice payloads may remove private keys that should never have been public.
- Internal runtime may keep private state in DB metadata or an internal structure, but public serializers must remove it.

禁止：

- 新增 API 让 runner 绕过 Conversation API。
- 使用 direct replay endpoint 代替 `/conversation/sessions/{session_id}/dispatch`。
- 改变 `wagent conversation` / eval runner 的用户可见命令语义。

## Evidence / Observation 契约

Allowed evidence sources:

- Conversation API dispatch result。
- Conversation session / messages / events / history read surfaces。
- runner JSON / Markdown artifacts after redaction。
- targeted pytest / ruff / format / `git diff --check`。

Private-id comparison rules:

- Runtime / runner evaluator 内部可以使用 raw `learned_path_id` 做 expected / actual comparison。
- JSON artifact、Markdown result、gate evidence、public event payload 不得输出 full private path id。
- 需要公开 path comparison 时，只能输出 choice alias、stable hash、match true / false。

Artifact redaction rules:

- `raw_api_responses.records[].response_text` 必须在写入 artifact 前 redacted 或完全替换。
- `response_json`、events、history、messages、gate evidence 中若含动态 private path id，必须替换为
  hash / `[REDACTED]`。
- 如果 redaction 发现无法安全清理的 raw planner payload，runner 必须 fail artifact safety check，
  不得提交 raw artifact。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：仍属于 L3 runtime conversation / task execution 验收，不新增 lifecycle stage。
- Scope boundary 对齐：不新增 internal Agent role，不改变 TaskPathPlanner / TaskResultReporter /
  Failure Recovery Agent 边界。
- Roadmap / milestone 对齐：归属于 M11.3.6 runtime eval program 的代码修复子包。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- Existing pending choice UX remains A/B/C selection。
- Existing single-path direct replay behavior remains unchanged。
- Existing failure recovery menu behavior remains unchanged。
- Existing 11.3.6.1 / 11.3.6.2 artifacts remain historical evidence；do not rewrite them。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API endpoint list：不变。
- Database schema：不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不修 unrelated 11.3.5.1 / 11.3.5.4 / 11.3.5.5 backlog。
- 不把 eval-only alias binding 说成真实 multi-action live capability。
- 不做 M15 audit platform。

## 未决问题

- None for implementation. If implementation discovers that the only viable fix requires schema / API / DB
  changes, stop and update this contract before coding further.
