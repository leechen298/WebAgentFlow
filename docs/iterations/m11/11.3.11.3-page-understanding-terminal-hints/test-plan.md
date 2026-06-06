# 测试计划（Test Plan）

状态：proposed

## 测试范围（Test Scope）

- Unit：terminal hint schema and deterministic extraction.
- Integration：optional result metadata if wired into autonomous explorer.
- API / Console / CLI：N/A.
- E2E / live autonomous run：not run.
- LLM provider smoke：not run.

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | list/search page | pytest terminal hints | search/filter function, list_refresh/network_completion candidates | Yes | Synthetic PageAnalysis |
| Unit | form/create page | pytest terminal hints | submit/form function, navigation/toast/region candidates | Yes | Synthetic PageAnalysis |
| Unit | export/download control | pytest terminal hints | export function, download_started candidate | Yes | Text/content hint based |
| Unit | navigation/detail controls | pytest terminal hints | navigation/open detail function | Yes | No selector output |
| Unit | no-control fallback | pytest terminal hints | low-confidence fallback/no_observable_change | Yes | No false success |
| Boundary | selector/raw DOM omitted | pytest terminal hints | no `selector` / `target_selector` in output | Yes | Product boundary |
| Static | lint/import | ruff | clean | Yes | changed files |
| Hygiene | whitespace | git diff --check | clean | Yes | whole diff |

## Live Run 边界

Do not run live autonomous validation, `verify-scenario`, product UI smoke or direct autonomous-run endpoints.

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| LLM provider smoke | First version deterministic | Provider prompt remains future work |
| Browser E2E / UI smoke | Not needed for synthetic PageAnalysis helper | Real pages may need later validation |
| Live autonomous validation | Not authorized | No run_id/pass_gate proof |
