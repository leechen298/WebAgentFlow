# 11.2.2 实施计划

状态：文档生成完成，能力未实现

## 触及文件

新增：

- `docs/iterations/m11/11.2.2-wait-for-change-mvp/README.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/intent.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/design.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/plan.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/review.md`

轻量更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/README.md`

不修改：

- `docs/roadmap.md`
- 源码。
- 测试代码。
- package 文件。
- public API。
- database schema。
- replay execution。
- Task Result Reporter。
- M12 / 12.x / M14 / 14.x / 11.3 目录。

## 步骤

1. 确认当前分支和工作区状态。
2. 阅读 M11 README、M11 plan、11.2 总纲、11.2.1 contract 和 realistic case catalog。
3. 创建 11.2.2 README，写清 Wait-for-change MVP 的目标、边界和“能力未实现”状态。
4. 创建 11.2.2 intent，说明与 11.2.1、11.2.5、M12 和 Page Understanding Agent 的边界。
5. 创建 11.2.2 design，定义 Wait Result、Wait Strategy、Agent / Reporter Boundary 和 conservative reporting。
6. 创建本 plan 文档，记录触及文件、步骤、验证命令和完成措辞。
7. 初始化 review，占位记录后续审查结论。
8. 更新 M11 README 和 M11 plan，加入 11.2.2 索引与 M11.3 候选决策点。
9. 更新 11.2 总纲 README / plan，补 11.2.2 与后续包关系。
10. 更新 11.2.1 README，补充不实现 page-load waiting。
11. 运行允许的验证命令。

## 与 11.2.1 的关系

11.2.1 定义 Observation Signal Contract。11.2.2 复用该 contract，但不新增
signal kind，不实现 signal 采集，也不创建 schema 文件。

11.2.2 定义 Wait Result，用于描述等待过程如何结束：

- `observed`
- `timeout`
- `skipped`
- `not_required`

这些 status 是 wait outcome，不是 observation signal kind。

## 与 11.2.3 / 11.2.5 的关系

11.2.2 文档定义 wait-for-change MVP。

后续开发包才实现最小等待机制。11.2.3 将 wait result 和 observation signal 接入
replay execution。11.2.5 将 observation / wait evidence 接入 Task Result Reporter。

Agent 式解释留给 11.2.5 evidence-aware Task Result Reporter。11.2.2 不使用 Agent
判断业务是否成功，也不引入每一步 wait 后的 Agent 业务判断。

## 与 M11.3 的关系

M11.3 只作为 M11.2 后的候选决策点记录，不是已确定执行包。

本轮不创建 `11.3-*` 目录，不实现 Page Context Bridge，也不提前 M14 的完整
Page Understanding Agent。

## 验证

只运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

预期：

- `git diff --check` 退出码为 0。
- code / package status check 无输出。
- M12 / M14 / 11.3 directory check 无输出。
- `git status --short` 只出现文档变更。

## 完成措辞

使用：`11.2.2 文档生成完成，能力未实现`。

不要写：

- `wait-for-change implemented`。
- `page-load waiting implemented`。
- `runtime observation implemented`。
- `Task Result Reporter observation integration complete`。
- `Page Understanding Agent integrated`。
- `M11.3 started`。
- `M14 started`。
