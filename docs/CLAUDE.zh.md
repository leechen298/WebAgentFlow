# CLAUDE.zh.md — docs-local 中文指南

给 Claude Code 在 `docs/` 目录下工作时使用的本地指导。

> 本文件需要和 `docs/AGENTS.md`、`docs/CLAUDE.md` 保持同步。

## 适用范围

本文件适用于 `docs/` 下的文档工作，尤其是
`docs/iterations/m10/10.1.5-*/` 这类较深的迭代目录。

仓库根目录的执行规则仍然适用：`../CLAUDE.zh.md` 是中文入口，
`../CLAUDE.md` 是英文入口。特别是，不要触发 autonomous run，除非通过
仓库允许的项目 skill 和报告契约。

## 必读文档

修改迭代文档前，先读：

1. `../CLAUDE.zh.md` 或 `../CLAUDE.md`
2. `product-model.md`
3. `iterations/README.md`
4. 相关里程碑索引，例如 `iterations/m10/README.md`
5. 相关里程碑计划，例如 `iterations/m10/m10-plan.md`
6. 当前迭代文档，按顺序读：
   - `README.md`
   - `intent.md`
   - `contract.md`
   - `technical-design.md`（代码型 / 混合型迭代）
   - `test-plan.md`（代码型 / 混合型迭代，或触发复杂验证时）
   - `plan.md`
   - `review.md`

这些文件读取成本很低时，不要依赖旧聊天摘要。

## 迭代文档是一个包

真实迭代的文档是一个整体：

- `README.md` 记录迭代类型、状态、文档清单和门禁状态。
- `intent.md` 说明为什么要做，以及什么不在范围内。
- `contract.md` 定义概念、状态、schema、evidence 和边界。
- `technical-design.md` 定义代码型 / 混合型迭代的实现设计，并且必须包含
  contract alignment。
- `test-plan.md` 定义代码型 / 混合型迭代的详细验证方案，或复杂验证触发时的
  验证方案。
- `plan.md` 说明如何实施和验证。
- `review.md` 记录实际发生了什么、相对计划有什么变化、实际验证了什么、
  哪些没跑，以及剩余风险。

当任务是为代码型或混合型迭代生成开发文档时，必须先从
`iterations/templates/` 生成完整文档包：`README.md`、`intent.md`、
`contract.md`、`technical-design.md`、`test-plan.md`、`plan.md`、`review.md`。
不要只生成 `intent.md` + `plan.md` + `review.md`。

纯文档迭代只有在不准备后续代码实现时，才可以省略 `technical-design.md` 和
`test-plan.md`。如果文档型迭代改变流程规则、里程碑语义、Agent 边界、
证据语义、迭代模板、概念、状态、字段或产品边界，仍必须包含 `contract.md`。

为代码实现任务更新文档时，必须保留实现门禁：实现 Agent 必须先读取当前迭代文档，
并按照 `contract.md`、已审核的 `technical-design.md`、`test-plan.md` 和 `plan.md`
实现。如果设计错误或不完整，先更新相关文档并完成审核，再继续实现。

不要把 `review.md` 当成可选项。只要发生了实现工作，迭代没有在 `review.md`
反映实际结果之前就不算关闭。

## 当前实现优先于旧计划

当代码已经偏离原计划时，更新文档来说明当前有效模型，而不是保留过期表述。

例子：

- 如果后续子迭代把某个操作从一个页面迁移到另一个页面，需要在早期 summary 或
  review 中补充“current valid behavior”说明。
- 如果 plan 写着“no backend changes”，但实现增加了 projection 字段，需要在
  `review.md` 里记录这是有意偏离。
- 如果里程碑索引仍写某项 “executable”，但对应 review 已完成，需要把里程碑索引
  和计划更新为 “completed”。

目标不是改写历史。历史说明保留，但必须标清当前有效行为，避免后续 Agent 按过期计划实现。

## 里程碑索引同步

在 `docs/iterations/m<N>/` 下新增、完成、重命名或废弃迭代时，检查并更新：

- `docs/iterations/m<N>/README.md`
- `docs/iterations/m<N>/m<N>-plan.md`（如果存在）
- 当前迭代自己的 `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
  `test-plan.md`、`plan.md`、`review.md`，按迭代类型决定是否必需
- 任何仍包含误导性当前状态表述的早期 summary 或 review

目录名和任务编号必须一致。避免隐藏映射，比如“目录 03 对应任务 10.2”。

## 验证记录

只记录真实运行过的命令。如果因为本次是文档改动而没有运行测试，直接说明。
如果命令因为无关的既有问题失败，记录准确失败内容，并说明它是否阻塞本轮迭代。

live autonomous run 遵循 `../CLAUDE.zh.md` / `../CLAUDE.md`：报告
`pass_gate.status`、Supervisor verdict、五个 scorecard 分数和 `run_id`。
