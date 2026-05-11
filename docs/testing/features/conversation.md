# Conversation 测试域

本文件记录 M11 Runtime Conversation 的长期测试矩阵。它不是 WebAgentFlow
全项目测试计划，也不是执行报告。

## 当前能力状态

Conversation 已不再是 pure-function only。当前已完成：

- 11.0.1 Conversation Domain Contract：parser、state transition、schema。
- 11.0.2 Conversation Session Store：DB-backed session / message / event store。
- 11.0.3 Conversation API：session、messages、events、transcript HTTP API。
- 11.0.4 Runtime CLI Shell：`wagent conversation` 非交互 CLI。
- 11.0.5 Orchestrator Dispatcher：service-only orchestrator / dispatcher baseline。
- 11.0.6 Explicit Replay Command Hook：显式 `/replay <learned_path_id> <url>`
  接入 M10 replay。
- 11.0.7 Conversation Tests and Evidence：conversation runtime E2E smoke。

下一开发阶段：

- M11.1 Task-to-Path 仍是 future，进入前需要保持 M11.0 baseline 和 E2E 证据。

## 覆盖范围

Conversation 测试域覆盖：

- domain parser / state transition。
- session / message / event repository。
- Conversation API。
- `wagent conversation` CLI。
- 11.0.5 service-only Orchestrator Dispatcher。
- 11.0.6 explicit replay command hook。
- conversation runtime smoke / E2E。

Conversation 测试域不覆盖：

- Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H） 具体实现。
- task-to-path planning。
- slot binding。
- path selection。
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
| CV-O | service-only Orchestrator Dispatcher | existing / keep-running | Unit / integration |
| CV-RH | explicit replay command hook | existing / keep-running | API / integration |
| CV-E2E | conversation runtime smoke | existing / keep-running | Deterministic E2E |

## 已有覆盖摘要

- CV-U：`apps/api/tests/test_conversation_commands.py`、
  `apps/api/tests/test_conversation_state.py`。
- CV-R：`apps/api/tests/test_conversation_repo.py`。
- CV-API：`apps/api/tests/test_conversation_api.py`。
- CV-CLI：`apps/cli/tests/test_conversation.py`。
- CV-O：`apps/api/tests/test_conversation_orchestrator.py`。
- CV-RH：`apps/api/tests/test_conversation_replay_hook.py`。
- CV-E2E：`apps/e2e/tests/conversation/runtime.spec.ts`。
- CV-CLI-E2E：`apps/e2e/tests/conversation/cli-runtime.spec.ts`。

这些测试不依赖 LLM provider，不调用 autonomous run。

## 当前第一批重点

11.0.7 已补 conversation runtime E2E。当前 conversation 域重点是 keep-running；
只有发现 contract 缺口时才新增 case。M11.1 开始前不提前写 task-to-path 测试。

| Case ID | 目标 | Status | Layer | Priority | CI | Evidence required |
| --- | --- | --- | --- | --- | --- | --- |
| CV-O-P0-01 | Orchestrator Dispatcher command routing matrix | existing baseline / keep-running | Unit | P0 | yes | pytest output |
| CV-O-P0-02 | Orchestrator Dispatcher state transition + response contract | existing baseline / keep-running | Unit | P0 | yes | pytest output |
| CV-RH-P0-01 | explicit `/replay` command hook | existing baseline / keep-running | API / integration | P0 | yes | pytest output |
| CV-E2E-P0-01 | session -> dispatch `/replay` -> transcript/events | existing baseline / keep-running | Deterministic E2E | P0 | yes | Playwright output |
| CV-CLI-E2E-P0-01 | `wagent conversation` -> `/replay` -> transcript/events | existing baseline / keep-running | Deterministic E2E | P0 | yes | Playwright output |
| CV-API-SMOKE-01 | session create / read / messages / transcript smoke | existing baseline / keep-running | API integration | P0 | yes | pytest output |
| CV-CLI-SMOKE-01 | `wagent conversation start/send/status/transcript` smoke | existing baseline / keep-running | CLI tests | P0 | yes | CLI test output |

## 后续可补

- headed visual exploratory：只有需要观察 console 呈现时再做，不能冒充 headless E2E。
- CLI human-readable output 或 interactive REPL：只有在产品需求进入对应包后再补。
- M11.1 task-to-path tests：等 M11.1 intent / plan 创建后再展开。

## 证据规则

- Unit / repo / API / CLI case 必须有命令和退出码证据。
- Deterministic E2E 必须不依赖 LLM，不调用 autonomous run。
- Live autonomous / verify-scenario 只能作为 manual live smoke，不进入常规 CI。
- 没有实际执行证据的 case 只能写 proposed、gap、deferred 或 NOT_RUN，不能写 PASS。
