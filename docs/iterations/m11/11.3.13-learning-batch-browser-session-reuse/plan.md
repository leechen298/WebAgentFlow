# Plan

状态：proposed

## Documentation Phase

1. Read current 11.3.12 parent / child package status.
2. Confirm package placement: new M11.3 sibling `11.3.13`, not `11.3.12.5`.
3. Inspect current browser lifecycle code.
4. Create 11.3.13 seven-document package.
5. Update M11 README index.
6. Update roadmap M11.3 post-closeout section and fix stale 11.3.12 status.
7. Record implementation authorization as `no`.

## Implementation Phase

1. Add test-only fake runtime factory coverage for capability discovery runtime count.
2. Add scenario reset helper / service.
3. Refactor `_run_capability_discovery()` to create one runtime around seed + scenario loop.
4. Ensure runtime closes in all normal / error / timeout / cancel paths.
5. Verify BrowserEventRecorder scenario isolation under runtime reuse.
6. Add batch summary reset metrics if small and useful.
7. Run scoped tests and hardcoding scan.

## Allowed Changes

- `LearningRunService._run_capability_discovery()`
- small helper under `apps/api/app/services/learning/`
- tests for learning run service / batch lifecycle / browser event recorder
- optional conversation history projection for reset/runtime counts
- docs for 11.3.13

## Forbidden Changes

- no `/users` special casing;
- no direct autonomous-run endpoint use;
- no live validation without explicit user approval;
- no changes to L1 / L2 / L3 lifecycle;
- no new Agent role;
- no replay runtime rewrite;
- no cross-batch browser reuse.

## Stop Conditions

Stop before implementation if:

- scenario reset cannot be made safe enough to prevent polluted evidence;
- BrowserEventRecorder leaks listeners across scenarios;
- tests require unauthorized live autonomous runs;
- implementation would require LLM step-by-step execution;
- package placement conflicts with M11 index / roadmap.

## Handoff

After docs generation:

```text
Review 11.3.13 contract / technical-design / test-plan.
If approved, set implementation_authorized: yes in review.md and implement.
```
