# 实施计划（Implementation Plan）

状态：accepted（implementation review passed, product-level CLI smoke passed）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`

## 文件 / 模块

已修改：

- `apps/product-test-site/` - 新增产品级 chat 验收站点。
- root workspace / scripts - 接入 product-test-site dev / build。
- conversation learning path - 增加 product-level learning mode，不读 validation specs。
- `apps/cli/wagent/chat.py` - 如需，补产品级输入解析和用户文案。
- tests - 覆盖 product-level learning 不传 `spec_id / scenario`。
- `docs/user-guide/wagent-chat.md` - 实现后把 product-test-site 从“计划”更新为“可用”。

文档阶段已创建 11.3.3 文档包并更新索引 / 用户指南。实现阶段已完成并通过
product-level CLI smoke。

## 步骤

1. 文档阶段：创建 11.3.3 七件套。
   - 文档审核后进入实现阶段，当前已完成实现收口。
   - 写清 validation-site 与 product-test-site 边界。
   - 写清 11.3.2 编号已占用。

2. 文档阶段：更新 M11 索引。
   - `README.md` 追加 11.3.3。
   - `m11-plan.md` 追加 11.3.3 章节。
   - 不移动 11.2.4.2，不修改 11.3.2 目录。

3. 文档阶段：更新用户指南。
   - 说明 product-test-site 是计划新增的产品级验收站。
   - 保持 `.venv/bin/wagent chat` 为主入口。
   - 不把 product-test-site 写成当前可用。

4. 实现阶段：新增 `apps/product-test-site`。
   - `@web-agent-flow/product-test-site`。
   - port `5176`。
   - 第一阶段实现 `/workspace-login`。
   - 接入根目录 `pnpm run dev` 一键启动。

5. 实现阶段：改造 `wagent chat` product learning。
   - 从用户 utterance 解析 URL 和必要输入。
   - 不读取 validation assertions。
   - 不传 `spec_id / scenario`。
   - 移除 product-level learning 的 `/login` only gate。
   - 学习时只打开用户输入的 target URL。
   - 学习成功后沉淀 LearnedPath。
   - `learned_actions` 至少按 alias + target URL / site scope 区分。
   - 执行未学习过的 target URL / site 时返回用户级未学习反馈。

6. 实现阶段：验证。
   - product-test-site build。
   - `pnpm run dev` 一键启动包含 product-test-site。
   - validation-site regression build。
   - product-level chat smoke。

## 验证

文档阶段：

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `git diff --check` | whitespace clean | Yes | 本轮唯一必跑命令 |

实现阶段：

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `pnpm --filter @web-agent-flow/product-test-site build` | product-test-site build pass | Yes | 不触发 browser |
| `pnpm run dev` | product-test-site 随 console / api / worker / validation-site 一起启动 | Yes | 实现阶段必须验证 |
| `pnpm --filter @web-agent-flow/validation-site build` | validation-site regression pass | Yes | 保留工程靶场 |
| `.venv/bin/wagent chat` | product-level learning / execution smoke | No | 必须记录真实 evidence |

## 复核清单（Review Checklist）

- [x] 11.3.3 不覆盖 11.3.2。
- [x] 11.2.4.2 仍属于 M11.2 validation fixture 体系。
- [x] 用户指南没有回退到只写 `source .venv/bin/activate && wagent chat`。
- [x] product-test-site 不复用 validation specs / assertions。
- [x] product-test-site 已接入根目录 `pnpm run dev`。
- [x] product-level learning 不传 `spec_id / scenario`。
- [x] product-level learning 不再限制为 `/login`。
- [x] 学习和执行都以用户输入或当前 session 已学习的 target URL 为边界。
- [x] 未学习过的站点 / 页面返回用户级反馈，不跨站点命中历史 LearnedPath。
- [x] 修改或删除 `login.assertions.json` 不影响 product-test-site learning。
- [x] validation-site 原有 verify / smoke 能力不被破坏。
- [x] 实际验证证据记录到 `review.md`，未运行项写明原因。
