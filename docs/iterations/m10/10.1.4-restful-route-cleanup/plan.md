# 实施计划

状态：**可执行**。

本迭代是接口命名 cleanup，不改变业务语义。项目当前只有本地自用，
不需要兼容旧路径；实现时直接迁移调用方和测试。

## 路由迁移表

### Autonomous runs

| 当前路径 | 新路径 | 说明 |
|---|---|---|
| `POST /exploration/autonomous-run` | `POST /exploration/autonomous-runs` | 创建 / 执行一次 autonomous run，并持久化 history。 |
| `POST /exploration/autonomous-run/stream` | `POST /exploration/autonomous-runs/stream` | 创建 / 执行一次 streaming autonomous run。 |
| `GET /exploration/autonomous-runs/list` | `GET /exploration/autonomous-runs` | 列表；`limit` / `cursor` / `spec_id` / `scenario` 仍放 query。 |
| `GET /exploration/autonomous-runs/get?run_id=...` | `GET /exploration/autonomous-runs/{run_id}` | 详情；`run_id` 进入 path。 |
| `DELETE /exploration/autonomous-runs/{run_id}` | 保持不变 | 删除资源，当前 method 和 path 已符合目标风格。 |

### Learned paths

| 当前路径 | 新路径 | 说明 |
|---|---|---|
| `GET /exploration/learned-paths/list` | `GET /exploration/learned-paths` | 列表；`limit` / `cursor` / `page_template` / `scenario` / `trust` 仍放 query。 |
| `GET /exploration/learned-paths/{path_id}` | 保持不变 | 详情。 |
| `PATCH /exploration/learned-paths/{path_id}/trust` | 保持不变 | 更新 trust 子资源。 |

### 其他接口

以下接口本轮不改：

- `GET /exploration/specs`
- `GET /exploration/specs/{spec_id}`
- `GET /exploration/screenshots/{filename}`
- `POST /ast/parse`
- `POST /ast/simplify`
- `POST /validation-api/login`
- `GET /validation-api/users`
- `GET /validation-api/users/{user_id}`
- `GET /validation-api/users/meta/options`
- `GET /health`

原因：这些接口的 method 语义正确，路径也没有明显 RPC 式
`/get` / `/list` 动词残留。`ast/parse`、`ast/simplify` 是计算型
command endpoint，用 `POST` 接收大请求体可以接受。

## 后端步骤

1. 修改 `apps/api/app/routers/exploration.py`：
   - `@router.post("/autonomous-run")` 改为
     `@router.post("/autonomous-runs")`。
   - `@router.post("/autonomous-run/stream")` 改为
     `@router.post("/autonomous-runs/stream")`。
   - `@router.get("/autonomous-runs/list")` 改为
     `@router.get("/autonomous-runs")`。
   - `@router.get("/autonomous-runs/get")` 改为
     `@router.get("/autonomous-runs/{run_id}")`，并把 `run_id` 从
     `Query(...)` 改为 path 参数。
   - `@router.get("/learned-paths/list")` 改为
     `@router.get("/learned-paths")`。
2. 不保留旧路由 alias。
3. 如现有路由顺序出现冲突，确保具体路径优先于 path 参数路径。
   当前目标路由里：
   - `DELETE /autonomous-runs/{run_id}` 与
     `GET /autonomous-runs/{run_id}` method 不同，不冲突。
   - `POST /autonomous-runs/stream` 与
     `GET /autonomous-runs/{run_id}` method 不同；FastAPI 按 method
     匹配，仍建议把 `/stream` 写在 `{run_id}` 之前，减少误读。

## 前端步骤

更新 `apps/console/src/api/exploration.ts`：

- `runAutonomousExploration` / stream wrapper：
  - `/exploration/autonomous-run` →
    `/exploration/autonomous-runs`
  - `/exploration/autonomous-run/stream` →
    `/exploration/autonomous-runs/stream`
- `listAutonomousRuns`：
  - `/exploration/autonomous-runs/list` →
    `/exploration/autonomous-runs`
- `getAutonomousRun`：
  - `/exploration/autonomous-runs/get?run_id=...` →
    `/exploration/autonomous-runs/{run_id}`
- `deleteAutonomousRun`：
  - 保持 `/exploration/autonomous-runs/{run_id}`
- `listLearnedPaths`：
  - `/exploration/learned-paths/list` →
    `/exploration/learned-paths`

然后搜索全仓：

```bash
rg -n "autonomous-run|autonomous-runs/list|autonomous-runs/get|learned-paths/list" \
  apps docs AGENTS.md CLAUDE.md CLAUDE.zh.md
```

所有旧路径引用都必须删除或更新。注意 `autonomous-runs` 这个新路径
会包含 `autonomous-run` 子串，检查时要人工区分旧 singular 路径和
新 plural 路径。

## 文档同步

需要同步更新：

- `AGENTS.md`
- `CLAUDE.md`
- `CLAUDE.zh.md`
- `docs/iterations/m10/10.1.4-restful-route-cleanup/review.md`

如果其他文档里也写了旧 route convention，一并更新。重点是不要让
后续 Agent 再按旧 `/list` / `/get` 路径开发。

## 测试计划

### 后端

更新现有 API 测试中的路径，并补充旧路径 404/405 检查：

1. 新列表路径：
   - `GET /exploration/autonomous-runs`
   - `GET /exploration/learned-paths`
2. 新详情路径：
   - `GET /exploration/autonomous-runs/{run_id}`
3. 新 run 创建路径：
   - 如现有测试 mock 了 run endpoint，改为
     `POST /exploration/autonomous-runs`。
4. 旧路径不再存在：
   - `GET /exploration/autonomous-runs/list` 应为 404 或 405。
   - `GET /exploration/autonomous-runs/get?run_id=...` 应为 404 或
     405。
   - `GET /exploration/learned-paths/list` 应为 404 或 405。
   - `POST /exploration/autonomous-run` 应为 404 或 405。
   - `POST /exploration/autonomous-run/stream` 应为 404 或 405。

### 前端

更新 API wrapper 测试，确保请求路径为新路径。

页面测试无需大改，除非测试里 mock 了旧 URL 字符串。

## 验证命令

至少执行：

```bash
cd apps/api && ../../.venv/bin/pytest

cd apps/api && ../../.venv/bin/ruff check \
  app/routers/exploration.py \
  tests

cd apps/console && pnpm run test

pnpm run build:console

rg -n "autonomous-runs/list|autonomous-runs/get|learned-paths/list|/exploration/autonomous-run([\"'/?]|$)" \
  apps docs AGENTS.md CLAUDE.md CLAUDE.zh.md

git diff --check
```

`rg` 最后一个模式用于抓旧 singular `/exploration/autonomous-run`。如
果只剩新 plural `/exploration/autonomous-runs`，说明迁移干净。

## 手动验收

1. 打开 autonomous use-case catalog，选择一个 scenario 进入
   workbench。
2. 不触发 live run，只确认页面能正常加载 specs 和 history。
3. 打开 history 列表，确认前端请求的是
   `GET /api/exploration/autonomous-runs`。
4. 打开一条 history detail，确认前端请求的是
   `GET /api/exploration/autonomous-runs/{run_id}`。
5. 如果需要测试删除，先创建一条测试 run，再通过页面删除；不要直接
   删除非本轮创建的记录。

