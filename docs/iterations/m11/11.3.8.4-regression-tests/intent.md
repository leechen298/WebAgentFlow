# 意图（Intent）

状态：ready_for_design_review

## Goal

新增一个非 live、target-agnostic automated regression，覆盖：

1. learn business action；
2. session learned action 保存 reusable business identity；
3. execute same business action with new slot values；
4. matcher 选中当前 session learned action；
5. replay handler 收到正确 learned path、synthetic URL 和 slot overrides。

## Motivation

`11.3.8.1`、`11.3.8.2`、`11.3.8.3` 分别修复 metadata、utterance 和 matcher。
单点测试不能证明三者组合后不会再次丢失业务对象或退回 wrapper label。这个包把
外部黑盒失败抽象成 repo-local regression，作为 `11.3.8.5` live revalidation 前的
非 live gate。

## Non-goals

- 不运行 external black-box validation。
- 不运行 `wagent chat` live product validation。
- 不调用 `verify-scenario`、browser smoke、direct autonomous-run endpoint 或 direct replay
  API product validation。
- 不依赖 external Validation-Site / Fixture-Site source、route、selector、seed copy、
  page source 或 service availability。
- 不修改 runtime behavior，除非 design review 明确批准 test seam 修复。

## Success Definition

- 七件套创建并通过 read-only design / safety review。
- Focused regression tests 覆盖 positive chain、different-action negative、
  ambiguity 和 generic-verb guard。
- Focused pytest / ruff / target scan / diff sanity 通过。
- `review.md` 如实记录 not-run live validation；不把 `PV-CLI-003` 写成 pass。
