# 实施计划

## 触及的文件 / 模块

### 后端（新增）

- `apps/api/alembic/versions/<timestamp>_add_learned_paths.py` ——
  新迁移，建表 + 索引。
- `apps/api/app/models/learned_path.py` —— ORM，包含 `TrustStatus`
  与 `Provenance` 枚举。
- `apps/api/app/schemas/learned_path.py` —— Pydantic 请求 / 响应
  模型。
- `apps/api/app/repos/learned_paths_repo.py` —— 数据访问。本迭代是
  §10.7 指定的数据访问边界，现在只暴露
  `ingest_run / list / get / set_trust`，不要把 SQL 漏到
  routers。
- `apps/api/app/services/learning/page_signature.py` —— 三个纯函数
  `path_template / query_signature / dom_fingerprint`。

### 后端（修改）

- `apps/api/app/routers/exploration.py` —— `_persist_autonomous_run`
  在成功写完 `exploration_run` 后，若 `pass_gate == "pass"` 继续
  调 `LearnedPathRepository.ingest_run(...)`；加 3 个新接口。
- `apps/api/app/schemas/common.py`（可选） —— 若需要额外的枚举外
  壳就加，否则在 `schemas/learned_path.py` 内部自治。

### 后端（测试）

- `apps/api/tests/test_page_signature.py` —— 三个函数的单测。
- `apps/api/tests/test_learned_paths_repo.py` —— ingest_run 幂等、
  hit_count 自增、trust 状态机。
- `apps/api/tests/test_exploration_learned_paths_api.py` —— 三个
  接口的契约测试（happy + 非法状态 + 不存在 id）。

### 前端（修改）

- `apps/console/src/api/exploration.ts` —— 加 `listLearnedPaths /
  getLearnedPath / patchLearnedPathTrust`。
- `apps/console/src/pages/AutonomousRunDetailPage.vue` —— 新增
  "LearnedPath" 区块；复用现有 block 样式。
- `apps/console/src/__tests__/learnedPathActions.spec.ts`（新增）——
  按钮行为 + 状态刷新。

### 文档（迭代尾声修改）

- `docs/product-model.md` / `.zh.md` §9 —— 把 "LearnedPath
  persistence does not exist yet" 改成"已交付；replay / drift
  detection 待后续迭代"。
- `docs/architecture.md` / `.zh.md` §G —— 在 `services/learning/`
  条目下追加一行 `page_signature.py` 职责。

## 步骤

每一步尽量能独立 commit + 独立绿。commit 粒度 ≈ 步骤。

### 1. 迁移 + ORM + repo 骨架

**表结构**（字段名 / 类型）：

| 列 | 类型 | 备注 |
|---|---|---|
| `id` | `String(36)` pk | UUID |
| `page_template` | `String(512)` NOT NULL | `/detail/:num` 这种归一过的 path |
| `query_signature` | `JSON` NOT NULL | 排序后的 `{key: value-or-"*"}` 字典 |
| `dom_fingerprint` | `String(64)` NOT NULL | sha256 hex |
| `scenario` | `String(255)` NOT NULL | 空字符串代表 ad-hoc run |
| `actions` | `JSON` NOT NULL | 有序 list，每项 `{selector, action_type, value, …}` |
| `provenance` | `String(16)` NOT NULL | 目前只会是 `system`；L2 落地后出现 `user` |
| `trust` | `String(16)` NOT NULL DEFAULT `'provisional'` | `provisional / confirmed / flaky / deprecated` |
| `trust_reason` | `Text` | nullable，最近一次切换原因 |
| `trust_updated_at` | `DateTime(timezone=True)` | nullable；首次 trust 切换时写 |
| `hit_count` | `Integer` NOT NULL DEFAULT `1` | `ingest_run` 命中同一 key 时 `+= 1` |
| `source_run_id` | `String(36)` | `ExplorationRun.id`；on delete set null |
| `dedup_key` | `String(64)` NOT NULL UNIQUE | sha256(page_template + json(query_signature) + dom_fingerprint + scenario) |
| `created_at` | `DateTime(tz)` server_default now() | 继承 mixin |
| `updated_at` | `DateTime(tz)` server_default now() onupdate now() | 继承 mixin |

**索引**：

- UNIQUE `(dedup_key)`（去重；跨 DB 兼容，不依赖 JSONB 索引）。
- `(page_template, scenario)`（list 查询）。
- `(trust)`（后续规划 Agent 读取热点）。

**ORM**：继承 `UUIDPrimaryKeyMixin + TimestampMixin`；
`TrustStatus` 与 `Provenance` 用 `StrEnum` 定义在 model 文件顶部。

