# 真实网页运行时场景目录（Realistic Web Runtime Cases）

状态：场景目录已初始化

本文档记录 M11.2 的真实网页运行时场景。它不是测试计划，也不是证据报告。

下列场景不代表已经自动化、人工验证或被 E2E 覆盖。它们是后续 11.2.x 设计、
fixture、实现、QA 和 evidence 包的输入。

## 观察边界

M11.2 负责观察和记录运行时变化。M12 决定当这些变化表示失败、不确定、中断
或需要 recovery 时应该怎么处理。

Post-action Observation 覆盖用户或 replay 动作后短时间内的页面变化。Passive
Runtime Observation 覆盖不是由当前动作直接触发的页面变化。

## 场景目录

### 点击后出现 Modal（Modal After Click）

- 场景名称（case name）：modal after click。
- 场景（scenario）：点击某个操作后打开确认、详情或表单 modal。
- 价值（why it matters）：如果下一步必需 UI 在 modal 内，replay 不能把 click
  完成误判为业务任务完成。
- M11.2 预期观察（expected observation）：记录 modal 出现、title / role /
  visible text，以及预期 modal 是否在点击后变为可见。
- 不在范围（not in scope）：modal 未出现时选择 recovery path。
- 后续 M12 含义（future M12 implication）：modal 缺失或出现非预期 modal，
  后续可能进入 recovery 或 takeover 决策。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  fixture pages。

### 提交后出现 Toast（Toast After Submit）

- 场景名称（case name）：toast after submit。
- 场景（scenario）：提交表单后显示短暂的 success、warning 或 error toast。
- 价值（why it matters）：toast 可能是唯一结果信号，而且可能在 result reporting
  读取最终状态前消失。
- M11.2 预期观察（expected observation）：记录 toast 出现、可见 severity、文本内容，
  以及可观察到的消失时间。
- 不在范围（not in scope）：判断 error toast 是否应该触发 retry。
- 后续 M12 含义（future M12 implication）：error toast 或 missing toast 后续
  可能需要 recovery dialogue。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.5
  observation evidence into Task Result Reporter。

### 按钮延迟变为可用（Delayed Button Enabled）

- 场景名称（case name）：delayed button enabled。
- 场景（scenario）：按钮在 validation、async permission check 或 network data
  完成前保持 disabled。
- 价值（why it matters）：如果不能观察 enabled 状态变化，replay 可能过早点击。
- M11.2 预期观察（expected observation）：记录 disabled -> enabled transition、
  目标元素 identity，以及 timeout / not-observed 状态。
- 不在范围（not in scope）：重试点击或要求用户修复输入。
- 后续 M12 含义（future M12 implication）：按钮一直未 enabled 后续可能成为
  blocked execution 或 recovery prompt。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.2
  wait-for-change MVP。

### 网络延迟后的搜索结果（Search Result After Network Delay）

- 场景名称（case name）：search result after network delay。
- 场景（scenario）：输入搜索词或点击 Search 后，结果行在延迟的网络请求完成后更新。
- 价值（why it matters）：立即读取结果可能读到旧行。
- M11.2 预期观察（expected observation）：记录 loading transition、row count /
  empty state change、可见结果文本，以及 action 后内容是否发生变化。
- 不在范围（not in scope）：修改搜索词或 retry 请求。
- 后续 M12 含义（future M12 implication）：timeout 或结果未变化后续可能需要
  用户选择或 recovery。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  fixture pages。

### 局部列表刷新（Partial List Refresh）

- 场景名称（case name）：partial list refresh。
- 场景（scenario）：URL 和页面 shell 不变，只有 table、list 或 card region 刷新。
- 价值（why it matters）：很多 SPA 和 dashboard flow 不能只靠 page-level
  navigation signals。
- M11.2 预期观察（expected observation）：记录 region-level content mutation、
  row count change、updated item text，以及 stale-vs-new evidence。
- 不在范围（not in scope）：从任意 list content 判断业务正确性。
- 后续 M12 含义（future M12 implication）：没有刷新或刷新了错误 region，后续
  可能变成 blocked / needs-review state。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.3
  replay integration with observation。

