# 契约（Contract）

状态：ready_for_implementation

## 概念 / 边界契约

本轮新增一个过程概念：`runtime_eval_program_closeout`。

它不是新的产品 runtime 能力，也不是新的 eval case family。它是一次 evidence / status
收口动作，用于把 11.3.6.x 子包的实现事实、runner 输出、artifact 和迭代文档状态对齐。

Closeout runner 可以执行现有命令，但不得改变 runner 的判定逻辑。若发现 runner gate
设计不充分或 runtime 代码 bug，closeout 必须停止并登记 follow-up，而不是在本包内修代码。

## 状态 / 结果契约

Program closeout 状态只允许使用以下值：

| Status | 含义 |
|---|---|
| `closed_live` | 所有 required child packages 已实现，且按 contract 要求完成 live Conversation eval pass。 |
| `closed_non_live` | 所有 required child packages 已实现，required non-live checks pass，但至少一个 live eval 明确未运行；required child package 不得处于 blocked。 |
| `partially_closed` | 部分 child packages 已 closeout，仍有 package 缺 review、artifact 或明确结果。 |
| `blocked` | closeout 命令无法运行、服务不可用、artifact 写入失败，或 required gate fail。 |
| `not_run` | closeout sweep 尚未执行。 |

子包 closeout 状态必须保留 live / non-live 差异：

- `implemented_and_live_eval_passed`
- `implementation_complete_non_live`
- `implementation_complete_blocked`
- `implementation_review_failed`
- `ready_for_implementation`

不得把 `implementation_complete_non_live` 自动升级为 `implemented_and_live_eval_passed`。

Blocked artifact 只能证明 blocked 状态已经被记录，不能证明对应 child package 完成：

- 如果 11.3.6.3 或 11.3.6.4 只产生 blocked artifact，对应子包状态必须是
  `implementation_complete_blocked` 或 `blocked`。
- 这种情况下不得写 `implementation_complete_non_live` 或
  `implemented_and_live_eval_passed`。
- Program status 不得为 `closed_live` 或 `closed_non_live`；只能是 `partially_closed` 或
  `blocked`。
- 只有 required gates pass，或明确被 contract 标为 optional / not_run 的项不影响 required
  closeout 时，才允许进入 `closed_non_live`。

## Schema / API 契约

No product schema/API changes.

本轮不新增 Conversation API、Exploration API、runner JSON schema 或 package script。Closeout
只消费现有 runner 输出：

- `pnpm run eval:wagent:items`
- `pnpm run eval:wagent:failure-recovery`
- `pnpm run eval:wagent:pending-choice`
- `pnpm run eval:wagent:planner-choice`

如果实现者认为需要新增 `eval:wagent:closeout`，必须先更新本 contract，并明确它只是命令聚合，
不得绕过现有 case 的 hard gates。

## Evidence / Observation 契约

允许的 closeout evidence：

- runner stdout / exit code；
- JSON artifact under `artifacts/wagent-eval/`；
- Markdown result under `docs/testing/results/`；
- pytest / ruff / format / `git diff --check` command output；
- git commit hash；
- review inspection of existing source and docs。

禁止的 closeout evidence：

- Codex 自然语言“看起来通过”；
- direct replay API 结果冒充 Conversation API runtime；
- autonomous-run endpoint direct call；
- `verify-scenario` 结果冒充 WAgent runtime eval；
- blocked artifact 冒充 live pass；
- fixture-only gate pass 冒充 live multi-action capability。

Artifact 必须继续遵守 11.3.6 program redaction 规则，不得泄露：

- `learned_path_id` full value；
- `pending_choice_private_map`；
- private retry payload；
- selectors / XPath；
- `slot_overrides` private payload；
- raw planner warnings；
- raw response text containing private ids；
- credentials / tokens / cookies / authorization headers。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：本轮只收口 M11 runtime eval evidence，不改变 L1 / L2 / L3 lifecycle。
- Scope boundary 对齐：不新增 internal Agent role，不改变 TaskPathPlanner、TaskResultReporter、
  Failure Recovery Agent 边界。
- Roadmap / milestone 对齐：归属于 M11.3.6 runtime eval program closeout。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

旧的 11.3.6.1 / 11.3.6.2 artifact 和 review 继续有效。Closeout 不重写历史结果；如果重跑命令，
必须新增新的 artifact / result，并在 review 里说明它是重跑证据还是原始证据。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不把 11.3.6.3 / 11.3.6.4 的 eval-only candidate binding 提升为真实 live multi-action
  product capability。
- 不要求 failure recovery retry after selecting A 必须 live verified；除非后续 contract 改变。
- 不做 M15 automated evaluation / audit platform。

## 未决问题

- 是否要求 11.3.6.3 / 11.3.6.4 跑 live Conversation eval，还是接受 non-live closeout？
  由用户 / reviewer 在执行前确认。
- 若 live 服务不可用，是否提交 blocked artifact？默认允许，但必须标为 `blocked`，不能标 pass。
