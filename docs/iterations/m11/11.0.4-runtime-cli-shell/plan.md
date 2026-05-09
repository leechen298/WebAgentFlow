# 实施计划

## 当前 CLI 结构核对

实现前必须先检查 `apps/cli/` 当前结构，不要凭空假设文件布局。本文只写
planned files；真正实现时必须遵循现有 CLI stack。

当前已知方向：

- `apps/cli` 是 Python `wagent` CLI workspace。
- 当前入口是 `apps/cli/wagent/main.py`。
- 当前已有子命令包括 `verify` 和 `skill`。
- 如实现时发现结构已经变化，以代码为准，并先更新本 plan。

## 触及的文件 / 模块

这是后续实现计划，不是本轮文档修正要改的代码。

- `apps/cli/` —— existing CLI workspace。
- `apps/cli/wagent/main.py` —— planned registration point for `conversation`
  subcommands, if current dispatcher structure is unchanged。
- `apps/cli/wagent/conversation.py` —— planned conversation command module。
- `apps/cli/tests/test_conversation.py` —— planned CLI tests, following existing
  CLI test style。
- `docs/iterations/m11/11.0.4-runtime-cli-shell/review.md` —— implementation
  evidence after code work。

实现阶段必须先 inspect `apps/cli/`；如果实际路径或测试结构和以上规划不一致，
按现有结构落地，并在 `review.md` 记录差异。

## CLI 主命名

主命名使用：

```text
wagent conversation
```

首版不使用 `wagent chat` 作为主命名。`conversation` 更贴合 M11.0 runtime
conversation surface，也避免和未来 full chat / natural-language loop 混淆。

## 第一版命令形态

11.0.4 首版只规划 non-interactive commands，不实现 interactive REPL。

```text
wagent conversation start
wagent conversation status <session_id>
wagent conversation send <session_id> --content "..."
wagent conversation messages <session_id> [--limit N]
wagent conversation transcript <session_id>
wagent conversation events <session_id> [--limit N]
```

要求：

- `send` 首版只追加 `user` message。
- 不暴露 `--role agent`。
- 不暴露 `--role system` / `--role engine` 给普通 CLI 用户。
- 不实现 `/replay`。
- 不实现 task planning。
- 不实现 interactive REPL。

## 输出策略

- 默认 stdout 输出 JSON，方便脚本和测试。
- 第一版推荐实现通用 `--pretty`，用于格式化 JSON 输出。
- stderr 只输出错误或简短人类提示。
- 错误输出必须包含 HTTP status 和 API error msg。
- 不输出内部 Agent 作为用户直接沟通对象。

## API dependency

CLI 必须调用 11.0.3 API：

```text
POST /conversation/sessions
GET /conversation/sessions/{session_id}
POST /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/transcript
GET /conversation/sessions/{session_id}/events
```

命令到 API 的映射：

```text
wagent conversation start
  -> POST /conversation/sessions

wagent conversation status <session_id>
  -> GET /conversation/sessions/{session_id}

wagent conversation send <session_id> --content "..."
  -> POST /conversation/sessions/{session_id}/messages
     body: { "role": "user", "content": "...", "metadata": {} }

wagent conversation messages <session_id> [--limit N]
  -> GET /conversation/sessions/{session_id}/messages?limit=N

wagent conversation transcript <session_id>
  -> GET /conversation/sessions/{session_id}/transcript

wagent conversation events <session_id> [--limit N]
  -> GET /conversation/sessions/{session_id}/events?limit=N
```

禁止：

- CLI 不直接操作 DB。
- CLI 不 import `ConversationRepository`。
- CLI 不调用 replay API。
- CLI 不调用 `/exploration/autonomous-runs` 或 stream。
- CLI 不依赖 LLM provider。

## API base URL 配置

实现前必须检查现有 CLI 配置，不要重复造轮子。

决策：

- 优先复用现有 `wagent verify` 的 API base URL 配置方式。
- 当前 `wagent verify` 使用 `WBAF_API_BASE`，默认
  `http://localhost:8001`，并支持 `--api-base`。
- 11.0.4 第一版应保持一致：使用 `WBAF_API_BASE`、默认
  `http://localhost:8001`、支持 `--api-base`。
- 不新增另一套 `WAGENT_API_BASE_URL`，避免同一 CLI 出现两个 API base 配置名。

## Timeout 策略

决策：

- conversation CLI 使用短请求 timeout。
- 推荐默认 `30s`。
- 不复用 live autonomous / verify-scenario 的长 timeout。
- 原因：conversation API 是普通 HTTP CRUD，不是长时间 browser / LLM run。

## Metadata 策略

决策：

- `send` 首版不支持 `--metadata`。
- metadata 默认 `{}`。
- 后续如果需要再扩展。
- 原因：降低 CLI 首版复杂度，避免 JSON parsing / escaping 干扰主链路。

## Limit 策略

决策：

- `messages` 和 `events` 第一版支持 `--limit N`。
- 默认 `100`。
- 不支持 cursor。
- `transcript` 第一版不支持 `--limit`，直接调用 transcript endpoint。

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

## 测试计划

后续实现时至少覆盖：

- `wagent conversation start` calls API and prints session id。
- `start` 输出 JSON 可解析。
- `wagent conversation status <session_id>` calls GET session。
- `wagent conversation send <session_id> --content "..."` appends user message。
- `wagent conversation messages <session_id>` lists messages。
- `wagent conversation messages <session_id> --limit 1` passes limit。
- `wagent conversation transcript <session_id>` lists transcript。
- `wagent conversation events <session_id>` lists events。
- `wagent conversation events <session_id> --limit 1` passes limit。
- API error is surfaced with status/message and exits `2`。
- Network error exits `2` and includes API base URL。
- `--pretty` outputs pretty JSON。
- CLI does not import DB repo / model。
- CLI does not import replay / autonomous / LLM modules。
- Existing `wagent verify` behavior remains unaffected。

## 验证

后续实现阶段运行：

```bash
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v
cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/conversation.py tests/test_conversation.py
git diff --check
```

当前文档阶段只运行：

```bash
git diff --check
```
