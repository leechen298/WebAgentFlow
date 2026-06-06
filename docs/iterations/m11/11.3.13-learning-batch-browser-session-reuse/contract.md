# Contract

状态：proposed

## Scope

本包定义并准备实现一次 learning batch 内的 browser session 复用。它只作用于
product-level capability discovery learning，不改变 spec-backed autonomous run、LearnedPath replay、
Task Path Planner、L2 teaching 或 M12 recovery / abort。

## New Concept: LearningBatchBrowserSession

`LearningBatchBrowserSession` 是一次 `LearningBatch` 内的 browser runtime ownership 边界。

Contract:

- exactly one primary `ExecutionRuntime` per learning batch;
- runtime starts after batch creation and before seed analysis;
- seed analysis and planned scenarios share this runtime;
- runtime closes exactly once when batch reaches terminal closeout or when setup fails;
- runtime is not shared across batches or conversations;
- runtime is not exposed to Agents as a browser control surface.

## Scenario Reset Contract

复用同一 browser/context/page 的前提是每个 scenario 必须从可审计 baseline 开始。

每个 scenario 前必须执行 reset gate：

- navigate to the target seed URL, without scenario query params;
- wait for page load / bounded stability;
- clear transient UI state when safe, such as open dropdowns, modals, focus state, and form values;
- preserve target-site session state by default; do not clear cookies / localStorage unless policy explicitly requests it;
- capture baseline summary: URL, title, key form values, visible result count or equivalent page summary;
- if baseline cannot be restored, stop or mark remaining scenarios skipped/unverified rather than continue polluted learning.

Allowed reset modes:

- `navigate_only`: default; navigate back to seed URL and rely on page load to reset UI.
- `reload_and_clear_form`: navigate/reload and clear known form values through generic controls.
- `new_context_same_browser`: create a new context/page inside the same browser when page pollution is unsafe.
- `clear_storage_and_reload`: explicit opt-in only; useful for fixtures, unsafe for logged-in real sites.

Default mode must not clear storage because login/session state belongs to the target site and operator.

## Evidence Isolation Contract

Even though browser runtime is reused, evidence remains scenario-scoped:

- each scenario has its own run id;
- each scenario has its own browser event timeline correlation id;
- BrowserEventRecorder listeners must not leak events across scenarios;
- terminal verdict must only use action-scoped evidence from the current scenario;
- screenshots remain per step / per scenario;
- scenario failure must not become success because a previous scenario changed the page.

## Cleanup Contract

Runtime cleanup must happen in `finally`-style closeout:

- normal completion closes runtime;
- `partial_success`, `timed_out`, `cancelled`, `failed`, and `unverified` close runtime;
- seed analysis failure closes runtime;
- scenario exception closes runtime after batch failure/partial closeout;
- persistence exception closes runtime;
- browser/page crash either creates a same-browser replacement page once or closes the batch as failed/unverified.

Forbidden:

- leaving visible browser windows open after terminal batch state;
- opening a new browser for every scenario in the same batch;
- continuing scenarios after reset baseline fails;
- writing LearnedCapability or LearnedPath after a cancelled batch;
- using direct autonomous-run endpoints as proof of product behavior.

## Compatibility Contract

Must not regress:

- spec-backed autonomous run lifecycle;
- ordinary product-level single-run learning;
- LearnedPath replay;
- `wagent chat --headless`;
- existing `ExecutionRuntime` context manager behavior;
- 11.3.12 `LearningBatch` status and evidence semantics.

## User Experience Contract

For visible learning:

- user sees one browser window for the learning batch;
- browser may navigate between scenarios but should not repeatedly open/close;
- progress text may still show scenario progress;
- if learning times out/cancels/fails, user receives a closed batch status and browser closes.

For headless learning:

- same lifecycle applies, but no visible window is shown.

## Product Boundary

This package is target-agnostic. It must not contain `/users`, field labels, target selectors, fixture data,
or validation-site-only wording in runtime code.

## Implementation Authorization

This contract does not authorize implementation by itself. Implementation requires reviewed
`technical-design.md`, reviewed `test-plan.md`, and `implementation_authorized: yes` in `review.md`.
