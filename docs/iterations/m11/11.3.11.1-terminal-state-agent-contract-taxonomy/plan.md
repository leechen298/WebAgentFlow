# 实施计划（Implementation Plan）

状态：proposed

## 输入

- `AGENTS.md`
- `docs/product-model.md`
- `docs/roadmap.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- parent `11.3.11-terminal-state-agent-learning-stop-control`
- this package `intent.md`
- this package `contract.md`
- this package `technical-design.md`
- this package `test-plan.md`

## 文档生成计划

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy/` |
| Package type | `mixed` |
| Parent / child route | child 1 of `11.3.11-terminal-state-agent-learning-stop-control` |
| Required docs | `README.md`, `intent.md`, `contract.md`, `technical-design.md`, `test-plan.md`, `plan.md`, `review.md` |
| Source inputs read | repository rules, product model, roadmap, iteration standards, parent docs |
| Contract / status / evidence changes | Adds terminal-state evidence contract, optional Terminal State Agent scoped evaluator boundary, taxonomy, evidence strength and stop decision docs |
| Design-review gate | required before any child 2 runtime work |
| Test-plan trigger | required because Agent/evidence/live-boundary semantics are changed |
| Implementation authorization boundary | child 1 never authorizes runtime implementation; child 2 must record its own authorization |
| Stop conditions | product-model conflict, legacy Agent letter invented, runtime code touched, live validation attempted, P0/P1 review finding |
| Handoff / checkpoint | after design review, route parent to `11.3.11.2-browser-event-recorder` docs/implementation gate |

## 文件 / 模块

- `docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy/*` - child seven-document set.
- `docs/product-model.md` - scoped product-model update for terminal-state evidence handoff and no-Agent-I boundary.
- `docs/roadmap.md` - scoped M11.3 post-closeout / M14 reuse wording.
- `docs/iterations/m11/README.md` - child package discoverability.
- `docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control/CURRENT_STATE.md` - parent checkpoint.

## 步骤

1. Create child seven-document package.
2. Update product model with terminal-state evidence handoff, no-Agent-I boundary, and optional Terminal State Agent no-legacy-alias wording.
3. Update roadmap and M11 index so child 1 route is discoverable.
4. Update parent `CURRENT_STATE.md` from child docs not created to child docs review state.
5. Run docs integrity commands from `test-plan.md`.
6. Record actual evidence, not-run items and implementation authorization in `review.md`.
7. Stop before child 2 implementation unless parent route explicitly advances and child 2 docs are created/reviewed.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| docs generation | child `review.md` records design review and commands | no P0/P1, docs checks pass | missing docs or template residue |
| parent route | parent `CURRENT_STATE.md` updated | route points to next allowed child | parent/child conflict |
| closeout | child `review.md` FINAL_STATUS | `PACKAGE_COMPLETE` for docs child | any runtime/live claim without evidence |

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy -maxdepth 1 -type f -print | sort` | seven docs exist | Yes | docs-only |
| `rg -n "Terminal State Agent|no legacy alias|11\\.3\\.11\\.1|implementation_authorized|live autonomous validation" ...` | role, route and live boundary discoverable | Yes | docs-only |
| `rg -n "T[B]D|T[O]DO" ...` | no template residue | Yes | docs-only |
| `git diff --check` | whitespace clean | Yes | whole diff |

## 复核清单（Review Checklist）

- [ ] `contract.md` defines terminal taxonomy, outcome, evidence strength and stop decision.
- [ ] Product model update preserves L1 / L2 / L3 and legacy A-H aliases.
- [ ] Roadmap places 11.3.11 under M11.3 post-closeout and only references M14 as future reuse.
- [ ] No runtime code / API / schema / DB / CLI / Console files changed by this child.
- [ ] Live validation remains not run.
- [ ] Parent `CURRENT_STATE.md` does not authorize runtime implementation from child 1.
