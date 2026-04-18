# Skill 规范

## Skill 是什么

Skill 是可复用的自动化定义，描述 WebAgentFlow 应该如何完成某项任务。后续会加入版本管理、校验，并在 API / worker / extension 三端可执行。

## `steps` 是什么

`steps` 是 skill 内部有序的动作或声明列表。每个 step 描述自动化流程里的一个步骤及其输入。

## 未来的 step 类型

后续版本预计会支持以下几类 step：

- 浏览器导航
- 元素交互
- 数据抽取
- 条件分支
- 变量赋值
- 工具调用
- 断言与校验

---

本文为 [`skill-spec.md`](./skill-spec.md) 的中文镜像，内容以英文版为准。
