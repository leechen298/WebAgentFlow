# Review

状态：accepted（implementation review passed, manual smoke passed）

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
  当前只有 `wagent chat` learning path 使用该 service；exploration router /
  Workbench 复用该 service 是后续 refactor，不作为 M11.3 验收条件。
- 学习成功后将当前 session `metadata.learned_actions` 按 alias 去重覆盖写入；
  `chat_learning_completed` event 保留 old/new learned_path id。
- “帮我登录”只匹配当前 session `learned_actions`，单一命中后直接 replay，
  不进入 `awaiting_confirmation`，并追加用户可见 agent transcript。
- `DispatchResult.previous_status` 返回进入 interactive chat runtime 前的真实
  session status，避免审计结果固定显示为 `task_intake`。
- 找不到当前 session learned action 时只返回
  `还没学过这个操作，需要先学习。`。

## 验证证据

- `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py -q`
  - `9 passed in 0.07s`
- `PYTHONPATH=apps/cli .venv/bin/python -m pytest apps/cli/tests/test_chat.py -q`
  - `4 passed in 0.03s`
- `PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_api.py apps/api/tests/test_conversation_orchestrator.py -q`
  - `104 passed in 0.64s`
- `PYTHONPATH=apps/cli .venv/bin/python -m pytest apps/cli/tests/test_chat.py apps/cli/tests/test_conversation.py -q`
  - `19 passed in 0.07s`
- `PYTHONPATH=apps/api .venv/bin/python -m ruff check apps/api/app/services/conversation apps/api/app/services/learning apps/api/app/routers/conversation.py apps/api/app/schemas/conversation.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_run_service.py`
  - `All checks passed!`
- `PYTHONPATH=apps/cli .venv/bin/python -m ruff check apps/cli/wagent/main.py apps/cli/wagent/chat.py apps/cli/tests/test_chat.py apps/cli/tests/test_conversation.py`
  - `All checks passed!`
- `git diff --check`
  - no output
- 真实 `wagent chat` smoke：
  - 先启动 validation-site：`pnpm run dev:validation`
  - 先启动当前工作区 API 临时端口：`.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8002`
  - 由于本机 `8001` 当时是旧 API 进程，本次 smoke 使用：
    `printf '学习一下这个登录页怎么登录，地址是 http://localhost:5175/login\n帮我登录\n帮我导出报表\nexit\n' | .venv/bin/wagent chat --api-base http://127.0.0.1:8002 --timeout 240`
  - 输出：
    ```text
    WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。
    You > WAgent > 开始学习页面操作。
    WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
    You > WAgent > 执行中。
    WAgent > 登录完成。
    You > WAgent > 还没学过这个操作，需要先学习。
    You >
    ```
  - persisted run evidence:
    - `run_id=91f595d0-3778-4011-80a0-968cbddd3d86`
    - `status=completed`
    - `pass_gate=pass`
    - scorecard 5/5：`element_recognition=1.0`、`action_coverage=1.0`、
      `verdict_accuracy=1.0`、`distraction_avoidance=1.0`、
      `supervisor_agreement=1.0`
    - Supervisor verdict：`success`
    - Supervisor summary：`在登录页使用有效凭据（admin/123456）填写用户名和密码后，点击 Sign in 按钮提交。认证成功，页面导航至 /dashboard，显示欢迎信息和登录成功提示，无任何错误提示。`

## 未运行项 / 风险

- 第一版只支持 `/login` happy path，且 execution matching 仅使用当前 session
  `learned_actions`；global LearnedPath fallback、复杂意图理解和 M12 recovery
  均未实现。
- 本次人工 smoke 为了避开旧的 8001 API 进程，使用 `--api-base http://127.0.0.1:8002`。
  常规本地验收前应重启默认 8001 API 到当前代码。
