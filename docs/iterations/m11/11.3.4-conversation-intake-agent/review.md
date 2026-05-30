# 复盘 / 评审（Review）

状态：implementation complete（scoped tests passed, real LLM smoke pending）

## 2026-05-17 需求确认

- Reviewer：User / ChatGPT / Codex
- Decision：approved_for_docs_generation
- Notes：
  - M11.3.3 product-level CLI smoke 已通过，但 `wagent chat` 的自然语言入口仍主要靠规则和 regex。
  - 当前问题不是浏览器执行能力，而是普通用户话语理解能力过窄。
  - 需要新增 Conversation Intake Agent / 对话理解 Agent，作为 schema-constrained intake layer。
  - 核心边界是：LLM 理解用户语言，代码校验和执行。

## 用户反馈

- “不是让 LLM 直接控制浏览器，而是让 LLM 负责理解用户说的话。” -> accepted；写入 intent / contract。
- “不要定义成登录字段解析器，要通用化。” -> accepted；slot schema 支持 semantic_type / label_seen / sensitive / source。
- “pending_intake 要能续接。” -> accepted；定义保存、合并和清理规则。
- “用户文案不能直接信 LLM。” -> accepted；最终 user_response 归 Conversation Orchestrator。
- “canonical_goal 不能成为授权。” -> accepted；只作为匹配辅助。
- “Intake output 不能污染 LearnedPath。” -> accepted；只作为 conversation intake evidence。
- “敏感信息和 prompt payload 也要处理。” -> accepted；history / events / debug console / prompt logs 均纳入 redaction 边界。
- “provider unavailable / malformed JSON / low confidence 要有负例。” -> accepted；写入 test-plan。

## 2026-05-17 补充需求：回复来源与 LLM 原始记录

- Reviewer：User / Codex
- Decision：merged_into_m11_3_4
- Notes：
  - 用户确认当前开发 Agent 已经切换为 Codex CLI；文档不再使用其他外部开发 Agent 作为主表述。
  - 用户要求在 `/conversation/history/<session_id>` 中显示当前回复用户的是具体哪一个 Agent。
  - 如果回复背后调用 LLM，需要显示 provider / model / raw trace 等详细信息。
  - 如果回复由代码产生，也要明确标注。
  - 如果失败回复由 Agent / LLM 生成，也必须留下 trace。
  - 该需求属于 M11.3.4 当前提交范围，因为 Conversation Intake Agent 引入 LLM-backed 用户语言理解后，
    history 必须能审计这条回复是否由 LLM / Agent 生成。
  - 不另拆新编号；response provenance / LLM trace 已并入 11.3.4 contract、technical-design、
    test-plan 和 plan。

## 2026-05-17 文档审核收口

- Reviewer：User / ChatGPT / Codex
- Decision：docs_review_passed
- Notes：
  - M11.3.4 文档包、产品模型更新、技术设计和测试计划通过审核。
  - 角色定位通过：Conversation Intake Agent 是受控自然语言入口层，不是浏览器操作 Agent。
  - 边界通过：LLM 负责听懂用户语言，代码负责裁决，Learning / Replay 负责行动。
  - 当时可进入实现阶段；后续已完成实现并在本 review 下方记录收口证据。

## 文档阶段验证记录

已运行：

```bash
git diff --check
```

## 2026-05-17 实现收口

- Reviewer：User / Codex
- Decision：implementation_review_passed_scoped
- Commit：`a08d434 feat: add conversation intake provenance tracing`
- Scope：
  - Conversation Intake Agent 基础设施已实现。
  - schema-constrained intake、LLM-backed provider entry、deterministic fallback 已接入 runtime。
  - malformed JSON / schema failure / low confidence guardrails 已覆盖。
  - pending intake guardrails 和 sensitive redaction 已覆盖。
  - WAgent 回复已记录 `response_provenance`。
  - LLM-backed intake trace 已记录为 redacted conversation evidence。
  - Conversation History detail 已展示代码生成 / Agent 生成 / 混合生成 / 未知来源，以及脱敏 LLM trace 摘要。
- Verification：

```bash
cd apps/api
../../.venv/bin/python -m pytest tests/test_conversation_intake.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py -q
# 101 passed

cd apps/cli
../../.venv/bin/python -m pytest tests/test_chat.py -q
# 13 passed

cd apps/console
pnpm test -- ConversationHistoryDetailPage
# 24 files passed, 169 tests passed

cd apps/api
../../.venv/bin/ruff check app/services/conversation app/schemas tests/test_conversation_intake.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py
# All checks passed

git diff --check
# clean
```

## 2026-05-17 人工测试发现：上下文恢复缺口

- Session：`a497358b-7c85-4b38-bf5a-7a8b555283fe`
- 输入：

```text
You > http://localhost:<fixture-port>/target-login
WAgent > 我会打开浏览器执行：http://localhost:<fixture-port>/target-login。
WAgent > 还没学过这个站点或页面，需要先学习。
You > 学习
WAgent > 我会打开浏览器执行：学习。
```

- Decision：deferred_to_m11_3_5
- Notes：
  - 该失败说明 `wagent chat` 仍缺少“小白用户”上下文恢复体验。
  - 裸 URL 应保存为 pending target，而不是被当作 execute。
  - 下一句“学习”应能引用上一轮 URL。
  - no-path 应主动引导学习，而不是冷拒绝。
  - CLI 应提供不误导用户的 loading / progress 状态。
  - 这些属于 11.3.5 Customer-Facing Agent Router & Skill Runtime，不继续压在 M11.3.4 基础设施收口里。

## 代码评审

- Reviewer：Codex
- Decision：passed_scoped
- Notes：Scoped code review passed；真实 LLM-backed smoke 和 live UI smoke 未执行。

## Acceptance Blockers

- 如果实现让 LLM step-by-step 操作浏览器，不得 accepted。
- 如果 LLM 输出 selector / browser actions / learned_path_id 并被执行，不得 accepted。
- 如果 malformed JSON、schema 校验失败或低 confidence 仍触发 learning / replay，不得 accepted。
- 如果 `provide_missing_info` 在没有 pending intake 时触发 learning / replay，不得 accepted。
- 如果 `canonical_goal` 被当作执行授权，不得 accepted。
- 如果 sensitive slot 明文出现在 history / events / debug console / prompt logs 中，不得 accepted。
- 如果 Intake output 被写入 LearnedPath 作为页面观察事实或执行证明，不得 accepted。
- 如果非 `interactive_chat` developer workflow 被改变，不得 accepted。
- 如果 WAgent 回复无法区分 code-generated 和 Agent-generated，不得 accepted。
- 如果 LLM-backed 回复看不到 provider / model / request trace，不得 accepted。
- 如果 raw LLM record 泄露 password / token / access_secret，不得 accepted。
- 如果 Codex CLI 被写成 WebAgentFlow 产品内部 Agent，不得 accepted。
- 如果 LLM trace 被写入 LearnedPath / replay / Supervisor evidence，不得 accepted。

## 未完成 / 风险

- 真实 LLM-backed provider smoke 尚未执行。
- fake / stub provider 可以用于实现测试，但真实 LLM smoke 才能标记 LLM-intake acceptance passed。
- Customer-Facing Agent Router & Skill Runtime 尚未实现，已转入 11.3.5。
