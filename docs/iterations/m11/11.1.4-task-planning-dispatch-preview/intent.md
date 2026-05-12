# 11.1.4 Task Planning Dispatch Preview

## Goal

Design the conversation-runtime preview path for ordinary user tasks: accept a
natural-language task through the existing conversation surface, construct a
minimal `TaskIntent`, retrieve and rank LearnedPath candidates, call the Task
Path Planner, return a planning preview, record conversation evidence, and stop
before execution.

## Motivation

11.1.3 proves that the Task Path Planner can produce a deterministic planning
result from ranked candidates. That still is not enough to execute user tasks:
the conversation runtime must first expose planning results in a reviewable
form, distinguish ordinary task requests from explicit replay commands, and
preserve the audit trail before any future confirmation or execution package.

Preview comes before execution because WebAgentFlow must show what it plans to
do, why the selected path was chosen, and which warnings or confirmations exist.
Without this preview layer, execution would collapse planning, confirmation,
and replay into one step.

## Position in M11.1

- 11.1.1 defines the task planning contracts.
- 11.1.2 retrieves and ranks LearnedPath candidates.
- 11.1.3 maps ranked candidates into Task Path Planner output.
- 11.1.4 designs how conversation dispatch exposes that output as a preview.
- Later packages may implement confirmation / consent, execution via replay,
  result verification, Task Result Reporter, recovery, and teaching mode.

## Ordinary Task vs Explicit Replay

Explicit replay commands already require the user to provide
`/replay <learned_path_id> <url>` and are routed to deterministic replay hook
behavior. Ordinary task requests are different: the user provides intent, not a
specific path id. 11.1.4 must design the ordinary task preview path without
breaking explicit replay compatibility.

## Why Preview Must Preserve Evidence

The planning preview must preserve:

- retrieval `match_reasons`;
- candidate warnings;
- planner warnings;
- risk hints;
- confirmation requirements;
- unable-to-plan reasons.

These signals are required for later user confirmation, execution audit, result
reporting, and recovery. They also prevent the planner from becoming an
unreviewable agent decision.

## Deterministic-First Boundary

11.1.4 does not introduce LLM planning, raw HTML inspection, hidden relearning,
or browser operation. The MVP intent construction may be minimal and
deterministic:

- preserve the original user text as `raw_text`;
- optionally fill `normalized_goal` only when a deterministic rule is
  explicitly available;
- do not infer business parameters;
- do not perform slot binding.

## No-Candidate Policy

If retrieval returns no candidates, the preview path must return
unable-to-plan. It must not start autonomous learning, hidden relearning,
browser exploration, or a fake route plan. The conversation layer should
produce a clear user-readable response and record an auditable event.

## Future E2E Prerequisite

Conversation-level task planning tests need a stable preview output before
execution E2E can be meaningful. 11.1.4 is therefore a prerequisite for future
confirmation, execution, verification, and evidence packages.

## Success Criteria

- The future conversation dispatch preview boundary is documented.
- Explicit replay compatibility is preserved.
- Ordinary task request detection is defined.
- Deterministic `TaskIntent` construction is defined.
- Retrieval and Task Path Planner orchestration is defined without merging the
  two services.
- Planning preview message and event outputs are defined.
- Confirmation-pending and unable-to-plan semantics are defined.
- The documentation forbids replay execution, autonomous run, raw HTML
  planning, LLM planning, hidden relearning, slot binding, result verification,
  recovery, and teaching mode.
