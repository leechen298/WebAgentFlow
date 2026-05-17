# 实施计划（Plan）

状态：implementation complete（scoped tests passed, real LLM smoke pending）

## 文档生成阶段记录

1. 新增 11.3.4 七件套文档。
2. 更新产品模型中英文镜像，新增 Conversation Intake Agent / 对话理解 Agent。
3. 更新 roadmap 中英文镜像，登记 M11.3.4 为 interactive chat productization 后续包。
4. 更新 M11 README / m11-plan 索引。
5. 更新 `docs/user-guide/wagent-chat.md`，文档生成阶段只写为计划能力，不写成当前已可用。
6. 运行 `git diff --check`。

## 实现阶段收口

实现已在 `a08d434 feat: add conversation intake provenance tracing` 中完成。
本包收口 Conversation Intake Agent 基础设施和 history provenance / LLM trace 可观察性。

不在本包继续扩展：

- 裸 URL 保存为 pending target。
- 用户下一句“学习”继承上一轮 URL。
- no-path 后主动引导学习。
- CLI loading / progress 体验细化。
- History 列表本地时区格式。

这些进入后续 11.3.5 Chat Context Recovery UX。

## 已实现阶段拆解

### 1. Schema and service contract

- 新增 conversation intake schema。
- 新增 `ConversationIntakeService`。
- 支持 LLM-backed provider、fake provider 和 deterministic fallback。
- schema 校验失败时返回 safe failure，不触发 browser action。

### 2. Pending intake state

- 在 session metadata 中保存 `pending_intake`。
- 实现 pending intake 合并、清理、turns_remaining 和 target URL guard。
- `provide_missing_info` 只有 pending intake 存在时生效。

### 3. Chat runtime integration

- `interactive_chat` session 优先走 intake flow。
- 完整 `learn_operation` 调用 product-level learning。
- 缺信息时由 Orchestrator 生成追问。
- `execute_operation` 仍按 current session learned actions + target scope 匹配。
- 非 interactive chat 保持原路径。

### 4. Redaction

- sensitive slots 在 history / events / debug console 中 redacted。
- prompt payload / provider trace 不长期保存明文 sensitive slot。
- 用户可见回复不重复明文敏感值。

### 5. Response provenance / LLM trace

- 为每条 user-visible agent message 写入 `response_provenance`。
- code-generated 回复标记具体 code producer。
- LLM-backed Agent 回复记录 internal Agent role 和 `llm_trace_ids`。
- provider failure + code fallback 标记 `fallback=true`。
- 追加 `llm_trace_recorded` event，并在写入前完成 redaction。
- History read model 聚合 top-level `llm_traces`，并在 message 上附加 provenance。
- Console history detail transcript 展示 `代码生成` / `Agent 生成` / `混合生成` / `未知来源`。
- Codex CLI 只作为外部开发 / 测试 Agent，不写成产品内部 Reply Producer。

### 6. Verification

- 单测覆盖自然说法、pending intake、失败负例和 redaction。
- 单测覆盖 response provenance、LLM trace 聚合、old history compatibility。
- Console 组件测试覆盖 history detail provenance 展示。
- scoped API / CLI tests。
- fake provider tests 通过后再做真实 LLM smoke。

## Review Checklist

- [ ] LLM 不直接操作浏览器。
- [ ] LLM 不输出 selector / browser steps。
- [ ] LLM 不输出 learned_path_id 作为执行授权。
- [ ] Orchestrator 统一用户文案。
- [ ] `canonical_goal` 只是匹配辅助。
- [ ] `pending_intake` 清理规则完整。
- [ ] sensitive slots 默认 redacted。
- [ ] provider unavailable / malformed JSON / low confidence 均不触发 browser action。
- [ ] 非 `interactive_chat` regression 通过。
- [ ] 每条 WAgent 回复有 code / agent / hybrid / unknown 来源。
- [ ] LLM-backed 回复可在 history 中看到 provider / model / schema / trace。
- [ ] Raw LLM record 默认 redacted。
- [ ] Codex CLI 不被写成产品内部 Agent。
