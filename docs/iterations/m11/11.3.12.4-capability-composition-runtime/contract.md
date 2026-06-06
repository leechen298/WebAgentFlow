# Contract

状态：proposed

## Scope

This child package defines and implements the first scoped capability composition runtime for L3. It does not change
L1 / L2 / L3 lifecycle stages and does not add an internal Agent role.

## CapabilityCompositionPlan

`CapabilityCompositionPlan` is a deterministic runtime artifact. It is not a LearnedPath and is not proof that the
workflow succeeded.

Required public fields:

- `composition_id`
- `version`: initially `capability_composition.v1`
- `target_url`
- `page_template`
- `user_goal`
- `status`: `ready`, `missing_capability`, `ambiguous`, `unsafe`, `prefer_learned_path`, or `unsupported`
- `source_capability_ids`
- `ordered_steps`
- `expected_terminal_target`
- `risk_level`: `low`, `medium`, or `high`
- `confidence`: `high`, `medium`, or `low`
- `missing_capabilities`
- `rejection_reasons`
- `warnings`

Public plan fields must not expose raw selectors, raw DOM paths, raw Playwright payloads, target fixture values, or
private evidence details. Execution-specific bindings may exist only in an internal execution handoff object.

## Candidate Compatibility

A LearnedCapability may participate in a composition only when all required checks pass:

- page signature scope is compatible: page template matches, query signature is compatible, and DOM fingerprint is
  accepted by the policy;
- capability kind matches the requested operation category;
- trust is allowed by policy (`trusted` or explicitly permitted `provisional`);
- evidence is not failed / unverified-only and carries a valid terminal target summary;
- action schema version and adapter type are supported;
- required slots can be bound from user goal slots, safe sample value policy, or operator-approved values;
- control / region / terminal refs are compatible with the current PageAnalysis hints when current hints are available.

Cross-page composition is forbidden in this package.

## Ordering Rules

Code owns the ordered plan. Agent / LLM output may recommend semantic categories, but must not provide browser steps.

Allowed v1 ordering:

1. prerequisite region or tab switch capability;
2. one or more control capabilities;
3. submit / terminal-action capability when required;
4. terminal observation expectation.

Forbidden ordering behavior:

- arbitrary all-capability permutations;
- LLM-authored CSS selectors or Playwright commands;
- using a capability whose required slot is missing;
- executing a submit capability before required controls are bound;
- combining multiple capabilities that write conflicting values to the same control.

## LearnedPath Preference

If an existing high-confidence LearnedPath matches the goal and page scope, the runtime must prefer the LearnedPath
over composition. Composition may be returned only as a fallback candidate or diagnostic, not as the primary execution
path.

## Execution and Promotion Gate

Plan construction is not execution.

Promotion to LearnedPath requires:

- actual execution through approved replay / execution runtime;
- pass-gate success or existing equivalent execution evidence;
- terminal-state evidence compatible with the composition terminal target;
- source capability ids recorded on the promoted LearnedPath metadata if the current LearnedPath model supports it,
  or in existing JSON metadata without breaking old rows.

Failed composition must not be persisted as a successful LearnedPath. It may become negative capability evidence or a
learning / teaching recommendation in a later package.

## Public / Private Boundary

Public:

- composition summary, redacted step ids, source capability ids, generic kinds, risk, confidence, missing capability
  reasons, warnings.

Private:

- selectors from `action_schema_json.control_binding`;
- execution payloads;
- raw evidence details;
- Playwright/runtime handles.

Private fields must not be serialized into normal user-facing conversation responses or persisted public summaries.

## Runtime Hardcoding Prohibition

Runtime code must not hardcode:

- `/users`;
- target field labels;
- target button text;
- fixture data values;
- DOM test ids as target-specific answers;
- validation-site-only aliases;
- route-specific prompt text.

Target details may appear only in tests, fixtures, docs, and redacted artifacts.

## Compatibility Contract

- Existing LearnedPath rows remain readable and replayable.
- Existing LearnedCapability rows remain readable.
- Existing LearningBatch and ExplorationRun rows remain readable.
- Existing `wagent verify`, autonomous run, and `wagent chat` surfaces are not replaced by this package.
- No direct autonomous-run HTTP endpoints are called by tests or implementation.

## Implementation Authorization

Implementation requires reviewed `technical-design.md`, current `test-plan.md`, and
`implementation_authorized: yes` in `review.md`.
