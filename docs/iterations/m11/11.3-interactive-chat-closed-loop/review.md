# Review

状态：implementation complete

## 实际完成内容

- 创建 M11.3 完整文档包，并更新 M11 README / m11-plan 索引；原 Page Context
  Bridge 记录为 later M11.x candidate。
- 新增顶层 `wagent chat` REPL 入口，启动时自动创建
  `current_mode=interactive_chat` session，并写入 `metadata.client=wagent_chat`
  与 `metadata.runtime_policy=auto_execute_happy_path`。
- 新增 interactive chat runtime：只在 `session.current_mode == "interactive_chat"`
  且 FREE_TEXT 时启用 happy path；非 chat session 继续走原 preview /
  confirmation / execution 逻辑。
- 新增 M11.3 deterministic learn intent parse；第一版只支持
  `http://localhost:5175/login` 的 `/login` happy path。
- 新增 learning run service，直接运行现有 autonomous learning pipeline，持久化
  `ExplorationRun`，并显式返回 `run_id` 与真实可查询的 `learned_path_id`。
- 学习成功后将当前 session `metadata.learned_actions` 按 alias 去重覆盖写入；
  `chat_learning_completed` event 保留 old/new learned_path id。
- “帮我登录”只匹配当前 session `learned_actions`，单一命中后直接 replay，
  不进入 `awaiting_confirmation`，并追加用户可见 agent transcript。
- 找不到当前 session learned action 时只返回
  `还没学过这个操作，需要先学习。`。

## 验证证据

- `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py -q`
  - `9 passed in 0.07s`
- `PYTHONPATH=apps/cli .venv/bin/python -m pytest apps/cli/tests/test_chat.py -q`
  - `4 passed in 0.03s`
- `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_api.py apps/api/tests/test_conversation_orchestrator.py -q`
  - `104 passed in 0.55s`
- `PYTHONPATH=apps/cli .venv/bin/python -m pytest apps/cli/tests/test_chat.py apps/cli/tests/test_conversation.py -q`
  - `19 passed in 0.05s`
- `PYTHONPATH=apps/api .venv/bin/python -m ruff check apps/api/app/services/conversation apps/api/app/services/learning apps/api/app/routers/conversation.py apps/api/app/schemas/conversation.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py`
  - `All checks passed!`
- `PYTHONPATH=apps/cli .venv/bin/python -m ruff check apps/cli/wagent/main.py apps/cli/wagent/chat.py apps/cli/tests/test_chat.py apps/cli/tests/test_conversation.py`
  - `All checks passed!`
- `git diff --check`
  - no output

## 未运行项 / 风险

- 未运行人工 `wagent chat` live smoke，因为该流程会触发真实 autonomous
  exploration / replay；本轮按代码实现与 scoped regression 收口。
- 第一版只支持 `/login` happy path，且 execution matching 仅使用当前 session
  `learned_actions`；global LearnedPath fallback、复杂意图理解和 M12 recovery
  均未实现。
