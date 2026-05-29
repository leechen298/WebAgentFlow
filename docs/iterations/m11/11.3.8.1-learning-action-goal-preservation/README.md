# 11.3.8.1 · Learning Action Goal Preservation

状态：implementation_complete_pending_followup
里程碑：M11
类型：code
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包是 11.3.8 recovery sequence 的第一个可执行代码包。文档 / 设计 review 已完成；
实现和 P1 review fix 已按本包范围完成。后续 reusable utterance generation、matcher
consumption、cross-chain regression 和 external black-box revalidation 仍由后续
11.3.8.x packages 负责。

## Goal

学习完成后，session learned action metadata 必须保留 intake 中的可复用业务目标：
`action.goal`、`canonical_goal`、useful aliases 和 business object / match terms。
主要 action identity 不应退化为 `Learn how to create` 这类教学包装句式。

## Scope

允许后续实现触及：

- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/intake.py` only if a small helper is needed to reuse existing intake action terms
- `apps/api/app/schemas/conversation_intake.py` only if the reviewed design requires an optional backward-compatible field
- focused tests in `apps/api/tests/test_learning_run_service.py` and `apps/api/tests/test_conversation_chat_runtime.py`
- this package's `review.md`

禁止本包触及：

- matcher policy beyond preserving richer session action metadata
- suggested utterance generation beyond keeping existing utterance behavior compatible
- external black-box validation result docs
- runtime routes, frontend, fixture sites, migrations, worker code, or autonomous-run endpoints
- target-specific constants such as `5177/inventory`, selectors, `data-testid`, seed data, field labels, or external site source

## Deliverables

- `README.md` - package index, status, scope, deliverables, and handoff.
- `intent.md` - problem, why now, roadmap relationship, non-goals, and expected handoff.
- `contract.md` - learned action identity metadata contract and compatibility boundaries.
- `technical-design.md` - implementation structure, affected files, data flow, anti-drift rules, and test entries.
- `test-plan.md` - exact documentation and later implementation verification commands.
- `plan.md` - ordered execution steps, phase boundaries, stop conditions, and review update step.
- `review.md` - documentation, implementation, verification, and follow-up record.

## Final Assessment State

Implementation complete for this package scope, including focused runtime tests and P1 review fix.
No CLI smoke, UI smoke, `verify-scenario`, autonomous run, or external black-box validation has been
completed by this package. `PV-CLI-003` is not claimed fixed / passed / verified here.

## Assumptions

- The failure baseline remains the 2026-05-25 external black-box result and PV-CLI-003 triage.
- `ConversationIntakeResult.action.goal`, `canonical_goal`, and `aliases` are available at or near the learning completion boundary.
- Session learned action metadata can accept additional JSON keys without a DB migration.
- Later packages 11.3.8.2 and 11.3.8.3 will consume the preserved identity; this package does not finish end-to-end matching.

## Open Risks

- Later packages must still consume the preserved metadata; 11.3.8.3 owns matcher consumption.
- Suggested utterance quality remains unchanged and belongs to 11.3.8.2.
- External black-box validation remains unverified until 11.3.8.5 reruns it through its own evidence path.
- Existing sessions without the new optional metadata remain compatible, but they do not retroactively gain business identity fields.
