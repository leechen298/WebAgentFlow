# 技术设计（Technical Design）

状态：implementation_complete（scoped tests passed, manual visible-browser smoke pending）

## 当前状态（Current State）

M11.3 已实现 `wagent chat`：

- CLI 顶层命令自动创建 `current_mode=interactive_chat` session；
- learning happy path 通过 `LearningRunService` 调用 autonomous learning 并沉淀 LearnedPath；
- execute happy path 通过 session `learned_actions` 命中后调用 replay；
- CLI 在 dispatch 前打印普通用户可理解的学习 / 执行反馈；
- 非 `interactive_chat` session 保持既有 preview / confirmation / replay 逻辑。

当前浏览器运行方式：

- `RuntimeConfig.headless` 默认 `True`；
- `LearningRunRequest.headless` 默认 `True`；
- `LearningRunService` 会把 `request.headless` 传给 `RuntimeConfig`；
- `learned_path_replay.run_replay()` 内部直接调用 `create_execution_runtime()`，不能由 chat runtime 覆盖
  headless；
- `run_explicit_replay()` 也没有暴露 headless 参数。

因此，`wagent chat` 的学习和执行虽然由 Playwright Chromium 驱动，但普通用户默认看不到浏览器窗口。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| `wagent chat` 默认 visible | CLI create-session metadata 写 `browser_visibility=visible`；chat runtime 转换为 `headless=False` | CLI tests + chat runtime tests | 只影响 interactive chat |
| `wagent chat --headless` opt-out | CLI 新增 `--headless`，metadata 写 `browser_visibility=headless` | CLI parser / request payload tests | 不改变 `--timeout` |
| CLI entry reliable before smoke | 用户指南和 smoke 前置检查使用 `.venv/bin/wagent`；`command not found` 排障安装 `apps/cli` | docs check + CLI smoke precheck | 不只提示重新 source |
| Session metadata 是权限来源 | Chat runtime 从 `session.metadata_json.browser_visibility` 读取；dispatch metadata 只审计 | chat runtime tests | 防止普通 dispatch 伪造 chat policy |
| 学习链路可见 | learning handler 接收 `headless` 并传给 `LearningRunRequest` | learning handler / service tests | Learning service 已有 headless 字段 |
| 执行链路可见 | replay hook / `run_replay` 支持 headless override | replay tests + chat runtime tests | 默认保持 existing headless |
| 非 chat mode 不变 | 只有 `session.current_mode == interactive_chat` 才读取 chat visibility | orchestrator regression tests | confirmation gate 不动 |
| 不暴露开发者信息 | CLI 文案继续过滤/避免 selector、id、className、LearnedPath、run_id | CLI tests + manual smoke | 可见浏览器不等于输出内部日志 |

## 实现方案（Proposed Implementation）

### CLI

修改 `apps/cli/wagent/chat.py`：

- 新增 `--headless` flag，默认 `False`。
- session create payload 中写入：
  - `metadata.browser_visibility = "visible"` 默认；
  - 用户传 `--headless` 时写 `"headless"`。
- dispatch metadata 可附带 `browser_visibility` 作为审计字段。
- 进度文案调整为用户能理解的浏览器动作：
  - 学习：`我会打开浏览器学习这个页面的操作。`
  - 执行：`我会打开浏览器执行这个操作。`
  - 保留具体动作说明，例如“输入账号密码，并点击‘登录’按钮完成登录”。
- `--timeout` 行为不变。
- 用户指南和人工 smoke 前置步骤使用 `.venv/bin/wagent chat`，不依赖 shell activation。
- `zsh: command not found: wagent` 的排障必须指向 CLI 安装 / PATH 问题：
  - `test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'`
  - `.venv/bin/wagent --help`
  - `.venv/bin/wagent chat`

### Conversation Runtime

修改 `apps/api/app/services/conversation/chat_runtime.py`：

- 增加 `_chat_headless(session)` helper：
  - `metadata.browser_visibility == "headless"` -> `True`；
  - 其他值或缺失 -> `False`。
- 在 `try_handle()` 中从 session metadata 解析 `headless`，传入 learn / execute 分支。
- 学习分支调用 `learning_handler(..., headless=headless)`。
- 执行分支调用 `replay_handler(..., headless=headless)`。
- event payload 可记录 `browser_visibility`，但用户响应不暴露内部参数名。

### Router Wiring

修改 `apps/api/app/routers/conversation.py`：

- learning handler wrapper 接收 `headless: bool = True`，并传给 `LearningRunRequest.headless`。
- replay handler wrapper 接收 `headless: bool = True`，并传给 `run_explicit_replay(..., headless=headless)`。
- developer workflow 调用 replay handler 时不传 headless，默认仍为 `True`。

### Replay Runtime

修改 `apps/api/app/services/conversation/replay_hook.py`：

- `run_explicit_replay(db_session, learned_path_id, url, *, headless: bool = True)`。
- 继续查 LearnedPath / trust status。
- 调用 `run_replay(learned_path, url, headless=headless)` 或等价 runtime config 参数。

修改 `apps/api/app/services/learning/learned_path_replay.py`：

- `run_replay(learned_path, url, *, headless: bool = True)`。
- 创建 runtime 时使用 `RuntimeConfig(headless=headless)`。
- 未传参数时保持原来的 headless behavior。

### Tests

新增或更新：

