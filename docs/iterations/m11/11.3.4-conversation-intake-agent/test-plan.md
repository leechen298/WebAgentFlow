# 测试计划（Test Plan）

状态：proposed（docs review pending, implementation not started）

## 文档阶段

本轮只运行：

```bash
git diff --check
```

不得触发 `verify-scenario`、autonomous run、product-driven browser execution 或 live LLM smoke。

## 后续实现阶段测试

### Intake schema / parser

覆盖自然语言变体：

```text
学习一下这个工作台登录页怎么进入，地址是 http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456
学习这个登录页：http://localhost:5176/workspace-login，用户名 demo，密码 123456
学习这个页面怎么登录，http://localhost:5176/workspace-login，账号 demo，口令 123456
学习这个入口：http://localhost:5176/workspace-login，demo / 123456
```

期望：

```text
intent=learn_operation
target.url=http://localhost:5176/workspace-login
target.site_origin=http://localhost:5176
slots include username-like and password-like values
password-like slot sensitive=true
```

### 缺失信息追问

输入：

```text
学习一下这个登录页：http://localhost:5176/workspace-login
```

期望：

```text
should_ask_user=true
missing_fields includes username/password-like fields
no learning run is started
pending_intake is saved
```

### 补充信息续接

已有 pending intake 时输入：

```text
用户名 demo，密码 123456
```

期望：

```text
intent=provide_missing_info
pending_intake is merged
missing_fields cleared
learning proceeds
```

没有 pending intake 时输入同一句，期望：

```text
no learning / replay
user is asked to first say what to learn or execute
```

### pending_intake 清理

覆盖：

- learning 成功后清除。
- 用户取消 / exit 后清除。
- 新学习目标覆盖时清除。
- `turns_remaining` 到 0 后清除。
- schema 校验失败时不清除。
- target URL 变化且用户未确认时不自动合并。

### 执行意图泛化

当前 session 已学过 `http://localhost:5176/workspace-login` 后，以下输入应能命中同一 action：

```text
帮我进入工作台
帮我登录这个页面
打开工作台
进一下刚才那个页面
```

仍必须遵守：

```text
only current session learned actions
target_url / site_origin scope
no global cross-site fallback
```

### LLM 失败负例

覆盖：

- provider 未配置：fallback deterministic parser，但不得标记 LLM-intake acceptance passed。
- malformed JSON：不得触发 learning / replay。
- schema 校验失败：不得触发 learning / replay。
- confidence 低于阈值：必须追问，不得猜测执行。
- LLM 输出 selector / learned_path_id / browser steps：schema 或 guardrail 拒绝。

### Redaction

覆盖：

- sensitive slot 在 events / history / debug console 中 redacted。
- LLM prompt payload / request log / provider trace 不长期保存明文 sensitive slot。
- 用户可见回复不重复明文密码。

### Regression

覆盖：

- 非 `interactive_chat` session 继续走 preview / confirmation / developer workflow。
- `wagent conversation send` 不启用 M11.3.4 auto execute path。
- M11.3.3 product-level target URL scope 不回退。

## 推荐命令

后续实现阶段建议至少运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_intake.py tests/test_conversation_chat_runtime.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py -q
git diff --check
```

如果实现接入真实 LLM provider，LLM-backed acceptance 必须另行记录真实 smoke evidence；
只跑 fake / stub provider 不得声称 LLM-intake acceptance passed。
