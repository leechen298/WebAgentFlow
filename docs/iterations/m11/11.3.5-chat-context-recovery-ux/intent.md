# 意图（Intent）

状态：proposed（docs generated, implementation not started）

## 背景

M11.3.4 已经把 `wagent chat` 的自然语言理解层从纯 regex 推进到
Conversation Intake Agent + schema-constrained intent。人工测试证明基础设施存在，
但小白用户并不会总是一次说完整命令。

用户常见输入是：

```text
先把页面地址发给系统
再说“学习”或“登录”
```

当前系统把每一句话过度孤立处理，导致裸 URL 被当成 execute，短句“学习”也被当成 execute。

## 用户目标

普通用户可以自然地分多轮表达：

```text
You > http://localhost:5176/workspace-login
WAgent > 我看到你发了一个页面地址。你想让我学习这个页面上的什么操作？
You > 学习登录，账号 demo，密码 123456
WAgent > 我会打开浏览器学习：登录。
```

## 成功标准

- 用户输入裸 URL 时，系统不会直接执行。
- 系统保存 pending target，并追问用户意图。
- 用户下一轮说“学习”“登录”“进入工作台”时，可以引用 pending target。
- 未学过页面的 no-path 结果会引导学习，而不是只冷拒绝。
- CLI 在后端判断前给出中性 loading，不提前猜测“执行”。
- 所有 learning / replay 仍由代码裁决和现有服务执行。

## 非目标

- 不让 LLM 直接操作浏览器。
- 不引入 LLM step-by-step browser execution。
- 不新增内部 Agent。
- 不做 M12 recovery / retry / abort。
- 不做全局 LearnedPath 自动召回。
- 不改变非 `interactive_chat` developer workflow。
