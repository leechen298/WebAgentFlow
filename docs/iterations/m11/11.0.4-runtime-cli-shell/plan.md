# 实施计划

## 触及的文件 / 模块

这是后续实现计划，不是本轮文档初始化要改的代码。实现必须遵循现有
`apps/cli` Python CLI stack。

- `apps/cli/wagent/main.py` —— 注册 future `conversation` 子命令。
- `apps/cli/wagent/conversation.py` —— planned HTTP client + argparse commands。
- `apps/cli/tests/test_conversation.py` —— planned CLI tests。
- `docs/iterations/m11/11.0.4-runtime-cli-shell/review.md` —— 实现完成后记录证据。

## CLI command shape

11.0.4 首版只规划非交互命令，不实现 interactive loop / REPL。

推荐命令：

```text
wagent conversation start
wagent conversation status <session_id>
wagent conversation send <session_id> --content "..."
wagent conversation messages <session_id>
wagent conversation transcript <session_id>
wagent conversation events <session_id>
```

`send` 命令首版只追加 `user` message。11.0.3 public API 支持 `system` /
`engine` role，但 runtime 用户入口不暴露这些 role；`agent` role 保留给未来
internal orchestrator / Agent integration。

## API interaction

CLI 只调用 11.0.3 Conversation API：

```text
POST /conversation/sessions
GET /conversation/sessions/{session_id}
POST /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/transcript
GET /conversation/sessions/{session_id}/events
```

映射关系：

```text
wagent conversation start
  -> POST /conversation/sessions

wagent conversation status <session_id>
  -> GET /conversation/sessions/{session_id}

wagent conversation send <session_id> --content "..."
  -> POST /conversation/sessions/{session_id}/messages
     body: { "role": "user", "content": "...", "metadata": {} }

wagent conversation messages <session_id>
  -> GET /conversation/sessions/{session_id}/messages

wagent conversation transcript <session_id>
  -> GET /conversation/sessions/{session_id}/transcript

wagent conversation events <session_id>
  -> GET /conversation/sessions/{session_id}/events
```

禁止：

- 不直接操作 DB。
- 不调用 replay API。
- 不调用 `/exploration/autonomous-runs` 或 stream。
- 不调用 LLM provider。
- 不做 task-to-path planning。
- 不实现 orchestrator dispatcher。

## Output and error policy

- 默认 stdout 输出一个 JSON object 或 JSON array，保持机器可读。
- `--pretty` 可以规划为格式化 JSON 输出。
- stderr 只输出错误或简短人类提示。
- API HTTP 404 / 422 / 5xx 映射为 CLI exit code `2`。
- 网络错误映射为 CLI exit code `2`，并提示 API base URL。
- 成功命令返回 exit code `0`。
- 本包不定义 task success / failure 语义，因为不执行 task。

## Configuration

- 复用 `WBAF_API_BASE`，默认 `http://localhost:8001`。
- 每个 conversation 命令支持 `--api-base` 覆盖。
- 默认 HTTP timeout 可沿用 `wagent verify` 的客户端风格，但不需要继承其
  autonomous run timeout；实现阶段可选择较短默认值并在 tests 中固定。

## Relationship to existing CLI surfaces

1. `wagent verify`
   - 当前 development verification skill backend。
   - 可以调用 autonomous run，但只能按 AGENTS.md 的 verify-scenario 契约使用。
   - 不属于 runtime conversation surface。

2. `wagent conversation`
   - 11.0.4 planned runtime conversation CLI。
   - 面向用户和 WebAgentFlow 的 session / message / transcript 入口。
   - 不调用 autonomous run，不调用 replay，不执行 browser action。

3. M16 external CLI / Skill / Tool
   - 未来稳定对外接口。
   - 不属于 11.0.4。

## Test plan

后续实现阶段至少覆盖：

- `wagent conversation start` POST `/conversation/sessions`，输出 session
  id / status。
- `wagent conversation send <id> --content ...` POST `/messages`，role 固定为
  `user`。
- `wagent conversation status <id>` GET session。
- `wagent conversation messages <id>` GET messages。
- `wagent conversation transcript <id>` GET transcript。
- `wagent conversation events <id>` GET events。
- API 404 / 422 / network error 映射为 exit code `2`。
- stdout 是可解析 JSON；`--pretty` 输出格式化 JSON。
- CLI 不调用 autonomous endpoint。
- CLI 不调用 replay API。
- CLI 不引用 LLM provider。
- `wagent verify` 现有行为不变。

## 验证

后续实现阶段运行：

```bash
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v
cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/conversation.py tests/test_conversation.py
git diff --check
```

当前文档初始化阶段只需要运行：

```bash
git diff --check
```
