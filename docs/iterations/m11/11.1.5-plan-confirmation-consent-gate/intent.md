# 11.1.5 Plan Confirmation and Consent Gate

## Goal

Design the confirmation and consent gate that handles user input while a
conversation is in `awaiting_confirmation` after a planning preview. The gate
must convert confirm, cancel, reject, clarification, and revision intent into
auditable conversation state without executing replay.

## Motivation

11.1.4 can produce a planning preview and ask the user to confirm before any
future execution. Without a dedicated confirmation / consent gate, the runtime
cannot reliably distinguish a clear approval from a cancellation, rejection,
ambiguous reply, or revised task request.

Execution must not start immediately after preview. The system needs a stable
decision boundary first, so later execution via replay can rely on explicit,
auditable user consent.

## Why Consent Must Be Explicit

Consent must be explicit because task execution may touch external websites,
submit forms, modify data, or trigger irreversible site-side effects in later
packages. Ambiguous input such as "maybe", "looks okay?", or unrelated free
text must not be interpreted as approval.

High-risk, flaky, provisional, ambiguous, destructive, external-send,
bulk-modification, and permission-modification plans require user confirmation.
In 11.1.5, even explicit confirmation only records consent or
ready-for-execution semantics. It does not execute replay.

## Position in M11.1

- 11.1.4 creates planning preview and moves proposed plans into
  `awaiting_confirmation`.
- 11.1.5 designs the decision gate for the user's response.
- Future execution via replay may consume confirmed plans.
- Future result verification and Task Result Reporter work only after
  execution evidence exists.

## Boundary

11.1.5 does not:

- execute replay;
- call autonomous run;
- perform hidden relearning;
- read raw HTML;
- connect an LLM provider;
- perform slot binding;
- fill forms;
- verify results;
- implement Task Result Reporter;
- implement recovery dialogue;
- implement teaching mode.

## Success Criteria

- Confirmation, cancellation, rejection, clarification, and revision intent are
  defined for `awaiting_confirmation`.
- Ambiguous input is never treated as consent.
- Confirmed plans become auditable confirmed / ready-for-execution state, not
  execution.
- Cancelled or rejected plans stop the pending preview.
- Event semantics are planned for user decisions.
- Explicit replay compatibility remains separated from pending preview handling.
- The behavior of `/replay` while awaiting confirmation is listed as an
  implementation decision that must be resolved before code work.
