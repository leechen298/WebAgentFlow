# 实施计划

状态：**可执行**。

本迭代的主线是：复用已有 LearnedPath，复刻一次同样的行为，并把
“还能不能用、哪里变了、哪一步失败”返回给用户。实现时必须保持
learning 和 replay 的边界：replay 不重新规划、不重新学习、不静默重试。

上位定位：本包属于 **M10 Path Asset Foundation**。它会给 **M11.1
Task-to-Path Planning & Execution MVP** 提供可调用的 replay engine，但
本包不实现 Agent D · Path Planner Agent，不做用户任务理解，也不做参数
绑定。

## 施工范围

### 后端 schema

新增或扩展 schema，建议优先放在独立文件，避免 `learned_path.py`
继续膨胀：

```text
apps/api/app/schemas/learned_path_replay.py
```

需要定义的核心对象：

- `ReplayAction`
  - 从 LearnedPath `actions` 里重建出来的稳定动作类型。
  - 支持第一版已有动作：`fill` / `click` / `press` / `observe`。
  - 必须校验 `target_selector`，除 `observe` 外不能为空。
- `ReplayStepLog`
  - 单步执行结果。
  - 包含 step index、action type、selector、ok、error、matched_count、
    URL / title before-after、screenshot ref。
- `ReplayDriftStatus`
  - 建议值：
    - `none`
    - `signature_changed`
    - `target_missing`
    - `page_mismatch`
    - `unsupported_action`
    - `no_candidate`
- `ReplayStatus`
  - 建议值：
    - `succeeded`
    - `observed`
    - `drifted`
    - `failed`
    - `unsupported`
    - `candidate_not_found`
    - `runtime_error`
- `ReplayResult`
  - 包含 selected path、当前 signature、stored signature、drift status、
    drift reasons、step logs、final state。
- `ReplayRequest`
  - 第一版显式 path replay 可以只需要 URL。
  - 如支持自动候选 replay，再加 `scenario` 和可选 `learned_path_id`。

注意：这些状态是 replay 自己的状态，不是 `pass_gate.status`。

### 后端 repo

更新：

```text
apps/api/app/repos/learned_paths_repo.py
```

新增候选选择能力：

```text
find_replay_candidates(page_template, scenario)
```

规则：

1. 只按 `page_template + scenario` 找候选，不要求
   `dom_fingerprint` 完全一致。
2. 排序优先级：
   - `confirmed`
   - `provisional`
3. 默认跳过：
   - `deprecated`
   - `flaky`
4. `flaky` 只允许显式指定 path id 时 replay，用于人工调试。
5. 同一 trust 内部优先：
   - `hit_count` 高
   - `updated_at` 新
   - `created_at` 新

第一版 UI 主入口是“指定某一条 LearnedPath replay”；候选选择主要给
后端服务和后续 M11.1 的 task-to-path planning 能力打基础。

### 后端 replay service

新增服务：

```text
apps/api/app/services/learning/learned_path_replay.py
```

职责：

1. 接收 URL 和 LearnedPath。
2. 启动 `ExecutionRuntime` 并导航到 URL。
3. 调用 `analyze_page(runtime)` 得到当前页面分析。
4. 用 `page_signature.py` 计算当前：
   - `page_template`
   - `query_signature`
   - `dom_fingerprint`
5. 对比 stored signature 和 current signature。
6. 检查 actions 是否支持。
7. 检查每个非 observe action 的 `target_selector` 是否能定位。
8. drift 不阻断时，按原 actions 顺序执行。
9. 捕获最终 URL、title、screenshot、必要 final state。
10. 返回 `ReplayResult`。

### Drift 判断规则

第一版不要说“轻微漂移 / 严重漂移”这种无法从 hash 里证明的词。

建议规则：

1. `page_mismatch`
   - 当前 `page_template` 和 stored `page_template` 不一致。
   - 不继续执行。
2. `signature_changed`
   - `page_template` 一致，但 `query_signature` 或 `dom_fingerprint`
     不一致。
   - 继续检查 selector。
   - selector 都能定位时允许 replay，但在结果里保留 drift warning。
3. `target_missing`
   - 任一非 observe action 的 selector 找不到。
   - 不继续执行。
4. `unsupported_action`
   - action 类型不是 `fill` / `click` / `press` / `observe`。
   - 不继续执行。
5. `none`
   - signature 一致，并且所有目标可定位。

`actions=[]`：

- 不执行浏览器动作。
- 如果页面能打开且 signature 可接受，返回 `ReplayStatus.observed`。
- 如果页面 template 不一致，仍返回 drift。

### Shared action executor

现在单步执行逻辑在：

```text
apps/api/app/services/learning/autonomous_explorer.py::_execute_step
```

