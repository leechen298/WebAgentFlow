# 意图（Intent）

状态：NEEDS_USER_INPUT

## Goal

在 11.3.8.1-11.3.8.4 repo-local fixes / regressions 完成后，重跑 external
black-box validation，判断外部产品路径是否真实恢复，并如实更新 closeout evidence。

## Motivation

此前 latest external black-box result 是 `FAIL`，主要因为 `PV-CLI-003` 没有执行已学
create action。现在 repo-local 修复和 regression 已完成，但 unit / service /
repo-local regression 不等于 live product pass。最终状态必须来自 approved operator
surface 的真实 revalidation。

## Non-goals

- 不在本包继续开发 matcher、learning、router、replay、reporter、frontend、worker 或 DB。
- 不绕过 `wagent chat` / product UI surface。
- 不把 direct replay、service import、hidden HTTP client 或 autonomous-run endpoint
  结果写成 product pass。
- 不在缺少 approval fields 时运行 live validation。

## Success Definition

- Live validation approval fields are recorded before any live run.
- Required scenarios run through approved product surface, or are honestly marked
  `BLOCKED` / `not run` with reason.
- Dated and latest reports are updated only from actual evidence.
- Final status is evidence-backed and preserves `PASS` / `FAIL` / `FOLLOW_UP` /
  `BLOCKED` / `UNVERIFIED` distinctions.
