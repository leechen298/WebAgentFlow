# 10.1.5 · LearnedPath catalog

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/phase-10/phase-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

状态：**可执行**。

硬边界：只执行 Phase 10 `10.1.5`；不做 `10.2+`；不改 autonomous
engine；不触发 live autonomous run；不新增 replay / drift detection。

## 当前关系

10.1 到 10.1.4 已经把三个概念拆开：

- **Autonomous use-case catalog**：authored specs / scenarios，回答
  “现在有哪些用例可以跑”。
- **Autonomous run history**：一次次已经发生过的运行记录，回答
  “系统刚才做了什么、结果和证据是什么”。
- **LearnedPath**：从 `pass_gate = pass` 的 run 中沉淀出的可复用
  路径资产，回答“系统已经学会了哪些可复用操作路径”。

当前 LearnedPath 已有后端接口：

- `GET /exploration/learned-paths`
- `GET /exploration/learned-paths/{path_id}`
- `PATCH /exploration/learned-paths/{path_id}/trust`

前端也已有 API wrapper，但没有独立页面入口。用户只能在某条 history
detail 里顺带看到关联 LearnedPath。只要 history 被清空、某条 run
没有关联路径、或者用户想从资产视角看系统学习结果，就没有稳定入口。

## 问题

没有 LearnedPath 列表页会带来几个直接问题：

- 用户看不见系统到底学到了什么。
- `confirmed` / `deprecated` 等路径级状态只能从 run detail 间接修改，
  入口位置不符合概念边界。
- 10.1.3 已经把 run review 和 LearnedPath trust 拆开，但 UI 仍缺少
  一个真正承载 LearnedPath trust 的主页面。
- 后续 10.2 要消费 LearnedPath 做 replay / drift detection；在 10.2
  之前，应该先让用户能检查现有路径资产。

## 目标

新增一个 console 里的 LearnedPath catalog 页面，用来查看和管理
LearnedPath 资产。

本迭代完成后：

- 侧边栏有明确入口进入 LearnedPath 列表。
- 列表能展示现有 LearnedPath，至少包括：
  - scenario
  - page template
  - trust
  - hit count
  - source run id
  - created / updated time
- 支持按 `trust` 过滤：
  - `all`
  - `provisional`
  - `confirmed`
  - `flaky`
  - `deprecated`
- 每条 LearnedPath 能查看 actions 摘要或进入详情展示 actions。
- 每条 LearnedPath 能跳转到 source run history detail。
- 路径级操作放在这里作为主入口：
  - `确认路径`
  - `标记为不稳定`
  - `废弃路径`
- 文案必须明确：这些操作影响未来复用，不代表某条 run 被确认或标错。

## 非目标

- 不实现 replay execution。
- 不实现 drift detection。
- 不改变 LearnedPath dedup 规则。
- 不新增 run-to-LearnedPath 关系表。
- 不新增账号 / 多租户 / reviewer identity 字段。
- 不删除 LearnedPath 数据；本轮只提供 trust 管理。
- 不把 LearnedPath catalog 做成 authored use-case catalog 的替代品。
- 不触发新的 autonomous run。

## 成功标准

1. 打开 LearnedPath catalog 时，即使没有 history run，也能独立展示
   `GET /exploration/learned-paths` 返回的数据。
2. 空状态能说清楚“还没有沉淀出 LearnedPath”，而不是让用户以为页面
   坏了。
3. `trust` 过滤可用，并且不会误过滤其他字段。
4. 路径级操作调用 `PATCH /exploration/learned-paths/{path_id}/trust`，
   不调用 run review API。
5. source run 跳转只作为关联入口；source run 不存在时页面仍可正常
   展示 LearnedPath。
6. 页面文案清楚区分：
   - use case：可跑的 authored scenario
   - run：一次历史运行
   - LearnedPath：可复用路径资产
7. 不新增或调用 `/exploration/autonomous-runs` run 创建接口。
