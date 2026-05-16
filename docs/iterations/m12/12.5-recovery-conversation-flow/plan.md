# 12.5 Implementation Plan

状态：approved for implementation

## 输入

Implementation Agent must read these documents in order:

1. `README.md`
2. `intent.md`
3. `contract.md`
4. `technical-design.md`
5. `test-plan.md`
6. `plan.md`
7. `review.md` as read-only history

Additional context:

- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`
- 12.1 / 12.2 / 12.3 / 12.4 recovery code and tests
- M11.0 conversation schema / state / orchestrator code

## 文件 / 模块

Implementation may touch:

- `apps/api/app/schemas/recovery.py`
  - Add internal recovery conversation schema if needed.
- `apps/api/app/services/recovery/conversation_flow.py`
  - Add deterministic pure service that converts 12.1-12.4 recovery outputs into
    user-facing conversation response, event payload, and next-state suggestion.
- `apps/api/app/services/recovery/__init__.py`
  - Add package-level exports only if a new recovery conversation service entrypoint
    is created.
- `apps/api/tests/test_recovery_conversation_flow.py`
  - Add focused unit tests required by `test-plan.md`.
- `apps/api/app/services/conversation/orchestrator.py`
- `apps/api/app/services/conversation/state.py`
- `apps/api/tests/test_conversation_recovery_flow.py`
  - Touch these only if the implementation intentionally integrates the pure service
    with existing conversation runtime boundaries.

Implementation Agent must not edit iteration documents or global planning docs during
the implementation pass:

- `docs/iterations/**`
- `AGENTS.md`
- `CLAUDE.md`
- `CLAUDE.zh.md`

If implementation reveals a document conflict or missing requirement, stop and report
the blocker instead of patching the documents inside the implementation workflow.

## 步骤

1. Precheck:
   - `git status --short --branch`
   - confirm current branch is not a `-local` branch before any push
   - confirm no unrelated dirty changes block a narrow implementation
2. Read the required 12.5 documents in the input order.
3. Inspect current recovery services and conversation foundations:
   - `apps/api/app/schemas/recovery.py`
   - `apps/api/app/services/recovery/classifier.py`
   - `apps/api/app/services/recovery/abort_handler.py`
   - `apps/api/app/services/recovery/proposal.py`
   - `apps/api/app/services/recovery/retry_policy.py`
   - `apps/api/app/schemas/conversation.py`
   - `apps/api/app/services/conversation/commands.py`
   - `apps/api/app/services/conversation/state.py`
   - `apps/api/app/services/conversation/orchestrator.py`
4. Implement the pure recovery conversation service first:
   - consume structured 12.1-12.4 outputs;
   - return user-facing response, prompt/options when relevant, evidence refs,
     event payload suggestion and next-state suggestion;
   - keep the service deterministic and side-effect free.
5. Add internal schema only as needed to express the contract:
   - `RecoveryConversationInput`
   - `RecoveryConversationDecision`
   - `RecoveryConversationResponse`
   - `RecoveryConversationEventPayload`
   - `RecoveryChoicePrompt`
   - `RecoveryChoiceOption`
   - `RecoveryConversationState`
   - `RecoveryConversationReason`
6. Add focused unit tests from `test-plan.md`.
7. Touch orchestrator / state only if required after the pure service is complete.
   If touched, add limited integration tests proving event payload / state suggestions
   do not execute recovery.
8. Run required validation commands.
9. Report actual files changed, validation evidence, not-run items and remaining risk
   in the final response. Do not write implementation evidence back into
   `review.md` during the implementation workflow.

## 验证

Validation plan comes from `technical-design.md` and `test-plan.md`.

Required for pure service implementation:

| Command | Expected proof | Notes |
|---|---|---|
| `cd apps/api && .venv/bin/python -m pytest tests/test_recovery_conversation_flow.py -q` | Recovery conversation unit tests pass. | Required when pure service is implemented. |
| `cd apps/api && .venv/bin/python -m pytest tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_proposal.py tests/test_retry_policy.py tests/test_recovery_exports.py -q` | Existing recovery regressions pass. | Guards 12.1-12.4 services. |
| `cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_recovery_conversation_flow.py` | Ruff clean for touched recovery surfaces. | Add integration test file to command if created. |
| `git diff --check` | No whitespace errors. | Static check. |

Conditional if orchestrator / state integration is touched:

| Command | Expected proof | Notes |
|---|---|---|
| `cd apps/api && .venv/bin/python -m pytest tests/test_conversation_recovery_flow.py -q` | Limited conversation integration tests pass. | Required only if implementation touches conversation runtime integration. |
| `cd apps/api && .venv/bin/ruff check app/services/conversation tests/test_conversation_recovery_flow.py` | Ruff clean for touched conversation surfaces. | Required only for touched files. |

Not required for 12.5 MVP unless separately scoped:

- API tests
- CLI tests
- UI smoke
- E2E
- `verify-scenario`
- autonomous run

## 对齐清单（Implementation Checklist）

- [x] 12.5 is a code iteration.
- [x] Required iteration documents exist.
- [x] `technical-design.md` has been reviewed for implementation.
- [x] `test-plan.md` exists because 12.5 involves recovery / conversation flow.
- [x] `contract.md` states conversation flow is not execution.
- [x] `technical-design.md` maps contract requirements to implementation mechanisms
  and test entries.
- [x] `test-plan.md` defines required unit tests and conditional integration tests.
- [x] Plan is implementation-ready and does not require the implementation Agent to
  rewrite iteration documents.
