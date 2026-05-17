# 实施计划（Implementation Plan）

状态：implementation_complete（scoped tests passed, manual visible-browser smoke pending）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`

## 文件 / 模块

- `apps/cli/wagent/chat.py` - 新增 `--headless`，写入 `browser_visibility` metadata，调整用户文案。
- `apps/cli/tests/test_chat.py` - 覆盖默认 visible、headless opt-out 和普通用户文案。
- `apps/api/app/services/conversation/chat_runtime.py` - 从 session metadata 推导 headless，并传给 learning / replay handler。
- `apps/api/app/routers/conversation.py` - handler wrapper 接收并传递 headless option。
- `apps/api/app/services/conversation/replay_hook.py` - replay hook 支持 headless override，默认保持 headless。
- `apps/api/app/services/learning/learned_path_replay.py` - `run_replay` 支持 headless override。
- `apps/api/tests/test_conversation_chat_runtime.py` - 覆盖 interactive chat visible/headless 参数传递。
- `apps/api/tests/test_conversation_replay_hook.py` - 覆盖 replay hook 兼容性。
- `apps/api/tests/test_learned_path_replay.py` - 覆盖 runtime config headless override。
- `docs/user-guide/wagent-chat.md` - 更新普通用户说明：默认会打开浏览器，`--headless` 后台运行。
- `docs/iterations/m11/README.md` / `m11-plan.md` - 更新 11.3.1 状态。

## 步骤

1. CLI 层加 `--headless` 和 metadata。
   - 默认 create session 写 `browser_visibility=visible`。
   - `--headless` 写 `browser_visibility=headless`。
   - dispatch metadata 同步写审计字段。

2. API chat runtime 解析 session-level browser visibility。
   - 新增 helper，缺失或非法值默认 visible。
   - learning / execute 分支都传入 `headless`。
   - event payload 可记录 browser visibility。

3. learning / replay handler wiring。
   - conversation router wrapper 接收 keyword-only `headless`。
   - learning request 使用传入的 headless。
   - replay hook 和 `run_replay` 支持 override，默认仍为 headless。

4. 测试补齐。
   - 先补 CLI payload tests。
   - 再补 chat runtime handler kwargs tests。
   - 最后补 replay hook / run_replay compatibility tests。

5. 更新普通用户文档。
   - 主入口使用 `.venv/bin/wagent chat`，不依赖 shell activation。
   - 加入 `test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'` 检查。
   - 区分 `zsh: command not found: wagent` 和旧 CLI 缺少 `chat` 子命令。
   - 说明 `wagent chat` 默认会打开浏览器。
   - 说明 `wagent chat --headless` 是后台运行。
   - 不把具体页面写成功能边界；页面只作为测试示例。

6. 运行 scoped verification。
   - API / CLI targeted pytest。
   - API / CLI ruff。
   - `git diff --check`。
   - 人工 smoke 留到实现后按 `test-plan.md` 执行。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。
如果本轮触发 `test-plan.md` 条件，不能只在这里写零散命令。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| CLI entry precheck below | 项目内 CLI 已安装且包含 `chat` | Yes | smoke 前置检查，不触发浏览器 |
| `cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py tests/test_conversation.py -q` | CLI default visible / headless opt-out / regression | Yes | 不启动真实浏览器 |
| `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_learned_path_replay.py -q` | chat runtime 和 replay headless 参数传递 | Yes | 通过 mock / unit 验证 |
| `cd apps/api && ../../.venv/bin/ruff check app/services/conversation app/services/learning tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_learned_path_replay.py` | API lint clean | Yes | scoped |
| `cd apps/cli && ../../.venv/bin/ruff check wagent/chat.py tests/test_chat.py` | CLI lint clean | Yes | scoped |
| `git diff --check` | whitespace clean | Yes | 文档和代码都检查 |
| `wagent chat` manual smoke | 用户真实看到浏览器打开并操作验收页面 | No | 实现后执行，记录 evidence |
| `wagent chat --headless` optional smoke | opt-out 不显示浏览器且功能仍可用 | No | 可作为补充 |

CLI entry precheck:

```bash
test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'
.venv/bin/wagent --help
```

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] 用户指南不再把 `command not found` 只归因于未 source。
- [ ] smoke 主入口使用 `.venv/bin/wagent chat`。
- [ ] 默认 visible 只作用于 `interactive_chat`。
- [ ] `--headless` opt-out 可用。
- [ ] 非 chat mode confirmation gate 不变。
- [ ] replay 默认 headless 兼容。
- [ ] 用户文案不暴露开发者内部字段。
- [ ] 验证命令已执行并记录到 `review.md`，或写明 not run / unverified 和原因。
