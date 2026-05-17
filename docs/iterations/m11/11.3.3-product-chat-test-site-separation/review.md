# 复盘 / 评审（Review）

状态：accepted（implementation review passed, product-level CLI smoke passed）

## 2026-05-17 需求确认

- Reviewer：User / ChatGPT / Codex
- Decision：approved_for_docs_generation（superseded by implementation closeout below）
- Notes：
  - 11.3.2 已被 `chat-history-debug-console` 占用，本轮使用 11.3.3。
  - validation-site 是工程验证靶场，不适合作为 product-level chat 验收站。
  - product-test-site 应独立于 validation-site specs / assertions。
  - 11.2.4.2 保持在 M11.2，不迁移。
  - 文档生成阶段只写文档，不实现代码；该阶段已完成。

## 2026-05-17 文档审核收口

- Reviewer：User / ChatGPT / Codex
- Decision：docs_review_passed（superseded by implementation closeout below）
- Notes：
  - M11.3.3 文档包、技术设计、测试计划和验收红线已通过审核。
  - 当时文档门禁已打开，允许进入 `apps/product-test-site` 和 product-level
    `wagent chat` learning 实现。
  - 此记录已被后续 implementation closeout 覆盖。

## 代码评审（Code Review）

- Reviewer：Codex
- Decision：passed
- Notes：
  - M11.3.3 已实现 product-test-site、product-level chat learning 和 target URL scoped execution。
  - 实现未修改 `docs/iterations/**`。
  - 代码审查确认 product-level learning 不再使用 validation `spec_id / scenario`。
  - 真实 `wagent chat` 小白用户路径 smoke 已通过，见下方 evidence。

## 用户反馈

- “先写文档，11.3.2 已经在开工了，不过两个冲突不大。” -> accepted；11.3.3 只追加文档和索引，不修改 11.3.2 目录。
- “用户指南入口修复不得回退。” -> accepted；用户指南继续以 `.venv/bin/wagent chat` 为主入口。
- “11.2.4.2 不应该放到 11.3。” -> accepted；11.2.4.2 继续属于 M11.2 validation fixture 体系。
- “项目的一键启动也要包含这次的站点拆分。” -> accepted；实现阶段 `pnpm run dev`
  必须同时启动 product-test-site。
- “只学习和操作用户输入的站点；未学习过的站点需要给用户反馈。” -> accepted；
  实现阶段必须移除 product-level `/login` gate，并按 target URL / site scope 匹配当前 session
  learned actions。

## 最终差异（Final Delta）

### 实际交付

- 新增 11.3.3 文档包。
- 更新 M11 README / m11-plan 索引。
- 更新 `docs/user-guide/wagent-chat.md`，说明 product-test-site 是当前可用的产品级聊天验收站。
- 文档审核通过；后续实现已经完成并收口。
- 新增 `apps/product-test-site`，默认端口 `5176`。
- 根 `pnpm run dev` 接入 product-test-site。
- `wagent chat` product-level learning 不再传 `spec_id / scenario`，输入来自用户 utterance。
- 当前 session learned action 按 target URL / site scope 隔离，未学习 URL 返回用户级反馈。
- 用户指南已切换到 product-test-site 主线。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- No requirement deviation found in closeout review.

### WebAgentFlow Live Run 边界（Live Run Boundary）

文档阶段未触发 `verify-scenario`、autonomous run 或 product-driven browser execution。

实现收口阶段使用普通用户入口 `.venv/bin/wagent chat` 触发 product-level learning / replay。
该路径是 product-driven browser execution，不是 direct autonomous-run endpoint 调用。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- Product-level CLI smoke 已执行。
- `wagent chat` session id：`20602dde-1a64-4e81-8784-9b7949a9d866`。
- Learning run id：`c4564860-5140-4f13-a552-bca6697208df`。
- LearnedPath id：`03fb1fa1-2589-45cf-8322-4ba3f2809077`。
- Browser visibility metadata：`visible`。
- Learned action：`进入工作台`，target URL `http://localhost:5176/workspace-login`。
- Replay result：`replay_status=succeeded`，`final_url=http://localhost:5176/workspace-home`，
  `drift_status=none`，`step_count=4`。
- 未学习 URL fallback：`帮我在 http://localhost:5176/orders 导出订单` 返回
  `还没学过这个站点或页面，需要先学习。`，event reason `unlearned_target_url`。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `git diff --check` | whitespace clean | clean | 0 | pass | command output empty | 文档阶段 whitespace 检查通过 |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py -q` from `apps/api` | product-level chat runtime / learning tests pass | `19 passed in 0.14s` | 0 | pass | local command output | 不触发 live autonomous run |
| `../../.venv/bin/pytest tests/test_chat.py -q` from `apps/cli` | CLI chat tests pass | `13 passed in 0.07s` | 0 | pass | local command output | 包含 product workspace progress labels |
| `PYTHONPATH=. ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/learning/learning_run_service.py app/routers/conversation.py tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py` from `apps/api` | API scoped ruff clean | `All checks passed!` | 0 | pass | local command output | scoped lint |
| `../../.venv/bin/python -m ruff check wagent/chat.py tests/test_chat.py` from `apps/cli` | CLI scoped ruff clean | `All checks passed!` | 0 | pass | local command output | scoped lint |
| `pnpm --filter @web-agent-flow/product-test-site build` | product-test-site build pass | build passed | 0 | pass | vite build output | product site |
| `pnpm --filter @web-agent-flow/validation-site build` | validation-site regression build pass | build passed | 0 | pass | vite build output | validation-site retained |
| `pnpm run build` | root build includes packages / console / validation / product | build passed | 0 | pass | local command output | validates build script wiring |
| `.venv/bin/wagent chat` | product-level learn / execute / unlearned URL fallback | passed | 0 | pass | session `20602dde-1a64-4e81-8784-9b7949a9d866` history | product-driven browser execution |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| Full API suite | 本轮只按 test-plan / scoped risk 跑 targeted tests | 如做发布级大回归可补 |
| Console UI smoke | M11.3.3 不改 Console UI | 由 11.3.2 history/debug console 验收覆盖 |

### Acceptance Blockers

- 如果实现阶段仍通过 `spec_id=login / scenario=valid_credentials` 完成 product-test-site learning，不得 accepted。
- 如果产品级学习读取 `apps/validation-site/specs/*.assertions.json`，不得 accepted。
- 如果用户未在聊天中提供必要输入而系统从 validation spec 自动拿输入，不得 accepted。
- 如果 product-test-site 与 validation-site 页面结构、文案、路由一比一复制，不得 accepted。
- 如果根目录 `pnpm run dev` 不启动 product-test-site，不得 accepted。
- 如果产品级学习仍限制为 `/login` 或固定站点，不得 accepted。
- 如果未学习过的 target URL / site 跨站点命中历史 LearnedPath，不得 accepted。

当前 closeout 结果：上述 blockers 均未触发。Conversation history 记录
`scenario=null`、learned action `scenario=null`，product-level learning event target URL 为
`http://localhost:5176/workspace-login`，未学习 URL 走 `chat_no_path` / `unlearned_target_url`。

### 后续事项（Follow-ups）

- P2：执行成功文案当前为 `进入工作台完成。`，后续可优化为更自然的 `已进入工作台。`。
- P2：未学习 URL 时 CLI progress 会先打印“我会打开浏览器执行...”，随后返回未学习提示；
  后续可改为 dispatch 后再打印执行进度，避免对普通用户显得过于乐观。
