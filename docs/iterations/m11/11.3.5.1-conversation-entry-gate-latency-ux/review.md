# 复盘 / 评审（Review）

状态：ready_for_implementation

## 2026-05-19 设计评审（Design Review）

- Reviewer：Codex CLI
- Decision：approved_for_implementation
- Notes：
  - 本 patch-level 迭代来自 11.3.5 人工试用反馈。
  - 当前 `wagent chat` 只有一次性 `正在理解你的需求。`，不能视为持续 loading / working UX。
  - 非网页输入不应默认进入 Intake + Router 两层 LLM。
  - Entry Gate 应是窄职责入口门禁，不是新 Agent、不调用 skill、不触发 learning / replay。

## 代码评审（Code Review）

- Reviewer：pending
- Decision：not_started
- Notes：implementation not started。

## 用户反馈

- 用户希望 CLI 使用体验至少接近 Codex CLI / Claude Code CLI：等待期间要能看出系统正在工作，
  不能像卡住。
  - accepted：本轮把持续 working indicator 写成一等验收项。
- 用户强调 CLI 工具开发设计要参考 Claude Code CLI / Codex CLI 和用户沟通时的体验。
  - accepted：本轮明确参考 agentic CLI 交互原则，但不要求复制具体视觉样式。
- 用户不接受通过硬编码问候白名单绕过 runtime。
  - accepted：Entry Gate 使用轻量、低延迟、schema-constrained 判断，不以白名单作为产品策略。
- 用户要求闲聊或无关内容也要快速响应，并引导用户回到 WebAgentFlow 的使用上。
  - accepted：本轮把 non-web reply policy 写入 contract，要求回复收束到网页操作任务。
- Codex CLI 审核指出低延迟 / 非 thinking 不够可执行，如果仍接慢模型，Entry Gate 也可能慢。
  - accepted：补入硬 timeout，默认目标不超过 1.5 秒，绝对上限不超过 2 秒；timeout 后 friendly fallback。
- Codex CLI 审核指出 history trace 必须禁止保存 provider thinking / CoT。
  - accepted：补入 trace redaction contract 和 test-plan，要求删除 `<think>` blocks 和 thinking / reasoning 字段。

## 最终差异（Final Delta）

### 实际交付

- Pending implementation。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- Pending implementation。

### WebAgentFlow Live Run 边界（Live Run Boundary）

除非用户明确要求 live run，不得触发 `verify-scenario`、autonomous run 或
product-driven browser execution。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 当前为文档阶段，未运行 CLI smoke、UI smoke、E2E 或 live autonomous run。
- 没有 run_id、截图、日志、exit code、pass / fail count 或可复查输出时，结论必须写成
  `not run` / `unverified`。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `git diff --check` | whitespace clean | pending | pending | pending | pending | 文档生成后执行 |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| CLI smoke | 文档阶段未实现 | 实现后必须补 |
| History UI smoke | 文档阶段未实现 | 实现后必须补 |
| Live autonomous run | 本轮不要求 | 不影响 Entry Gate / CLI latency 验收 |

### 后续事项（Follow-ups）

- 已切到 `ready_for_implementation`，进入 Codex CLI 实现。