**Repo 接口**：

```python
class LearnedPathRepository:
    def ingest_run(self, *, page_template, query_signature,
                   dom_fingerprint, scenario, actions,
                   source_run_id, provenance="system") -> tuple[LearnedPath, bool]
        # 返回 (row, created)；已存在则 hit_count += 1 并返回 (existing, False)

    def list(self, *, page_template=None, scenario=None, trust=None,
             cursor=None, limit=20) -> tuple[list[LearnedPath], bool]
    def get(self, path_id: str) -> LearnedPath | None
    def set_trust(self, path_id: str, status: TrustStatus,
                  reason: str | None) -> LearnedPath  # 非法转换抛 ValueError
```

**trust 状态机**：

```
provisional ──confirm──→ confirmed
provisional ──reject──→ deprecated
provisional ──flake──→ flaky
confirmed  ──reject──→ deprecated      # 用户反悔
confirmed  ──flake──→ flaky            # 系统自动降级（本迭代不触发）
flaky      ──confirm──→ confirmed      # 用户撤销降级
flaky      ──reject──→ deprecated
deprecated ──confirm──→ confirmed      # 用户撤销废弃
# 其他转换一律非法
```

本迭代只实现 PATCH 接口手动触发；`flaky` 的自动降级路径留给未来
replay 迭代。

**验证**：

- `alembic upgrade head` / `downgrade -1` 干净通过。
- `tests/test_learned_paths_repo.py`：ingest 幂等、hit_count 自增、
  trust 合法转换成功、非法转换抛 `ValueError`。

### 2. `page_signature.py` + 单测

**`path_template(url) -> str`**：

- `urllib.parse.urlsplit` 取 path。
- 对每个 segment：纯数字 → `:num`；匹配 UUID v4 正则 → `:uuid`；
  其它保持原样。
- 去掉 trailing slash（除根 `/`）。

**`query_signature(url) -> dict[str, str]`**：

- `urllib.parse.parse_qsl(keep_blank_values=True)` 取所有键值对。
- 同 key 多值取首值。
- 白名单规则：`len(v) <= 8 and v.isalpha()` → 保留 `v.lower()`；
  否则归一为 `"*"`。
- 结果按 key 排序，返回 `dict`（Python 3.7+ 保序）。

**`dom_fingerprint(analysis: PageAnalysis) -> str`**：

- 从 `analysis` 里提取四组稳定特征：
  - `forms`：所有 fillable 的 `(semantic_role or type, name_or_id_if_stable)`
    对，排序。
  - `buttons`：所有 clickable 的 `text or aria_label`，去空，排序。
  - `headings`：取 `<h1>` 第一条 + `<h2>` 第一条（structured_text
    里有）。
  - `table_headers`：如果 analysis 有表格信息，取列标签排序；否则
    空列表。
- **剔除**：`rc_*` / `css-dev-only-do-not-override-*` 前缀的 id /
  class 碎片；随机 id 里的 hash 段（长度 > 12 的 base62 串视为
  hash）。
- `json.dumps(payload, sort_keys=True, ensure_ascii=False)` →
  `hashlib.sha256(...).hexdigest()`。

**测试用例**（除 intent.md 列出的以外）：

- `path_template`：`"/"` → `"/"`；`"/users/"` → `"/records"`；
  `"/users/42/edit/"` → `"/users/:num/edit"`；
  `"/detail/550e8400-e29b-41d4-a716-446655440000"` → `"/detail/:uuid"`；
  空字符串 / 不规范 URL 不崩溃（返回 `"/"`）。
- `query_signature`：空 query → `{}`；重复 key `?a=1&a=2` → 取
  `"1"` 经白名单 → `{"a": "*"}`；大小写 `?Type=Edit` → key 小写
  化（`{"type": "edit"}`）。
- `dom_fingerprint`：同一页面 2 次分析，行数不同、行数据不同，但
  fingerprint 一致；把 `rc_abc123` id 换成 `rc_xyz789` 后
  fingerprint 不变。

**开发过程中遇到的异常 case**（query 白名单漏网、指纹不稳、等）
每一个都新增一行测试 + 在同目录 `review.md` 追加一条 `<日期>
异常 case 记录`；阶段尾拉回来和用户对一次，决定哪些进白名单。

### 3. 写回 hook

位置：`apps/api/app/routers/exploration.py` 的
`_persist_autonomous_run`，在 `ExplorationRunRepository(db).create(run)`
返回 run_id 之后追加：

