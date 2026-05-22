# 测试计划（Test Plan）

状态：draft_for_review（总体测试规划已生成，未实现代码）

## 测试范围

本包是 docs-only planning package，不运行 runtime tests。验证重点是文档结构、索引同步和
边界一致性。

## 检查矩阵

| Layer | Check | Expected | Required |
|---|---|---|---|
| Docs | 11.3.6 directory exists | seven planning docs exist | Yes |
| Docs | 11.3.6.1 directory exists | runner core seven docs exist | Yes |
| Docs | M11 README links | both 11.3.6 and 11.3.6.1 are indexed | Yes |
| Docs | m11-plan links | program and child package roadmap are indexed | Yes |
| Docs | Review final decision | 11.3.6.1 review has parseable final decision | Yes |
| Boundary | docs-only | no tests / eval claimed | Yes |

## 推荐命令

```bash
find docs/iterations/m11/11.3.6-wagent-runtime-eval-program -maxdepth 1 -type f | sort
find docs/iterations/m11/11.3.6.1-wagent-runtime-eval-runner-core -maxdepth 1 -type f | sort
rg -n "11\\.3\\.6|11\\.3\\.6\\.1|Final Decision" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.6*
rg -n "TBD|TODO|fill in|implement later" docs/iterations/m11/11.3.6* docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md
git diff --check
```

## 不运行

| Item | Reason |
|---|---|
| pytest | no code changed |
| ruff | no Python changed |
| eval runner | not implemented in this package |
| autonomous run | out of scope and prohibited |
| `verify-scenario` | out of scope |

## 通过标准

- 文档目录和索引一致。
- 11.3.6 是 program。
- 11.3.6.1 是 runner core implementation package。
- 没有模板残留。
- 没有声称运行未执行的测试。
