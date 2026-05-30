# 11.3.8.6 · Slot Alias & Form Binding Fix

状态：PACKAGE_COMPLETE
里程碑：M11
类型：code / validation-repair
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)
前置包：

- [`11.3.8.3-learned-action-matching-improvement`](../11.3.8.3-learned-action-matching-improvement/)
- [`11.3.8.4-regression-tests`](../11.3.8.4-regression-tests/)
- [`11.3.8.5-external-black-box-revalidation-closeout`](../11.3.8.5-external-black-box-revalidation-closeout/)

## Iteration Type

- [ ] Documentation-only
- [x] Code / tests
- [x] Validation repair

## Goal

Fix the `11.3.8.5` live validation failure where WAgent now matches the learned
`create inventory item` action, but replay is blocked by incompatible slot names
and the learned path may bind business values to the wrong form fields.

## Triggering Evidence

`11.3.8.5` live session:

- session: `3f1d42c9-9c6a-4198-8e27-e59b1be2f270`
- learned run: `ce807dfd-614f-4d87-9e02-f6e13772ec07`
- `PV-CLI-003`: `chat_execution_failed`
- failure reason: `unsupported_value_slot`
- unsupported slots: `name`, `category`, `record_quantity`

This means `11.3.8.3` fixed learned-action matching, but the full
learn-then-execute path still needs target-agnostic slot compatibility and
field-binding hardening.

## Scope

Allowed:

- Target-agnostic action-planner field binding improvements.
- Target-agnostic chat slot alias compatibility for replay slot overrides.
- Focused tests proving learned slot names and execute-turn aliases align.
- Focused tests proving create-like multi-field planning does not fill search
  controls when exact create-form labels exist.
- 11.3.8 docs / review updates and rerun evidence.

Forbidden:

- Hardcoding `<fixture-port>`, `/target-page`, inventory item labels, selectors, seed copy,
  button text, or Fixture-Site implementation details in product runtime or
  prompts.
- Direct autonomous-run endpoint calls.
- Direct replay API evidence as WAgent pass evidence.
- External Fixture-Site source edits.
- PASS wording without rerunning approved live validation.

## Handoff

Implementation may start only after design / safety review records no P0 / P1
findings and `review.md` sets `implementation_authorized: yes`.
