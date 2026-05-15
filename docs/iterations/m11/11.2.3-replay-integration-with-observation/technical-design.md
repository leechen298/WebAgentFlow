# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

11.2.2 已经完成最小 step-level wait result 能力：

- `ReplayStepLog` 已有可选字段 `wait_result: WaitResult | None = None`。
- `WaitResult` 是 step-level wait outcome，只描述某个 replay step 后等待过程如何结束。
- `ObservationSignal` 是 observed evidence atom，只描述观察到了什么。
- `apps/api/app/services/learning/wait_for_change.py` 当前实际生成：
  - `url_changed`：primary signal。
  - `title_changed`：primary signal。
  - `network_idle_observed`：supporting signal only。
- `page_load_finished` 保留在 schema 中，但当前 11.2.2 MVP 不实际生成。
- 当前 `ReplayResult` 尚未有 replay-level `observation_summary`。
- 当前 Task Result Reporter 尚未消费 observation / wait evidence。

11.2.3 当前已有 `contract.md`，定义 replay-level observation evidence
aggregation 的概念、字段 proposal 和 status。本文档只定义后续实现设计，不改
`contract.md`。如果实现阶段发现 `contract.md` 不足，应记录为设计阻塞或 follow-up，
不能静默改变实现语义。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Replay Observation Evidence 是 replay-level aggregation | 后续新增 `ReplayObservationSummary`，由 replay steps 的 `wait_result` 聚合生成。 | `test-plan.md` aggregation service tests / replay integration tests | 不重新执行 wait-for-change。 |
| WaitResult 是 step-level outcome | 只读取 `ReplayStepLog.wait_result`，不修改 `WaitResult` 语义。 | `test-plan.md` backward compatibility tests | 11.2.2 已实现 step-level 能力。 |
| ObservationSignal 是 evidence atom | 从 `wait_result.observed_signals` 汇总 signal kinds 和 refs。 | `test-plan.md` aggregation service tests | 不复制完整 signal payload 以外的大对象。 |
| `has_primary_observation` 不等于业务成功 | summary 仅设置布尔字段和 status，不改变 `ReplayResult.status`，不输出 success verdict。 | `test-plan.md` boundary tests | Reporter 未来也必须保守消费。 |
| `has_timeout` 不等于 retry | timeout 只进入 counts / flags / notes，不触发 retry 或 recovery。 | `test-plan.md` boundary tests | M12 才处理 retry / recovery。 |
| `has_only_supporting_observation` 必须保守消费 | 仅当没有 primary signal 且至少一个 supporting signal 存在时为 true。 | `test-plan.md` only network idle case | 当前 supporting signal 是 `network_idle_observed`。 |
| 不修改 `ReplayResult.status` 语义 | `observation_summary` 是 `ReplayResult` 的可选补充字段，不参与 replay status 推导。 | `test-plan.md` replay integration tests | `succeeded` / `failed` / `drifted` 等语义保持不变。 |
| 不接 Task Result Reporter | `build_replay_observation_summary` 不导入、不调用 reporter。 | `test-plan.md` boundary tests | 11.2.5 才接 reporter。 |
| 不保存 raw HTML / DOM dump | summary 和 refs 只保存统计、signal kind、wait id、step index 和短 notes。 | `test-plan.md` schema / boundary tests | 不复制 DOM、HTML、screenshot payload 或 reporter 文案。 |

## 实现方案（Proposed Implementation）

后续代码实现应新增 replay-level aggregation，而不是扩展 wait-for-change 本身：

1. 在 `apps/api/app/schemas/learned_path_replay.py` 中新增
   `ReplayObservationStatus`、`StepObservationRef`、`ReplayObservationSummary`。
2. 给 `ReplayResult` 增加可选字段：
   `observation_summary: ReplayObservationSummary | None = None`。
3. 新增 `apps/api/app/services/learning/replay_observation.py`，实现
   `build_replay_observation_summary(...)`。
4. 在 `run_replay()` 构造最终 `ReplayResult` 前，从 steps 聚合 summary。
5. 对 precheck blocked / drifted / unsupported / candidate missing 等未进入
   action execution 的结果，不生成 `observation_summary`，保持为 `None`。
