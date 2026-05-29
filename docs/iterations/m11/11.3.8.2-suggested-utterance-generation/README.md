# 11.3.8.2 · Suggested Utterance Generation

状态：PACKAGE_COMPLETE
里程碑：M11
类型：code
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)
前置包：[`11.3.8.1-learning-action-goal-preservation`](../11.3.8.1-learning-action-goal-preservation/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

## Goal

生成可复用 suggested utterances，使学习完成后的 session learned action 不再只暴露
`Learn how to ...` 这种教学句式变体，而是包含业务动作、canonical goal、useful aliases
和稳定 business object。

## Scope

本包只改 deterministic utterance generation 和 focused tests：

- learning service 根据 `business_goal` / `canonical_goal` / `action_aliases` /
  `business_object` 生成可复用 utterances。
- chat runtime 在保存 session learned action 时可用已保留的 business identity
  修正 stale wrapper utterances。
- utterances 必须排除 slot values、敏感值、URL、selector、外部站点细节和 seed data。

本包不改 matcher threshold、candidate selection、replay execution、Task Result Reporter、
eval runner、external validation result docs 或外部站点源码。

## Deliverables

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
- Focused implementation in:
  - `apps/api/app/services/learning/learning_run_service.py`
  - `apps/api/app/services/conversation/chat_runtime.py`
- Focused tests in:
  - `apps/api/tests/test_learning_run_service.py`
  - `apps/api/tests/test_conversation_chat_runtime.py`

## Implementation Gate

Code implementation is not authorized until this package `review.md` records a
read-only spec / design review decision with:

```text
implementation_authorized: yes
```

The user explicitly requested full child-package cycle mode for `11.3.8.2`, so
the design review and implementation may happen in the same `/goal` only after
the review evidence is recorded.

## Final Assessment State

Current state: `PACKAGE_COMPLETE`. Runtime implementation, focused verification,
and code/test review are recorded in `review.md`.

## Current Handoff

`11.3.8.1` is `PACKAGE_COMPLETE` and confirmed the stable metadata contract:

- `business_goal`
- `canonical_goal`
- `action_aliases`
- `business_object`
- `match_terms`

This package consumes those fields only to generate better reusable utterances.
`11.3.8.3` may now create / review its own seven-document package in a separate
goal. Do not start it from the `11.3.8.2` goal.
