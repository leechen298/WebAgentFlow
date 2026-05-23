# 契约（Contract）

状态：draft_for_review（planner-backed choice eval 设计稿，未实现代码）

## Scope Contract

11.3.6.4 只为 WAgent Runtime Eval Program 增加 planner-backed choice eval coverage。
它验证 11.3.5.9 已实现的 TaskPathPlanner multi-candidate chat path，不新增产品能力。

Runner 必须继续遵守 11.3.6 program 的通用原则：

- 通过 Conversation API 驱动 runtime conversation。
- 不调用 autonomous-run endpoints。
- 不用 direct replay API 冒充 conversation closed loop。
- 不直接调用 `TaskPathPlanner.plan()` 冒充 runtime planner path。
- hard gates 决定 pass / fail。
- Codex 只做 artifact 审计员。
- public artifact 必须 redaction。

## Case Contract

### `planner_backed_choice`

推荐流程：

```text
1. 准备多个候选 learned actions，且候选必须来自当前 eval run 的 setup evidence。
2. 创建 / 继续一个 interactive_chat eval session。
3. 发送 vague goal，例如“帮我处理一下这个页面”或“<items URL> 帮我处理一下”。
4. Runtime 进入 TaskPathPlanner-backed choice path。
5. Runtime 生成 sanitized public A/B/C choices。
6. 发送用户选择，例如“A”。
7. Runtime 记录 planner_choice_selected 并执行对应 learned action。
8. 读取 session / messages / events / history / raw request log。
9. 校验 gates。
```

本 case 必须是 planner-backed pending choice。Non-planner pending choice 属于 11.3.6.3；
如果本 case 只出现普通 `pending_choice_created` 而没有 planner events，应 fail。

### `planner_single_path_bypass_regression`

本包还必须保护单路径回归：

```text
1. 当前 eval session 只有一个明确 matched learned action。
2. 用户发出明确执行请求。
3. Runtime 直接 replay。
4. 不生成 planner candidates / planner choice。
5. 执行 verified。
```

该 case 可以复用 11.3.6.1 的 single-path setup，但必须在本包 gate 中明确校验 no-planner
signals。

## Candidate Setup Contract

本 case 必须避免全局旧 LearnedPath 污染。候选数量、choice 映射和 expected execution path
只能来自当前 eval run 的 setup evidence。

允许的 setup 来源优先级：

1. `live_same_session_distinct_paths`：同一 conversation session 中通过 Conversation API 学习得到
   多个 distinct learned paths。
2. `live_setup_session_distinct_paths`：当前 eval run 的 setup session 通过 Conversation API 学习得到
   多个 distinct learned paths，再用 Conversation API 创建 eval session 并绑定这些 learned actions。
3. `eval_only_planner_candidate_binding`：最小 eval-only setup hook，用于把当前 eval run 中已知的
   真实 learned path 绑定为 safe learned action summaries，以稳定触发 runtime planner branch。
4. `fixture_only`：非 live gate evaluator fixture，仅用于 unit / artifact 测试；不能声称 live
   runtime eval pass。

### Candidate Setup Practicality

当前 `/items` P0 页面主要稳定支持“新增项目”闭环；第一版实现不得假设 live UI 一定能稳定学习出
多个 distinct product actions。如果 live setup 不稳定，11.3.6.4 第一版允许使用
`setup_type=eval_only_planner_candidate_binding`，但必须满足：

- 至少一个真实 LearnedPath 来自当前 eval run；`fixture_only` 的 non-live evaluator test 除外。
- 如果多个 aliases 绑定到同一个真实 path，result 必须记录
  `live_multi_action_capability=false` 和 `planner_distinct_path_capability=false`。
- 该 setup 只能证明 planner branch、sanitized planner events、public / private payload safety 和
  selection control flow；不得声称产品已具备完整 live distinct-action Planner capability。
- 如果需要证明 Planner 收到多个 distinct learned paths，setup manifest 必须记录 redacted path
  hashes，且 full ids 只能用于 runner 内部比较。
- 若没有 eval-only binding 或 fixture，且 live setup 无法稳定产生多个候选，本 case 应输出
  `blocked` / `not_run`，不能降级为 subjective pass。

如果实现 eval-only setup hook，必须满足：

- 只在 `client=wagent_eval` 且显式 opt-in metadata 存在时生效。
- 默认关闭；普通 conversation、CLI chat、Console 和 product runtime 不受影响。
- Hook 只能准备 session learned action summaries 或 setup manifest，不能直接写
  `pending_choice_private_map`，不能直接生成 `planner_choice_created`，不能伪造
  TaskPathPlanner output。
- 后续 planner choice 必须由 Conversation API dispatch 触发 runtime path 自然产生。
- Hook event 如需记录，只能记录 case id、setup type、candidate count、aliases 和 redacted
  path hashes；不得记录完整 learned path ids、selector、slot overrides、private map 或 raw
  planner payload。

## Gate Contract

### `planner_backed_choice`

