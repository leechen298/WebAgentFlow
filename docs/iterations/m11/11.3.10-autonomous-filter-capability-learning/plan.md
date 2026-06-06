# 实施计划（Implementation Plan）

状态：FOLLOW_UP_REQUIRED

## 输入

- `AGENTS.md`
- `docs/product-model.md`
- `docs/roadmap.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/m11/README.md`
- 用户提供的 11.3.10 文档输出计划

## 文档生成计划

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.10-autonomous-filter-capability-learning/` |
| Package type | umbrella / campaign |
| Parent / child route | parent package with two code/mixed child packages |
| Required docs | parent: README / intent / contract / plan / review / GOAL_RUNNER / CURRENT_STATE; child packages: full seven-document set |
| Source inputs read | repository docs listed above, current M11 index, iteration templates |
| Contract / status / evidence changes | parent defines capability-learning campaign route and evidence boundaries |
| Design-review gate | required for both child packages before runtime implementation |
| Test-plan trigger | required for both child packages because Agent / replay / autonomous run / UI / API boundaries are involved |
| Implementation authorization boundary | parent does not authorize implementation; child `review.md` controls implementation authorization |
| Stop conditions | missing docs, M11 index conflict, child docs conflict, live-run request missing explicit approval, runtime implementation attempted from parent |
| Handoff / checkpoint | active child starts at `11.3.10.1-filter-capability-discovery-learning` |

## Planned Package 1

| Field | Value |
|---|---|
| Package name | `11.3.10.1-filter-capability-discovery-learning` |
| Status | PACKAGE_COMPLETE |
| Type | code / mixed |
| Goal | Add target-agnostic autonomous discovery for filter capabilities and persist clean scenarios as LearnedPaths. |
| Why this exists | URL-only product learning currently collapses a rich filter page into one `#btn-search` click path. |
| Inputs / required reading | parent package docs; product model; autonomous explorer / action planner / learning run service / exploration router code; M10 LearnedPath contract; M11.3 chat docs. |
| Allowed changes | capability discovery service, scenario matrix, action planning/binding adapters, run metadata, LearnedPath ingest gating, tests, docs. |
| Forbidden changes | hardcoding `/users`, field names, button text, fixture data in runtime/prompt; changing product lifecycle stages; direct live-run evidence without approval; bypassing pass/evidence gates. |
| Expected deliverables | scenario inventory, single/pairwise/all-supported scenario generation, run history metadata, clean-pass LearnedPath ingest, test coverage. |
| Expected tests / verification | unit, integration, API/service regression; live autonomous run excluded unless user explicitly authorizes. |
| Compatibility constraints | old LearnedPaths remain readable; old run history remains readable; existing explicit replay and chat happy paths must not regress. |
| Scope guardrails | filter/search capability only; no full arbitrary page operation library; no exponential combination generation. |
| Exit criteria | child review records `PACKAGE_COMPLETE`, tests pass, no P0/P1 findings, parent CURRENT_STATE moves to child 2. |
| Handoff to next package | child 2 consumes child 1 outcome schema and capability summaries. |

## Planned Package 2

| Field | Value |
|---|---|
| Package name | `11.3.10.2-learning-outcome-gate-chat-feedback` |
| Status | PACKAGE_COMPLETE |
| Type | code / mixed |
| Goal | Summarize capability learning outcome and produce honest `wagent chat` success/partial/failure feedback. |
| Why this exists | Current feedback says “我学会了开始操作 / 帮我开始” even when learning evidence is weak or the alias came from a control choice. |
| Inputs / required reading | parent docs; child 1 completed docs/review; chat runtime; learning run result; conversation history/debug timeline; CLI tests. |
| Allowed changes | learning outcome aggregate, chat feedback templates, control-term identity filtering, history/debug timeline learning summary, CLI history path hint, tests. |
| Forbidden changes | faking success without child 1 evidence; adding failed/unverified actions to session learned catalog; requiring users to memorize fixed command phrases; running live validation without approval. |
| Expected deliverables | outcome status, capability summaries, feedback gate, learned action catalog filtering, history visible learning outcome. |
| Expected tests / verification | API/runtime unit tests, CLI tests, Console/API tests; live run excluded by default. |
| Compatibility constraints | explicit learn with real user goal still works; old history payload remains readable; existing learned actions continue matching. |
| Scope guardrails | feedback and outcome gate only; does not implement new discovery mechanics already scoped to child 1. |
| Exit criteria | child review records `PACKAGE_COMPLETE`, success/partial/failed/unverified cases tested, parent can close 11.3.10. |
| Handoff to next package | closeout / optional live validation only after user provides explicit approval. |

## 步骤

1. Create parent umbrella docs and `GOAL_RUNNER.md` / `CURRENT_STATE.md`.
2. Update M11 milestone README with parent and child package index entries.
3. Create child 1 seven-document set with reviewed design boundary.
4. Create child 2 seven-document set with child-1 dependency boundary.
5. Run documentation integrity checks: required files, M11 index search, no runtime code edits in this pass.
6. Record actual documentation evidence in parent and child `review.md`.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| parent docs | parent `review.md`; `CURRENT_STATE.md` | child docs can be generated | parent docs incomplete or M11 index conflict |
| child 1 docs | child 1 `review.md` design entry | implementation may start only if `implementation_authorized: yes` | missing technical design / test plan |
| child 2 docs | child 2 `review.md` design entry | waits for child 1 complete | attempts implementation before child 1 |
| closeout | parent `review.md` final status | docs generation complete | runtime code diff appears in this pass |

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.10* -maxdepth 1 -type f -print` | parent and children docs exist | Yes | docs-only generation evidence |
| `rg -n "11.3.10" docs/iterations/m11/README.md docs/iterations/m11/11.3.10*` | milestone index and package docs discoverable | Yes | no runtime execution |
| `git diff --name-only docs/iterations/m11/README.md docs/iterations/m11/11.3.10*` | scoped documentation diff | Yes | ensure no runtime implementation in this pass |

## 复核清单（Review Checklist）

- [x] Parent plan lists both child packages with required planned-package fields.
- [x] M11 README lists parent and both children.
- [x] Child 1 defines all supported filter controls and combination boundary.
- [x] Child 1 forbids target-specific runtime hardcoding.
- [x] Child 2 defines success / partial_success / failed / unverified.
- [x] Child 2 forbids control terms in learned action identity.
- [x] Both child packages include technical-design.md and test-plan.md.
- [x] No live autonomous run was executed in documentation generation.
