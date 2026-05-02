# Phase 10 · 10.1 — LearnedPath persistence

**Iteration window**: 2026-04-23 → 2026-04-25
**Branch**: `v0.1-local`（local-only，未推远端）
**Iteration record**: `docs/iterations/phase-10/10.1-learned-path-persistence/`
**Live evidence run_id**: `6c97c030-5aae-4f93-8abd-91c4446df9d7`
**Sunk learned_path_id**: `31d3cf58-65a8-4298-bafc-9feee1ed6a90`
**Status**: closed

> 当前有效口径：本文件记录的是 `10.1` 初版交付。后续 `10.1.3`
> 和 `10.1.5` 已把 run review 与 LearnedPath trust 拆开：history
> detail 只保留 run 级审核和 LearnedPath 只读关联信息；路径级
> `confirmed` / `flaky` / `deprecated` 操作在 LearnedPath catalog
> 中完成。

## 一句话

`pass_gate = pass` 的 autonomous 运行从此自动落成 `learned_paths`
行，带四态信用生命周期；后续迭代已把 run 级审核和路径级 trust
操作拆成两个入口。同时显式写进 product-model.md §10.7 "引擎数据
是 instance-local，不引入账号 / 多租户" 这条产品级硬约束。

## 关键决策（开工前对齐用户拍板的）

| 维度 | 决定 | 理由 |
|---|---|---|
| LearnedPath 粒度 | A：`(page, scenario)` | 暴力存，由 Phase 3 Planner Agent 选 |
| page_signature | URL（path 模板 + query 白名单）+ DOM 指纹 | 双要素抗 redirect / 抗动态路由 / 抗改版 |
| 写回时机 | 自动（`pass_gate = pass`）+ 用户事后路径级 trust 管理 | 大部分场景自学，少数人工纠偏；当前路径级操作入口在 LearnedPath catalog |
| 数据归属 | instance-local，引擎不认识"用户" | 用户体系是壳层职责，§10.7 显式化 |
| schema 不引入 | `user_id` / `scope_id` 多租户列 | 防止现在猜未来的壳层形态 |
| empty-actions | 也存（observational） | 单纯打开页面看一眼也是合法成功，给 Phase 3 信号 |

## 主要交付

### 后端
- 新表 `learned_paths`（迁移 `20260424_0001` + follow-up
  `20260424_0002` 给 `provenance` / `trust` 加 DB-level
  server_default）
- ORM `LearnedPath` + `TrustStatus` / `Provenance` `StrEnum` + 状态机
- `LearnedPathRepository`（壳层拦截点）：`ingest_run` 幂等去重 /
  `list_page` 游标分页 / `get` / `find_by_source_run` / `set_trust`
  非法转换抛 `ValueError`
- `services/learning/page_signature.py` 三个纯函数
  `path_template` / `query_signature` / `dom_fingerprint`
- `_persist_autonomous_run` 末尾 hook：仅 `pass_gate == "pass"` 时
  `_maybe_ingest_learned_path`；身份从 `analysis.url` 取（不是
  `payload.url`）；持久化失败只 `logger.warning`
- 三个新接口：
  - `GET /exploration/learned-paths/list`（page_template / scenario
    / trust 过滤 + 游标分页）
  - `GET /exploration/learned-paths/{id}`（含 actions）
  - `PATCH /exploration/learned-paths/{id}/trust`（非法转换 422、
    不存在 404）
- `get_autonomous_run` 响应补 `pass_gate_status` / `learned_path_id`
  / `learned_path_trust`

### 前端
- `api/exploration.ts`：`listLearnedPaths` / `getLearnedPath` /
  `patchLearnedPathTrust` + 类型定义
- `AutonomousRunDetailPage.vue` 新增 LearnedPath 区块：初版包含
  trust tag + Confirm / Mark wrong；当前实现已在后续 `10.1.5`
  中把 trust 操作迁到 LearnedPath catalog，history detail 只保留
  只读关联信息。未沉淀时按
  `pass_gate_status` 三档分叉文案（pass-but-missing / not-pass /
  pre-hook unknown）
- en / zh / ja 三份 locale 同步加 13 个新 key；CTA 按钮在 zh / ja
  也本地化（"确认"/"标记错误"、"確認"/"誤りとして報告"）

