# basic-detail Fixture Design

Status: redesign source of truth

## Business Goal

让用户查看一个简单业务对象详情并刷新详情数据。页面要包含 summary card、metadata fields、refresh、
load missing item、not found state、loading、secondary action / distractor 和 reset。

## Page Anatomy

- Detail heading and object status badge。
- Summary card:
  - object id。
  - object name。
  - owner。
  - last updated。
  - simple status。
- Metadata section:
  - created date。
  - category。
  - source。
- Actions:
  - refresh detail。
  - load missing item。
  - secondary action / distractor such as copy id or view audit note。
- Status surfaces:
  - loading indicator。
  - not found state。
  - refreshed success surface。
- Reset control。

## Happy Path

1. Page starts with detail summary visible。
2. User clicks refresh detail。
3. Page shows deterministic loading。
4. Page shows refreshed metadata and success status。

## Local Validation / Deterministic Business Failure States

- User clicks load missing item。
- Page shows deterministic loading。
- Page shows local not-found state。
- This is not a real HTTP 404。

## Loading / Pending States

- Refresh and load missing buttons disabled while loading。
- Status label changes to loading。
- Previous success/not-found surfaces are cleared at pending start。

## Success States

- Refreshed detail card appears with changed deterministic fields。
- Result region shows detail refreshed。
- Status label changes to success。

## Secondary Actions / Distractors

- Copy id or view audit note reveals local hint。
- It must not write clipboard unless explicitly designed and approved in a later browser smoke。
- It must not call backend。

## Reset Behavior

Reset must:

- restore initial detail summary。
- restore initial metadata fields。
- hide not-found state。
- clear refreshed success state。
- stop pending timer。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-detail-summary-card`
- `basic-detail-metadata`
- `basic-fixture-primary-trigger`
- `basic-fixture-secondary-trigger`
- `basic-detail-distractor`
- `basic-detail-loading`
- `basic-detail-not-found`
- `basic-detail-success`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP may observe route/title changes only as primary signals。
- Same-page detail refresh and not-found are future observation surfaces。
- `network_idle_observed` is supporting only。

## Future Expected Observation

- `loading_finished` for refresh / load missing。
- `text_appeared` or equivalent future signal for refreshed metadata。
- `form_validation_message` is not expected for this page unless future policy defines not-found surfaces that way。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- success。
- not found。
- reset。

## Deferred States

- weak network。
- offline。
- real HTTP 404。
- server-side error。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use fixed initial and refreshed local records。
- Load missing item must be deterministic。
- Do not call detail API。
- Do not simulate server 404 in 11.2.4.2。

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Initial summary card and metadata are visible。
- [ ] Refresh shows loading then refreshed detail。
- [ ] Load missing shows loading then not-found。
- [ ] Secondary action does not call backend。
- [ ] Reset restores initial detail。
