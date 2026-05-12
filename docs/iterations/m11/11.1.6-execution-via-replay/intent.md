# 11.1.6 Execution via Replay

## Goal

Design the first confirmed-plan execution package for M11.1: when a
conversation has a confirmed-but-not-executed plan, WebAgentFlow can invoke
existing deterministic replay capability for that selected LearnedPath and
record replay execution evidence without claiming business-result success.

## Motivation

11.1.4 made ordinary user tasks visible as planning previews. 11.1.5 made user
consent explicit and auditable. The next step is execution, but only after
confirmation and only through the deterministic replay foundation already built
in M10 / 11.0.6.

This stage must remain narrower than task success:

- replay execution is a deterministic engine action;
- replay completion is not the same as verifying the business result;
- result verification and user-facing success reporting belong to later
  Result Verification and Task Result Reporter work;
- recovery, teaching, and hidden relearning are still out of scope.

## Why Confirmation Comes First

Execution changes page state. A planning preview is only a proposal; 11.1.5 is
the gate that records the user's explicit consent. 11.1.6 should only run when
that consent exists and the pending plan has not been cancelled, rejected, or
superseded.

## Why Deterministic Replay

The product model keeps execution anchored to known path assets. 11.1.6 must
reuse existing deterministic replay capability rather than:

- calling autonomous exploration;
- asking an LLM to control the browser step by step;
- reading raw HTML for ad hoc planning;
- inventing browser actions;
- relearning hidden paths.

If the confirmed plan cannot provide a `learned_path_id` and target URL / entry
context, execution should be blocked instead of guessed.

## Boundary

11.1.6 does not:

- reconstruct plans from raw user text;
- call the Task Path Planner again;
- perform slot binding or form filling beyond what the confirmed replay path
  already contains;
- verify postconditions;
- produce a Task Result Reporter summary;
- perform recovery;
- call autonomous run;
- connect an LLM provider.

## Success Criteria

- There is a clear execution precondition contract.
- Confirmed plan lookup is defined from auditable conversation evidence.
- Replay invocation requires explicit `learned_path_id + url` or equivalent
  entry context.
- Execution events are planned without claiming task success.
- Missing context returns unable-to-execute / needs-more-context semantics.
- Explicit replay command compatibility is preserved.
- Result verification remains future scope.
