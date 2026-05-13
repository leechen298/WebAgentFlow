# Intent

## Why This Package Exists

M11.1 has moved from isolated task-planning components to a runnable
task-to-path chain. Unit and integration tests are necessary, but they do not
by themselves prove that the full MVP boundary is coherent from user task to
honest result report.

11.1.8 exists to close that gap with scoped tests and evidence.

This package is not a feature package. It does not introduce new runtime
behavior. It defines how to test and document the current M11.1 chain so the
project can distinguish shipped behavior, known limitations, and future scope.

## Why Unit Tests Are Not Enough

11.1.1 through 11.1.7 each validate their own layer:

- schemas;
- retrieval and ranking;
- planning;
- conversation preview;
- confirmation;
- replay execution;
- result reporting.

The risk now sits between layers. Examples:

- a planning preview may be correct, but confirmation could be bypassed;
- replay could complete, but reporting could claim success without evidence;
- explicit `/replay` could accidentally bypass pending confirmation;
- blocked or uncertain paths could be hidden behind successful test summaries.

11.1.8 must test the chain, not just individual parts.

## Why Scoped E2E

The M11.1 MVP should not start with broad browser automation or a generalized
task runner. Scoped E2E is enough for this package:

```text
ordinary task
-> planning preview
-> awaiting_confirmation
-> confirm
-> plan_confirmed
-> execute
-> replay started
-> replay completed
-> task_result_reported
-> uncertain / needs_review report
```

That path proves the MVP wiring while keeping result verification honest.

Negative paths are equally important:

- no candidates returns unable-to-plan;
- ambiguous confirmation stays awaiting confirmation;
- `/cancel` returns to intake;
- `/replay` does not bypass awaiting confirmation;
- execute without target URL is blocked;
- replay failure reports failed without recovery;
- replay completion without postcondition evidence reports uncertain.

## Why Evidence Must Be Split

11.1.8 must keep these categories separate:

- deterministic API / unit / E2E tests;
- exploratory tests;
- Codex autonomous review;
- manual UI smoke;
- visual UI exploratory work.

They answer different questions. A deterministic test pass is not the same as
an exploratory review. A Codex review finding is not a product-internal
Supervisor verdict. A sandbox-blocked E2E run is not a failed product behavior.

The evidence package must say exactly what ran, where it ran, what passed,
what failed, and what was blocked by environment.

## Why Codex Autonomous Review Is Auxiliary

Codex autonomous review can help find boundary bugs:

- replay completed treated as task succeeded;
- confirmation bypass;
- `/replay` bypass in pending states;
- missing target URL guessed from user text;
- result reporter inventing success;
- failed / uncertain triggering recovery;
- event order mismatches;
- final assistant message contradicting events or state.

However, Codex review is not the final acceptance authority. It is a review
input. Deterministic tests and explicit evidence remain the primary acceptance
surface for 11.1.8.

## Result Verification Boundary

11.1.8 does not change 11.1.7 semantics.

The evidence must continue to prove:

```text
Replay completed != task succeeded.
No postcondition evidence -> uncertain / needs_review.
Failed does not trigger recovery.
Blocked does not trigger hidden learning.
```

This is the core safety boundary for the task-to-path MVP.

## Why This Is Not New Feature Work

11.1.8 should not add runtime capability. Its value is closure:

- a test matrix that maps to the M11.1 runtime chain;
- evidence reports that can be audited later;
- explicit exit criteria for the M11.1 MVP;
- known limitations separated from defects.

That makes it possible to decide whether M11.1 is ready to close or whether
specific issues must be fixed before moving to later milestones.
