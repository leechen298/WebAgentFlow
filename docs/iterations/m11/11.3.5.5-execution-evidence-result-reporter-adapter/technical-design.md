# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未开始实现）

## 设计目标

在 11.3.5.4 已经实现参数化 replay 的基础上，本包增加最小执行证据链：

```text
slot_overrides.record_name
-> evidence_targets.dom_text_present
-> replay 后、runtime stop 前检查 DOM
-> ReplayResult.execution_evidence
-> ConversationReplaySummary.execution_evidence
-> Reporter Adapter
-> TaskResultReporter verified path
```

本设计保持 code-owned Runtime / Orchestrator 边界。证据采集和 reporter adapter 都是
内部代码步骤，不是 Router 可推荐 skill。

## 文件责任

| 文件 | 责任 |
|---|---|
| `apps/api/app/schemas/learned_path_replay.py` | 定义 `ExecutionEvidenceTarget`、`ExecutionEvidence`，扩展 `ReplayRequest` / `ReplayResult` |
| `apps/api/app/schemas/conversation.py` | 扩展 `ConversationReplaySummary`，带出 execution evidence |
| `apps/api/app/services/learning/learned_path_replay.py` | 在 runtime stop 前采集 evidence，返回到 `ReplayResult` |
| `apps/api/app/services/conversation/replay_hook.py` | 把 `evidence_targets` 传入 `run_replay()`，并把 evidence 摘要映射到 `ConversationReplaySummary` |
| `apps/api/app/services/conversation/chat_runtime.py` | execute branch 根据 `slot_overrides.record_name` 构造 `/records` evidence target，调用 reporter adapter 生成保守回复 |
| `apps/api/app/services/task_planning/result_reporter.py` | 让 `_check_postconditions()` 读取 structured postcondition evidence |
| `apps/api/tests/test_learned_path_replay.py` | replay schema / evidence capture targeted tests |
| `apps/api/tests/test_conversation_replay_hook.py` | evidence targets propagation tests |
| `apps/api/tests/test_conversation_chat_runtime.py` | chat runtime evidence target + reporter response tests |
| `apps/api/tests/test_task_planning_result_reporter.py` | Reporter verified / uncertain / needs_review outcome tests |
| `apps/api/tests/test_exploration_learned_paths_api.py` | replay API request compatibility tests |

## Schema 设计

在 `learned_path_replay.py` 中新增：

```python
class ExecutionEvidenceTarget(BaseModel):
    kind: Literal["dom_text_present"]
    text: str
    source_slot: str | None = None
    selector: str | None = None


class ExecutionEvidence(BaseModel):
    kind: Literal["dom_text_present", "unknown"]
    target: str | None = None
    status: Literal["verified", "missing", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
```

扩展：

```python
class ReplayRequest(BaseModel):
    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)
    evidence_targets: list[ExecutionEvidenceTarget] = Field(default_factory=list)


class ReplayResult(BaseModel):
    ...
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

在 `conversation.py` 中扩展：

```python
class ConversationReplaySummary(BaseModel):
    ...
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

如果 import 产生循环，可使用：

```python
execution_evidence: list[dict[str, Any]] = Field(default_factory=list)
```

但 adapter 必须用 `ExecutionEvidence.model_validate()` 重新校验。

## Evidence Capture 设计

在 `learned_path_replay.py` 中新增内部 helper：

```python
def capture_execution_evidence(
    page: Page | None,
    evidence_targets: list[ExecutionEvidenceTarget],
) -> list[ExecutionEvidence]:
    ...
```

P0 只实现 `dom_text_present`：

```python
def _capture_dom_text_present(
    page: Page | None,
    target: ExecutionEvidenceTarget,
) -> ExecutionEvidence:
    if page is None or page.is_closed():
        return ExecutionEvidence(
            kind="unknown",
            target=target.text,
            status="unknown",
            confidence=0.0,
            summary="操作执行后未能采集页面证据。",
        )

    try:
        scope = page.locator(target.selector) if target.selector else page.locator("body")
        text = scope.inner_text(timeout=1000)
    except Exception:
        return ExecutionEvidence(
            kind="unknown",
            target=target.text,
            status="unknown",
            confidence=0.0,
            summary="操作执行后未能采集页面证据。",
        )

    if target.text in text:
        return ExecutionEvidence(
            kind="dom_text_present",
            target=target.text,
            status="verified",
            confidence=0.95,
            summary=f"列表中出现了名称为“{target.text}”的项目行。",
        )

    return ExecutionEvidence(
        kind="dom_text_present",
        target=target.text,
        status="missing",
        confidence=0.7,
        summary=f"操作执行后，列表中没有确认看到“{target.text}”。",
    )
```

实现注意：

- `target` 必须使用 `ExecutionEvidenceTarget.text`。
- selector 指定时只查 selector 区域。
- selector 缺失时才查 `body`。
- 采集失败返回 `unknown`，不得抛出覆盖 replay 结果。

## run_replay 集成

`run_replay()` 目标签名：

```python
def run_replay(
    learned_path: LearnedPath,
    url: str,
    *,
    headless: bool = True,
    slot_overrides: dict[str, str] | None = None,
    evidence_targets: list[ExecutionEvidenceTarget] | None = None,
) -> ReplayResult:
```

执行流程：

