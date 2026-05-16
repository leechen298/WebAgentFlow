# M12 Plan

Status: completed with follow-ups.

Current package: 12.6 Recovery tests and evidence — evidence closed.

## Goal

M12 defines how WebAgentFlow behaves after the M11.1 task-to-path loop reports
`failed`, `blocked`, `uncertain`, or `needs_review`, or after the runtime
receives a user-abort signal. The goal is safe, explainable, auditable
next-step handling, not automatic repair.

## Starting Point

M11.1 established the first L3 task-to-path path:

1. user task
2. planning preview
3. confirmation / consent
4. replay execution
5. Task Result Reporter output

Its evidence closure shows the required boundary for M12: failed, blocked, and
uncertain outcomes do not trigger recovery, hidden relearning, or autonomous
run. M12 adds the explicit dialogue and decision layer after those outcomes.

M11.2 Runtime Observation / Wait-for-change is not part of this plan. M12 may
later consume richer runtime observation as evidence, but it must not depend on
M11.2 to define its first safety semantics.

## Package Split

### 12.0 · M12 overview / scope

Define the terms, boundaries, and first safety contract for failure recovery,
abort handling, and runtime robustness.

### 12.1 · Failure classification and recovery boundary

Status: implemented / shipped.

Classify `failure`, `blocked`, `uncertain`, and `needs_review` from M11.1
structured execution and reporting evidence. The classifier returns evidence
references and recovery boundary recommendations, but must not execute
recovery.

### 12.2 · User abort / stop handling

Status: implemented / shipped.

Handle explicit user interruption. Abort should pause or stop immediately,
record what was known, acknowledge the stop boundary, avoid new browser
actions, and hand later choices to 12.3 / 12.4 / 12.5.

### 12.3 · Recovery proposal MVP

Status: implemented / shipped.

Generate recovery proposals such as ask user, review evidence, suggest
re-teach, consider retry later, hand off to takeover later, wait for runtime
observation later, or abandon. A proposal is not an execution command.
Proposal options are non-executable by default and may be ranked or labelled,
but must not be auto-selected. 12.3 is a code-type iteration; implementation
should use its contract, technical design, test plan, and plan as execution
inputs rather than requiring an extra review checkbox inside the documents.

### 12.4 · Retry / re-run policy

Status: implemented / shipped.

Define when retry is allowed, when it is unsafe, and what user confirmation is
required before a retry or re-run. 12.4 is a code-type iteration and has shipped
a pure deterministic retry policy evaluator. Retry policy is not retry
execution, and `retry_allowed_requires_confirmation` is not `retry_started`.

### 12.5 · Recovery conversation flow

Status: implemented / shipped.

Route recovery and abort conversations through WebAgentFlow's runtime
conversation surface while preserving the internal role boundaries for Failure
Recovery Agent (legacy: Agent F) and User Abort Handler (legacy: Agent G).
12.5 has shipped a pure deterministic recovery conversation flow service.
Recovery conversation flow is not recovery execution; it may display, explain,
ask, route, and record choices, but must not execute retry, replan, browser
continuation, takeover, teaching mode, or LearnedPath write-back.

### 12.6 · Recovery tests and evidence

Status: evidence closed.

Close M12 with deterministic tests, conversation/event evidence, and static
review that prove no hidden recovery, no hidden relearning, and no browser
continuation without user consent.

Evidence-closure submission has executed the required recovery suite,
recovery ruff command, and `git diff --check`. Result: 157 passed, ruff clean,
diff clean. Completion decision recorded in
`docs/testing/results/2026-05-16-m12-recovery-tests-and-evidence.md`.

## Decision Rules

| Situation | Default M12 action |
|---|---|
| Replay failed, drifted, or returned an error | Stop execution, explain the failure evidence, and hand off to a later recovery-proposal flow. |
| Required context is missing | Stay blocked, ask for the missing context, and do not execute. |
| Result cannot be verified | Report `uncertain` / `needs_review`, preserve evidence, and ask for review or clarification. |
| User aborts | Pause or stop immediately, record current state, acknowledge that no new browser action may start, and hand later choices to recovery conversation flow. |
| Partial state may be unsafe | Must stop; retry or re-run requires explicit user confirmation. |
| Missing path coverage or repeated drift | Suggest re-teach / update LearnedPath, but do not write a new path automatically. |

## Retry Policy

Retry is allowed only when all of these are true:

- the failed action is safe to repeat;
- evidence explains what failed;
- repeated execution will not duplicate an irreversible side effect;
- the user confirms the retry or re-run;
- the retry uses existing confirmed route data or an explicit new plan.

Retry must stop when side effects are unknown, the page state is unsafe, the
user aborts, required context is missing, or the recovery proposal would need
autonomous exploration / hidden relearning.

## Evidence and Audit

M12 decisions must preserve:

- original execution / replay status;
- result reporter outcome and `needs_review` marker;
- failure or blocked reason;
- user abort signal when present;
- recovery proposal shown to the user;
- user choice before any retry, replan, handoff, or abandon action;
- evidence that proposal options were not executed or auto-selected by 12.3;
- markers showing that autonomous recovery and hidden relearning did not run.

## Explicit Non-goals

- autonomous recovery;
- hidden relearning;
- automatic autonomous exploration;
- raw HTML planning;
- default LLM provider dependency;
- bypassing confirmation;
- treating `uncertain` as success;
- treating `replay completed` as task success;
- M11.2 wait-for-change / runtime observation implementation;
- slot binding;
- teaching mode implementation;
- account, tenant, commercial, remote trigger, WeChat, or Feishu integration.

## Validation for Current Planning State

12.6 now exists as the current evidence closure design package. Current
planning-state checks should ensure no code/package drift and no M11 history
document changes.

- `git diff --check`
- `git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'`
- `git status --short docs/iterations/m11`
