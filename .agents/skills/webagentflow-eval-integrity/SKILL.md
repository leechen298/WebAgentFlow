---
name: webagentflow-eval-integrity
description: Use for WebAgentFlow eval and evidence-integrity checkpoints when validating runtime behavior, eval runners, user-facing behavior tests, closeout reviews, forbidden target scans, artifact redaction, and PASS/FAIL/BLOCKED/UNVERIFIED decisions. Also use inside Codex App /goal campaigns when GOAL_RUNNER.md or CURRENT_STATE.md routes the active checkpoint to eval, evidence review, closeout, or final status gating. This skill protects evidence boundaries; it does not implement product behavior.
---

# webagentflow-eval-integrity

## Purpose

Use this skill when validating WebAgentFlow product-level runtime behavior, eval runners, closeout reviews, or evidence artifacts.

This skill is responsible for eval integrity, not feature implementation. Its job is to answer whether a claimed eval result is trustworthy, whether the product was exercised through an allowed surface, whether the evidence supports the conclusion, and whether the status should be `PASS`, `FAIL`, `BLOCKED`, or `UNVERIFIED`.

## When to use

Use this skill for:

- user-facing WAgent behavior evals
- runtime eval runner review
- closeout review
- forbidden target scans
- anti-hardcoding review
- artifact redaction review
- pass / fail / blocked / unverified decisions
- live eval vs non-live eval distinction
- direct replay / autonomous-run substitution checks
- scope isolation checks for known / unknown learned actions

Do not use this skill as the primary workflow for implementing product behavior. Use `webagentflow-iteration-dev` for implementation work, then use this skill for integrity review and closeout gating.

## Goal Mode Integration

In Codex App `/goal` campaigns, this skill is the checkpoint-level integrity
gate for eval, evidence, closeout, and final status decisions. It is not the
campaign runner and it must not implement product behavior.

Before reviewing evidence, read `GOAL_RUNNER.md` and `CURRENT_STATE.md` when
present, then identify the active child package, required gates, allowed
validation surface, hard stops, stable latest artifact requirements, and final
status vocabulary.

Use this skill when the active checkpoint asks whether a result is trustworthy,
whether a campaign may advance, or whether evidence supports `PASS`, `FAIL`,
`BLOCKED`, `UNVERIFIED`, `NON_LIVE_PASS`, or `PASS_WITH_CAVEATS`.

If the evidence shows a product defect, forbidden runtime target detail, scope
contamination, missing redaction, missing stable artifact, failed required gate,
or unresolved P0/P1 finding, report the integrity decision and route the fix
back to implementation work.

A `/goal` campaign may advance only when the owning contract allows the
resulting status. `UNVERIFIED`, `BLOCKED`, unresolved P0/P1 findings, missing
reviewable evidence, or unapproved live-run requirements must stop campaign
progress.

## Non-goals

This skill must not be used to:

- implement new planner, replay, learning, or runtime product capability
- rewrite product prompts to make a specific eval pass
- convert failing evals into pass by changing wording only
- treat cleanup follow-ups as substitutes for required gates
- produce hidden direct-service evidence and call it product evidence

Small eval observability fixes are allowed only when explicitly scoped and documented. If product behavior must change, switch to the implementation workflow and return to this skill after the fix.

## Hard rules

1. Product runtime and product prompts must be target-agnostic.
2. Product-test-site details may only appear in fixture source, eval specs, tests, docs, reviews, testing results, and redacted artifacts.
3. Product runtime and product prompts must not contain target route, URL, DOM test id, fixture item names, button labels, field labels, placeholder text, fixture selectors, or operation aliases from test targets.
4. There is no grandfather exception for existing test-site special cases. Existing target-specific runtime logic is a blocker until removed, or the iteration must be explicitly marked `BLOCKED`.
5. Direct replay API results cannot be used as WAgent chat runtime pass evidence.
6. Autonomous-run / verify-scenario surfaces cannot be used unless the iteration explicitly allows that surface and the repository execution-boundary rules are followed.
7. Eval-only candidate binding must be labeled as eval-only and cannot be claimed as full live product capability.
8. Unknown-page cases must isolate old LearnedPath data by fresh session, isolated eval scope, or explicit filtered catalog.
9. Private ids, private maps, selectors, slot overrides, evidence targets, ReplayAction payloads, execution payloads, credentials, tokens, cookies, and secrets must not appear in public committed artifacts.
10. Missing evidence must be marked `UNVERIFIED`, `WARNING`, `BLOCKED`, or `FAIL`. It must not be inferred as pass.
11. Required gates decide pass/fail. Codex natural-language judgment does not decide pass/fail.
12. Cleanup follow-up cannot turn a blocker into pass.

## Decision vocabulary

Use these terms consistently:

- `PASS`: all required gates pass with reviewable evidence.
- `FAIL`: a required gate ran and failed.
- `BLOCKED`: a forbidden condition, environment issue, missing precondition, or scope contamination prevents valid evaluation.
- `UNVERIFIED`: an eval ran, but the evidence is insufficient or not reviewable.
- `NON_LIVE_PASS`: non-live tests pass, but no live Conversation runtime eval was run.
- `PASS_WITH_CAVEATS`: required gates pass, but documented caveats limit the capability claim.

Important equivalences:

- `UNVERIFIED` is not pass.
- `BLOCKED` is not pass.
- `NON_LIVE_PASS` is not live product pass.
- eval-only binding pass is not full live product capability pass.
- a cleanup issue does not waive a required gate.

## Required review workflow

