# basic-register Fixture Design

Status: redesign source of truth

## Business Goal

让用户在一个业务系统中创建新账号。页面业务目标单一，但必须包含真实注册页常见字段、条款确认、
字段校验、密码确认、secondary sign-in action、loading、success panel 和 reset。

## Page Anatomy

- Register heading and short description。
- Registration form:
  - username input。
  - email input。
  - password input。
  - confirm password input。
  - terms checkbox。
  - submit button。
- Secondary actions / distractors:
  - sign in link。
  - view terms link / local terms hint。
- Status surfaces:
  - field validation alert。
  - password mismatch alert。
  - terms not accepted alert。
  - loading state。
  - success panel。
- Reset control。

## Happy Path

1. User enters username。
2. User enters syntactically valid email。
3. User enters password。
4. User enters matching confirm password。
5. User checks terms。
6. User submits。
7. Page shows deterministic loading。
8. Page shows success panel with account-created summary。

## Local Validation / Deterministic Business Failure States

- Required username/email/password/confirm password missing。
- Email format invalid。
- Password and confirm password mismatch。
- Terms checkbox not accepted。
- Optional local deterministic business error: username `taken-user` shows account name unavailable, but it must not be described as server validation。

## Loading / Pending States

- Submit disabled while pending。
- Form remains visible。
- Status label changes to loading。
- Previous errors are cleared at pending start。

## Success States

- Success panel appears with:
  - username。
  - email。
  - account created message。
- Result region shows created account status。
- Status label changes to success。

## Secondary Actions / Distractors

- Sign in link returns to `/runtime-observation/basic/login` or reveals a local hint。
- Terms link reveals local terms hint only。
- No external navigation and no backend calls。

## Reset Behavior

Reset must:

- clear all inputs。
- uncheck terms。
- clear validation errors。
- hide success panel。
- stop pending timer。
- restore submit enabled。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-register-username`
- `basic-register-email`
- `basic-register-password`
- `basic-register-confirm-password`
- `basic-register-terms`
- `basic-fixture-primary-trigger`
- `basic-register-sign-in`
- `basic-register-terms-link`
- `basic-register-alert`
- `basic-register-success-panel`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP can only observe route/title changes as primary signals。
- Same-page validation, terms errors, loading, and success panel are future observation surfaces。
- `network_idle_observed` is supporting only。

## Future Expected Observation

- `form_validation_message` for field errors。
- `loading_finished` for submit pending。
- `toast_shown` or success surface signal if future policy supports it。
- `element_enabled` / `element_disabled` for submit disabled while pending。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- success。
- reset。

## Deferred States

- weak network。
- offline。
- server-side error。
- email already exists from backend。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use frontend-local state only。
- Do not call registration API。
- Do not model real email verification。
- Keep `taken-user` optional and local if implemented。

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Empty form shows required validation。
- [ ] Invalid email shows email error。
- [ ] Password mismatch shows mismatch error。
- [ ] Missing terms acceptance shows terms error。
- [ ] Valid form shows loading then success panel。
- [ ] Reset restores deterministic initial state。
