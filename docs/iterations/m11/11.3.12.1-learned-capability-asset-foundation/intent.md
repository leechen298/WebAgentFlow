# Intent

状态：proposed

## 目标

本迭代实现 `LearnedCapability` 资产基础层：

```text
ExplorationRun evidence -> LearnedCapability -> later bounded learning / composition
```

成功状态是仓库拥有可迁移、可读写、可去重、可审计的原子能力资产表和访问层，并证明它不会破坏
现有 LearnedPath 读取、replay 和 catalog API。

## 动机

父包 11.3.12 设计审查确认整包范围过大，不能一次性授权实现。最小可独立交付的第一步是资产层：
后续 learning batch、bounded planner 和 runtime composition 都需要一个稳定的能力证据落点。

当前 `ExplorationRun` 是尝试历史，`LearnedPath` 是完整路径资产；系统缺少表达
“这个页面上的某个控件 / 按钮 / tab / 导出动作已被验证”的持久化资产。

## 成功标准

- 新增 `learned_capabilities` 表、ORM、repo 和 Pydantic schemas。
- `dedup_key` 对同一 page signature + capability identity + terminal target 保持稳定。
- repo ingest 对重复能力证据幂等，重复 ingest 不制造重复成功资产。
- 能力资产保留 source `exploration_run_id` / optional `source_learned_path_id`。
- 能力资产区分 `provenance`、`trust`、`evidence_json`、`action_schema_json`、
  `terminal_target_json` 和 redaction/debug 边界。
- 旧 `learned_paths` 行保持可读、可 replay、可被现有 API 返回。
- 不引入 `/users` 或 validation-site 运行时硬编码。

## 非目标

- 不修改 URL-only learning scenario generation。
- 不实现 `LearningBatchController`、batch timeout/cancel 或 async job。
- 不修改 `wagent chat` learning timeout 行为。
- 不实现 bounded planner 默认预算。
- 不实现 Page Understanding capability hints。
- 不实现 runtime capability composition。
- 不修改 LearnedPath schema 或 API。
- 不新增 LearnedCapability HTTP API。
- 不运行 live autonomous validation、`verify-scenario` 或 product UI autonomous run。

## 假设

- M11.3.10 的 `FilterCapability` 可作为未来 candidate 来源，但本包不消费它。
- M11.3.11 的 terminal / attempt evidence 可作为未来 evidence 输入，但本包只定义资产存储形态。
- 现有 DB 使用 Alembic 显式 migration；JSON 字段使用 `sa.JSON()` 保持当前跨后端风格。
