<template>
  <div class="workspace-page">
    <main class="workspace-card" aria-labelledby="workspace-login-title">
      <div class="workspace-mark" aria-hidden="true">W</div>
      <h1 id="workspace-login-title" data-testid="workspace-login-title">工作台入口</h1>
      <p class="workspace-desc">请输入操作员账号和访问口令以进入工作台</p>

      <div v-if="errorMessage" class="workspace-alert" role="alert" data-testid="login-error">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" novalidate>
        <div class="workspace-field">
          <label for="operator-id">操作员账号</label>
          <input
            id="operator-id"
            name="operator-id"
            type="text"
            autocomplete="username"
            data-testid="operator-id-input"
            placeholder="请输入操作员账号"
            v-model="operatorId"
          />
        </div>

        <div class="workspace-field">
          <label for="access-code">访问口令</label>
          <input
            id="access-code"
            name="access-code"
            type="password"
            autocomplete="current-password"
            data-testid="access-code-input"
            placeholder="请输入访问口令"
            v-model="accessCode"
          />
        </div>

        <button
          type="submit"
          class="workspace-btn"
          data-testid="workspace-submit"
          :disabled="submitting"
        >
          {{ submitting ? '正在进入...' : '进入工作台' }}
        </button>
      </form>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const operatorId = ref('');
const accessCode = ref('');
const errorMessage = ref('');
const submitting = ref(false);
const router = useRouter();

function handleSubmit() {
  errorMessage.value = '';
  submitting.value = true;

  // Deterministic credentials for product-level chat learning
  if (operatorId.value === 'demo' && accessCode.value === '123456') {
    setTimeout(() => {
      router.push('/workspace-home');
      submitting.value = false;
    }, 300);
  } else {
    setTimeout(() => {
      errorMessage.value = '操作员账号或访问口令不正确，请重新输入。';
      submitting.value = false;
    }, 300);
  }
}
</script>

<style scoped>
.workspace-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background:
    linear-gradient(180deg, rgba(24, 144, 255, 0.08), rgba(82, 196, 26, 0.06)),
    #f4f6f8;
}
.workspace-card {
  width: 100%;
  max-width: 420px;
  padding: 32px;
  background: #fff;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  box-shadow: 0 14px 34px rgba(35, 47, 62, 0.12);
}
.workspace-mark {
  display: grid;
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  place-items: center;
  border-radius: 8px;
  background: #1f6feb;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
}
.workspace-card h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #20262e;
  text-align: center;
}
.workspace-desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: #666;
  text-align: center;
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
  padding: 10px 14px;
  border: 1px solid #c8d2dc;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.workspace-field input:focus {
  outline: none;
  border-color: #1f6feb;
  box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.12);
}
.workspace-btn {
  width: 100%;
  padding: 12px;
  background: #1f6feb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}
.workspace-btn:hover {
  background: #1158c7;
}
.workspace-btn:disabled {
  background: #999;
  cursor: not-allowed;
}
</style>
