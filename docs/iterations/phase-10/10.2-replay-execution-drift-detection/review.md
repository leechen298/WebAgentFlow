# 审核与反思

## 2026-05-01 draft 初始化

- 本目录最初仅作为 `10.2` 主线草案，尚未执行。
- 草案目标是消费 LearnedPath，做 replay execution 和 drift detection。

## 2026-05-02 可执行规划修订

- 复核当前代码后，将本迭代从 draft 改为可执行计划。
- 当前基础：
  - `learned_paths` 已保存 page / query / dom signature、scenario、
    actions、trust、source run。
  - `10.1.5` 已提供 LearnedPath catalog，路径级操作入口集中在
    catalog。
  - actions 当前是裁剪后的 dict，需要在 10.2 里稳定成 replay schema。
  - 单步执行逻辑仍在 `autonomous_explorer.py::_execute_step` 私有函数里，
    需要抽成共享 executor。
- 规划修订：
  - 第一版 UI 主入口放在 LearnedPath catalog，不新开复杂 workbench。
  - 第一版主打“指定某条 LearnedPath replay”，自动候选选择先做后端
    服务 / repo 能力。
  - drift 第一版不用“轻微 / 严重”这类不可证明词，而是按 page
    mismatch、signature changed、selector missing、unsupported action
    返回可解释状态。
  - replay 不调用 autonomous run 创建接口，不触发隐藏的重新学习。

## 2026-05-02 路线图重排后的定位确认

- 全局路线改为 L1/L2/L3 生命周期阶段 + M10/M11/... 交付里程碑。
- 10.2 归属 M10 Path Asset Foundation；目录名保留历史 `phase-10`。
- 10.2 继续可执行，不因路线图重排而推翻。
- 10.2 明确不实现 Agent D · Path Planner Agent、用户自然语言任务入口、
  slot binding、执行前确认或 Agent E 汇报；这些属于 M11
  Task-to-Path Planning MVP。
- 10.2 的 replay engine 是 M11 后续可调用的执行底座。

## 2026-05-07 可施工细化

- 将 `plan.md` 中影响实现的“建议 / 可选”收口为固定 contract。
- 固定第一版只做显式 path replay：
  `POST /exploration/learned-paths/{path_id}/replay`，request body 只含
  `url`，不做自动候选 replay API / UI。
- 固定 replay / drift status 枚举、`flaky` / `deprecated` 行为、
  action 重建规则、UI loading / error / result 三态。
- 这次只是文档细化，尚未开始实现。

## 2026-05-07 文档拆分

- 保留 `plan.md` 作为总纲 / 索引 / 核心 contract，避免 codex-review
  上下文变弱。
- 新增 `brief.md` 和 `simple.md`，分别提供极简版和通俗版。
- 新增 `steps/01` 到 `steps/07` 分步施工文档，让实现可以按 schema、
  repo、drift、executor、API、UI、测试顺序推进。
- 这次仍然只做文档整理，尚未开始实现。

## 收尾反思

待实现完成后追加。
