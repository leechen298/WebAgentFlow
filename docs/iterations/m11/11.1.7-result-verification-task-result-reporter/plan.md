# Implementation Plan

## Inputs and Dependencies

Future implementation must inspect the current task planning schemas,
conversation events, execution service, and replay result shape before choosing
the final module boundary.

Expected inputs:

- `plan_execution_started` event;
- `plan_execution_completed` event;
- `plan_execution_failed` event;
- `plan_execution_blocked` event;
- replay run id / execution id if available;
- learned path id;
- target URL or replay entry context;
- route summary;
- replay-level error summary;
- `no_result_verification` marker from 11.1.6;
- `no_autonomous` marker from 11.1.6;
- existing `PostconditionSignal`, `TaskExecutionResult`,
  `AgentEReporterInput`, or `AgentEReporterOutput` schema fields when stable.

Potential implementation locations:

- inspect existing task planning schemas before choosing the final path;
- likely under `apps/api/app/services/task_planning/` for result verification
  and reporter logic;
- conversation integration likely under `apps/api/app/services/conversation/`;
- tests likely under `apps/api/tests/`.

This documentation package does not create code files.

## Verification Input Evidence

11.1.7 must consume execution evidence. It must not reconstruct results from raw
user text.

Allowed evidence sources may include:

- 11.1.6 execution events;
- replay result summary;
- explicit postcondition signals;
- artifact references;
- route summary or terminal route step metadata;
- manually provided verification signal;
- stable external system response summary if already present.

11.1.7 must not:

- infer success from replay completion alone;
- call replay again;
- call retrieval or Task Path Planner again;
- infer target URL or result state from raw user text;
- read raw HTML;
- call Page Understanding Agent;
- call LLM provider;
- open a browser for a second check.

## Verification Outcome Semantics

First-version outcome semantics:

- `verified`: explicit postcondition evidence supports task success.
- `failed`: replay failed, or negative evidence proves the intended result did
  not happen.
- `uncertain`: replay completed, but evidence is insufficient to prove the
  business result.
- `needs_review`: user or later system review is required before marking the
  task successful.
- `blocked`: execution did not happen, or verification cannot run because
  required evidence is missing.

Default rule:

```text
plan_execution_completed + no postcondition evidence -> uncertain / needs_review
```

`verified` requires evidence. It is not the default.

## Postcondition Evidence Boundary

Future postcondition evidence may include:

- URL changed or stayed at an expected URL;
- page title or known success marker if already captured in structured form;
- known success message;
- artifact reference exists;
- replay action log reached an expected terminal step;
- stable external response summary if available;
- manually provided verification signal.

First-version 11.1.7 must stay conservative. If available evidence cannot prove
the result, return `uncertain` or `needs_review`.

This package must not introduce:

- raw HTML parsing;
- Page Understanding Agent calls;
- LLM-based result judgment;
- browser re-open / second pass verification;
- autonomous relearning;
- recovery execution.

## Task Result Reporter Output

Task Result Reporter turns the verification outcome into a user-facing report.

The report may include:

- replay execution completed / failed / blocked;
- verification outcome;
- evidence used;
- evidence missing;
- whether user review is needed;
- no recovery attempted;
- no autonomous learning started.

The report must not claim:

- task success unless outcome is `verified`;
- form submission success without postcondition evidence;
- artifact production without an artifact reference;
- external system completion without evidence.

## AgentEReporter Schema Relationship

11.1.1 may keep schema class names such as `AgentEReporterInput` and
`AgentEReporterOutput` for compatibility.

Documentation and implementation language should use the primary role name:
Task Result Reporter. Agent E is a legacy alias and should only appear where
compatibility with older naming is useful.

11.1.7 should not casually change 11.1.1 schemas. If implementation discovers a
schema hardening need, it must be explicit, minimal, and covered by tests.

## Conversation Event Recording

Future event semantics may include:

- `result_verification_completed`;
- `result_verification_failed`;
- `result_verification_uncertain`;
- `task_result_reported`.

Event payload should include:

- execution event id or replay run id if available;
- learned path id;
- verification outcome;
- evidence summary;
- missing evidence summary;
- user-facing report summary;
- `no_recovery: true`;
- `no_autonomous: true`;
- `no_llm: true` when applicable.

Event payload must not include:

- raw HTML;
- screenshot payload;
- user/account/tenant fields;
- unsupported success assertion.

## Conversation State Transition Options

Future implementation may introduce or reuse statuses with these semantics:

```text
execution_finished -> result_verified
execution_finished -> result_uncertain
execution_failed -> result_failed
execution_blocked -> result_blocked
```

This documentation package does not modify schemas.

Required rule:

```text
verified state requires evidence.
uncertain / needs_review is valid when verification evidence is incomplete.
```

## Assistant Message Behavior

Verified:

```text
The replay completed and the expected result was verified based on available evidence.
```

Uncertain:

```text
Replay completed, but I could not verify the business result from available evidence. Please review the target page or provide a verification signal.
```

Failed:

```text
Replay execution failed before result verification. No recovery was attempted.
```

Blocked:

```text
Result verification could not run because execution was blocked or required evidence is missing.
```

Needs review:

```text
The replay evidence is incomplete. Manual review is needed before marking the task successful.
```

Exact wording can change during implementation. The semantics must remain
evidence-bound.

## Recovery Boundary

11.1.7 does not recover.

When verification is failed, uncertain, or needs review:

- do not re-run replay;
- do not call Failure Recovery Agent;
- do not start autonomous run;
- do not repair learned paths;
- do not enter teaching mode.

This package only reports `failed`, `uncertain`, `needs_review`, or `blocked`.

## Test Plan

Future implementation tests should cover:

- `plan_execution_completed` without postcondition evidence returns
  `uncertain` or `needs_review`;
- explicit postcondition evidence can produce `verified`;
- replay failure produces `failed`;
- execution blocked produces `blocked`;
- reporter does not claim task success for `uncertain`, `needs_review`,
  `failed`, or `blocked`;
- evidence summary and missing evidence summary are populated;
- no raw HTML, autonomous, LLM, Page Understanding Agent, replay re-run, or
  recovery imports;
- AgentEReporter schema compatibility remains intact if reused;
- event payload does not include raw HTML, screenshot payload, or
  user/account/tenant fields.

## Evidence Plan

Future implementation review should record:

- changed files;
- verification input examples;
- outcome examples for verified / failed / uncertain / needs_review / blocked;
- reporter message examples;
- event payload examples;
- proof that replay completed is not reported as task success;
- proof that recovery was not attempted;
- test commands and results.

## Out-of-Scope Items

11.1.7 does not do:

- replay execution;
- replay re-execution;
- autonomous run;
- hidden relearning;
- raw HTML planning or parsing;
- LLM-based verification;
- Page Understanding Agent invocation;
- slot binding;
- form filling;
- recovery dialogue;
- teaching mode;
- browser exploration;
- full deterministic E2E;
- evidence report aggregation;
- 11.1.8 detail directory creation.

## Open Questions

- Which postcondition evidence source is stable enough for the first
  implementation?
- Should `uncertain` and `needs_review` be separate persisted statuses or only
  reporter outcomes?
- Should Task Result Reporter output reuse `AgentEReporterOutput` directly, or
  should a narrower service result type map into that schema?
- Which event enum names should be added if conversation event recording is
  implemented in 11.1.7?
- How should manually provided verification signals be represented without
  adding user/account/tenant ownership concepts?
