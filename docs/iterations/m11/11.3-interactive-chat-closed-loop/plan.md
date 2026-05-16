# 实施计划

状态：implemented

## 施工顺序

### 1. 文档包与索引

- 创建本目录完整文档包。
- 更新 `docs/iterations/m11/README.md`，加入 11.3 索引。
- 更新 `docs/iterations/m11/m11-plan.md`，加入 11.3 计划，并把 Page Context Bridge
  改为 later M11.x candidate。

验证：

```bash
git diff --check
```

### 2. API / service TDD

先写失败测试：

- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`

覆盖：

- learn intent parse。
- interactive_chat gating。
- learning success requires queryable `learned_path_id`。
- metadata learned_actions alias overwrite。
- current-session-only execution match。
- no-path fallback。
- non-chat mode regression。

### 3. CLI TDD

先写失败测试：

- `apps/cli/tests/test_chat.py`
- 更新 `apps/cli/tests/test_conversation.py` regression 如有必要。

覆盖：

- top-level `wagent chat`。
- session create payload。
- default timeout / `--timeout`。
- REPL multi-turn dispatch。
- exit commands。

### 4. API implementation

实现：

- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/orchestrator.py`
- `apps/api/app/routers/conversation.py`

保持：

- 非 `interactive_chat` session 不变。
- confirmation gate 不删除、不重写。
- global LearnedPath fallback 不实现。

### 5. CLI implementation

实现：

- `apps/cli/wagent/chat.py`
- `apps/cli/wagent/main.py`

保持：

- `wagent conversation ...` 不变。
- `wagent verify` 不变。

### 6. 验证与收尾

运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_api.py tests/test_conversation_orchestrator.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py tests/test_conversation.py -q
cd apps/api && ../../.venv/bin/ruff check app/services/conversation app/services/learning app/routers/conversation.py tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py
cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/chat.py tests/test_chat.py tests/test_conversation.py
git diff --check
```

如果执行人工 smoke，必须记录真实命令输出和运行结果；否则在 `review.md` 标记
manual smoke not run。
