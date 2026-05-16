# basic-login Fixture Design

Status: redesign source of truth

## Business Goal

让用户通过账号密码登录一个业务系统。页面业务目标单一，但页面必须像真实登录页：包含主登录流程、
辅助链接、错误面、loading、success panel、reset 和干扰元素。

## Page Anatomy

- Brand / product heading: `WebAgentFlow Business Portal`。
- Login form card:
  - username input。
  - password input。
  - remember me checkbox。
  - primary submit button。
- Secondary actions / distractors:
  - forgot password link。
  - contact admin link。
  - switch account link or help text。
- Status surfaces:
  - local validation alert。
  - invalid credentials alert。
  - loading indicator on submit。
  - success panel after deterministic success。
- Reset control。

## Happy Path

1. User enters `demo.operator` as username。
2. User enters `correct-password` as password。
3. User optionally checks remember me。
4. User clicks submit。
5. Page enters loading / pending for a deterministic short timer。
6. Page shows success panel with signed-in identity and session summary。

## Local Validation / Deterministic Business Failure States

- Required username missing -> required field alert。
- Required password missing -> required field alert。
- Username/password pair not equal to deterministic valid pair -> invalid credentials alert。
- These failures are local deterministic business states, not HTTP 401 / 403.

## Loading / Pending States

- Submit button disabled while pending。
- Button label changes to signing-in text。
- Status label changes to loading。
- Existing error/success surfaces are cleared at pending start。

## Success States

- Success panel appears with:
  - signed-in username。
  - remember me state。
  - short session-ready message。
- Status label changes to success。
- Result region contains success message。

## Secondary Actions / Distractors

- Forgot password link opens or reveals a local help hint only。
- Contact admin link opens or reveals local support hint only。
- These actions must not navigate outside validation-site or call backend。

## Reset Behavior

Reset must:

- clear username。
- clear password。
- uncheck remember me。
- clear required-field and invalid-credentials alerts。
- hide success panel。
- stop pending timer。
- restore submit enabled。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-login-username`
- `basic-login-password`
- `basic-login-remember-me`
- `basic-fixture-primary-trigger`
- `basic-login-forgot-password`
- `basic-login-contact-admin`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`
- `basic-login-alert`
- `basic-login-success-panel`

## Current MVP Expected Observation

- Current MVP may observe `title_changed` or `url_changed` only if route/title changes。
- Same-page validation, invalid credentials, loading, and success panel are future observation surfaces。
- `network_idle_observed` may appear only as supporting evidence and must not be treated as business success。

## Future Expected Observation

- `form_validation_message` for required field and invalid credentials surfaces。
- `loading_finished` for submit pending -> success/error。
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
- HTTP 401 / 403。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use frontend-local state only。
- Use deterministic valid credentials。
- Do not call auth API。
- Do not route to dashboard on success; keep success visible on the page。
- Keep secondary actions local and non-navigating unless they route within validation-site.

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Empty submit shows required field alert。
- [ ] Wrong credentials show invalid credentials。
- [ ] Valid credentials show loading then success panel。
- [ ] Remember me state is visible in success panel or status。
- [ ] Forgot password / contact admin do not call backend。
- [ ] Reset restores deterministic initial state。
