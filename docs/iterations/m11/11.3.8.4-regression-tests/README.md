# 11.3.8.4 · Regression Tests

状态：ready_for_design_review
里程碑：M11
类型：code
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)
前置包：

- [`11.3.8.1-learning-action-goal-preservation`](../11.3.8.1-learning-action-goal-preservation/)
- [`11.3.8.2-suggested-utterance-generation`](../11.3.8.2-suggested-utterance-generation/)
- [`11.3.8.3-learned-action-matching-improvement`](../11.3.8.3-learned-action-matching-improvement/)

## Iteration Type

- [ ] Documentation-only
- [x] Code / tests
- [ ] Mixed

## Goal

把 11.3.8.1 metadata preservation、11.3.8.2 reusable utterances、11.3.8.3
matcher consumption 串成 repo-local automated regression，证明 learn business
action 后 execute same business action with new values 可以进入 replay handoff。

## Scope

本包只增加 target-agnostic regression tests 和必要的 test helper cleanup：

- synthetic target URL；
- fake intake / learning / replay handlers；
- current-session learned action metadata；
- replay handoff / slot override assertions；
- negative / ambiguous / generic guard coverage。

本包不修改 runtime behavior，除非 design review 明确发现缺少 test seam 且更新本包
technical design。

## Deliverables

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
- Focused regression tests in one or more of:
  - `apps/api/tests/test_learning_run_service.py`
  - `apps/api/tests/test_conversation_chat_runtime.py`
  - `apps/api/tests/test_conversation_router_agent.py`

## Implementation Gate

Code / test changes are not authorized until this package `review.md` records:

```text
implementation_authorized: yes
```

That authorization requires read-only design / safety review with no unresolved
P0 / P1 findings.

## Subagent Requirement

Because this is `/goal` campaign work, subagents are required by default.

Required checkpoints:

- Design review: spec / regression reviewer and safety / evidence reviewer.
- Closeout review: test / coverage reviewer and evidence / scope reviewer.

Subagent outputs are advisory; the parent agent must verify and integrate.

## Handoff

If this package reaches `PACKAGE_COMPLETE`, `11.3.8.5-external-black-box-revalidation-closeout`
may create its validation package. Live validation still requires explicit user
approval fields from parent `CURRENT_STATE.md`.
