# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未开始实现）

## 现状

本包涉及的现有文件：

```text
apps/api/app/services/conversation/intake.py
apps/api/app/services/conversation/chat_runtime.py
apps/api/app/services/conversation/replay_hook.py
apps/api/app/services/learning/learning_run_service.py
apps/api/app/schemas/learned_path_replay.py
apps/api/app/services/learning/learned_path_replay.py
apps/api/app/services/execution/action_executor.py
```

当前关键缺口：

| 文件 | 当前行为 | 缺口 |
|---|---|---|
| `intake.py` | fallback 只抽 username / password | 不抽 `record_name` |
| `chat_runtime.py` | `_fill_values_from_intake()` 只收 username / password | 执行阶段拿不到 `record_name` |
| `learning_run_service.py` | LearnedPath actions 只保留固定 `value` | 学习后无法绑定 `value_slot` |
| `learned_path_replay.py` schema | `ReplayRequest` 只有 `url`；`ReplayAction` 没有 `value_slot` | 无法表达运行时覆盖 |
| `learned_path_replay.py` service | `run_replay()` 固定执行 action.value | 学习 A 后会继续填 A |
| `replay_hook.py` | replay handler 只接 learned_path_id / url / headless | runtime 无法传 `slot_overrides` |

## Contract Alignment

| Contract | Design |
|---|---|
| `record_name` canonical slot | Intake fallback 增加 `/records` 新增项目名抽取；runtime fill values 接受 `record_name` |
| `value_slot` action metadata | 学习完成后扫描 fill action，匹配学习时 `fill_values.record_name` 并写入 `value_slot=record_name` |
| `slot_overrides` request | 扩展 replay schema、hook 和 runtime execute branch |
| fixed value replay 阻断 | 当用户给 `record_name` 但 matched path 没有 `value_slot=record_name` 时，runtime 阻断 |
| effective action | replay 执行前生成 `effective_action`，执行和 wait-for-change 都使用它 |
| step log evidence | replay step log / debug data 记录 `value_slot`、`override_applied`、`effective_value` |
| 不接 evidence / reporter | 本包不引入 `ExecutionEvidence` 或 TaskResultReporter adapter |

## 文件变更

### 预计修改

```text
apps/api/app/services/conversation/intake.py
apps/api/app/services/conversation/chat_runtime.py
apps/api/app/services/conversation/replay_hook.py
apps/api/app/services/learning/learning_run_service.py
apps/api/app/schemas/learned_path_replay.py
apps/api/app/services/learning/learned_path_replay.py
```

### 预计测试

```text
apps/api/tests/test_conversation_intake.py
apps/api/tests/test_conversation_chat_runtime.py
apps/api/tests/test_conversation_replay_hook.py
apps/api/tests/test_learning_run_service.py
apps/api/tests/test_learned_path_replay.py
```

如果实现需要 repository helper，可小范围修改：

```text
apps/api/app/repos/learned_paths_repo.py
apps/api/tests/test_learned_paths_repo.py
```

## 设计 1：Intake `record_name`

### LLM schema

现有 intake slot schema 支持任意 slot name / semantic type，因此 P0 不需要新增独立
Pydantic schema。Prompt / fallback 需要明确 canonical slot：

```json
{
  "name": "record_name",
  "semantic_type": "record_name",
  "value": "测试项目A",
  "sensitive": false
}
```

### Deterministic fallback

fallback 至少支持：

```text
名称叫<name>
名称为<name>
项目名是<name>
项目叫<name>
新增<name>
name 是<name>
```

抽取规则要避免把“新增项目”本身当作 item name。建议先识别 action intent，再用更具体
pattern 抽取尾部名称。

## 设计 2：Runtime fill values

扩展 `_fill_values_from_intake()`：

```python
allowed_semantic_types = {"username", "password", "record_name"}
allowed_names = {"username", "password", "record_name"}
```

P0 canonical 输出：

```json
{
  "record_name": "测试项目A"
}
```

可以保留 username / password 现有行为，但不得把 sensitive slot 明文写入 trace。

## 设计 3：LearnedPath Parameterizer

学习完成后，runtime / learning service 基于本轮 `fill_values` 对 actions 做 metadata-only
参数绑定。

P0 规则：

```python
if action["action_type"] == "fill" and action.get("value") == fill_values["record_name"]:
    action["value_slot"] = "record_name"
```

建议函数：

```python
def parameterize_learned_path_actions(
    actions: list[dict[str, Any]],
    fill_values: dict[str, str],
) -> tuple[list[dict[str, Any]], ParameterizationReport]:
    ...
```

返回报告：

```json
{
  "status": "bound",
  "slots": ["record_name"],
  "warnings": []
}
```

### Dedup 处理

`LearningRunService` 当前可能命中已有 LearnedPath。P0 不覆盖整条 actions；如需更新已有
row，只允许做 metadata-only merge：

```text
same action_type
same target_selector
same value
existing action missing value_slot
```

不满足这些条件时，不强行改旧 path，返回 `not_bound` 或 warning。

