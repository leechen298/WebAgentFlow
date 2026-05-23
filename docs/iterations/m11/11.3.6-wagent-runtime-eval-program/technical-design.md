# 技术设计（Technical Design）

状态：accepted_program_plan（program review passed，docs-only）

## 当前状态（Current State）

11.3.5 working runtime 已完成核心 happy path、choice、failure recovery 和 planner choice 的
基础实现 / targeted tests。原 11.3.6 runner 文档已经通过设计评审，但它同时承担总体规划和
v1 runner 实现职责。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Requirement | Program-level mechanism |
|---|---|
| 总体规划和实现解耦 | 11.3.6 只做 program，11.3.6.1+ 做 code packages |
| hard gates 不漂移 | 11.3.6 contract 定义通用 gate / artifact / exit code 规则 |
| case family 独立推进 | 每个 11.3.6.x 子包有自己的七件套和 review evidence |
| 不扩大产品 runtime | 11.3.6 program 不改代码，不新增 Agent |
| 审计边界稳定 | Codex 只复核 artifact，不替 runner 判定 pass |

## Program Structure

```text
11.3.6 WAgent Runtime Eval Program
  |
  +-- 11.3.6.1 Runner Core
  +-- 11.3.6.2 Failure Recovery Eval
  +-- 11.3.6.3 Pending Choice Multi-candidate Eval
  +-- 11.3.6.4 Planner-backed Choice Eval
```

### 11.3.6.1 Runner Core

Implements the first executable runner. Detailed API flow, case gates, data structures and artifact
rules live in the 11.3.6.1 documents, not in this program-level package.

### 11.3.6.2 Failure Recovery Eval

Adds stable failure path coverage after a fault injection / eval-only hook design is approved.
The child package now lives at
[`../11.3.6.2-failure-recovery-eval/`](../11.3.6.2-failure-recovery-eval/).

### 11.3.6.3 Pending Choice Multi-candidate Eval

Adds multi-candidate choice coverage.
The child package now lives at
[`../11.3.6.3-pending-choice-multi-candidate-eval/`](../11.3.6.3-pending-choice-multi-candidate-eval/).

### 11.3.6.4 Planner-backed Choice Eval

Adds planner-backed choice coverage while preserving the single-path direct replay regression.

## Data Flow

11.3.6 does not define executable data flow. Child runner packages define their own runtime flow and
must align with the shared artifact / gate / exit code contracts.

## Compatibility

This package is docs-only. Compatibility risk is limited to documentation links and milestone indexing.
No migration, schema, service, API, CLI or UI changes are introduced here.

## Test Matrix

| Check | Expected |
|---|---|
| M11 README | links both 11.3.6 program and 11.3.6.1 runner core |
| m11-plan | 11.3.6 described as program with child roadmap |
| 11.3.6.1 | retains ready-for-implementation runner core design |
| review.md | final decision is easy to parse |
| docs-only boundary | no runtime test or eval pass claimed |
