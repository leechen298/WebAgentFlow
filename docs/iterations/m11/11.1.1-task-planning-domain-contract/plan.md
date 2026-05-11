# 实施计划

## 触及的文件 / 模块

后续实现阶段预计触及：

- `apps/api/app/schemas/task_planning.py`
- `apps/api/tests/test_task_planning_schemas.py`
- `docs/iterations/m11/11.1.1-task-planning-domain-contract/review.md`

本轮只写文档，不创建以上代码 / 测试文件。

## 建议 schema

```text
TaskInput
- raw_text
- locale optional
- metadata

TaskIntent
- raw_text
- normalized_goal optional
- normalization_source optional: none | deterministic | agent_d
- target_page_hint optional
- scenario_hint optional
- required_outputs
- constraints
- uncertainty

LearnedPathCandidate
- learned_path_id
- scenario
- page_template
- trust
- hit_count
- match_reasons
- warnings
- drift_evidence_summary optional
- negative_evidence_summary optional

RoutePlan
- id optional
- task_intent
- steps
- confirmation_required
- risk_hints
- postconditions
- uncertainty

RouteStep
- order
- learned_path_id
- purpose
- bound_slots
- expected_result
- can_execute
- warnings

SlotBindingProposal
- slot_name
- source_text
- target_action_index optional
- target_field optional
- proposed_value
- confidence
- requires_confirmation

ConfirmationRequirement
- reason
- message
- fields
- severity
- linked_risk_ids

RiskHint
- id optional
- risk_type
- reason
- severity
- policy_source optional

ConsentRequirement
- reason
- message
- fields
- severity
- linked_risk_ids
- requires_user_confirmation
- policy_source

PostconditionSignal
- signal_type
- expected
- source
- required

TaskExecutionResult
- status: succeeded | failed | uncertain | needs_review
- failure_stage optional: planning | confirmation | replay | verification | artifact | unknown
- failure_reason optional
- route_plan_id optional
- replay_results
- postcondition_results
- artifacts
- final_state_summary
- errors
- warnings

ArtifactReference
- kind
- label
- uri optional
- status
- metadata

AgentDPlannerInput / Output
- input includes TaskIntent, LearnedPathCandidate list, SlotBindingProposal list,
  negative / replay evidence summaries.
- output includes RoutePlan, ConfirmationRequirement list, RiskHint list,
  uncertainty, warnings.

AgentEReporterInput / Output
- input includes TaskExecutionResult, PostconditionSignal results,
  ArtifactReference placeholders, warnings, final state evidence.
- output includes status, user-facing summary, evidence summary, uncertainty,
  warnings, next suggested action optional.
```

11.1.1 的 schema 类名可以保留 `AgentD` / `AgentE` 前缀以保持连续性；
面向用户和后续文档时优先使用 Task Path Planner / Task Result Reporter。

## Contract rules

- 不加入 user / account / tenant 字段。
- schema module 不 import replay / autonomous / LLM modules。
- `TaskIntent.raw_text` 是不可丢失原始输入；`normalized_goal` 是 optional，
  后续可由 deterministic normalizer 或 Task Path Planner / 任务路径规划器填充
  （legacy: Agent D）。本包只定义
  `normalization_source` contract，不实现 normalizer。
- `RiskHint` 和 `ConsentRequirement` 分离：前者表示风险信号，后者表示执行前
  必须获得用户确认的门槛。risk / consent policy engine 属于 11.1.5。
- `TaskExecutionResult.status` 不拆 replay failure / verification failure；
  失败来源通过 `failure_stage` 和 `failure_reason` 表达。
- Task Path Planner / 任务路径规划器 schema 定义相对完整的 planner 输入 /
  输出 contract（legacy: Agent D），但不定义 prompt，不实现 Task Path Planner，
  不调用 LLM provider。
- Task Result Reporter / 任务结果汇报器 schema 定义相对完整的 reporter 输入 /
  输出 contract（legacy: Agent E），但不定义 prompt，不实现 Task Result Reporter，
  不调用 LLM provider。
- artifact fields 只保留 `ArtifactReference` 占位，不实现 artifact lifecycle。

## 测试计划

后续实现阶段至少覆盖：

- schema accepts minimal valid data。
- trust / status enums reject invalid values。
- route step order preserved。
- confirmation requirement required fields。
- `TaskExecutionResult.failure_stage` rejects invalid values。
- AgentD / AgentE contract accepts complete minimal input / output data。
- `ArtifactReference` accepts minimal placeholder data without lifecycle behavior。
- no user / account / tenant fields。
- schema module does not import replay / autonomous / LLM modules。

## 验证

当前文档阶段：

```bash
git diff --check
```

后续实现阶段：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_schemas.py
cd apps/api && ../../.venv/bin/ruff check app/schemas/task_planning.py tests/test_task_planning_schemas.py
git diff --check
```
