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

RiskHint / ConsentRequirement
- risk_type
- reason
- requires_user_confirmation
- policy_source

PostconditionSignal
- signal_type
- expected
- source
- required

TaskExecutionResult
- status: succeeded | failed | uncertain | needs_review
- route_plan_id optional
- replay_results
- postcondition_results
- artifacts
- final_state_summary
- errors
- warnings

AgentDPlannerInput / Output
AgentEReporterInput / Output
```

## Contract rules

- 不加入 user / account / tenant 字段。
- schema module 不 import replay / autonomous / LLM modules。
- Agent D schema 只定义 planner 输入 / 输出，不实现 Agent D。
- Agent E schema 只定义 reporter 输入 / 输出，不实现 Agent E。
- artifact fields 只保留必要占位，不实现 artifact lifecycle。

## 测试计划

后续实现阶段至少覆盖：

- schema accepts minimal valid data。
- trust / status enums reject invalid values。
- route step order preserved。
- confirmation requirement required fields。
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
