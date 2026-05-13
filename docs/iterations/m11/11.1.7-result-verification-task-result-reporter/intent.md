# 11.1.7 Result Verification and Task Result Reporter

## Goal

Establish the result verification and Task Result Reporter boundary for M11.1.
This package should define how WebAgentFlow consumes replay execution evidence,
derives a conservative verification outcome, and reports the result to the user
without inventing success.

## Motivation

11.1.6 executes a confirmed plan through deterministic replay, but replay
completion is not the same as task success. A browser action sequence can finish
without proving that the external system accepted the intended operation,
created the expected artifact, or reached the expected business state.

M11.1 therefore needs a separate verification/reporting layer:

- Result verification evaluates available execution and postcondition evidence.
- Task Result Reporter converts that evidence into a user-facing response.
- Missing evidence is a first-class outcome, not a reason to claim success.

## Why Replay Completion Is Not Enough

`plan_execution_completed` only means the replay invocation reached a completed
replay-level state. It does not prove:

- the task succeeded;
- the business result was verified;
- a form submission was accepted;
- an artifact was produced;
- the external system reached the intended state.

If no verification evidence exists, the correct outcome is `uncertain` or
`needs_review`, not `verified`.

## Why the Reporter Must Be Evidence-Bound

Task Result Reporter must only report what the evidence supports. It may say
that replay completed, failed, or was blocked. It may summarize what evidence
was used and what evidence was missing.

It must not say:

- "task succeeded" unless the verification outcome is `verified`;
- "form submitted successfully" without explicit postcondition evidence;
- "artifact produced" without an artifact reference;
- "operation completed in the external system" without supporting evidence.

## Recovery Boundary

11.1.7 does not recover from failed or uncertain results. If verification fails
or evidence is incomplete, this package should report `failed`, `uncertain`, or
`needs_review`.

It must not:

- re-run replay;
- call Failure Recovery Agent;
- trigger autonomous run;
- repair LearnedPath assets;
- enter teaching mode.

Recovery remains future scope.

## Relationship to Future Evidence Work

11.1.7 is a prerequisite for a broader task-to-path evidence package. It defines
the result semantics and reporting boundary that later deterministic E2E,
operator review, and evidence aggregation can build on.

It is not the full E2E evidence package itself.

## Success Criteria

- Verification inputs are clearly scoped to replay execution evidence and
  explicit postcondition evidence.
- Outcomes include `verified`, `failed`, `uncertain`, `needs_review`, and
  `blocked` or equivalent semantics.
- `plan_execution_completed` defaults to non-verified unless postcondition
  evidence proves success.
- Task Result Reporter output is evidence-bound and user-readable.
- Failure or uncertainty does not trigger recovery.
- No replay, autonomous run, raw HTML reading, LLM call, or browser exploration
  is introduced by this documentation package.
