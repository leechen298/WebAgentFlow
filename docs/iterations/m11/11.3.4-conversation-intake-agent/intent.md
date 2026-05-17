# 意图（Intent）

状态：proposed（docs review pending, implementation not started）

## 目标

把 `wagent chat` 从规则驱动入口升级为可自然理解普通用户话语的产品入口：

```text
用户自然语言
-> Conversation Intake Agent 输出结构化 intent / target / action / slots / missing fields
-> Conversation Orchestrator 校验 session、target scope 和执行策略
-> Learning / Replay 服务完成真实浏览器学习或执行
```

## 动机

M11.3.3 已经证明 product-level `wagent chat` 可以学习并执行用户输入的目标站点。
但当前语言入口仍然过窄：

- 学习意图主要靠 URL + `学习 / learn / teach` 关键词。
- 输入值主要靠固定 label regex，例如 `账号`、`用户名`、`操作员账号`、`密码`、`访问口令`。
- 执行命中主要靠 utterance 精确匹配或 alias 包含匹配。

普通用户不会遵守固定格式。比如他们可能说：

```text
学习这个入口：http://localhost:5176/workspace-login，demo / 123456
帮我登录这个页面
进一下刚才那个工作台
```

这些都应该先被理解为结构化意图，再由代码做安全校验和执行。

## 第一原则

```text
不是让 LLM 控制浏览器。
是让 LLM 理解用户说的话。
```

Conversation Intake Agent 是受 schema 约束的自然语言理解层，不是浏览器操作 Agent。

## 成功标准

- 用户不需要遵守固定话术。
- 系统能抽取目标 URL、站点 origin、操作目标、输入槽位和缺失信息。
- 系统能理解 `用户名 / 密码`、`账号 / 口令`、`操作员账号 / 访问口令` 等自然说法。
- 缺少必要信息时系统追问，而不是猜测执行。
- 用户补充信息后能续接同一个 pending intake。
- `登录`、`进入工作台`、`打开工作台` 等近义目标可作为匹配辅助归一化。
- 执行仍只命中当前 session 已学习过的同 target URL / site scope action。
- 未学习 URL 不跨站点误执行。
- LLM 输出 JSON 解析失败、schema 校验失败或低 confidence 时不得触发浏览器动作。
- 敏感 slot 默认在 history / events / debug console / prompt logs 中脱敏。

## 非目标

- 不做 LLM step-by-step 浏览器控制。
- 不让 LLM 输出 Playwright selector 或浏览器操作步骤。
- 不让 LLM 直接选择 LearnedPath 并执行。
- 不做复杂多页面 workflow。
- 不做 M12 recovery / retry / abort。
- 不做真实业务系统适配。
- 不做完整风险 / consent policy。
- 不改变非 `interactive_chat` 的 developer workflow。
