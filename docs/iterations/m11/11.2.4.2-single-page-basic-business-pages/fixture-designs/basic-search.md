# basic-search Fixture Design

Status: redesign source of truth

## Business Goal

让用户在一个简单业务对象集合中搜索记录。页面要像真实搜索页：包含 query、简单 filter、搜索、
清空筛选、loading、结果列表、结果数、empty state、secondary action / distractor 和 reset。

## Page Anatomy

- Search heading and description。
- Search controls:
  - query input。
  - category or status filter。
  - search button。
  - clear filters button。
- Secondary actions / distractors:
  - saved searches link / local hint。
  - export placeholder button disabled or local hint。
- Result surface:
  - loading indicator。
  - result count。
  - result list。
  - empty state。
- Reset control。

## Happy Path

1. User enters query such as `alpha`。
2. User chooses category/status filter。
3. User clicks search。
4. Page shows deterministic loading。
5. Page shows result count and list。

## Local Validation / Deterministic Business Failure States

- Empty query can show a local hint asking for keyword or can search all if explicitly documented。
- Query `empty` must show deterministic empty result。
- Invalid filter combination, if present, shows local warning only。
- No real API search failure in 11.2.4.2。

## Loading / Pending States

- Search button disabled while loading。
- Result list cleared or marked stale at pending start。
- Status label changes to loading。

## Success States

- Result list appears。
- Result count appears。
- Result region describes query and filter。
- Status label changes to success。

## Secondary Actions / Distractors

- Clear filters resets query/filter/results to initial search state。
- Saved searches or export placeholder may reveal local hint but must not call backend or download files。

## Reset Behavior

Reset must:

- clear query。
- restore filter default。
- clear results。
- hide empty state。
- stop loading timer。
- clear local warnings。
- set status to idle。

## Stable Anchors

- `basic-fixture-heading`
- `basic-search-query`
- `basic-search-category-filter`
- `basic-fixture-primary-trigger`
- `basic-search-clear-filters`
- `basic-search-secondary-action`
- `basic-search-loading`
- `basic-search-result-count`
- `basic-search-result-list`
- `basic-search-empty`
- `basic-fixture-status`
- `basic-fixture-result`
- `basic-fixture-reset`

## Current MVP Expected Observation

- Current MVP has no primary same-page list-change signal。
- `network_idle_observed` may appear as supporting evidence only。
- Result list and empty state are future observation surfaces。

## Future Expected Observation

- `loading_finished` for search pending。
- `list_changed` for result refresh。
- `form_validation_message` for local query/filter warning。
- `element_enabled` / `element_disabled` for search disabled while loading。

## In-scope States

- happy path。
- local validation / deterministic business failure。
- loading / pending。
- empty result。
- success。
- reset。

## Deferred States

- weak network。
- offline。
- search API 500。
- server-side error。
- retry / recovery / abort。
- user takeover。

## Implementation Notes

- Use a fixed local dataset。
- Query `empty` should deterministically return no rows。
- Do not call search API。
- Do not implement actual export/download。

## Business Density Checklist

- [ ] Has a clear primary business goal.
- [ ] Has at least one secondary action or distractor.
- [ ] Has at least one local error / validation state.
- [ ] Has loading / pending state.
- [ ] Has success state.
- [ ] Has reset behavior.
- [ ] Has stable anchors.

## Acceptance Checklist

- [ ] Search with normal query shows loading then result count/list。
- [ ] Search with `empty` shows empty state。
- [ ] Clear filters restores query/filter/results。
- [ ] Secondary action does not call backend。
- [ ] Reset restores deterministic initial state。
