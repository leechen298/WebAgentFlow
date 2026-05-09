# Replay E2E Codex 探索式运行提示词

你正在为 WebAgentFlow M10.2 replay E2E 运行 Codex 探索式验证。

你不能编造结果。除非每一个写成 PASS 的 case 都有命令证据，否则不能宣称测试完成。

硬规则：

- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不 import 或直接运行 autonomous explorer。
- 不依赖 LLM provider。
- 不修改产品代码。
- 不修改 E2E 测试代码，除非后续任务明确要求。
- 没有原始命令证据，不得标记 PASS。
- 没有执行的 case 标记 `NOT_RUN`。
- 环境阻塞的 case 标记 `BLOCKED`。
- 命令失败时，用真实 stdout/stderr 标记 `FAIL` 或 `BLOCKED`。
- 不得写“全部测试通过”，除非精确命令输出证明这一点。
- 不得写“手动测试完成”，除非有命令或浏览器操作证据。

必填报告路径：

`docs/testing/results/YYYY-MM-DD-replay-e2e-codex-exploratory.md`

每个 case 必须包含：

- case_id
- status: PASS | FAIL | BLOCKED | NOT_RUN
- command_or_method
- 如果运行了命令，必须写 exit_code
- evidence excerpt
- notes（备注）
- 如有需要，写 follow_up（后续处理）

执行顺序：

1. 读取 `docs/testing/exploratory/replay-e2e-cases.md`。
2. 记录 `git rev-parse HEAD`。
3. 记录 `git status --short`。
4. 执行 preflight cases。
5. 复跑 deterministic E2E。
6. preflight 通过后执行 API exploratory cases。
7. 仅在 console/API/validation-site 可访问，且不需要修改产品或 E2E spec 代码时，
   执行 UI exploratory cases。
8. 写入报告。
9. 运行 `git diff --check`。

Autonomous endpoint 搜索规则：

- `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream` 字符串只允许
  出现在禁止请求保护逻辑、文档或边界说明中。
- 如果它们作为请求目标、API helper 或真实调用路径出现，该 case 必须 FAIL。
- 报告必须包含搜索输出摘录和判断理由。

API exploratory 执行规则：

- 可以使用 curl、`python -c`、`node -e` 或临时脚本。
- 如果创建临时脚本，执行后必须删除。
- 不要把临时脚本提交为长期测试。

UI exploratory 执行规则：

- 第一轮 replay exploratory 不强制执行全部 UI exploratory cases。
- 如果不修改产品代码或 E2E spec 代码就无法可靠执行，标记 `NOT_RUN` 或 `BLOCKED`。
- 不添加 `data-testid`。
- 不修改现有 E2E specs。
- 如果报告声明 visual UI exploratory PASS，必须使用 Codex Browser panel /
  in-app browser 或 headed Playwright 打开真实页面并执行可见 UI 操作。
- Headless Playwright E2E 不能算 visual UI exploratory。
- API-only 调用不能算 visual UI exploratory。
- visual UI exploratory 必须记录页面观察、截图、trace、video 或明确的
  browser observation 证据。

最终回复必须包含：

- 报告路径
- 执行了多少 case
- PASS / FAIL / BLOCKED / NOT_RUN 统计
- 执行了哪些命令
- 是否调用了 autonomous endpoint
- 是否使用了 LLM provider
- `git diff --check` 结果
