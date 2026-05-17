<template>
  <div class="home-page">
    <header class="home-header">
      <h1 data-testid="workspace-home-title">工作台首页</h1>
      <span class="home-badge" data-testid="workspace-home-success">已进入工作台</span>
    </header>
    <main class="home-main">
      <p>欢迎进入工作台。这里是产品级聊天验收的登录成功页面。</p>
      <p>当前没有真实业务数据，仅用于验证 WebAgentFlow 产品级学习路径。</p>
    </main>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f4f6f8;
}
.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  background: #fff;
  border-bottom: 1px solid #d9e2ec;
}
.home-header h1 {
  margin: 0;
  font-size: 22px;
  color: #20262e;
}
.home-badge {
  padding: 6px 14px;
  background: #14804a;
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
}
.home-main {
  padding: 32px;
  font-size: 15px;
  color: #333;
  line-height: 1.8;
}
</style>
