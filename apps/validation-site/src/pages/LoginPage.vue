<template>
  <div class="page">
    <div class="card">
      <h1>Sign in</h1>
      <div class="subtitle">WebAgentFlow Validation Site</div>

      <!-- Stable error region, role=alert so it's observable. Hidden when empty. -->
      <div
        v-if="errorMessage"
        class="alert alert-error"
        role="alert"
        data-testid="login-error"
      >
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" novalidate>
        <div class="field">
          <label for="username">Username</label>
          <input
            id="username"
            name="username"
            type="text"
            autocomplete="username"
            placeholder="Enter username"
            v-model="username"
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autocomplete="current-password"
            placeholder="Enter password"
            v-model="password"
          />
        </div>

        <button
          type="submit"
          class="btn btn-primary"
          :disabled="submitting"
        >
          {{ submitting ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <!-- Minor distraction: secondary links that are NOT the main action. -->
      <div class="secondary-links">
        <a href="#forgot">Forgot password?</a>
        <a href="#contact">Contact admin</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const username = ref('');
const password = ref('');
const errorMessage = ref('');
const submitting = ref(false);
const router = useRouter();

async function handleSubmit() {
  errorMessage.value = '';
  submitting.value = true;
  try {
    const res = await axios.post('/validation-api/login', {
      username: username.value,
      password: password.value,
    });
    const data = res.data?.data as { token: string; username: string } | undefined;
    if (data?.token) {
      sessionStorage.setItem('validation_token', data.token);
      sessionStorage.setItem('validation_user', data.username);
      router.push('/dashboard');
      return;
    }
    errorMessage.value = '登录失败：返回数据异常';
  } catch (err: unknown) {
    // Extract msg from backend envelope; fall back to generic.
    const resp = (err as { response?: { data?: { msg?: string } } }).response;
    errorMessage.value = resp?.data?.msg || '用户名或密码错误';
  } finally {
    submitting.value = false;
  }
}
</script>
