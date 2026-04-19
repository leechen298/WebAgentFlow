<template>
  <div class="page">
    <div class="card">
      <h1>{{ t('login.title') }}</h1>
      <div class="subtitle">{{ t('login.subtitle') }}</div>

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
          <label for="username">{{ t('login.labelUsername') }}</label>
          <input
            id="username"
            name="username"
            type="text"
            autocomplete="username"
            :placeholder="t('login.placeholderUsername')"
            v-model="username"
          />
        </div>

        <div class="field">
          <label for="password">{{ t('login.labelPassword') }}</label>
          <input
            id="password"
            name="password"
            type="password"
            autocomplete="current-password"
            :placeholder="t('login.placeholderPassword')"
            v-model="password"
          />
        </div>

        <button
          type="submit"
          class="btn btn-primary"
          :disabled="submitting"
        >
          {{ submitting ? t('login.submitting') : t('login.submit') }}
        </button>
      </form>

      <!-- Minor distraction: secondary links that are NOT the main action. -->
      <div class="secondary-links">
        <a href="#forgot">{{ t('login.linkForgot') }}</a>
        <a href="#contact">{{ t('login.linkContact') }}</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import axios from 'axios';

const { t } = useI18n();

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
    errorMessage.value = t('login.unexpectedError');
  } catch (err: unknown) {
    // Extract msg from backend envelope; fall back to localized generic.
    const resp = (err as { response?: { data?: { msg?: string } } }).response;
    errorMessage.value = resp?.data?.msg || t('login.genericError');
  } finally {
    submitting.value = false;
  }
}
</script>
