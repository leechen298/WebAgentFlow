# 审核与反思

## 2026-05-01 文档准备

- 本迭代先补 `intent.md` 和 `plan.md`，用于在进入下一步 M10
  核心任务前，把 `10.1.1` “自主探索用例列表页”独立拆成可执行包。
- 当前尚未实现代码，也未运行测试。

## 2026-05-01 收尾反思

### 实际做了什么

- 新增 `AutonomousUseCasesPage.vue` — 调用 `listSpecs()` 加载 specs，按 spec
  分组以 card + table 展示 scenarios，支持 deep-link 跳转到 workbench
  （带 `url`、`spec_id`、`scenario`、`goal` 查询参数）。
- 新增路由 `/exploration/autonomous/cases`，注册到 `router/index.ts`。
- 侧边栏新增 “自主探索用例” 菜单项（`MainLayout.vue`），使用
  `UnorderedListOutlined` 图标。
- `env.d.ts` 新增 `VITE_VALIDATION_SITE_ORIGIN` 类型声明。
- 补全 zh / en / ja 三语言的 `autonomousUseCases` 命名空间（15 个 key）。
- `setup.ts` 全局 stubs 新增 `a-tooltip`。
- 新增页面单元测试 `AutonomousUseCasesPage.test.ts`（4 个 case：加载渲染、
  空状态、错误提示、deep-link 跳转参数）。
- router 测试新增 `exploration-autonomous-cases` 路由名断言。
- Kimi 遗留的 Vitest hoist 问题（`vi.mock` 引用顶层变量）已通过
  `vi.hoisted()` 修复，测试全部通过。

### 和 plan 的偏离点

无偏离，按 plan 执行。

### 验证命令与结果

```bash
cd apps/console && pnpm run test
# 15 test files, 59 tests — all passed

pnpm run build:console
# vue-tsc --noEmit + vite build — clean
```

`pnpm run lint` 有 22 个报错，全部来自既有文件
（`autonomousStream.ts`、`MainLayout.vue`、`AutonomousWorkbenchPage.vue` 等），
本次新增文件不在其中，不阻塞本迭代交付。

### 是否触发 live autonomous run

否。本次改动为纯前端页面 + i18n + 测试，不涉及后端或 autonomous explorer
逻辑，无需触发 live run。

## 2026-05-01 增量交付：批量选择与批量运行

### 实际做了什么

在 v1 基础上增加批量能力：

- **`AutonomousUseCasesPage.vue` 重写**：
  - scenario 行新增 checkbox，缺少 `url_pattern` 时 disabled + tooltip。
  - 批量工具栏：已选/可运行计数、全选可运行用例、清空选择、批量运行、
    中止运行中任务。
  - 批量运行复用 `streamAutonomousRun`，并发上限 3（CONCURRENCY_LIMIT）。
  - 每个 scenario 展示 queued / running / completed / failed / aborted 状态
    （含颜色 tag + 失败错误摘要）。
  - 运行中禁用刷新、清空、选择变更、跳转 workbench；仅中止可用。
  - `onBeforeUnmount` 时 abort 所有 running task。
- **i18n**：zh / en / ja 各新增 14 个 key（`selectAllRunnable`、
  `clearSelection`、`runSelected`、`abortRunning`、`selectFirst`、
  `notRunnable`、`selectedCount`、`runnableCount`、`batchStatus`、
  `statusQueued`～`statusAborted`）。
- **`setup.ts`**：全局 stubs 新增 `a-checkbox`。
- **页面测试重写**：从 4 个 case 扩展到 11 个，覆盖全选只选可运行、
  清空、batch payload 字段、并发上限 3、abort 调用运行中任务、
  queued 任务直接标为 aborted、deep link 不回退。
  `streamAutonomousRun` 全部 mock，不触发真实 run。

### 和 plan 的偏离点

无偏离，按 plan 执行。

### 验证命令与结果

```bash
cd apps/console && pnpm run test
# 15 test files, 66 tests — all passed

pnpm run build:console
# vue-tsc --noEmit + vite build — clean
```

### 是否触发 live autonomous run

否。本次改动为纯前端 + i18n + 测试，批量运行通过 mock 验证，不涉及
后端或 autonomous explorer 逻辑，无需触发 live run。

## 2026-05-02 Codex review 修复

修复 Codex 指出的两个问题：

1. **`run_failed` SSE 事件未处理** — `onEvent` 原先只处理
   `run_completed`，导致 `run_failed` 事件到达后 `onDone` 会把状态
   从 `running` 误标为 `completed`。修复：`onEvent` 新增
   `run_failed` 分支，提取 `data.error` 写入 `task.error`，
   并确保 `onDone` 的 `if (task.status === 'running')` 守卫不会把
   `failed` 翻转回 `completed`。新增单测验证 `run_failed` →
   `failed` 且 `onDone` 不回退。

2. **新增文件 lint error** — `toggleSelect` 的 `_event` 参数声明
   后未使用。修复：移除该参数，同步清理模板中的 `$event` 实参。
   修复后 `eslint` 对新增文件报 0 errors / 3 warnings（均为
   `vue/attributes-order` 风格警告），不阻塞交付。

### 验证命令与结果

```bash
cd apps/console && pnpm run test
# 15 test files, 67 tests — all passed

pnpm run build:console
# vue-tsc --noEmit + vite build — clean

npx eslint src/pages/AutonomousUseCasesPage.vue \
  src/__tests__/components/AutonomousUseCasesPage.test.ts
# 0 errors, 3 warnings (attribute order style)
```
