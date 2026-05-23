# 意图（Intent）

状态：draft_for_review（pending choice eval 设计稿，未实现代码）

## 背景

11.3.5.7 已经给 conversation runtime 增加 `pending_choice` 和
`pending_choice_private_map`：当用户输入对应多个候选 learned actions 时，Runtime 应给用户
展示 A/B/C 等安全选项，下一轮由代码解析用户选择，并用私有映射执行正确 action。

11.3.6.1 runner core 先覆盖 `/items` happy path 和 single-path direct replay regression。
11.3.6.2 将 failure recovery 纳入 runner。11.3.6.3 的目标是把 pending choice
多候选澄清也纳入同一套 hard-gate eval program。

## 目标

本迭代目标是为 WAgent Runtime Eval Runner 增加 pending choice multi-candidate coverage：

- 稳定准备多个当前 eval run 产生或绑定的 candidate learned actions。
- 触发 non-planner pending choice。
- 验证 WAgent visible reply 和 public events 出现 A/B/C choices。
- 验证 public payload 不泄露 `learned_path_id`、selector、slot overrides 或 private map。
- 发送用户选择 A，验证 Runtime 执行 A 对应 learned action。
- 验证 selection 后 `pending_choice` 和 private map 从 public session state 中消失。

## 非目标

- 不实现新的 choice 产品能力。
- 不接 TaskPathPlanner；planner choice 属于 11.3.6.4。
- 不验证 failure recovery menu。
- 不把全局 LearnedPath catalog row count 当作候选数量证据。
- 不调用 direct replay endpoint 或 internal replay service 替代 Conversation API dispatch。
- 不运行登录页、凭证、cookie、权限或验证码场景。

## 成功标准

实现完成后，应满足：

- `pending_choice_multi_candidate` case 可以由 runner 执行并写出 JSON / Markdown artifact。
- required gates 由 events / messages / history / raw request log / current eval setup evidence 判定。
- 旧全局 `/items` LearnedPath 不会污染候选数量和选择结果。
- public artifact 和 Markdown result 不泄露 private map / path id / selector / sensitive payload。
- 未运行 live eval 时，review 和 Markdown result 不声称 live pass。