6. 对已进入 replay 流程但 `actions=[]` 的 observational path，生成
   `status=not_applicable` 的 `observation_summary`。
7. 不改变 `ReplayResult.status`。
8. 不调用 Task Result Reporter。
9. 不做 recovery / retry / abort。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 不新增 API 路径。 | N/A |
| API response schema | Yes | `ReplayResult` 后续可选增加 `observation_summary`。 | 向后兼容；旧客户端可忽略。 |
| Database schema / migration | No | 不新增表，不修改 migration。 | N/A |
| CLI | No | 不修改 CLI。 | N/A |
| Console UI | No | 不修改 UI。 | N/A |
| Conversation events | No | 不新增 conversation event。 | N/A |
| Replay execution | Yes | 后续在 replay result 构造时聚合 step `wait_result`。 | 不改变 replay status，不重新执行 action。 |
| Task Result Reporter | No | 本轮不接 reporter。 | 11.2.5 才消费。 |
| Worker / async jobs | No | 不改 worker。 | N/A |
| Tests / fixtures | Yes | 后续新增 aggregation 单测和 replay integration 单测。 | 不跑 E2E。 |
| Docs | Yes | 本轮新增 technical-design / test-plan。 | N/A |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

后续计划在 `apps/api/app/schemas/learned_path_replay.py` 新增：

```text
ReplayObservationStatus
StepObservationRef
ReplayObservationSummary
```

建议 `ReplayObservationStatus` 收敛为：

```text
observed
no_primary_observation
partial_observation
not_applicable
```

建议 `ReplayObservationSummary` 字段对齐 `contract.md`：

```text
observation_summary_id
replay_id
learned_path_id
status
step_count
wait_result_count
observed_step_count
timeout_step_count
skipped_step_count
not_required_step_count
primary_signal_kinds
supporting_signal_kinds
has_primary_observation
has_timeout
has_only_supporting_observation
has_uncertain_observation
observation_notes
step_observation_refs
```

`ReplayResult` 后续增加：

```python
observation_summary: ReplayObservationSummary | None = None
```

边界：

- 可选字段，向后兼容。
- 不改 API route。
- 不改 DB schema。
- 不改 `ReplayResult.status`。
- 不保存 raw HTML / DOM dump。
- 不复制完整 step log 或 screenshots。

## StepObservationRef 设计

`step_observation_refs` 不复制完整对象，只引用最小信息：

```text
step_index
wait_id
wait_status
primary_signal_kind
signal_kinds
has_primary_signal
has_supporting_signal
notes
```

边界：

- 不复制完整 step log。
- 不复制 `screenshot_ref`。
- 不复制 screenshot payload。
- 不复制 raw HTML。
- 不复制 DOM dump。
- 不复制 reporter wording。

## 服务 / 模块设计（Service / Module Design）

建议新增：

```text
apps/api/app/services/learning/replay_observation.py
```

建议函数签名：

```python
def build_replay_observation_summary(
    *,
    learned_path_id: str,
    steps: list[ReplayStepLog],
    replay_id: str | None = None,
) -> ReplayObservationSummary:
    ...
```

职责：

- 输入来自 replay steps。
- 只读取 `step.wait_result`。
- 统计 wait status。
- 聚合 primary / supporting signal kinds。
- 生成最小 `StepObservationRef`。
- 输出 `ReplayObservationSummary`。

禁止：

- 不读取页面。
- 不调用 Playwright。
- 不调用 LLM。
- 不调用 Task Result Reporter。
- 不触发 recovery / retry / abort。
- 不读取 raw HTML。
- 不保存 DOM dump。
- 对没有 `wait_result` 的旧 step 保持兼容。

## 数据流（Data Flow）

后续代码实现的数据流：

```text
run_replay()
-> execute_action(action, runtime)
-> wait_for_change_after_action(...)
-> ReplayStepLog(wait_result=...)
-> build_replay_observation_summary(learned_path_id, steps)
-> ReplayResult(observation_summary=...)
```

summary 生成发生在 replay result 构造阶段。它只聚合已经存在的 step-level evidence，
不重新观察页面，不修改 action execution，不影响 replay status。

## 状态推导（Status / State Derivation）

Primary / supporting signal 分类：

