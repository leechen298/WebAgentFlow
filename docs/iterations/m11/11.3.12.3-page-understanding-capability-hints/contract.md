# Contract

状态：proposed

## Scope

This child package defines and implements Page Understanding capability hints for L1 learning. It does not
change L1 / L2 / L3 lifecycle stages and does not add an internal Agent role.

## CapabilityHintSet

`CapabilityHintSet` is a deterministic, redacted, page-level hint projection attached to PageAnalysis.

Required fields:

- `version`: initially `capability_hints.v1`.
- `page_purpose`: generic page purpose when inferable, for example `list_management`, `detail_view`,
  `form_entry`, `settings`, or `unknown`.
- `regions`: list of page regions with stable ids and generic roles.
- `controls`: list of control capability candidates.
- `terminal_targets`: list of likely terminal observation targets.
- `sample_value_sources`: list of generic sample value sources.
- `dependency_groups`: list of control dependencies that justify pair probes.
- `warnings`: conservative caveats.

## Public Hint Projection vs Executable Bindings

This package must keep two references separate:

- Public / serialized hint refs: `region_ref`, `control_ref`, `terminal_target_ref`, and dependency source refs are
  stable redacted ids. They are safe to include in PageAnalysis responses, persisted summaries, logs, tests, and
  user-facing learning feedback.
- Private executable bindings: runtime-only resolver state may map those redacted ids back to existing
  `DiscoveredElement` bindings such as selectors, element ids, frame context, and action metadata. This resolver is
  not part of `CapabilityHintSet`, must not be serialized in PageAnalysis, and must not be persisted in
  LearnedCapability evidence summaries.

Capability discovery may use the public hint ids to choose scenarios, but actual execution must resolve back through
the private resolver or the original `DiscoveredElement` inventory. A valid implementation cannot satisfy redaction by
dropping executable bindings, and cannot satisfy execution by exposing selectors in serialized hints.

## Region Hints

Allowed region roles:

- `filter_region`
- `result_region`
- `action_bar`
- `tab_region`
- `modal_region`
- `detail_region`
- `form_region`
- `pagination_region`
- `unknown`

Region hints must not expose raw selectors in normal projections. Stable region ids may be derived from
structural position and role, not target names.

## Control Hints

Control hints describe possible atomic capabilities:

- `control_input`
- `control_select`
- `control_toggle`
- `submit_search`
- `reset_filters`
- `switch_tab`
- `open_detail`
- `export_download`
- `show_modal_or_toast`

Each control hint must include:

- stable `hint_id`;
- `capability_kind`;
- generic redacted `region_ref`;
- redacted `control_ref`;
- `adapter_type`;
- `confidence`;
- `support_status`: `supported`, `unsupported`, or `unknown`;
- optional `terminal_target_ref`;
- warnings.

`control_ref` is a hint reference, not a CSS selector, XPath, accessible label, test id, or raw DOM path.

## Sample Value Sources

`sample_value_sources` describe where safe probe values may come from. They do not directly authorize target-specific
seed data in serialized hints.

Allowed source kinds:

- `generated_by_type`: runtime may synthesize a generic value from the control adapter type, for example a harmless
  short text probe for a text input.
- `static_safe_default`: runtime may use a code-owned generic value that is not copied from the target page or fixture
  data.
- `empty_safe_probe`: runtime may submit an empty value only when the control and terminal target make that safe.
- `existing_option_value_redacted`: evidence may record that an existing option exists, but serialized hints must keep
  the value redacted. Runtime may use the original option value only through the private resolver in the same analysis
  context.
- `operator_supplied`: runtime may use a value supplied by the user/operator through an approved product surface.

Only `generated_by_type`, `static_safe_default`, `empty_safe_probe`, and approved `operator_supplied` values may be
materialized directly from serialized hints. `existing_option_value_redacted` is evidence-only in serialized form and
requires private resolver access before execution.

## Dependency Hints

Dependency groups justify bounded dependency-pair probes. They are opt-in evidence, not a default pairwise
matrix.

Allowed dependency kinds:

- `range_pair`
- `cascader_chain`
- `tab_scoped_controls`
- `filter_requires_submit`
- `modal_requires_open`

Dependency hints must cite generic source refs, not target labels or values.

## Terminal Target Hints

Terminal target hints may describe:

- `list_refresh`
- `empty_result`
- `query_persisted`
- `url_query_changed`
- `modal_opened`
- `toast_shown`
- `download_started`
- `detail_visible`
- `unknown`

Empty results remain valid weaker evidence when request completion or result refresh is observable.

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

- Existing PageAnalysis fields remain available.
- Existing `build_filter_inventory()` behavior remains compatible when hints are absent.
- 11.3.12.2 bounded policy still defaults to independent single-capability probes.
- Existing LearnedPath and LearnedCapability rows remain readable.
- No direct autonomous-run HTTP endpoints are called by tests or implementation.

## Implementation Authorization

Implementation requires reviewed `technical-design.md`, current `test-plan.md`, and
`implementation_authorized: yes` in `review.md`.
