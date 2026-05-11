# 11.1 · Task-to-Path Planning & Execution MVP

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/iterations/m11/m11-plan.md`
6. `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/intent.md`
7. `docs/iterations/m11/11.0.7-conversation-tests-and-evidence/review.md`
8. 本目录的 `intent.md`
9. 本目录的 `plan.md`

状态：**总纲初始化中**。

## 当前关系

- 前置：M10 replay / M11.0 runtime conversation loop。
- 本阶段：从 user task 到 LearnedPath route plan，再到 replay execution MVP。
- 后续：M12 recovery / abort dialogue、M13 teaching、M17 multi-page workflow。

## 硬边界

- 不调用 autonomous run。
- 不做 hidden relearning。
- 不让 LLM 逐步控制浏览器。
- 不做 M12 recovery / abort dialogue。
- 不做 M13 teaching。
- 不做 M17 multi-page workflow。
- 不创建 PC App、账号体系、云端数据、消息通道。

## 目标

让用户通过 M11.0 runtime conversation surface 提交自然语言任务，并让
WebAgentFlow 基于 LearnedPath catalog 和 replay evidence 选择候选路径、
绑定任务参数、请求确认、执行 replay、验证结果、汇报结果。

## 非目标

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
