# M12 · Failure Recovery / Abort / Runtime Robustness

Status: completed with follow-ups.

M12 turns failure, blocked execution, uncertainty, and user abort into
auditable runtime decisions. It is the follow-up layer after the M11.1
task-to-path MVP: M11.1 can plan, confirm, execute through replay, and report
`failed` / `blocked` / `uncertain` / `needs_review`; M12 decides what
WebAgentFlow may safely ask, propose, retry, or stop after those outcomes.

M12 is not an automatic page-repair layer. It must not hide recovery,
relearn paths behind the operator's back, or continue operating the browser
without explicit user consent.

## Relationship to Earlier Work

- **M10** provides LearnedPath persistence, catalog, replay execution, and
  drift signals.
- **M11.0** provides the runtime conversation surface and Conversation
  Orchestrator / Dispatcher foundation.
- **M11.1** provides the task-to-path happy path and conservative result
  reporting. `replay completed` is not task success; `uncertain` and
  `needs_review` are valid outputs.
- **M12** starts where M11.1 stops: failure classification, abort handling,
  recovery proposal, retry policy, and auditable user choice.
- **M11.2 Runtime Observation / Wait-for-change** remains a separate line of
  work. M12 may later consume richer observation, but this documentation
  initialization does not design or implement M11.2.

## Iteration Index

- [m12-plan](./m12-plan.md) — M12 overview and future package split. Status:
  in progress.
- [12.0-failure-recovery-abort-runtime-robustness](./12.0-failure-recovery-abort-runtime-robustness/) —
  M12 scope, terms, and safety boundary. Status: documentation initialized.
- [12.1-failure-classification-recovery-boundary](./12.1-failure-classification-recovery-boundary/) —
  failure classification and recovery boundary classifier. Status:
  implemented / shipped.
- [12.2-user-abort-stop-handling](./12.2-user-abort-stop-handling/) —
  user abort / stop handling boundary. Status: implemented / shipped.
- [12.3-recovery-proposal-mvp](./12.3-recovery-proposal-mvp/) —
  recovery proposal MVP. Status: implemented / shipped.
- [12.4-retry-rerun-policy](./12.4-retry-rerun-policy/) —
  retry / re-run policy. Status: implemented / shipped.
- [12.5-recovery-conversation-flow](./12.5-recovery-conversation-flow/) —
  recovery conversation flow. Status: implemented / shipped.
- [12.6-recovery-tests-and-evidence](./12.6-recovery-tests-and-evidence/) —
  recovery tests and evidence closure. Status: evidence closed / reviewed.
  Completion: `m12_completed_with_followups`.

## Core Runtime Terms

| Term | Meaning in M12 |
|---|---|
| `failure` | Execution ran and produced negative evidence: replay failed, drifted, hit an error, or visible/result evidence contradicts the intended task. |
| `blocked` | WebAgentFlow cannot safely execute or verify because required context, permission, target page state, or supported capability is missing. |
| `uncertain` | Execution may have run, but WebAgentFlow does not have enough postcondition evidence to claim the business task succeeded. |
| `needs_review` | A user or later review step must inspect the evidence before WebAgentFlow can treat the outcome as resolved. |
| `user abort` | The user explicitly stops or interrupts a run. This is not an engine error; it starts the abort handling path. |

## Hard Boundaries

- No autonomous recovery by default.
- No hidden relearning.
- No automatic autonomous exploration.
- No raw HTML free-form planning.
- No default dependency on an LLM provider.
- No continuing browser operation after user abort without a new user choice.
- No rewriting `uncertain` or `replay completed` into success.
- No recovery proposal execution without user confirmation.
