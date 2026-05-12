# AUI-02 · Console Operator Visual UI

## Purpose

Use an Agent-operated browser to verify that the core console operator pages
remain visually navigable without starting a live autonomous run. This covers
history, detail, workbench, and use-cases pages as visible operator surfaces.

This is Agent-operated UI exploratory evidence. It is not deterministic E2E,
API-only exploratory, component testing, or a live autonomous run.

## Scope

Target pages are based on the current console router:

- `http://127.0.0.1:5174/exploration/autonomous/history`
- `http://127.0.0.1:5174/exploration/autonomous/history/<run_id>`
- `http://127.0.0.1:5174/exploration/autonomous`
- `http://127.0.0.1:5174/exploration/autonomous/cases`

Primary evidence report:

- `docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md`

The detail-page case may be `BLOCKED` when no persisted run exists. Do not
create a live run to manufacture detail data.

## Target Pages

| Area | URL |
| --- | --- |
| Run history | `http://127.0.0.1:5174/exploration/autonomous/history` |
| Run detail | `http://127.0.0.1:5174/exploration/autonomous/history/<run_id>` |
| Workbench | `http://127.0.0.1:5174/exploration/autonomous` |
| Use cases | `http://127.0.0.1:5174/exploration/autonomous/cases` |

## Preconditions

Before browser operation, record:

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5174/exploration/autonomous/history
curl -sS -I http://127.0.0.1:5174/exploration/autonomous
curl -sS -I http://127.0.0.1:5174/exploration/autonomous/cases
```

Detail-page data precondition:

- Prefer opening a detail page by clicking `View` from a visible history row.
- If the history page has no rows, mark `COV-002` as `BLOCKED` with visible
  empty-state evidence.
- Do not trigger a new run to create data.

If the console or API is unreachable, mark affected cases `BLOCKED`. Do not
replace browser evidence with curl, source inspection, component tests, or
headless E2E output.

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
- Do not click workbench `Run`.
- Do not click workbench `Abort` unless a run was already active before the
  test and the operator explicitly asks for intervention.
- Do not click use-cases `Run selected`.
- Do not click per-scenario `Run in Workbench` if it would prepare or trigger a
  live run outside the case objective.
- Do not click history/detail destructive or mutating actions such as delete,
  accept review, or reject review.
- Do not edit product code, E2E specs, package scripts, or iteration docs.
- Do not claim PASS without actual browser-visible evidence.

## Cases

### COV-001 · History page renders key controls or empty state

Target URL:

```text
http://127.0.0.1:5174/exploration/autonomous/history
```

Actions:

1. Open the history page.
2. Record the current URL and page title or main visible title.
3. Confirm the history page shell is visible.
4. Confirm refresh and workbench navigation controls are visible if present.
5. Observe whether a run table is visible or an empty state is visible.

Expected visible result:

- History page renders normally.
- A run table/list or clear empty state is visible.
- No live autonomous run is triggered.

Evidence requirement:

- Browser method.
- Page URL.
- Visible title or card title.
- Table/list or empty-state observation.
- Screenshot, trace, video, or browser observation excerpt.

### COV-002 · Detail page renders selected item details or is blocked due to missing seed data

Target URL:

```text
http://127.0.0.1:5174/exploration/autonomous/history/<run_id>
```

Actions:

1. Open the history page.
2. If at least one row is visible, click only the safe detail navigation action,
   such as `View`.
3. Record the resulting detail URL.
4. Observe the detail page sections.
5. If no row is visible, mark this case `BLOCKED` and record the history empty
   state.

Expected visible result:

- When a run exists, the detail page shows run configuration, status/verdict,
  result or raw JSON sections, and any LearnedPath relation block if present.
- When no run exists, the case is `BLOCKED`, not failed.
- No new run is created.

Evidence requirement:

- Browser observation of the source history row or empty state.
- Browser observation of the detail URL and visible detail sections when run
  data exists.
- Screenshot, trace, video, or browser observation excerpt.

### COV-003 · Workbench page renders form and config areas

Target URL:

```text
http://127.0.0.1:5174/exploration/autonomous
```

Actions:

1. Open the workbench page.
2. Observe the run configuration card.
3. Confirm URL and goal inputs are visible.
4. Confirm fill-values and toggle-values sections are visible.
5. Confirm live status / analysis / plan / result areas are present if visible
   in the initial shell.
6. Do not click `Run`.

Expected visible result:

- Workbench shell renders normally.
- Configuration controls are visible.
- The run button may be visible, but it is not clicked.
- No autonomous run is triggered.

Evidence requirement:

- Browser method.
- Page URL.
- Visible observations for form/config areas.
- Explicit note that `Run` was not clicked.
- Screenshot, trace, video, or browser observation excerpt.

### COV-004 · Use cases page renders list or empty state

Target URL:

```text
http://127.0.0.1:5174/exploration/autonomous/cases
```

Actions:

1. Open the use-cases page.
2. Observe the page title or card title.
3. Confirm refresh and workbench navigation controls are visible if present.
4. Observe whether spec cards/tables are visible or an empty state is visible.
5. Do not select runnable scenarios for execution.

Expected visible result:

- Use-cases page renders normally.
- Spec list/table or clear empty state is visible.
- No batch run starts.

Evidence requirement:

- Browser method.
- Page URL.
- Visible list/table or empty-state observation.
- Screenshot, trace, video, or browser observation excerpt.

### COV-005 · Live-run buttons are observed but not clicked

Target URLs:

```text
http://127.0.0.1:5174/exploration/autonomous
http://127.0.0.1:5174/exploration/autonomous/cases
```

Actions:

1. On the workbench page, observe the `Run` button or equivalent live-run
   control.
2. On the use-cases page, observe `Run selected` and per-scenario run affordances
   if visible.
3. Record whether these controls are enabled, disabled, or absent.
4. Do not click any live-run control.

Expected visible result:

- Live-run controls are visible, disabled, or absent according to current page
  state.
- The report explicitly records that none were clicked.
- No `/exploration/autonomous-runs` or stream request is made.

Evidence requirement:

- Browser observation of the live-run controls.
- Explicit no-click note.
- Screenshot, trace, video, or browser observation excerpt.

## Report Template

```md
# Console Operator Visual UI Exploratory

Date:
Commit:
Working tree:
Tool:
Target URLs:

## Preconditions

- API health:
- console history:
- console workbench:
- console use cases:
- persisted run availability:

## Summary

| Case | Status | Evidence |
| --- | --- | --- |

## Case Results

### COV-001 · History page renders key controls or empty state

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
- Live-run buttons clicked:
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
