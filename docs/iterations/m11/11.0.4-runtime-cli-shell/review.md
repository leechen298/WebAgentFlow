# 审核与反思

## 规划初始化

- 本目录用于 11.0.4 Runtime CLI Shell。
- 当前状态：已实现并通过验证。
- 前置 11.0.1 Conversation Domain Contract 已完成。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 前置 11.0.3 Conversation API 已实现并通过验证。
- 本包已实现 `wagent conversation` CLI-first runtime conversation 入口。

## 实现证据

### 新增文件

- `apps/cli/wagent/conversation.py` — conversation CLI command module。
- `apps/cli/tests/test_conversation.py` — 15 个 CLI 测试全部通过。

### 修改文件

- `apps/cli/wagent/main.py` — 注册 `conversation` subcommand。

### 命令列表

```text
wagent conversation start
wagent conversation status <session_id>
wagent conversation send <session_id> --content "..."
wagent conversation messages <session_id> [--limit N]
wagent conversation transcript <session_id>
wagent conversation events <session_id> [--limit N]
```

### API 调用映射

| CLI 命令 | HTTP 方法 | Endpoint |
|---|---|---|
| `start` | POST | `/conversation/sessions` |
| `status <id>` | GET | `/conversation/sessions/{id}` |
| `send <id> --content` | POST | `/conversation/sessions/{id}/messages` |
| `messages <id>` | GET | `/conversation/sessions/{id}/messages?limit=N` |
| `transcript <id>` | GET | `/conversation/sessions/{id}/transcript` |
| `events <id>` | GET | `/conversation/sessions/{id}/events?limit=N` |

### 关键策略决策

| 问题 | 决策 |
|---|---|
| CLI 是否直接操作 DB | **否** — 通过 `httpx` 调用 11.0.3 Conversation API，不 import `ConversationRepository` 或 ORM 模型。 |
| `send` role 策略 | **固定 `user`** — 不暴露 `--role` 参数，metadata 固定 `{}`。 |
| 输出格式 | **默认 JSON stdout**，支持 `--pretty` 格式化。错误到 stderr。 |
| API base | **复用 `WBAF_API_BASE`** / `--api-base`，默认 `http://localhost:8001`。 |
| Timeout | **默认 `30s`** — 短 timeout，不复用 verify 的 300s。 |
| Exit code | **0 = 成功 / 2 = CLI/网络/API 错误**。 |

### 测试覆盖

15 个 CLI 测试全部通过：

- `start` calls POST `/conversation/sessions` and prints JSON
- `start --pretty` outputs indented JSON
- `status` calls GET session
- `send` calls POST messages with `role=user`
- `messages` calls GET messages with default limit=100
- `messages --limit 5` passes custom limit
- `transcript` calls GET transcript
- `events` calls GET events with default limit=100
- `events --limit 10` passes custom limit
- API 404 returns exit code 2
- API business error returns exit code 2
- Network error returns exit code 2
- Module does not import replay / autonomous / LLM
- Module does not import DB repo / model
- Existing `wagent verify` behavior unaffected

### 验证命令

```bash
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v
# 67 passed
cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/conversation.py tests/test_conversation.py
# All checks passed!
git diff --check
# clean
```

## 边界遵守

本轮未触及：

- orchestrator dispatcher
- replay API / `/replay` command side effect
- Agent D/E/F/G/H
- task-to-path planning
- slot binding
- recovery / abort dialogue
- teaching mode
- artifact lifecycle
- risk gate
- multi-page workflow
- autonomous run
- LLM provider
- M16 external CLI stabilization
- E2E
- user / account / tenant 字段
- 11.0.5 或 M11.1 详情目录

## Follow-up

- 11.0.5 Orchestrator Dispatcher 负责 session status mutation 和 replay side effect。
- 未来可考虑扩展 `send` 支持 `--role system/engine`（内部/debug 场景）。
- interactive REPL 作为 future follow-up，不属 11.0.4 范围。
