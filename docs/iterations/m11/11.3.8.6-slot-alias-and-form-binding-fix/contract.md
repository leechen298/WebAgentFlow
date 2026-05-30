# 契约（Contract）

状态：PACKAGE_COMPLETE

## Runtime Contract

1. Learned action matching remains owned by `11.3.8.3`; this package must not
   weaken ambiguity / low-confidence protection.
2. A learned path may contain `value_slot` names from learning-time semantic
   types, while an execute turn may emit semantically equivalent slot aliases.
   The replay handoff may map a user-provided slot to a supported learned slot
   only when the alias relationship is generic and explicit.
3. Execute-turn slot names may include a business-object prefix before a
   supported field name. Replay handoff may strip leading underscore-separated
   prefix tokens only when the remaining suffix exactly matches one supported
   learned slot, or exactly one supported generic alias target.
4. Unsupported slot values must still block replay with `unsupported_value_slot`
   when no compatible learned slot exists.
5. Multi-field planning must prefer exact field-signal matches for the requested
   role or role alias before falling back to loose prominence ranking.
6. Field-signal matching may use generic sources available on
   `DiscoveredElement`: `semantic_role`, `label_text`, `id`, `name`,
   `placeholder`, and `aria_label`.
7. Runtime / prompts must remain target-agnostic. Validation target URL, route,
   selectors, seed values, labels, and implementation details may appear only in
   tests, docs, reports, or redacted artifacts.

## Generic Slot Alias Set

Allowed initial aliases:

- `name` <-> `record_name`
- `category` <-> `record_category`
- `record_quantity` <-> `quantity`
- `record_code` remains exact unless a future package documents generic record_code aliases.

These are target-agnostic semantic slot-name compatibility pairs derived from
learned-path `value_slot` names and execute-turn request slot names. They are
not Fixture-Site answer keys, field-label exceptions, operation aliases, or
selector knowledge.

Alias mapping is directional at replay handoff: preserve learned path
`value_slot` keys in `slot_overrides` so replay receives the keys stored in the
path.

Business-object-prefixed slots are target-agnostic: the prefix is not enumerated
or matched to a known site. A key such as `<object>_name` may map to `name` only
because `name` is a supported learned slot after exact suffix extraction.

## Public Surface

No public API, DB schema, response envelope, CLI option, Agent role, lifecycle
stage, or milestone vocabulary changes.

## Evidence Contract

Required before closing this package:

- focused RED/GREEN tests for slot alias handoff;
- focused RED/GREEN tests for form-field binding;
- focused chat runtime / action planner test suites;
- focused Ruff;
- forbidden target scan over product runtime / prompts / CLI / console /
  packages;
- rerun approved `11.3.8.5` live validation through `wagent chat`.

`PASS` requires live rerun evidence, not unit tests alone.
