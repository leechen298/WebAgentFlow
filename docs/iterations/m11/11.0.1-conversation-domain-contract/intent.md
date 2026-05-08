# 11.0.1 Conversation Domain Contract

## 目标

定义 M11.0 runtime conversation 的领域 contract：session、message、event、
slash command、state transition 的 schema 和纯逻辑边界，为后续 session
store、API、CLI 和 orchestrator 做准备。

## 动机

M11.0 总纲覆盖 CLI runtime conversation、session state、message / event
schema、API、orchestrator、replay hook 和 testing strategy，范围太大，不能
一次性施工。11.0.1 先把 conversation 的领域语言和状态机说清，避免后续
API、CLI、store、orchestrator 互相猜字段和语义。

本包只做纯 schema / parser / state transition 逻辑规划与后续实现边界，不在
第一步混入 DB、API、CLI 或 replay side effects。它为 11.0.2 store、
11.0.3 API、11.0.4 CLI 和 11.0.5 orchestrator 铺路。

## 边界（本轮不做）

- 不做 DB / persistence。
- 不做 API endpoint。
- 不做 CLI command。
- 不调用 replay API。
- 不实现 orchestrator side effects。
- 不实现 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 E2E。

## 成功标准

- 明确 `ConversationSession` / `ConversationMessage` /
  `ConversationEvent` 的 schema 或 Pydantic model contract。
- 明确 session status enum。
- 明确 message role enum。
- 明确 event type enum。
- 明确 slash command parser contract。
- 明确 state transition 纯函数 contract。
- 有单元测试计划。
- 不引入 user / account / tenant 字段。
- 不修改 M10 replay contract。
