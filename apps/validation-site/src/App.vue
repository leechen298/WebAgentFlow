<template>
  <div class="validation-shell">
    <LangSwitcher class="lang-switcher" />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import LangSwitcher from './components/LangSwitcher.vue';
</script>

<style>
.validation-shell {
  position: relative;
  min-height: 100vh;
}
.lang-switcher {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1000;
}
</style>
