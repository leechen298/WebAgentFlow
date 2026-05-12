# AUI-01 · LearnedPath Catalog Visual UI

## Purpose

Use an Agent-operated browser to verify that the LearnedPath catalog remains
usable as an operator surface: the page opens, the catalog list or empty state is
visible, the trust filter can be operated, a LearnedPath detail drawer can be
opened when seeded data exists, and the drawer exposes the replay section
without triggering a live autonomous run.

This is Agent-operated UI exploratory evidence. It is not deterministic E2E,
API-only exploratory, component testing, or a live autonomous run.

## Scope

Target page:

- `http://127.0.0.1:5174/exploration/learned-paths`

Primary evidence report:

- `docs/testing/results/YYYY-MM-DD-learned-path-catalog-visual-ui-exploratory.md`

The report may record `BLOCKED` for drawer-specific cases when there are no
LearnedPath rows available. Do not replace browser evidence with API output or
headless Playwright output.

## Target Pages

| Area | URL |
| --- | --- |
| LearnedPath catalog | `http://127.0.0.1:5174/exploration/learned-paths` |

## Preconditions

Before browser operation, record:

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5174/exploration/learned-paths
```

Recommended data precondition for drawer cases:

- At least one LearnedPath row exists in the catalog.
- Deterministic E2E seed data is acceptable if already present.
- If no row exists, mark `LPC-003` and `LPC-004` as `BLOCKED` with the visible
  empty state as evidence.

If the console or API is unreachable, mark affected cases `BLOCKED`. Do not
modify product code, seed data, package scripts, or iteration docs to make the
visual run pass.

## Allowed Tools

- Codex Browser panel / in-app browser.
- Claude Code Browser Use / Computer Use.
- Other browser-capable agents.
- Headed Playwright only when used as a visible browser observation tool.

## Forbidden Actions

- Do not call `/exploration/autonomous-runs`.
- Do not call `/exploration/autonomous-runs/stream`.
- Do not import or run the autonomous explorer directly.
- Do not use `verify-scenario`.
- Do not use an LLM provider.
- Do not click replay if the goal is only replay section presence.
- Do not click trust mutation actions such as confirm, mark flaky, or deprecate.
- Do not edit product code, E2E specs, package scripts, or iteration docs.
- Do not claim PASS without actual browser-visible evidence.

## Cases

### LPC-001 · Catalog page renders list or empty state

Target URL:

```text
http://127.0.0.1:5174/exploration/learned-paths
```

Actions:

1. Open the catalog page.
2. Record the current URL and page title or main visible title.
3. Observe whether a LearnedPath table/list is visible.
4. If no rows are present, observe the empty state.
5. Record whether the refresh action is visible.

Expected visible result:

- The catalog page renders normally.
- Either the LearnedPath table/list is visible, or a clear empty state is
  visible.
- The page does not attempt to start an autonomous run.

Evidence requirement:

- Browser method.
- Page URL.
- Visible title.
- Visible list/table or empty-state observation.
- Screenshot, trace, video, or browser observation excerpt.

### LPC-002 · Trust filter changes visible state or filter state

Target URL:

```text
http://127.0.0.1:5174/exploration/learned-paths
```

Actions:

1. Open the catalog page.
2. Locate the trust filter control.
3. Open the filter dropdown.
4. Select one trust value, for example `Flaky`, `Confirmed`, or the visible
   localized equivalent.
5. Observe the table/list, empty state, or selected filter label.

Expected visible result:

- The trust filter is visible and operable.
- The selected filter state changes visibly, or the list/empty-state updates.
- If no matching rows exist, the empty state is visible and recorded.

Evidence requirement:

- Browser observation before and after filter selection.
- Selected filter label or visible list/empty-state change.
- Screenshot, trace, video, or browser observation excerpt.

### LPC-003 · LearnedPath drawer opens from a row/card

Target URL:

```text
http://127.0.0.1:5174/exploration/learned-paths
```

Actions:

1. Open the catalog page.
2. Find a visible LearnedPath row or card.
3. Click only the row/card action that opens details, such as `View actions`.
4. Observe the drawer.

Expected visible result:

- A detail drawer opens.
- The drawer shows path identity or scenario information.
- The drawer shows path trust and action details when available.
- If no row/card exists, mark `BLOCKED` and record the visible empty state.

Evidence requirement:

- Browser observation showing the chosen row/card.
- Browser observation showing the opened drawer.
- Visible drawer title or scenario/path identity.
- Screenshot, trace, video, or browser observation excerpt.

### LPC-004 · Drawer replay section is visible but does not trigger live autonomous run

Target URL:

```text
http://127.0.0.1:5174/exploration/learned-paths
```

Actions:

1. Open the catalog page.
2. Open a LearnedPath drawer from a visible row/card.
3. Observe the replay section.
4. Confirm the target URL input is visible if present.
5. Confirm the replay button is visible if present.
6. Do not click replay.

Expected visible result:

- The drawer contains a replay section or equivalent replay affordance.
- The replay target input and replay button are visible when the selected path
  supports replay.
- No autonomous run is triggered.
- No `/exploration/autonomous-runs` or stream request is made.

Evidence requirement:

- Browser observation of the opened drawer.
- Browser observation of the replay section.
- Explicit note that replay was not clicked.
- Screenshot, trace, video, or browser observation excerpt.

## Report Template

```md
# LearnedPath Catalog Visual UI Exploratory

Date:
Commit:
Working tree:
Tool:
Target URLs:

## Preconditions

- API health:
- console learned-path catalog:
- LearnedPath row availability:

## Summary

| Case | Status | Evidence |
| --- | --- | --- |

## Case Results

### LPC-001 · Catalog page renders list or empty state

- Status:
- Method:
- Page URL:
- Visible actions:
- Visible observations:
- Evidence:
- Notes:
- Follow-up:

## Boundaries

- Autonomous endpoints called:
- `/exploration/autonomous-runs` called:
- `/exploration/autonomous-runs/stream` called:
- Autonomous explorer imported or run directly:
- verify-scenario used:
- LLM provider used:
- Product code modified:
- E2E spec modified:
- Package scripts modified:
- Replay clicked:
```

## Boundaries Checklist

- Product code modified: no.
- E2E spec modified: no.
- Package scripts modified: no.
- `docs/iterations/` modified: no.
- Autonomous endpoint called: no.
- `/exploration/autonomous-runs` called: no.
- `/exploration/autonomous-runs/stream` called: no.
- LLM provider used: no.
- Deterministic E2E claimed: no.
