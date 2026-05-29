# 11.3.8.3 · Learned Action Matching Improvement

状态：ready_for_implementation
里程碑：M11
类型：code
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)
前置包：

- [`11.3.8.1-learning-action-goal-preservation`](../11.3.8.1-learning-action-goal-preservation/)
- [`11.3.8.2-suggested-utterance-generation`](../11.3.8.2-suggested-utterance-generation/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

## Goal

让执行阶段能用已学 action 的 `business_goal`、`canonical_goal`、
`business_object`、`match_terms`、aliases 和 reusable utterances 匹配同一业务动作，
同时继续保护低置信度、泛化动词和多候选场景。

## Scope

本包只改 current-session learned action binding：

- 扩展 chat runtime action matching 的 action-side terms。
- 保持 target URL / site origin / page template scope 不变。
- 保持 replay execution、reporter、recovery、abort、learning、suggested utterance generation
  不变。
- 必要时同步 router known-action counting，使 router context 与 runtime matcher 对齐。

本包不做 external black-box revalidation；`PV-CLI-003` 只能在 `11.3.8.5` 真实重跑后
更新为 pass / fail / blocked / unverified。

## Deliverables

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
- Focused matcher implementation in:
  - `apps/api/app/services/conversation/chat_runtime.py`
  - `apps/api/app/services/conversation/router_agent.py` only if required for known-action counting alignment
- Focused tests in:
  - `apps/api/tests/test_conversation_chat_runtime.py`
  - `apps/api/tests/test_conversation_router_agent.py` only if router counting changes

## Implementation Gate

Code implementation is not authorized until this package `review.md` records a
read-only spec / design review decision with:

```text
implementation_authorized: yes
```

This package may proceed to implementation only after read-only design review
records no unresolved P0 / P1 findings and `review.md` records
`implementation_authorized: yes`. The current read-only review request does not
itself authorize code edits.

## Subagent Requirement

Because this is `/goal` campaign work, subagents are required by default.

Required subagent checkpoints for this package:

- Design review: spec / contract reviewer and safety / evidence reviewer.
- Code closeout: code / test reviewer and evidence / scope reviewer.

Subagent reports are advisory until the parent agent reviews, verifies, and
integrates them.

## Current Handoff

`11.3.8.1` preserved stable session action identity metadata.
`11.3.8.2` generated deterministic reusable utterances. This package consumes
those fields for matching but must not compensate for missing metadata with broad
fuzzy thresholds or target-specific constants.

If this package reaches `PACKAGE_COMPLETE`, `11.3.8.4-regression-tests` may
create / review its own seven-document package and add target-agnostic
regression coverage.
