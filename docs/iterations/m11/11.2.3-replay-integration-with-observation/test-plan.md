# 测试计划（Test Plan）

状态：proposed

## 适用条件

本文件适用于 11.2.3 后续代码实现。11.2.3 涉及 replay、observation evidence、
schema、aggregation 和 compatibility，因此必须维护测试计划。

## 测试范围（Test Scope）

- Unit：schema tests、aggregation service tests、boundary tests。
- Integration：replay integration tests，验证 `run_replay()` 可以携带 summary。
- API：通过 replay response schema 间接覆盖，不新增 API route。
- Console UI：N/A，本轮不改 UI。
- E2E：N/A，本轮不跑 E2E。
- Agent / Reporter / Recovery：只测试不调用 Reporter / recovery / abort。
- Codex / AI External Operator：N/A，本轮不做 live UI smoke。
- Live autonomous run：N/A，本轮不运行 `verify-scenario` 或 autonomous run。

不覆盖：

- E2E。
- live UI smoke。
- `verify-scenario`。
- autonomous run。
- Task Result Reporter。
- M12 recovery。
- Common Component Runtime Semantics。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| schema | `ReplayObservationSummary` accepts valid statuses | `tests/test_replay_observation_summary.py` | `observed` / `no_primary_observation` / `partial_observation` / `not_applicable` are valid | Yes | status literal coverage |
| schema | invalid summary status rejected | `tests/test_replay_observation_summary.py` | invalid status raises validation error | Yes | if using Pydantic model |
| schema | `ReplayResult.observation_summary` may be None | `tests/test_replay_observation_summary.py` | old response shape remains valid | Yes | backward compatible |
| schema | `StepObservationRef` excludes raw payloads | `tests/test_replay_observation_summary.py` | no raw HTML / DOM dump / screenshot payload fields | Yes | field-level invariant |
| aggregation | empty steps | `tests/test_replay_observation_summary.py` | status=`not_applicable`, step_count=0 | Yes | actions=[] equivalent |
| aggregation | observational path actions=[] | `tests/test_replay_observation_summary.py` | status=`not_applicable` | Yes | no replay action steps |
| aggregation | all wait results are `not_required` | `tests/test_replay_observation_summary.py` | status=`not_applicable` | Yes | observe-only path |
| aggregation | one observed primary signal | `tests/test_replay_observation_summary.py` | status=`observed`, has_primary_observation=true | Yes | no timeout / skipped |
| aggregation | observed primary + skipped | `tests/test_replay_observation_summary.py` | status=`partial_observation` | Yes | matches contract priority |
| aggregation | observed primary + timeout | `tests/test_replay_observation_summary.py` | status=`partial_observation`, has_timeout=true | Yes | timeout does not retry |
| aggregation | only `network_idle_observed` | `tests/test_replay_observation_summary.py` | status=`no_primary_observation`, has_only_supporting_observation=true | Yes | supporting only |
| aggregation | timeout only | `tests/test_replay_observation_summary.py` | status=`no_primary_observation`, has_timeout=true | Yes | no primary signal |
| aggregation | skipped only | `tests/test_replay_observation_summary.py` | status=`no_primary_observation` | Yes | skipped is not failure and not not_applicable |
| aggregation | `wait_result=None` | `tests/test_replay_observation_summary.py` | no crash; wait_result_count excludes it | Yes | old step compatibility |
| aggregation | duplicated signal kinds | `tests/test_replay_observation_summary.py` | `primary_signal_kinds` / `supporting_signal_kinds` are deduped | Yes | stable summary |
| replay integration | successful replay returns optional summary | `tests/test_learned_path_replay.py` | `ReplayResult.observation_summary` may be populated | Yes | implementation phase |
| replay integration | replay status unchanged | `tests/test_learned_path_replay.py` | observation summary does not alter `ReplayResult.status` | Yes | core invariant |
| replay integration | failed replay may carry summary | `tests/test_learned_path_replay.py` | failure semantics unchanged | Yes | summary is diagnostic evidence |
| replay integration | wait service exception produced skipped wait result | `tests/test_learned_path_replay.py` | summary aggregates skipped safely | Yes | follows 11.2.2 behavior |
| replay integration | blocked / drifted precheck without action execution | `tests/test_learned_path_replay.py` | `observation_summary is None` | Yes | no observation window exists |
| replay integration | `actions=[]` observational path | `tests/test_learned_path_replay.py` | `observation_summary.status == not_applicable` | Yes | legal replay result with no action steps |
| boundary | reporter not called | `tests/test_replay_observation_summary.py` or patch assertions | no Task Result Reporter import/call | Yes | 11.2.5 only |
| boundary | recovery / retry / abort not called | `tests/test_replay_observation_summary.py` or import boundary checks | no recovery side effects | Yes | M12 only |
| boundary | Page Understanding Agent not called | `tests/test_replay_observation_summary.py` or import boundary checks | no Page Understanding Agent dependency | Yes | M14 / L1 only |
| boundary | raw HTML not read or stored | schema/service tests | no raw HTML / DOM dump fields in summary/ref | Yes | evidence boundary |
| boundary | `network_idle_observed` not primary | aggregation service tests | not present in `primary_signal_kinds` | Yes | supporting-only invariant |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本测试计划不要求 E2E。
- 本测试计划不要求 live UI smoke。
- 如果没有真实打开浏览器或产品 UI，不得声称已经完成 UI smoke / E2E。
- 如果只运行单元测试、API 测试或静态检查，必须明确写成“未进行浏览器验证”。
- 使用浏览器验证时，必须记录入口 URL / 页面、操作路径、截图或可复查的观察结果。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

