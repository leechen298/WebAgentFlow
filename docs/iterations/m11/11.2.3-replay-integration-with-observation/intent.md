# Intent

状态：implementation complete

## 本轮意图

11.2.3 的意图是将 11.2.2 已实现的 step-level `wait_result` 提升为
replay-level observation evidence，并按技术设计落地为 replay result 上的可选
observation summary。

11.2.2 已经回答：

```text
某个 replay action 后，系统等了什么？
这个 step 的 wait outcome 是 observed / timeout / skipped / not_required 中的哪一个？
这个 step 观察到了哪些 signals？
```

11.2.3 定义下一层问题：

```text
整个 replay 执行过程中观察到了哪些变化？
哪些 step 有 primary observation？
哪些 step timeout / skipped / not_required？
是否只有 supporting observation？
这些 evidence 如何成为后续 Task Result Reporter 的输入？
```

## 非目标

11.2.3 代码实现可以修改 replay response schema、learning service、replay
integration 和 scoped tests，但不做：

- 不接 Task Result Reporter。
- 不做 recovery / retry / abort / user takeover。
- 不做 Page Understanding Agent。
- 不做 Page Context Bridge。
- 不做 Common Component Runtime Semantics。
- 不读取或保存 raw HTML。

## 设计边界

Replay Observation Evidence 只能记录 replay 期间的观察事实和 uncertainty flags。
它不是 replay status，不是业务成功判断，也不是 recovery decision。

如果 summary 发现 `timeout`、`no_primary_observation` 或
`has_only_supporting_observation`，11.2.3 只能记录 evidence 和不确定性。是否 retry、
abort、询问用户或进入 recovery dialogue 属于 M12。
