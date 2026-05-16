# 测试计划（Test Plan）

状态：documentation generated; implementation not started

## Test Scope

后续 11.2.4.1 实现完成后应覆盖：

- validation-site index catalog。
- runtime observation route shell。
- category navigation。
- fixture card metadata rendering。
- stable anchors。
- no backend dependency。
- no reporter / replay dependency。

不覆盖：

- 具体业务 fixture 页面。
- mock backend。
- E2E evidence closure。
- Task Result Reporter。
- M12 recovery。
- `verify-scenario`。
- autonomous run。

## Documentation Validation

- 11.2.4.1 文档包完整。
- Shell contract 存在。
- Route namespace 使用完整路径：
  - `/runtime-observation`
  - `/runtime-observation/basic`
  - `/runtime-observation/medium`
  - `/runtime-observation/complex`
  - `/runtime-observation/mobile`
- PC priority 写清。
- current MVP signals 与 evidence capabilities 分离。
- future labels 未写成 implemented。

## Future Unit / Component Tests

如果 validation-site 有组件测试基础，后续应覆盖：

- `RuntimeObservationIndex` renders category cards。
- Fixture card renders `fixture_id`、platform、business complexity、phase、status。
- Current MVP observation signals render separately from evidence capabilities。
- Future signal labels do not appear as implemented。
- Reset convention text exists。
- Stable anchor convention text exists。
- Mobile category exists but is labeled as later 11.2.4.6 priority。

## Future Route Smoke

后续实现后可验证：

- `/runtime-observation` 可打开。
- 首页 `/` 有 Runtime Observation 分类入口。
- `/login`、`/users` 原入口不受影响。
- category navigation 可见。
- planned fixture cards 可见。
- missing future fixture routes are not presented as implemented links。

## Boundary Tests

后续实现后必须确认：

- 不调用 API。
- 不调用 replay。
- 不调用 Task Result Reporter。
- 不调用 autonomous run。
- 不触发 `verify-scenario`。
- 不依赖外部网站。

## Planned Commands

后续实现完成后可能运行：

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site test
pnpm --filter @web-agent-flow/e2e exec playwright test tests/runtime-observation/*.spec.ts
```

后续实现前需确认 validation-site / e2e 的实际 test command。没有真实运行不得写成 PASS。

本轮文档生成只运行文档级 validation：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

## Evidence Requirements

未来 `review.md` 记录测试时必须包含：

- command。
- expected result。
- actual result。
- exit code。
- pass / fail / skip count。
- not run reason。

不得写：

- `tested`
- `E2E passed`
- `verified`
- `works`

除非有实际命令和证据。
