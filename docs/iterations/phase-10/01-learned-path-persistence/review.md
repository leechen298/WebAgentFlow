# 审核与反思

迭代过程中的审核产出、用户反馈、收尾反思按时间顺序追加到本文件。

## 2026-04-24 环境基线

- `pytest tests/test_form_label_extractor.py` 在 `v0.1-local` 基线
  commit `57eb8a0` 上已有 20 个用例失败（12 通过）。本迭代开工前
  已 `git stash && pytest ... && git stash pop` 复现，证明这批失败
  **与本迭代无关**，属于已有技术债；本次不拉回去修。
- `pytest` 的若干 collection error（`test_assess_outcome` /
  `test_autonomous_supervisor` / `test_execution_runtime` /
  `test_page_analyzer_selector` / `test_semantic_role_inference` /
  `test_supervisor_prompt` / `test_toggle_values`）因当前 venv 缺少
  `playwright` 模块。`python -m playwright install chromium` 本机
  已装浏览器，但 `playwright` PyPI 包未同步进 venv —— 需要补装，
  和本迭代无关。验收时用 `--ignore` 跳过这几个文件来跑剩下的，本
  迭代自己的单测全绿。

## 开发过程中的 query_signature 异常 case 记录

开发 `page_signature.query_signature` 时每遇到一个白名单"漏网之鱼"
或"误伤"就在本节追加一行，阶段尾拉回来和用户对一次，决定哪些要进
特殊白名单。起始白名单规则：`len(v) <= 8 and v.isalpha()` 保留
（小写化），否则归一为 `"*"`。

- 2026-04-24 · `q=中文`（Unicode alpha）触发首轮规则漏网：Python
  `str.isalpha()` 对 CJK 字符返回 True，导致"中文"被保留。第一次
  写测试就暴露出来了。修法：白名单改成 `value.isascii() and
  value.isalpha()`。已加入单测 (`tests/test_page_signature.py::
  test_query_signature[/x?q=中文-expected11]`)。

## 开发过程中的 dom_fingerprint 调整记录

`page_signature.dom_fingerprint` 第一版靠 forms / buttons / toggles
/ selects + title + sha256。PageAnalysis 里没有 h1/h2 / 表头结构化
字段，所以暂用 title 兜底。遇到"明显同一页但指纹不等"或"明显不同
页但指纹相等"的 case 都在此追加。

- 2026-04-24 · 首次落地。已去除 `rc_*` / `css-dev-only-do-not-override-*`
  / 长 hex token（>=12 字符）三类 per-render 垃圾。未包含 h1/h2 /
  table_headers（PageAnalysis 没有这些槽）。后续真实运行出现抖动
  再调。

## 2026-04-24 代码实现进度

按 plan.md 的 6 步推进，这里记截止时间点的状态：

- ✅ **步骤 1** 迁移 + ORM + repo 骨架：`learned_paths` 表
  (`20260424_0001_add_learned_paths.py`)、`LearnedPath` 模型 + trust
  状态机枚举、`LearnedPathRepository` (ingest_run / list_page / get /
  find_by_source_run / set_trust)、16 条 repo 单测全绿。
- ✅ **步骤 2** page_signature：`path_template` / `query_signature` /
  `dom_fingerprint` 三函数 + 38 条单测全绿（含 Unicode alpha 边界
  case）。
- ✅ **步骤 3** 写回 hook：`_persist_autonomous_run` 在主写入成功
  后调 `_maybe_ingest_learned_path`。`pass_gate == "pass"` 时才
  写，其他 gate 状态短路；持久化异常只 `logger.warning`，不阻塞
  主运行返回。
- ✅ **步骤 4** 三个接口：`GET/PATCH /exploration/learned-paths/*`
  全部挂上；`get_autonomous_run` 返回体加 `learned_path_id` +
  `learned_path_trust`；12 条 API + hook 端到端单测全绿。
- ✅ **步骤 5** 前端：`exploration.ts` 加 `listLearnedPaths /
  getLearnedPath / patchLearnedPathTrust` + 类型定义；
  `AutonomousRunDetailPage.vue` 加 LearnedPath 区块（trust tag +
  Confirm / Mark wrong 按钮 + popconfirm 二次确认 + loading 状态 +
  空态提示）；en/zh/ja 三个 locale 同步添加 10 个新 key；
  4 条 API 单测 + 全套 vitest 48 条全绿；`vue-tsc --noEmit` 清；
  `pnpm run build:console` 成功。
- ⏳ **步骤 6** 文档尾声（未开始）：`product-model.md §9`（把
  "LearnedPath 尚不存在"改成"已交付"）、`architecture.md §G`（补一
  行 `page_signature.py` 职责）。留到用户确认迭代 OK 后再一起落。

## 2026-04-24 基线 lint / test 已知残留

这批问题在我开工前就存在，**和本迭代无关**；列在这里是给 codex-review
/ 未来接手的 AI 一个清单，别误算到本迭代头上：

- **pytest collection error** × 7（`test_assess_outcome` /
  `test_autonomous_supervisor` / `test_execution_runtime` /
  `test_page_analyzer_selector` / `test_semantic_role_inference` /
  `test_supervisor_prompt` / `test_toggle_values`）—— venv 缺
  `playwright` PyPI 包（浏览器是装了的，但 Python wrapper 没装进
  venv）。跟 LearnedPath 无关。
- **pytest 失败** × 20 在 `tests/test_form_label_extractor.py` ——
  Phase 9 留下的已有 bug，计划在 Phase 10 后续"Form-label extractor
  扩展"迭代里修。
- **ESLint** 18 error + 4 warning：`AutonomousWorkbenchPage.vue`
  (`v-model:` + `any`)、`autonomousStream.ts`
  (`no-constant-condition`)、`MainLayout.vue` (`v-model:` /
  hyphenation)、`HomePage.test.ts` (`any`)、`AutonomousRunDetailPage.vue`
  12:11（`:disabled` 在 `@click` 之后，但这一行**早于本迭代**就存在，
  stash 验证过）。我没碰这些文件里的问题，也没新增 lint 错误。

## 收尾反思（待填充）

等步骤 6 文档尾声落地后再追加一节，对比实际产出 vs intent.md / plan.md。
