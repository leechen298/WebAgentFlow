# 10.1.2 · Scenario-relative verdict cleanup

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/m10/m10-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

硬边界：只执行 M10 `10.1.2`；不做 `10.2+`；不改 autonomous
engine 的浏览器执行策略；不触发 live autonomous run。若需要清理旧
运行记录，只能在删除接口完成并经过人工确认后执行。

## 目标

统一 autonomous run 的对外裁决语义：接口和页面展示的 `verdict`
必须是**场景相对结果**，即符合 scenario 预期就是 `success`，偏离
scenario 预期才是 `failure`。历史中已按旧语义写入的 run 不做读取
兼容，改由显式删除接口清理。

## 动机

- `invalid_credentials` 这类负向场景的机械页面结果是“登录失败”，
  但如果错误提示、URL 停留等都符合 spec，它在产品语义上就是一次
  成功验证。
- 前端不应该为了负向场景做特殊判断；对外 API 返回的主 verdict 就
  应该已经是用户可理解的结果。
- 之前为了马上修显示做过旧数据读取兼容，但这会让存量脏数据继续
  混在系统里。本轮改为明确删除旧 run 数据，保持接口语义单一。

## 边界（本轮不做）

- 不实现 replay execution / drift detection。
- 不修改 `learned_paths` replay 消费逻辑。
- 不新增批量删除、按条件删除或自动清理任务。
- 不直接改数据库数据；旧数据清理只能通过新增 DELETE 接口完成。
- 不通过 curl / fetch / browser 直接触发 `/exploration/autonomous-run`
  或 stream。

## 成功标准

1. spec-driven autonomous run 的主 `verdict` 语义改为：
   - `pass_gate.status == "pass"` → `verdict = "success"`。
   - `pass_gate.status == "fail"` → `verdict = "failure"`。
   - `pass_gate.status == "unverified"` → `verdict = "uncertain"`。
2. 机械页面结果保留在独立字段（例如 `mechanical_verdict`），供调试
   和 scorecard evidence 使用。
3. `GET /exploration/autonomous-runs/get` 不再为旧 snapshot 做读取时
   verdict 兼容；旧数据是什么就返回什么。
4. `GET /exploration/autonomous-runs/list` 不再为旧 strategy verdict
   做读取时兼容。
5. 新增单条 autonomous run 删除接口，只允许删除
   `strategy_json.kind == "autonomous"` 的记录。
6. 如果被删 run 已经沉淀 LearnedPath，删除接口要给出明确行为：
   本轮采用同时删除该 run 的 source LearnedPath，避免留下指向已删
   run 的路径记录。
7. 后端测试覆盖 verdict 语义、无旧数据兼容、删除接口 happy path /
   404 / 非 autonomous run 拒绝 / 关联 LearnedPath 清理。
8. 前端只展示接口返回的 verdict，不再包含负向场景特殊转换逻辑。
9. 开发完成后，删除旧数据前必须人工确认具体 `run_id` 和会删除的
   关联 LearnedPath。
