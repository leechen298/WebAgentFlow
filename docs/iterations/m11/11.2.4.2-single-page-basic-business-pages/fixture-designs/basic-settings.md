# basic-settings Fixture Design

Status: redesign source of truth

## Business Goal

让用户修改一个简单设置页并保存。页面要覆盖至少两个设置控件、dirty state、save disabled until changed、
local warning、saving、saved state、reset changes 和 stable anchors。

## Page Anatomy

- Settings heading and description。
- Settings controls:
  - enable notifications toggle。
  - digest frequency radio/select。
  - optional quiet hours checkbox。
- Status surfaces:
  - dirty state badge。
  - local warning surface。
  - saving indicator。
  - saved status。
- Actions:
  - save。
  - reset changes。
  - secondary safe action / distractor such as preview settings。

## Happy Path

1. Initial controls match default values。
2. Save button is disabled while unchanged。
3. User changes at least one setting。
4. Dirty state appears and save becomes enabled。
5. User clicks save。
6. Page shows deterministic saving。
7. Page shows saved state and dirty state clears。

## Local Validation / Deterministic Business Failure States

- If notifications are disabled while digest frequency is still daily, show local warning asking user to confirm preference。
- If quiet hours are enabled without notifications, show local warning。
- These are local deterministic warnings, not backend save failures。

## Loading / Pending States

- Save button disabled while saving。
- Controls may remain visible。
- Status label changes to loading。
- Previous saved state clears at saving start。

## Success States

- Saved status appears。
- Dirty state clears。
- Result region shows settings saved。
- Status label changes to success。

## Secondary Actions / Distractors

- Preview settings reveals local preview hint。
- It must not call backend and must not navigate outside validation-site。

## Reset Behavior

Reset must:

- restore all controls to initial values。
- clear dirty state。
- disable save button。
- clear warnings。
- hide saved state。
- stop saving timer。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-settings-notifications`
- `basic-settings-frequency`
- `basic-settings-quiet-hours`
- `basic-settings-dirty-state`
- `basic-settings-warning`
- `basic-fixture-primary-trigger`
- `basic-settings-preview`
- `basic-settings-saved`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP has no same-page setting-change primary signal。
- `network_idle_observed` may appear as supporting only。
- Dirty state, warning, save disabled/enabled, and saved state are future observation surfaces。

## Future Expected Observation

- `element_enabled` / `element_disabled` for save button。
- `form_validation_message` or warning surface signal for local warning。
- `loading_finished` for saving pending。
- `toast_shown` or saved surface signal if future policy supports it。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- dirty state。
- success。
- reset。

## Deferred States

- weak network。
- offline。
- real server save failure。
- backend business conflict。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use frontend-local settings object。
- Do not call settings API。
- Keep save disabled until dirty。
- Local warning may still allow save if design says warning only; document exact behavior in implementation review。

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Initial save is disabled。
- [ ] Changing a setting shows dirty state and enables save。
- [ ] Warning surface appears for invalid local combination。
- [ ] Save shows loading then saved。
- [ ] Reset restores defaults and disables save。
