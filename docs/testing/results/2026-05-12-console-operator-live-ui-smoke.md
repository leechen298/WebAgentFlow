# Console Operator Live UI Smoke Report

Date: 2026-05-12
Commit at capture start: `fe5cf58e1a2fb9a200c87b03e7b6f9b4bf52e945`
Current HEAD while writing report: `ea26d951ffc13681f012dff6401b71fcbfc6e5cb`
Evidence commit: `74d34d2980d4d8a2a91050418476ca5a9caf9fed`
Working tree at capture start: dirty. Relevant testing/doc changes were present under `AGENTS.md`, `CLAUDE.md`, `CLAUDE.zh.md`, `docs/testing/agent-operated-ui/`, and `docs/testing/results/`. Separate staged M11 iteration documentation changes were also present and were not touched by this live UI smoke.
Tool: headed Playwright fallback. The in-app browser / Browser Use backend was attempted first, but no Codex in-app browser backend was available in this session.
Target URLs:

- `http://127.0.0.1:5174/exploration/autonomous/cases`
- `http://127.0.0.1:5174/exploration/autonomous`
- `http://127.0.0.1:5174/exploration/autonomous/history`
- `http://127.0.0.1:5175/users`

## Preconditions

- `curl -sS -i http://127.0.0.1:8001/health`
  - `HTTP/1.1 200 OK`
  - `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}`
- `curl -sS -I http://127.0.0.1:5174/exploration/autonomous/cases`
  - `HTTP/1.1 200 OK`
- `curl -sS -I http://127.0.0.1:5174/exploration/autonomous`
  - `HTTP/1.1 200 OK`
- `curl -sS -I http://127.0.0.1:5174/exploration/autonomous/history`
  - `HTTP/1.1 200 OK`
- `curl -sS -I http://127.0.0.1:5175/login`
  - `HTTP/1.1 200 OK`
- `curl -sS -I http://127.0.0.1:5175/users`
  - `HTTP/1.1 200 OK`

## Summary

| Case | Status | Evidence |
|---|---|---|
| LIVE-001 Use Cases page renders and can deep-link to Workbench | PASS | The Use Cases page rendered 5 runnable scenarios. The `users / filter_by_name` scenario was selected and `在工作台运行` navigated to Workbench with `url`, `spec_id`, `scenario`, and `goal` query params prefilled. Screenshot: `output/playwright/aui02-live/use-cases.png`. |
| LIVE-002 Workbench single run executes from UI | PASS | The Workbench was prefilled for `users / filter_by_name`; clicking `运行` started a live run through the product UI. The run completed with `pass_gate.status=pass`, self assessment `success`, Supervisor verdict `success`, and all 5 scorecard values at `1.0`. Screenshots: `output/playwright/aui02-live/workbench-before-run.png`, `output/playwright/aui02-live/workbench-running.png`, `output/playwright/aui02-live/workbench-result.png`. |
| LIVE-003 History page shows the new run | PASS | The History page initially showed an empty/checking state, then after refresh displayed the new `users / filter_by_name` run as the first row with status `completed`, result `通过`, and review status `未审核`. Screenshot: `output/playwright/aui02-live/history-new-run.png`. |
| LIVE-004 Detail page opens for the new run | PASS | The Detail page opened for run `b7a2bbdd-ab8b-4f54-9b41-d3a3bee3c53c` and displayed run config, page analysis, step timeline, verification, run review, LearnedPath relation, and raw JSON entry. Screenshot: `output/playwright/aui02-live/detail-new-run.png`. |
| LIVE-005 Optional batch run from Use Cases | PASS | One scenario was selected on the Use Cases page, `批量运行选中用例` was clicked, and the row moved from `运行中` to completed `success`. Screenshots: `output/playwright/aui02-live/batch-selected.png`, `output/playwright/aui02-live/batch-run.png`. |

## Live Run Details

- Selected spec: `users`
- Selected scenario: `filter_by_name`
- Target validation URL: `http://localhost:5175/users`
- Run started: yes, by clicking Workbench `运行`
- Run completed: yes
- Final status: `completed`
- pass_gate.status: `pass`
- pass_gate.reasons: `[]`
- Run ID: `b7a2bbdd-ab8b-4f54-9b41-d3a3bee3c53c`
- LearnedPath ID: `d7e73239-4fc7-449b-ab02-6c73e14418eb`
- LearnedPath trust: `provisional`
- Error: none observed
- Self assessment verdict: `success`
- Self assessment summary: `All 2 action step(s) succeeded and URL changed.`
- Supervisor verdict: `success`
- Supervisor source: `llm`
- Supervisor model: `MiniMax-M2.7`
- Supervisor confidence: `null`
- Supervisor summary: `在Name输入框填入'alice'后点击Search，页面未发生路径跳转但URL从/users变为/users?name=alice，结果列表正确过滤为1行（alice@example.com），搜索表单保留输入值，无错误提示。`
- Scorecard:
  - element_recognition: `1.0`
  - action_coverage: `1.0`
  - verdict_accuracy: `1.0`
  - distraction_avoidance: `1.0`
  - supervisor_agreement: `1.0`

