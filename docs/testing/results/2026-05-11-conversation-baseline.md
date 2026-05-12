# Conversation Baseline — Keep-running 证据

日期：2026-05-11
运行时 base commit：`0c009f0774ef042265e378841851b1ff9d814c80`
分支：`v0.1-local`
工作区：包含未提交的 11.0.7 测试 / 证据改动。

## 范围

复跑 M11.0.1–11.0.6 conversation baseline：

- domain parser / state transition
- session / message / event repository
- Conversation API
- Orchestrator / Dispatcher
- Explicit replay command hook
- `wagent conversation` CLI
- M10 replay service/API dependencies used by the hook

本报告不调用 autonomous run，不依赖 LLM provider。

## 命令

### API / Orchestrator / Replay Hook baseline

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_replay_hook.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_learned_path_replay.py tests/test_exploration_learned_paths_api.py -v
```

结果：**PASS / exit 0**

摘录：

```text
collected 179 items
179 passed in 1.31s
```

### CLI baseline

```bash
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -v
```

结果：**PASS / exit 0**

摘录：

```text
collected 15 items
15 passed in 0.07s
```

## 摘要

| 区域 | 状态 | 证据 |
| --- | --- | --- |
| CV-U domain parser/state | PASS | included in API pytest command |
| CV-R repo/store | PASS | included in API pytest command |
| CV-API Conversation API | PASS | included in API pytest command |
| CV-O Orchestrator / Dispatcher | PASS | included in API pytest command |
| CV-RH explicit replay hook | PASS | included in API pytest command |
| CV-CLI `wagent conversation` | PASS | CLI pytest command |
| Autonomous endpoints called | NO | static tests and API/CLI tests do not call live autonomous run |
| LLM provider used | NO | deterministic tests |

## 备注

- This is keep-running evidence, not a new product feature.
- It confirms 11.0.6 remains covered before adding conversation runtime E2E.
