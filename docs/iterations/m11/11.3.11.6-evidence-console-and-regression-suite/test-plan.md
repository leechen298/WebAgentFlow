# 测试计划（Test Plan）

状态：PACKAGE_COMPLETE

## 测试矩阵

| Layer | Scenario | Expected | Required? | Notes |
|---|---|---|---|---|
| Console component | result has terminal / ingest evidence | Evidence card renders compact values | Yes | Non-live |
| Console component | legacy result has no evidence | Evidence card hidden | Yes | Backward compatible |
| API detail | result snapshot contains evidence | Detail endpoint returns result evidence | Yes | Existing route |
| Regression | terminal / ingest stack tests | Prior child tests still pass | Yes | Non-live |

## Not Run

- Live autonomous validation.
- Browser UI smoke against running Console.
- `verify-scenario`.
