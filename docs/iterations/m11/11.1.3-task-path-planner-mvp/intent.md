# 11.1.3 Task Path Planner MVP Design

## Goal

Define the MVP design for a future Task Path Planner: a deterministic-first
planning boundary that consumes user task intent and ranked LearnedPath
candidates, then produces a minimal, explainable route-plan proposal for later
confirmation and execution.

This package initializes documentation only. It does not implement planner
code.

## Motivation

M11.0 proved that users can talk to WebAgentFlow through the runtime
conversation loop and can trigger explicit replay when they already know a
LearnedPath id and URL. 11.1.1 defined the task-to-path planning contracts.
11.1.2 defines how LearnedPath candidates are retrieved and ranked.

The next risk is letting planning logic become an uncontrolled agent. The Task
Path Planner must not browse pages, read raw HTML, control Playwright step by
step, perform hidden relearning, or invent actions outside known LearnedPath
assets. It needs a documented boundary before implementation starts.

## Position in M11.1

- LearnedPath Retrieval and Ranking narrows the catalog into ranked candidates.
- The future Task Path Planner selects from those candidates and explains a
  route-plan proposal.
- Confirmation / consent gate decides whether a risky or uncertain plan can be
  executed.
- Execution via replay runs only confirmed deterministic routes.
- Task Result Reporter consumes execution and verification evidence later; it
  does not drive planning.

## Deterministic-First Boundary

11.1.3 keeps planner design deterministic-first because the first task-to-path
MVP must be explainable, testable, and reviewable. If a later package adds LLM
assistance, it must remain bounded by task intent, retrieved candidates,
available evidence, and explicit route-plan schema.

The planner must not:

- read raw HTML;
- call page analyzer;
- call autonomous run;
- perform hidden relearning;
- select paths outside the retrieval result set;
- execute replay;
- fill forms;
- perform recovery dialogue;
- implement teaching mode.

## No-Candidate Policy

When no candidates are available, the future planner must return an explicit
unable-to-plan result or equivalent planning status. It must not automatically
start autonomous learning, hidden relearning, path discovery, or browser
execution.

## Explainability Requirement

The future planner output must preserve why a candidate was selected:

- `match_reasons` from retrieval;
- warnings from trust, drift, or flaky status;
- confirmation requirements for ambiguous or risky plans;
- uncertainty flags when the plan is incomplete.

These signals are required so later confirmation, execution, result reporting,
and recovery can audit what happened.

## Success Criteria

- The future planner service boundary is documented.
- Inputs and outputs are aligned with 11.1.1 schemas.
- Candidate selection and candidate-to-RoutePlan mapping are defined as future
  implementation targets.
- RoutePlan is clearly described as a design target, not this documentation
  pass's implemented artifact.
- The documentation forbids replay execution, LLM free planning, raw HTML
  planning, autonomous run, hidden relearning, and real slot binding.
