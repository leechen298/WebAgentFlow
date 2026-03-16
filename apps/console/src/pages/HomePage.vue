<template>
  <div class="grid">
    <n-card title="Project Status">
      <p>WebAgentFlow engineering foundation is ready for subsequent feature work.</p>
    </n-card>
    <n-card title="Included Apps">
      <ul>
        <li>Console</li>
        <li>API</li>
        <li>Worker</li>
        <li>Extension</li>
      </ul>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { NCard } from 'naive-ui';
</script>

<style scoped>
.grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

ul {
  margin: 0;
  padding-left: 18px;
}
</style>
