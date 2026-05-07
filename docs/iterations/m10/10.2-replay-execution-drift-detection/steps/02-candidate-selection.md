# 10.2.2 Candidate Selection

## 目标

为后端和后续 M11.1 提供候选路径排序能力。本轮 UI 仍然只做显式 path
replay，不做自动候选 replay 入口。

## 触及模块

- `apps/api/app/repos/learned_paths_repo.py`
- `apps/api/tests/test_learned_paths_repo.py`

## 固定规则

新增 repo 方法：

```text
find_replay_candidates(page_template, scenario)
```

规则：

1. 只按 `page_template + scenario` 查找。
2. 不要求 `dom_fingerprint` 完全一致。
3. 自动候选列表只包含：
   - `confirmed`
   - `provisional`
4. 自动候选列表固定跳过：
   - `deprecated`
   - `flaky`
5. 排序：
   - `confirmed` 在 `provisional` 前；
   - 同一 trust 下 `hit_count` 高的在前；
   - 再按 `updated_at` 新的在前；
   - 再按 `created_at` 新的在前。
6. `flaky` 只允许通过显式 path id replay，用于人工调试。

## 本轮不做

- 不新增自动候选 replay API。
- 不新增自动候选 replay UI。
- 不做自然语言任务到路径的 retrieval / ranking。

## 验收

- `confirmed` 排在 `provisional` 前。
- `deprecated` 不进入自动候选。
- `flaky` 不进入自动候选。
- 同一 trust 下按 `hit_count` / `updated_at` / `created_at` 排序。
