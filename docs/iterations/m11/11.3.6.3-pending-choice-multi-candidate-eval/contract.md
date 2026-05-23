# 契约（Contract）

状态：draft_for_review（pending choice eval 设计稿，未实现代码）

## Scope Contract

11.3.6.3 只为 WAgent Runtime Eval Program 增加 pending choice multi-candidate eval coverage。
它验证 11.3.5.7 已实现的 pending choice / private map / selection cleanup 边界，不新增产品能力。

Runner 必须继续遵守 11.3.6 program 的通用原则：

- 通过 Conversation API 驱动 runtime conversation。
- 不调用 autonomous-run endpoints。
- 不用 direct replay API 冒充 conversation closed loop。
- hard gates 决定 pass / fail。
- Codex 只做 artifact 审计员。
- public artifact 必须 redaction。

## Case Contract

### `pending_choice_multi_candidate`

推荐流程：

```text
1. 准备至少三个候选 learned actions，且候选必须来自当前 eval run 的 setup evidence。
2. 创建 / 继续一个 interactive_chat eval session。
3. 发送模糊但可执行的用户消息，例如“帮我处理一下这个页面”。
4. Runtime 生成 public A/B/C choices 和 sanitized pending_choice event。
5. 发送用户选择“A”。
6. Runtime 执行 A 对应 learned action。
7. 读取 session / messages / events / history / raw request log。
8. 校验 gates。
```

本 case 必须是 non-planner pending choice。Planner-backed choice 的 ranked candidates /
planner route summary / planner fallback 属于 11.3.6.4。

## Candidate Setup Contract

本 case 必须避免全局旧 LearnedPath 污染。候选数量和 A/B/C 映射只能来自当前 eval run 的
setup evidence。

允许的 setup 来源优先级：

1. 同一 conversation session 中通过 Conversation API 学习得到三个 distinct learned paths。
2. 当前 eval run 的 setup session 通过 Conversation API 学习得到三个 distinct learned paths，
   再用 Conversation API 创建 eval session 并绑定这些 learned actions。
3. 最小 eval-only setup hook，用于把当前 eval run 中已知的 learned path ids 绑定为多个
   learned action aliases。
4. 非 live gate evaluator fixture，仅用于 unit / artifact 测试；不能声称 live runtime eval pass。

如果实现 eval-only setup hook，必须满足：

- 只在 `client=wagent_eval` 且显式 opt-in metadata 存在时生效。
- 默认关闭；普通 conversation、CLI chat、Console 和 product runtime 不受影响。
- 只能绑定当前 eval run setup evidence 已产生的 learned path ids。
- 不得创建虚假的 learned path id。
- 不得把 `pending_choice_private_map`、`learned_path_id` 或 selector 暴露到 public events /
  public session payload / visible reply。

## Gate Contract

| Gate | Required | Source | Pass semantics |
|---|---:|---|---|
| `setup_multi_candidate_current_eval` | yes | setup turns / learning events / setup manifest | 至少三个候选来自当前 eval run，且有 distinct aliases |
| `pending_choice_created` | yes | events / history | 有 non-planner `pending_choice_created` event |
| `public_choices_abc_visible` | yes | final WAgent message / pending_choice public payload | public choice 至少包含 A / B / C 三个候选 |
| `public_choice_payload_sanitized` | yes | messages / session public payload / events / history | public surface 不含 `learned_path_id`、private map、selector、slot overrides、ReplayAction |
| `planner_not_invoked` | yes | events / history | 本 case 不出现 planner choice / planner candidate events |
| `select_A_dispatched` | yes | turn record / messages | 用户选择 A 的 dispatch 成功返回 |
| `choice_A_execution_started` | yes | `chat_execution_started` after A turn | A turn 后进入 execution |
| `execution_uses_choice_A_path` | yes | setup manifest + execution event | execution event 的 `learned_path_id` 等于 setup 中 choice A 对应 path |
| `slot_override_after_choice` | conditional | execution event | 如果 A turn 带业务 slot，则 `slot_overrides.item_name` 等于执行阶段目标值 |
| `pending_choice_cleared` | yes | session public payload / history | 选择 A 后 public session 不再有 `pending_choice` |
| `private_map_not_public_after_selection` | yes | session / history / messages / events | 选择 A 后 public surface 不出现 private map |
| `execution_verified` | yes | execution evidence / reporter event | A 对应执行结果 verified |
| `final_response_verified` | yes | final WAgent message | 回复基于 evidence 说明执行成功 |
| `no_autonomous_or_direct_replay` | yes | runner raw request log | runner 不调用 autonomous-run endpoints 或 direct replay endpoint |

如果某个 source 当前不可观察，runner 只能给该 gate 标记 `not_observable` / `warning`，并在
Markdown result 中写出 follow-up；不得从 final text 推断 private map 存在或 candidate path id。

## Public / Private Payload Contract

Public surface 允许：

- choice id：`A` / `B` / `C`。
- label。
- description。
- intent。
- choice group id。
- turns remaining。

Public surface 禁止：

- `learned_path_id`
- `pending_choice_private_map`
- raw selector / XPath
- `slot_overrides`
- `ReplayAction`
- `execution_payload`
- credential / password / secret / token / cookie / authorization / api_key

Private map 可以在 runtime 内部存在，但 runner 不能要求 public API 直接暴露 private map。
选择 A 后的正确执行必须通过 setup manifest + `chat_execution_started.learned_path_id` 等
runtime evidence 判定。

## Artifact Contract

沿用 11.3.6 program artifact 规则。推荐本 case 输出：

```text
artifacts/wagent-eval/wagent-runtime-eval-${timestamp}.json
docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-${date}.md
```

Markdown result 必须显式说明：

- live runtime eval 是否实际运行。
- candidate setup 使用了 same-session learning、setup-session learning、eval-only hook，还是 fixture。
- choice A 对应的 setup evidence。
- required gates / warnings / not observable。

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
