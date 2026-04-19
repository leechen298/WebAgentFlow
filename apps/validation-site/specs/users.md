# Page Verification Spec · User Directory

**Location**: `apps/validation-site/src/pages/UserDirectoryPage.vue`
**Route**: `/users`
**Backend**: `GET /validation-api/users` (+ `/users/meta/options`, `/users/{id}`)

This document is the authored baseline for autonomous exploration on
the second validation-site fixture. Like the login spec, it is NOT
derived from any autonomous-run output — authored first, compared
against later.

---

## 1. Page Goal

Let an operator filter a list of seeded users by several common
business-table controls and view details of one row. The page is
deliberately dense so the engine gets exercised against the shape of
a real enterprise listing page, not a toy search input.

The **primary task** covered by this spec is:
**fill one filter field → click Search → read the filtered table**.
Detail-panel interactions and multi-control workflows are out of
scope for the Phase 9 gate (see §7).

## 2. Key Regions

| Region | DOM | Notes |
|---|---|---|
| Name input | `<input id="search-name">` | Primary fillable for this spec's scenarios |
| Email input | `<input id="search-email">` | Present; scenarios do not use it |
| Role select | `<select id="search-role">` (Ant Design select) | Present; scenarios do not use it |
| Status radio group | `<input type=radio>` siblings under `#search-status` | Present; scenarios do not use it |
| Registered from / to | `<input id="search-registered-from">`, `<input id="search-registered-to">` | Ant Design DatePicker — opens a popup panel on click |
| Registered range | Ant Design RangePicker at `#search-registered-range` | Popup panel |
| Region Cascader | Ant Design Cascader at `#search-region` | Popup tree |
| Month picker | `#search-month` (Ant Design MonthPicker) | Popup panel. Filters by registration month (backend query param `month=YYYY-MM`). |
| Department tag filter | `<span class="ant-tag tag-filter">` cluster | Click-to-toggle pills. Filters by user department (backend `department=<comma-sep>`). |
| Search button | `<button id="btn-search" type="submit">` | Primary submit; should be chosen over Reset and the per-row View buttons |
| Reset button | `<button id="btn-reset">` | Distraction — clears form state, should never be clicked during a filter task |
| Per-row View buttons | `<button class="btn-view-row" data-user-id="…">` (one per table row) | Distraction for filter tasks — operates on a single row, not on the filter |
| Results table | `<table>` with columns Name / Email / Role / Status / Registered / Department / Actions | Column headers carry sort / filter affordances (popup-style) |

## 3. Key Actions (Phase 9 scope)

The correct action path for the Phase 9 scenarios is:

1. **fill** one or more text inputs (Name and/or Email)
2. **click** the Search button

That's it. No popup controls, no Tag toggling, no per-row View.

## 4. Success Criteria

For a filter scenario the run is correct when, after Search:

- The URL query includes the filter that was applied (e.g.
  `?name=alice` after typing "alice" in Name)
- The table shows only matching rows (or the empty-state text
  `No users found`)
- The Reset button has NOT been clicked
- No per-row View button has been clicked

For `no_match` specifically:
- The URL carries the filter value that produced zero results
- The empty-state text `No users found` is visible
- The page is still `/users` (no transition away)

## 5. Out-of-scope for this spec (deferred to Phase 10)

The following belong to the fixture UI but **do not have scenarios in
this round** because the engine doesn't support their interaction
shape yet:

- Cascader (`#search-region`) — popup tree, click-through-layers
- DatePicker (`#search-registered-from` / `#search-registered-to`),
  RangePicker, MonthPicker — all popup panels (the backend DOES honor
  the resulting query params, it's the engine's popup-operation
  capability that is missing)
- Tag-as-filter department pills — click-to-toggle on span-like tags
- Table column sort (clickable header arrow, popup-less but still not
  a standard form control)
- Table column filter (clickable header funnel, opens a popup menu)

When Phase 10 lands popup-surface support in `page_analyzer` +
`action_planner`, these controls get Tier 2 scenarios backfilled into
`users.assertions.json`. Until then, the analyzer will still see
these elements (the DOM is there on initial render) — we just don't
assert on them.

## 6. Distractions

Elements that must **not** be chosen as the primary submit during a
filter task:

- `#btn-reset` (Reset button)
- Any `.btn-view-row` (per-row View buttons — there's one per table
  row, which also tests that the planner doesn't get confused by
  N distinct buttons all of which are plausible clicks)

## 7. Expected Coverage Scope

Phase 1 of this spec enforces:

1. **`filter_by_name`** — a single text filter + Search,
   expected verdict `success`.
2. **`no_match`** — a text filter that returns zero rows,
   expected verdict still `success` (the empty-state IS a valid
   outcome for a search that was performed correctly, even when it
   yields zero hits).

Out of scope:

- Any scenario operating a popup-based control (Phase 10).
- Multi-control combination scenarios (Phase 10).
- Column sort / filter interactions (Phase 10).
- The View detail panel flow (later).

---

## Notes for the Spec Author

- As with the login spec: this is authored **before** any autonomous
  run against `/users`. If a run disagrees with this spec, the
  default assumption is the system is wrong, not the spec. Patch the
  system.
- The JSON equivalent in `users.assertions.json` is the source of
  truth for the comparator.
- When Phase 10 backfills Tier 2 scenarios, this markdown should
  update §7 to reflect the new coverage.
