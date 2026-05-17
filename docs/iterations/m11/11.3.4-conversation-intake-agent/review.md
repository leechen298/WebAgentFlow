# 复盘 / 评审（Review）

状态：ready_for_implementation（docs review passed, implementation not started）

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

## 2026-05-17 文档审核收口

- Reviewer：User / ChatGPT / Codex
- Decision：docs_review_passed
- Notes：
  - M11.3.4 文档包、产品模型更新、技术设计和测试计划通过审核。
  - 角色定位通过：Conversation Intake Agent 是受控自然语言入口层，不是浏览器操作 Agent。
  - 边界通过：LLM 负责听懂用户语言，代码负责裁决，Learning / Replay 负责行动。
  - 可进入实现阶段；实现前状态更新为 `ready_for_implementation`。

## 文档阶段验证

计划运行：

```bash
git diff --check
```

## 代码评审

- Reviewer：not_started
- Decision：not_started
- Notes：本轮只生成文档包，不实现代码。

## Acceptance Blockers

- 如果实现让 LLM step-by-step 操作浏览器，不得 accepted。
- 如果 LLM 输出 selector / browser actions / learned_path_id 并被执行，不得 accepted。
- 如果 malformed JSON、schema 校验失败或低 confidence 仍触发 learning / replay，不得 accepted。
- 如果 `provide_missing_info` 在没有 pending intake 时触发 learning / replay，不得 accepted。
- 如果 `canonical_goal` 被当作执行授权，不得 accepted。
- 如果 sensitive slot 明文出现在 history / events / debug console / prompt logs 中，不得 accepted。
- 如果 Intake output 被写入 LearnedPath 作为页面观察事实或执行证明，不得 accepted。
- 如果非 `interactive_chat` developer workflow 被改变，不得 accepted。

## 未完成 / 风险

- Conversation Intake Agent 尚未实现。
- LLM-backed provider 尚未接入。
- fake / stub provider 可以用于实现测试，但真实 LLM smoke 才能标记 LLM-intake acceptance passed。
