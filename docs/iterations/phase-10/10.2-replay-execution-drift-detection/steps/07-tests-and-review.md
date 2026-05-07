# 10.2.7 Tests And Review

## 目标

覆盖 10.2 的关键误判风险，并在实现完成后更新 `review.md`。

## 后端测试

新增：

```text
apps/api/tests/test_learned_path_replay.py
```

覆盖：

1. 显式 path replay 成功。
2. `actions=[]` 返回 `observed`。
3. `deprecated` path 返回 `422`。
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

## 前端测试

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

本迭代理论上不需要 live autonomous run。replay API 自身的浏览器执行用
service / API 测试和手工 catalog 点击验证即可。

## Review 收尾

完成实现后更新本目录 `review.md`：

- 实际新增 / 修改了哪些后端模块。
- 实际新增 / 修改了哪些前端入口。
- replay status / drift status 是否和计划一致。
- 哪些验证命令通过。
- 明确记录自动候选 replay UI 未进入本轮。
- 如果实现中发现当前 action schema 仍不够稳定，记录后续 schema
  migration 风险。

如果执行过 live autonomous run，只能通过 `verify-scenario` skill，并在
`review.md` 里按 `pass_gate.status`、Supervisor verdict、五项 scorecard、
`run_id` 原样记录。
