# 11.3.9 Conversation Debug Timeline

状态：docs_generated_pending_design_review
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包为后续代码实现准备完整七件套。当前只生成文档，不授权实现；实现前必须先完成
design review，并在 `review.md` 中把 `implementation_authorized` 更新为 `yes`。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - 调试时间线、可见 payload、终端日志边界和 evidence 契约。
- `technical-design.md` - API read model、history service、Console detail、CLI handoff 设计。
- `test-plan.md` - API / Console / CLI / smoke 验证方案和 live-run 边界。
- `plan.md` - 分步实施、验证命令和停止条件。
- `review.md` - 文档生成记录、设计评审、实际验证证据和未运行项。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录实现差异和验证证据。

## 当前状态

现有 11.3.2 已实现 Conversation History / Debug Console 基础：

- Console 有 `/conversation/history` 和 `/conversation/history/:session_id`。
- API 有 `GET /conversation/sessions/{session_id}/history`，返回 messages、events、
  learned_actions、learning_runs、replay_summaries、llm_traces 和 raw。
- Detail 页当前以 Transcript / Events / Raw JSON 为主，事件 payload 主要还是面向开发者。
- 开发终端日志主要来自 Uvicorn / WatchFiles / httpx，能看到 HTTP 请求，但不能解释
  `wagent chat` 当前正在理解什么、路由到哪里、为什么产生某个用户回复或选项。

本包把已有 history detail 升级为“人能读懂的调试时间线”：先解释流程，再允许展开
脱敏 raw payload。它不新增运行时能力，不替代 conversation events，也不把后端终端日志
变成完整 payload dump。

## 文档

- [Intent](./intent.md)
- [Contract](./contract.md)
- [Technical Design](./technical-design.md)
- [Test Plan](./test-plan.md)
- [Plan](./plan.md)
- [Review](./review.md)

## 明确不做

- 不新增数据库表或长期日志归档系统。
- 不把 LLM request / response、用户输入、页面信息完整打印到后端终端。
- 不新增 live autonomous run、`verify-scenario`、replay 或 learning 行为。
- 不让 Console 页面发明 Supervisor / Planner / Reporter verdict。
- 不把普通用户-facing 文案改成内部 trace 术语。
