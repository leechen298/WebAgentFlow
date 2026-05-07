# 10.2.3 Drift Checker

## 目标

在执行 LearnedPath actions 前判断当前页面和已学路径是否还能对得上，并
给出可解释 drift 状态。

## 触及模块

- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/app/services/learning/page_signature.py`
- `apps/api/tests/test_learned_path_replay.py`

## 固定规则

1. `page_mismatch`
   - current `page_template` 与 stored `page_template` 不一致。
   - 不继续执行。
   - `status = drifted`。
2. `signature_changed`
   - `page_template` 一致，但 `query_signature` 或 `dom_fingerprint`
     不一致。
   - 继续检查 selector。
   - selector 都能定位时允许 replay。
   - 执行成功后 `status` 仍可为 `succeeded` 或 `observed`，但
     `drift_status = signature_changed`，并写入 warning。
3. `target_missing`
   - 任一 supported 非 `observe` action 的 selector 找不到。
   - 不继续执行。
   - `status = drifted`。
4. `unsupported_action`
   - action 类型不是 `fill` / `click` / `press` / `observe`。
   - 不继续执行。
   - `status = unsupported`。
5. `none`
   - signature 一致，并且所有目标可定位。

## `actions=[]`

- 不执行浏览器动作。
- template 一致时返回 `status = observed`。
- template 不一致时返回 `status = drifted`、
  `drift_status = page_mismatch`。
- template 一致但 signature 变化时返回 `status = observed`、
  `drift_status = signature_changed`，并附带 warning。

## 文案边界

不要写“轻微漂移 / 严重漂移”。第一版只报告可证明的状态：
page mismatch、signature changed、target missing、unsupported action。

## 验收

- page template 不一致时返回 `page_mismatch`。
- dom hash 不一致但 selector 都在时返回 `signature_changed`，允许继续。
- selector 找不到时返回 `target_missing`，不执行。
- unsupported action 返回 `unsupported_action`，不执行。
- `actions=[]` 走 observational 分支。
