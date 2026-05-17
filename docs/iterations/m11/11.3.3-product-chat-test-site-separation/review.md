# 复盘 / 评审（Review）

状态：proposed

## 2026-05-17 需求确认

- Reviewer：User / ChatGPT / Codex
- Decision：approved_for_docs_generation
- Notes：
  - 11.3.2 已被 `chat-history-debug-console` 占用，本轮使用 11.3.3。
  - validation-site 是工程验证靶场，不适合作为 product-level chat 验收站。
  - product-test-site 应独立于 validation-site specs / assertions。
  - 11.2.4.2 保持在 M11.2，不迁移。
  - 本轮只写文档，不实现代码。

## 代码评审（Code Review）

- Reviewer：N/A
- Decision：not_started
- Notes：本轮为文档生成阶段，尚未实现 product-test-site 或 product-level learning。

## 用户反馈

- “先写文档，11.3.2 已经在开工了，不过两个冲突不大。” -> accepted；11.3.3 只追加文档和索引，不修改 11.3.2 目录。
- “用户指南入口修复不得回退。” -> accepted；用户指南继续以 `.venv/bin/wagent chat` 为主入口。
- “11.2.4.2 不应该放到 11.3。” -> accepted；11.2.4.2 继续属于 M11.2 validation fixture 体系。
- “项目的一键启动也要包含这次的站点拆分。” -> accepted；实现阶段 `pnpm run dev`
  必须同时启动 product-test-site。

## 最终差异（Final Delta）

### 实际交付

- 新增 11.3.3 文档包。
- 更新 M11 README / m11-plan 索引。
- 更新 `docs/user-guide/wagent-chat.md`，说明 product-test-site 是计划新增能力。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- None yet。

### WebAgentFlow Live Run 边界（Live Run Boundary）

文档阶段未触发 `verify-scenario`、autonomous run 或 product-driven browser execution。

后续实现阶段如果运行 product-level `wagent chat` smoke，必须记录真实 CLI 输出、
浏览器行为、LearnedPath id 和未使用 validation spec 的证据。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 文档阶段未执行 E2E。
- 文档阶段未真实打开浏览器。
- 文档阶段未运行 `wagent chat`。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `git diff --check` | whitespace clean | clean | 0 | pass | command output empty | 文档阶段 whitespace 检查通过 |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| product-test-site build | 站点尚未实现 | 实现阶段必须补 |
| product-level chat smoke | 文档阶段不运行产品 flow | 实现阶段必须补 |
| validation regression build | 文档阶段未改代码 | 实现阶段补 |

### Acceptance Blockers

- 如果实现阶段仍通过 `spec_id=login / scenario=valid_credentials` 完成 product-test-site learning，不得 accepted。
- 如果产品级学习读取 `apps/validation-site/specs/*.assertions.json`，不得 accepted。
- 如果用户未在聊天中提供必要输入而系统从 validation spec 自动拿输入，不得 accepted。
- 如果 product-test-site 与 validation-site 页面结构、文案、路由一比一复制，不得 accepted。
- 如果根目录 `pnpm run dev` 不启动 product-test-site，不得 accepted。

### 后续事项（Follow-ups）

- 审核 11.3.3 文档包。
- 通过后进入 product-test-site 和 product-level learning code implementation。
