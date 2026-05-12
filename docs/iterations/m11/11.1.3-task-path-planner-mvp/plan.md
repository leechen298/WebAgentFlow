# Implementation Plan

## Inputs and Dependencies

Future Task Path Planner implementation should consume:

- `TaskInput` / `TaskIntent` from 11.1.1.
- Ranked `LearnedPathCandidate` list from 11.1.2.
- Retrieval `match_reasons` and `warnings`.
- Optional future Slot Binding proposals if they exist in a later package.
- Optional risk / consent hints if they exist in a later package.

11.1.3 documentation does not require Slot Binding implementation. Slot
Binding remains future scope.

Potential implementation location for a later package:

- `apps/api/app/services/task_planning/planner.py`
- `apps/api/tests/test_task_path_planner.py`

Do not create these files in this documentation pass.

## Planner Service Shape

The future implementation should use a small service boundary similar to:

```text
TaskPathPlanner

plan(
    task_intent: TaskIntent,
    candidates: list[LearnedPathCandidate],
) -> AgentDPlannerOutput
```

`AgentDPlannerOutput` is the existing schema class name from 11.1.1, but
documentation and user-facing language should call this the Task Path Planner
output. Agent D is only a legacy alias.

The planner should not call retrieval directly in its core planning method. The
caller should pass already-ranked candidates, keeping retrieval and planning
separate and testable.

## Candidate Selection Policy

The future planner implementation will select from already-ranked candidates.

Minimum policy:

- If the candidate list is empty, return unable-to-plan semantics.
- Ignore deprecated paths if any appear defensively.
- Prefer the top ranked confirmed candidate when no warnings require
  confirmation.
- Allow provisional candidates but preserve warnings and likely require
  confirmation.
- Allow flaky candidates only with explicit warnings and confirmation
  requirements.
- Treat close-ranked candidates as ambiguous and surface confirmation
  requirements instead of silently choosing.

The planner must not search the full catalog by itself, use embeddings, call
LLM providers, or select a path outside the passed candidate list.

## Candidate-to-RoutePlan Mapping

The future planner implementation will map selected LearnedPath candidates into
a minimal explainable `RoutePlan`.

The mapping should be conservative:

- One selected LearnedPath candidate produces one route step by default.
- A route step references the known `learned_path_id`.
- Route step purpose is derived from task intent and candidate scenario /
  page_template.
- Existing candidate warnings are copied to the route plan or route step.
- `match_reasons` remain available for review.
- The planner does not invent browser actions that are not represented by the
  LearnedPath asset.

This package does not implement RoutePlan generation. It only defines the
future mapping target.

## Warning / Risk / Confirmation Propagation

The future planner should propagate:

- flaky candidate warnings;
- drift evidence summary;
- negative evidence summary;
- low confidence / ambiguity warnings;
- risk hints from future policy layers;
- confirmation requirements for ambiguous, risky, destructive, external-send,
  bulk-modification, or permission-modification flows.

Risk and confirmation policy may be expanded in a later confirmation / consent
gate package. The planner should preserve enough structured data for that
later gate.

## No-Candidate and Ambiguous-Candidate Handling

No candidates:

- Return unable-to-plan semantics.
- Include a user-facing response hint for later conversation integration.
- Do not call autonomous run.
- Do not trigger hidden learning.
- Do not create a placeholder route plan that cannot execute.

Ambiguous candidates:

- Return a plan proposal that requires user confirmation, or return an
  ambiguous-plan result that lists candidate options.
- Preserve candidate reasons and warnings.
- Do not execute or silently choose a high-risk path.

Risky candidate:

- Preserve warnings.
- Add confirmation requirements.
- Do not execute in the planner.

## Test Plan

Future implementation tests should cover:

- empty candidates returns unable-to-plan and does not call autonomous run;
- deprecated candidate is ignored defensively;
- confirmed candidate can produce a minimal route-plan proposal;
- provisional candidate adds confirmation requirement;
- flaky candidate preserves warning and adds confirmation requirement;
- ambiguous close-ranked candidates require confirmation;
- planner does not call retrieval service from core planning method;
- planner does not import LLM, replay, autonomous explorer, raw HTML parser, or
  CLI modules;
- route plan preserves `learned_path_id`, `match_reasons`, and warnings;
- no user / account / tenant fields are introduced.

## Evidence Plan

Future implementation review should record:

- changed files;
- planner inputs / outputs;
- candidate selection behavior;
- route-plan mapping behavior;
- non-goals verified by import / source checks;
- test command output;
- `git diff --check` result.

11.1.3 documentation initialization only runs:

```bash
git diff --check
```

## Out of Scope

- Implementing planner service code.
- Modifying 11.1.1 schemas.
- Completing 11.1.2 retrieval implementation.
- Adding retrieval preview API.
- Adding CLI commands.
- Executing replay.
- Calling autonomous run.
- Reading raw HTML.
- Hidden relearning.
- LLM free planning.
- Real slot binding.
- Form filling.
- Result verification.
- Recovery dialogue.
- Teaching mode.
- Creating a 11.1.4 detail directory.

## Open Questions

- Whether future planner implementation needs a structured unable-to-plan enum
  or can reuse existing planner output uncertainty fields.
- Whether close-ranked ambiguity should be threshold-based or count-based.
- Whether future Slot Binding is a prerequisite for executing planner output or
  only needed for parameterized paths.
- Whether Task Path Planner implementation should remain fully deterministic
  in the first code package or allow a separately documented bounded LLM
  adapter later.
