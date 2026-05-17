# 实施计划（Plan）

状态：ready_for_implementation（docs review passed, implementation not started）

## 本轮文档生成

1. 新增 11.3.4 七件套文档。
2. 更新产品模型中英文镜像，新增 Conversation Intake Agent / 对话理解 Agent。
3. 更新 roadmap 中英文镜像，登记 M11.3.4 为 interactive chat productization 后续包。
4. 更新 M11 README / m11-plan 索引。
5. 更新 `docs/user-guide/wagent-chat.md`，只写为计划能力，不写成当前已可用。
6. 运行 `git diff --check`。

## 后续实现阶段建议

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

### 5. Verification

- 单测覆盖自然说法、pending intake、失败负例和 redaction。
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
