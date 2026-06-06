# Intent

状态：proposed

## Goal

Implement a target-agnostic Page Understanding capability hint layer so bounded learning can plan capability
probes from structured page semantics instead of only raw discovered controls.

## Motivation

11.3.12.1 added durable `LearnedCapability` assets. 11.3.12.2 added durable learning batches and bounded
scenario execution. The next gap is scenario quality: current filter discovery mostly infers from raw
fillable / toggle / select elements. It lacks explicit page regions, terminal targets, dependency hints, and
sample value sources. Without those hints, later composition risks either under-learning useful atomic
capabilities or expanding combinations too broadly.

## Success Criteria

- Page analysis exposes a target-agnostic capability hint set.
- Hints identify candidate regions, controls, terminal targets, sample-value sources, and dependency groups.
- Bounded learning can consume hints without hardcoding a route, field label, fixture selector, or seed value.
- Existing PageAnalysis consumers remain compatible.
- Unit / regression tests prove hints are deterministic, redacted, and do not trigger live browser runs.

## Non-goals

- No runtime capability composition.
- No LearnedCapability trust promotion rules beyond existing ingest.
- No Console UI.
- No live validation, `verify-scenario`, or product UI autonomous run.
- No route-specific `/users` logic or validation-site wording in runtime code.
