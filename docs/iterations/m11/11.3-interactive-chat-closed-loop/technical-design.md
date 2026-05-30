# 技术设计（Technical Design）

状态：accepted（manual smoke passed）

## 当前状态

当前 CLI 只有 `verify`、`conversation`、`skill` 顶层命令。`wagent conversation`
是 non-interactive developer workflow，`send` 会调用
`/conversation/sessions/{session_id}/dispatch`。

当前 conversation dispatch 对普通 free text 会走 planning preview，并在需要确认时
进入 `awaiting_confirmation`。这个逻辑必须保留给非 `interactive_chat` session。

当前 autonomous exploration endpoint 会持久化 run，并在 pass gate 通过时尝试 ingest
LearnedPath，但 response data 只暴露 `run_id`，不直接暴露 `learned_path_id`。

M11.3 代码只保证 `wagent chat` learning path 使用 `LearningRunService` 并显式返回
`run_id` / `learned_path_id`。`POST /exploration/autonomous-runs` / Workbench 仍保留
既有 router pipeline；将 exploration router 复用该 service 是后续 refactor，不作为本轮
验收条件。

## Contract Alignment

- `interactive_chat` gating：由 `session.current_mode` 决定；dispatch metadata 只审计。
- `wagent chat` 是顶层命令；不塞进 `wagent conversation` 子命令。
- 学习成功必须以 `learned_path_id` 可查询为准。
- session learned actions 只在当前 session 内命中；不做 global fallback。
- chat happy path 追加 agent messages，保证 transcript 可复查。
- 非 chat mode 不绕过 confirmation。

## 模块设计

### CLI

新增 `apps/cli/wagent/chat.py`：

- 解析 `--api-base`，默认 `WBAF_API_BASE` 或 `http://localhost:8001`。
- 解析 `--timeout`，默认 `180` 秒。
- 启动时 `POST /conversation/sessions`：
  ```json
  {
    "current_mode": "interactive_chat",
    "metadata": {
      "client": "wagent_chat",
      "runtime_policy": "auto_execute_happy_path"
    }
  }
  ```
- 打印欢迎语。
- 循环读取 stdin，支持 `exit` / `quit` / `:q`。
- 每轮发 dispatch 前先打印普通用户可理解的动作级反馈：
  - 学习登录页：`我会学习：在登录页输入账号密码，并点击“登录”按钮。`
  - 执行登录：`我会执行：输入账号密码，并点击“登录”按钮完成登录。`
  - 其它任务：去掉“帮我 / 请 / 麻烦”等口语前缀后，打印例如
    `我会执行：导出报表。`
- CLI 输出不得暴露 selector、className、id、LearnedPath、run_id 或 replay id。
- 后端返回 `开始学习页面操作。` / `执行中。` 时，CLI 可去重，避免用户看到重复等待语。
- 每轮 `POST /conversation/sessions/{session_id}/dispatch`，body：
  ```json
  {
    "input": "...",
    "metadata": {
      "client": "wagent_chat"
    }
  }
  ```
- 打印 `data.user_response`。多行 response 按行输出，每行加 `WAgent > `。

修改 `apps/cli/wagent/main.py`：

- 注册顶层 `chat` 命令。
- 保持 `conversation` 命令不变。

### Learning Service

新增 `apps/api/app/services/learning/learning_run_service.py`：

- 提供同步 learning API，供 exploration router 和 interactive chat runtime 复用。
- 负责：
  - 加载 spec scenario inputs；
  - 创建 execution runtime；
  - 调用 `run_autonomous_exploration`；
  - 运行 spec verification；
  - 持久化 exploration run；
  - ingest LearnedPath；
  - 返回 `run_id` 和 `learned_path_id`。

现有 exploration router 可以逐步改为调用该 service，避免 duplication。M11.3
实现时至少要保证 chat runtime 使用该 service，不直接调用 router 私有函数。

### Conversation Chat Runtime

新增 `apps/api/app/services/conversation/chat_runtime.py`：

- `parse_chat_intent(raw_input) -> learn_page | execute_task | unknown`
- `handle_interactive_chat(session, raw_input, metadata) -> DispatchResult | None`
- 学习分支：
  - 仅支持 `/entry` URL；
  - 调用 learning service；
  - 校验 `learned_path_id` 可查询；
  - 读取 session metadata，按 alias merge learned action；
  - append agent messages；
  - append audit events；
  - 返回两行用户文案。
- 执行分支：
  - 只从当前 session metadata learned_actions 命中；
  - 命中“登录”后调用 replay handler；
  - append “执行中。”和最终结果 agent messages；
  - replay_status in `succeeded | observed` 返回“登录完成。”；
  - 其他状态返回简洁失败文案，不做 recovery。
- 未命中分支：
  - append agent message；
  - 返回“还没学过这个操作，需要先学习。”

修改 `ConversationOrchestrator`：

- 在 append user message 和 parse command 后，优先检查 `session.current_mode`。
- 仅当 `session.current_mode == "interactive_chat"` 时调用 chat runtime。
- chat runtime 返回结果时短路，不进入 planning preview / confirmation gate。
- 非 chat mode 完全保持现有路径。

### Router Wiring

修改 `apps/api/app/routers/conversation.py`：

- 构造 learning handler 并注入 orchestrator。
- replay handler 继续使用 `run_explicit_replay`。
- chat runtime 使用同一 DB session 查询 LearnedPath。

## 数据流

学习：

```text
wagent chat
-> create interactive_chat session
-> user learn input
-> dispatch
-> chat runtime learn_page
-> LearningRunService.run_and_persist(...)
-> exploration_runs + learned_paths
-> session.metadata.learned_actions upsert
-> agent messages + events
-> user_response
```

执行：

```text
user: 帮我登录
-> dispatch
-> chat runtime execute_task
-> current session learned_actions alias match
-> replay handler
-> agent messages + events
-> user_response
```

## 失败 / 边界情况

- URL 不是 `/entry`：返回当前只支持登录页学习。
- autonomous run pass gate 未通过：不返回学习完成。
- run persisted 但未产生 LearnedPath：返回学习失败或内部错误。
- 当前 session 没有 learned_actions：返回需要先学习。
- replay drift / failure：返回简洁失败文案，不做恢复。
- 非 interactive_chat session：不进入 chat runtime。

## Test Matrix

- intent parser：learn keywords + URL；普通任务；未知空输入。
- learning service：返回 run_id + learned_path_id；未沉淀 path 时失败。
- metadata merge：同 alias 覆盖并保留其他 metadata。
- chat runtime：learn_page、execute_task、no-path fallback、非 chat mode regression。
- CLI：top-level `wagent chat` registration、session create payload、timeout、REPL exit。
- regression：`wagent conversation send` 和 confirmation gate 不变。

## 验证命令入口

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_api.py tests/test_conversation_orchestrator.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py tests/test_conversation.py -q
cd apps/api && ../../.venv/bin/ruff check app/services/conversation app/services/learning app/routers/conversation.py tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py
cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/chat.py tests/test_chat.py tests/test_conversation.py
git diff --check
```
