# 10.1.3 · Run review vs LearnedPath trust

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/phase-10/phase-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

状态：**可执行**。

硬边界：只执行 Phase 10 `10.1.3`；不做 `10.2+`；不改 autonomous
engine 的浏览器执行策略；不触发 live autonomous run。

## 当前关系

当前代码里，历史运行记录和 LearnedPath 不是同一个概念：

- `ExplorationRun` 是一次 autonomous run 的审计记录，保存本次运行的
  URL、spec、scenario、步骤、最终页面、Supervisor、scorecard 和
  `pass_gate`。
- `LearnedPath` 是从 `pass_gate = pass` 的运行里沉淀出来的可复用
  路径数据，未来给 planner 复用。
- LearnedPath 会按 `(page_template, query_signature, dom_fingerprint,
  scenario)` 去重。多条相似 run 可能命中同一条 LearnedPath。
- `learned_paths.source_run_id` 只表示“最早创建这条 LearnedPath 的
  run”，不表示“只有这条 run 关联它”。

因此，`source_run_id` 不是完整的 run-to-path 关系表。后续重复命中
同一 LearnedPath 的 run，不会把自己的 `run_id` 写到
`source_run_id`。

## 问题

10.1 的 history detail 页把“确认 / 标记错误”按钮直接绑定到了
`LearnedPath.trust`。这会造成语义混淆：

- 用户在某一条 history run 上点“标记错误”，直觉上是在标记**这次
  运行**有问题。
- 当前实现实际改的是**这条 LearnedPath**的 `trust`。
- 如果另一条 run 通过 dedup 命中了同一个 LearnedPath，它也会显示
  同一个 `deprecated` 状态，看起来像是另一条 run 也被标记错误。
- 这容易被误解成“整个 authored use case 被标记错误”。

具体例子：

- `16ecbcd3-ab1f-436d-9917-3645dfe011a9` 被用户标记错误。
- `ec69ddb7-efff-4e61-af98-d1226614d2ae` 没有被用户标记过。
- 两者命中同一个 LearnedPath：
  `fa51d9aa-0c86-4932-94eb-019f222228fd`。
- 当前页面会让 `ec69...` 也看起来“已废弃 / 已标错”，这是错误的
  操作语义。

## 目标

把两个概念拆开：

1. **Run review**：用户对某一次历史运行的人工判断。
2. **LearnedPath trust**：用户对一条可复用路径数据的未来复用信任度。

本迭代完成后：

- “确认这次运行 / 标记这次运行错误”只修改当前
  `ExplorationRun` 的人工审核状态。
- 标记某条 run 错误，不会影响其他命中同一 LearnedPath 的 run。
- 标记某条 run 错误，不会自动修改 `LearnedPath.trust`。
- `LearnedPath.trust` 仍然存在，但必须作为明确的“路径级操作”展示，
  不能混在 run review 主按钮里。
- 页面文案明确说明：run review 不等于 authored use case verdict，
  也不等于 LearnedPath trust。

## 非目标

- 不实现 replay execution / drift detection。
- 不改变 `pass_gate`、Supervisor verdict 或 scorecard 的计算方式。
- 不把人工 review 结果回写到 authored specs。
- 不新增账号 / 多租户 / reviewer identity 字段。
- 不触发新的 autonomous run。
- 不在本轮做批量审核、批量废弃或自动清理任务。

## 成功标准

1. `ExplorationRun` 有独立的人工审核状态，至少能表达：
   `unreviewed` / `accepted` / `rejected`。
2. history detail 页面主操作改为 run 级：
   - `确认这次运行`
   - `标记这次运行错误`
3. run 级操作只更新当前 run，不修改 LearnedPath。
4. LearnedPath 区块展示为“关联路径信息”，至少显示：
   - path id
   - trust
   - source run id
   - hit_count
   - 当前 run 与该 path 的关系：`source` 或 `dedup_hit`
5. 如果保留 LearnedPath trust 修改入口，必须放在单独的“路径级操作”
   区域，并明确提示“会影响未来复用，不代表当前 run 错误”。
6. `16ec...` 标记为 rejected 后，`ec69...` 仍显示自己的 review
   状态，不被污染。
7. 现有 `pass_gate` 展示不被人工 review 覆盖；两者并列展示。
