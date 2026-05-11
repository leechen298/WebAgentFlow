# Conversation 测试域

本文件记录 M11 Runtime Conversation 的长期测试矩阵。它不是 WebAgentFlow
全项目测试计划，也不是执行报告。

## 当前能力状态

Conversation 已不再是 pure-function only。当前已完成：

- 11.0.1 Conversation Domain Contract：parser、state transition、schema。
- 11.0.2 Conversation Session Store：DB-backed session / message / event store。
- 11.0.3 Conversation API：session、messages、events、transcript HTTP API。
- 11.0.4 Runtime CLI Shell：`wagent conversation` 非交互 CLI。

当前下一步：

- 11.0.5 Orchestrator Dispatcher。

## 覆盖范围

Conversation 测试域覆盖：

- domain parser / state transition。
- session / message / event repository。
- Conversation API。
- `wagent conversation` CLI。
- 后续 11.0.5 Orchestrator Dispatcher。
- 后续 conversation smoke / E2E。

Conversation 测试域不覆盖：

- Agent D/E/F/G/H 具体实现。
- task-to-path planning。
- slot binding。
- replay side effect；显式 replay hook 属于 11.0.6 之后。
- LLM provider。
- autonomous run。
- teaching mode、artifact lifecycle、risk gate、multi-page workflow。

## 用例分组

| Group | 范围 | 当前状态 | 证据类型 |
| --- | --- | --- | --- |
| CV-U | command parser、state transition、schema invariant | existing | Unit |
| CV-R | conversation session / message / event store | existing | Repo integration |
| CV-API | Conversation HTTP API | existing | API integration |
| CV-CLI | `wagent conversation` CLI | existing | CLI tests |
| CV-O | Orchestrator Dispatcher | gap | Unit / integration after 11.0.5 |
| CV-E2E | conversation runtime smoke | proposed / deferred | Deterministic E2E after 11.0.5+ |

## 已有覆盖摘要

- CV-U：`apps/api/tests/test_conversation_commands.py`、
  `apps/api/tests/test_conversation_state.py`。
- CV-R：`apps/api/tests/test_conversation_repo.py`。
- CV-API：`apps/api/tests/test_conversation_api.py`。
- CV-CLI：`apps/cli/tests/test_conversation.py`。

这些测试不依赖 LLM provider，不调用 autonomous run。

## 当前第一批重点

真正新增的第一优先级是 11.0.5 Orchestrator Dispatcher 测试。API / CLI 已有基线，
当前应 keep-running；只有发现 contract 缺口时才新增 case。

| Case ID | 目标 | Status | Layer | Priority | CI | Evidence required |
| --- | --- | --- | --- | --- | --- | --- |
| CV-O-P0-01 | Orchestrator Dispatcher command routing matrix | gap / new with 11.0.5 | Unit | P0 | yes | pytest output |
| CV-O-P0-02 | Orchestrator Dispatcher state transition + response contract | gap / new with 11.0.5 | Unit | P0 | yes | pytest output |
| CV-API-SMOKE-01 | session create / read / messages / transcript smoke | existing baseline / keep-running | API integration | P0 | yes | pytest output |
| CV-CLI-SMOKE-01 | `wagent conversation start/send/status/transcript` smoke | existing baseline / keep-running | CLI tests | P0 | yes | CLI test output |

## 后续可补

- CV-E2E conversation smoke：等 11.0.5 dispatcher 明确 API/CLI flow 后再定。
- CLI human-readable output 或 interactive REPL：只有在产品需求进入对应包后再补。
- `/replay <learned_path_id> <url>`：属于 11.0.6 explicit replay command hook，不在
  11.0.5 前提前补。

## 证据规则

- Unit / repo / API / CLI case 必须有命令和退出码证据。
- Deterministic E2E 必须不依赖 LLM，不调用 autonomous run。
- Live autonomous / verify-scenario 只能作为 manual live smoke，不进入常规 CI。
- 没有实际执行证据的 case 只能写 proposed、gap、deferred 或 NOT_RUN，不能写 PASS。