- CLI tests：`wagent chat` 默认 create-session metadata 为 visible；`--headless` 写 headless。
- Chat runtime tests：interactive chat visible session 会把 `headless=False` 传给 learning / replay handler；
  headless session 会传 `True`。
- Replay hook tests：默认 headless 不变；显式 `headless=False` 传到 `run_replay` / runtime factory。
- Regression：非 interactive chat confirmation gate 不变。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | Yes | conversation router wiring 接收并传递 handler headless option | 不改变 endpoint path 或 response envelope |
| API response schema | No | 不新增 response 字段 | N/A |
| Database schema / migration | No | 仅使用 metadata JSON | 无 migration |
| CLI | Yes | `wagent chat --headless`，默认 visible | 旧 `wagent chat` 命令仍可用 |
| Console UI | No | 不涉及 console | N/A |
| Conversation events | Yes | 可在 chat event payload 记录 browser visibility | 不改变 event type |
| Replay execution | Yes | 支持 headless override | 默认仍 headless |
| Reporter | No | 不接 Task Result Reporter | N/A |
| Worker / async jobs | No | 同步 CLI / API 路径 | N/A |
| Tests / fixtures | Yes | CLI / API unit tests 补覆盖 | 不改 fixture 页面 |
| Docs | Yes | 更新 M11.3.1 docs 和用户指南 | 页面样例放 test-plan；入口排障必须可靠 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

不新增数据库字段和 migration。

新增 session metadata 约定：

```json
{
  "browser_visibility": "visible"
}
```

允许值：

- `visible`
- `headless`

非法值按 `visible` 处理，避免 chat 默认退回不可见运行。

## 服务 / 模块设计（Service / Module Design）

### Browser visibility helper

建议放在 `chat_runtime.py` 内部，避免过早抽象：

```python
def _chat_headless(session: Any) -> bool:
    metadata = session.metadata_json or {}
    return metadata.get("browser_visibility") == "headless"
```

### Handler signature

Learning handler:

```python
def learning_handler(url: str, raw_text: str, *, headless: bool = True) -> LearningRunResult:
    ...
```

Replay handler:

```python
def replay_handler(learned_path_id: str, url: str, *, headless: bool = True) -> ConversationReplaySummary:
    ...
```

默认值为 `True`，保障非 chat 调用方不变。

## 数据流（Data Flow）

默认可见学习：

```text
wagent chat
-> create session metadata.browser_visibility=visible
-> user learn message
-> chat runtime reads session metadata
-> headless=False
-> LearningRunService.run(...)
-> RuntimeConfig(headless=False)
-> visible Playwright Chromium window
-> user_response
```

默认可见执行：

```text
user task message
-> chat runtime matches session learned action
-> headless=False
-> run_explicit_replay(..., headless=False)
-> run_replay(..., headless=False)
-> visible Playwright Chromium window
-> user_response
```

后台运行：

```text
wagent chat --headless
-> create session metadata.browser_visibility=headless
-> chat runtime passes headless=True
-> Playwright Chromium runs without visible window
```

## 状态推导（Status / State Derivation）

本轮不改变 conversation status 推导。

浏览器可见性推导优先级：

1. `session.metadata_json.browser_visibility == "headless"` -> headless；
2. 其他值或缺失 -> visible；
3. dispatch metadata 不参与运行决策。

## 兼容性（Compatibility）

- 已有 `wagent chat` 用户不需要改命令；默认从 headless 变为 visible。
- 不希望显示浏览器的用户使用 `wagent chat --headless`。
- 旧 session metadata 缺少 `browser_visibility` 时，interactive chat 视为 visible。
- 非 chat replay 默认仍是 headless。
- API response 不变，前端无需适配。

## 失败 / 边界情况（Failure / Edge Cases）

- Playwright headed browser 启动失败：返回现有 runtime error / 学习失败文案，不做 M12 recovery。
- 用户在浏览器窗口中手动干预：本轮不检测、不接管，测试时记录为人工干预风险。
- 无图形界面环境：用户应使用 `wagent chat --headless`；默认 visible 失败时文案保持简洁。
- 浏览器窗口被用户关闭：按现有 Playwright runtime failure 处理。
- 非法 `browser_visibility` metadata：按 visible 处理并可记录 event payload。

## 非目标（Non-goals）

- 不接用户系统 Chrome。
- 不实现 browser profile / cookie persistence。
- 不做 streaming step-by-step progress。
- 不让用户接管或继续未完成操作。
- 不扩展具体页面能力；页面只属于测试计划。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| CLI unit | 默认 visible、`--headless` opt-out、payload 正确 | `test-plan.md` CLI-1 / CLI-2 |
| CLI entry docs | `.venv/bin/wagent` 检查、安装和 `--help` 前置验证 | `test-plan.md` CLI-0 |
| Chat runtime unit | session metadata 驱动 learning / replay headless option | `test-plan.md` API-1 / API-2 |
| Replay integration | replay hook / run_replay 默认兼容并支持 override | `test-plan.md` API-3 |
| Regression | 非 chat confirmation / conversation send 不变 | `test-plan.md` REG-1 |
| Manual smoke | 用户真实看到浏览器打开和操作 | `test-plan.md` MANUAL-1 |

## 验证命令入口（Validation Commands）

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_learned_path_replay.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py tests/test_conversation.py -q
cd apps/api && ../../.venv/bin/ruff check app/services/conversation app/services/learning tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_learned_path_replay.py
cd apps/cli && ../../.venv/bin/ruff check wagent/chat.py tests/test_chat.py
git diff --check
```
