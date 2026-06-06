# 测试计划（Test Plan）

状态：PACKAGE_COMPLETE

## 范围

- Unit：attempt ingest evaluation pure service。
- Service：LearningRunService ingest gate regression。
- Live autonomous run：not run。

## 测试矩阵

| Layer | Scenario | Expected | Required? | Notes |
|---|---|---|---|---|
| Unit | pass_gate pass + terminal_detected strong + actions | `eligible/success_candidate` | Yes | Happy path |
| Unit | pass_gate pass + terminal_unverified | `unverified`, not eligible | Yes | No false success |
| Unit | pass_gate pass + not_terminal_yet/wait | `not_terminal`, not eligible | Yes | Pending state |
| Unit | pass_gate pass + terminal_failed | `failed`, not eligible | Yes | Failure evidence |
| Unit | pass_gate fail/unverified + terminal_detected | ineligible/unverified | Yes | pass_gate remains mandatory |
| Unit | missing terminal verdict | unverified/not eligible | Yes | Backward-compatible safety |
| Service | `_maybe_ingest_learned_path` rejects unverified terminal verdict | no LearnedPath id | Yes | Existing flexible payload |
| Service | existing pass_gate fail still rejects | no LearnedPath id | Yes | Regression |

## Live Boundary

Do not run `verify-scenario`, autonomous runs, Console UI smoke or direct autonomous endpoints.

## Evidence Required For Closeout

- targeted pytest output;
- targeted ruff output;
- `git diff --check`;
- explicit list of unrun live validations.