```text
primary:
- url_changed
- title_changed

supporting:
- network_idle_observed

schema-reserved but not emitted by current 11.2.2:
- page_load_finished
```

`network_idle_observed` 不得进入 `primary_signal_kinds`。

`page_load_finished` 当前 11.2.2 不会实际生成。未来如果生成，只有在后续 contract
明确其 action-related page-load evidence 边界后，才能作为 primary / target signal
处理。

Status 推导优先级：

```text
if step_count == 0 or all wait_result.status == not_required:
    status = not_applicable
elif has_primary_observation and (has_timeout or has_skipped_or_uncertain):
    status = partial_observation
elif has_primary_observation:
    status = observed
else:
    status = no_primary_observation
```

说明：

- `timeout` 不触发 retry。
- `skipped` 不等于失败。
- `skipped only` 不等于 `not_applicable`；它表示 replay 有 action step，但没有形成
  primary observation，应归为 `no_primary_observation` 并通过 counts / notes 保守表达。
- `partial_observation` 不等于业务部分成功，只表示 observation evidence 不完整。
- `observed` 不等于任务成功。

## 兼容性（Compatibility）

- 旧 `ReplayResult` 没有 `observation_summary` 时仍合法。
- 旧 `ReplayStepLog` 没有 `wait_result` 时仍合法。
- 若 steps 中没有任何 `wait_result`，summary 可返回 `no_primary_observation`，并通过
  `wait_result_count=0` 表示旧数据或未接入状态。
- Precheck blocked / drifted / unsupported / candidate missing 等未进入 action
  execution 的结果不生成 `observation_summary`，保持为 `None`。
- `actions=[]` observational path 应为 `not_applicable`。
- 全部 `not_required` 应为 `not_applicable`。
- `skipped only` 应为 `no_primary_observation`，不是失败，也不是 `not_applicable`。
- 不改 replay status。
- 不影响 existing API clients。

## 失败 / 边界情况（Failure / Edge Cases）

后续实现必须覆盖：

- steps 为空。
- 所有 wait_result 都是 `not_required`。
- 有 observed primary signal。
- 只有 supporting signal。
- 有 timeout。
- 有 skipped。
- 有 `wait_result = None`。
- primary + timeout / skipped 混合。
- duplicated signal kinds。
- malformed / missing signal fields。
- no raw HTML fields。

异常处理原则：

- summary aggregation 不应让 replay result 从 succeeded 变为 failed。
- malformed signal 应尽量降级为 notes / uncertainty，而不是触发 recovery。
- 如果实现阶段发现 schema 无法表达边界，应先更新 contract / technical-design，再实现。

## 非目标（Non-goals）

- 不实现 Task Result Reporter integration。
- 不做 recovery / retry / abort / user takeover。
- 不实现 Common Component Runtime Semantics。
- 不调用 Page Understanding Agent。
- 不实现 Page Context Bridge。
- 不读取或保存 raw HTML。
- 不保存 DOM dump。
- 不修改 database schema。
- 不新增 API route。
- 不修改 CLI / UI / conversation event。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Schema tests | 验证 summary / ref schema 和可选 response 字段。 | `test-plan.md` schema tests |
| Aggregation service tests | 验证 status 推导、counts、primary/supporting 聚合。 | `test-plan.md` aggregation service tests |
| Replay integration tests | 验证 `run_replay()` 后续可挂载 summary 且不改变 replay status。 | `test-plan.md` replay integration tests |
| Compatibility tests | 验证旧 step / no wait_result / actions=[] 兼容。 | `test-plan.md` backward compatibility tests |
| Boundary tests | 验证不调用 reporter / recovery / raw HTML / Page Understanding Agent。 | `test-plan.md` boundary tests |

## 验证命令入口（Validation Commands）

后续代码实现的最低验证命令：

```bash
git diff --check

cd apps/api && ../../.venv/bin/python -m pytest \
  tests/test_replay_observation_summary.py \
  tests/test_learned_path_replay.py \
  -v

cd apps/api && ../../.venv/bin/ruff check \
  app/schemas/learned_path_replay.py \
  app/services/learning/replay_observation.py \
  app/services/learning/learned_path_replay.py \
  tests/test_replay_observation_summary.py \
  tests/test_learned_path_replay.py
```
