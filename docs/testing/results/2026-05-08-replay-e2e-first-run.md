# 10.2 Replay E2E 首次实跑结果

日期：2026-05-08

## 摘要

M10.2 LearnedPath replay 的首次确定性 E2E 实跑通过。

- 命令：`pnpm run test:e2e`
- 结果：`9 passed`
- 耗时：约 `13.5s`

这次实跑验证了 replay API 和 LearnedPath catalog UI，没有扩大 M10.2 范围。

## 环境前置

- Docker 基础设施已运行。
- 数据库迁移已执行。
- API、console、fixture-site 服务已运行。
- API health 返回 HTTP `200`，并且 `database=ok`。

## Seed 结果

E2E seed 脚本写入了 `8` 条 LearnedPath 固定数据，并生成
`apps/e2e/.tmp/replay-fixtures.json`。

写入的固定数据：

- `happy`
- `observational`
- `pageMismatch`
- `targetMissing`
- `unsupportedAction`
- `flaky`
- `deprecated`
- `signatureChanged`

## E2E 覆盖

本次通过的用例覆盖：

1. replay API 正常路径
2. 无动作观察路径
3. catalog UI 正常路径
4. page mismatch
5. target missing
6. unsupported action
7. flaky warning
8. deprecated 422
9. signature changed but executable

## 边界确认

- 未调用 `/exploration/autonomous-runs`。
- 未调用 `/exploration/autonomous-runs/stream`。
- 未依赖 LLM 服务。

## 检查结果

- `git diff --check`：通过，无输出。
- `git status --short`：干净，无输出。

## 已知注意事项

`pnpm run test:e2e:install` 可能因为浏览器下载或网络问题卡在
`playwright install chromium`。如果本机已经有 Chromium 缓存，
`pnpm run test:e2e` 仍然可以通过。

这个注意事项只和浏览器安装有关，不是 replay E2E 行为问题。