| Gate | Required | Source | Pass semantics |
|---|---:|---|---|
| `setup_planner_candidates_current_eval` | yes | setup turns / learning events / setup manifest | 至少三个 public candidates；setup type 合法；live case 至少一个真实 path 来自当前 eval run |
| `planner_candidates_generated` | yes | events / history | 有 `planner_candidates_generated` event，且 candidate count 与 setup manifest 不冲突 |
| `planner_choice_created` | yes | events / history | 有 `planner_choice_created` event |
| `non_planner_choice_not_used` | yes | events / history | 本 case 不以 11.3.6.3 eval-only non-planner hook 生成普通 pending choice |
| `public_choices_abc_visible` | yes | final WAgent message / session public payload | public choice 至少包含 A / B / C |
| `planner_public_payload_sanitized` | yes | messages / session public payload / events / history | public surface 不含 `learned_path_id`、private map、selector、slot overrides、ReplayAction、raw planner warning |
| `planner_event_sanitized` | yes | planner events / history | planner events 只含 counts / choice group / safe booleans，不含 private ids、selector、raw slot values |
| `planner_warning_wording_safe` | conditional | visible choices / planner event counts | 如果 planner warning / risk / uncertainty count > 0，visible text 只能是 generic wording |
| `planner_top_choice_observable` | conditional | planner choice event / visible public choice / setup manifest | 如果当前 read surface 暴露 top choice hash / generic planner marker，则可审计；否则 `not_observable` |
| `select_planner_choice_dispatched` | yes | turn record / messages | 用户选择 dispatch 成功返回 |
| `planner_choice_selected` | yes | events / history | 有 `planner_choice_selected` event |
| `planner_choice_execution_started` | yes | `chat_execution_started` after selection | 选择后进入 execution |
| `execution_uses_selected_choice_path` | yes | setup manifest + execution event | runner 内部用 raw `learned_path_id` 比较 selected choice path；公开 evidence 只输出 hash / alias / match |
| `pending_choice_cleared` | yes | session public payload / history | 选择后 public session 不再有 `pending_choice` |
| `execution_verified` | yes | execution evidence / reporter event | 对应执行结果 verified |
| `final_response_verified` | yes | final WAgent message | 回复基于 evidence 说明执行成功 |
| `no_autonomous_or_direct_replay` | yes | runner raw request log | runner 不调用 autonomous-run endpoints 或 direct replay endpoint |

### `planner_single_path_bypass_regression`

| Gate | Required | Source | Pass semantics |
|---|---:|---|---|
| `single_candidate_detected` | yes | current session learned actions / runtime route events | 当前 turn 只有一个明确 matched learned action |
| `no_planner_candidates_generated` | yes | events / history | 不出现 `planner_candidates_generated` |
| `no_planner_choice_created` | yes | events / history | 不出现 `planner_choice_created` |
| `direct_execution_started` | yes | `chat_execution_started` | 直接进入 execution |
| `execution_uses_current_learned_path` | yes | current eval learned path + execution event | execution path 来自当前 eval session |
| `execution_verified` | yes | execution evidence / reporter event | 执行 verified |
| `final_response_verified` | yes | final WAgent message | 回复基于 evidence 说明执行成功 |

如果某个 source 当前不可观察，runner 只能给该 gate 标记 `not_observable` / `warning`，并在
Markdown result 中写出 follow-up；不得从 final text 推断 Planner top choice、private map 或
candidate path id。

## Planner Event Observability Contract

当前 11.3.5.9 runtime 已有这些 planner progress kinds：

```text
planner_candidates_generated
planner_choice_created
planner_choice_selected
planner_unable_to_plan
planner_fallback_used
```

11.3.6.4 runner 可以使用这些 event 判断 planner branch 是否发生，但不得要求 public API 暴露
private planner map。若需要验证 selected choice 对应 path，runner 可以在内部 raw setup manifest
与 `chat_execution_started.payload.learned_path_id` 做比较；public evidence 只能输出 hash / alias /
match。

如果实现阶段发现 `planner_choice_created` 不能观察 top choice id 或 top path hash，第一版可以把
`planner_top_choice_observable` 标为 `not_observable` / `warning`。不得通过 visible final response
或 Codex 自然语言判断补齐该 gate。

## Public / Private Payload Contract

Public surface 允许：

- choice id：`A` / `B` / `C`。
- label。
- generic description。
- intent。
- choice group id。
- turns remaining。
- sanitized planner counts / booleans。
- generic warning wording，例如“存在 Planner 警告”“存在风险提示”“存在不确定性”。

Public surface 禁止：

- `learned_path_id`
- `pending_choice_private_map`
- raw selector / XPath
- `slot_overrides`
- `ReplayAction`
- `execution_payload`
- raw planner warnings / risk reasons / uncertainty text
- private planner summary payload
- credential / password / secret / token / cookie / authorization / api_key

Private planner map 可以在 runtime 内部存在，但 runner 不能要求 public API 直接暴露 private map。

## Choice Path Comparison / Redaction Contract

`execution_uses_selected_choice_path` 需要同时满足“可硬判定”和“不泄露内部 id”：

- Runner 内部可以从 raw setup manifest 和 raw execution event 读取完整 `learned_path_id` 做比较。
- Public JSON artifact、Markdown result 和 public gate evidence 不得输出完整 `learned_path_id`。
- Gate evidence 应输出可审计的 redacted form：

```json
{
  "selected_choice": "A",
  "expected_alias": "新增项目",
  "expected_path_hash": "sha256:abc123def456",
  "actual_path_hash": "sha256:abc123def456",
  "match": true,
  "setup_type": "eval_only_planner_candidate_binding",
  "planner_distinct_path_capability": false
}
```

Hash 必须稳定到足以审计同一次 artifact 内的 expected / actual match，但不能反推出完整 id。

## Artifact Contract

沿用 11.3.6 program artifact 规则。推荐本 case 输出：

```text
artifacts/wagent-eval/wagent-runtime-eval-${timestamp}.json
docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-${date}.md
```

Markdown result 必须显式说明：

- live runtime eval 是否实际运行。
- candidate setup 使用了 `live_same_session_distinct_paths`、`live_setup_session_distinct_paths`、
  `eval_only_planner_candidate_binding`，还是 `fixture_only`。
- `live_multi_action_capability` 和 `planner_distinct_path_capability`。
- planner events observed。
- selected choice 对应的 setup evidence。
- required gates / warnings / not observable。
- 如果只是 eval-only alias binding，必须说明它不证明 full live distinct-action Planner capability。

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
