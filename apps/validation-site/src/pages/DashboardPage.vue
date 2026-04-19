<template>
  <div>
    <header class="dashboard-header">
      <h2>{{ t('dashboard.headerTitle') }}</h2>
      <span>
        {{ username
          ? t('dashboard.signedInAs', { user: username })
          : t('dashboard.notSignedIn') }}
      </span>
    </header>
    <main class="dashboard-content">
      <div class="welcome" data-testid="dashboard-welcome">
        <h1>
          {{ username
            ? t('dashboard.welcome', { user: username })
            : t('dashboard.welcomeGuest') }}
        </h1>
        <p>{{ t('dashboard.body') }}</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const username = ref('');
const router = useRouter();

onMounted(() => {
  const token = sessionStorage.getItem('validation_token');
  const user = sessionStorage.getItem('validation_user');
  if (!token) {
    router.replace('/login');
    return;
  }
  username.value = user || 'User';
});
</script>
