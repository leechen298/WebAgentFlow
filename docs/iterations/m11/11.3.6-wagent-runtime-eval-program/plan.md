# 实施计划（Implementation Plan）

状态：accepted_program_plan（program review passed，docs-only）

## 文件 / 模块

本包只改文档：

- `docs/iterations/m11/11.3.6-wagent-runtime-eval-program/`
- `docs/iterations/m11/11.3.6.1-wagent-runtime-eval-runner-core/`
- `docs/iterations/m11/11.3.6.4-planner-backed-choice-eval/`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`

## 步骤

### Step 1 · 移动原 runner 设计

将原 `11.3.6-wagent-runtime-eval-runner` 移动为：

```text
11.3.6.1-wagent-runtime-eval-runner-core
```

保持其 ready-for-implementation 状态，并补充拆分记录。

### Step 2 · 新建 11.3.6 总体规划

创建：

```text
11.3.6-wagent-runtime-eval-program
```

写入七件套，定位为 docs-only program package。

### Step 3 · 同步索引

更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`

让它们同时指向：

- 11.3.6 program。
- 11.3.6.1 runner core。
- 11.3.6.4 planner-backed choice eval。

### Step 4 · 检查

运行：

```bash
find docs/iterations/m11/11.3.6-wagent-runtime-eval-program -maxdepth 1 -type f | sort
find docs/iterations/m11/11.3.6.1-wagent-runtime-eval-runner-core -maxdepth 1 -type f | sort
find docs/iterations/m11/11.3.6.4-planner-backed-choice-eval -maxdepth 1 -type f | sort
rg -n "11\\.3\\.6|11\\.3\\.6\\.1|Final Decision" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.6*
rg -n "TBD|TODO|fill in|implement later" docs/iterations/m11/11.3.6* docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md
git diff --check
```

### Step 5 · Review

Update `review.md` with:

- what was split;
- why the split happened;
- not-run items;
- final status.

## 非目标

- 不实现 runner。
- 不修改 `package.json`。
- 不新增 generated artifacts。
- 不运行 live eval。
