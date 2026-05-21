# Review

状态：draft_docs（设计草案，未开始实现）

## 文档阶段记录

| 时间 | Reviewer | Decision | Notes |
|---|---|---|---|
| 2026-05-21 | Codex | draft_docs_created | 新增 11.3.5.5 七件套文档，范围限定为 ExecutionEvidence + TaskResultReporter adapter；未写实现代码。 |

## Implementation Review

实现阶段完成后补充。

### 预期记录项

| 项目 | 内容 |
|---|---|
| 变更文件 | schema、replay service、replay hook、chat runtime、reporter、tests |
| 核心行为 | runtime stop 前采集 DOM evidence；Reporter verified path 打通 |
| 证据 | targeted pytest、replay API boundary、scoped ruff、`git diff --check` |
| 未运行项 | live UI smoke、`verify-scenario`、autonomous run、11.3.5.6 closed-loop evaluation |

## 当前未运行项

| 项目 | 状态 | 原因 |
|---|---|---|
| 代码实现 | 未运行 | 本轮只生成设计文档 |
| Python tests | 未运行 | 无代码改动 |
| UI smoke | 未运行 | 不属于文档生成阶段 |
| `verify-scenario` | 未运行 | 本包不使用 autonomous verification |
| autonomous run | 未运行 | 禁止作为普通文档 / code review 测试 |

## 设计自检

- [x] 明确 `ExecutionEvidenceTarget.text -> ExecutionEvidence.target`。
- [x] 明确 selector 优先 `[data-testid='item-list']`。
- [x] 明确 evidence capture 在 runtime stop 前。
- [x] 明确 Reporter verified path 必须读取 structured postcondition evidence。
- [x] 明确 outcome 保持 `verified / failed / uncertain / needs_review / blocked`。
- [x] 明确 Internal Runtime Adapters 不是 Application Skills。
- [x] 明确本包不做 Failure Recovery / TaskPathPlanner / pending_choice。
