# basic-confirm Fixture Design

Status: redesign source of truth

## Business Goal

让用户执行一个需要确认的简单业务操作。页面要覆盖 primary action、confirm surface、cancel、
confirm、pending after confirm、success status、secondary safe action / distractor 和 reset。

## Page Anatomy

- Confirm action heading and risk description。
- Summary card describing the object/action。
- Primary action button。
- Secondary safe action / distractor:
  - view details。
  - download preview placeholder or local hint。
- Confirm surface:
  - confirmation message。
  - cancel button。
  - confirm button。
- Status surfaces:
  - pending after confirm。
  - success status。
  - cancel state / returned-to-idle hint if useful。
- Reset control。

## Happy Path

1. User sees action summary。
2. User clicks primary action。
3. Confirm surface appears。
4. User clicks confirm。
5. Page shows deterministic pending state。
6. Page shows success status。

## Local Validation / Deterministic Business Failure States

- User clicks cancel in confirm surface。
- Confirm surface closes and page returns to idle。
- Optional local warning if user tries primary action while pending, but no backend failure.

## Loading / Pending States

- Confirm button disabled while pending。
- Primary action disabled while pending。
- Status label changes to loading。
- Confirm surface may remain visible or collapse after confirm, but behavior must be deterministic。

## Success States

- Success panel or status appears。
- Result region shows action confirmed。
- Status label changes to success。
- Primary action may become disabled after success until reset。

## Secondary Actions / Distractors

- View details reveals local details panel or hint。
- It must not navigate outside validation-site。
- It must not call backend。

## Reset Behavior

Reset must:

- close confirm surface。
- clear pending state。
- clear success state。
- restore primary action enabled。
- clear secondary details hint。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-confirm-summary`
- `basic-fixture-primary-trigger`
- `basic-fixture-secondary-trigger`
- `basic-confirm-surface`
- `basic-confirm-cancel`
- `basic-confirm-confirm`
- `basic-confirm-pending`
- `basic-confirm-success`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP has no same-page confirm-surface primary signal。
- Confirm surface, pending, and success status are future observation surfaces。
- `network_idle_observed` is supporting only。

## Future Expected Observation

- `modal_opened` for confirm surface。
- `loading_finished` for confirm pending。
- `toast_shown` or success surface signal if future policy supports it。
- `element_enabled` / `element_disabled` for buttons while pending。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- confirm cancel。
- success。
- reset。

## Deferred States

- weak network。
- offline。
- server-side error。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use frontend-local action state only。
- Do not call mutation API。
- Do not implement real destructive behavior。
- Keep confirm/cancel deterministic and visible.

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Primary action opens confirm surface。
- [ ] Cancel closes confirm and returns idle。
- [ ] Confirm shows pending then success。
- [ ] Secondary action stays local。
- [ ] Reset restores initial state。