## 设计 4：Replay schema

扩展：

```python
class ReplayRequest(BaseModel):
    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)

class ReplayAction(BaseModel):
    step: int
    action_type: str
    target_selector: str | None = None
    target_description: str | None = None
    value: str | None = None
    value_slot: str | None = None
```

`_build_replay_actions()` 必须读取：

```python
value_slot=raw.get("value_slot")
```

建议扩展 `ReplayStepLog`，方便测试和后续 11.3.5.6 记录：

```python
value_slot: str | None = None
override_applied: bool = False
effective_value: str | None = None
```

P0 `/records` 的 `effective_value` 可以明文；未来敏感字段必须 redacted。

## 设计 5：Replay slot override adapter

内部函数：

```python
def apply_replay_slot_overrides(
    action: ReplayAction,
    slot_overrides: dict[str, str],
) -> tuple[ReplayAction, OverrideReport]:
    if action.action_type != "fill":
        return action, OverrideReport(applied=False)

    if not action.value_slot:
        return action, OverrideReport(applied=False)

    if action.value_slot not in slot_overrides:
        raise MissingSlotOverrideError(action.value_slot)

    return action.model_copy(
        update={"value": slot_overrides[action.value_slot]}
    ), OverrideReport(applied=True, value_slot=action.value_slot)
```

`MissingSlotOverrideError` 可以被 `run_replay()` 捕获并转成 failed replay result；chat
runtime 更应该在调用 replay 前先阻断。

## 设计 6：`run_replay()` effective action

目标结构：

```python
slot_overrides = slot_overrides or {}

for action in precheck.actions:
    effective_action, override_report = apply_replay_slot_overrides(
        action,
        slot_overrides,
    )

    log = execute_action(effective_action, runtime)
    log.value_slot = override_report.value_slot
    log.override_applied = override_report.applied
    log.effective_value = safe_effective_value(effective_action, override_report)

    wait_result = wait_for_change_after_action(
        page=runtime.page if runtime else None,
        action=effective_action,
        step_log=log,
    )
```

关键约束：`wait_for_change_after_action()` 必须使用 `effective_action`，不能继续使用原始
action，否则等待、日志和诊断会继续引用录制值 A。

## 设计 7：Chat runtime execute branch

执行分支需要：

1. 从 intake slots 生成 `fill_values.record_name`。
2. 找到唯一 matched learned action。
3. 读取 LearnedPath actions 或 action summary，确认存在 `value_slot=record_name`。
4. 构造 `slot_overrides={"record_name": "测试项目B"}`。
5. 调 `_replay_handler(..., slot_overrides=slot_overrides)`。

如果用户给了 `record_name` 但 LearnedPath 不支持 `value_slot=record_name`：

```text
Runtime 阻断
不调用 replay
回复要求重新学习参数化路径
```

## 设计 8：Replay hook propagation

扩展 protocol：

```python
class ReplayHandler(Protocol):
    async def __call__(
        self,
        learned_path_id: str,
        url: str,
        *,
        headless: bool = True,
        slot_overrides: dict[str, str] | None = None,
    ) -> ReplayHookResult:
        ...
```

`run_explicit_replay()` 把 `slot_overrides` 传入 `run_replay()`。

显式 slash replay 如果没有 slot 参数，默认 `{}`，保持旧行为。

## Test Matrix

| Layer | Scenario | Expected |
|---|---|---|
| Intake | `学习新增项目，名称叫测试项目A` | slots 含 `record_name=测试项目A` |
| Intake | `帮我新增项目，名称叫测试项目B` | execute intent + `record_name=测试项目B` |
| Runtime | `_fill_values_from_intake()` | 输出 `record_name` |
| Learning | fill action value 等于学习值 | actions JSON 写入 `value_slot=record_name` |
| Learning | 无匹配 fill action | parameterization status `not_bound` |
| Replay schema | `ReplayRequest(slot_overrides=...)` | schema 接受并默认 `{}` |
| Replay build | raw action 有 `value_slot` | `ReplayAction.value_slot` 被读取 |
| Replay execute | A action + B override | `execute_action()` 收到 B |
| Replay wait | A action + B override | `wait_for_change_after_action()` 收到 B |
| Runtime execute | path 支持 `value_slot` | replay handler 收到 `slot_overrides.record_name=B` |
| Runtime block | path 不支持 `value_slot` | 不调用 replay，返回重新学习提示 |

## 风险与约束

| 风险 | 处理 |
|---|---|
| 只改 schema，runtime 没传 override | test-plan 必须覆盖 chat runtime -> replay handler propagation |
| replay 执行 B，但 wait/log 仍使用 A | 强制 wait-for-change 使用 `effective_action` |
| 把 internal adapter 暴露给 Router | 文档明确 adapter 不是 Application Skill |
| 旧 LearnedPath 被误改 | 只允许 metadata-only merge，不覆盖原 action 行为 |
| 敏感值进日志 | P0 只允许非敏感 `record_name` 明文，future credential slot 必须 redacted |