### URL 不变的 SPA 内容更新（SPA Content Update Without URL Change）

- 场景名称（case name）：SPA content update without URL change。
- 场景（scenario）：route-like state change 替换 main content，但浏览器 URL 不变。
- 价值（why it matters）：只等待 URL 会漏掉客户端状态切换。
- M11.2 预期观察（expected observation）：记录不依赖 URL 变化的 title、heading、
  landmark、visible text 或 main-region change。
- 不在范围（not in scope）：实现完整 SPA router 语义。
- 后续 M12 含义（future M12 implication）：预期内容一直不出现，后续可能需要
  explanation 或 takeover。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.3 replay
  integration with observation。

### 动作后延迟完整页面刷新（Delayed Full Page Reload After Action）

- 场景名称（case name）：delayed full page reload after action。
- 场景（scenario）：用户点击提交、保存、跳转或确认按钮后，页面触发完整
  document reload。URL 可能变化，也可能保持不变。刷新完成前，新内容不会立即出现。
- 价值（why it matters）：replay 不能在点击后立即判断结果，否则会误判页面尚未
  稳定。same-url reload 也不能只靠 URL 变化判断。
- M11.2 预期观察（expected observation）：记录 `page_load_started` 和
  `page_load_finished`；可选记录 `url_changed`、`title_changed`、
  `text_appeared`、`network_idle_observed`。
- 不在范围（not in scope）：不判断刷新失败后是否 retry，不处理 timeout
  recovery，不自动 abort。
- 后续 M12 含义（future M12 implication）：如果 page load 长时间未完成，M12
  可基于 observation evidence 决定是否提出 retry / recovery / user takeover。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.2
  wait-for-change MVP / 11.2.3 replay integration。

### 校验错误信息（Validation Error Message）

- 场景名称（case name）：validation error message。
- 场景（scenario）：表单提交或字段 blur 后显示 inline validation errors。
- 价值（why it matters）：replay 可能机械完成，但实际任务被 validation 拒绝。
- M11.2 预期观察（expected observation）：记录可见 validation message、可观察到的
  field association 和 error text。
- 不在范围（not in scope）：修复 input values 或重新绑定 slots。
- 后续 M12 含义（future M12 implication）：validation failure 后续可能路由到
  recovery、用户澄清或教学阶段。
- 后续执行包（future package）：11.2.5 observation evidence into Task Result
  Reporter / 11.2.7 runtime observation tests and evidence。

### 骨架屏后出现内容（Loading Skeleton Then Content）

- 场景名称（case name）：loading skeleton then content。
- 场景（scenario）：skeleton、spinner 或 placeholder 被真实内容替换。
- 价值（why it matters）：skeleton 仍可见时读取页面，可能产生 false uncertainty
  或 stale evidence。
- M11.2 预期观察（expected observation）：记录 skeleton / loading presence、
  disappearance，以及后续 content appearance。
- 不在范围（not in scope）：内容一直不加载时选择 fallback action。
- 后续 M12 含义（future M12 implication）：loading 持续存在后续可能成为 blocked
  或 recovery dialogue。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  fixture pages。

### 延迟出现的 Popup（Delayed Popup）

- 场景名称（case name）：delayed popup。
- 场景（scenario）：popup、dropdown、date picker、cascader 或 menu 在延迟 click
  或 hover-related UI update 后出现。
- 价值（why it matters）：如果 replay 预期 popup 立即可见，就可能漏掉
  popup-based controls。
- M11.2 预期观察（expected observation）：记录 popup visibility、可观察到的
  anchor relation，以及 option text / role signals。
- 不在范围（not in scope）：实现新的 popup control operation logic。
- 后续 M12 含义（future M12 implication）：popup 缺失后续可能需要 takeover 或
  teaching。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  fixture pages。

### 组件库交互后生成运行时界面片段（Component-generated Runtime Surface After Interaction）

