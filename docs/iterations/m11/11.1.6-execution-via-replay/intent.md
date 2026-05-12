# 11.1.6 通过 Replay 执行已确认计划

## 目标

为 M11.1 设计第一个 confirmed-plan execution 包：当 conversation 已经存在
confirmed-but-not-executed plan 时，WebAgentFlow 可以针对选中的 LearnedPath
调用现有 deterministic replay 能力，并记录 replay execution evidence，但不声明
业务结果成功。

## 动机

11.1.4 让普通用户任务可以生成 planning preview。11.1.5 让用户同意变成显式、
可审计的 consent。下一步才是 execution，但 execution 只能发生在确认之后，并且
只能通过 M10 / 11.0.6 已经建立的 deterministic replay foundation。

本阶段必须比“任务成功”更窄：

- replay execution 是确定性引擎动作；
- replay completion 不等于业务结果验证成功；
- result verification 和面向用户的成功汇报属于后续 Result Verification 和
  Task Result Reporter；
- recovery、teaching、hidden relearning 仍然不在本包范围内。

## 为什么必须先确认

Execution 会改变页面状态。Planning preview 只是 proposal；11.1.5 是记录用户
explicit consent 的 gate。11.1.6 只有在 consent 存在，并且 pending plan 没有被
cancelled、rejected 或 superseded 时，才允许执行。

## 为什么必须使用 deterministic replay

产品模型要求 execution 绑定到已知 path assets。11.1.6 必须复用现有
deterministic replay 能力，而不是：

- 调用 autonomous exploration；
- 让 LLM 逐步控制浏览器；
- 读取 raw HTML 临场规划；
- 发明 browser actions；
- hidden relearning 新路径。

如果 confirmed plan 不能提供 `learned_path_id` 和 target URL / entry context，
execution 必须 blocked，而不是猜测。

## 边界

11.1.6 不做：

- 从 raw user text 重建 plan；
- 再次调用 Task Path Planner；
- 做 slot binding 或超出 confirmed replay path 的 form filling；
- 验证 postconditions；
- 生成 Task Result Reporter summary；
- 做 recovery；
- 调用 autonomous run；
- 接入 LLM provider。

## 成功标准

- 有明确的 execution precondition contract。
- confirmed plan lookup 来源于可审计 conversation evidence。
- replay invocation 要求显式 `learned_path_id + url` 或等价 entry context。
- execution events 不声明 task success。
- missing context 返回 unable-to-execute / needs-more-context 语义。
- explicit replay command 保持兼容。
- result verification 保持 future scope。
