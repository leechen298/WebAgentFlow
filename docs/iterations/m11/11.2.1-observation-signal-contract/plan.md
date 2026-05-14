# 11.2.1 实施计划

## 触及文件

新增：

- `docs/iterations/m11/11.2.1-observation-signal-contract/README.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/intent.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/contract.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/plan.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/review.md`

轻量更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

不修改：

- `docs/roadmap.md`
- 源码。
- 测试代码。
- package 文件。
- API / schema / database 文件。
- replay execution。
- Task Result Reporter。
- M12 / 12.x / v0.2 文件或分支。

## 步骤

1. 确认分支和工作区状态。
2. 阅读 11.2.0 文档包、M11 README、M11 plan 和 realistic case catalog。
3. 新增 11.2.1 文档包。
4. 在 `contract.md` 中定义 Observation Signal、signal kind、scope、字段 proposal
   和 conservative reporting 边界。
5. 明确 `page_load_started` / `page_load_finished` 与 `loading_started` /
   `loading_finished` 的区别。
6. 明确 timeout / not-observed 不属于 11.2.1 signal kind。
7. 在 scenario catalog 中补充 delayed full page reload after action。
8. 轻量更新 M11 索引和 11.2 总纲链接。
9. 运行允许的验证命令。

## 后续拆包关系

- 11.2.1 定义 signal contract。
- 11.2.2 基于 contract 做 wait-for-change MVP。
- 11.2.3 将 observation 接入 replay execution。
- 11.2.4 用 realistic fixture pages 覆盖典型场景。
- 11.2.5 将 observation evidence 接入 Task Result Reporter。
- 11.2.6 / 11.2.7 做 QA、测试和 evidence closure。

## 验证

只运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' \) -print
```

预期：

- `git diff --check` clean。
- code / package status check 无输出。
- M12 directory check 无输出。
- `git status --short` 只出现文档变更。

## 完成措辞

使用：`11.2.1 文档生成完成`。

不要写：

- `runtime observation implemented`。
- `wait-for-change implemented`。
- `page-load waiting implemented`。
- `reporter observation integration implemented`。
- `M12 started`。
