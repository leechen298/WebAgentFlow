# 复盘 / 评审（Review）

状态：implementation_complete（scoped tests passed, manual visible-browser smoke pending）

## 2026-05-17 设计反馈

- Reviewer：User
- Decision：addressed
- Notes：
  - `wagent chat` 学习和执行网页操作时，应默认打开用户可见的项目内置浏览器。
  - 用户可以选择不可见 / headless。
  - 功能不应该绑定具体页面。
  - 具体页面样例属于测试计划，不应写成功能边界。

## 2026-05-17 文档包生成

- Reviewer：Codex
- Decision：superseded_by_approved_for_implementation
- Notes：
  - 已按代码型迭代文档规范生成七件套。
  - Contract / technical design 描述通用 visible browser operation。
  - `test-plan.md` 单独记录当前人工验收页面样例。

## 2026-05-17 文档审查补充

- Reviewer：ChatGPT / Codex
- Decision：addressed
- Notes：
  - 已确认远端 `refs/heads/v0.1` 指向 `0b1b276afc9771f112c3fa51f5747a1f5da7a303`。
  - `test-plan.md` 和 `plan.md` 的 Markdown 表格中不能直接放 `||` 命令，应改为表格外代码块。

## 2026-05-17 文档审核通过

- Reviewer：User / ChatGPT
- Decision：approved_for_implementation
- Notes：
  - `v0.1` 分支发布一致性已通过。
  - `plan.md` / `test-plan.md` command table rendering 已修复。
  - M11.3.1 需求文档、技术设计、测试计划和用户指南入口修复均已通过。
  - 当前可进入实现阶段；实现仍需补代码、测试和真实可见浏览器 smoke。

## 代码评审（Code Review）

- Reviewer：Codex
- Decision：implementation_complete_with_manual_smoke_pending
- Notes：
  - 当前 HEAD 已包含 `86b947c feat: enable visible chat browser loop`。
  - `wagent chat` 支持 `--headless`，默认 create session metadata 写入
    `browser_visibility=visible`。
  - Conversation runtime 从 session metadata 推导 `headless`，并传给 learning / replay
    handlers。
  - scoped CLI / API tests passed。
  - 真实可见浏览器人工 smoke 尚未在本 review 中记录。

## 用户反馈

- “wagent 的操作，其实是要真实打开一个浏览器” -> accepted，写入 `intent.md` / `contract.md`。
- “学习的时候也可以默认以用户可见的方式学习。当然用户可以选择不可见。” -> accepted，定义默认 visible 和 `--headless` opt-out。
- “功能不应该关心具体页面” -> accepted，contract / design 不绑定页面。
- “/login 那个应该是测试计划了” -> accepted，页面样例只放在 `test-plan.md`。
- “`wagent: command not found` 不能只提示重新 source，必须补 CLI 安装 / 检查步骤” -> accepted，补入 user guide、technical design、test plan 和 plan。

## 最终差异（Final Delta）

### 实际交付

- `wagent chat` 默认 visible browser policy 已实现。
- `wagent chat --headless` opt-out 已实现。
- learning / replay 链路已接收并传递 headless policy。
- scoped CLI / API tests passed。
- Manual visible browser smoke pending。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- None yet。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本次收口未触发 `verify-scenario`、autonomous run 或 product-driven browser execution。

后续人工 smoke 如果通过 `wagent chat` 学习页面，会触发真实 autonomous learning；届时必须
记录 `pass_gate.status`、Supervisor verdict、scorecard 和 `run_id`。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 本次收口执行了 scoped CLI / API tests。
- 本次收口未真实打开可见浏览器。
- 本次收口未运行 live `wagent chat` learning smoke。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `find docs/iterations/m11/11.3.1-visible-chat-browser-operation -maxdepth 1 -type f -print | sort` | 七件套文档完整 | 7 files present | 0 | pass | README / intent / contract / technical-design / test-plan / plan / review | 文档包完整性 |
| `rg -n "localhost:5175/login" docs/iterations/m11/11.3.1-visible-chat-browser-operation/{README,intent,contract,technical-design,plan}.md` | 功能文档不包含具体验收 URL | no matches | 1 | pass | concrete URL kept out of capability docs | 具体 URL 留在 `test-plan.md` acceptance sample；`review.md` 只记录本检查 |
| `git diff --check` | whitespace clean | clean | 0 | pass | no output | 文档阶段检查 |
| `git ls-remote origin refs/heads/v0.1` | remote v0.1 points at docs entry fix | `0b1b276afc9771f112c3fa51f5747a1f5da7a303` | 0 | pass | remote ref output | 确认 0b1b276 已落到远端 v0.1 |
| `git ls-remote origin refs/heads/v0.1` | remote v0.1 points at rendered table fix | `e62b2ca3e606ccca7b1efb64de9db4a1f91f5cf5` | 0 | pass | remote ref output | 确认 e62b2ca 已落到远端 v0.1 |
| `cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py tests/test_conversation.py -q` | CLI scoped tests pass | 30 passed | 0 | pass | pytest output | 覆盖 `wagent chat` payload / wording / conversation regression |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_learned_path_replay.py -q` | API scoped tests pass | 61 passed | 0 | pass | pytest output | 覆盖 visible/headless learning/replay 参数传递 |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| Live `wagent chat` smoke | 本次收口不触发 product-driven browser execution | 后续必须记录真实 CLI 输出 / run_id / visible browser evidence |
| Manual browser smoke | 本次收口未真实打开可见浏览器 | 通过前不得声称 MANUAL-1 passed |
| Ruff scoped lint | 本次只补 scoped pytest 和文档状态 | 如继续做 implementation closeout，可补 ruff evidence |

### 后续事项（Follow-ups）

- 补真实可见浏览器人工 smoke evidence。
- 如需要发布级 closeout，再补 ruff evidence 并将 manual smoke 状态更新为 passed。
