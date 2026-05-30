# 意图（Intent）

状态：PACKAGE_COMPLETE

## Problem

The post-fix live validation no longer fails because WAgent cannot find the
learned action. It now finds the learned action and routes to replay, but replay
blocks because the execute turn emits slot names that are semantically compatible
with, but not byte-identical to, the learned path's `value_slot` names.

The same evidence also shows a field-binding risk during learning: generic
multi-field planning can fill a search box or shift values across create-form
fields when slot names such as `record_name`, `record_category`, and `quantity` do
not exactly match the current `SemanticRole` vocabulary.

## Goal

Make the learn-then-execute path robust for target-agnostic business forms:

- learning should bind multi-field values to exact visible form fields when
  label / name / id / placeholder signals match the slot role or its aliases;
- execution should translate compatible slot aliases before deciding a learned
  path does not support parameter replacement;
- incompatible slots should still be blocked honestly.

## Non-goals

- No new internal Agent roles.
- No DB schema change.
- No external site source edit.
- No selector-specific or target-specific product logic.
- No claim of external validation pass until live rerun evidence supports it.