## Steps And Observations

1. Opened the Use Cases page.
   - Page title: `自主探索用例 | WebAgentFlow`.
   - The page showed 5 runnable scenarios.
   - The selected scenario was `users / filter_by_name`.
   - The `在工作台运行` button was clicked from the scenario row.

2. Confirmed Workbench prefill.
   - Workbench URL included:
     - `url=http://localhost:5175/users`
     - `spec_id=users`
     - `scenario=filter_by_name`
     - the authored goal text for filtering users by `alice`
   - Visible form state included URL input, goal input, matched spec `users`, selected scenario `filter_by_name`, and fill value `name = alice`.
   - The `运行` button was visible and enabled.

3. Started a single live run from Workbench.
   - Clicking `运行` started the run and changed the UI to `运行中...`.
   - The stream showed live phase updates for page open, analysis, planning, execution, self assessment, Supervisor, verification, and completion.
   - During execution, the target page title was `User Directory — Validation Site`.
   - Page analysis reported `32 visible / 4 hidden` elements.
   - The plan contained 3 steps.

4. Observed the completed Workbench result.
   - Execution reached `3/3`.
   - Step 1 filled `#search-name` with `alice`.
   - Step 2 clicked `#btn-search`.
   - Step 3 observed the filtered result area.
   - Final URL was `http://localhost:5175/users?name=alice`.
   - The raw SSE event stream contained 16 events, ending with `run_completed`.

5. Checked History.
   - The first History load briefly showed an empty/checking state.
   - After clicking `刷新`, the new run appeared as the first row.
   - Visible row values included `users`, `filter_by_name`, result `通过`, review status `未审核`, and status `completed`.
   - No review or destructive action was clicked.

6. Opened Detail.
   - Detail URL: `http://127.0.0.1:5174/exploration/autonomous/history/b7a2bbdd-ab8b-4f54-9b41-d3a3bee3c53c`.
   - Visible sections included run config, page analysis, step timeline, verification, run review, LearnedPath, and raw JSON.
   - The LearnedPath section showed that this run created path `d7e73239-4fc7-449b-ab02-6c73e14418eb` with trust `暂存`.

7. Ran the optional one-scenario batch smoke.
   - Returned to Use Cases.
   - Selected only `users / filter_by_name`.
   - Clicked `批量运行选中用例`.
   - The row showed `运行中` and later completed with `success`.
   - The test did not expand to all scenarios.

## Screenshots

- `output/playwright/aui02-live/use-cases.png`
- `output/playwright/aui02-live/workbench-before-run.png`
- `output/playwright/aui02-live/workbench-running.png`
- `output/playwright/aui02-live/workbench-result.png`
- `output/playwright/aui02-live/history-new-run.png`
- `output/playwright/aui02-live/detail-new-run.png`
- `output/playwright/aui02-live/batch-selected.png`
- `output/playwright/aui02-live/batch-run.png`

## Network / Endpoint Observations

- `/api/exploration/specs` called: yes, product UI request, `200 OK`.
- `/api/health` called: yes, product UI request, `200 OK`.
- `/api/exploration/autonomous-runs/stream` called: yes, expected product UI traffic, `200 OK`.
- `/api/exploration/autonomous-runs?limit=20` called: yes, product UI request from History, `200 OK`.
- Read-only run detail fetch: yes, `GET /exploration/autonomous-runs/b7a2bbdd-ab8b-4f54-9b41-d3a3bee3c53c` was used only to quote the exact pass gate, Supervisor, and scorecard evidence in this report.
- Direct autonomous run POST outside the product UI: no.

## Boundaries

- Live autonomous run triggered: yes, expected for this live UI smoke and triggered only through product UI controls.
- `/exploration/autonomous-runs` called: yes for read/history/detail retrieval; no direct POST was made outside the product UI.
- `/exploration/autonomous-runs/stream` called: yes, expected product UI traffic from Workbench and batch run.
- Product-side LLM provider triggered: yes, expected for this live smoke; Supervisor source was `llm`, model `MiniMax-M2.7`.
- External real website visited: no.
- Product code modified: no.
- E2E spec modified: no.
- Package scripts modified: no.
- M11.1 implementation touched by this run: no.
- Historical run deleted: no.
- Old run review status modified: no.

## Failures / Gaps Found

- The in-app browser / Browser Use backend was not available in this session, so the run used headed Playwright as the external browser operator.
- History initially rendered an empty/checking state before refresh. Refreshing populated the new run correctly.
- No product functional failure was observed in the single-run Workbench smoke or one-scenario batch smoke.

## Verification

- `git diff --check`: clean

## Follow-ups

- If the in-app browser backend becomes available, the same AUI-02 live smoke can be repeated with Browser panel evidence.
- The optional batch smoke was intentionally limited to one scenario. A broader batch run should be a separate task with explicit runtime budget and failure handling.