10.2 不应该直接 import 这个私有函数，也不应该复用整个 autonomous
pipeline。需要抽成共享模块：

```text
apps/api/app/services/execution/action_executor.py
```

建议暴露：

```text
execute_action(action, runtime) -> dict
observe_step(runtime, step_index=...) -> dict
```

然后：

- `autonomous_explorer.py` 调用共享 executor。
- `learned_path_replay.py` 也调用共享 executor。

抽取时保持原有 step log 字段尽量不变，避免破坏 history / workbench
已有展示。

### API

更新：

```text
apps/api/app/routers/exploration.py
```

第一版新增显式路径 replay：

```text
POST /exploration/learned-paths/{path_id}/replay
```

请求体建议：

```json
{
  "url": "http://127.0.0.1:5175/users"
}
```

响应：

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "learned_path_id": "...",
    "status": "succeeded",
    "drift_status": "none",
    "drift_reasons": [],
    "stored_signature": {},
    "current_signature": {},
    "steps": [],
    "final_url": "...",
    "final_title": "..."
  }
}
```

HTTP 行为：

- path 不存在：`404`
- path 是 `deprecated`：默认 `422`，除非后续明确支持 force replay。
- path 是 `flaky`：第一版可以允许显式 replay，但结果里标记 trust warning。
- body 缺 URL：`422`
- Playwright 启动或导航失败：返回 `ReplayStatus.runtime_error`，不要吞掉错误。

不要新增或调用 autonomous run 创建接口。

### Console UI

更新：

```text
apps/console/src/api/exploration.ts
apps/console/src/pages/LearnedPathCatalogPage.vue
apps/console/src/i18n/locales/zh.ts
apps/console/src/i18n/locales/en.ts
apps/console/src/i18n/locales/ja.ts
```

入口放在 LearnedPath catalog 的 actions drawer 里。

建议交互：

1. 用户打开某条 LearnedPath 的 actions drawer。
2. drawer 顶部展示 Replay 区块：
   - URL 输入框，默认值可以为空。
   - Replay 按钮。
3. 点击后调用：
   - `replayLearnedPath(pathId, { url })`
4. 在 drawer 内展示：
   - replay status
   - drift status
   - drift reasons
   - 当前 signature vs stored signature
   - step logs timeline
   - final URL / title

第一版不新开复杂 workbench 页面；catalog 是路径资产入口，replay 也放
在这里最直观。

### 文案要求

中文文案要说人话：

- `Replay`：重跑这条路径
- `drift`：页面变化
- `target_missing`：找不到当初记录的按钮或输入框
- `unsupported_action`：这类动作当前还不能重跑

必须避免：

- “已通过”这类容易和 `pass_gate` 混淆的文案。
- “Supervisor 验证成功”这类 replay 并没有做的事。
- “重新学习”暗示。10.2 不自动学习。

### 明确不做 M11 能力

10.2 是 replay / drift，不是 task planner。不要在本包里加入：

- task input / chat 入口。
- Runtime Conversation Surface / CLI。
- Conversation Orchestrator / Dispatcher。
- 根据用户自然语言任务检索、选择、组合 LearnedPath。
- slot binding（把“张三”“本周”“导出 CSV”等任务参数绑定到 actions）。
- Agent D · Path Planner Agent。
- Agent E · Result Reporter Agent。
- Agent F / G recovery / abort dialogue。
- Agent H Teaching Guide Agent 或 teaching mode。
- 执行前确认流。
- action risk / consent gate 或用户自定义 risk policy。
- artifact lifecycle（download / export / screenshot 的 capture /
  storage / display / retention / cleanup）。
- task postcondition verification；本包只返回 replay final state 和
  drift / failure result，不判断“用户任务是否完成”。
- multi-page workflow composition；本包不编排多个 LearnedPath。
- 目标网页 Cookie、`localStorage`、session state 或目标站点权限托管。
  这些状态由操作者与目标网页负责；失效或权限不足只表现为 replay 的
  drift / failure / runtime result，恢复对话留给后续里程碑。

这些能力统一留给 M11.0 / M11.1 及后续里程碑。

## 实施步骤

### 10.2.1 Replay schema

目标：先把 replay 的输入和输出长什么样定下来。

产出：

- `ReplayRequest`
- `ReplayAction`
- `ReplayStepLog`
- `ReplayStatus`
- `ReplayDriftStatus`
- `ReplayResult`

验证：

- schema 能校验合法 `fill` / `click` / `press` / `observe`。
- schema 会拒绝缺少 selector 的非 observe action。
- unsupported action 不在 schema 层直接炸成 500，而是能被 service
  转成 `unsupported_action`。

### 10.2.2 Candidate selection

目标：明确系统自动找路径时该优先用哪条。

产出：

- repo 方法：按 `page_template + scenario` 返回 replay candidates。
- 排序规则测试。

验证：

- `confirmed` 排在 `provisional` 前。
- `deprecated` 不进入默认候选。
- `flaky` 不进入默认候选。
- 同一 trust 下按 `hit_count` / 更新时间排序。

### 10.2.3 Drift checker

目标：在执行前先判断这条旧路径现在还对不对得上。

产出：

- drift 计算函数。
- selector 定位检查函数。

验证：

- page template 不一致时返回 `page_mismatch`。
- dom hash 不一致但 selector 都在时返回 `signature_changed`，允许继续。
- 任一 selector 找不到时返回 `target_missing`，不执行。
- unsupported action 返回 `unsupported_action`，不执行。
- `actions=[]` 能走 observational 分支。

### 10.2.4 Shared action executor

目标：把“填输入框 / 点按钮 / 按键 / observe”抽成 replay 和 autonomous
都能共用的执行器。

产出：

- `apps/api/app/services/execution/action_executor.py`
- `autonomous_explorer.py` 改为调用共享 executor。
- replay service 调用同一个 executor。

验证：

- 原 autonomous 相关单测不因为抽取破坏 step log 字段。
- executor 单测覆盖 fill / click / press / observe / selector missing /
  unsupported action。

### 10.2.5 Replay API

目标：给前端一个明确入口，能指定某条 LearnedPath 重跑。

产出：

- `POST /exploration/learned-paths/{path_id}/replay`
- API wrapper 类型。

验证：

- path 不存在返回 404。
- deprecated path 默认拒绝。
- valid path 返回 `ReplayResult`。
- runtime error 返回结构化 `runtime_error`。

### 10.2.6 Catalog UI

目标：让用户在 LearnedPath catalog 里直接试跑某条路径。

产出：

- actions drawer 增加 replay 区块。
- 支持 URL 输入。
- 展示 replay / drift / step log。

验证：

- 点击 Replay 调用 API。
- loading / error / result 状态都有展示。
- `target_missing` 能显示“找不到当初记录的按钮或输入框”。
- `observed` 能显示“这条路径没有动作，已完成页面观察”。

### 10.2.7 Tests and docs

目标：覆盖本轮的关键误判风险，并在 review 里记录实际偏差。

产出：

- 后端 repo / service / API 单测。
- 前端 catalog 单测更新。
- `review.md` 追加实际实现和验证结果。

验证命令见下方。

## 测试计划

### 后端单测

建议新增：

```text
apps/api/tests/test_learned_path_replay.py
```

覆盖：

1. 显式 path replay 成功。
2. `actions=[]` 返回 observed。
3. `deprecated` path 默认拒绝。
4. `flaky` path 显式 replay 时返回 trust warning。
5. page template mismatch。
6. query / dom signature changed but selectors still locatable。
7. selector missing。
8. unsupported action。
9. runtime navigation error。
10. replay result 暴露足够结构化的 drift / failure evidence，供未来
    consumers 使用。
11. 不要求任何 WebAgentFlow 自有 session / 权限托管行为。

更新：

```text
apps/api/tests/test_learned_paths_repo.py
apps/api/tests/test_exploration_learned_paths_api.py
```

覆盖候选选择和新 API contract。

### 前端单测

更新：

```text
apps/console/src/__tests__/components/LearnedPathCatalogPage.test.ts
apps/console/src/__tests__/api/exploration.test.ts
apps/console/src/__tests__/i18n/locales.test.ts
```

覆盖：

1. drawer 中渲染 replay 区块。
2. URL 输入后点击 Replay 调用 API。
3. replay 成功展示 status / drift / steps。
4. target missing 展示友好文案。
5. loading 和 error 状态。
6. 三语 i18n key 齐全。

## 验证命令

实现后至少执行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_learned_paths_repo.py \
  tests/test_exploration_learned_paths_api.py \
  tests/test_learned_path_replay.py

cd apps/console && pnpm run test -- \
  LearnedPathCatalogPage exploration locales

pnpm run build:console

git diff --check
```

如执行过 live autonomous run，只能通过 `verify-scenario` skill，并在
`review.md` 里按 `pass_gate.status`、Supervisor verdict、五项 scorecard、
`run_id` 原样记录。

本迭代理论上不需要 live autonomous run；replay API 自身的浏览器执行
用服务/API 测试和手工 catalog 点击验证即可。

## 收尾要求

完成实现后更新本目录 `review.md`：

- 实际新增/修改了哪些后端模块。
- 实际新增/修改了哪些前端入口。
- replay status / drift status 是否和本计划一致。
- 哪些验证命令通过。
- 如果没有做自动候选 replay UI，明确写成后续事项。
- 如果发现当前 action schema 仍不够稳定，记录后续 schema migration
  风险。
