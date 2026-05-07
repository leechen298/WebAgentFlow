# 10.2.6 Catalog UI

## 目标

让用户在 LearnedPath catalog 中直接对某条路径发起 replay，并在同一个
drawer 里看到 replay / drift / step log 结果。

## 触及模块

- `apps/console/src/api/exploration.ts`
- `apps/console/src/pages/LearnedPathCatalogPage.vue`
- `apps/console/src/i18n/locales/zh.ts`
- `apps/console/src/i18n/locales/en.ts`
- `apps/console/src/i18n/locales/ja.ts`
- `apps/console/src/__tests__/components/LearnedPathCatalogPage.test.ts`
- `apps/console/src/__tests__/api/exploration.test.ts`
- `apps/console/src/__tests__/i18n/locales.test.ts`

## 固定交互

1. 用户打开某条 LearnedPath 的 actions drawer。
2. drawer 顶部展示 Replay 区块。
3. Replay 区块包含：
   - URL 输入框，默认值为空；
   - Replay 按钮；
   - URL 为空时按钮 disabled。
4. 点击后调用：

```text
replayLearnedPath(pathId, { url })
```

5. drawer 内展示：
   - replay status；
   - drift status；
   - drift reasons；
   - warnings；
   - current signature vs stored signature；
   - step logs timeline；
   - final URL / title。

## UI 状态

- loading：按钮 loading，输入框保留当前 URL。
- error：HTTP / runtime error 以 drawer 内 alert 展示。
- result：展示 status、drift、warnings、steps、final state。

## 文案要求

中文文案要说人话：

- `Replay`：重跑这条路径
- `drift`：页面变化
- `target_missing`：找不到当初记录的按钮或输入框
- `unsupported_action`：这类动作当前还不能重跑
- `observed`：这条路径没有动作，已完成页面观察

必须避免：

- “已通过”这类容易和 `pass_gate` 混淆的文案。
- “Supervisor 验证成功”这类 replay 并没有做的事。
- “重新学习”暗示。

## 本轮不做

- 不新开 replay workbench。
- 不做自动候选 replay UI。
- 不做 task input / chat 入口。

## 验收

- drawer 中渲染 replay 区块。
- URL 输入后点击 Replay 调用 API。
- loading / error / result 状态都有展示。
- `target_missing` 能显示友好文案。
- `observed` 能显示“这条路径没有动作，已完成页面观察”。
- 三语 i18n key 齐全。