### 文档
- `docs/iterations/README.md`（迭代规范，本仓库首次启用）
- `docs/iterations/phase-10/README.md`（Phase 索引 + 六项交付物）
- `docs/iterations/phase-10/10.1-learned-path-persistence/`
  `intent.md` + `plan.md` + `review.md`（review 累积写入：codex
  per-commit + range 两轮审查 + 收尾反思 + verify-scenario 端到端
  证据）
- `docs/product-model.md` / `.zh.md` 顶部加 Terminology 块
  （区分"产品阶段 1/2/3"vs"交付阶段 N"vs"§N"）；§9 把 LearnedPath
  从"未交付"改成"已交付，replay 待后续"；新增 **§10.7
  Instance-local data & the shell boundary**
- `docs/architecture.md` / `.zh.md` §G 在 `services/learning/`
  列表里加 `page_signature.py` 一行
- `docs/roadmap.md` Phase 10 章节把 LearnedPath 那条改成 SHIPPED

### 测试
- 后端 73 条新增单测（38 page_signature + 16 repo + 17 API/hook）
- 前端 +11 条新增单测（4 API wrapper + 7 组件按钮行为）
- ruff / vue-tsc / build:console 全绿
- 端到端：`verify-scenario --spec-id login --scenario
  valid_credentials` 跑通 → `pass_gate = pass` / 5/5 / supervisor
  source `llm`

### 全局 skill 也修了
- `~/.claude/skills/codex-review/SKILL.md`：增加 `range
  <BASE>..<HEAD>` 模式，写明"一个 feature 拆 N commit 时绝不要用
  `commit <SHA1> <SHA2> ...`"，记录了 `codex review --commit` 不接受
  `[PROMPT]` 的 CLI 限制 + UTF-8 字节截断的坑

## Codex 独立审核

### 第一轮（per-SHA，3 次调用）—— 误判
按 commit 拆开审，commit 1 (docs) 被打了 `critical`：因为只看
单个 commit 的 diff，看不到 commit 2/3 里的实现，误以为"docs 说
完成了但代码里没实现"。为这次踩坑，更新了 `codex-review` skill。

### 第二轮（range 模式，1 次调用）—— 干净
`git diff 1dba861^..d06387f | codex exec -`。Codex 明确确认：
> 主实现方向是对的：迁移、ORM、repo、`pass_gate=pass` 写回、3 个
> 接口、详情页 Confirm/Mark wrong，以及 A1/A2/A3/A4/B2 都基本到
> 位，**没有偏离 §10.7 的硬约束**。

逐条回看上一轮 10 条发现：5 条已修验证 OK（`payload.url` →
`analysis.url`、fragment 剥离、DB-level default、`pass_gate_status`
分档文案、zh/ja CTA 本地化）；剩 5 条按用户决定一并在收尾 commit
里清理（empty-actions / 组件测试 / path_template 兜底 / 文档术语 /
review.md disclaimer / iter 文档收口）。

## 偏离原计划的地方

- 多了 `20260424_0002` follow-up migration（codex c2 #4 nit 驱动）
- 详情页未沉淀分支按 `pass_gate_status` 三档分叉，原 plan 没考虑
  pre-hook / ingest-failure edge case（codex c3 #1 驱动）
- empty-actions 改为入库（用户拍板，原 plan 默认 guard 丢弃）
- `path_template("not a url")` 兜底返回 `/`（原 plan 提了，初版
  实现漏掉，codex range 模式发现）

均比 plan 更严，没有缩水承诺。

## 下一迭代候选（按 phase-10/README.md）

1. Popup-based control 支持（最大块）
2. Custom click-toggle 控件（与 1 同条代码路径）
3. Form-label extractor 扩展（独立、低风险）
4. Replay execution + drift detection（消费本迭代落的 LearnedPath）
5. Cross-page pattern mining（最后做）

待用户拍板。

## 6 个 commit

```
93b2f85 docs(phase-10/iter-01): record verify-scenario evidence
21da6fb chore(learned-path): close out iter-01
d06387f fix(learned-path): address codex-review findings (A1-A4, B2)
47ad7de feat(console): LearnedPath confirm/mark-wrong block on run detail
a16fa53 feat(api): LearnedPath persistence with auto-ingest on pass_gate=pass
1dba861 docs(phase-10): add iteration scaffolding, terminology, §10.7
```
