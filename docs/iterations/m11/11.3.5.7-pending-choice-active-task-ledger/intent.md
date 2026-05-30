# 意图（Intent）

状态：implementation complete（code review passed，targeted tests passed）

## 目标

让 `wagent chat` 在多候选、模糊输入、用户选择和取消场景下使用 code-owned
`pending_choice` 与最小 `active_task` metadata 进行状态管理，而不是让 Router 或
LLM 猜测下一步。

## 动机

11.3.5.6 已经证明 WebAgentFlow 可以跑通第一条窄闭环：

```text
学习新增项目 A
-> 执行新增项目 B
-> 看到 DOM evidence
-> Reporter verified
```

下一步问题不是继续扩大 happy path，而是处理真实用户会说的模糊话：

```text
帮我处理一下这个页面
搞一下
继续
A
算了
不是，我要搜索
```

当前 runtime 已有 `pending_intake`、`pending_target`、`last_no_path_reason` 和
`learned_actions`，但还没有：

- `pending_choice`：保存 A/B/C 候选、用户可见 choice id、内部私有映射。
- `active_task`：记录当前学习 / 执行 / 澄清任务的最小运行态。
- 统一 cancel：同时清理 pending 和 active task。

如果不补这个包，多候选和混乱输入会继续落到“追问一句话”或“无法匹配路径”，后续
11.3.5.8 failure recovery 和 11.3.5.9 TaskPathPlanner 多候选接入也没有稳定状态底座。

## 边界 / 非目标

- 不把 TaskPathPlanner 接进 chat runtime；本包可用 deterministic learned actions 构造 choice。
- 不实现复杂 planning preview；11.3.5.9 再接 Planner。
- 不做 retry / relearn / cancel failure menu；11.3.5.8 再做。
- 不启用 `learn_then_execute`。
- 不实现搜索 / 编辑 / 删除 `/records` 业务闭环。
- 不新增数据库列；P0/P1 状态继续放在 conversation session metadata。
- 不让 Router 或 LLM 看见真实 `learned_path_id`。
- 不让 Router 推荐 internal runtime adapters。
- 不调用 `verify-scenario` 或 autonomous run。

## 成功标准

- 多个候选 learned actions 或低置信目标时，Runtime 写入 `pending_choice` 并回复 A/B/C。
- 用户输入 `A` / `1` / `第一个` 时，代码命中对应 choice，并通过私有映射解析真实 action。
- 用户输入“不是，我要搜索”时，旧 `pending_choice` 被清理，消息重新走 intake。
- 用户输入“算了”或 `/cancel` 时，`pending_intake`、`pending_target`、`pending_choice`、
  `active_task` 都被清理或标记取消。
- `pending_choice` 过期后不会污染后续任务。
- 学习 / 执行 / clarify 开始、完成、失败时，`active_task` 有最小状态记录。
- Router prompt、LLM trace、用户可见回复和 progress event 不暴露真实 `learned_path_id`。
- 既有 `/records` 单路径 happy path 仍不经过 TaskPathPlanner，且 targeted tests 仍通过。
