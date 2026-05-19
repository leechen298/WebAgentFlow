# 实施计划（Implementation Plan）

状态：ready_for_implementation

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`

## 文件 / 模块

- `apps/api/app/schemas/conversation_entry_gate.py` - Entry Gate schema。
- `apps/api/app/services/conversation/entry_gate.py` - Entry Gate provider / fallback / validation。
- `apps/api/app/prompts/agents/conversation_entry_gate/` - Entry Gate prompt asset。
- `apps/api/app/prompts/registry.toml` - 登记 prompt id / version / hash。
- `apps/api/app/services/conversation/chat_runtime.py` - 在 Intake 前接入 Entry Gate。
- `apps/api/app/services/conversation/history.py` - history read model 暴露 Entry Gate trace。
- `apps/api/app/services/conversation/provenance.py` - 如有需要，标记 entry gate + code reply provenance。
- `apps/cli/wagent/chat.py` - 持续 working indicator。
- `apps/api/tests/test_conversation_entry_gate.py` - Entry Gate unit tests。
- `apps/api/tests/test_conversation_chat_runtime.py` - integration regression。
- `apps/api/tests/test_conversation_api.py` - history trace regression。
- `apps/cli/tests/test_chat.py` - CLI working UX tests。
- `apps/console/src/pages/ConversationHistoryDetailPage.vue` - 如 history trace UI 需要展示，补 UI。
- `apps/console/src/__tests__/components/ConversationHistoryDetailPage.test.ts` - 如 Console UI 修改，补测试。

## 步骤

1. 新增 Entry Gate schema，覆盖 category、requires_agent_runtime、confidence、reply_hint、
   latency、timeout 和 provider metadata。
2. 新增 Entry Gate service，使用 prompt asset loader 和 schema validation；provider / parse /
   schema / timeout / low-confidence failure 全部 fail closed。
3. 新增 Entry Gate prompt asset，明确 no-thinking、low-latency、只做 runtime relevance gate。
4. 在 ChatRuntime 中把 Entry Gate 放到 Intake 之前。
5. 非网页任务路径由 Orchestrator 生成统一友好回复，引导用户回到 WebAgentFlow 的网页操作能力，
   并记录 entry gate trace。
6. 网页任务候选继续进入现有 11.3.5 Intake + Router + Skill Runtime。
7. History read model 暴露 Entry Gate trace、latency、是否跳过 Intake / Router。
8. History / raw trace sanitizer 删除 provider thinking / CoT 字段和 `<think>` blocks。
9. CLI dispatch wait loop 增加参考 Codex CLI / Claude Code CLI 交互原则的持续 working
   indicator；非 TTY fallback 保持日志干净。
10. 补 API / CLI / history 测试，包括 provider sleep timeout 和 CoT redaction。
11. 运行 scoped pytest、ruff 和 `git diff --check`。

## 验证

验证计划来自 `technical-design.md` 和 `test-plan.md`。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_entry_gate.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py -q` | Entry Gate、ChatRuntime、history regression pass | Yes | 不触发 live run |
| `cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py -q` | CLI working UX regression pass | Yes | 不打开浏览器 |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation app/schemas tests/test_conversation_entry_gate.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py` | touched API scope ruff clean | Yes | scoped |
| `git diff --check` | whitespace clean | Yes | repo root |

## 复核清单（Review Checklist）

- [ ] Entry Gate 没有被写成新 Agent。
- [ ] Entry Gate 不调用 skill。
- [ ] 非网页输入不进入 Intake / Router。
- [ ] 闲聊 / 无关内容回复快速、简短，并引导用户回到 WebAgentFlow 使用场景。
- [ ] 网页任务候选继续进入 11.3.5 runtime。
- [ ] provider / parse / schema / low-confidence failure 不触发 learning / replay。
- [ ] provider timeout 在硬超时内 fallback，不把慢模型等待转嫁给用户。
- [ ] History / raw trace 不保存 provider thinking / chain-of-thought。
- [ ] CLI 等待期间有持续 working 状态。
- [ ] CLI 交互满足 agentic CLI 体验原则：提交后立即反馈、等待期间不静默、可中断、
  progress 与最终回复分离。
- [ ] progress / working 不作为正式 WAgent 回复记录。
- [ ] History detail 有 Entry Gate trace 和 provenance。
- [ ] 未运行 live run 时，review 不写成 live evidence passed。
