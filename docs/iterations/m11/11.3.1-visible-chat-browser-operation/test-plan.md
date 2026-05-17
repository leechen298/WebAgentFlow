# 测试计划（Test Plan）

状态：proposed

## 适用条件

本轮满足以下触发条件，因此必须维护 `test-plan.md`：

- 涉及 replay / autonomous learning runtime config。
- 涉及 CLI product entry。
- 涉及 product-driven browser execution。
- 涉及人工测试和 live browser evidence。
- 需要区分 unit / integration / CLI / manual smoke。

## 测试范围（Test Scope）

- Unit：CLI parser / payload、chat runtime metadata policy、replay hook headless option。
- Integration：conversation dispatch 到 learning / replay handler 的 headless 参数传递。
- API：conversation dispatch regression，确保非 interactive chat 不变。
- Console UI：N/A，本轮不改 console。
- E2E：只在人工 smoke 中通过 `wagent chat` 观察真实浏览器。
- Agent / Reporter / Recovery：N/A，本轮不改 internal Agent、Reporter、recovery。
- Codex / AI External Operator：如由 Codex 操作，只能记录真实 CLI / 浏览器结果。
- Live autonomous run：人工 smoke 的学习链路会触发真实 learning run；必须记录可复查 evidence。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| CLI | CLI-0 reliable local entry | `test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'` and `.venv/bin/wagent --help` | local CLI exists and help lists `chat` | Yes | Must pass before browser smoke |
| CLI | CLI-1 default visible payload | `apps/cli/tests/test_chat.py` | create-session metadata includes `browser_visibility=visible` | Yes | 不启动真实 API |
| CLI | CLI-2 headless opt-out payload | `apps/cli/tests/test_chat.py` | `wagent chat --headless` writes `browser_visibility=headless` | Yes | 覆盖 dispatch metadata 审计值 |
| CLI | CLI-3 ordinary wording | `apps/cli/tests/test_chat.py` | 输出用户可懂的打开浏览器 / 学习 / 执行文案 | Yes | 不暴露 selector / id / LearnedPath |
| API unit | API-1 visible learning | `apps/api/tests/test_conversation_chat_runtime.py` | visible session calls learning handler with `headless=False` | Yes | handler mock records kwargs |
| API unit | API-2 visible replay | `apps/api/tests/test_conversation_chat_runtime.py` | visible session calls replay handler with `headless=False` | Yes | 不进入 confirmation |
| API unit | API-3 headless session | `apps/api/tests/test_conversation_chat_runtime.py` | headless session passes `headless=True` | Yes | 学习和执行都覆盖 |
| API unit | API-4 missing metadata default | `apps/api/tests/test_conversation_chat_runtime.py` | missing `browser_visibility` defaults to visible for interactive chat | Yes | 兼容旧 session |
| Replay | API-5 replay hook override | `apps/api/tests/test_conversation_replay_hook.py` / `test_learned_path_replay.py` | default headless remains true; override false reaches runtime config | Yes | 不真实启动浏览器 |
| Regression | REG-1 non-chat confirmation | existing conversation tests | non interactive free text still uses preview / confirmation | Yes | 不受 visible policy 影响 |
| Docs | DOC-1 doc hygiene | `git diff --check` | no whitespace errors | Yes | 文档阶段也跑 |
| Manual smoke | MANUAL-1 visible browser operation | `wagent chat` | 用户能看到 Playwright Chromium 打开并执行验收页面操作 | Yes before acceptance | 需要用户或外部测试操作员记录真实观察 |
| Manual smoke | MANUAL-2 headless opt-out | `wagent chat --headless` | 不显示浏览器，CLI 仍能完成同一验收路径 | Optional | 可作为 regression |

## 人工验收样例（Manual Acceptance Sample）

本节只定义当前验收靶子，不定义功能边界。可见浏览器能力应适用于 `wagent chat` 的学习和执行链路。

启动项目：

```bash
pnpm run dev
```

进入聊天：

```bash
test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'
.venv/bin/wagent chat
```

可选写法是先 `source .venv/bin/activate` 再运行 `wagent chat`，但人工验收的主入口使用
`.venv/bin/wagent chat`，避免 PATH 指到错误虚拟环境。

输入：

```text
学习一下这个登录页怎么登录，地址是 http://localhost:5175/login
```

期望：

- 终端出现普通用户文案，说明会打开浏览器学习页面操作。
- 用户能看到 Playwright Chromium 窗口打开。
- 用户能看到页面被加载，并看到系统输入账号密码、点击登录按钮。
- 学习完成后 CLI 返回类似：

```text
WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
```

继续输入：

```text
帮我登录
```

期望：

- 用户能看到浏览器再次打开或继续打开，并执行登录操作。
- CLI 返回：

```text
WAgent > 登录完成。
```

后台运行 opt-out：

```bash
.venv/bin/wagent chat --headless
```

期望：

- 不显示浏览器窗口。
- CLI 行为仍然完成同一学习 / 执行流程。

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 如果没有真实打开浏览器，不得声称 `MANUAL-1` 已通过。
- 如果只跑了单元测试，必须写成“未进行可见浏览器人工 smoke”。
- 人工 smoke 需要记录：
  - 运行命令；
  - 验收 URL；
  - 用户实际看到的浏览器行为；
  - CLI 输出；
  - 如产生 run_id / history detail，可附上可复查路径。
- 如果浏览器验证由用户执行，必须标记为 user acceptance。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 只能作为外部测试操作员记录自己真实执行过的动作。不得编造内部 Agent 结论，
不得把代码审查、静态推理或未执行的命令写成测试通过。

每次声称“已测试”时必须能回答：

- 实际运行了什么 CLI？
- 是否真实看到可见浏览器？
- 原始 CLI 输出是什么？
- 是否有截图、日志、exit code、pass / fail count 或可复查输出？

## Live Run 边界（Live Run Boundary）

本轮不要求 Codex 在文档阶段触发 live run。

实现完成后，如果通过 `wagent chat` 学习验收页面，会触发真实 autonomous learning。报告时必须遵守
AGENTS.md 的 WebAgentFlow live run reporting style：

- lead with `pass_gate.status`；
- 记录 `run_id`；
- 记录 Supervisor verdict / confidence / scorecard；
- 不把 `unverified` 写成 pass。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| Manual visible browser smoke | 文档阶段不运行产品 flow | 实现后必须补真实可见浏览器 evidence |
| Headless opt-out smoke | 文档阶段不运行产品 flow | 实现后至少用 CLI / unit 覆盖，必要时人工 smoke |
