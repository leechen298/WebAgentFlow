# LearnedPath Catalog Agent-operated UI Exploratory Report

Date: 2026-05-12
Commit: `ebb538777c104d7f95a9218015a68e3c7d4d05e8`
Working tree at capture start: `?? output/`
Tool: headed Playwright (fallback after in-app browser / Browser Use was unavailable)
Target URL: `http://127.0.0.1:5174/exploration/learned-paths`

## Preconditions

- `curl -sS -i http://127.0.0.1:8001/health`
  - `HTTP/1.1 200 OK`
  - `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}`
- `curl -sS -I http://127.0.0.1:5174/exploration/learned-paths`
  - `HTTP/1.1 200 OK`
- Browser session console had one non-blocking error: missing `favicon.ico` (`404`).

## Case Results

| Case | Status | Evidence |
|---|---|---|
| LPC-001 catalog page renders list or empty state | PASS | The page showed `LearnedPath` heading, trust filter, refresh button, and a populated table. Visible seeded rows included `e2e:replay:deprecated`, `valid_credentials`, and `invalid_credentials`. Supporting local snapshot: `.playwright-cli/page-2026-05-12T07-23-20-675Z.yml`. |
| LPC-002 trust filter changes visible state or query/filter state | PASS | The trust filter was visible and operable. Switching to `暂存` changed the table to the empty-state row `还没有沉淀出 LearnedPath`; switching back to `全部` restored the list. Supporting local snapshots: `.playwright-cli/page-2026-05-12T07-25-25-390Z.yml`, `.playwright-cli/page-2026-05-12T07-26-28-585Z.yml`. |
| LPC-003 learned path drawer opens from a row/card | PASS | Clicking the first row's `查看动作` button opened a right-side drawer titled `动作序列`, with detail rows for ID, 场景, 页面模板, 信任度, 命中次数, 来源运行. Supporting local snapshot: `.playwright-cli/page-2026-05-12T07-29-48-173Z.yml`. |
| LPC-004 drawer replay section is visible but does not trigger live autonomous run | PASS | The drawer showed `重跑这条路径`, a `目标 URL` textbox, and a disabled `重 跑` button. The action sequence was visible with Step 1 `fill #name-field -> alice` and Step 2 `click #btn-apply`. Committed screenshot: `output/playwright/aui01/drawer-open.png`. Browser request log contained only `GET /api/exploration/learned-paths...`, `GET /api/health`, and `GET /api/exploration/learned-paths/{id}`. No autonomous-run endpoints were called. |

## Steps And Observations

1. Opened the catalog page in a headed Playwright browser session.
   - URL stayed at `/exploration/learned-paths`.
   - Page title was `LearnedPath | WebAgentFlow`.
   - The page rendered a populated table rather than an empty state.

2. Checked the trust filter.
   - Opened the filter dropdown from the top-right control.
   - Visible options in this environment were `全部` and `暂存`.
   - Selecting `暂存` changed the visible state to the empty-state row `还没有沉淀出 LearnedPath`.
   - Switching back to `全部` restored the populated list.

3. Opened a safe, non-mutating detail view.
   - Clicked the first row's `查看动作` button only.
   - Did not click `确认路径`, `标记为不稳定`, or `废弃路径`.
   - The drawer opened on the right and displayed metadata for `e2e:replay:deprecated` on `/records`.

4. Verified replay section presence without executing it.
   - The drawer included a `重跑这条路径` section with a `目标 URL` input and a disabled `重 跑` button.
   - The drawer also listed the stored action sequence:
     - Step 1: fill `#name-field` with `alice`
     - Step 2: click `#btn-apply`
   - No replay execution was triggered.

## Boundaries

- `/exploration/autonomous-runs` called: no
- `/exploration/autonomous-runs/stream` called: no
- Live autonomous run triggered: no
- Product-side LLM provider triggered: no
- Product code modified: no
- E2E spec modified: no
- Package scripts modified: no

## Verification

- `git diff --check`: clean
- Local `.playwright-cli/*.yml` snapshots were supporting transient evidence during the run. The key UI observations they captured are summarized directly in this report, and the committed durable artifact is `output/playwright/aui01/drawer-open.png`.

## Follow-ups

- AUI-01 is complete for the current seeded dataset.
- This report used headed Playwright because the in-app browser / Browser Use backend was not available in this session.
- The next Agent-operated UI run can be AUI-02 Console Operator UI. If it is scoped as Live UI Smoke, `Run` / `Run selected` may be clicked through the product UI and the report must record the resulting autonomous-run endpoints, product-side LLM / Supervisor behavior, run status, and run id.
