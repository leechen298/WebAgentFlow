<template>
  <div class="login-page">
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">WF</span>
        <div>
          <strong>WebAgentFlow 工作台</strong>
          <span>产品级测试环境</span>
        </div>
      </div>
      <span class="env-badge">本地验证</span>
    </header>

    <main class="login-main">
      <section class="login-context" aria-label="工作台说明">
        <p class="context-label">Business Console</p>
        <h2>业务操作控制台</h2>
        <p>
          统一查看业务任务、运行记录和流程状态。请使用已分配的账号登录后进入工作台。
        </p>
        <dl class="context-grid">
          <div>
            <dt>环境</dt>
            <dd>演示环境</dd>
          </div>
          <div>
            <dt>入口</dt>
            <dd>工作台登录</dd>
          </div>
          <div>
            <dt>目标</dt>
            <dd>访问业务控制台</dd>
          </div>
        </dl>
      </section>

      <section class="login-card" aria-labelledby="workspace-login-title">
        <p class="card-kicker">账号登录</p>
        <h1 id="workspace-login-title" data-testid="workspace-login-title">登录工作台</h1>
        <p class="workspace-desc">使用测试账号登录业务工作台</p>

        <div v-if="errorMessage" class="workspace-alert" role="alert" data-testid="login-error">
          {{ errorMessage }}
        </div>

        <form @submit.prevent="handleSubmit" novalidate>
          <div class="workspace-field">
            <label for="operator-id">用户名</label>
            <input
              id="operator-id"
              name="operator-id"
              type="text"
              autocomplete="username"
              data-testid="operator-id-input"
              placeholder="请输入用户名"
              v-model="username"
            />
          </div>

          <div class="workspace-field">
            <label for="access-code">密码</label>
            <input
              id="access-code"
              name="access-code"
              type="password"
              autocomplete="current-password"
              data-testid="access-code-input"
              placeholder="请输入密码"
              v-model="password"
            />
          </div>

          <button
            type="submit"
            class="workspace-btn"
            data-testid="workspace-submit"
            :disabled="submitting"
          >
            {{ submitting ? '登录中...' : '登录' }}
          </button>
        </form>

        <p class="credential-hint">测试账号：demo / 123456</p>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const submitting = ref(false);
const router = useRouter();

function handleSubmit() {
  errorMessage.value = '';
  submitting.value = true;

  if (username.value === 'demo' && password.value === '123456') {
    setTimeout(() => {
      router.push('/workspace-home');
      submitting.value = false;
    }, 300);
  } else {
    setTimeout(() => {
      errorMessage.value = '用户名或密码错误，请重新输入。';
      submitting.value = false;
    }, 300);
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #f3f5f7;
  color: #1f2933;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 64px;
  padding: 0 32px;
  background: #fff;
  border-bottom: 1px solid #d8dee5;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  background: #174ea6;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.brand strong,
.brand span {
  display: block;
}
.brand strong {
  font-size: 15px;
}
.brand span {
  margin-top: 2px;
  color: #6b7280;
  font-size: 12px;
}
.env-badge {
  padding: 5px 10px;
  border: 1px solid #c7d0d9;
  border-radius: 6px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
}
.login-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 48px;
  align-items: center;
  width: 100%;
  max-width: 1080px;
  min-height: calc(100vh - 65px);
  margin: 0 auto;
  padding: 48px 32px;
  box-sizing: border-box;
}
.login-context {
  max-width: 520px;
}
.context-label,
.card-kicker {
  margin: 0 0 12px;
  color: #174ea6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}
.login-context h2 {
  margin: 0 0 16px;
  font-size: 32px;
  line-height: 1.25;
  color: #111827;
}
.login-context p {
  margin: 0;
  max-width: 500px;
  color: #4b5563;
  font-size: 15px;
  line-height: 1.8;
}
.context-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 28px 0 0;
}
.context-grid div {
  padding: 14px;
  background: #fff;
  border: 1px solid #d8dee5;
  border-radius: 8px;
}
.context-grid dt {
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 12px;
}
.context-grid dd {
  margin: 0;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
}
.login-card {
  width: 100%;
  padding: 32px;
  background: #fff;
  border: 1px solid #d8dee5;
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  box-sizing: border-box;
}
.login-card h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #111827;
}
.workspace-desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: #64748b;
}
.workspace-alert {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  color: #cf1322;
  font-size: 14px;
}
.workspace-field {
  margin-bottom: 20px;
}
.workspace-field label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}
.workspace-field input {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #c8d2dc;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.workspace-field input:focus {
  outline: none;
  border-color: #174ea6;
  box-shadow: 0 0 0 3px rgba(23, 78, 166, 0.12);
}
.workspace-btn {
  width: 100%;
  padding: 12px;
  background: #174ea6;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}
.workspace-btn:hover {
  background: #0f3f8a;
}
.workspace-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
.credential-hint {
  margin: 18px 0 0;
  padding-top: 16px;
  border-top: 1px solid #edf1f5;
  color: #64748b;
  font-size: 13px;
}
@media (max-width: 820px) {
  .topbar {
    padding: 0 20px;
  }
  .login-main {
    grid-template-columns: 1fr;
    gap: 28px;
    min-height: auto;
    padding: 32px 20px;
  }
  .login-context {
    max-width: none;
  }
  .login-context h2 {
    font-size: 26px;
  }
  .context-grid {
    grid-template-columns: 1fr;
  }
}
</style>