本轮不要求 Codex / AI 作为外部测试操作员。

如果后续用户明确要求 live UI smoke，Codex / AI 只能记录自己真实执行过的动作。不得编造
内部 Agent 结论，不得把代码审查、静态推理或未执行的命令写成测试通过。

## Live Run 边界（Live Run Boundary）

本轮不运行 `verify-scenario`、autonomous run 或 product-driven browser execution。

如果后续用户明确要求 live run，必须记录：

- invocation surface。
- run_id。
- pass_gate.status。
- supervisor verdict。
- scorecard。
- 是 product UI traffic 还是 skill invocation。
- 原始输出或可复查路径。

`pass_gate.status` 是权威结果；`unverified` 不是通过。

## 后续实现验证命令

后续代码实现完成后运行：

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

cd apps/api && ../../.venv/bin/python -m pytest -q
```

要求：

- scoped tests + ruff 是硬门槛。
- full API suite 如因 sandbox Playwright 权限失败，必须记录失败原因，不能写成 PASS。
- 本轮测试计划不要求 live UI smoke / verify-scenario / autonomous run。

## Evidence Requirements

后续 `review.md` 必须记录：

- command。
- expected。
- actual result。
- exit code。
- pass count。
- fail count。
- skip count。
- not run reason。

不得写：

- `tested`。
- `E2E passed`。
- `verified`。
- `works`。

除非有实际命令和证据。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| E2E | 11.2.3 aggregation 可由 API / service tests 覆盖；本轮不改 UI。 | 不能证明 Console UI 展示 summary。 |
| Live UI smoke | 本轮不改 UI，不要求外部测试操作员。 | 不能证明浏览器路径可视化结果。 |
| `verify-scenario` | 本轮不触发 autonomous run。 | 无 live supervisor evidence。 |
| Task Result Reporter tests | 11.2.5 才接 reporter。 | 当前不能证明 reporter 已消费 summary。 |
| M12 recovery tests | M12 才处理 recovery / retry / abort。 | 当前不能证明 failure dialogue。 |
| Common Component Runtime Semantics tests | later 11.2.x 才实现。 | 当前不能证明组件库 runtime surface detection。 |
