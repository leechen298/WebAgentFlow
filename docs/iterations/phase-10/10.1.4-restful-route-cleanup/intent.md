# 10.1.4 · RESTful route cleanup

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/phase-10/phase-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

状态：**可执行**。

硬边界：只执行 Phase 10 `10.1.4`；不做 `10.2+`；不改 autonomous
engine 的浏览器执行策略；不触发 live autonomous run。

## 背景

当前 exploration API 混用了两种风格：

```http
GET    /exploration/autonomous-runs/get?run_id=...
DELETE /exploration/autonomous-runs/{run_id}
```

这两者操作的是同一种资源 `autonomous run`，但一个是 RPC 风格的
`/get?run_id=...`，另一个是资源路径风格的 `/{run_id}`。这会让接口
使用者难以形成稳定规则。

行业里更通行的 REST-ish 资源风格是：

```http
GET    /resources
GET    /resources/{id}
POST   /resources
PATCH  /resources/{id}
DELETE /resources/{id}
```

本项目现在是个人本地项目，不需要为旧前端或外部调用方保留兼容层。
因此本迭代直接移除旧 RPC 风格路径，把 exploration 相关接口统一成
资源风格。

## 目标

统一 exploration API 路由命名：

- 列表：`GET /exploration/<resources>`
- 详情：`GET /exploration/<resources>/{id}`
- 删除：`DELETE /exploration/<resources>/{id}`
- 局部状态更新：`PATCH /exploration/<resources>/{id}/<subresource>`
- 执行一次 autonomous run：`POST /exploration/autonomous-runs`
- 执行一次 streaming autonomous run：
  `POST /exploration/autonomous-runs/stream`

## 非目标

- 不改变 response envelope：仍然是 `{"code": 0, "msg": "ok",
  "data": ...}`。
- 不改变 request / response payload 字段语义。
- 不改变 `pass_gate`、Supervisor verdict、scorecard、LearnedPath
  ingest 逻辑。
- 不保留旧 `/list` / `/get` / singular `/autonomous-run` 兼容路径。
- 不新增 API versioning。
- 不触发新的 autonomous run。

## 成功标准

1. 后端路由不再暴露：
   - `GET /exploration/autonomous-runs/list`
   - `GET /exploration/autonomous-runs/get?run_id=...`
   - `GET /exploration/learned-paths/list`
   - `POST /exploration/autonomous-run`
   - `POST /exploration/autonomous-run/stream`
2. 后端改为暴露：
   - `GET /exploration/autonomous-runs`
   - `GET /exploration/autonomous-runs/{run_id}`
   - `DELETE /exploration/autonomous-runs/{run_id}`
   - `POST /exploration/autonomous-runs`
   - `POST /exploration/autonomous-runs/stream`
   - `GET /exploration/learned-paths`
   - `GET /exploration/learned-paths/{path_id}`
   - `PATCH /exploration/learned-paths/{path_id}/trust`
3. 前端 API wrapper 全部改用新路径。
4. console 页面和测试不再引用旧路径。
5. 仓库文档里的 route conventions 同步更新，不再把旧路径写成推荐
   用法。
6. OpenAPI 中旧路径不存在，新路径存在。

