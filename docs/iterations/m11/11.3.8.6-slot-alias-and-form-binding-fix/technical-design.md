# 技术设计（Technical Design）

状态：PACKAGE_COMPLETE

## Current State

`11.3.8.5` live validation produced:

```text
chat_learning_completed alias=create inventory item canonical_goal=create_inventory_item
router route_decision=delegate_to_web_operation_agent recommended_skill=start_replay
chat_execution_failed reason=unsupported_value_slot
unsupported_slots=["name", "category", "stock_quantity"]
```

The learned path stored generic `value_slot` keys such as `item_name`,
`item_category`, and `quantity`, while the execute intake emitted `name`,
`category`, and `stock_quantity`.

A later live rerun also showed execute intake can emit business-object-prefixed
semantic types such as `<object>_sku`, `<object>_name`, `<object>_category`, and
`<object>_quantity`, while the learned path stores the suffix slots.

## Design

### 1. Replay Slot Alias Resolution

In `apps/api/app/services/conversation/chat_runtime.py`, update
`_slot_overrides_for_path()` so it can translate execute-turn slot keys to a
supported learned path key using a small generic alias table.

Rules:

- exact learned slot wins;
- alias mapping only applies when exactly one supported learned slot matches the
  incoming slot alias;
- object-prefixed slot names may map by exact supported suffix only when the
  suffix match is unique;
- keep the learned slot key in the final `slot_overrides`;
- still report unsupported slots when no alias applies.

### 2. Field-Signal Matching In Action Planner

In `apps/api/app/services/learning/action_planner.py`, update
`_match_fillable_for_role()` so arbitrary business slot roles can match generic
field signals before loose fallback:

- normalize role and aliases into comparable tokens / phrases;
- inspect `semantic_role`, `label_text`, `id`, `name`, `placeholder`, and
  `aria_label`;
- rank exact label / name / id matches above placeholder containment;
- only use loose fallback when no field-signal match exists.

This keeps the code target-agnostic while avoiding a create-form value being
placed into a search field merely because the search field is prominent.

## Impact

- Chat runtime replay handoff.
- Learning action planner multi-field mode.
- Focused tests.

## Non-goals

- Do not change PageAnalysis schema.
- Do not add target-specific dictionaries.
- Do not alter autonomous-run endpoint behavior.
- Do not run direct replay as product validation evidence.

## Verification

See `test-plan.md`.
