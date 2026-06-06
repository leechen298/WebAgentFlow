# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

父包 `11.3.11-terminal-state-agent-learning-stop-control` 已定义 campaign route，
当前 `CURRENT_STATE.md` 将本 child 标为 `CHILD_DOCS_REVIEW_READY`。运行时代码未授权。

当前产品模型中 L1 pipeline 只有 Page Understanding Agent、Attempt Evaluation Agent 和
Learning Report Agent。terminal-state classification 仍停留在父包 proposed boundary，需要在
产品模型和 roadmap 中做 scoped doc update，明确它是 Attempt Evaluation handoff 前的 evidence
contract / evaluator worker，而不是 Agent I 或 Attempt Evaluation Agent 的替代品。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Terminal-state classification is an evidence contract, not a new lifecycle stage | 更新 `docs/product-model.md` L1 pipeline 和 Agent boundary wording | `test-plan.md` docs alignment checks | 不改变 L1/L2/L3 |
| Terminal State Agent naming, if used, has no legacy alias | 更新 Agent table 或 boundary note | `test-plan.md` product-model alignment | 不新增 Agent I |
| Agent 不控制 browser operation | 在 product model、contract、roadmap 中声明 code owns operation | `rg` boundary check | 后续 child runtime design 必须继承 |
| terminal taxonomy / outcome / stop decision 固定 | 本包 `contract.md` 定义 logical enum | docs integrity / design review | child 4 才落 schema |
| failed/unverified 不得进入成功 LearnedPath | 本包 contract + child 5 gate requirement | docs review, child 5 tests later | 本包不改 runtime |
| storage/redaction 必须向后兼容 | 本包给 logical shape，child 2-6 细化 | docs review | 不做 migration |
| live validation 默认不运行 | test-plan / review 记录 not_run | docs review | 无 run_id / pass_gate claim |

## 实现方案（Proposed Implementation）

本包只做文档和路由实现：

1. 创建 child package 七件套。
2. 更新 `docs/product-model.md`：
   - 在 L1 pipeline 中加入 terminal-state classification 的位置和职责。
   - 如使用 Agent table 条目，加入 `Terminal State Agent | no legacy alias | L1 scoped evaluator worker`。
   - 更新 cross-cutting / implementation status / milestone alignment。
3. 更新 `docs/roadmap.md`：
   - 在 M11.3 post-closeout follow-up 中加入 11.3.11 的定位。
   - 明确未来 M14 可复用该 evidence / stop-control contract。
4. 更新 `docs/iterations/m11/README.md`：
   - 加入 child 1 索引和父包 active child 状态。
5. 更新父包 `CURRENT_STATE.md`：
   - active child 从 `CHILD_DOCS_NOT_CREATED` 推进为 `CHILD_DOCS_REVIEW_READY` 或后续设计复核状态。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | N/A | No runtime change |
| API response schema | No | N/A | No runtime change |
| Database schema / migration | No | N/A | No runtime change |
| CLI | No | N/A | No runtime change |
| Console UI | No | N/A | No runtime change |
| Conversation events | No | N/A | No runtime change |
| Replay execution | No | N/A | No runtime change |
| Reporter | No | N/A | No runtime change |
| Worker / async jobs | No | N/A | No runtime change |
| Tests / fixtures | No | N/A | Docs checks only |
| Docs | Yes | Child docs, product model, roadmap, M11 index, parent state | Scoped documentation update |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No runtime data model changes in this child package.

Logical schema direction is documented in `contract.md`; child 2-6 must define concrete schema,
storage and migration choices in their own `technical-design.md`.

## 服务 / 模块设计（Service / Module Design）

No service/module implementation in this child package.

Expected future module ownership, not implemented here:

- Child 2: browser event recorder service and redaction helpers.
- Child 3: PageTerminalHint schema and Page Understanding handoff.
- Child 4: Terminal State Agent adapter and deterministic stop controller.
- Child 5: AttemptTerminalSummary ingest gate and LearnedPath / failure evidence policy.
- Child 6: history / Console / CLI evidence presentation.

## 数据流（Data Flow）

Future runtime data flow, for downstream child alignment:

```text
PageAnalysis + Page Understanding terminal hints
  -> attempt action log + before snapshot
  -> code-driven Playwright action
  -> browser event timeline + bounded wait result + after snapshot
  -> terminal-state classification / Terminal State Agent verdict
  -> ExplorationStopController stop/wait/continue/unverified_stop
  -> Attempt Evaluation Agent
  -> LearnedPath candidate / failure evidence / negative knowledge gate
  -> run history / conversation history / Console evidence summary
```

本包只记录该数据流，不实现。

## 状态推导（Status / State Derivation）

本包状态推导：

- Child docs generated + product model/roadmap scoped update + docs checks pass -> `REVIEW_READY`。
- Design review has no P0/P1 and review records authorization boundary -> `PACKAGE_COMPLETE` for child 1 docs.
- Runtime implementation authorization remains `no` for child 1; child 2 must create/review its own docs before code.

## 兼容性（Compatibility）

因为本包只改文档，不影响 runtime compatibility。后续 child 必须保持：

- old runs readable;
- old LearnedPaths replayable;
- old history pages render missing terminal evidence as not available;
- no existing pass_gate / Supervisor semantics overwritten.

## 失败 / 边界情况（Failure / Edge Cases）

- 如果 product model update 会发明 Agent I、替代 Agent B 或改变 L1/L2/L3，停止为 `BLOCKED`。
- 如果 roadmap 把 11.3.11 错路由到 M14 implementation，停止为 `NEEDS_USER_INPUT`。
- 如果 docs integrity 发现模板残留、parent/child 状态冲突或 live-run claim，停止为 `BLOCKED`。
- 如果后续 child 试图从父包或 child 1 直接实现 runtime code，停止为 `BLOCKED`。

## 非目标（Non-goals）

- 不实现 runtime code。
- 不运行 live validation。
- 不做 database / API / CLI / Console schema changes。
- 不把 Terminal State Agent 写成 legacy Agent I 或新的顶层 god Agent。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Docs integrity | 七件套存在、无模板残留、状态 discoverable | `test-plan.md` Current Verification |
| Product model alignment | L1 pipeline evidence handoff + optional no legacy alias | `test-plan.md` Product Model Alignment |
| Roadmap / M11 index | 11.3.11 child route discoverable, M14 reuse wording correct | `test-plan.md` Roadmap / Index Alignment |
| Live boundary | No run_id/pass_gate claim, live validation not run | `test-plan.md` Live Boundary |

## 验证命令入口（Validation Commands）

```bash
find docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy -maxdepth 1 -type f -print | sort
rg -n "Terminal State Agent|no legacy alias|11\\.3\\.11\\.1|implementation_authorized|live autonomous validation" docs/product-model.md docs/roadmap.md docs/iterations/m11/README.md docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy
rg -n "T[B]D|T[O]DO" docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy docs/product-model.md docs/roadmap.md
git diff --check
```
