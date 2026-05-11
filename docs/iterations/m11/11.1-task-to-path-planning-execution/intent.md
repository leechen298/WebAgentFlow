# 11.1 Task-to-Path Planning & Execution MVP

## 目标

让用户通过 M11.0 runtime conversation surface 提交自然语言任务。
WebAgentFlow 基于 LearnedPath catalog 和 replay evidence 选择候选路径、
绑定任务参数、请求确认、执行 replay、验证结果、汇报结果。

这是第一个 L3 Actual Work MVP。

## 动机

- M11.0 已完成 runtime conversation 基座。
- 11.0.6 已证明 conversation flow 能显式调用 replay。
- 但用户还不能说“帮我筛选 active 用户并导出”这类任务。
- M11.1 把 explicit replay 推进到 task-to-path planning。
- 必须分阶段做，不能一次性把 Agent D / E / execution / verification
  混在一起。

## 边界（本阶段不做）

- 不做 autonomous learning。
- 不做 hidden path learning。
- 不做 raw HTML planner。
- 不让 LLM per-step control browser。
- 不做 recovery / abort dialogue 完整流程。
- 不做 guided teaching。
- 不做 multi-page workflow。
- 不做 full artifact lifecycle。
- 不引入账号体系 / PC App / 云端数据 / 消息通道。

## 成功标准

- 有 M11.1 总体拆分。
- 有 11.1.1 domain contract 执行包。
- 明确 Agent D / E 边界。
- 明确 path retrieval / slot binding / confirmation / execution /
  verification 拆分。
- 明确不调用 autonomous run。
- 明确 LLM 不逐步控制浏览器。