```python
if _pass_gate_status_for(run) == "pass":
    try:
        _ingest_learned_path(db, run, final_data)
    except Exception as exc:   # pragma: no cover - defensive
        logger.warning("Failed to ingest LearnedPath: %s", exc)
```

`_ingest_learned_path(db, run, final_data)`：

1. 从 `final_data` / `run.strategy_json` 解出 URL / scenario / 分析
   结果。
2. `page_signature` 三件套生成 key。
3. actions 摘自 `final_data["execution"]` / 时间线中 verdict ==
   `success` 的步骤，剔除截图 / 大 payload。
4. `LearnedPathRepository(db).ingest_run(..., source_run_id=run.id,
   provenance="system")`。

**测试**：`test_learned_paths_repo.py` 已覆盖幂等；
`test_exploration_learned_paths_api.py` 通过注入 mock `final_data`
走一次端到端写回路径验证 hook 不破坏主运行。

### 4. 三个接口

路径前缀统一 `/exploration/learned-paths/...`：

- `GET /exploration/learned-paths/list` —— query 参数：
  `page_template?` / `scenario?` / `trust?` / `limit?` /
  `cursor?`。返回 `ApiResponse[CursorPage[LearnedPathSummary]]`。
- `GET /exploration/learned-paths/{path_id}` —— 返回
  `ApiResponse[LearnedPathDetail]`（含 actions / 完整字段）。
- `PATCH /exploration/learned-paths/{path_id}/trust` ——
  body: `{status: "confirmed" | "deprecated" | "flaky",
  reason?: str}`。返回 `ApiResponse[LearnedPathDetail]`。非法转换
  返回 `HTTPException(status_code=422)`；不存在返回 404。

**测试**：`test_exploration_learned_paths_api.py`。

### 5. 前端按钮

`AutonomousRunDetailPage.vue`：

- 加一个 `<a-card title="LearnedPath">` 区块（参考同页其他 block
  的样式）。
- `onMounted` 后根据 `run.id` 调 `listLearnedPaths({
  source_run_id: run.id })` —— **注**：list 接口**不需要**支持
  `source_run_id` 过滤来专门服务这一点；更简单做法是在 get_autonomous_run
  的返回里加一个 `learned_path_id` 字段（或 null）。本迭代二选一，我
  倾向后者：后端在 `get_autonomous_run` 里顺手查一次，少一次前端
  round-trip。
- 如果 `learned_path_id` 存在：显示 trust tag + 两个按钮。点击走
  `a-popconfirm` → `patchLearnedPathTrust` → 成功后 `message.success`
  并刷新。
- 如果 `learned_path_id` 为 null：显示灰色 "此运行未沉淀成
  LearnedPath（`pass_gate != pass`）"。

**测试**：`__tests__/learnedPathActions.spec.ts` 用
`@vue/test-utils` 渲染组件，mock axios，断言按钮点击触发正确请求 +
状态刷新。

### 6. 文档尾声

- 更新 `product-model.md` / `.zh.md` §9。
- 更新 `architecture.md` / `.zh.md` §G（添加一行 `page_signature.py`
  职责）。
- 本迭代 `review.md` 追加"收尾反思"章节：
  - 开发过程中遇到的 query 异常 case + 是否要进白名单；
  - dom_fingerprint 实际跑下来需要微调的地方；
  - 本计划外的偏离点 + 下一步挂哪个迭代。

## 验证

- `cd apps/api && .venv/bin/pytest tests/test_page_signature.py
  tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py
  -v` 全绿。
- `cd apps/api && .venv/bin/pytest` 整套回归全绿。
- `pnpm run lint` + `pnpm run test` + `pnpm run build:packages` +
  `pnpm run build:console` 全绿。
- 手动：`pnpm run dev` 起全栈，workbench 跑
  `login.valid_credentials`；到
  `/exploration/autonomous/history/<run_id>`，看到 LearnedPath 区块
  + 两个按钮；点 Confirm，刷新后 `trust = confirmed`。
- `verify-scenario` skill：`.venv/bin/wagent verify --spec-id login
  --scenario valid_credentials`。`pass_gate = pass` + `run_id` +
  沉淀出来的 `learned_path_id` 都写进本迭代 `review.md`。

## 与 §10.7 的对齐点（审核清单）

迭代收尾时逐条核对：

- [ ] `LearnedPathRepository` 是唯一数据访问入口；router 不直接
      写 SQL。
- [ ] 写回 / 查询 / trust 切换都**没有**向实例外推数据（没有
      webhook、没有上报、没有 LLM 传 instance 身份）。
- [ ] LLM prompt、logger、SSE 事件里**没有**"who is running this
      instance"的概念。
