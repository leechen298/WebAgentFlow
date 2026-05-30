# 契约（Contract）

状态：ready_for_implementation（design review passed，未开始实现）

## 概念 / 边界契约

### ExecutionEvidenceTarget

`ExecutionEvidenceTarget` 是 replay 请求中的证据采集目标。P0 只支持
`dom_text_present`：

```python
class ExecutionEvidenceTarget(BaseModel):
    kind: Literal["dom_text_present"]
    text: str
    source_slot: str | None = None
    selector: str | None = None
```

`/records` 新增项目的 P0 target：

```json
{
  "kind": "dom_text_present",
  "text": "测试项目B-20260521-001",
  "source_slot": "record_name",
  "selector": "[data-testid='record-list']"
}
```

规则：

- `text` 是要查找的业务结果文本。
- `source_slot` 记录该文本来自哪个 slot，P0 是 `record_name`。
- `selector` 存在时必须优先在 selector 指定区域内查找文本。
- selector 缺失时才退化为全页面查找。
- 不允许用 toast、debug log 或历史文本优先判断 `/records` 新增成功。

### ExecutionEvidence

`ExecutionEvidence` 是 replay 后采集到的结构化页面证据。P0 只支持
`dom_text_present` 和 `unknown`：

```python
class ExecutionEvidence(BaseModel):
    kind: Literal["dom_text_present", "unknown"]
    target: str | None = None
    status: Literal["verified", "missing", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
```

关键映射：

```text
采集 dom_text_present evidence 时，
ExecutionEvidence.target 必须使用 ExecutionEvidenceTarget.text。
```

这保证 Reporter verified 条件可以稳定比较：

```text
execution_evidence.target == slot_overrides.record_name
```

### Internal Runtime Adapter 边界

以下能力是内部代码步骤，不是 Application Skill：

- build evidence targets from slot overrides。
- capture execution evidence。
- build replay reporter input。
- map execution evidence into postcondition evidence。

它们不得出现在 Router skill menu，也不得由 LLM agents 直接请求。Router 仍然只能推荐
业务级 `start_replay`，不能推荐 `capture_execution_evidence` 或 reporter adapter。

## Schema / API 契约

### ReplayRequest

在 11.3.5.4 的基础上扩展：

```python
class ReplayRequest(BaseModel):
    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)
    evidence_targets: list[ExecutionEvidenceTarget] = Field(default_factory=list)
```

兼容性：

- 旧请求只传 `url` 仍然有效。
- 不传 `evidence_targets` 时 replay 不做 DOM evidence 采集，Reporter 不得因此输出 verified。

### ReplayResult

推荐直接扩展：

```python
class ReplayResult(BaseModel):
    ...
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

### ConversationReplaySummary

Conversation replay summary 必须带出最小 evidence：

```python
class ConversationReplaySummary(BaseModel):
    ...
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

如果为避免 schema import 环，需要使用 `list[dict[str, Any]]`，也必须保证字典内容
符合 `ExecutionEvidence` 字段，并在 adapter 层重新校验。

## Evidence 采集契约

采集时机必须是：

```text
所有 replay action 执行完成之后
runtime.stop() 之前
ReplayResult 返回之前
```

P0 采集规则：

| 场景 | Evidence |
|---|---|
| selector 区域存在目标文本 | `kind=dom_text_present`, `status=verified`, `confidence=0.95` |
| selector 区域不存在目标文本 | `kind=dom_text_present`, `status=missing`, `confidence=0.7` |
| selector 查找异常或 page unavailable | `kind=unknown`, `status=unknown`, `confidence=0.0` |

`summary` 必须是用户可读但不夸大的页面证据描述。

## Reporter Adapter 契约

Reporter Adapter 输入：

```python
class ReplayReporterAdapterInput(BaseModel):
    user_goal: str
    target_url: str | None = None
    learned_action_alias: str | None = None
    replay_status: str
    drift_status: str | None = None
    replay_warnings: list[str] = Field(default_factory=list)
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
    slot_overrides: dict[str, str] = Field(default_factory=dict)
```

Reporter Adapter 输出必须能喂给当前 `TaskResultReporter.build_report()`：

```python
execution_status: str
execution_payload: dict[str, Any]
replay_summary: ConversationReplaySummary | None
confirmed_plan_context: dict[str, Any] | None
```

P0 必须让 `TaskResultReporter._check_postconditions()` 读到 structured postcondition
evidence。允许两种实现：

1. 把 verified `ExecutionEvidence` 转成 `confirmed_plan_context["postconditions"]`。
2. 扩展 `_check_postconditions()`，读取 `execution_payload` 或
   `confirmed_plan_context` 中的 `execution_evidence` / `postcondition_evidence`。

不得只把 evidence 放进 event payload。

## Reporter Outcome 契约

Reporter 原生 outcome 保持：

```text
verified
failed
uncertain
needs_review
blocked
```

不得改成：

```text
success
partial_success
failed
unknown
```

P0 outcome 映射：

| Replay / Evidence | Reporter outcome |
|---|---|
| replay succeeded / observed + drift none + no error + `dom_text_present` verified | `verified` |
| replay succeeded / observed + drift none + no error + no useful evidence | `uncertain` |
| replay succeeded / observed + target text missing | `needs_review` |
| replay failed or runtime error | `failed` |
| replay drifted / unsupported / candidate missing | `blocked` 或 `needs_review` |

P0 `verified` 条件必须同时满足：

```text
replay_summary.replay_status in ("succeeded", "observed")
replay_summary.drift_status == "none"
replay_summary.error is empty
execution_evidence 中存在：
  kind = "dom_text_present"
  status = "verified"
  target = slot_overrides.record_name
```

不满足时不得输出 `verified`。

## 用户回复契约

`verified`：

```text
执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。
```

`uncertain`：

```text
操作已经执行，但我还没有拿到足够页面证据确认结果。建议你查看列表是否出现了“测试项目B”。
```

`needs_review`：

```text
操作执行后，我没有在列表中确认看到“测试项目B”。可能页面更新较慢，也可能操作没有成功。
```

`blocked`：

```text
我找到了已学习路径，但当前页面和学习时的页面不匹配，所以没有继续执行。请确认是否打开了正确的页面。
```

`failed`：

```text
执行过程中遇到问题，这次没有完成新增项目。
```

本包不提供“重试 / 重新学习 / 取消”菜单；那属于 11.3.5.8。

## 测试数据契约

P0 测试 `record_name` 必须唯一，例如：

```text
测试项目B-20260521-001
测试项目B-${timestamp}
```

原因是 DOM evidence 不应被页面其他区域、历史状态、toast 或旧数据误导。

## 兼容性契约

- 不新增数据库 migration。
- 不改变 LearnedPath 表结构。
- 不改变 replay action 参数化语义。
- 不改变 `TaskResultReporter` 原生 outcome 枚举。
- 旧 replay 不传 `evidence_targets` 时继续可运行，但 reporter 不能输出 verified。
- 旧 tests 对 replay status / drift status 的断言必须继续成立。

## 非目标

- 不实现 `dom_text_absent`、`url_changed`、`toast_visible`、`list_row_count_changed`。
- 不让 LLM 读取页面判断成功。
- 不新增 Recovery Agent。
- 不接 TaskPathPlanner。
- 不改变 Router skill menu。
- 不把 Internal Runtime Adapters 暴露成 Application Skills。
