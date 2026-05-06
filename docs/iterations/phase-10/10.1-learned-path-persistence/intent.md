# 10.1 · LearnedPath persistence

## 目标

在 autonomous 运行结束后，把 `pass_gate = pass` 的运行**自动**沉淀
成一条可查询、可被未来产品阶段 3 规划 Agent 消费的 **LearnedPath**
记录，并让用户能在 history 详情页通过一键操作调整这条记录的信用
状态。

## 动机

- 产品模型 §9 把 LearnedPath 持久化列为**交付阶段 10 的 headline
  deliverable**；缺了它，产品阶段 3 "实际工作"没有可执行输入，产品
  主链路无法继续。
- 同时在本迭代里把 [`docs/product-model.md` §10.7 Instance-local data](../../../product-model.md)
  的约束显式化 —— 新表的 schema 和反馈回路都必须对齐这条不变量：
  不向实例外推送数据。
- 用户已经明确"真实用户数据微调"就是三阶段模型在一个实例内持续发生
  的结果；本迭代是这件事第一次真正有数据落盘。

## 边界（本轮不做）

- **不**做产品阶段 3 replay / drift detection —— 那是后续迭代。本轮
  只**写入** LearnedPath，不消费它。
- **不**做跨页面 pattern mining（login / search / CRUD 模板抽象）——
  留给 Phase 10 的后续迭代。
- **不**扩展 `page_analyzer` / `action_planner` 去支持 popup /
  click-toggle 控件 —— 那是并行的 Phase 10 迭代。
- **不**改稳态文档 `roadmap.md` / `scope-boundaries.md`（整个 Phase
  收尾时再一起刷新）。`architecture.md` §G 的一行描述在本迭代尾声
  补上。`product-model.md` §9 里"LearnedPath 持久化尚不存在"的表述
  改成"已交付，replay 待后续迭代"。

## 成功标准

1. Alembic 迁移新增 `learned_paths` 表；`alembic upgrade head` 干净
   通过，`alembic downgrade -1` 可逆；迁移脚本内容和 §10.7 一致。
2. 新模块 `apps/api/app/services/learning/page_signature.py` 导出
   `path_template / query_signature / dom_fingerprint` 三个纯函数，
   单测覆盖下列**至少** case：
   - `path_template`：`/detail/1` 与 `/detail/2` 归到同一模板
     `/detail/:num`；`/items/abc-uuid` 归一为 `/items/:uuid`；
     trailing slash 统一。
   - `query_signature`：`type=edit` 保留、`id=2` 归一 `*`、
     `mode=view` 保留、`token=abcdefghij`（>8）归一 `*`、
     `type=a1b`（含数字）归一 `*`、`q=中文`（非字母）归一 `*`、
     `type=Edit` 归一小写；key 多值取首值；key 排序稳定。
   - `dom_fingerprint`：剔除 `css-dev-only-do-not-override-*` 与
     `rc_*` id；同一结构不同数据值产出同一指纹；同一结构不同登录态
     产出不同指纹（天然结果，不特殊处理）。
3. `autonomous_explorer` / `exploration` 路由的 `_persist_autonomous_run`
   收尾位置在 `pass_gate == "pass"` 时调 repo `ingest_run(...)` 写入
   `trust = provisional` 的 LearnedPath；
   `(page_template, query_signature, dom_fingerprint, scenario)` 相同
   则幂等（`hit_count += 1`，`source_run_id` 保留最早的那条）；
   非 pass 不写。持久化失败只 `logger.warning`，**绝不**破坏主运行
   返回。
4. 新增三个接口（挂在 `/exploration/` 前缀下）：
   - `GET /exploration/learned-paths/list` —— 支持按 `page_template`
     / `scenario` / `trust` 过滤 + 游标分页。
   - `GET /exploration/learned-paths/{id}` —— 单条详情。
   - `PATCH /exploration/learned-paths/{id}/trust` —— 切换
     `confirmed | deprecated | flaky` 并记录 `trust_reason`；非法
     状态转换返回 422。
5. `AutonomousRunDetailPage.vue` 新增 "LearnedPath" 区块：
   - 如果当前 run 已经沉淀（`source_run_id == run.id`），显示 trust
     状态 + `Confirm` / `Mark wrong` 按钮。
   - 如果未沉淀（`pass_gate != pass`），显示灰色提示。
   - 按钮走 `a-popconfirm` 二次确认，失败 `message.error`。
6. `cd apps/api && .venv/bin/pytest`、`pnpm run lint`、
   `pnpm run test`、`pnpm run build:packages`、`pnpm run build:console`
   全绿。
7. 用 `verify-scenario` skill 在 `login.valid_credentials` 上跑一次，
   `pass_gate = pass` 的那条运行事后能在
   `/exploration/learned-paths/list` 里查到，点 Confirm 后
   `trust = confirmed`；`run_id` + 新 learned_path id 写入
   `review.md`。
