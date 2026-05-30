# 意图（Intent）

状态：ready_for_implementation

## 背景

`PV-CLI-003` 的既有失败说明：learning / router 层已经识别出
`Create inventory item` 和 `create_inventory_item`，但 runtime action matching
没有把 execute request 绑定到具体 session learned action。早期根因包括：

- `learning_action_label_too_generic`
- `business_object_not_preserved`
- `execution_action_match_too_literal`

`11.3.8.1` 已保留业务身份 metadata，`11.3.8.2` 已生成更可复用的 utterances。本包负责
让 runtime matcher 消费这些 target-agnostic identity terms。

## 用户价值

用户学习过一个业务动作后，可以用新的参数要求执行同一业务动作。WebAgentFlow 应能匹配到
当前 session 内的已学 action，而不是因为早期 label / wrapper 文字不完全一致就拒绝。

## 成功标准

- 同一业务动作的新参数执行请求能匹配唯一已学 action。
- 不同业务动作不能因为共享对象或共享动词而误匹配。
- 多个 plausible actions 时继续进入 choice / clarification，而不是静默执行。
- 泛化动词如 `Create`、`Open`、`Update`、`Delete` 不单独授权执行。
- 不引入外部 Fixture-Site route、selector、seed data、button text、field label、
  placeholder、operation alias 或 page source。

## 非目标

- 不重跑 external black-box validation。
- 不更新 `docs/testing/results/external-black-box-validation-latest.md`。
- 不修改 learning metadata preservation 或 suggested utterance generation。
- 不修改 replay execution、Task Result Reporter、recovery、abort、worker、frontend 或 DB schema。
- 不实现 full learn-then-execute arbitrary-domain capability。

## Handoff

若本包 `PACKAGE_COMPLETE`，交给 `11.3.8.4-regression-tests` 把 metadata、utterances、
matcher 和 replay handoff 组合成 repo-local automated regression。
