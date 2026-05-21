# 测试计划（Test Plan）

状态：ready_for_implementation（design review passed，未开始实现）

## 测试边界

本包验证 ExecutionEvidence 和 TaskResultReporter adapter，不验证完整 live closed loop。

允许：

- Python schema tests。
- replay service mocked Playwright page tests。
- conversation replay hook propagation tests。
- chat runtime mocked replay handler tests。
- TaskResultReporter outcome tests。
- API replay request compatibility tests。
- scoped ruff 和 `git diff --check`。

不允许把以下内容写成本包通过证据：

- product UI live run。
- `wagent chat` 真实浏览器闭环。
- `verify-scenario`。
- autonomous run。
- TaskPathPlanner 多候选。
- Failure Recovery 菜单。

完整 `/items` live closed-loop evidence 留给 11.3.5.6。

## Test Matrix

| 编号 | 范围 | 测试 | 期望 |
|---|---|---|---|
| EVS-1 | Schema | `ReplayRequest` 默认 `evidence_targets=[]` | 旧请求兼容 |
| EVS-2 | Schema | `ReplayRequest` 接收 `dom_text_present` target | target 字段完整 |
| EVS-3 | Schema | `ExecutionEvidence` 校验 confidence 范围 | 超出 0-1 被拒 |
| CAP-1 | Capture | selector 区域包含 target text | `status=verified`, `target=ExecutionEvidenceTarget.text` |
| CAP-2 | Capture | selector 区域不包含 target text | `status=missing` |
| CAP-3 | Capture | page unavailable / selector exception | `kind=unknown`, `status=unknown` |
| REP-1 | Replay | `run_replay()` 把 evidence target 传给 capture | `ReplayResult.execution_evidence` 有结果 |
| REP-2 | Replay | capture 在 runtime stop 前执行 | mocked runtime stop 在 capture 后 |
| HOOK-1 | Replay hook | `run_explicit_replay()` 传递 `evidence_targets` | `run_replay(... evidence_targets=...)` |
| HOOK-2 | Replay hook | `ConversationReplaySummary` 带出 evidence | summary evidence 与 result 一致 |
| RTR-1 | Reporter | replay succeeded + verified evidence | outcome `verified` |
| RTR-2 | Reporter | replay succeeded + no evidence | outcome `uncertain` |
| RTR-3 | Reporter | replay succeeded + missing target | outcome `needs_review` 或不为 `verified` |
| RTR-4 | Reporter | replay failed | outcome `failed` |
| RTR-5 | Reporter | drift != none | outcome `failed` / `blocked`，不 verified |
| CHAT-1 | Runtime | execute `/items` with `slot_overrides.item_name` | 构造 `[data-testid='item-list']` evidence target |
| CHAT-2 | Runtime | reporter returns verified | user_response 说明看到目标项目 |
| CHAT-3 | Runtime | no evidence | user_response 不说成功 |

## 推荐新增测试

### `tests/test_learned_path_replay.py`

- `test_replay_request_accepts_evidence_targets`
- `test_capture_execution_evidence_finds_text_inside_selector`
- `test_capture_execution_evidence_missing_text_inside_selector`
- `test_capture_execution_evidence_unknown_when_page_unavailable`
- `test_run_replay_captures_evidence_before_runtime_stop`

示例断言：

```python
def test_execution_evidence_target_text_maps_to_evidence_target() -> None:
    target = ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="测试项目B-001",
        source_slot="item_name",
        selector="[data-testid='item-list']",
    )

    evidence = _capture_dom_text_present(page_with_item_list, target)

    assert evidence.kind == "dom_text_present"
    assert evidence.target == "测试项目B-001"
    assert evidence.status == "verified"
```

### `tests/test_conversation_replay_hook.py`

- `test_run_explicit_replay_passes_evidence_targets`
- `test_run_explicit_replay_summary_contains_execution_evidence`

示例断言：

```python
assert mock_run_replay.call_args.kwargs["evidence_targets"] == [
    ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="测试项目B-001",
        source_slot="item_name",
        selector="[data-testid='item-list']",
    )
]
```

### `tests/test_task_planning_result_reporter.py`

- `test_verified_when_structured_dom_text_evidence_matches_item_name`
- `test_uncertain_when_replay_succeeded_without_postcondition_evidence`
- `test_not_verified_when_dom_text_evidence_missing`

示例断言：

```python
report = reporter.build_report(
    execution_status="completed",
    execution_payload={
        "slot_overrides": {"item_name": "测试项目B-001"},
        "execution_evidence": [
            {
                "kind": "dom_text_present",
                "target": "测试项目B-001",
                "status": "verified",
                "confidence": 0.95,
                "summary": "列表中出现了名称为“测试项目B-001”的项目行。",
            }
        ],
    },
    replay_summary=ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://localhost:5176/items",
        replay_status="succeeded",
        drift_status="none",
    ),
    confirmed_plan_context={
        "learned_path_id": "lp-001",
        "slot_overrides": {"item_name": "测试项目B-001"},
        "postcondition_evidence": [
            {
                "kind": "dom_text_present",
                "target": "测试项目B-001",
                "status": "verified",
                "confidence": 0.95,
                "summary": "列表中出现了名称为“测试项目B-001”的项目行。",
            }
        ],
    },
)

assert report.outcome == "verified"
assert report.needs_review is False
assert report.event_payload["task_verified"] is True
```

### `tests/test_conversation_chat_runtime.py`

- `test_interactive_chat_execute_builds_items_evidence_target`
- `test_interactive_chat_execute_uses_reporter_verified_response`
- `test_interactive_chat_execute_does_not_claim_success_without_evidence`

示例断言：

```python
assert replay_call.kwargs["evidence_targets"][0].selector == "[data-testid='item-list']"
assert replay_call.kwargs["evidence_targets"][0].text == "测试项目B-001"
assert "看到了“测试项目B-001”" in result.user_response
```

## 验证命令

实现阶段至少运行：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_learned_path_replay.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_conversation_chat_runtime.py
```

Replay API 边界：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py -k replay
```

Scoped ruff：

```bash
uv run ruff check \
  apps/api/app/schemas/learned_path_replay.py \
  apps/api/app/schemas/conversation.py \
  apps/api/app/services/learning/learned_path_replay.py \
  apps/api/app/services/conversation/replay_hook.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/task_planning/result_reporter.py \
  apps/api/tests/test_learned_path_replay.py \
  apps/api/tests/test_conversation_replay_hook.py \
  apps/api/tests/test_task_planning_result_reporter.py \
  apps/api/tests/test_conversation_chat_runtime.py
```

Diff hygiene：

```bash
git diff --check
```

## 不运行项

本包不运行：

- `verify-scenario`
- autonomous exploration
- live product UI smoke
- full `/items` learn A / execute B closed loop

如果实现者临时做了本地浏览器 smoke，只能记录为辅助观察，不能替代本包 targeted tests，
也不能写成 11.3.5.6 闭环证据。