```python
step_logs = []
execution_evidence = []

for action in precheck.actions:
    effective_action, override_report = apply_replay_slot_overrides(action, slot_overrides)
    log = execute_action(effective_action, runtime)
    wait_result = wait_for_change_after_action(
        page=runtime.page if runtime else None,
        action=effective_action,
        step_log=log,
    )
    step_logs.append(log)

execution_evidence = capture_execution_evidence(
    runtime.page if runtime else None,
    evidence_targets or [],
)

return ReplayResult(
    ...,
    execution_evidence=execution_evidence,
)
```

关键要求：

- evidence capture 必须在 `finally: runtime.stop()` 前。
- replay action 失败时也允许返回已有 replay status；P0 不要求失败后继续采集 evidence。
- 如果 replay precheck blocked，`execution_evidence` 为空。

## Chat Runtime Evidence Target

在 `InteractiveChatRuntime` execute branch 中，已有 `slot_overrides.record_name` 时构造：

```python
evidence_targets = []
record_name = slot_overrides.get("record_name")
if record_name and action.get("page_template") == "/records" or action.get("target_url", "").endswith("/records"):
    evidence_targets.append(
        ExecutionEvidenceTarget(
            kind="dom_text_present",
            text=record_name,
            source_slot="record_name",
            selector="[data-testid='record-list']",
        )
    )
```

实现时要避免 operator precedence bug，建议写成：

```python
is_items_target = (
    action.get("page_template") == "/records"
    or urlparse(action.get("target_url", "")).path.rstrip("/") == "/records"
)
```

然后再判断：

```python
if record_name and is_items_target:
    ...
```

## Replay Hook 传播

扩展 `ReplayHandler` / `run_explicit_replay()`：

```python
def __call__(
    learned_path_id: str,
    url: str,
    *,
    headless: bool = True,
    slot_overrides: dict[str, str] | None = None,
    evidence_targets: list[ExecutionEvidenceTarget] | None = None,
) -> ConversationReplaySummary:
    ...
```

`run_explicit_replay()` 调 `run_replay()` 后，把 `result.execution_evidence` 带入
`ConversationReplaySummary`。

## Reporter Adapter 设计

新增内部 helper，可以放在 `chat_runtime.py` 或小型 module 中：

```python
def build_replay_reporter_input(
    *,
    user_goal: str,
    target_url: str,
    learned_action_alias: str,
    slot_overrides: dict[str, str],
    replay_summary: ConversationReplaySummary,
) -> tuple[str, dict[str, Any], ConversationReplaySummary, dict[str, Any]]:
    execution_payload = {
        "learned_path_id": replay_summary.learned_path_id,
        "target_url": target_url,
        "alias": learned_action_alias,
        "slot_overrides": slot_overrides,
        "execution_evidence": [ev.model_dump() for ev in replay_summary.execution_evidence],
    }
    confirmed_plan_context = {
        "learned_path_id": replay_summary.learned_path_id,
        "target_url": target_url,
        "postcondition_evidence": [ev.model_dump() for ev in replay_summary.execution_evidence],
    }
    return "completed", execution_payload, replay_summary, confirmed_plan_context
```

如果 `ConversationReplaySummary.execution_evidence` 是 dict list，先 validate：

```python
evidence = [ExecutionEvidence.model_validate(raw) for raw in replay_summary.execution_evidence]
```

## TaskResultReporter verified path

修改 `TaskResultReporter._check_postconditions()`：

```python
def _check_postconditions(
    self,
    replay_summary: ConversationReplaySummary,
    confirmed_plan_context: dict[str, Any] | None,
) -> bool:
    evidence_items = []
    if confirmed_plan_context:
        evidence_items.extend(confirmed_plan_context.get("postcondition_evidence") or [])
        evidence_items.extend(confirmed_plan_context.get("execution_evidence") or [])

    expected_target = None
    if confirmed_plan_context:
        slot_overrides = confirmed_plan_context.get("slot_overrides") or {}
        expected_target = slot_overrides.get("record_name")

    for raw in evidence_items:
        ev = ExecutionEvidence.model_validate(raw)
        if (
            ev.kind == "dom_text_present"
            and ev.status == "verified"
            and (expected_target is None or ev.target == expected_target)
        ):
            return True
    return False
```

实现时可调整字段位置，但必须满足 contract 的 verified 条件。

## 用户回复集成

`chat_runtime` execute branch 当前可以直接根据 replay status 写“完成 / 失败”。
本包完成后，execute branch 对有 reporter evidence 的路径应优先使用
`TaskResultReporter.build_report()` 的 `user_response`。

P0 中文回复可在 adapter 后覆盖 reporter 默认英文文案，或扩展 reporter 文案。要求是：

- `verified` 明确说明页面证据。
- `uncertain` 不说成功。
- `needs_review` 说明没有确认看到目标。
- `failed` / `blocked` 不给恢复菜单。

## Contract Alignment

| Contract | Design 对齐 |
|---|---|
| `ExecutionEvidenceTarget.text -> ExecutionEvidence.target` | capture helper 明确使用 target.text |
| runtime stop 前采集 | `run_replay()` 在 return 前、finally stop 前调用 capture |
| selector 优先 | `_capture_dom_text_present()` 先用 selector scope |
| Reporter verified path | `_check_postconditions()` 读取 structured evidence |
| outcome 不改名 | `TaskResultReporter` 保持原生 outcome |
| adapters 不是 skills | helper 只在 runtime / replay service 内调用 |
| P0 不做 recovery | 回复不包含重试 / 重新学习 / 取消菜单 |