1. Read the iteration `README.md`, `contract.md`, `technical-design.md`, `test-plan.md`, `plan.md`, and `review.md` when present.
2. Identify eval target details and forbidden tokens from the contract, test plan, eval spec, or target manifest.
3. Run a forbidden target scan against product runtime and product prompts.
4. If target-specific constants appear in product runtime or product prompts, mark the eval `BLOCKED` unless the iteration itself is explicitly blocked.
5. Check known / unknown state isolation. Global old LearnedPaths must not turn unknown-page cases into known-page cases.
6. Check that the eval runner uses the allowed product surface. Direct replay, direct internal service import, and direct autonomous-run endpoint calls are not substitutes for WAgent chat evidence unless the iteration explicitly permits them.
7. Run eval commands only when the iteration and repository execution-boundary rules allow them.
8. Inspect JSON and Markdown artifacts, including stable latest artifacts when required.
9. Run artifact redaction checks before treating artifacts as reviewable or commit-ready.
10. Compare result status with required gates and report `PASS`, `FAIL`, `BLOCKED`, or `UNVERIFIED` from evidence.
11. Update review / closeout only with evidence-backed conclusions and explicit caveats.

## WebAgentFlow evidence boundaries

Follow the repository execution-boundary rules exactly:

- Do not call autonomous-run endpoints directly by curl, fetch, httpx, inline scripts, or service imports.
- Do not import internal autonomous explorer services to create Agent-operated evidence.
- Use project-provided eval CLIs only when that surface is the requested validation path.
- Live UI smoke is allowed only when the user explicitly asks for UI smoke / browser validation, and product UI actions must be reported as external-operator actions.
- Do not summarize a run as pass unless the authoritative product gate says pass.

## Built-in helper scripts

The helper scripts are deterministic local checks. They do not replace product evals, but they block untrustworthy eval claims.

### forbidden_target_scan.py

Use this before running or accepting target-specific evals.

Example:

```bash
python .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py \
  --manifest docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval/target-manifest.json \
  --root /Users/leechen/projects/WebAgentFlow/v0.1
```

Expected manifest shape:

```json
{
  "target_name": "product-test-site-items",
  "forbidden_tokens": ["/items", "item-list", "测试项目A"],
  "forbidden_paths": ["apps/api/app/services", "apps/cli/wagent", "apps/console/src"],
  "allowed_paths": ["apps/product-test-site", "scripts/evals", "apps/api/tests", "docs", "artifacts"]
}
```

Any match under forbidden product paths makes the eval `BLOCKED` until removed or explicitly marked blocked.

### eval_artifact_redaction_check.py

Use before committing eval artifacts or review documents.

It scans committed/public artifacts for private payload terms, selectors, secret-like keys, and internal execution payload names. A match means the artifact is not safe to publish until redacted or explicitly moved to local-only ignored storage.

### eval_result_gate_check.py

Use after an eval produces JSON results. It reads the result, checks required gates / cases where detectable, and emits an integrity decision. The script is conservative: ambiguous or missing required gate evidence becomes `UNVERIFIED` or `BLOCKED`, not pass.

## 11.3.7 reference workflow

For `11.3.7 User-facing WAgent Behavior Eval`:

1. Read `contract.md`, `test-plan.md`, and `review.md`.
2. Extract or create a target manifest from the eval spec. The manifest belongs in the eval layer, not product runtime.
3. Run `forbidden_target_scan.py` against product runtime and product prompts.
4. If product runtime contains target-specific constants such as route, URL, DOM test id, fixture item name, button text, field label, or operation alias, mark `11.3.7` as `BLOCKED`.
5. Verify known / unknown setup isolation. Known must come from current eval session or explicit eval scope. Unknown must use fresh session, isolated scope, or explicit filtered catalog.
6. Run the required user-facing eval cases only through the allowed product conversation surface.
7. Confirm first-wave required scenarios include:
   - `url_only_known_page`
   - `url_only_unknown_page`
   - `execute_known_action`
   - `execute_unknown_action`
   - `vague_input_no_execution`
   - `forbidden_test_target_not_in_runtime_code_or_prompts`
   - `url_only_unknown_choose_learn_starts_learning`
   - `execute_unknown_choose_learn_then_execute_or_learning_flow`
8. If `learn_then_execute` is not product-supported, record the narrower learning-flow result and an explicit follow-up. Do not claim full learn-then-execute pass.
9. Inspect artifacts and run redaction checks.
10. Update review with `PASS`, `FAIL`, `BLOCKED`, or `UNVERIFIED`, plus exact evidence and caveats.

## Relationship to webagentflow-iteration-dev

Recommended loop:

1. `webagentflow-iteration-dev` implements the approved design.
2. `webagentflow-eval-integrity` validates the implementation and evidence.
3. If `FAIL` or `BLOCKED`, return to implementation work.
4. If `PASS`, use this skill for closeout wording and evidence integrity.

Keep the responsibilities separate: implementation does not certify itself.

## Reporting template

Use a short, evidence-first report:

```text
Decision: BLOCKED
Reason: product runtime contains target-specific test fixture constants.
Evidence:
- apps/api/app/services/conversation/chat_runtime.py:123 contains forbidden token `/items`.
- apps/api/app/services/conversation/intake.py:88 contains forbidden token `item-list`.
Impact: 11.3.7 cannot be claimed as product-generic behavior.
Next step: remove target-specific runtime logic or mark 11.3.7 blocked with cleanup issue.
```

For clean pass:

```text
Decision: PASS
Scope: user-facing WAgent behavior eval, first-wave required cases.
Evidence:
- forbidden target scan: pass, 0 matches in product runtime/prompts.
- known/unknown isolation: pass, fresh eval scope used for unknown cases.
- eval result: all required cases pass.
- redaction scan: pass, public artifacts contain no private payloads.
Caveats: list any non-blocking caveats exactly.
```
