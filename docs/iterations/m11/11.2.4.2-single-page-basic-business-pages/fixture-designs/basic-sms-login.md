# basic-sms-login Fixture Design

Status: redesign source of truth

## Business Goal

让用户通过手机号和短信验证码登录。页面要覆盖验证码获取、倒计时、验证码输入、invalid code、
loading、success 和 reset，而不模拟真实短信服务或网络异常。

## Page Anatomy

- SMS login heading and explanation。
- Phone input。
- Request code button。
- Countdown / resend status。
- Verification code input。
- Submit button。
- Secondary actions / distractors:
  - use password login link。
  - contact support link or help hint。
- Status surfaces:
  - invalid phone alert。
  - missing code alert。
  - invalid code alert。
  - countdown status。
  - loading state。
  - success panel。
- Reset control。

## Happy Path

1. User enters a valid local phone number such as `13800000000`。
2. User clicks request code。
3. Request code enters deterministic countdown。
4. User enters deterministic valid code `123456`。
5. User submits。
6. Page shows loading then success panel。

## Local Validation / Deterministic Business Failure States

- Phone missing。
- Phone format invalid。
- Code missing。
- Code not equal to deterministic valid code `123456`。
- These failures are local; do not describe them as SMS provider or backend failures。

## Loading / Pending States

- Request code disables resend while countdown is active。
- Submit disables while pending。
- Status label changes to loading during submit。
- Countdown status remains visible and deterministic。

## Success States

- Success panel appears with masked phone number。
- Result region shows login success。
- Status label changes to success。

## Secondary Actions / Distractors

- Use password login link routes locally to basic-login or reveals a local hint。
- Contact support reveals local help hint。
- No external navigation and no backend call。

## Reset Behavior

Reset must:

- clear phone。
- clear code。
- stop countdown timer。
- set resend button enabled。
- clear invalid phone / missing code / invalid code surfaces。
- hide success panel。
- stop submit timer。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-sms-phone`
- `basic-sms-request-code`
- `basic-sms-countdown`
- `basic-sms-code`
- `basic-fixture-primary-trigger`
- `basic-sms-password-login`
- `basic-sms-support`
- `basic-sms-alert`
- `basic-sms-success-panel`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP primary signals only cover route/title changes。
- Countdown, invalid code, loading, and success panel are future observation surfaces。
- `network_idle_observed` is supporting only and must not imply login success。

## Future Expected Observation

- `form_validation_message` for invalid phone / missing code / invalid code。
- `element_enabled` / `element_disabled` for resend disabled/enabled。
- `loading_finished` for submit pending。
- `toast_shown` or success surface signal if future policy supports it。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- countdown。
- success。
- reset。

## Deferred States

- weak network。
- offline。
- SMS provider failure。
- server-side error。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use deterministic phone/code rules。
- Use short deterministic countdown suitable for local smoke。
- Do not call SMS API。
- Do not simulate provider or network failure in 11.2.4.2。

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Invalid phone shows local validation。
- [ ] Request code starts countdown and disables resend。
- [ ] Missing code shows local validation。
- [ ] Invalid code shows deterministic business error。
- [ ] Valid phone/code shows loading then success。
- [ ] Reset stops countdown and restores initial state。
