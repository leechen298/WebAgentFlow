# Technical Design

Status: proposed

## Current State

<Current code, schema, service, and test state.>

## Contract Alignment / Invariants

Every key contract state, boundary, compatibility rule, and non-goal from
`contract.md` must map to an implementation mechanism or a reasoned `N/A`.

| Contract requirement | Implementation mechanism | Test coverage | Notes |
|---|---|---|---|
| <contract rule> | <schema/service/check, or `N/A` with reason> | <test file/case, or `N/A` with reason> | <risk/edge> |

## Proposed Implementation

<Concrete implementation approach for this iteration.>

## Affected Surfaces

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | Yes / No |  |  |
| API response schema | Yes / No |  |  |
| Database schema / migration | Yes / No |  |  |
| CLI | Yes / No |  |  |
| Console UI | Yes / No |  |  |
| Conversation events | Yes / No |  |  |
| Replay execution | Yes / No |  |  |
| Reporter | Yes / No |  |  |
| Worker / async jobs | Yes / No |  |  |
| Tests / fixtures | Yes / No |  |  |
| Docs | Yes / No |  |  |

## Data Model / Schema Changes

<New or changed schemas, request/response fields, migrations, and compatibility notes.>

## Service / Module Design

<Services/modules/functions to add or change, including input/output shape.>

## Data Flow

<Flow from entrypoint to output, including intermediate events or persisted state.>

## Status / State Derivation

<How status is derived, including precedence and fallback behavior.>

## Compatibility

<How old data, old API responses, and existing callers remain compatible.>

## Failure / Edge Cases

<Nulls, timeouts, partial results, provider failures, stale data, or unsupported states.>

## Non-goals

- <Implementation scope this iteration explicitly does not cover.>

## Test Matrix

| Case | Coverage | Expected Result |
|---|---|---|
| <case> | <unit / integration / E2E / doc check> | <expected result> |

## Validation Commands

```bash
<command>
```
