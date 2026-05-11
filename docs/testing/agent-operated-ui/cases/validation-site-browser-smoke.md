# AUI-03 · Validation-site Browser Smoke

## Purpose

Use an Agent-operated browser to verify that the validation-site fixtures still
render the core controls needed by deterministic E2E, replay, and authored
scenario checks.

This is visual exploratory evidence. It is not deterministic E2E, API-only
exploratory, static selector smoke, or a live autonomous run.

## Scope

Target pages:

- `http://127.0.0.1:5175/login`
- `http://127.0.0.1:5175/users`

Primary evidence report:

- `docs/testing/results/2026-05-11-validation-site-browser-smoke.md`

## Preconditions

Before browser operation, record:

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5175/login
curl -sS -I http://127.0.0.1:5175/users
```

If API or validation-site is unreachable, mark the affected cases `BLOCKED`.
Do not replace browser evidence with curl, source inspection, component tests,
or headless E2E output.

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
- Do not edit product code, E2E specs, package scripts, or iteration docs.
- Do not claim PASS without actual browser-visible evidence.

## Cases

### VSB-001 · Login page renders key controls

Target URL:

```text
http://127.0.0.1:5175/login
```

Actions:

1. Open `/login`.
2. Confirm the page renders normally.
3. Confirm the username input is visible.
4. Confirm the password input is visible.
5. Confirm the submit/login button is visible.
6. Confirm the error region behavior. If hidden by default, record that and
   verify it through VSB-002.

Expected visible result:

- Login page is visible.
- Username input, password input, and login button are visible.
- Hidden-by-default error region behavior is explained, not assumed.

Evidence requirement:

- Browser method.
- Page URL.
- Visible UI observation.
- Screenshot, trace, video, or browser observation excerpt.

### VSB-002 · Login invalid credentials shows error

Target URL:

```text
http://127.0.0.1:5175/login
```

Actions:

1. Open `/login`.
2. Enter username `wrong`.
3. Enter password `wrong`.
4. Click the login submit button.
5. Observe the visible error state.

Expected visible result:

- The page remains in a failed-login state.
- A user-visible error message appears.
- No autonomous run is triggered.

Evidence requirement:

- Browser observation for the typed values and click.
- Visible error text.
- Current URL after submission.

### VSB-003 · Users page renders search controls

Target URL:

```text
http://127.0.0.1:5175/users
```

Actions:

1. Open `/users`.
2. Confirm the search area is visible.
3. Confirm the name search input is visible.
4. Confirm the status control is visible.
5. Confirm the search button is visible.
6. Confirm a result table or empty state is visible.

Expected visible result:

- Users page renders normally.
- Name, status, and search controls are visible.
- Result table or empty state is visible.

Evidence requirement:

- Browser method.
- Page URL.
- Visible observations for controls and result area.
- Screenshot, trace, video, or browser observation excerpt.

### VSB-004 · Users search by name changes result area

Target URL:

```text
http://127.0.0.1:5175/users
```

Actions:

1. Open `/users`.
2. Enter `alice` in the name search input.
3. Click search.
4. Observe the result area.

Expected visible result:

- The page does not crash.
- The URL or visible result area reflects the search.
- If a matching seeded user is visible, record the row text.
- If no matching seeded user is visible, record the empty state.

Evidence requirement:

- Browser observation for input and click.
- Current URL after search.
- Visible result count, row text, or empty-state text.

### VSB-005 · Users no-match search shows empty state

Target URL:

```text
http://127.0.0.1:5175/users
```

Actions:

1. Open `/users`.
2. Enter `zzzz-no-match-9999` in the name search input.
3. Click search.
4. Observe the result area.

Expected visible result:

- The page does not crash.
- The result area gives clear no-match feedback, such as an empty state or
  no-results message.

Evidence requirement:

- Browser observation for input and click.
- Current URL after search.
- Visible no-match result count or empty-state text.

## Report Template

```md
# Validation-site Browser Smoke

Date:
Commit:
Working tree:
Tool:
Scope:

## Preconditions

- API health:
- validation-site /login:
- validation-site /users:

## Summary

| Case | Status | Evidence |
| --- | --- | --- |

## Case Results

### VSB-001 · Login page renders key controls

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
```

## Current Evidence

The latest recorded run is:

- `docs/testing/results/2026-05-11-validation-site-browser-smoke.md`

That report records Browser Use / in-app browser PASS evidence for VSB-001
through VSB-005, with no autonomous endpoint calls and no LLM provider use.