- 场景名称（case name）：component-generated runtime surface after interaction。
- 场景（scenario）：用户点击、聚焦、选择或输入后，常用组件库生成新的运行时
  界面片段。该片段可能插入到 `body`、当前元素内部、兄弟节点、portal / teleport
  容器，或只表现为 class / aria / selected / disabled / active 状态变化。
- 价值（why it matters）：replay 不能只依赖 URL / title / 原节点子树变化。真实
  组件库经常把 option panel、picker、toast、modal、drawer、action sheet、
  validation message 等渲染到触发元素之外。
- M11.2 预期观察（expected observation）：记录 `element_appeared`、
  `element_disappeared`、`modal_opened`、`modal_closed`、`toast_shown`、
  `loading_finished`、`element_enabled`、`element_disabled`、
  `form_validation_message`、`list_changed`，以及 future component relation
  evidence。
- 关联提示（relation hints）：action timing、aria-expanded / aria-controls /
  aria-owns、role=listbox / option / menu / dialog、focus movement、active
  descendant、bounding rect proximity、component class pattern as supporting
  evidence。
- PC 组件库示例（PC component examples）：Ant Design、Element Plus、Naive UI、
  Arco Design、TDesign、MUI / Material-ish、Bootstrap-style components。
- 移动端组件库示例（mobile component examples）：Ant Design Mobile、Vant、NutUI、
  Varlet、Ionic、Framework7-style mobile components。
- 不在范围（not in scope）：不在 11.2.2 MVP 中完整实现组件库行为识别；不调用
  LLM 判断 popup / panel 归属；不让 Agent 进入 per-step execution loop；不把
  组件库 class 作为唯一依据。
- 后续 M12 含义（future M12 implication）：组件库界面片段缺失、状态未变化或
  关联不确定时，后续可成为 result reporter uncertainty 或 M12 recovery / takeover
  的输入，但 M11.2 不做决策。
- 后续执行包（future package）：later 11.2.x Common Component Runtime Semantics /
  11.2.4 realistic fixture pages / 11.2.5 reporter evidence integration。

### 服务端推送消息（Server Push Message）

- 场景名称（case name）：server push message。
- 场景（scenario）：backend event 在没有用户动作的情况下向页面推送新
  notification、message 或 status。
- 价值（why it matters）：页面独立变化可能改变 replay result evidence。
- M11.2 预期观察（expected observation）：记录 passive message appearance、可见
  timestamp、visible text 和 affected region。
- 不在范围（not in scope）：决定是否 interrupt 当前 execution。
- 后续 M12 含义（future M12 implication）：passive changes 后续可能需要
  v0.2 / M12 的 interruption 或 recovery handling。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.3
  replay integration with observation。

### WebSocket / SSE / Polling 更新

- 场景名称（case name）：WebSocket / SSE / polling update。
- 场景（scenario）：live transport 或 polling 更新 task status、list content
  或 counters。
- 价值（why it matters）：runtime evidence 可能在 replay action 之后、普通
  navigation 或 click completion 之外到达。
- M11.2 预期观察（expected observation）：记录 live update 造成的 DOM / text
  changes；11.2.0 不要求 transport-level interception。
- 不在范围（not in scope）：实现 WebSocket、SSE 或 polling protocol inspection。
- 后续 M12 含义（future M12 implication）：live failure status 后续可能需要
  recovery 或 abort dialogue。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.5
  observation evidence into Task Result Reporter。

### 被动 DOM 变化（Passive DOM Mutation）

- 场景名称（case name）：passive DOM mutation。
- 场景（scenario）：ads、personalization、timer、counter、banner 或 background
  scripts 在没有直接用户动作的情况下改变 DOM。
- 价值（why it matters）：不是每个 DOM mutation 都应该被当成 task evidence。
- M11.2 预期观察（expected observation）：记录 passive mutation category、
  affected region，以及它是否可能和当前 replay / result boundary 有关。
- 不在范围（not in scope）：完整 relevance classification 或 recovery policy。
- 后续 M12 含义（future M12 implication）：相关 passive mutation 后续可能驱动
  interruption 或 user-choice flows。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.6
  Codex realistic web QA。
