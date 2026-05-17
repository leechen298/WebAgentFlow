# 11.3.2 Chat History & Debug Console

状态：implementation complete（implementation review passed, UI smoke pending）
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - history list、aggregate history payload、debug console、CLI resume 契约。
- `technical-design.md` - API、CLI、Console、测试和兼容设计。
- `test-plan.md` - API / CLI / Console / manual smoke 验证方案。
- `plan.md` - 分步实施和验证命令。
- `review.md` - 评审记录、实际验证证据和未运行项。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录文档审核和实现前验证边界；实现收尾时继续补代码验证证据。

## 当前状态

M11.0 / M11.3 已经具备 conversation 底层持久化和 `wagent chat` 普通用户入口：

- 后端有 `conversation_sessions`、`conversation_messages`、`conversation_events`。
- API 有 session create / get、message append / list、transcript、event append / list、dispatch。
- CLI 有 `wagent conversation start/status/send/messages/transcript/events`。
- `wagent chat` 会创建 `interactive_chat` session，并通过 conversation dispatch 完成学习和执行。

当前缺口不是“没有聊天记录存储”，而是没有产品化 history / debug 入口：

- 不能列出最近 sessions。
- 不能按 mode / status / time 筛选历史会话。
- 没有聚合视图一次性展示 messages、events、session learned actions、learning run、replay summaries。
- Console 没有 Conversation / Chat History 页面。
- `wagent chat` 创建 session 后没有把 session id 明确告诉用户。
- `wagent chat` 不能 resume 某个历史 `interactive_chat` session。
- Codex CLI 调试时必须先知道 session id，再手动组合 messages / events / transcript 命令。

本包把这些底层水管补成可观察、可复制、可复用的调试入口。它不新增任务执行能力，不新增 internal Agent role，也不改变 replay / Reporter / recovery 边界。

## 文档

- [Intent](./intent.md)
- [Contract](./contract.md)
- [Technical Design](./technical-design.md)
- [Test Plan](./test-plan.md)
- [Plan](./plan.md)
- [Review](./review.md)

## 明确不做

- 不做复杂搜索、全文检索或长期归档。
- 不做多用户权限、账号体系、云端用户数据或脱敏策略。
- 不做 LLM 总结历史、评分系统或失败恢复。
- 不新增 autonomous run、`verify-scenario` 或 product-driven live run。
- 不让 Codex CLI 冒充内部 WebAgentFlow Agent。
