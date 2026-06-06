# Contract

状态：proposed

## Scope

本包只定义并实现 `LearnedCapability` 资产基础。它不改变 L1 / L2 / L3 lifecycle，不新增 Agent
角色，不改变现有学习、replay、chat runtime 或 pass_gate 语义。

## LearnedCapability Identity

Required identity fields:

- `page_template`: normalized page path template, same conceptual scope as LearnedPath.
- `query_signature`: JSON object for stable query shape.
- `dom_fingerprint`: page fingerprint at learning time.
- `capability_key`: stable human-readable key within a page signature.
- `capability_kind`: operation category.
- `region_ref`: stable region reference, not a raw selector-only identity.
- `control_ref`: stable control reference; may include selector hints in debug evidence but public schemas must not expose unsafe raw detail by default.
- `terminal_target_json`: expected terminal target evidence shape.
- `dedup_key`: sha256 over canonical identity payload.

`dedup_key` must include page signature, `capability_kind`, `region_ref`, `control_ref`, and
`terminal_target_json`. It must not include sample runtime values that would prevent reusable capability dedup.

## Capability Kinds

Allowed initial kinds:

- `control_input`
- `control_select`
- `control_toggle`
- `submit_search`
- `reset_filters`
- `switch_tab`
- `open_detail`
- `export_download`
- `show_modal_or_toast`
- `unknown`

Unknown or unsupported controls may be recorded as failed evidence in future batch summaries, but this child only stores successful or provisional `LearnedCapability` rows.

## Trust and Provenance

Use the existing trust vocabulary for asset-level trust:

- `provisional`
- `confirmed`
- `flaky`
- `deprecated`

Use existing provenance values:

- `system`
- `user`

Trust on a capability is independent from LearnedPath trust. Changing capability trust must not mutate any LearnedPath trust.

## Evidence Contract

`evidence_json` must be a JSON object. Required keys for stored rows:

- `version`: `"capability_evidence.v1"`
- `source`: `"exploration_run"` or `"user_demonstration"`
- `terminal_outcome`: string summary such as `terminal_detected`, `terminal_unverified`, or `not_recorded`
- `business_match_observed`: boolean or null
- `evidence_strength`: `strong`, `medium`, or `weak`
- `warnings`: array of strings
- `redaction`: object describing whether selectors/raw text are hidden from normal schemas

Normal public summaries must not expose raw selectors, raw DOM snippets, seed fixture data, or validation-site-only labels.
Debug/detail schemas may expose structured evidence only when explicitly documented by the schema.

## Action Schema Contract

`action_schema_json` describes how the operation can be attempted later, but it is not executable authorization.

Required keys:

- `version`: `"capability_action.v1"`
- `adapter_type`
- `operation`
- `required_slots`
- `control_binding`

It must not contain direct Playwright commands or LLM-generated step-by-step instructions.

## LearnedPath Compatibility

Existing `learned_paths` rows must stay readable and replayable.

This child does not modify `learned_paths`.

Future composition metadata, if still needed, must be designed in the runtime composition child package.

No existing LearnedPath API field may be removed or renamed.

## API Contract

No HTTP API is implemented in this child.

The Pydantic schemas created here are repository/service boundary schemas and future API building blocks.
Read-only HTTP routes may be designed in a later debug/API child package.

## Runtime Hardcoding Prohibition

Runtime code must not hardcode:

- `/users`
- target field labels
- target button text
- fixture data values
- DOM test ids
- validation-site-only aliases
- route-specific prompt text

Target details may appear only in tests, fixtures, docs, and redacted artifacts.

## Implementation Authorization

This contract does not authorize implementation by itself. Implementation requires reviewed
`technical-design.md`, reviewed `test-plan.md`, and `implementation_authorized: yes` in `review.md`.
