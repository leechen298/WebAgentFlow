<template>
  <div>
    <header class="dashboard-header">
      <h2>Validation Site — Dashboard</h2>
      <span>{{ username ? `Signed in as ${username}` : 'Not signed in' }}</span>
    </header>
    <main class="dashboard-content">
      <div class="welcome" data-testid="dashboard-welcome">
        <h1>Welcome, {{ username || 'Guest' }}</h1>
        <p>You have successfully signed in.</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

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
